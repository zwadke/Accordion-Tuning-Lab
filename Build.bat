@echo off
setlocal
cd /d "%~dp0"
py -3.12 -m venv .buildenv || goto fail
set "PY=.buildenv\Scripts\python.exe"
"%PY%" -m pip install numpy sounddevice mido python-rtmidi pyinstaller || goto fail
"%PY%" -m PyInstaller --noconfirm --clean --onefile --windowed --name Accordion_Tuning_Lab --icon Accordion.ico --add-data "Profiles;Profiles" --collect-all sounddevice --collect-all _sounddevice_data --hidden-import mido.backends.rtmidi --hidden-import rtmidi Accordion_Tuning_Lab.py || goto fail
set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (echo Install Inno Setup 6, then run Build.bat again.& goto fail)
"%ISCC%" Setup.iss || goto fail
echo Done. See dist and Output folders.
pause
exit /b 0
:fail
echo Build failed. See messages above.
pause
exit /b 1
