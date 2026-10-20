"""Current-user Windows startup registration, changed only by Settings save."""
from pathlib import Path
import subprocess

RUN_KEY=r'Software\Microsoft\Windows\CurrentVersion\Run'
VALUE='Yumi'

def command():
    root=Path(__file__).resolve().parent
    executable=root/'.venv/Scripts/pythonw.exe';launcher=root/'launch.py'
    if not executable.is_file() or not launcher.is_file():raise OSError('Yumi başlatıcısı bulunamadı.')
    return subprocess.list2cmdline([str(executable),str(launcher)])

def enabled():
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,RUN_KEY) as key:
            return winreg.QueryValueEx(key,VALUE)[0]==command()
    except FileNotFoundError:return False

def set_enabled(value):
    import winreg
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER,RUN_KEY,0,winreg.KEY_SET_VALUE) as key:
        if value:winreg.SetValueEx(key,VALUE,0,winreg.REG_SZ,command())
        else:
            try:winreg.DeleteValue(key,VALUE)
            except FileNotFoundError:pass
    if enabled()!=bool(value):raise OSError('Windows başlangıç ayarı doğrulanamadı.')
