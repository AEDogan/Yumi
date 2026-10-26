"""Yumi: Windows-native 3D desktop companion and voice assistant."""
from __future__ import annotations

import json
import math
import os
import queue
import random
import sys
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import sounddevice as sd
from PySide6.QtCore import QObject, Qt, QTimer, QUrl, Signal, QEvent, QPropertyAnimation, QPoint, QEasingCurve, QCoreApplication
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer, QAudioBufferOutput, QAudioFormat
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QMainWindow, QMenu, QPushButton, QScrollArea, QSystemTrayIcon,
    QVBoxLayout, QWidget, QSlider, QFileDialog, QSizePolicy, QLayout, QTabWidget, QGroupBox, QStackedWidget, QListWidget, QListWidgetItem, QMessageBox)

if QCoreApplication.instance() is None:QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

from api import answer, speech, transcribe
from avatar import AvatarView
from overlay import DesktopCharacter
from system_audio import SystemAudio
from voice_profiles import profile,apply_profile,VOICES,OPENAI_VOICES,character_name,wake_command
from skins import available as available_skins, add_model, remove_model, skin_path, default_skin, valid_skin, is_builtin
from backend import Assistant, local_transcribe, local_speech, login, login_status, OFFLINE_MESSAGE, is_offline_error, offline_warning_speech, prepare_offline_warning
from platform_win import ActivityCounter, GlobalHotkey, protect, unprotect

from app_paths import ROOT,APP_ID,data_dir,env_value,migrated_default_name
DATA_DIR = data_dir()
try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
except PermissionError:
    DATA_DIR = ROOT / 'data'
    DATA_DIR.mkdir(parents=True, exist_ok=True)
os.environ['YUMI_DATA_DIR']=str(DATA_DIR)
SETTINGS_FILE = DATA_DIR / 'settings.json'
KEY_FILE = DATA_DIR / 'key.dat'
GEMINI_KEY_FILE = DATA_DIR / 'gemini-key.dat'
DEFAULTS = {'theme':'ios','panel_opacity':94,'gemini_model':'gemini-3.5-flash-lite','speech_voice':'gemini-live:Kore','skin':default_skin(),'voice':'coral','always_listen':False,'name_wake_enabled':False,'roam':True,'mic_device':'Otomatik','model':'gpt-5.4-mini','provider':'gemini','city':'','size':100}


DEFAULTS.update(daily_scenarios=True,music_family='unknown',music_auto=True)

def load_settings():
    try:
        saved=json.loads(SETTINGS_FILE.read_text(encoding='utf-8'));settings={**DEFAULTS, **saved}
        settings['name_wake_enabled']=bool(saved.get('name_wake_enabled',saved.get('always_listen',False)))
        if settings.get('gemini_model') in ('gemini-flash-lite-latest','gemini-flash-latest','gemini-3.6-flash'):
            settings['gemini_model']=DEFAULTS['gemini_model']
        if not valid_skin(settings.get('skin')):apply_profile(settings,default_skin())
        native_voices={key for _,key,_ in VOICES}
        if settings.get('speech_voice') not in native_voices:settings['speech_voice']='gemini-live:Kore'
        for saved in settings.get('voice_profiles',{}).values():
            if isinstance(saved,dict) and saved.get('speech_voice') not in native_voices:saved['speech_voice']='gemini-live:Kore'
        for saved in settings.get('voice_profiles',{}).values():
            if isinstance(saved,dict) and str(saved.get('name') or '').strip():saved['name']=migrated_default_name(saved['name'])
        settings['speech_voice']=profile(settings)['speech_voice']
        settings['always_listen']=False
        from character_names import migrate
        if migrate(settings):save_settings(settings)
        return settings
    except (OSError, ValueError):
        return DEFAULTS.copy()


def save_settings(settings):
    temporary=SETTINGS_FILE.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(SETTINGS_FILE)


def load_key():
    try:
        return unprotect(KEY_FILE.read_bytes()).decode('utf-8')
    except (OSError, UnicodeError):
        return os.getenv('OPENAI_API_KEY','')


def load_gemini_key():
    try:return unprotect(GEMINI_KEY_FILE.read_bytes()).decode('utf-8')
    except (OSError,UnicodeError):return os.getenv('GEMINI_API_KEY','')


class Signals(QObject):
    hotkey = Signal()


