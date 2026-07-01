@echo off
REM Build LoL Auto Director as Windows .exe
REM Requires: Python 3.10+, pip install -r requirements.txt

echo Installing dependencies...
pip install -r requirements.txt

echo Building executable...
pyinstaller build.spec --noconfirm

echo.
echo Done! Executable: dist\LoLAutoDirector.exe
pause
