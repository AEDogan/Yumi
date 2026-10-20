"""Eight frameless resize handles using the platform's normal resize operation."""
from PySide6.QtCore import Qt,QObject,QEvent,QRect
from PySide6.QtWidgets import QWidget

def system_resize(window,edges):
    handle=window.windowHandle()
    return bool(handle and handle.startSystemResize(edges))

class EdgeGrip(QWidget):
    def __init__(self,window,edges):
        super().__init__(window);self.edges=edges;self.start=None
        self.setObjectName('windowResizeGrip');self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        horizontal=bool(edges&(Qt.Edge.LeftEdge|Qt.Edge.RightEdge))
        vertical=bool(edges&(Qt.Edge.TopEdge|Qt.Edge.BottomEdge))
        diagonal=edges in (Qt.Edge.TopEdge|Qt.Edge.LeftEdge,Qt.Edge.BottomEdge|Qt.Edge.RightEdge)
        self.setCursor(Qt.CursorShape.SizeFDiagCursor if horizontal and vertical and diagonal else
            Qt.CursorShape.SizeBDiagCursor if horizontal and vertical else
            Qt.CursorShape.SizeHorCursor if horizontal else Qt.CursorShape.SizeVerCursor)
    def mousePressEvent(self,event):
        if event.button()!=Qt.MouseButton.LeftButton:return super().mousePressEvent(event)
        window=self.window()
        if not system_resize(window,self.edges):
            self.start=(event.globalPosition().toPoint(),window.geometry());self.grabMouse()
        event.accept()
    def mouseMoveEvent(self,event):
        if self.start is None:return super().mouseMoveEvent(event)
        point,initial=self.start;delta=event.globalPosition().toPoint()-point;rect=QRect(initial);w=self.window()
        if self.edges&Qt.Edge.LeftEdge:rect.setLeft(min(initial.left()+delta.x(),initial.right()-w.minimumWidth()+1))
        if self.edges&Qt.Edge.RightEdge:rect.setRight(max(initial.right()+delta.x(),initial.left()+w.minimumWidth()-1))
        if self.edges&Qt.Edge.TopEdge:rect.setTop(min(initial.top()+delta.y(),initial.bottom()-w.minimumHeight()+1))
        if self.edges&Qt.Edge.BottomEdge:rect.setBottom(max(initial.bottom()+delta.y(),initial.top()+w.minimumHeight()-1))
        w.setGeometry(rect);event.accept()
    def mouseReleaseEvent(self,event):
        if self.start is not None:self.start=None;self.releaseMouse()
        event.accept()

class WindowResize(QObject):
    def __init__(self,window):
        super().__init__(window);self.window=window
        L,R,T,B=Qt.Edge.LeftEdge,Qt.Edge.RightEdge,Qt.Edge.TopEdge,Qt.Edge.BottomEdge
        self.handles=[EdgeGrip(window,edges) for edges in (L,R,T,B,L|T,R|T,L|B,R|B)]
        window.installEventFilter(self);self.layout_handles()
    def eventFilter(self,obj,event):
        if event.type() in (QEvent.Type.Resize,QEvent.Type.Show,QEvent.Type.WindowStateChange):self.layout_handles()
        return False
    def layout_handles(self):
        w,h=self.window.width(),self.window.height();edge=6;corner=12
        rects=[(0,corner,edge,max(0,h-2*corner)),(w-edge,corner,edge,max(0,h-2*corner)),
            (corner,0,max(0,w-2*corner),edge),(corner,h-edge,max(0,w-2*corner),edge),
            (0,0,corner,corner),(w-corner,0,corner,corner),(0,h-corner,corner,corner),(w-corner,h-corner,corner,corner)]
        for grip,rect in zip(self.handles,rects):
            grip.setGeometry(*rect);grip.setVisible(not self.window.isMaximized() and not self.window.isFullScreen());grip.raise_()