class VoiceCapture:
    """Local VAD turns microphone sound into bounded WAV snippets."""
    def __init__(self, completed, status, device_name='Otomatik'):
        self.completed = completed
        self.status = status
        self.blocks = queue.Queue(maxsize=100)
        self.stream = None
        self.always = False
        self.manual = False
        self.recording = []
        self.started = 0.0
        self.last_loud = 0.0
        self._suspended = False;self.resume_after=0.;self.voiced_seconds=0.
        self.device_name = device_name
        self.wake_name='Yumi'
        self.noise_floor=.008;self.had_speech=False;self.pre_roll=deque(maxlen=3);self.wake_armed_until=0.
        self.sample_rate = 16000
        self.timer = QTimer()
        self.timer.timeout.connect(self._pump)
        self.timer.start(100)

    @property
    def suspended(self):return self._suspended

    @suspended.setter
    def suspended(self,value):
        value=bool(value)
        if value==self._suspended:return
        self._suspended=value
        self.recording=[];self.had_speech=False;self.pre_roll.clear();self.voiced_seconds=0.
        self.wake_armed_until=0.
        while not self.blocks.empty():
            try:self.blocks.get_nowait()
            except queue.Empty:break
        # Discard device buffers and the tail of our own speaker output.
        self.resume_after=time.perf_counter()+(.35 if not value else 0.)

    def _callback(self, data, frames, timing, flags):
        if self.suspended or time.perf_counter()<self.resume_after:return
        try:
            self.blocks.put_nowait((data[:,0].copy(),time.perf_counter()))
        except queue.Full:
            pass

    def ensure_stream(self):
        if self.stream is None:
            devices=sd.query_devices()
            choices=[i for i,d in enumerate(devices) if d['max_input_channels']>0]
            if self.device_name!='Otomatik':
                choices.sort(key=lambda i:0 if devices[i]['name']==self.device_name else 1)
            else:
                default=sd.default.device[0]
                choices.sort(key=lambda i:0 if i==default else 1)
            errors=[]
            for index in choices:
                rates=list(dict.fromkeys([16000,int(devices[index]['default_samplerate'])]))
                for rate in rates:
                    try:
                        stream=sd.InputStream(device=index,samplerate=rate,channels=1,dtype='float32',
                                              blocksize=int(rate/10),callback=self._callback)
                        stream.start()
                        self.stream=stream
                        self.sample_rate=rate
                        return
                    except Exception as error:
                        errors.append(str(error))
            raise RuntimeError('Kullanılabilir mikrofon açılamadı. Windows ses giriş aygıtını ve mikrofon izinlerini kontrol edin.')

    def set_always(self, enabled):
        self.always = enabled
        if enabled:
            self.ensure_stream()
            self.status(f'“{self.wake_name}” diye seslen')
        elif not self.manual:
            self._stop_stream()
            self.status('Hazır')

    def toggle_manual(self):
        if self.manual:
            self.manual = False
            self._finish(requires_wake=False)
            if not self.always: self._stop_stream()
        else:
            self.ensure_stream()
            self.manual = True
            self.recording = [];self.had_speech=False;self.pre_roll.clear();self.voiced_seconds=0.
            self.started = time.perf_counter()
            self.last_loud = self.started
            self.status('Dinliyorum…')

    def _stop_stream(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        while not self.blocks.empty():
            try: self.blocks.get_nowait()
            except queue.Empty: break

    def _finish(self, requires_wake=True):
        if not self.recording: return
        samples = np.concatenate(self.recording)
        self.recording = []
        voiced=self.voiced_seconds;self.voiced_seconds=0.
        if len(samples) >= self.sample_rate//2 and voiced>=.25:
            if self.sample_rate!=16000:
                length=max(1,round(len(samples)*16000/self.sample_rate))
                samples=np.interp(np.linspace(0,len(samples)-1,length),np.arange(len(samples)),samples).astype('float32')
            self.completed(samples, requires_wake)

    def arm_next_utterance(self):
        self.suspended=False;self.wake_armed_until=time.perf_counter()+10;self.recording=[];self.had_speech=False;self.voiced_seconds=0.;self.status('Dinliyorum, söyle…')
    def _pump(self):
        while True:
            try:item=self.blocks.get_nowait()
            except queue.Empty:break
            block,now=item if isinstance(item,tuple) else (item,time.perf_counter())
            if self.suspended or now<self.resume_after:continue
            if not self.manual and not self.always:continue
            level=float(np.sqrt(np.mean(np.square(block))))
            start_threshold=max(.012,min(.035,self.noise_floor*3.))
            continue_threshold=max(.008,min(.025,self.noise_floor*1.8))
            loud=level>(continue_threshold if self.had_speech else start_threshold)
            if not self.had_speech and not loud:self.noise_floor=.98*self.noise_floor+.02*min(level,.015)
            if loud:
                self.voiced_seconds+=len(block)/self.sample_rate
                self.last_loud=now
                if not self.had_speech:
                    self.started=now;self.recording=list(self.pre_roll);self.had_speech=True;self.status('Seni dinliyorum…')
            if self.had_speech:
                self.recording.append(block)
                if now-self.last_loud>=.75 or now-self.started>=10:
                    manual=self.manual;armed=time.perf_counter()<self.wake_armed_until;self.manual=False;self.had_speech=False;self.pre_roll.clear();self.wake_armed_until=0.
                    self._finish(requires_wake=not(manual or armed))
                    if manual and not self.always:self._stop_stream()
            else:
                self.pre_roll.append(block)
                if self.manual and now-self.started>=8:
                    self.manual=False;self.recording=[];self.status('Ses algılanmadı; tekrar deneyebilirsin.')
                    if not self.always:self._stop_stream()
        if self.manual and not self.had_speech and time.perf_counter()-self.started>=8:
            self.manual=False;self.recording=[];self.status('Ses algılanmadı; tekrar deneyebilirsin.')
            if not self.always:self._stop_stream()
        if self.wake_armed_until and time.perf_counter()>self.wake_armed_until and not self.had_speech:
            self.wake_armed_until=0.;self.status(f'“{self.wake_name}” diye seslen')

    def close(self):
        self.timer.stop()
        self._stop_stream()


class SettingsDialog(QDialog):
    def __init__(self,parent):
        super().__init__(parent);self.owner=parent;self.setWindowTitle('Yumi · Ayarlar');self.setWindowFlags(Qt.WindowType.Widget);self.setModal(False)
        self.setWindowFlag(Qt.WindowType.WindowMinimizeButtonHint,False)
        from ui_shell import SectionTabs,ThemePicker
        outer=QVBoxLayout(self);outer.setContentsMargins(20,18,20,18);outer.setSpacing(18);title=QHBoxLayout();title.addWidget(QLabel('Ayarlar'));title.addStretch();back=QPushButton('Sohbete dön');back.clicked.connect(self.reject);title.addWidget(back);outer.addLayout(title);self.setObjectName('settingsPage');self.tabs=SectionTabs();outer.addWidget(self.tabs,1)
        def tab(title):
            scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QFrame.Shape.NoFrame);scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll.viewport().setAutoFillBackground(False)
            content=QWidget();content.setObjectName('settingsContent');scroll.setWidget(content);layout=QVBoxLayout(content);layout.setSpacing(12);layout.setAlignment(Qt.AlignmentFlag.AlignTop);self.tabs.addTab(scroll,title);return layout
        title.itemAt(0).widget().setObjectName('heading')
        assistant=tab('Asistan');sound=tab('Ses');character=tab('Model');behavior=tab('Davranış');appearance=tab('Görünüm')
        appearance.addWidget(QLabel('Renk teması'));self.theme=QComboBox()
        from themes import THEMES
        for title,key in THEMES:self.theme.addItem(title,key)
        self.theme.setCurrentIndex(max(0,self.theme.findData(parent.settings.get('theme','pearl'))));self.theme.hide();self.theme_picker=ThemePicker(self.theme);appearance.addWidget(self.theme_picker)
        self.opacity_label=QLabel();appearance.addWidget(self.opacity_label);self.opacity=QSlider(Qt.Orientation.Horizontal);self.opacity.setRange(45,100);self.opacity.setValue(parent.settings.get('panel_opacity',94));appearance.addWidget(self.opacity)
        self.opacity.valueChanged.connect(lambda value:self.opacity_label.setText(f'Arka plan doluluğu · %{value}'));self.opacity_label.setText(f'Arka plan doluluğu · %{self.opacity.value()}')
        self.theme.currentIndexChanged.connect(self.preview_theme)
        self.opacity.valueChanged.connect(self.preview_theme)
        hint=QLabel('Saydamlık yalnızca pencere arka planını etkiler; yazılar okunaklı kalır. Karakter masaüstünde görünür.');hint.setWordWrap(True);appearance.addWidget(hint)
        assistant.addWidget(QLabel('Hesapla bağlan'))
        account_row=QVBoxLayout();self.account_buttons={}
        for caption,site in [('Gemini hesabımla giriş yap','gemini-web'),('ChatGPT hesabımla giriş yap','chatgpt-web')]:
            button=QPushButton(caption);button.setObjectName('accountButton')
            button.clicked.connect(lambda checked=False,site=site:self.login_account(site))
            self.account_buttons[site]=button;account_row.addWidget(button)
        assistant.addLayout(account_row)
        account_note=QLabel('Web sohbeti için API anahtarı gerekmez. Kendi hesabına açılan tarayıcıda giriş yap; oturum bu bilgisayardaki Yumi profilinde korunur. Girişten sonra “Giriş tamamlandı” düğmesine bas.')
        account_note.setWordWrap(True);assistant.addWidget(account_note)
        assistant.addWidget(QLabel('Sohbet bağlantısı'))
        self.provider=QComboBox()
        for title,value in [('Gemini · hesabımla (anahtarsız)','gemini-web'),('ChatGPT · hesabımla (anahtarsız)','chatgpt-web'),('Gemini API · gelişmiş bağlantı','gemini')]:self.provider.addItem(title,value)
        self.provider.setCurrentIndex(max(0,self.provider.findData(parent.settings['provider'])));assistant.addWidget(self.provider)
        routing=QLabel('Web bağlantısı seçtiğin hesabı ve sitenin kullanım sınırlarını kullanır. Gemini Live sesli sohbeti ayrı bir bağlantıdır; web hesabıyla giriş, canlı ses API erişimini otomatik sağlamaz.');routing.setWordWrap(True);assistant.addWidget(routing)
        self.browser_login=QPushButton('Seçilen siteye giriş yap');self.browser_login.clicked.connect(lambda:parent._browser_login(self.provider.currentData()));assistant.addWidget(self.browser_login)
        self.browser_hide=QPushButton('Giriş tamamlandı · tarayıcıyı arka plana al');self.browser_hide.clicked.connect(lambda:parent._browser_login(self.provider.currentData(),True));assistant.addWidget(self.browser_hide)
        self.browser_status=QLabel('Girişten sonra ikinci düğmeye bas; Yumi pencereyi kapatıp bağlantıyı hazırlayacak.');self.browser_status.setWordWrap(True);assistant.addWidget(self.browser_status)
        parent.browser_status_changed.connect(self.show_browser_status)
        self.openai_group=QGroupBox('OpenAI bağlantısı');assistant.addWidget(self.openai_group);oa=QVBoxLayout(self.openai_group)
        self.openai_connection=QComboBox();self.openai_connection.addItems(['Codex hesabımla','API anahtarımla']);self.openai_connection.setCurrentIndex(1 if parent.settings['provider']=='openai' else 0);oa.addWidget(self.openai_connection)
        self.signin=QPushButton('Codex / ChatGPT hesabımla giriş yap');self.signin.clicked.connect(parent._login);oa.addWidget(self.signin)
        self.openai_api_group=QGroupBox('API ayarları');oa.addWidget(self.openai_api_group);api_layout=QVBoxLayout(self.openai_api_group)
        self.key=QLineEdit();self.key.setEchoMode(QLineEdit.EchoMode.Password);self.key.setPlaceholderText('Kayıtlı · değiştirmek için yeni anahtar gir' if parent.api_key else 'OpenAI API anahtarı · sk-…');api_layout.addWidget(self.key)
        save=QPushButton('Anahtarı kaydet');save.clicked.connect(self.save_key);api_layout.addWidget(save)
        self.key_status=QLabel('Anahtar hazır.' if parent.api_key else 'API bağlantısı için anahtar ekle.');self.key_status.setWordWrap(True);api_layout.addWidget(self.key_status)
        delete=QPushButton('Anahtarı sil');delete.clicked.connect(self.delete_key);api_layout.addWidget(delete)
        api_layout.addWidget(QLabel('OpenAI model adı'));self.openai_model=QLineEdit(parent.settings['model']);api_layout.addWidget(self.openai_model)
        self.gemini_group=QGroupBox('Gemini bağlantısı');assistant.addWidget(self.gemini_group);ga=QVBoxLayout(self.gemini_group)
        self.gemini_key=QLineEdit();self.gemini_key.setEchoMode(QLineEdit.EchoMode.Password);self.gemini_key.setPlaceholderText('Kayıtlı · değiştirmek için yeni anahtar gir' if parent.gemini_key else 'Google AI Studio anahtarı');ga.addWidget(self.gemini_key)
        save=QPushButton('Anahtarı kaydet');save.clicked.connect(self.save_gemini_key);ga.addWidget(save)
        self.gemini_status=QLabel('Anahtar hazır.' if parent.gemini_key else 'Gemini için API anahtarı ekle.');self.gemini_status.setWordWrap(True);ga.addWidget(self.gemini_status)
        delete=QPushButton('Anahtarı sil');delete.clicked.connect(self.delete_gemini_key);ga.addWidget(delete)
        from gemini_chat import CHAT_MODELS
        ga.addWidget(QLabel('Sohbet modeli'));self.gemini_model=QComboBox()
        for title,value in CHAT_MODELS:self.gemini_model.addItem(title,value)
        self.gemini_model.setCurrentIndex(max(0,self.gemini_model.findData(parent.settings['gemini_model'])));ga.addWidget(self.gemini_model)
        hint=QLabel('Flash-Lite hız için, Flash daha güçlü yanıtlar için. Free tier kotası dolunca ücretli modele veya web hesabına otomatik geçilmez.');hint.setWordWrap(True);ga.addWidget(hint)
        assistant.addWidget(QLabel('Hava durumu için şehir (isteğe bağlı)'));self.city=QLineEdit(parent.settings['city']);self.city.setPlaceholderText('Boşsa Yumi sorar');assistant.addWidget(self.city)
        self.provider.currentIndexChanged.connect(self.update_provider_fields);self.openai_connection.currentIndexChanged.connect(self.update_provider_fields);self.update_provider_fields()
        sound.addWidget(QLabel('Bu karakter için tercih edilen ses tonu'))
        self.voice_gender=QComboBox()
        for title,key in [('Kadın','female'),('Erkek','male'),('Serbest seçim','any')]:self.voice_gender.addItem(title,key)
        current_profile=profile(parent.settings);self.voice_gender.setCurrentIndex(max(0,self.voice_gender.findData(current_profile['gender'])));sound.addWidget(self.voice_gender)
        sound.addWidget(QLabel('Ses motoru / konuşma modeli'));self.speech_voice=QComboBox();sound.addWidget(self.speech_voice)
        self.fill_voices(current_profile['speech_voice']);self.voice_gender.currentIndexChanged.connect(lambda _:self.fill_voices())
        self.voice=QComboBox();self.voice.addItems(OPENAI_VOICES);self.voice.setCurrentText(current_profile['voice']);sound.addWidget(self.voice)
        self.voice.setVisible(self.speech_voice.currentData()=='openai-tts');self.speech_voice.currentIndexChanged.connect(lambda _:self.voice.setVisible(self.speech_voice.currentData()=='openai-tts'))
        preview=QPushButton('Seçili sesi dene');preview.clicked.connect(self.preview_voice);sound.addWidget(preview)
        self.preview_status=QLabel();self.preview_status.setWordWrap(True);sound.addWidget(self.preview_status)
        from voice_preview import VoicePreview
        self.voice_preview=VoicePreview(self,parent,preview,self.preview_status)
        self.speech_voice.currentIndexChanged.connect(lambda *_:self.voice_preview.cancel())
        self.voice.currentTextChanged.connect(lambda *_:self.voice_preview.cancel())
        note=QLabel('Yalnız sağlayıcının native canlı sesleri kullanılıyor. Gemini bağlantısı hazır bekler; mikrofon düğmesi sesli sohbeti açar/kapatır. Beklemede ortam sesi gönderilmez. OpenAI canlı sesi için API erişimi gerekli; kayıtlı anahtar yok ve denenmedi.');note.setWordWrap(True);sound.addWidget(note)
        sound.addWidget(QLabel('Mikrofon'));self.mic_device=QComboBox();self.mic_device.addItem('Varsayılan mikrofon','Otomatik')
        self.mic_device.setMinimumHeight(42);self.mic_device.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed)
        self.mic_device.setToolTip('Mikrofon seçmek için aç')
        try:
            from audio_devices import input_devices
            for index,name in input_devices(sd):
                self.mic_device.addItem(name,name)
                self.mic_device.setItemData(self.mic_device.count()-1,name,Qt.ItemDataRole.ToolTipRole)
        except Exception:pass
        self.mic_device.setCurrentIndex(max(0,self.mic_device.findData(parent.settings['mic_device'])));sound.addWidget(self.mic_device)
        self.always=QCheckBox('Model adıyla sesli sohbet başlat');self.always.setToolTip('Yalnız etkin karakterin çağrı adı yerelde algılanır. Beklerken ortam sesi Gemini’ye gönderilmez. Adı söyleyip Dinliyor durumunu bekle.');self.always.setChecked(parent.settings.get('name_wake_enabled',False))
        self.character_drafts={};self.editing_skin=parent.settings['skin']
        character.addWidget(QLabel('Model kütüphanesi'));self.skin=QComboBox();character.addWidget(self.skin);self.fill_skins(parent.settings['skin'])
        row=QHBoxLayout();remove=QPushButton('Kaldır');self.remove_skin_button=remove;remove.setToolTip('Seçili modeli kaldır');remove.clicked.connect(self.remove_skin);row.addWidget(remove);character.addLayout(row)
        inspect=QPushButton('Modeli önizle');inspect.clicked.connect(self.inspect_skin);character.addWidget(inspect);character.addWidget(self.always)
        voice_button=QPushButton('Konuşma sesini değiştir');voice_button.clicked.connect(lambda:self.tabs.setCurrentIndex(1));character.addWidget(voice_button)
        self.character_drafts={};self.editing_skin=parent.settings['skin']
        self.adult_character=QCheckBox('Bu karakterin 18 yaşından büyük olduğunu doğruluyorum');self.adult_character.setChecked(bool(current_profile.get('adult',False)))
        self.skin.currentIndexChanged.connect(self.load_character_voice)
        self.skin_info=QLabel();self.skin_info.setWordWrap(True);character.addWidget(self.skin_info);self.skin.currentIndexChanged.connect(self.describe_skin);self.describe_skin()
        self.size_label=QLabel();character.addWidget(self.size_label);self.size=QSlider(Qt.Orientation.Horizontal);self.size.setRange(50,180);self.size.setValue(parent.settings['size']);character.addWidget(self.size)
        self.size.valueChanged.connect(lambda value:self.size_label.setText(f'Karakter boyutu · %{value}'));self.size_label.setText(f"Karakter boyutu · %{parent.settings['size']}")
        self.profile_status=QLabel('Ses ve boyut tercihleri bu modele özel otomatik kaydedilir.');self.profile_status.setWordWrap(True);character.addWidget(self.profile_status)
        self.voice_gender.activated.connect(self._save_character_profile);self.speech_voice.activated.connect(self._save_character_profile);self.voice.activated.connect(self._save_character_profile)
        self.adult_character.clicked.connect(self._save_character_profile);self.size.sliderReleased.connect(self._save_character_profile)
        note=QLabel('Masaüstünde sağ tık > Model seç ile kayıtlı modeller arasında geçebilirsin. Fare tekerleği boyutu değiştirir.');note.setWordWrap(True);character.addWidget(note)
        add=QPushButton('Model paketi ekle');add.setToolTip('Onaylı Yumi model paketini ekle');add.clicked.connect(self.add_skin);character.addWidget(add)
        from windows_startup import enabled as startup_enabled
        self.windows_startup=QCheckBox('Windows açıldığında Yumi’yi başlat');self.windows_startup.setChecked(startup_enabled());behavior.addWidget(self.windows_startup)
        self.roam=QCheckBox('Görev çubuğu boyunca gezinsin');self.roam.setChecked(parent.settings['roam']);behavior.addWidget(self.roam)
        button=QPushButton('Animasyon dosyaları');button.clicked.connect(lambda:self.open_tool(parent._motion_library));behavior.addWidget(button)
        note=QLabel('Elle sürüklemek gezinmeyi durdurur. Sağ tık > Görev çubuğuna dön ve gezin ile devam eder.');note.setWordWrap(True);behavior.addWidget(note)
        close=QPushButton('Değişiklikleri kaydet');close.setObjectName('primaryButton');close.clicked.connect(self.accept);outer.addWidget(close)
        for combo in self.findChildren(QComboBox):
            combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            combo.setMinimumContentsLength(12);combo.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed)
        self.preview_theme()
    def preview_theme(self,*args):
        from themes import stylesheet
        style=stylesheet(self.theme.currentData(),self.opacity.value())
        self.owner.setStyleSheet(style)
        self.owner._refresh_icons(self.theme.currentData())
        self.setStyleSheet(style)
    def reject(self):
        if not self._save_character_profile():return
        self.owner.apply_theme()
        super().reject()
    def open_tool(self,action):
        QTimer.singleShot(0,action)
    def fill_voices(self,selected=None):
        previous=self.speech_voice.currentData();chosen=selected or previous;self.speech_voice.blockSignals(True);self.speech_voice.clear();gender=self.voice_gender.currentData()
        for title,key,tone in VOICES:
            if gender=='any' or tone in (gender,'any'):self.speech_voice.addItem(title,key)
        index=self.speech_voice.findData(chosen);self.speech_voice.setCurrentIndex(max(0,index));self.speech_voice.blockSignals(False)
        if previous!=self.speech_voice.currentData() and hasattr(self,'voice_preview'):self.voice_preview.cancel()
        if hasattr(self,'voice'):self.voice.setVisible(self.speech_voice.currentData()=='openai-tts')
    def show_browser_status(self,message,pending):
        self.browser_status.setText(message);self.browser_login.setEnabled(not pending);self.browser_hide.setEnabled(not pending)
        for button in self.account_buttons.values():button.setEnabled(not pending)

    def login_account(self,provider):
        self.provider.setCurrentIndex(self.provider.findData(provider))
        self.owner._browser_login(provider)

    def load_character_voice(self,*args,store_current=True):
        selected=self.skin.currentData()
        if not selected:return
        if store_current and getattr(self,'editing_skin',None):
            if not self._save_character_profile():
                self.skin.blockSignals(True);self.skin.setCurrentIndex(self.skin.findData(self.editing_skin));self.skin.blockSignals(False);return
        saved=self.character_drafts.get(selected,profile(self.owner.settings,selected));self.editing_skin=selected
        self.voice_gender.setCurrentIndex(max(0,self.voice_gender.findData(saved['gender'])));self.fill_voices(saved['speech_voice']);self.voice.setCurrentText(saved['voice']);self.voice.setVisible(self.speech_voice.currentData()=='openai-tts');self.adult_character.setChecked(bool(saved.get('adult',False)))
        if hasattr(self,'size'):self.size.setValue(int(saved.get('size',100)))

    def character_values(self):
        saved=profile(self.owner.settings,self.editing_skin)
        return {**saved,'name':saved['name'],'wake_alias':'','gender':self.voice_gender.currentData(),'speech_voice':self.speech_voice.currentData(),'voice':self.voice.currentText(),'adult':self.adult_character.isChecked(),'size':self.size.value()}

    def _save_character_profile(self,*args):
        if not getattr(self,'editing_skin',None) or not hasattr(self,'size'):return True
        values=self.character_values();self.character_drafts[self.editing_skin]=values
        old=self.owner.settings
        profiles={**old.get('voice_profiles',{}),**self.character_drafts}
        if profiles==old.get('voice_profiles',{}):return True
        candidate={**old,'voice_profiles':profiles};active=profile(candidate)
        candidate.update(speech_voice=active['speech_voice'],voice=active.get('voice','marin'),size=int(active.get('size',old['size'])))
        try:save_settings(candidate)
        except OSError:
            self.profile_status.setText('Profil kaydedilemedi. Değişiklikler burada korunuyor; tekrar dene.');return False
        previous_name=character_name(old);previous_voice=old.get('speech_voice');previous_size=old.get('size')
        old.update(candidate);self.owner.voice_capture.wake_name=character_name(old)
        if previous_size!=old['size']:self.owner.overlay.set_scale(old['size'])
        self.owner._sync_name_wake()
        if previous_name!=character_name(old) or previous_voice!=old['speech_voice']:QTimer.singleShot(0,self.owner._warm_native)
        self.profile_status.setText('Bu modelin tercihleri kaydedildi.');return True

    def update_provider_fields(self,*args):
        self.openai_group.hide();self.gemini_group.setVisible(self.provider.currentData()=='gemini')
        for field in (self.browser_login,self.browser_hide,self.browser_status):field.setVisible(self.provider.currentData() in ('chatgpt-web','gemini-web'))
        self.openai_api_group.setVisible(self.openai_connection.currentIndex()==1);self.signin.setVisible(self.openai_connection.currentIndex()==0)
    def preview_voice(self):
        self.voice_preview.start(self.speech_voice.currentData(),self.voice.currentText())

    def fill_skins(self,selected):
        self.skin.blockSignals(True)
        self.skin.clear()
        from skins import grouped_available
        for group,entries in grouped_available(self.owner.settings):
            self.skin.addItem(group if entries else group+' · henüz eklenmedi',None)
            self.skin.model().item(self.skin.count()-1).setEnabled(False)
            for title,key in entries:self.skin.addItem(title,key)
        index=self.skin.findData(selected);self.skin.setCurrentIndex(index if index>=0 else next((i for i in range(self.skin.count()) if self.skin.itemData(i)), -1))
        self.skin.blockSignals(False)
        if hasattr(self,'skin_info'):self.load_character_voice(store_current=False)

    def describe_skin(self):
        key=self.skin.currentData() or ''
        self.remove_skin_button.setEnabled(bool(skin_path(key)) and not is_builtin(key))
        self.remove_skin_button.setToolTip('Yerleşik karakter kaldırılamaz.' if is_builtin(key) else 'Seçili modeli kaldır')
        path=skin_path(self.skin.currentData() or '')
        if path:
            from vrm import load_data
            meta=load_data(str(path.resolve())).meta
            self.skin_info.setText('Yazar: '+str(meta.get('author',', '.join(meta.get('authors',[]))))+' · '+str(meta.get('format','VRM'))+' model · ticari kullanım: '+str(meta.get('commercialUssageName',meta.get('commercialUsage','belirtilmemiş'))))
        elif self.skin.currentData()=='Clippy':self.skin_info.setText('Orijinal Microsoft Clippit · 43 animasyon · sesli sohbet · konuşma balonu yok.')
        else:self.skin_info.setText('Karakter dosyası bulunamadı.')

    def inspect_skin(self):
        path=skin_path(self.skin.currentData() or '')
        if not path:self.skin_info.setText('Önizleme için kütüphaneden bir VRM karakter seç.');return
        from three_vrm_view import ThreeVRMInspection
        self.owner._push_page(ThreeVRMInspection(self.owner,path))

    def add_skin(self):
        paths,_=QFileDialog.getOpenFileNames(self,'Model paketi ekle',str(Path.home()/'Downloads'),'Yumi model paketi (*.yumimodel)')
        from model_setup import import_models
        def completed(keys):
            if keys:
                for key in keys:self.character_drafts[key]=dict(profile(self.owner.settings,key))
                self.fill_skins(keys[-1]);self.describe_skin()
        import_models(self.owner,paths,completed)

    def remove_skin(self):
        key=self.skin.currentData() or ''
        if is_builtin(key) or not key.startswith('vrm:'):return
        try:
            if self.owner.settings['skin']==key:
                fallback=default_skin()
                self.owner.avatar.skin=fallback;self.owner.overlay.avatar.skin=fallback
                apply_profile(self.owner.settings,fallback);save_settings(self.owner.settings)
            remove_model(key);self.fill_skins(self.owner.settings['skin']);self.describe_skin()
        except Exception as error:self.owner.show_error('Model kaldırılamadı: '+str(error))

    def save_key(self):
        value=self.key.text().strip()
        if not value.startswith('sk-') or len(value)<25:
            self.key_status.setText('Geçerli bir OpenAI API anahtarı girin.'); return False
        try:
            temporary=KEY_FILE.with_suffix('.tmp');temporary.write_bytes(protect(value.encode('utf-8')));temporary.replace(KEY_FILE)
            self.owner.api_key=value
            self.owner.previous_id=None
            self.key.clear();self.key.setPlaceholderText('Kayıtlı · değiştirmek için yeni anahtar gir')
            self.key_status.setText('Anahtar Windows hesabınızla şifrelenerek kaydedildi.')
        except OSError as error:
            self.key_status.setText(str(error));return False
        return True

    def delete_key(self):
        try: KEY_FILE.unlink(missing_ok=True)
        except OSError: pass
        self.owner.api_key=os.getenv('OPENAI_API_KEY','')
        self.owner.previous_id=None
        self.key_status.setText('Kaydedilmiş anahtar silindi.')

    def save_gemini_key(self):
        value=self.gemini_key.text().strip()
        if len(value)<20:self.gemini_status.setText('Geçerli bir Gemini API anahtarı gir.');return False
        try:
            temporary=GEMINI_KEY_FILE.with_suffix('.tmp');temporary.write_bytes(protect(value.encode('utf-8')));temporary.replace(GEMINI_KEY_FILE);self.owner.gemini_key=value;self.gemini_key.clear();self.gemini_key.setPlaceholderText('Kayıtlı · değiştirmek için yeni anahtar gir');self.gemini_status.setText('Gemini anahtarı Windows hesabınla şifrelenerek kaydedildi.')
        except OSError as error:self.gemini_status.setText(str(error));return False
        return True
    def delete_gemini_key(self):
        GEMINI_KEY_FILE.unlink(missing_ok=True);self.owner.gemini_key=os.getenv('GEMINI_API_KEY','');self.gemini_status.setText('Kaydedilmiş Gemini anahtarı silindi.')

    def accept(self):
        if not self._save_character_profile():return
        if self.key.text().strip() and not self.save_key():return
        if self.gemini_key.text().strip() and not self.save_gemini_key():return
        from windows_startup import enabled as startup_enabled,set_enabled as set_startup
        try:
            if self.windows_startup.isChecked()!=startup_enabled():set_startup(self.windows_startup.isChecked())
        except OSError:
            self.owner.show_error('Windows başlangıç ayarı kaydedilemedi.');return
        old_always=self.owner.settings.get('name_wake_enabled',False)
        previous_provider=self.owner.settings['provider']
        self.character_drafts[self.skin.currentData()]=self.character_values()
        self.owner.settings.setdefault('voice_profiles',{}).update(self.character_drafts)
        self.owner.settings.update(theme=self.theme.currentData(),panel_opacity=self.opacity.value(),speech_voice=self.speech_voice.currentData(),skin=self.skin.currentData(), voice=self.voice.currentText(),mic_device=self.mic_device.currentData(),
            provider=self.provider.currentData(),model=self.openai_model.text().strip() or DEFAULTS['model'],gemini_model=self.gemini_model.currentData(),city=self.city.text().strip(),size=self.size.value(),
            always_listen=False,name_wake_enabled=self.always.isChecked(),roam=self.roam.isChecked())
        if previous_provider!=self.owner.settings['provider']:self.owner.previous_id=None
        save_settings(self.owner.settings)
        self.owner._work('browser_warm',self.owner.assistant.warm_browser)
        self.owner.voice_capture.wake_name=character_name(self.owner.settings)
        self.owner.apply_theme()
        self.owner.avatar.skin=self.owner.settings['skin']
        self.owner.overlay.set_scale(self.size.value())
        if self.owner.voice_capture.device_name!=self.mic_device.currentData():
            self.owner.voice_capture._stop_stream()
            self.owner.voice_capture.device_name=self.mic_device.currentData()
        self.owner._sync_name_wake()
        QTimer.singleShot(0,lambda:self.owner._warm_native(force=True))
        super().accept()


