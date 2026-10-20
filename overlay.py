"""Transparent desktop character with alpha hit region and persistent VRM library."""
import time,ctypes
import numpy as np
from PySide6.QtCore import Qt,QEvent,QTimer,QRect
from PySide6.QtGui import QCursor,QImage,QRegion,QBitmap,QPainter
from PySide6.QtWidgets import QWidget,QLabel,QMenu,QApplication,QFileDialog
from avatar import AvatarView

def compose_hit_frame(frame,front,size):
    """Compose physical pixels first, then map the silhouette to Qt coordinates."""
    frame=frame.convertToFormat(QImage.Format.Format_RGBA8888)
    frame.setDevicePixelRatio(1.)
    if front is not None and not front.isNull():
        front=front.convertToFormat(QImage.Format.Format_RGBA8888);front.setDevicePixelRatio(1.)
        painter=QPainter(frame);painter.drawImage(frame.rect(),front);painter.end()
    return frame if frame.size()==size else frame.scaled(size)

class DesktopCharacter(QWidget):
    def __init__(self,owner):
        super().__init__();self.owner=owner;self.drag=None;self.generation=0;self.manually_placed=False;self.body_bounds=QRect();self.last_region=None;self.drag_clock=0.;self.drag_position=None
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint|Qt.WindowType.WindowStaysOnTopHint|Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground);self.setWindowTitle('Yumi · Masaüstü karakteri')
        self.avatar=AvatarView(self,transparent=True);self.avatar.installEventFilter(self);self.installEventFilter(self)
        self.avatar.runtimeWarning.connect(owner.show_error)
        self.avatar.skin=owner.settings.get('skin','Sakura')
        self.bubble=QLabel(self);self.bubble.setWordWrap(True);self.bubble.setStyleSheet('background:#fff9ff;color:#624b74;border:1px solid #d6b9e3;border-radius:12px;padding:10px;font:12px "Segoe UI";')
        self.bubble.hide();self.set_scale(owner.settings.get('size',100))
        rect=QApplication.primaryScreen().availableGeometry();self.move(rect.right()-self.width()-30,rect.bottom()-self.height()+1)
        from async_mask import AsyncMask
        self.async_mask=AsyncMask();self.mask_readback_failed=False
        self.mask_timer=QTimer(self);self.mask_timer.timeout.connect(self.update_hit_region);self.mask_timer.start(50)
        self.hit_timer=QTimer(self);self.hit_timer.timeout.connect(self.update_mouse_passthrough);self.hit_timer.start(16)
    def set_scale(self,percent):
        self.resize(round(400*percent/100),round(440*percent/100));self.avatar.setMinimumHeight(0);self.avatar.setGeometry(self.rect())
        self.bubble.setGeometry(10,8,max(160,self.width()-20),80);self.bubble.raise_()
    def update_hit_region(self):
        if not self.isVisible() or not self.avatar.isValid():return
        bridge=getattr(self.avatar,'three_desktop',None)
        front=None
        if bridge and bridge.ready:
            # The OpenGL framebuffer excludes the WebEngine child. Compose
            # both alpha surfaces in logical pixels before hit testing.
            frame=self.avatar.grabFramebuffer()
            if bridge.display.isVisible():front=bridge.display.pixmap().toImage()
        elif not self.mask_readback_failed:
            self.avatar.makeCurrent()
            try:frame=self.async_mask.capture(self.avatar)
            except Exception:
                self.async_mask.release();self.mask_readback_failed=True;self.mask_timer.setInterval(200);frame=None
            finally:self.avatar.doneCurrent()
            if frame is None:return
        else:frame=self.avatar.grabFramebuffer().convertToFormat(QImage.Format.Format_RGBA8888)
        frame=compose_hit_frame(frame,front,self.size())
        region=QRegion(QBitmap.fromImage(frame.createAlphaMask(Qt.ImageConversionFlag.ThresholdAlphaDither)))
        self.body_bounds=region.boundingRect()
        if self.bubble.isVisible():region|=QRegion(self.bubble.geometry())
        self.last_region=region
        self.update_mouse_passthrough()
        self.contain()
    def contain(self):
        if not self.isVisible() or self.drag is not None:return
        screen=self.screen().availableGeometry()
        bounds=self.body_bounds if not self.body_bounds.isEmpty() else self.rect()
        if self.manually_placed:
            left=screen.left()-bounds.left();right=screen.right()-bounds.right()
        else:left,right=self.walk_limits()
        x=max(left,min(right,self.x()))
        low=screen.top()-bounds.top();high=screen.bottom()-bounds.bottom()
        y=max(low,min(high,self.y())) if low<=high else low
        if not self.manually_placed:
            if self.avatar.model:
                from locomotion import ground_pixel
                y=round(screen.bottom()+1-ground_pixel(self.height()))
            else:y=high if low<=high else low
        if x!=self.x() or y!=self.y():self.move(x,y)
    def update_mouse_passthrough(self):
        if not self.isVisible() or self.last_region is None:return
        point=self.mapFromGlobal(QCursor.pos())
        # A few pixels of tolerance let users catch moving hair and narrow limbs.
        hit=self.last_region.intersects(QRect(point.x()-7,point.y()-7,15,15))
        inside=self.drag is not None or self.last_region.contains(point) or hit
        # Layered window alpha remains uncut; Windows passes clicks through outside the current silhouette.
        user32=ctypes.windll.user32;get=user32.GetWindowLongPtrW;set_style=user32.SetWindowLongPtrW
        get.argtypes=[ctypes.c_void_p,ctypes.c_int];get.restype=ctypes.c_ssize_t
        set_style.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_ssize_t];set_style.restype=ctypes.c_ssize_t
        hwnd=int(self.winId());style=get(hwnd,-20);desired=(style&~0x20) if inside else (style|0x20)
        if style!=desired:set_style(hwnd,-20,desired)
    def walk_limits(self):
        screen=self.screen().availableGeometry()
        # The entire render viewport stays inside horizontally. Pose, tail and
        # wing changes therefore cannot invalidate a cached silhouette limit.
        left=screen.left()+4;right=screen.right()-self.width()+1-4
        if right<left:left=right=screen.left()+(screen.width()-self.width())//2
        return left,right
    def return_to_taskbar(self):
        self.manually_placed=False;self.owner.settings['roam']=True;self.owner.last_user_action=0;self.update_hit_region();self.owner._roam()
    def select_skin(self,key):
        from app import save_settings
        try:
            self.owner.avatar.skin=key
            self.avatar.skin=key
            from voice_profiles import apply_profile
            saved=apply_profile(self.owner.settings,key)
            self.set_scale(saved.get('size',100))
            self.owner.voice_capture.wake_name=saved.get('name','Yumi');self.sync();save_settings(self.owner.settings);self.owner._sync_name_wake();self.owner._warm_native(force=True)
        except Exception as error:self.owner.show_error('Model seçilemedi: '+str(error))
    def load_vrm(self):
        from pathlib import Path
        from skins import add_model
        paths,_=QFileDialog.getOpenFileNames(self,'VRM modellerini ekle',str(Path.home()/'Downloads'),'VRM karakter (*.vrm)')
        from model_setup import import_models
        self.owner._show()
        import_models(self.owner,paths,lambda keys:self.select_skin(keys[-1]) if keys else None)
    def say(self,text,ms=5000):
        # Responses already live in the chat window and speech output. Desktop
        # callouts obscure other applications and enlarge the click region.
        self.bubble.hide()
    def sync(self):
        for name in ('walk_direction','walking_turn','pose','prop','skin','speaking','mouth_level','conversation','hand_gesture'):setattr(self.avatar,name,getattr(self.owner.avatar,name))
    def eventFilter(self,obj,event):
        if event.type()==QEvent.Type.MouseButtonDblClick:self.owner._show();return True
        if event.type()==QEvent.Type.MouseButtonPress:
            if event.button()==Qt.MouseButton.RightButton:self.menu();return True
            if event.button()!=Qt.MouseButton.LeftButton:return False
            self.owner.move_animation.stop();self.owner.manual_pose=None;self.manually_placed=True;self.drag=event.globalPosition().toPoint()-self.pos();self.drag_clock=time.perf_counter();self.drag_position=self.pos();self.owner.last_user_action=time.perf_counter()
            # Capture at the top-level window, so dragging still works when the
            # character rotates or the pointer leaves its OpenGL child widget.
            self.grabMouse();self.update_mouse_passthrough();return True
        if event.type()==QEvent.Type.MouseMove and self.drag is not None:
            pointer=event.globalPosition().toPoint()
            target_screen=QApplication.screenAt(pointer) or self.screen()
            rect=target_screen.availableGeometry();pos=pointer-self.drag;bounds=self.body_bounds if not self.body_bounds.isEmpty() else self.rect()
            now=time.perf_counter();delta=pos-(self.drag_position or self.pos());dt=max(.008,now-self.drag_clock);self.drag_clock=now;self.drag_position=pos
            if self.avatar.model:
                velocity=np.clip(np.array([delta.x(),-delta.y(),0.])*3.1/max(80,self.body_bounds.height())/dt,-8.,8.)
                # Sideways mouse motion used to throw long hair and skirts too far.
                # Keep the vertical response while reducing horizontal inertia.
                velocity[0]*=.55
                from motion_space import drag_to_vrm
                # The tip must lag opposite the cursor after both VRM and scene rotations.
                self.avatar.model.hair_springs.external_velocity=drag_to_vrm(
                    velocity,self.avatar.model.data.flip,
                    self.avatar.model.data.scale*self.avatar.render_scale,
                    *self.avatar.render_angles)
            self.move(max(rect.left()-bounds.left(),min(rect.right()-bounds.right(),pos.x())),max(rect.top()-bounds.top(),min(rect.bottom()-bounds.bottom(),pos.y())));return True
        if event.type()==QEvent.Type.MouseButtonRelease and event.button()==Qt.MouseButton.LeftButton:
            if self.drag is not None:
                self.drag=None;self.releaseMouse();self.contain();self.update_mouse_passthrough()
                return True
            return False
        if event.type()==QEvent.Type.Wheel:
            size=max(50,min(180,self.owner.settings['size']+(10 if event.angleDelta().y()>0 else -10)));self.owner.settings['size']=size;self.set_scale(size)
            from voice_profiles import profile
            self.owner.settings.setdefault('voice_profiles',{})[self.owner.settings['skin']]={**profile(self.owner.settings),'size':size}
            from app import save_settings
            save_settings(self.owner.settings);return True
        return super().eventFilter(obj,event)
    def menu(self):
        menu=self.build_menu();menu.exec(QCursor.pos())
    def build_menu(self):
        menu=QMenu(self);models=menu.addMenu('Model seç')
        menu.model_menu=models
        from skins import available
        for title,key in available(self.owner.settings):
            action=models.addAction(title);action.setCheckable(True);action.setChecked(key==self.owner.settings['skin']);action.triggered.connect(lambda checked=False,k=key:self.select_skin(k))
        menu.addAction('Yumi’yi aç',self.owner._show)
        from model_visibility import add_action
        add_action(menu,self.owner)
        menu.addAction('Ayarlar',self.owner._settings)
        menu.addAction('🏠 Akıllı Ev & Cihazlar',self.owner._open_smart_home)
        def action(text):
            from voice_actions import execute
            answer=execute(self.owner,text)
            if answer:self.owner.show_bubble(answer)
        menu.addAction('Koltuğa otur',lambda:action('koltuğa otur'))
        menu.addAction('Bilgisayara otur',lambda:action('bilgisayara otur'))
        menu.addAction('Ayağa kalk',lambda:action('ayağa kalk'))
        scenarios=menu.addMenu('Günlük senaryolar')
        for label,command in [('Kitap oku','kitap oku'),('TV / film izle','film izle'),('Yazı yaz','yazı yaz'),('Toplantı','toplantıya katıl'),('Kahve yap','kahve yap'),('Pencereden bak','pencereden bak'),('Dinlen','dinlen')]:
            scenarios.addAction(label,lambda checked=False,c=command:action(c))
        scenarios.addAction('Kodlama / odaklanma',lambda:action('kod yaz'))
        scenarios.addAction('Web / metin okuma',lambda:action('webde oku'))
        enabled=scenarios.addAction('Otomatik günlük senaryolar');enabled.setCheckable(True);enabled.setChecked(self.owner.settings.get('daily_scenarios',True))
        enabled.triggered.connect(lambda checked:action('günlük senaryoları aç' if checked else 'günlük senaryoları kapat'))
        music=menu.addMenu('Müzik')
        automatic=music.addAction('Müziği otomatik algıla');automatic.setCheckable(True);automatic.setChecked(self.owner.settings.get('music_auto',True))
        automatic.triggered.connect(lambda checked:action('otomatik müzik tepkisini aç' if checked else 'otomatik müzik tepkisini kapat'))
        music.addAction('Ritme göre dans et',lambda:action('müziğe göre dans et'))
        music.addAction('Direk dansı · ritme göre',lambda:action('direk dansı yap'))
        music.addAction('Sakince dinle',lambda:action('müzik dinle'))
        music.addAction('Durdur',lambda:action('müzik dansını durdur'))
        genres=music.addMenu('Tür seç')
        genres.addAction('Otomatik · medya ve yerel ses',lambda:action('müzik türü otomatik'))
        from music_analysis import GENRES
        for genre in GENRES:genres.addAction(genre,lambda checked=False,g=genre:action('müzik türü '+g))
        menu.addAction('Yeniden gezin',self.return_to_taskbar)
        return menu
