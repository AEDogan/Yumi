"""Ephemeral Chromium full-duplex audio with mandatory acoustic echo cancellation.
No keys/network transport/transcripts enter the renderer. PCM exists only in memory.
"""
import asyncio,base64,json,queue,time,os
from pathlib import Path
from PySide6.QtCore import QObject,Signal,Slot,QUrl,QUrlQuery,QTimer
from PySide6.QtWidgets import QApplication
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage,QWebEngineProfile,QWebEngineSettings,QWebEngineUrlRequestInterceptor
from live_core import LiveError

class LocalOnly(QWebEngineUrlRequestInterceptor):
    def interceptRequest(self,info):
        if info.requestUrl().scheme() not in ('file','qrc','blob','data','about'):info.block(True)

class AudioPage(QWebEnginePage):
    def javaScriptConsoleMessage(self,*args):pass # Never print audio or browser internals.
    def acceptNavigationRequest(self,url,kind,main):return url.scheme() in ('file','qrc','about')

class Bridge(QObject):
    command=Signal(str)
    def __init__(self,owner):super().__init__();self.owner=owner
    @Slot(str)
    def ready(self,settings):
        try:item=json.loads(settings)
        except ValueError:self.owner.failure='Ses ayarları doğrulanamadı.';return
        if item.get('echoCancellation') is not True or item.get('noiseSuppression') is not True:
            self.owner.failure='Mikrofon yankı giderme desteklemiyor; korumasız ses oturumu açılmadı.';return
        self.owner.ready=True;self.owner.session.emit('aec_ready',echo_cancellation=True,noise_suppression=True,sample_rate=item.get('sampleRate',0))
    @Slot(str)
    def failed(self,code):self.owner.failure='Yankı korumalı ses aygıtı açılamadı ('+code[:40]+').' 
    @Slot(str)
    def microphone(self,encoded):
        if self.owner.closed:return
        try:pcm=base64.b64decode(encoded,validate=True)
        except ValueError:return
        if len(pcm)!=1280:return
        self.owner.capture(pcm)
    @Slot(int)
    def pull(self,epoch):
        owner=self.owner
        if owner.closed or epoch!=owner.epoch:return
        pcm,count=owner.session.playback.read(960)
        self.command.emit(json.dumps({'kind':'audio','epoch':epoch,'pcm':base64.b64encode(pcm).decode(),'count':count}))
    @Slot(bool,int,float)
    def played(self,audible,epoch,level):
        if self.owner.closed or epoch!=self.owner.epoch:return
        self.owner.session.emit('avatar_playback',audible=bool(audible),level=min(1.,max(0.,float(level))))
        if audible:self.owner.session.played(.02)
        else:self.owner.session.silent_output()

class BrowserAudioDevice:
    def __init__(self,session,input_device=None,output_device=None,capture_enabled=True):
        if output_device is not None:raise LiveError('Özel hoparlör seçimi desteklenmiyor.')
        if isinstance(input_device,int):
            from startup_runtime import prepare_audio_runtime
            input_device=prepare_audio_runtime().query_devices(input_device)['name']
        self.session=session;self.input=queue.Queue(maxsize=8);self.ready=False;self.failure=None;self.closed=False;self.epoch=0;self.dropped=0;self.notified_dropped=0;self.first=True
        self.profile=QWebEngineProfile();self.interceptor=LocalOnly();self.profile.setUrlRequestInterceptor(self.interceptor)
        self.page=AudioPage(self.profile);self.page.settings().setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture,False)
        self.bridge=Bridge(self);self.channel=QWebChannel();self.channel.registerObject('audio',self.bridge);self.page.setWebChannel(self.channel)
        # Grant only microphone capture to this fixed local page, no camera or remote origins.
        self.page.featurePermissionRequested.connect(self.permission)
        self.page.renderProcessTerminated.connect(lambda *_:setattr(self,'failure','Ses işleyicisi durdu.'))
        self.previous_flush=getattr(session,'on_audio_flush',None);session.on_audio_flush=self.flush
        url=QUrl.fromLocalFile(str(Path(__file__).with_name('audio.html').resolve()))
        query=QUrlQuery();query.addQueryItem('capture','1' if capture_enabled else '0');query.addQueryItem('microphone',input_device or '')
        url.setQuery(query);self.page.setUrl(url)
    def permission(self,origin,feature):
        allowed=origin.scheme()=='file' and feature==QWebEnginePage.Feature.MediaAudioCapture
        self.page.setFeaturePermission(origin,feature,QWebEnginePage.PermissionPolicy.PermissionGrantedByUser if allowed else QWebEnginePage.PermissionPolicy.PermissionDeniedByUser)
    async def open(self):
        deadline=time.monotonic()+8
        while not self.ready:
            if self.failure:raise LiveError(self.failure,code='aec_device_failed')
            if time.monotonic()>deadline:raise LiveError('Yankı korumalı ses aygıtı 8 saniyede açılamadı.',code='aec_device_timeout')
            await asyncio.sleep(.01)
    def start(self):pass
    def capture(self,pcm):
        try:self.input.put_nowait(pcm)
        except queue.Full:
            try:self.input.get_nowait()
            except queue.Empty:pass
            try:self.input.put_nowait(pcm);self.dropped+=1
            except queue.Full:pass
        if self.first:self.first=False;self.session.emit('first_microphone_block')
    async def send(self):
        while True:
            if self.failure:raise LiveError(self.failure,code='aec_device_failed')
            if self.dropped!=self.notified_dropped:
                self.session.emit('input_recovered',dropped_blocks=self.dropped,overflow_count=0);self.notified_dropped=self.dropped
            try:pcm=self.input.get_nowait()
            except queue.Empty:await asyncio.sleep(.005);continue
            await self.session.send_audio(pcm)
    def flush(self):
        self.epoch+=1;self.bridge.command.emit(json.dumps({'kind':'clear','epoch':self.epoch}))
    def close(self):
        if self.closed:return
        self.closed=True;self.session.on_audio_flush=self.previous_flush
        self.bridge.command.emit(json.dumps({'kind':'close'}));self.page.setUrl(QUrl('about:blank'))
        while not self.input.empty():
            try:self.input.get_nowait()
            except queue.Empty:break
        # Delete page before its owning off-the-record profile.
        self.page.deleteLater();self.profile.deleteLater()

def run_qt(coroutine):
    """Run Qt and asyncio on the same thread: one receiver, one capture sender."""
    app=QApplication.instance() or QApplication([]);app.setQuitOnLastWindowClosed(False)
    loop=asyncio.new_event_loop();asyncio.set_event_loop(loop);task=loop.create_task(coroutine)
    timer=QTimer();timer.setInterval(5)
    def pump():
        loop.call_soon(loop.stop);loop.run_forever()
        if task.done():timer.stop();app.quit()
    timer.timeout.connect(pump);timer.start();app.exec()
    try:return task.result()
    finally:
        for pending in asyncio.all_tasks(loop):pending.cancel()
        loop.run_until_complete(asyncio.gather(*asyncio.all_tasks(loop),return_exceptions=True));loop.close();app.processEvents()
