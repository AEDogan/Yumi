"""Nonblocking alpha readback for the desktop hit region (GPU PBO + fence)."""
import ctypes
from OpenGL.GL import *
from OpenGL.raw.GL.VERSION.GL_1_0 import glReadPixels as raw_read_pixels
from PySide6.QtGui import QImage
class AsyncMask:
 def __init__(self):self.size=None;self.pbo=0;self.fbo=0;self.texture=0;self.fence=None
 def release(self):
  if self.fence:glDeleteSync(self.fence);self.fence=None
  if self.pbo:glDeleteBuffers(1,[self.pbo])
  if self.fbo:glDeleteFramebuffers(1,[self.fbo])
  if self.texture:glDeleteTextures([self.texture])
  self.pbo=self.fbo=self.texture=0;self.size=None
 def capture(self,view):
  if not bool(glFenceSync):raise RuntimeError('Async readback is unavailable')
  ratio=view.devicePixelRatioF();size=(round(view.width()*ratio),round(view.height()*ratio));width,height=size
  if width<1 or height<1:return None
  old_read=int(glGetIntegerv(GL_READ_FRAMEBUFFER_BINDING));old_draw=int(glGetIntegerv(GL_DRAW_FRAMEBUFFER_BINDING));old_texture=int(glGetIntegerv(GL_TEXTURE_BINDING_2D));old_pack=int(glGetIntegerv(GL_PIXEL_PACK_BUFFER_BINDING))
  result=None
  try:
   if self.size!=size:
    self.release();self.size=size;self.pbo=int(glGenBuffers(1));glBindBuffer(GL_PIXEL_PACK_BUFFER,self.pbo);glBufferData(GL_PIXEL_PACK_BUFFER,width*height*4,None,GL_STREAM_READ)
    self.fbo=int(glGenFramebuffers(1));self.texture=int(glGenTextures(1));glBindTexture(GL_TEXTURE_2D,self.texture);glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA8,width,height,0,GL_RGBA,GL_UNSIGNED_BYTE,None)
    glBindFramebuffer(GL_DRAW_FRAMEBUFFER,self.fbo);glFramebufferTexture2D(GL_DRAW_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,self.texture,0)
    if glCheckFramebufferStatus(GL_DRAW_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE:raise RuntimeError('Readback framebuffer incomplete')
   if self.fence:
    status=glClientWaitSync(self.fence,0,0)
    if status in (GL_ALREADY_SIGNALED,GL_CONDITION_SATISFIED):
     glBindBuffer(GL_PIXEL_PACK_BUFFER,self.pbo);raw=bytes(glGetBufferSubData(GL_PIXEL_PACK_BUFFER,0,width*height*4))
     result=QImage(raw,width,height,width*4,QImage.Format.Format_RGBA8888).mirrored(False,True)
     glDeleteSync(self.fence);self.fence=None
    elif status==GL_WAIT_FAILED:raise RuntimeError('Readback fence failed')
   if self.fence is None:
    glBindFramebuffer(GL_READ_FRAMEBUFFER,view.defaultFramebufferObject());glBindFramebuffer(GL_DRAW_FRAMEBUFFER,self.fbo)
    glBlitFramebuffer(0,0,width,height,0,0,width,height,GL_COLOR_BUFFER_BIT,GL_NEAREST)
    glBindFramebuffer(GL_READ_FRAMEBUFFER,self.fbo);glBindBuffer(GL_PIXEL_PACK_BUFFER,self.pbo)
    raw_read_pixels(0,0,width,height,GL_RGBA,GL_UNSIGNED_BYTE,ctypes.c_void_p(0))
    self.fence=glFenceSync(GL_SYNC_GPU_COMMANDS_COMPLETE,0);glFlush()
  finally:
   glBindBuffer(GL_PIXEL_PACK_BUFFER,old_pack);glBindTexture(GL_TEXTURE_2D,old_texture);glBindFramebuffer(GL_READ_FRAMEBUFFER,old_read);glBindFramebuffer(GL_DRAW_FRAMEBUFFER,old_draw)
  return result
