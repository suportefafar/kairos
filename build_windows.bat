@echo off
setlocal
py -3.8 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
pyinstaller --clean --noconfirm --onefile --noconsole --name Kairos kairos_agent.py
if errorlevel 1 exit /b 1
if not exist "dist\Kairos.exe" exit /b 1

set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
  echo Inno Setup 6 was not found. Install it, then run this script again.
  exit /b 2
)

"%ISCC%" installer\Kairos.iss
if errorlevel 1 exit /b 1
echo Installer created at installer\output\Kairos-Setup.exe