class YumiWindow(QMainWindow):
    browser_status_changed=Signal(str,bool)
    skill_alert_received=Signal(str,dict)
    skill_result_received=Signal(str,dict)
    def __init__(self):
        super().__init__()
        self.settings=load_settings()
        for key in tuple(self.settings):
            if key.startswith('dance_') or key in ('auto_dance','adult_dance'):self.settings.pop(key)
        save_settings(self.settings)
        self.api_key=load_key()
        self.gemini_key=load_gemini_key()
        self.previous_id=None
        self.assistant=Assistant(self.settings,DATA_DIR)
        self.executor=ThreadPoolExecutor(max_workers=3)
        self.chat_executor=ThreadPoolExecutor(max_workers=1)
        self.results=queue.Queue()
        if not env_value('TEST_OUTPUT') and not env_value('DISABLE_BROWSER'):
            self._work('browser_warm',self.assistant.warm_browser)
        self.activity=ActivityCounter()
        self.system_audio=SystemAudio()
        self.manual_pose=None
        self.manual_pose_end=0
        self.last_user_action=time.perf_counter()
        self.busy=False
        self.reply_pending=False
        self.speech_queue=deque()
        self.speech_active=False
        self.speech_epoch=0
        self.chat_history=[]
        self.exiting=False
        self.drag_pos=None
        self.bubble_generation=0
        self.setWindowTitle('Yumi · 3D Masaüstü Asistanı')
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(440,500)
        saved_size=self.settings.get('chat_window_size',[640,600])
        if not isinstance(saved_size,(list,tuple)) or len(saved_size)!=2 or not all(isinstance(n,int) and not isinstance(n,bool) for n in saved_size):saved_size=[640,600]
        available=QApplication.primaryScreen().availableGeometry()
        self.resize(max(440,min(saved_size[0],available.width())),max(500,min(saved_size[1],available.height())))
        self._build_ui()
        from window_resize import WindowResize
        self.window_resize=WindowResize(self)
        self.resize_save_timer=QTimer(self);self.resize_save_timer.setSingleShot(True)
        self.resize_save_timer.timeout.connect(self._remember_window_size)
        self.chat_expiry=QTimer(self);self.chat_expiry.setInterval(60000);self.chat_expiry.timeout.connect(self._expire_chats);self.chat_expiry.start()
        import sys
        parent_dir=str(ROOT.parent)
        if parent_dir not in sys.path:sys.path.insert(0,parent_dir)
        try:
            from yumi_skills import YumiSkillEngine
            from yumi_skills.dispatcher import SkillDispatcher
            self.skill_alert_received.connect(self._on_skill_alert)
            self.skill_result_received.connect(self._on_skill_result)
            self.skill_engine=YumiSkillEngine(custom_storage_dir=str(DATA_DIR),on_alert_callback=self.skill_alert_received.emit)
            self.skill_engine.on_result=self.skill_result_received.emit
            self.skill_dispatcher=SkillDispatcher(self.skill_engine)
            from gemini_chat import set_skill_engine
            set_skill_engine(self.skill_engine)
        except Exception:
            self.skill_engine=None
            self.skill_dispatcher=None
        self.overlay=DesktopCharacter(self)
        self.move_animation=QPropertyAnimation(self.overlay,b'pos',self)
        self.move_animation.setDuration(2000)
        self.move_animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        from model_visibility import apply as apply_model_visibility
        apply_model_visibility(self)
        self._tray()
        self.voice_capture=VoiceCapture(self._audio_complete,self.set_status,self.settings['mic_device'])
        self.voice_capture.wake_name=character_name(self.settings)
        from native_wake import NativeWake
        self.name_wake=NativeWake(self)
        self.name_wake.wakeDetected.connect(self._wake_called)
        self.name_wake.ready.connect(self._wake_ready)
        self.name_wake.failed.connect(self._wake_failed)
        self.audio_output=QAudioOutput(self)
        self.player=QMediaPlayer(self)
        self.player.setAudioOutput(self.audio_output)
        self.audio_buffers=QAudioBufferOutput(self)
        self.player.setAudioBufferOutput(self.audio_buffers)
        self.audio_buffers.audioBufferReceived.connect(self._speech_amplitude)
        self.player.playbackStateChanged.connect(self._playback_changed)
        self.player.mediaStatusChanged.connect(self._media_status_changed)
        self.player.errorOccurred.connect(self._playback_error)
        self.signals=Signals()
        self.signals.hotkey.connect(self._hotkey)
        self.hotkey=GlobalHotkey(self.signals.hotkey.emit)
        self.tick=QTimer(self); self.tick.timeout.connect(self._tick); self.tick.start(100)
        self.result_tick=QTimer(self); self.result_tick.timeout.connect(self._read_results); self.result_tick.start(100)
        self.roam_tick=QTimer(self); self.roam_tick.timeout.connect(self._roam); self.roam_tick.start(16)
        self.overlay.avatar.simulationStep.connect(self._render_movement)
        from fullscreen_pause import FullscreenPause
        self.fullscreen_pause=FullscreenPause(self)
        from media_activity import MediaActivity
        from music_runtime import MusicRuntime
        from daily_scenarios import DailyDirector
        self.media_activity=MediaActivity();self.media_activity.start()
        self.music_runtime=MusicRuntime(self);self.daily_director=DailyDirector(self)
        if self.settings.get('name_wake_enabled',False):
            QTimer.singleShot(500,self._start_auto_listen)
        if not env_value('TEST_OUTPUT') and not env_value('DISABLE_LIVE'):
            QTimer.singleShot(900,self._warm_native)

    def _build_ui(self):
        from ui_shell import build_window
        build_window(self)

    def _refresh_icons(self,theme=None):
        from ui_shell import icon
        from themes import PALETTES
        bg,text,*_=PALETTES.get(theme or self.settings.get('theme','ios'),PALETTES['ios'])
        if hasattr(self,'navigation'):self.navigation.recolor(text)
        for key,button in getattr(self,'header_buttons',{}).items():button.setIcon(icon(key,text))
        if hasattr(self,'wave_button'):self.wave_button.setIcon(icon('wave',text))
        if hasattr(self,'new_chat_button'):self.new_chat_button.setIcon(icon('plus',text,17))
        if hasattr(self,'send_button'):self.send_button.setIcon(icon('send',bg))
        if hasattr(self,'mic_button'):self.mic_button.setIcon(icon('stop' if self.mic_button.isChecked() else 'mic',text))

    def _set_microphone_button(self,listening):
        self.mic_button.setText('');self.mic_button.setChecked(listening)
        self._refresh_icons()
        if hasattr(self,'voice_hint'):
            self.voice_hint.setWordWrap(True)
            self.voice_hint.setText('Sohbet mikrofonu açık' if listening else 'Adla çağırma yereldir; beklemede Gemini’ye ses gönderilmez.' if self.settings.get('name_wake_enabled') else 'Sesli sohbet için mikrofona dokun')

    def _route_page(self,key,opener):
        if self.pages.busy:return
        current=self.pages.currentWidget()
        if current is not self.panel:
            self.navigation_pending=(key,opener);current.reject();return
        self.navigation_pending=None;opener();self.navigation.select(key)

    def _nav_chat(self):
        self._route_page('chat',lambda:None)

    def _nav_settings(self,index=0,key='settings'):
        page=getattr(self,'settings_page',None)
        if page is not None and self.pages.currentWidget() is page:
            page.tabs.setCurrentIndex(index);self.navigation.select(key);return
        def open_section():
            self._settings()
            page=getattr(self,'settings_page',None)
            if page is not None:page.tabs.setCurrentIndex(index)
        self._route_page(key,open_section)

    def _activities(self):
        if self.pages.busy or getattr(self,'activity_page',None):return
        from ui_activities import ActivitiesDialog
        self.activity_page=ActivitiesDialog(self);self._push_page(self.activity_page)

    def apply_theme(self):
        from themes import stylesheet
        style=stylesheet(self.settings.get('theme','pearl'),self.settings.get('panel_opacity',94))
        self.setStyleSheet(style);self._refresh_icons()
        if hasattr(self,'overlay'):self.overlay.setStyleSheet(style)

    def _jump_latest(self):
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())

    def _update_jump(self,*args):
        bar=self.scroll.verticalScrollBar();self.jump_button.move(max(0,self.scroll.viewport().width()-144),max(0,self.scroll.viewport().height()-44))
        self.jump_button.setVisible(bar.maximum()-bar.value()>45);self.jump_button.raise_()

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'avatar'):
            QTimer.singleShot(0,self._layout_stage)
        if hasattr(self,'resize_save_timer'):self.resize_save_timer.start(500)

    def _remember_window_size(self):
        if not self.isMaximized() and not self.isMinimized() and not self.isFullScreen():
            self.settings['chat_window_size']=[self.width(),self.height()]
            save_settings(self.settings)

    def _layout_stage(self):
        if hasattr(self,'jump_button'):self._update_jump()
        if hasattr(self,'brand_description'):self.brand_description.setVisible(self.width()>=700)
        if hasattr(self,'chat_messages'):
            compact=self.width()<680
            if compact!=getattr(self,'compact_chat',None):
                self.compact_chat=compact
                if compact:self.chat_toggle.setChecked(False)
            history=self.chat_toggle.isChecked()
            self.chat_sidebar.setVisible(history)
            self.chat_messages.setVisible(not(compact and history))
            self.chat_toggle.setText('Sohbete dön' if compact and history else 'Geçmiş')
            self.navigation.compact(self.pages.height())

    def eventFilter(self,obj,event):
        if isinstance(getattr(self,'scroll',None),QScrollArea) and obj is self.scroll.viewport():
            if event.type()==QEvent.Type.Resize:
                QTimer.singleShot(0,self._layout_messages);QTimer.singleShot(0,self._update_jump)
            return False
        if obj is getattr(self,'stage',None) and event.type()==QEvent.Type.Resize:
            QTimer.singleShot(0,self._layout_stage)
        if event.type()==QEvent.Type.MouseButtonPress and event.button()==Qt.MouseButton.LeftButton:
            self.drag_pos=event.globalPosition().toPoint()-self.pos(); self.last_user_action=time.perf_counter(); return True
        if event.type()==QEvent.Type.MouseMove and self.drag_pos is not None:
            self.move(event.globalPosition().toPoint()-self.drag_pos); return True
        if event.type()==QEvent.Type.MouseButtonRelease:
            self.drag_pos=None; return True
        return super().eventFilter(obj,event)

    def _tray(self):
        icon=QIcon(str(ROOT/'assets/yumi.svg'));self.setWindowIcon(icon)
        self.tray=QSystemTrayIcon(icon,self);self.tray.setToolTip('Yumi')
        menu=QMenu(); menu.addAction('Yumi’yi göster',self._show)
        from model_visibility import add_action
        add_action(menu,self)
        menu.addAction('🏠 Akıllı Ev & Cihazlar',self._open_smart_home); menu.addAction('Konuş (Ctrl+Alt+M)',self._hotkey); menu.addSeparator(); menu.addAction('Çıkış',self.quit)
        self.tray.setContextMenu(menu); self.tray.activated.connect(lambda reason: self._show() if reason==QSystemTrayIcon.ActivationReason.DoubleClick else None)
        self.tray.show()

    def _show(self):
        from model_visibility import visible
        if visible(self) and not getattr(getattr(self,'fullscreen_pause',None),'paused',False):self.overlay.show()
        self.show();self.raise_();self.activateWindow()
    def _login(self):
        self.set_status('Tarayıcıda Codex girişini tamamla…'); self.overlay.say('Tarayıcıda hesabına giriş yap.'); self._work('login',login)
    def _hotkey(self): self._show(); self._mic()
    def _settings(self):
        if self.pages.busy or getattr(self,'settings_page',None):return
        page=SettingsDialog(self);self.settings_page=page
        self._push_page(page)

    def _open_smart_home(self):
        if self.pages.busy or getattr(self,'smart_home_page',None):return
        try:
            from yumi_skills.ui_smart_home_panel import SmartHomeDialog
            page=SmartHomeDialog(self,engine=self.skill_engine)
            self.smart_home_page=page
            self._push_page(page)
        except Exception as e:
            self.show_error(f'Akıllı ev paneli açılamadı: {e}')

    def _on_skill_alert(self,alert_type,alert_data):
        if self.exiting:return
        msg=alert_data.get('message') or alert_type or 'Süreniz doldu!'
        self._on_skill_result('alert',{'ok':True,'speech':msg})
        self.add_message(msg,'assistant');self.show_bubble(msg);self._speak(msg)
        self._save_chat_history()
        self._speak_skill_result(msg)

    def _speak_skill_result(self,text):
        native=getattr(self,'native_audio',None)
        if native and native.active and native.feedback(text):return
        self._skill_feedback_fallback()

    def _skill_feedback_fallback(self):
        if not self.busy:self.set_status('Sonuç ekranda · Seslendirme kullanılamıyor')

    def _on_skill_result(self,name,result):
        if self.exiting:return
        from skill_reactions import reaction
        intent,style=reaction(name,result)
        now=time.perf_counter()
        for view in (self.avatar,self.overlay.avatar):
            if view.model:view.model.skill_reaction=(now,intent)
        self.avatar.conversation.begin(result.get('speech',''));self.avatar.conversation.intent=intent
        scene=self.overlay.avatar.furniture or self.avatar.furniture
        if style and not scene and not self.avatar.hand_gesture and not getattr(getattr(self,'music_runtime',None),'enabled',False):
            self.avatar.hand_gesture=style;self.gesture_until=now+2.2;self.overlay.sync()

    def _start_skill_command(self,text,native=False):
        dispatcher=getattr(self,'skill_dispatcher',None)
        call=dispatcher.parse(text) if dispatcher else None
        if call is None:return False
        if not native:self.busy=True;self.voice_capture.suspended=True
        if not native:self.active_skill_requests=getattr(self,'active_skill_requests',0)+1
        self.set_status('İşlem yürütülüyor…')
        name,args=call
        def run():return text,self.skill_engine.execute_skill(name,args).get('speech','İşlem sonucu alınamadı.')
        self._work('skill_native' if native else 'skill_answer',run)
        return True

    def _push_page(self,page):
        page.finished.connect(lambda *_:self.pages.pop(page))
        return self.pages.setCurrentWidget(page)

    def _page_closed(self,page):
        if page is getattr(self,'settings_page',None):self.settings_page=None
        if page is getattr(self,'motion_dialog',None):self.motion_dialog=None
        if page is getattr(self,'smart_home_page',None):self.smart_home_page=None
        if page is getattr(self,'activity_page',None):self.activity_page=None
        pending=getattr(self,'navigation_pending',None)
        if pending:QTimer.singleShot(0,lambda:self._route_page(*pending))
        elif hasattr(self,'navigation') and self.pages.currentWidget() is self.panel:self.navigation.select('chat')

    def _browser_login(self,provider,finish=False):
        if getattr(self,'browser_login_pending',False):return
        if self.busy:
            self.set_status('Önce mevcut konuşmanın bitmesini bekle.');return
        self.settings['provider']=provider;save_settings(self.settings)
        self.browser_login_pending=True
        self.browser_status_changed.emit('Giriş penceresi kapatılıyor, web sohbeti hazırlanıyor…' if finish else 'Normal tarayıcıda giriş penceresi açılıyor…',True)
        self._work('browser_login',self.assistant.browser_login,finish)
    def _toggle_panel(self):
        showing=self.panel.isVisible(); self.panel.setVisible(not showing); self.resize(self.width(),400 if showing else 690)

    def set_status(self,text):
        self.status.setText(text);self.status.setToolTip(text)
        if hasattr(self,'chat_list'):
            self.chat_list.setEnabled(not self.busy);self.new_chat_button.setEnabled(not self.busy)
            self.delete_chat_button.setEnabled(not self.busy)
            self.chat_list.setToolTip('Sohbet değiştirmek için önce ses oturumunu veya yanıtı durdur.' if self.busy else 'Sohbeti aç')
        if hasattr(self,'send_button'):self.send_button.setEnabled(not self.busy or (not self.reply_pending and (self.speech_active or bool(self.speech_queue))))
        if hasattr(self,'stop_reply_button'):self.stop_reply_button.setVisible(bool(getattr(self,'reply_pending',False)) and self.settings.get('provider') in ('gemini','chatgpt-web','gemini-web'))

    def _cancel_reply(self):
        if not self.reply_pending:return
        self.assistant.cancel_reply();self._clear_speech_queue();self.player.stop();self.speech_active=False;self.speech_failed=True
        self.avatar.speaking=False;self.avatar.mouth_level=0.;self.set_status('Yanıt durduruluyor…')
    def show_bubble(self,text,ms=4500):
        self.bubble.hide()
        self.overlay.say(text,ms)
    def _layout_messages(self):
        width=max(80,min(540,int(self.scroll.viewport().width()*.88)))
        for label in self.message_labels:
            label.ensurePolished()
            label.setFixedWidth(width)
            # Fixed height from the previous layout must not become the next
            # heightForWidth minimum (otherwise every transcript tick adds 2px).
            label.setMinimumHeight(0)
            label.setMaximumHeight(16777215)
            label.setFixedHeight(max(36,label.heightForWidth(width)+2))
        self.message_layout.invalidate()
        self.message_layout.activate()

    def _save_chat_history(self):
        try:
            self.chat_store.update(self.chat_history)
            self._refresh_chat_list()
        except OSError:
            import logging
            logging.exception('Chat history could not be saved')

    def _load_chat_history(self):
        from chat_store import ChatStore
        self.chat_store=ChatStore(DATA_DIR)
        self._show_selected_chat()

    def _refresh_chat_list(self):
        self.chat_list.clear()
        for chat in sorted(self.chat_store.chats,key=lambda c:c['updated_at'],reverse=True):
            item=QListWidgetItem(self.chat_store.title(chat));item.setData(Qt.ItemDataRole.UserRole,chat['id']);item.setToolTip(item.text());self.chat_list.addItem(item)
            if chat['id']==self.chat_store.active:self.chat_list.setCurrentItem(item)

    def _show_selected_chat(self):
        for label in self.message_labels:label.hide();self.message_layout.removeWidget(label);label.deleteLater()
        self.message_labels=[];self.chat_history=[m.copy() for m in self.chat_store.current['messages']]
        self.assistant.history=[m.copy() for m in self.chat_history[-24:] if m.get('complete',True)]
        self.assistant.pending_weather=False;self.assistant.weather_city='';self.assistant.weather_tomorrow=False;self.previous_id=None
        self.assistant.chat_scope=self.chat_store.active;self.assistant.chat_urls=self.chat_store.current.setdefault('web_urls',{})
        if hasattr(self,'input'):self.input.clear()
        for item in self.chat_history:self.add_message(item['text'],item['role'],record=False)
        if not self.chat_history:self.add_message('Merhaba! Bana yazabilir veya mikrofonla konuşabilirsin.','assistant',record=False)
        self._refresh_chat_list()
        if hasattr(self,'native_audio'):self._warm_native(force=True)

    def _new_chat(self):
        if self.busy:return
        self._save_chat_history()
        if hasattr(self,'native_transcripts'):self.native_transcripts.new_session()
        self.chat_store.new();self._show_selected_chat()

    def _chat_context_menu(self,position):
        if self.busy:return
        item=self.chat_list.itemAt(position)
        if item is None:return
        key=item.data(Qt.ItemDataRole.UserRole)
        menu=QMenu(self.chat_list);action=menu.addAction('Sohbeti sil')
        if menu.exec(self.chat_list.viewport().mapToGlobal(position))==action:self._delete_chat(key)

    def _delete_chat(self,key=None):
        if self.busy:return
        item=self.chat_list.currentItem()
        if key is None:key=item.data(Qt.ItemDataRole.UserRole) if item else None
        chat=next((c for c in self.chat_store.chats if c['id']==key),None)
        if chat is None:return
        answer=QMessageBox.question(self,'Sohbeti sil',f'“{self.chat_store.title(chat)}” sohbeti silinsin mi?\nBu bilgisayardaki mesajlar kaldırılacak.',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)
        if answer!=QMessageBox.StandardButton.Yes:return
        if hasattr(self,'native_transcripts'):self.native_transcripts.new_session()
        selected=self.chat_store.active
        try:
            if not self.chat_store.delete(key):return
        except OSError:
            self.show_error('Sohbet silinemedi; geçmiş korundu.');return
        if key==selected:self._show_selected_chat()
        else:self._refresh_chat_list()
        self.set_status('Sohbet bu bilgisayardaki geçmişten silindi')

    def _select_chat_item(self,item):
        if self.busy:return
        key=item.data(Qt.ItemDataRole.UserRole)
        if key==self.chat_store.active:return
        self._save_chat_history()
        if hasattr(self,'native_transcripts'):self.native_transcripts.new_session()
        if self.chat_store.select(key):self._show_selected_chat()

    def _expire_chats(self):
        # Never remove the selected conversation while audio/text is in flight.
        if self.busy:return
        active=self.chat_store.active
        from chat_store import RETENTION
        if self.chat_store.clock()-self.chat_store.current['updated_at']>RETENTION and hasattr(self,'native_transcripts'):self.native_transcripts.new_session()
        if self.chat_store.prune():
            if not any(c['id']==active for c in self.chat_store.chats):
                if self.chat_store.chats:self.chat_store.active=self.chat_store.chats[0]['id']
                else:self.chat_store.new(save=False)
                self._show_selected_chat()
            self.chat_store.save();self._refresh_chat_list()

    def add_message(self,text,role,record=True):
        if record and role in ('user','assistant'):
            self.chat_history.append({'role':role,'text':text})
        label=QLabel(text); label.setWordWrap(True); label.setProperty('role',role)
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        label.setSizePolicy(QSizePolicy.Policy.Fixed,QSizePolicy.Policy.Fixed)
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.message_labels.append(label)
        index=self.message_layout.count()-1
        self.message_layout.insertWidget(index,label,0,Qt.AlignmentFlag.AlignLeft if role!='user' else Qt.AlignmentFlag.AlignRight)
        def refresh():
            self._layout_messages()
            QTimer.singleShot(0,lambda:self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum()))
        QTimer.singleShot(0,refresh)
        return label
    def show_error(self,text): self.add_message(text,'error'); self.show_bubble(text,9000); self.set_status('Hata')

    def _work(self,kind,function,*args):
        executor=self.chat_executor if kind in ('answer','stream_answer','transcribe') else self.executor
        future=executor.submit(function,*args)
        future.add_done_callback(lambda result:self.results.put((kind,result)))

    def _send(self):
        text=self.input.text().strip()
        if not text:return
        if self.busy:
            if self.reply_pending or not (self.speech_active or self.speech_queue):return
            self._clear_speech_queue();self.player.stop();self.speech_active=False;self.busy=False
            self.avatar.speaking=False;self.avatar.mouth_level=0.
        self.input.clear(); self.add_message(text,'user'); self._save_chat_history(); self._ask(text)
    def _local_command(self,text):
        command=text.lower().strip(' !?.')
        if command in ('akıllı ev','akıllı evi aç','akıllı ev menüsü','akıllı ev menüsünü aç','akıllı ev panelini aç','cihazları göster','akıllı cihazlar','odaları göster'):
            self._open_smart_home();return 'Akıllı ev ve cihazlar panelini açıyorum.'
        if getattr(self,'skill_dispatcher',None):
            skill_res=self.skill_dispatcher.dispatch(text)
            if skill_res:return skill_res
        from voice_actions import execute
        action=execute(self,command)
        if action is not None:return action
        if command in ('dans et','hadi dans et'):
            path=Path(__file__).resolve().parent/'motions/quaternius-Dance_Loop.vrma'
            if not path.exists():return 'Dans animasyonu bulunamadı.'
            try:self._play_motion(path)
            except (ValueError,OSError) as error:return str(error)
            return 'Dans ediyorum.'
        if command in ('dansı durdur','dans etmeyi bırak','hareketi durdur'):
            self.manual_pose='idle';self.manual_pose_end=time.perf_counter()+3
            return 'Hareketi durdurdum.'
        if command in ('uyu','yatağa git','yat uyu','bilgisayara otur','çalışmaya başla','oyun oyna'):
            return 'Bu davranış şu anda kullanıma açık değil.'
        if command in ('el salla','merhaba de'):
            self._wave();return 'Merhaba!'
        if command in ('büyü','küçül','biraz büyü','biraz küçül'):
            self.settings['size']=max(50,min(180,self.settings['size']+(20 if 'büyü' in command else -20)))
            self.overlay.set_scale(self.settings['size']);save_settings(self.settings);return 'Boyutumu değiştirdim.'
        if command in ('gizlen','saklan'):
            self.overlay.hide();self.hide();return 'Tekrar çağırana kadar gizleniyorum.'
        if command in ('görün','geri gel'):
            from model_visibility import set_visible
            set_visible(self,True);return 'Buradayım!'
        return None


    def _ask(self,text):
        if self.busy: return
        if hasattr(self,'name_wake'):self.name_wake.pause()
        self.speech_failed=False
        self.assistant.begin_reply()
        if self._start_skill_command(text):return
        local=self._local_command(text)
        if local:
            self.busy=True;self.voice_capture.suspended=True;self.add_message(local,'assistant');self.show_bubble(local)
            self.assistant._remember(text,local)
            self._save_chat_history()
            self._speak(local)
            return
        self.busy=True; self.reply_pending=True; self.voice_capture.suspended=True; self.set_status('Düşünüyor…')
        self.streaming_label = self.add_message('…', 'assistant',record=False)
        self.streaming_text = ''
        self.streaming_speech_offset = 0
        def on_chunk(chunk):
            self.results.put(('stream_chunk', chunk))
        def on_status(status):
            self.results.put(('connection_state',status))
        def runner():
            key = self.gemini_key if self.settings['provider']=='gemini' else self.api_key
            return self.assistant.stream_ask(text, key, self.previous_id, on_chunk=on_chunk,on_status=on_status)
        self._work('stream_answer', runner)
    def _speak(self,text,voice=None,openai_voice=None):
        if not text.strip():return
        self.speech_failed=True
        self._finish_turn()

    def _start_next_speech(self):
        if self.speech_active:return
        if not self.speech_queue:
            self._finish_turn();return
        text,selected,openai_voice,prepared=self.speech_queue.popleft()
        self.speech_active=True
        self.active_speech_voice=selected
        self.active_speech_text=text
        if selected=='browser-voice':
            def play_browser():
                if not self.assistant.web:raise RuntimeError('Web sohbeti açık değil.')
                self.assistant.web.read_aloud(lambda:self.results.put(('browser_voice_started',text)))
            self._work('browser_voice',play_browser);return
        label=next((title for title,key,_ in VOICES if key==selected),selected)
        self.set_status(f'Ses hazırlanıyor · {label}…')
        epoch=self.speech_epoch
        prepared.add_done_callback(lambda result:self.results.put(('speech_ready',(result,epoch))))

    def _clear_speech_queue(self):
        self.speech_epoch+=1
        for _,_,_,prepared in self.speech_queue:
            if prepared is not None:prepared.cancel()
        self.speech_queue.clear()

    def _queue_stream_speech(self,final=False):
        if getattr(self,'speech_failed',False):return
        if self.settings['speech_voice']=='browser-voice':
            if final and self.streaming_text.strip():self._speak(self.streaming_text)
            return
        import re
        remaining=self.streaming_text[self.streaming_speech_offset:]
        end=len(remaining) if final else 0
        if not final:
            for match in re.finditer(r'(?<!\d)[.!?](?:\s+)',remaining):end=match.end()
        if end:
            text=remaining[:end].strip()
            self.streaming_speech_offset+=end
            if text:self._speak(text)

    def _finish_turn(self):
        if getattr(self,'active_skill_requests',0):return
        if self.reply_pending or self.speech_active or self.speech_queue:return
        if getattr(self,'site_voice_fallback',False):
            self.site_voice_fallback=False
            text=getattr(self,'streaming_text','').strip()
            if text:
                self.set_status('Microsoft sesi kullanılamıyor; sitenin sesiyle okunuyor…')
                self._speak(text,voice='browser-voice');return
        self.busy=False;self.voice_capture.suspended=False
        self.set_status(f'“{character_name(self.settings)}” diye seslen' if self.voice_capture.always else 'Hazır')
        if hasattr(self,'name_wake'):self._sync_name_wake()

    def _media_status_changed(self,status):
        if status==QMediaPlayer.MediaStatus.EndOfMedia:
            self.speech_active=False
            self._start_next_speech()

    def _playback_error(self,*args):
        self.speech_active=False;self._clear_speech_queue()
        self.speech_failed=True
        self.show_error('Ses dosyası oynatılamadı: '+self.player.errorString())
        self._finish_turn()

    def _audio_complete(self,samples,requires_wake):
        return  # Native input is owned by the isolated live prototype.
    def _retry_browser(self):
        if self.busy or self.exiting or getattr(self,'browser_retry_pending',False):return
        self.browser_retry_pending=True;self.web_retry_button.setEnabled(False)
        self.web_recovery_text.setText('Web bağlantısı kontrol ediliyor…');self.web_recovery.show()
        self._work('browser_warm',self.assistant.warm_browser)
    def _read_results(self):
        while True:
            try: kind,item=self.results.get_nowait()
            except queue.Empty: break
            if kind=='speech_ready':
                item,epoch=item
                if epoch!=self.speech_epoch:continue
                kind='speech'
            if kind=='connection_state':
                if self.reply_pending:self.set_status(item)
                continue
            if kind=='stream_chunk':
                chunk=item
                if getattr(self,'streaming_label',None):
                    self.streaming_text=(self.streaming_text or '')+chunk
                    self.streaming_label.setText(self.streaming_text)
                    self._layout_messages()
                    self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())
                    self._queue_stream_speech()
                continue
            if kind=='browser_voice_started':
                self.avatar.conversation.begin(item);self.browser_voice_start=time.perf_counter();self.avatar.speaking=True
                self.set_status('Site sesiyle konuşuyor…');continue
            future=item
            try: value=future.result()
            except Exception as error:
                if kind=='skill_answer':self.active_skill_requests=max(0,getattr(self,'active_skill_requests',0)-1)
                if kind=='browser_login':
                    self.browser_login_pending=False;self.browser_status_changed.emit(str(error),False);self.show_error(str(error));continue
                if kind=='browser_warm':
                    self.browser_retry_pending=False;self.web_retry_button.setEnabled(True)
                    self.web_recovery_text.setText('Web bağlantısı hazırlanamadı. Yeniden bağlanabilir veya site girişini kontrol edebilirsin.')
                    self.web_recovery.show()
                    if not self.busy:self.set_status('Web bağlantısı hazır değil · Sohbetin korunuyor')
                    continue
                if kind in ('answer','stream_answer') and is_offline_error(error):
                    value=(OFFLINE_MESSAGE,self.previous_id)
                else:
                    if kind in ('answer','stream_answer'):
                        self.reply_pending=False
                        if getattr(error,'retry_text',None) and not self.input.text():
                            self.input.setText(error.retry_text)
                        if getattr(self,'streaming_label',None):
                            partial=getattr(self,'streaming_text','').strip()
                            if partial:self.streaming_label.setText(partial)
                            else:
                                self.streaming_label.hide();self.message_layout.removeWidget(self.streaming_label)
                                if self.streaming_label in self.message_labels:self.message_labels.remove(self.streaming_label)
                                self.streaming_label.deleteLater()
                            self._layout_messages()
                            if partial:
                                self.chat_history.append({'role':'assistant','text':partial,'complete':False})
                                self._save_chat_history()
                        self.streaming_label=None
                    elif kind in ('speech','browser_voice'):
                        self.avatar.speaking=False;self.avatar.mouth_level=0.;self.browser_voice_start=None
                        self.speech_active=False;self._clear_speech_queue()
                        self.streaming_speech_offset=len(getattr(self,'streaming_text',''))
                        self.speech_failed=True
                    else:self.busy=False;self.voice_capture.suspended=False
                    if kind=='speech' and '403' in str(error) and self.settings.get('provider') in ('chatgpt-web','gemini-web'):
                        self.site_voice_fallback=True
                        self.set_status('Microsoft sesi reddetti; yanıt sitenin sesiyle okunacak.')
                    else:self.show_error(str(error))
                    if getattr(error,'retry_text',None):self.web_recovery.show()
                    self._finish_turn();continue
            if kind in ('skill_answer','skill_native'):
                if kind=='skill_answer':self.active_skill_requests=max(0,getattr(self,'active_skill_requests',0)-1)
                text,message=value
                self.add_message(message,'assistant');self.show_bubble(message)
                self.assistant._remember(text,message);self._save_chat_history()
                if kind=='skill_answer':self._speak(message)
                self._speak_skill_result(message)
                continue
            if kind=='login':
                self.add_message(value,'assistant'); self.show_bubble(value); self.set_status('Giriş durumu güncellendi')
            elif kind=='transcribe':
                self.busy=False
                text=value.strip()
                recognized=False
                if self._requires_wake:recognized,text=wake_command(text,character_name(self.settings))
                if text:self.add_message(text,'user');self._save_chat_history();self._ask(text)
                elif self._requires_wake and recognized:
                    self.voice_capture.arm_next_utterance();self.manual_pose='listen';self.manual_pose_end=time.perf_counter()+10
                else:self.voice_capture.suspended=False;self.set_status(f'“{character_name(self.settings)}” diye seslen' if self.voice_capture.always else 'Hazır')
            elif kind in ('answer','stream_answer'):
                self.reply_pending=False
                message,self.previous_id=value
                if getattr(self,'streaming_label',None):
                    self.streaming_label.setText(message)
                    self._layout_messages()
                    self.chat_history.append({'role':'assistant','text':message})
                else:
                    self.add_message(message,'assistant')
                self.show_bubble(message)
                self._save_chat_history()
                self.streaming_text=message
                if not getattr(self,'speech_failed',False):self._queue_stream_speech(final=True)
                self.streaming_label=None
                if hasattr(self,'native_audio') and not self.native_audio.listening:self._warm_native(force=True)
                self._finish_turn()
            elif kind=='browser_warm':
                self.browser_retry_pending=False;self.web_retry_button.setEnabled(True)
                if value is False:
                    self.web_recovery_text.setText('Web sohbeti hazır değil. Yeniden bağlan veya site girişini kontrol et.');self.web_recovery.show()
                    if not self.busy:self.set_status('Web bağlantısı hazır değil · Sohbetin korunuyor')
                else:
                    self.web_recovery.hide()
                    if not self.busy:self.set_status('Web sohbeti hazır')
            elif kind=='browser_login':
                self.web_recovery.hide()
                self.browser_login_pending=False;self.browser_status_changed.emit(value or 'Web bağlantısı güncellendi.',False)
                self.set_status(value or 'Giriş penceresini kapatıp Giriş tamamlandı düğmesine bas.')
            elif kind=='browser_voice':
                self.avatar.speaking=False;self.avatar.mouth_level=0.;self.browser_voice_start=None
                self.speech_active=False;self._start_next_speech()
            elif kind=='speech':
                if getattr(self,'speech_failed',False):continue
                soundfile=DATA_DIR/(f'response-{time.monotonic_ns()}'+('.wav' if value[:4]==b'RIFF' else '.mp3'))
                soundfile.write_bytes(value)
                self.player.setSource(QUrl.fromLocalFile(str(soundfile)))
                for old_audio in sorted(DATA_DIR.glob('response-*.*'),key=lambda p:p.stat().st_mtime,reverse=True)[3:]:
                    if old_audio.suffix in ('.wav','.mp3'):
                        try:old_audio.unlink()
                        except OSError:pass
                self.avatar.conversation.begin(getattr(self,'active_speech_text',''),getattr(value,'boundaries',()))
                self.player.play(); self.avatar.speaking=True
                label=next((title for title,key,_ in VOICES if key==getattr(self,'active_speech_voice',None)),'Seçili ses')
                self.set_status(f'Konuşuyor · {label}')

    def _speech_amplitude(self,buffer):
        if not buffer.isValid():
            self.avatar.mouth_level=0.;return
        formats={QAudioFormat.SampleFormat.Int16:(np.int16,32768.),QAudioFormat.SampleFormat.Int32:(np.int32,2147483648.),QAudioFormat.SampleFormat.Float:(np.float32,1.),QAudioFormat.SampleFormat.UInt8:(np.uint8,128.)}
        spec=formats.get(buffer.format().sampleFormat())
        if not spec:return
        samples=np.frombuffer(buffer.data(),dtype=spec[0]).astype(np.float32)
        if spec[0]==np.uint8:samples-=128.
        if samples.size:
            rms=float(np.sqrt(np.mean((samples/spec[1])**2)))
            self.avatar.mouth_level=float(np.clip((rms-.008)*5.5,0.,.85))

    def _playback_changed(self,state):
        if state==QMediaPlayer.PlaybackState.StoppedState:
            self.avatar.speaking=False; self.avatar.mouth_level=0.
    def _ensure_native(self):
        from native_live import NativeLive
        if not hasattr(self,'native_audio'):
            self.native_audio=NativeLive(self)
            self.native_audio.feedbackFailed.connect(self._skill_feedback_fallback)
            self.native_audio.stateChanged.connect(self._native_state)
            self.native_audio.playbackChanged.connect(self._native_playback)
            self.native_audio.transcriptChanged.connect(self._native_expression)
            self.native_audio.failed.connect(self._native_failed)
            self.native_audio.finished.connect(self._native_finished)
            self.native_audio.conversationPaused.connect(self._native_paused)
            from native_transcripts import NativeTranscriptView
            self.native_transcripts=NativeTranscriptView(self)
            self.native_audio.transcriptChanged.connect(self.native_transcripts.changed)
            self.native_audio.transcriptEnded.connect(self.native_transcripts.ended_turn)

    def _warm_native(self,force=False):
        if self.exiting or not self.gemini_key:return
        self._ensure_native()
        configuration=(self.settings.get('speech_voice','gemini-live:Kore'),character_name(self.settings),self.settings.get('mic_device','Otomatik'))
        if self.native_audio.active:
            if not force and (configuration==getattr(self,'native_configuration',None) or self.native_audio.listening):return
            self.native_audio.shutdown()
        selected=self.settings.get('speech_voice','gemini-live:Kore')
        if selected.startswith('gemini-live:'):
            try:
                self.native_audio.start(selected.split(':',1)[1],character_name(self.settings),history=self.chat_history,standby=True,microphone=self.settings.get('mic_device','Otomatik'))
                self.native_configuration=configuration
            except Exception as error:self._native_failed(str(error))

    def _mic(self):
        self._ensure_native()
        if self.native_audio.listening or self.native_audio.pending_activation or getattr(self,'native_conversation_active',False):
            self.native_audio.deactivate();return
        if self.busy:
            self._set_microphone_button(False)
            self.show_bubble('Önce mevcut yanıtı tamamla veya durdur.');return
        self._warm_native()
        selected=self.settings.get('speech_voice','gemini-live:Kore')
        if not selected.startswith('gemini-live:'):
            self._set_microphone_button(False)
            self.show_error('Bu aşamada yalnız Gemini Live sesi kullanılabilir. OpenAI canlı ses erişimi henüz yok.');return
        if hasattr(self,'name_wake'):self.name_wake.pause()
        self.avatar.conversation.begin('');self.native_expression_turn=None;self.native_expression_text='';self.native_speaking=False
        self.native_error=None;self.native_conversation_active=True;self.busy=True;self.voice_capture.suspended=True
        if hasattr(self,'native_transcripts'):self.native_transcripts.new_session()
        self._set_microphone_button(True);self.mic_button.setToolTip('Gemini canlı sesi durdur')
        try:
            if not self.native_audio.active:self.native_audio.start(selected.split(':',1)[1],character_name(self.settings),history=self.chat_history,standby=True,microphone=self.settings.get('mic_device','Otomatik'))
            if not self.native_audio.activate():raise RuntimeError('Ses oturumu etkinleştirilemedi.')
        except Exception as error:
            self._native_failed(str(error));self._native_finished()

    def _native_command(self,text):
        from avatar_commands import command_text
        command=command_text(text,character_name(self.settings),'')
        if command:
            if self._start_skill_command(command,native=True):return
            result=self._local_command(command)
            if result:self.show_bubble(result)
        else:self._start_skill_command(text,native=True)

    def _native_expression(self,role,turn,text,mode):
        if role!='assistant':return
        if getattr(self,'native_expression_turn',None)!=turn:
            self.native_expression_turn=turn;self.native_expression_text=''
            self.avatar.conversation.begin('')
        old=self.native_expression_text
        self.native_expression_text=(text if mode=='snapshot' else old+text)[:16000]
        from conversation_motion import classify
        self.avatar.conversation.text=self.native_expression_text
        self.avatar.conversation.intent=classify(self.native_expression_text)

    def _native_playback(self,audible,level):
        now=time.perf_counter()
        if audible:
            if not getattr(self,'native_speaking',False):self.native_voice_start=now-self.avatar.conversation.position
            self.native_last_audible=now;self.native_speaking=True;self.avatar.speaking=True
            self.avatar.mouth_level=min(.85,max(0.,(level-.004)*5.5))
        else:
            self.avatar.mouth_level=0.
            if now-getattr(self,'native_last_audible',0.)>.18:self.native_speaking=False;self.avatar.speaking=False
        self.overlay.sync()

    def _native_state(self,text):
        self.set_status(text)
        if text.startswith(('Gemini bağlantısı hazır','Gemini bağlı','Dinliyor · Gemini Live','Seni dinliyor')):
            self.native_error=None;self.native_recovery.hide()
            self.native_reconnect_button.setEnabled(True)
        if text.startswith('Seni dinliyor') or text.startswith('Canlı ses durduruluyor'):
            self.native_speaking=False;self.avatar.speaking=False;self.avatar.mouth_level=0.
            self.avatar.conversation.position=0.
            self.overlay.sync()

    def _native_failed(self,text):
        self.native_error=text
        self.native_recovery_text.setText(text);self.native_recovery.show()
        self.native_reconnect_button.setEnabled(True)
        self.set_status('Ses bağlantısı kapalı · Yazılı sohbet kullanılabilir')
        if getattr(self,'native_conversation_active',False):self.show_error(text)

    def _reconnect_native(self):
        if self.busy or self.exiting:return
        if not self.gemini_key:
            self.native_recovery_text.setText('Canlı ses için Ayarlar → Asistan bölümündeki Gemini Live bağlantısını yapılandır. Hesapla yazılı sohbeti kullanmaya devam edebilirsin.')
            return
        if not self.settings.get('speech_voice','').startswith('gemini-live:'):
            self.native_recovery_text.setText('Ayarlar → Ses bölümünden bir Gemini Live sesi seç.')
            return
        self.native_reconnect_button.setEnabled(False)
        self.native_recovery_text.setText('Ses bağlantısı kuruluyor… Mikrofon beklemede kalacak.')
        self._warm_native(force=True)

    def _native_paused(self):
        self.native_speaking=False;self.avatar.speaking=False;self.avatar.mouth_level=0.
        if hasattr(self,'native_transcripts'):self.native_transcripts.finish_session()
        self.native_conversation_active=False;self.busy=False;self.voice_capture.suspended=False
        self._set_microphone_button(False);self.mic_button.setToolTip('Hazır bağlantıyla sesli sohbeti başlat')
        self._sync_name_wake()
        self._warm_native()

    def _native_finished(self):
        if not getattr(self,'native_conversation_active',False):
            if getattr(self,'voice_restart',False):
                self.voice_restart=False;QTimer.singleShot(200,self._warm_native)
            return
        self.native_conversation_active=False
        self.native_speaking=False;self.avatar.speaking=False;self.avatar.mouth_level=0.;self.avatar.conversation.position=0.
        if hasattr(self,'native_transcripts'):self.native_transcripts.finish_session()
        self.busy=False;self.voice_capture.suspended=False
        self._set_microphone_button(False);self.mic_button.setToolTip('Gemini canlı ses başlat / durdur')
        self.set_status(getattr(self,'native_error',None) or 'Ses bağlantısı kapalı · Mikrofonla yeniden dene')
        if getattr(self,'voice_restart',False):
            self.voice_restart=False;QTimer.singleShot(200,self._mic)
        elif hasattr(self,'name_wake'):self._sync_name_wake()
    def _start_auto_listen(self):
        self._sync_name_wake()
    def _sync_name_wake(self):
        if self.exiting:return
        try:self.name_wake.configure(bool(self.settings.get('name_wake_enabled',False)),character_name(self.settings),paused=self.busy or bool(getattr(getattr(self,'native_audio',None),'listening',False)) or bool(getattr(getattr(self,'native_audio',None),'pending_activation',False)),wake_name='',microphone=self.settings.get('mic_device','Otomatik'))
        except Exception:self._wake_failed('Yerel çağrı adı dinlemesi açılamadı; mikrofon düğmesini kullanabilirsin.')
    def _wake_ready(self,name):
        if not self.busy:self.set_status(f'“{name}” diye seslen · Yalnız bu bilgisayarda')
    def _wake_called(self):
        if not self.settings.get('name_wake_enabled',False):return
        if not self.busy:self._mic()
        else:self._sync_name_wake()
    def _wake_failed(self,message):
        # A transient microphone failure must not erase the user's preference.
        # Background retry failures belong in service status, not chat history.
        self.set_status(message)
    def _motion_library(self):
        if self.pages.busy or getattr(self,'motion_dialog',None):return
        from motion_ui import MotionDialog
        self.motion_dialog=MotionDialog(self);self._push_page(self.motion_dialog)

    def _play_motion(self,path):
        from vrma import MotionClip
        clip=MotionClip(path)
        for view in (self.avatar,self.overlay.avatar):
            if not view.model:raise ValueError('Önce bir VRM karakter seç.')
            view.model.clip=clip;view.model.clip_start=time.perf_counter()-view.clock
        self.manual_pose='clip';self.manual_pose_end=time.perf_counter()+clip.duration+.1
        self.show_bubble('Animasyon: '+Path(path).stem)
    def _wave(self): self.last_user_action=time.perf_counter(); self.manual_pose='wave'; self.manual_pose_end=time.perf_counter()+7.7; self.show_bubble('Merhaba! 👋')


    def _tick(self):
        if getattr(getattr(self,'fullscreen_pause',None),'paused',False):return
        now=time.perf_counter()
        if getattr(self,'native_speaking',False):
            self.avatar.conversation.position=now-self.native_voice_start
            self.avatar.conversation.duration=0.
            if now-getattr(self,'native_last_audible',0.)>.3:self.native_speaking=False;self.avatar.speaking=False;self.avatar.mouth_level=0.
        elif getattr(self,'browser_voice_start',None):
            self.avatar.conversation.position=now-self.browser_voice_start
            self.avatar.conversation.duration=0.
            self.avatar.mouth_level=min(.85,max(0.,self.system_audio.sample())*4)
        else:
            self.avatar.conversation.position=self.player.position()/1000.
            self.avatar.conversation.duration=self.player.duration()/1000.
        if self.settings.get('skin')=='Clippy':
            if not getattr(self,'clippy_actions_stopped',False):
                self.music_runtime.stop(suppress=False)
                self.music_runtime.enabled=False;self.music_runtime._rest()
                self.daily_director.cancel()
                self.pending_avatar_command=None;self.voice_target=None;self.manual_pose=None
                self.clippy_actions_stopped=True
            self.move_animation.stop()
            self.avatar.pose='idle';self.avatar.prop='none';self.avatar.hand_gesture=None
            self.avatar.clippy_state=('thinking' if self.busy else 'listening' if getattr(getattr(self,'native_audio',None),'listening',False) else 'idle')
            self.overlay.sync()
            return
        self.clippy_actions_stopped=False
        from voice_actions import music
        if now>=getattr(self,'gesture_until',0.):self.avatar.hand_gesture=None
        music(self,now)
        self.daily_director.tick(now)
        if self.manual_pose and now>self.manual_pose_end:self.manual_pose=None
        performing=self.music_runtime.active
        pose='clip' if performing else 'idle' if self.avatar.speaking else self.manual_pose or 'idle'
        if pose not in ('idle','walk','wave','listen','clip'):pose='idle'
        if pose!='walk':self.move_animation.stop()
        self.avatar.pose=pose;self.avatar.prop='none'
        self.overlay.sync()






    def _render_movement(self,dt):
        self.last_render_movement=time.perf_counter();self.in_render_movement=True
        try:
            self._roam();self._tick()
            x=getattr(self,'roam_x',float(self.overlay.x()))-self.overlay.x()
            self.overlay.avatar.subpixel_x=x if abs(x)<=1.5 else 0.
        finally:self.in_render_movement=False

    def _roam(self):
        if self.settings.get('skin')=='Clippy':return
        if getattr(getattr(self,'fullscreen_pause',None),'paused',False):return
        from action_transition import dispatch
        if dispatch(self):return
        if getattr(self.overlay.avatar,'furniture',None):return
        if not getattr(self,'in_render_movement',False) and time.perf_counter()-getattr(self,'last_render_movement',0)<.05:return
        now=time.perf_counter();previous=getattr(self,'roam_clock',now);self.roam_clock=now
        dt=max(0.,min(.05,now-previous))
        self.overlay.contain()
        from voice_actions import travel
        if travel(self,dt):return
        if getattr(getattr(self,'music_runtime',None),'enabled',False):return
        self.avatar.walking_turn=False
        if not self.settings['roam'] or self.overlay.manually_placed or self.overlay.drag is not None or now-self.last_user_action<20 or self.busy or self.avatar.speaking or not self.overlay.isVisible():
            from locomotion import halt
            halt(self)
            return
        if self.manual_pose not in (None,'walk','idle') or self.avatar.pose not in ('idle','walk'):return
        left,right=self.overlay.walk_limits()
        if right-left<2:return
        direction=getattr(self,'walk_direction',-1)
        x=max(left,min(right,getattr(self,'roam_x',float(self.overlay.x()))))
        if abs(x-self.overlay.x())>1.5:x=float(self.overlay.x())
        if (direction<0 and x<=left+.5) or (direction>0 and x>=right-.5):direction=-direction
        self.walk_direction=direction;self.avatar.walk_direction=direction
        target=90*direction
        self.avatar.walking_turn=True;self.overlay.sync()
        # Turn on planted feet before travelling in the new direction.
        turning=abs(self.overlay.avatar.yaw.angle-target)>5
        self.manual_pose='idle' if turning else 'walk';self.manual_pose_end=now+.25
        if turning:
            from locomotion import halt
            halt(self)
        if not turning:
            from locomotion import stride_step
            x=max(left,min(right,x+stride_step(self,direction,dt)))
            self.overlay.move(round(x),self.overlay.y())
        self.roam_x=x

    def closeEvent(self,event):
        if self.exiting: event.accept()
        else: event.ignore(); self.hide()
    def quit(self):
        self.exiting=True
        if any(worker.isRunning() for worker in getattr(QApplication.instance(),'_yumi_skill_workers',[])):
            QTimer.singleShot(100,self.quit);return
        if getattr(self,'skill_engine',None):
            self.skill_engine.time.stop_worker()
            self.skill_engine.smart_home.close()
        if hasattr(self,'music_runtime'):self.music_runtime.stop()
        if hasattr(self,'media_activity'):self.media_activity.stop()
        if hasattr(self,'fullscreen_pause'):self.fullscreen_pause.shutdown()
        if hasattr(self,'name_wake'):self.name_wake.shutdown()
        if hasattr(self,'native_audio'):self.native_audio.shutdown()
        self.exiting=True
        self.assistant.close()
        if getattr(self.overlay.avatar,'three_desktop',None):self.overlay.avatar.three_desktop.dispose()
        self.overlay.close()
        self.hotkey.close(); self.voice_capture.close(); self.player.stop(); self.tray.hide()
        self.chat_executor.shutdown(wait=False,cancel_futures=True)
        self.executor.shutdown(wait=False,cancel_futures=True)
        QApplication.quit()


