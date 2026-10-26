"""Bounded, cancellable voice previews independent of the conversation queue."""
import time
import hashlib
import subprocess,threading,queue,json,os
from collections import OrderedDict
from pathlib import Path
from PySide6.QtCore import QObject,QTimer,QTemporaryDir,QUrl
from PySide6.QtMultimedia import QMediaPlayer,QAudioOutput
from backend import local_speech
from api import speech

_cache=OrderedDict()
SAMPLE='Merhaba, sesimi böyle duyacaksın.'

class VoicePreview(QObject):
    def __init__(self,dialog,owner,button,label):
        super().__init__(dialog)
        self.owner=owner;self.button=button;self.label=label
        self.future=None;self.active=False;self.deadline=0.;self.key=None
        self.process=None;self.events=queue.Queue(maxsize=8);self.preview_error=None
        self.directory=QTemporaryDir();self.player=QMediaPlayer(self)
        self.output=QAudioOutput(self);self.player.setAudioOutput(self.output)
        self.timer=QTimer(self);self.timer.setInterval(100);self.timer.timeout.connect(self.poll)
        self.player.mediaStatusChanged.connect(self.media_status)
        self.player.errorOccurred.connect(lambda *_:self.finish('Ses oynatılamadı: '+self.player.errorString()))
        self.player.playbackStateChanged.connect(self.playback_state)
        dialog.finished.connect(lambda *_:self.cancel())
    def start(self,voice,api_voice):
        self.cancel()
        if not isinstance(voice,str) or not voice.startswith('gemini-live:'):
            self.label.setText('Bu ses için canlı örnek henüz kullanılamıyor.');return
        if self.owner.busy:
            self.label.setText('Ses örneğinden önce mevcut konuşmayı bitir.');return
        selected=voice.split(':',1)[1]
        if selected not in __import__('voice_profiles').GEMINI_VOICE_NAMES:
            self.label.setText('Bu Gemini sesi desteklenmiyor.');return
        from resource_guard import require_capacity,GiB
        from voice_profiles import character_name
        root=Path(__file__).resolve().parent
        command=[str(root/'.venv/Scripts/python.exe'),'-u','-B',str(root/'live_voice/run_live.py'),'--worker','--ui-mode','--probe','--play-test','--voice',selected,'--name',character_name(self.owner.settings)]
        environment=os.environ.copy();environment['PYTHONIOENCODING']='utf-8'
        self.previous_suspended=self.owner.voice_capture.suspended;self.preview_error=None;self.events=queue.Queue(maxsize=8)
        try:
            require_capacity(GiB)
            self.process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',env=environment,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        except (OSError,RuntimeError):self.label.setText('Ses örneği başlatılamadı. Bağlantını ve kayıtlı anahtarını kontrol et.');return
        self.active=True;self.owner.busy=True;self.owner.voice_capture.suspended=True
        if hasattr(self.owner,'name_wake'):self.owner.name_wake.pause()
        self.button.setEnabled(False);self.label.setText('Seçtiğin ses hazırlanıyor…');self.deadline=time.monotonic()+35
        process=self.process;events=self.events
        def read():
            for line in process.stdout:
                try:item=json.loads(line)
                except ValueError:continue
                if isinstance(item,dict) and item.get('event') in ('error','first_audio_to_device'):
                    try:events.put_nowait(item)
                    except queue.Full:pass
        threading.Thread(target=read,daemon=True).start();self.timer.start()
    def poll(self):
        if not self.active:return
        if self.process is not None:
            while not self.events.empty():
                event=self.events.get_nowait()
                if event.get('event')=='error':self.preview_error=event.get('message','Ses örneği alınamadı.')
                elif event.get('event')=='first_audio_to_device':self.label.setText('Seçtiğin ses çalıyor…')
            if self.process.poll() is not None:
                self.finish(self.preview_error or ('Ses örneği tamamlandı.' if self.process.returncode==0 else 'Ses örneği alınamadı. Bağlantını ve kayıtlı anahtarını kontrol et.'));return
        if time.monotonic()>=self.deadline:
            self.finish('Ses zamanında başlamadı. Yeniden dene veya başka bir ses seç.');return
        if self.future is None or not self.future.done():return
        future=self.future;self.future=None
        try:audio=future.result()
        except Exception as error:
            self.finish(str(error));return
        _cache[self.key]=audio;_cache.move_to_end(self.key)
        while len(_cache)>8:_cache.popitem(last=False)
        self.play(audio)
    def play(self,audio):
        if not self.active:return
        suffix='.wav' if audio[:4]==b'RIFF' else '.mp3'
        identity=hashlib.sha256(repr(self.key).encode()).hexdigest()[:12]
        path=Path(self.directory.path())/('preview-'+identity+suffix);path.write_bytes(audio)
        self.label.setText('Ses başlatılıyor…');self.deadline=time.monotonic()+8
        self.player.setSource(QUrl.fromLocalFile(str(path)));self.player.play()
    def playback_state(self,state):
        if self.active and state==QMediaPlayer.PlaybackState.PlayingState:
            self.deadline=time.monotonic()+30;self.label.setText('Ses çalıyor…')
    def media_status(self,status):
        if self.active and status==QMediaPlayer.MediaStatus.EndOfMedia:self.finish('Ses örneği tamamlandı.')
    def finish(self,message):
        if not self.active:return
        if self.process is not None:
            process=self.process;self.process=None
            if process.poll() is None:
                import psutil
                try:children=psutil.Process(process.pid).children(recursive=True)
                except psutil.Error:children=[]
                for child in reversed(children):
                    try:child.terminate()
                    except psutil.Error:pass
                process.terminate()
                try:process.wait(1)
                except subprocess.TimeoutExpired:process.kill()
            try:process.stdin.close()
            except (OSError,ValueError):pass
        self.active=False;self.timer.stop();self.player.stop();self.button.setEnabled(True)
        self.label.setText(message)
        self.owner.busy=False;self.owner.voice_capture.suspended=self.previous_suspended
        self.owner.set_status('Ses örneği durdu' if not message else message)
        if hasattr(self.owner,'_sync_name_wake'):self.owner._sync_name_wake()
    def cancel(self):
        self.finish('')
        if self.future is not None:self.future.cancel()
