"""VRM import with a real rendered preview and explicit name/voice profile."""
from pathlib import Path
from PySide6.QtCore import QObject,Qt,QTimer,Signal
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QComboBox,QPushButton,QCheckBox,QScrollArea,QWidget,QFrame
from three_vrm_view import ThreeVRMView
from skins import add_model,existing_model_key
from voice_profiles import VOICES,OPENAI_VOICES,profile

class ModelSetup(QDialog):
 compatibilityReady=Signal(dict)
 compatibilityFailed=Signal(str)
 def __init__(self,owner,path):
  super().__init__(owner);self.owner=owner;self.path=path;self.setWindowTitle('Yeni karakter');self.setWindowFlags(Qt.WindowType.Widget);self.setModal(False)
  outer=QVBoxLayout(self);outer.setContentsMargins(0,0,0,0)
  scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QFrame.Shape.NoFrame);scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
  content=QWidget();scroll.setWidget(content);outer.addWidget(scroll);layout=QVBoxLayout(content)
  heading=QLabel('Karakterini tanıyalım');heading.setStyleSheet('font-size:20px;font-weight:600');layout.addWidget(heading)
  self.preview=ThreeVRMView(self,path);self.preview.setMinimumHeight(170);self.preview.setMaximumHeight(260);layout.addWidget(self.preview,1)
  self.compatibility=None;self.compatibility_error=None;self.disposed=False
  self.compatibility_label=QLabel('İskelet, parmak ve fizik uyumluluğu inceleniyor…');self.compatibility_label.setWordWrap(True);layout.addWidget(self.compatibility_label)
  self.compatibilityReady.connect(self._compatibility_ready);self.compatibilityFailed.connect(self._compatibility_failed)
  import threading
  threading.Thread(target=self._analyze_model,daemon=True,name='YumiModelCompatibility').start()
  layout.addWidget(QLabel('Karakter adı · bu isimle seslenince dinler'))
  self.name=QLineEdit('');self.name.setPlaceholderText('Örneğin Clara');self.name.setMaxLength(30);layout.addWidget(self.name)
  self.gender=QComboBox()
  for title,key in [('Kadın sesi','female'),('Erkek sesi','male'),('Tüm sesler','any')]:self.gender.addItem(title,key)
  layout.addWidget(self.gender);self.engine=QComboBox();layout.addWidget(self.engine);self.voice=QComboBox();self.voice.addItems(OPENAI_VOICES);layout.addWidget(self.voice)
  self.gender.currentIndexChanged.connect(self.fill_voices);self.engine.currentIndexChanged.connect(lambda _:self.voice.setVisible(self.engine.currentData()=='openai-tts'));self.fill_voices()
  self.adult=QCheckBox('Bu karakterin 18 yaşından büyük olduğunu doğruluyorum');layout.addWidget(self.adult)
  self.test_button=test=QPushButton('Sesi dinle');test.clicked.connect(self.test_voice);layout.addWidget(test)
  self.error=QLabel();self.error.setWordWrap(True);layout.addWidget(self.error)
  from voice_preview import VoicePreview
  self.voice_preview=VoicePreview(self,owner,test,self.error)
  self.engine.currentIndexChanged.connect(lambda *_:self.voice_preview.cancel())
  self.voice.currentTextChanged.connect(lambda *_:self.voice_preview.cancel())
  row=QHBoxLayout();cancel=QPushButton('Vazgeç');cancel.clicked.connect(self.reject);row.addWidget(cancel);save=QPushButton('Karakteri ekle');save.clicked.connect(self.accept);row.addWidget(save);layout.addLayout(row)
  key=existing_model_key(path)
  self.saved_profile=profile(owner.settings,key) if key and key in owner.settings.get('voice_profiles',{}) else {}
  if self.saved_profile:
   saved=self.saved_profile;self.name.setText(saved['name']);self.gender.setCurrentIndex(max(0,self.gender.findData(saved['gender'])))
   self.engine.setCurrentIndex(max(0,self.engine.findData(saved['speech_voice'])));self.voice.setCurrentText(saved.get('voice','marin'));self.adult.setChecked(bool(saved.get('adult',False)))
   self.error.setText('Bu modelin kayıtlı tercihleri yüklendi; değiştirmeden ekleyebilirsin.')
 def fill_voices(self,*args):
  self.engine.clear()
  for title,key,gender in VOICES:
   if self.gender.currentData()=='any' or gender in ('any',self.gender.currentData()):self.engine.addItem(title,key)
  self.voice.setVisible(self.engine.currentData()=='openai-tts')
 def _analyze_model(self):
  try:
   from vrm import load_data
   from model_compatibility import profile
   result=profile(load_data(str(Path(self.path).resolve())))
   if not self.disposed:self.compatibilityReady.emit(result)
  except Exception:
   if not self.disposed:self.compatibilityFailed.emit('Modelin iskeleti okunamadı; karakter eklenmedi.')
 def _compatibility_ready(self,report):
  from model_compatibility import summary
  self.compatibility=report;self.compatibility_label.setText(summary(report))
 def _compatibility_failed(self,message):
  self.compatibility_error=message;self.compatibility_label.setText(message)
 def test_voice(self):
  self.voice_preview.start(self.engine.currentData(),self.voice.currentText())
 def accept(self):
  name=self.name.text().strip()
  if not name or not any(c.isalpha() for c in name):self.error.setText('Seslenebilmek için bir karakter adı yaz.');return
  if self.compatibility_error:self.error.setText(self.compatibility_error);return
  if self.compatibility is None:self.error.setText('İskelet uyumluluğu incelemesinin bitmesini bekle.');return
  if not self.compatibility['desktop_supported']:self.error.setText('Bu modelde masaüstü hareketleri için gerekli iskelet bulunamadı.');return
  if self.preview.model_error:self.error.setText('Model görüntülenemedi: '+str(self.preview.model_error));return
  if not self.preview.status.get('ready'):self.error.setText('Karakter önizlemesinin yüklenmesini bekle.');return
  self.character_profile={**self.saved_profile,'name':name,'gender':self.gender.currentData(),'speech_voice':self.engine.currentData(),'voice':self.voice.currentText(),'adult':self.adult.isChecked()}
  super().accept()
 def dispose(self):
  self.disposed=True
  self.voice_preview.cancel()
  self.preview.dispose()
  self.deleteLater()

