"""Bounded latest-frame bridge to the upstream material renderer.

Python owns animation, IK, source SpringBone and prop placement. The browser
only draws the final pose; it never runs a second physics simulation.
"""
import json,time,base64
import numpy as np
from contextlib import contextmanager
from contextvars import ContextVar
from PySide6.QtCore import Qt,QUrl,QTimer
from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QImage,QPixmap
from three_vrm_view import ThreeVRMView

PROP_SINK=ContextVar('yumi_prop_sink',default=None)

class DesktopVRM:
    def __init__(self,host):
        self.host=host;self.path=None;self.inflight=False;self.last=0.;self.props=[]
        self.failed=False;self.ready=False;self.generation=0
        self.present_pending=False;self.disposed=False;self.paused=False;self.delivered=False
        self.view=ThreeVRMView(host.parentWidget() or host);self.view.label.hide()
        self.display=QLabel(host.parentWidget() or host);self.display.setScaledContents(True)
        self.display.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.display.hide()
        self.view.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.view.ready.connect(self._ready);self.view.failed.connect(self._failed)
        self.view.page.renderProcessTerminated.connect(lambda status,code:self._failed('Görsel motor durdu ('+str(code)+').'))
        self.view.hide()
    def _ready(self,status):
        if self.disposed or self.path is None or status.get('url')!=QUrl.fromLocalFile(str(self.path)).toString():return
        self.ready=True;self.view.page.runJavaScript('window.yumiVRM.pause(true)')
    def _failed(self,message):
        if self.disposed:return
        self.ready=False;self.failed=True;self.view.hide();self.display.hide()
        self.host.runtimeWarning.emit('three-vrm masaüstü çizimi açılamadı: '+message)
    def begin(self):
        if self.disposed:return False
        model=self.host.model
        if model is None:
            if self.path is not None:self.generation+=1
            self.view.hide();self.display.hide();self.ready=False;self.path=None;return False
        path=model.data.path.resolve()
        if path!=self.path:
            self.path=path;self.ready=False;self.failed=False;self.generation+=1;self.inflight=False;self.delivered=False
            self.display.clear();self.display.hide()
            QTimer.singleShot(0,lambda p=path:self.view.load_model(p) if p==self.path else None)
        if self.failed:return False
        # First draw compiles this model's material shaders. Give it the same
        # bounded startup budget as the model loader, then enforce 5s per frame.
        if self.inflight and time.perf_counter()-self.last>(5 if self.delivered else 20):
            self._failed('Çizici yanıt süresi aşıldı.');return False
        geometry=self.host.geometry() if self.display.parentWidget() is self.host.parentWidget() else self.host.rect()
        if self.delivered and (self.display.geometry()!=geometry or self.display.isHidden()) and not self.present_pending:
            self.present_pending=True;QTimer.singleShot(0,self._present)
        self.props=[];self.pole_frame=None
        return self.ready
    def _present(self):
        self.present_pending=False
        if self.disposed or self.failed or self.path is None or self.paused or not self.delivered or not self.host.isVisible():return
        geometry=self.host.geometry() if self.display.parentWidget() is self.host.parentWidget() else self.host.rect()
        self.display.setGeometry(geometry);self.display.show();self.display.raise_()
    def pole(self,point,height,radius,visible,matrix):
        transform=np.eye(4);transform[:3,3]=point
        scale=np.diag([visible,visible,visible,1.])
        self.pole_frame={'matrix':(matrix@transform@scale).T.ravel().tolist(),'height':float(height),'radius':float(radius)}
    @contextmanager
    def capture_props(self):
        token=PROP_SINK.set(self if self.ready else None)
        try:yield
        finally:PROP_SINK.reset(token)
    def capture(self,asset,exclude,include,placements,animation_time,opacity):
        from OpenGL.GL import glGetDoublev,GL_MODELVIEW_MATRIX
        matrix=np.asarray(glGetDoublev(GL_MODELVIEW_MATRIX),float).T
        animation=asset.animation_matrices(animation_time) if animation_time is not None else {}
        url=QUrl.fromLocalFile(str(asset.path.resolve())).toString()
        self.view.guard.assets.add(asset.path.resolve())
        parts=[];ordinals={}
        for index,part in enumerate(asset.parts):
            ordinal=ordinals.get(part['node'],0);ordinals[part['node']]=ordinal+1
            name=part['name']
            if any(word.casefold() in name.casefold() for word in exclude):continue
            if include and not any(word.casefold() in name.casefold() for word in include):continue
            transform=matrix.copy()
            if placements is not None:
                if name not in placements:continue
                anchor,scale,target,yaw=placements[name]
                from furniture_scene import rotation
                translate=np.eye(4);translate[:3,3]=target
                resize=np.diag([*scale,1.]);shift=np.eye(4);shift[:3,3]=-anchor
                turn=np.eye(4);turn[:3,:3]=rotation(yaw)
                transform=transform@translate@resize@shift@turn
            if part['node'] in animation:transform=transform@animation[part['node']]
            parts.append({'part':index,'node':part['node'],'primitive':ordinal,'mesh':part['mesh'],'matrix':transform.T.ravel().tolist()})
        self.props.append({'url':url,'parts':parts,'opacity':float(opacity)})
    def submit(self,matrix):
        now=time.perf_counter()
        if self.disposed or self.paused or not self.host.isVisible() or self.inflight or now-self.last<1/30 or not self.ready:return
        self.last=now;self.inflight=True;generation=self.generation
        model=self.host.model;d=model.data
        local=[]
        for node in range(len(d.nodes)):
            parent=d.parents.get(node)
            m=np.linalg.solve(model.world[parent],model.world[node]) if parent is not None else model.world[node]
            local.append(m.T.ravel().tolist())
        canonical=np.eye(4);canonical[:3,:3]=d.flip*d.scale;canonical[:3,3]=-d.origin*d.scale
        frame={'width':self.host.width(),'height':self.host.height(),'dpr':self.host.devicePixelRatioF(),'matrix':(matrix@canonical).T.ravel().tolist(),'nodes':local,
               'expressions':[[mesh,index,float(value)] for (mesh,index),value in getattr(model,'expression_weights',{}).items()],
               'props':self.props,'pole':self.pole_frame}
        from seated_garment import patches
        frame['garments']=patches(model)
        source='(()=>{window.yumiVRM.desktopFrame('+json.dumps(frame,separators=(',',':'),allow_nan=False)+');return JSON.stringify({status:window.yumiVRM.status,image:window.yumiVRM.capture()})})()'
        def done(value):
            if self.disposed or generation!=self.generation:return
            self.inflight=False
            try:
                result=json.loads(value);status=result['status']
                if status.get('error'):raise ValueError('renderer error')
                if not self.paused and self.host.isVisible():
                    data=result.get('image','').partition(',')[2]
                    image=QImage.fromData(base64.b64decode(data))
                    if image.isNull():raise ValueError('empty frame')
                    image.setDevicePixelRatio(frame['dpr']);self.display.setPixmap(QPixmap.fromImage(image));self.delivered=True
                    self._present()
            except (ValueError,TypeError,KeyError):self._failed('Son poz görüntüsü okunamadı.')
        self.view.page.runJavaScript(source,done)
    def pause(self,paused):
        self.paused=bool(paused)
        if self.disposed:return
        if paused:
            self.generation+=1;self.inflight=False;self.delivered=False;self.display.hide()
        # Final poses are rendered by desktopFrame, including after resume.
        # The preview RAF must stay paused to avoid a duplicate render loop.
        self.view.page.runJavaScript('window.yumiVRM?.pause(true)')
    def dispose(self):
        if self.disposed:return
        self.disposed=True;self.generation+=1;self.ready=False
        self.view.dispose();self.display.hide()
