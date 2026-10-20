@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" python -m venv .venv
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto fail
.venv\Scripts\python.exe setup_local.py
if errorlevel 1 goto fail
echo Kurulum tamamlandi. BASLAT.cmd ile acabilirsiniz.
exit /b 0
:fail
echo Kurulum tamamlanamadi. Internet ve Python kurulumunu kontrol edin.
pause
exit /b 1