def main():
    from PySide6.QtNetwork import QLocalServer, QLocalSocket
    app=QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    client=QLocalSocket()
    client.connectToServer(APP_ID)
    if client.waitForConnected(400):
        client.write(b'show\n')
        client.waitForBytesWritten(400)
        client.disconnectFromServer()
        return 0

    server=QLocalServer()
    server.removeServer(APP_ID)
    window=YumiWindow()
    screen=app.primaryScreen().availableGeometry()
    window.move(screen.right()-window.width()-20,screen.bottom()-window.height()-10)
    window._show()
    from startup_runtime import mark_startup_ready
    QTimer.singleShot(0,mark_startup_ready)

    def on_new_connection():
        conn=server.nextPendingConnection()
        if conn:
            conn.waitForReadyRead(200)
            window._show()
            conn.disconnectFromServer()
    server.newConnection.connect(on_new_connection)
    server.listen(APP_ID)

    if env_value('TEST_OUTPUT'):
        def finish_test():
            Path(env_value('TEST_OUTPUT')).parent.mkdir(parents=True,exist_ok=True)
            window.overlay.grab().save(env_value('TEST_OUTPUT'))
            window.quit()
        QTimer.singleShot(2500,finish_test)
    return app.exec()


if __name__=='__main__':
    sys.exit(main())
