"""One-window page history with bounded horizontal transitions."""
from PySide6.QtCore import Signal,Qt,QPoint,QPropertyAnimation,QParallelAnimationGroup,QEasingCurve
from PySide6.QtWidgets import QWidget,QScrollArea,QFrame

class PageStack(QWidget):
    pageClosed=Signal(object)
    def __init__(self,parent=None,reduced_motion=False):
        super().__init__(parent)
        self.history=[];self.frames={};self.busy=False;self.group=None;self.complete=None
        self.duration=0 if reduced_motion else 220
        try:
            import ctypes
            enabled=ctypes.c_int(1)
            if ctypes.windll.user32.SystemParametersInfoW(0x1042,0,ctypes.byref(enabled),0) and not enabled.value:self.duration=0
        except (AttributeError,OSError):pass
    def addWidget(self,page):
        if page in self.frames:return
        if not self.history:
            page.setParent(self);frame=page;self.history.append(page)
        else:
            page.setWindowFlags(Qt.WindowType.Widget)
            frame=QScrollArea(self);frame.setWidgetResizable(True);frame.setFrameShape(QFrame.Shape.NoFrame)
            frame.setWidget(page)
        self.frames[page]=frame;frame.setGeometry(self.rect());frame.hide()
        if len(self.history)==1 and self.history[0] is page:self.setCurrentWidget(page)
    def currentWidget(self):return self.history[-1] if self.history else None
    def setCurrentWidget(self,page):
        if self.busy:return False
        if page==self.currentWidget():
            self.frames[page].show();return True
        if page in self.history:return False
        current=self.currentWidget()
        if hasattr(current,'voice_preview'):current.voice_preview.cancel()
        self.addWidget(page)
        old=self.frames[self.currentWidget()];self.history.append(page)
        self.animate(old,self.frames[page],True)
        return True
    def pop(self,page):
        if self.busy or len(self.history)<2 or page!=self.currentWidget():return False
        old=self.frames[page];self.history.pop();target=self.frames[self.currentWidget()]
        self.animate(old,target,False,page)
        return True
    def animate(self,old,target,forward,closing=None):
        self.busy=True;self.closing=closing;self.old=old;self.target=target
        old.setEnabled(False);target.setEnabled(False)
        width=max(1,self.width());target.move(width if forward else -width,0);target.show();target.raise_()
        if not self.duration:self.finish();return
        self.group=QParallelAnimationGroup(self)
        for frame,start,end in ((old,QPoint(0,0),QPoint(-width if forward else width,0)),(target,target.pos(),QPoint(0,0))):
            animation=QPropertyAnimation(frame,b'pos',self.group);animation.setDuration(self.duration)
            animation.setStartValue(start);animation.setEndValue(end);animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
            self.group.addAnimation(animation)
        self.group.finished.connect(self.finish);self.group.start()
    def finish(self):
        if not self.busy:return
        self.old.hide();self.target.setGeometry(self.rect());self.target.setEnabled(True);self.target.show()
        closing=self.closing;self.busy=False
        if self.group:self.group.deleteLater();self.group=None
        self.currentWidget().setFocus(Qt.FocusReason.OtherFocusReason)
        if closing:
            frame=self.frames.pop(closing);frame.takeWidget();frame.deleteLater()
            self.pageClosed.emit(closing)
            if hasattr(closing,'dispose'):closing.dispose()
            else:closing.deleteLater()
    def removeWidget(self,page):
        return self.pop(page)
    def resizeEvent(self,event):
        super().resizeEvent(event)
        if self.busy:
            if self.group:self.group.stop()
            self.finish()
        for frame in self.frames.values():frame.setGeometry(self.rect())