class ModelImport(QObject):
 def __init__(self,owner,paths,completed):
  super().__init__(owner);self.owner=owner;self.paths=list(paths);self.completed=completed;self.keys=[];self.page=None
  owner.pages.pageClosed.connect(self.closed)
 def next(self):
  if not self.paths:
   self.owner.pages.pageClosed.disconnect(self.closed)
   self.owner.model_import=None
   if self.completed:self.completed(self.keys)
   self.deleteLater();return
  path=self.paths.pop(0)
  try:
   self.page=ModelSetup(self.owner,path);self.page.finished.connect(self.result)
   self.owner._push_page(self.page)
  except Exception as error:
   self.owner.show_error(Path(path).name+': '+str(error));self.paths.clear();self.next()
 def result(self,result):
  if result!=QDialog.DialogCode.Accepted:
   self.paths.clear();return
  from app import save_settings
  try:
   key=add_model(self.page.path);self.owner.settings.setdefault('voice_profiles',{})[key]=self.page.character_profile
   save_settings(self.owner.settings);self.keys.append(key)
  except Exception as error:self.owner.show_error(str(error));self.paths.clear()
 def closed(self,page):
  if page is self.page:
   self.page=None;QTimer.singleShot(0,self.next)

def import_models(owner,paths,completed=None):
 if not paths or owner.pages.busy or getattr(owner,'model_import',None):return
 owner.model_import=ModelImport(owner,paths,completed);owner.model_import.next()
