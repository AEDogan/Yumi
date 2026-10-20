"""Isolated offline upstream VRM renderer for import and source comparison."""
import json,logging
from pathlib import Path
from PySide6.QtCore import Qt,QUrl,QTimer,Signal,QCoreApplication
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel,QDialog,QPushButton
from PySide6.QtWebEngineCore import QWebEnginePage,QWebEngineProfile,QWebEngineSettings,QWebEngineUrlRequestInterceptor
from PySide6.QtWebEngineWidgets import QWebEngineView
ROOT=Path(__file__).resolve().parent/'vrm_runtime'
if QCoreApplication.instance() is None:QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

class LocalFilesOnly(QWebEngineUrlRequestInterceptor):
    def __init__(self,parent):super().__init__(parent);self.asset=None;self.assets=set()
    def interceptRequest(self,info):
        url=info.requestUrl();scheme=url.scheme()
        allowed=scheme in ('data','blob','about')
        if scheme=='file':
            target=Path(url.toLocalFile()).resolve()
            allowed=target.is_relative_to(ROOT) or target==self.asset or target in self.assets
        if not allowed:info.block(True)

class LocalPage(QWebEnginePage):
    def javaScriptConsoleMessage(self,level,message,line,source):
        logging.getLogger(__name__).warning('three-vrm viewer [%s:%s] %s',Path(source).name,line,message)
    def acceptNavigationRequest(self,url,kind,main):
        return url==QUrl.fromLocalFile(str(ROOT/'viewer.html')) or url.toString()=='about:blank'

class ThreeVRMView(QWidget):
    ready=Signal(dict);failed=Signal(str)
    def __init__(self,parent=None,path=None):
        super().__init__(parent);self.model_error=None;self.status={};self.path=None;self.started=False;self.polling=False;self.load_requested=False;self.generation=0;self.disposed=False
        layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0)
        self.web=QWebEngineView(self);layout.addWidget(self.web,1)
        self.label=QLabel('Karakter three-vrm ile hazırlanıyor…');self.label.setWordWrap(True);layout.addWidget(self.label)
        self.profile=QWebEngineProfile(self);self.guard=LocalFilesOnly(self.profile);self.profile.setUrlRequestInterceptor(self.guard)
        self.page=LocalPage(self.profile,self.web);self.page.setBackgroundColor(QColor(0,0,0,0));self.web.setPage(self.page)
        self.web.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.page.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,False)
        self.page.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls,True)
        self.profile.downloadRequested.connect(lambda download:download.cancel())
        self.timer=QTimer(self);self.timer.setInterval(120);self.timer.timeout.connect(self.poll)
        self.web.loadFinished.connect(self._loaded);self.web.setUrl(QUrl.fromLocalFile(str(ROOT/'viewer.html')))
        if path:self.load_model(path)
    def load_model(self,path):
        self.path=Path(path).resolve();self.guard.asset=self.path;self.model_error=None;self.status={}
        self.generation+=1
        generation=self.generation;QTimer.singleShot(20000,lambda:self._timeout(generation))
        self.load_requested=False
        self.label.setText('Karakter three-vrm ile hazırlanıyor…')
        if self.started:self.timer.start()
    def _loaded(self,ok):
        self.started=ok
        if not ok:self._error('three-vrm görüntüleyicisi açılamadı.');return
        if self.path:self.timer.start()
    def _load_model(self):
        self.load_requested=True
        url=QUrl.fromLocalFile(str(self.path)).toString()
        self.page.runJavaScript('window.yumiVRM?.load('+json.dumps(url)+')')
        self.timer.start();generation=self.generation
        QTimer.singleShot(20000,lambda:self._timeout(generation))
    def _timeout(self,generation):
        if generation==self.generation and not self.disposed and not self.status.get('ready') and not self.model_error:self._error('three-vrm model yükleme süresi aşıldı.')
    def poll(self):
        if self.polling or self.disposed:return
        self.polling=True
        self.page.runJavaScript('JSON.stringify(window.yumiVRM?.status ?? null)',self._status)
    def _status(self,value):
        self.polling=False
        if self.disposed:return
        if isinstance(value,str):
            try:value=json.loads(value)
            except ValueError:return
        if not isinstance(value,dict):return
        if not self.load_requested:
            self._load_model();return
        if value.get('url')!=QUrl.fromLocalFile(str(self.path)).toString():return
        self.status=value
        if value.get('error'):self._error(value['error'])
        elif value.get('ready'):
            self.timer.stop();self.label.setText('three-vrm · modelin kendi malzemeleri ve fiziği');self.ready.emit(value)
    def _error(self,error):
        self.timer.stop();self.model_error=str(error);self.label.setText('Model açılamadı: '+str(error));self.failed.emit(str(error))
    def dispose(self):
        self.disposed=True;self.generation+=1
        self.timer.stop();self.page.runJavaScript('window.yumiVRM?.dispose()');self.web.stop()
    def hideEvent(self,event):
        super().hideEvent(event)
        if self.started:self.page.runJavaScript('window.yumiVRM?.pause(true)')
    def showEvent(self,event):
        super().showEvent(event)
        if self.started:self.page.runJavaScript('window.yumiVRM?.pause(false)')

class ThreeVRMInspection(QDialog):
    def __init__(self,owner,path):
        super().__init__(owner);self.setWindowTitle('Karakter önizlemesi');self.setWindowFlags(Qt.WindowType.Widget)
        layout=QVBoxLayout(self);title=QLabel('Karakter önizlemesi');title.setStyleSheet('font-size:20px;font-weight:600');layout.addWidget(title)
        self.preview=ThreeVRMView(self,path);self.preview.setMinimumHeight(350);layout.addWidget(self.preview,1)
        note=QLabel('Modelin kendi malzemeleri ve tanımlı fiziği gösterilir. Bu görünüm masaüstü hareketlerini veya tam kumaş çarpışmasını doğrulamaz.');note.setWordWrap(True);layout.addWidget(note)
        close=QPushButton('Geri dön');close.clicked.connect(self.reject);layout.addWidget(close)
    def dispose(self):
        self.preview.dispose();self.deleteLater()
