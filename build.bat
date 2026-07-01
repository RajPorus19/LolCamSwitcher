@echo off
REM Build LolCamSwitcher as Windows .exe
REM Requires: Python 3.10+, pip install -r requirements.txt

echo Installing dependencies...
pip install -r requirements.txt

echo Building executable...
pyinstaller build.spec --noconfirm

echo.
echo Done! Executable: dist\LolCamSwitcher.exe
pause
