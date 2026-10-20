"""OS-owned single microphone worker lease; no stale lock file after a crash."""
import ctypes
from ctypes import wintypes
from live_core import LiveError
class MicrophoneLease:
    def __init__(self):
        self.api=ctypes.WinDLL('kernel32',use_last_error=True)
        self.api.CreateMutexW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.LPCWSTR];self.api.CreateMutexW.restype=wintypes.HANDLE
        self.api.CloseHandle.argtypes=[wintypes.HANDLE];self.api.CloseHandle.restype=wintypes.BOOL
        self.handle=self.api.CreateMutexW(None,False,'Local\\YumiNativeMicrophoneWorker')
        error=ctypes.get_last_error()
        if not self.handle:raise LiveError('Mikrofon oturum kilidi oluşturulamadı.',code='microphone_lease_failed')
        if error==183:
            self.close();raise LiveError('Başka bir Yumi canlı mikrofon oturumu açık; ikinci oturum açılmadı.',code='microphone_already_active')
    def close(self):
        if self.handle:self.api.CloseHandle(self.handle);self.handle=None
