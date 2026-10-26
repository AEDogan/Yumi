"""Procedural 3D chibi avatar and small animated stage props."""
from __future__ import annotations

import math
import time
from pathlib import Path
import numpy as np
from motion import MotionRig
from vrm import VRMModel
from skins import skin_path

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtGui import QSurfaceFormat
from three_vrm_view import ThreeVRMView  # establishes shared GL contexts before QApplication

# Qt top-level composition must use the same nonblocking swap policy.
_frame_format=QSurfaceFormat.defaultFormat();_frame_format.setSwapInterval(0);QSurfaceFormat.setDefaultFormat(_frame_format)
from OpenGL.GL import *
from OpenGL.GLU import gluLookAt, gluNewQuadric, gluPerspective, gluSphere


SKIN = (1.0,.85,.78)
WHITE = (1,1,1)


def color(rgb):
    glColor3f(*rgb)


def sphere(quad, rgb, xyz, scale):
    glPushMatrix()
    glTranslatef(*xyz)
    glScalef(*scale)
    color(rgb)
    gluSphere(quad, 1, 20, 14)
    glPopMatrix()


def segment(quad,rgb,start,end,radius):
    import numpy as np
    delta=np.asarray(end)-np.asarray(start);length=float(np.linalg.norm(delta))
    if length<1e-5:return
    center=(np.asarray(start)+np.asarray(end))*.5
    direction=delta/length;axis=np.cross([0.,1.,0.],direction)
    glPushMatrix();glTranslatef(*center)
    if np.linalg.norm(axis)>1e-6:glRotatef(math.degrees(math.acos(max(-1,min(1,float(direction[1]))))),*axis)
    elif direction[1]<0:glRotatef(180,1,0,0)
    glScalef(radius,length*.5+radius*.35,radius);color(rgb);gluSphere(quad,1,14,10);glPopMatrix()

def box(rgb, xyz, size):
    x,y,z=xyz; w,h,d=(v/2 for v in size)
    glPushMatrix(); glTranslatef(x,y,z); color(rgb)
    glBegin(GL_QUADS)
    for normal, verts in [
        ((0,0,1), [(-w,-h,d),(w,-h,d),(w,h,d),(-w,h,d)]),
        ((0,0,-1), [(w,-h,-d),(-w,-h,-d),(-w,h,-d),(w,h,-d)]),
        ((0,1,0), [(-w,h,d),(w,h,d),(w,h,-d),(-w,h,-d)]),
        ((0,-1,0), [(-w,-h,-d),(w,-h,-d),(w,-h,d),(-w,-h,d)]),
        ((1,0,0), [(w,-h,d),(w,-h,-d),(w,h,-d),(w,h,d)]),
        ((-1,0,0), [(-w,-h,-d),(-w,-h,d),(-w,h,d),(-w,h,-d)])]:
        glNormal3f(*normal)
        for vertex in verts: glVertex3f(*vertex)
    glEnd(); glPopMatrix()


