@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" call KURULUM.cmd
if not exist "models\vosk-model-small-tr-0.3\am\final.mdl" call KURULUM.cmd
if not exist "models\whisper-small\model.bin" call KURULUM.cmd
if not exist ".venv\Scripts\pythonw.exe" exit /b 1
start "Yumi" ".venv\Scripts\pythonw.exe" "%~dp0launch.py"
