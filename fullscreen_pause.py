"""Suspend avatar work for foreground full-screen games, without reading window contents."""
import ctypes
from ctypes import wintypes as w
import os,time
from pathlib import PureWindowsPath
from PySide6.QtCore import QObject,QTimer,QAbstractAnimation

MEDIA_APPS={'chrome.exe','msedge.exe','firefox.exe','brave.exe','opera.exe','vlc.exe','mpv.exe','potplayer64.exe','wmplayer.exe','netflix.exe'}
GAME_FOLDERS=('/steamapps/common/','/epic games/','/epicgames/','/riot games/','/xboxgames/','/gog galaxy/games/')

def game_candidate(executable,d3d_fullscreen=False,extra_names=()):
    path=str(executable).replace('\\','/').casefold()
    name=PureWindowsPath(path).name
    if name in {str(value).casefold() for value in extra_names}:return True
    if name in MEDIA_APPS:return False
    return d3d_fullscreen or any(folder in path for folder in GAME_FOLDERS)

def covers_monitor(client,monitor,tolerance=2):
    left,top,right,bottom=client;ml,mt,mr,mb=monitor
    return right>left and bottom>top and left<=ml+tolerance and top<=mt+tolerance and right>=mr-tolerance and bottom>=mb-tolerance

class MonitorInfo(ctypes.Structure):
    _fields_=[('cbSize',w.DWORD),('rcMonitor',w.RECT),('rcWork',w.RECT),('dwFlags',w.DWORD)]

class ForegroundGame:
    def __init__(self):
        self.user=ctypes.WinDLL('user32',use_last_error=True)
        self.shell=ctypes.WinDLL('shell32',use_last_error=True)
        self.user.GetForegroundWindow.restype=w.HWND
        self.user.GetWindowThreadProcessId.argtypes=[w.HWND,ctypes.POINTER(w.DWORD)]
        self.user.IsIconic.argtypes=[w.HWND];self.user.IsIconic.restype=w.BOOL
        self.user.GetClientRect.argtypes=[w.HWND,ctypes.POINTER(w.RECT)];self.user.GetClientRect.restype=w.BOOL
        self.user.ClientToScreen.argtypes=[w.HWND,ctypes.POINTER(w.POINT)];self.user.ClientToScreen.restype=w.BOOL
        self.user.MonitorFromWindow.argtypes=[w.HWND,w.DWORD];self.user.MonitorFromWindow.restype=w.HANDLE
        self.user.GetMonitorInfoW.argtypes=[w.HANDLE,ctypes.POINTER(MonitorInfo)];self.user.GetMonitorInfoW.restype=w.BOOL
        self.shell.SHQueryUserNotificationState.argtypes=[ctypes.POINTER(ctypes.c_int)];self.shell.SHQueryUserNotificationState.restype=ctypes.c_long
        self.cached_pid=None;self.cached_exe='';self.cache_until=0.
    def __call__(self,settings):
        handle=self.user.GetForegroundWindow()
        if not handle or self.user.IsIconic(handle):return False
        pid=w.DWORD();self.user.GetWindowThreadProcessId(handle,ctypes.byref(pid))
        if not pid.value or pid.value==os.getpid():return False
        rect=w.RECT();point=w.POINT();info=MonitorInfo();info.cbSize=ctypes.sizeof(info)
        monitor=self.user.MonitorFromWindow(handle,0)
        if not monitor or not self.user.GetClientRect(handle,ctypes.byref(rect)) or not self.user.ClientToScreen(handle,ctypes.byref(point)) or not self.user.GetMonitorInfoW(monitor,ctypes.byref(info)):return False
        client=(point.x,point.y,point.x+rect.right,point.y+rect.bottom)
        full=(info.rcMonitor.left,info.rcMonitor.top,info.rcMonitor.right,info.rcMonitor.bottom)
        if not covers_monitor(client,full):return False
        if self.cached_pid!=pid.value or time.monotonic()>self.cache_until:
            import psutil
            try:self.cached_exe=psutil.Process(pid.value).exe()
            except (psutil.Error,OSError):self.cached_exe=''
            self.cached_pid=pid.value;self.cache_until=time.monotonic()+3.
        state=ctypes.c_int()
        d3d=self.shell.SHQueryUserNotificationState(ctypes.byref(state))==0 and state.value==3
        return game_candidate(self.cached_exe,d3d,settings.get('fullscreen_game_names',()))

class FullscreenPause(QObject):
    def __init__(self,owner,probe=None):
        super().__init__(owner);self.owner=owner;self.probe=probe or ForegroundGame()
        self.paused=False;self.clear_samples=0;self.saved_timers=[]
        self.timer=QTimer(self);self.timer.setInterval(750);self.timer.timeout.connect(self.poll);self.timer.start()
    def poll(self):
        if self.owner.exiting:return
        try:active=self.probe(self.owner.settings)
        except (OSError,ValueError):return
        if active:self.clear_samples=0;self.set_paused(True)
        elif self.paused:
            self.clear_samples+=1
            if self.clear_samples>=2:self.set_paused(False)
    def set_paused(self,value):
        if value==self.paused:return
        self.paused=value;owner=self.owner
        runtime=getattr(owner,'music_runtime',None)
        if runtime:runtime.output.paused=value
        director=getattr(owner,'daily_director',None)
        if director and not value:
            director.suppressed_until=time.perf_counter()+30.;director.candidate=None
        if value:
            self.started=time.perf_counter();self.overlay_visible=owner.overlay.isVisible();self.window_visible=owner.isVisible()
            self.saved_timers=[(timer,timer.interval()) for timer in (owner.tick,owner.roam_tick,owner.overlay.mask_timer,owner.overlay.hit_timer) if timer.isActive()]
            for timer,_ in self.saved_timers:timer.stop()
            self.moving=owner.move_animation.state()==QAbstractAnimation.State.Running
            if self.moving:owner.move_animation.pause()
            owner.avatar.set_render_paused(True);owner.overlay.avatar.set_render_paused(True)
            owner.overlay.hide();owner.hide()
        else:
            elapsed=time.perf_counter()-self.started
            owner.roam_clock=time.perf_counter();owner.last_render_movement=0.
            if owner.manual_pose_end:owner.manual_pose_end+=elapsed
            model_visible=owner.settings.get('model_visible',True)
            if self.overlay_visible and model_visible:owner.overlay.show()
            if self.window_visible:owner.show()
            owner.avatar.set_render_paused(not model_visible);owner.overlay.avatar.set_render_paused(not model_visible)
            for timer,interval in self.saved_timers:timer.start(interval)
            if self.moving:owner.move_animation.resume()
            self.saved_timers=[];owner.overlay.sync()
    def shutdown(self):self.timer.stop()