class AvatarView(QOpenGLWidget):
    simulationStep=Signal(float)
    runtimeWarning=Signal(str)
    def __init__(self, parent=None, transparent=False):
        super().__init__(parent)
        self.setUpdateBehavior(QOpenGLWidget.UpdateBehavior.PartialUpdate)
        self.transparent = transparent
        self.fps_limit=197;self.next_frame=0.;self.subpixel_x=0.
        fmt=QSurfaceFormat(); fmt.setSwapInterval(0); fmt.setAlphaBufferSize(8); fmt.setSamples(4); fmt.setVersion(2,1); fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CompatibilityProfile); self.setFormat(fmt)
        if transparent:
            import os
            if os.environ.get('YUMI_DESKTOP_RENDERER','three-vrm')=='legacy':self.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop)
        self.setMinimumHeight(300)
        self._skin = None
        self.clippy=None;self.clippy_state='idle'
        self.model=None
        self.furniture=None;self.previous_chair=None
        self.model_error=None
        self.reported_runtime_error=None
        self.pose = 'idle'
        self.walk_direction=-1
        self.render_scale=1.;self.render_angles=(0.,0.,0.)
        self.prop = 'none'
        self.speaking = False
        self.hand_gesture=None
        self.mouth_level = 0.
        from conversation_motion import ConversationMotion
        self.conversation=ConversationMotion();self.facing_mix=0.
        from roaming import YawTurn
        self.yaw=YawTurn();self.walking_turn=False
        self.scene_mix = 0.0
        self.clock = time.perf_counter()
        self.frame_clock=self.clock
        self.render_paused=False;self.render_was_active=False;self.render_pause_started=0.
        self.quad = None
        self.rig=MotionRig()
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._request_frame)
        self.timer.start(0)
        self.three_desktop=None
        if transparent:
            import os
            if os.environ.get('YUMI_DESKTOP_RENDERER','three-vrm')!='legacy':
                from desktop_vrm import DesktopVRM
                self.three_desktop=DesktopVRM(self)

    def _request_frame(self):
        if self.render_paused:return
        if not self.isVisible():self.timer.start(100);return
        now=time.perf_counter();remaining=self.next_frame-now
        if remaining>0:
            self.timer.start(max(0,int(remaining*1000)));return
        self.next_frame=now+1/max(30,min(197,self.fps_limit))
        self.update();self.timer.start(5)

    def set_render_paused(self,paused):
        if paused==self.render_paused:return
        self.render_paused=paused
        if self.three_desktop:self.three_desktop.pause(paused)
        if paused:
            self.render_pause_started=time.perf_counter();self.render_was_active=self.timer.isActive();self.timer.stop()
        else:
            now=time.perf_counter();self.clock+=now-self.render_pause_started;self.frame_clock=now;self.next_frame=0.
            if self.render_was_active:self.timer.start(0)

    @property
    def skin(self):return self._skin

    @skin.setter
    def skin(self,key):
        from skins import valid_skin,default_skin
        if not valid_skin(key):key=default_skin()
        if key==self._skin:return
        from clippy_character import ClippyCharacter
        clippy=ClippyCharacter() if key=='Clippy' else None
        path=skin_path(key)
        model=VRMModel(path) if path else None
        if key.startswith('vrm:') and path is None:raise ValueError('Seçilen VRM modeli bulunamadı.')
        if self.model and self.isValid():
            self.makeCurrent()
            if self.furniture:self.furniture.release();self.furniture=None
            self.model.release();self.doneCurrent()
        self.clippy=clippy
        self.model=model;self._skin=key;self.model_error=None;self.reported_runtime_error=None
        self.update()

    def initializeGL(self):
        glClearColor(0,0,0,0) if self.transparent else glClearColor(.96,.91,.99,1)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        glEnable(GL_NORMALIZE)
        glShadeModel(GL_SMOOTH)
        glLightfv(GL_LIGHT0, GL_POSITION, [-3,5,6,1])
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [.72,.72,.72,1])
        glLightfv(GL_LIGHT0, GL_AMBIENT, [.30,.28,.33,1])
        self.quad = gluNewQuadric()

    def resizeGL(self, width, height):
        glViewport(0,0,width,max(1,height))

    def sit(self,mode='lounge'):
        if self.furniture:return
        if not self.model:raise ValueError('Oturmak için bir VRM karakter seç.')
        from furniture_scene import FurnitureScene
        self.furniture=FurnitureScene(self.model,self.previous_chair,mode=mode)
        self.furniture.current_angle=self.yaw.angle
        self.previous_chair=self.furniture.fit.item['id']

    def stand(self):
        if self.furniture:self.furniture.request_exit()

    def paintGL(self):
        if self.render_paused or self.quad is None:return
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glMatrixMode(GL_PROJECTION);glLoadIdentity()
        gluPerspective(35,max(.2,self.width()/max(1,self.height())),.1,40)
        glMatrixMode(GL_MODELVIEW);glLoadIdentity()
        gluLookAt(0,1.8,8.5,0,1.47,0,0,1,0)
        t=time.perf_counter()-self.clock
        now=time.perf_counter();dt=min(.10,now-self.frame_clock);self.frame_clock=now
        self.simulationStep.emit(dt)
        if self.clippy is not None:
            if self.three_desktop:self.three_desktop.begin()
            self.clippy.advance('speaking' if self.speaking else self.clippy_state)
            from PySide6.QtGui import QPainter
            painter=QPainter(self)
            self.clippy.draw(painter,self.rect());painter.end()
            return
        if self.pose not in ('idle','walk','wave','listen','clip'):self.pose='idle'
        scene=self.furniture
        three_ready=self.three_desktop.begin() if self.three_desktop else False
        scene_angle=scene.step(dt) if scene else None
        pose=scene.pose if scene else self.pose
        if self.model:
            self.model.external_renderer=three_ready
            if scene:scene.contacts.update()
            self.model.mouth_level=self.mouth_level;self.model.conversation=self.conversation;self.model.hand_gesture=self.hand_gesture
            if self.conversation.fitted_data is not self.model.data:
                self.conversation.fit(self.model.rest_canonical,self.model.data,self.model.hair_springs.physics)
            self.model.frame(t,pose,0.,self.speaking,0.)
            runtime_error=self.model.hair_springs.runtime_error
            if runtime_error and runtime_error!=self.reported_runtime_error:
                self.reported_runtime_error=runtime_error
                self.runtimeWarning.emit('Karakterin ikincil fiziği başlatılamadı; kaynak görünümü korunuyor. '+runtime_error)
        self.facing_mix+=(float(self.speaking)-self.facing_mix)*(1-math.exp(-dt/.22))
        target=(90*self.walk_direction if self.pose=='walk' or self.walking_turn else math.sin(t*.5)*4)*(1-self.facing_mix)
        angle=scene_angle if scene else self.yaw.advance(target,dt,self.model is not None)
        if scene:self.yaw.angle=angle
        self.render_scale=1.;self.render_angles=(angle,0.,0.)
        frame_center=0.
        if scene:
            from scene_framing import scene_bounds,fit_frame
            aspect=self.width()/max(1,self.height())
            if getattr(scene,'_framing_aspect',None)!=aspect:
                scene._framing_fit=fit_frame(scene_bounds(scene),scene.floor_points(),aspect)
                scene._framing_aspect=aspect
            scale,center=scene._framing_fit
            self.render_scale=1.+(scale-1.)*scene.visibility
            frame_center=center*scene.visibility
        pole_floor=None
        if self.model and not scene and getattr(self.model,'music_clip_time',None) is not None and (getattr(self.model.clip,'pole',False) or getattr(self.model.clip,'uses_stage_bounds',False)) and callable(getattr(self.model.clip,'frame_bounds',None)):
            from scene_framing import fit_frame
            motion=self.model.clip;aspect=self.width()/max(1,self.height())
            key=(id(motion),id(self.model.data),aspect)
            if getattr(self,'pole_frame_key',None)!=key:
                points,floor=motion.frame_bounds(self.model.data)
                self.pole_frame_fit=fit_frame(points,floor,aspect);self.pole_frame_floor=floor;self.pole_frame_key=key
            scale,center=self.pole_frame_fit;visible=motion.presence(self.model.music_clip_time)
            self.render_scale=1+(scale-1)*visible;frame_center=center*visible;pole_floor=self.pole_frame_floor
        glPushMatrix()
        if self.model and (pose!='clip' or getattr(self.model,'music_clip_time',None) is not None):
            from grounding import projected_floor_offset,UP
            if scene:
                from furniture_scene import rotation
                points=self.model.ground.points@rotation(angle).T+scene.position
                # Furniture and soles share one floor transform. Include the
                # front furniture footprint so legs never slip below the taskbar.
                floor=scene.floor_points()
                points=(points-[frame_center,0.,0.])*self.render_scale
                floor=(floor-[frame_center,0.,0.])*self.render_scale
                base=projected_floor_offset(points,0.)
                offset=base+(projected_floor_offset(np.concatenate((points,floor)),0.)-base)*scene.visibility
            elif pole_floor is not None:
                from furniture_scene import rotation
                points=self.model.ground.points@rotation(angle).T
                floor=pole_floor@rotation(angle).T
                points=(points-[frame_center,0.,0.])*self.render_scale
                floor=(floor-[frame_center,0.,0.])*self.render_scale
                base=projected_floor_offset(points,0.)
                visible=self.model.clip.presence(self.model.music_clip_time)
                offset=base+(projected_floor_offset(np.concatenate((points,floor)),0.)-base)*visible
            else:offset=projected_floor_offset(self.model.ground.points,angle)
            glTranslatef(*(UP*offset))
        if self.subpixel_x:
            glTranslatef(self.subpixel_x*2*8.5*math.tan(math.radians(35)/2)/max(1,self.height()),0,0)
        glScalef(self.render_scale,self.render_scale,self.render_scale)
        glTranslatef(-frame_center,0.,0.)
        if scene:
            if three_ready:
                with self.three_desktop.capture_props():scene.draw()
            else:scene.draw()
            glTranslatef(*scene.position)
        glRotatef(angle,0,1,0)
        if self.model:
            motion=self.model.clip;music_time=getattr(self.model,'music_clip_time',None)
            if music_time is not None and getattr(motion,'pole',False):
                point,height,radius=motion.pole_spec(self.model.data)
                visible=motion.presence(music_time)
                from OpenGL.GLU import gluCylinder,gluDisk
                if three_ready:self.three_desktop.pole(point,height,radius,visible,np.asarray(glGetDoublev(GL_MODELVIEW_MATRIX),float).T)
                else:
                    glPushMatrix();glTranslatef(*point);glScalef(visible,visible,visible)
                    color((.62,.68,.74));glRotatef(-90,1,0,0)
                    gluCylinder(self.quad,radius,radius,height,20,1)
                    gluDisk(self.quad,0.,radius*3.5,20,1)
                    glTranslatef(0,0,height);gluDisk(self.quad,0.,radius,20,1);glPopMatrix()
        if self.model and three_ready:
            self.three_desktop.submit(np.asarray(glGetDoublev(GL_MODELVIEW_MATRIX),float).T)
            # Keep the native model until the new renderer has an actual frame.
            if not self.three_desktop.delivered:self.model.draw()
        elif self.model:self.model.draw()
        glPopMatrix()
        if scene and scene.done:scene.release();self.furniture=None
