"""Single instance launcher with crash logs for windowless startup."""
import ctypes,logging,os,sys
from ctypes import wintypes
from pathlib import Path
from app_paths import ROOT as root,APP_ID,data_dir
logs=data_dir()
logs.mkdir(parents=True,exist_ok=True)
logging.basicConfig(filename=logs/'yumi.log',level=logging.WARNING,format='%(asctime)s %(levelname)s %(message)s')
# app.main owns the only QApplication and handles local-socket activation.
ctypes.windll.kernel32.CreateMutexW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.LPCWSTR]
ctypes.windll.kernel32.CreateMutexW.restype=wintypes.HANDLE
ctypes.windll.kernel32.CloseHandle.argtypes=[wintypes.HANDLE]
mutex=ctypes.windll.kernel32.CreateMutexW(None,False,'Local\\'+APP_ID)
if ctypes.windll.kernel32.GetLastError()==183:
    # Existing instance holds the mutex. Restore existing window:
    hwnd = ctypes.windll.user32.FindWindowW(None, 'Yumi · 3D Masaüstü Asistanı')
    if hwnd:
        ctypes.windll.user32.ShowWindow(hwnd, 9)
        ctypes.windll.user32.SetForegroundWindow(hwnd)
        sys.exit(0)
    hwnd_char = ctypes.windll.user32.FindWindowW(None, 'Yumi · Masaüstü karakteri')
    if hwnd_char:
        ctypes.windll.user32.ShowWindow(hwnd_char, 9)
        ctypes.windll.user32.SetForegroundWindow(hwnd_char)
        sys.exit(0)
try:
    from startup_runtime import prepare_audio_runtime,guard_startup
    guard_startup(str(logs))
    from resource_guard import MemoryJob,GiB,require_capacity
    require_capacity(2*GiB)
    memory_job=MemoryJob(6*GiB,4*GiB)
    memory_job.attach()
    logging.getLogger("yumi.startup").info("Memory limits attached; preparing audio")
    prepare_audio_runtime()
    logging.getLogger("yumi.startup").info("Audio ready; importing desktop application")
    from app import main
    sys.exit(main())
except Exception:
    logging.exception('Yumi startup failure')
    ctypes.windll.user32.MessageBoxW(None,f'Yumi açılamadı. Hata kaydı: {logs / "yumi.log"}','Yumi',16)
finally:
    if mutex:ctypes.windll.kernel32.CloseHandle(mutex)
