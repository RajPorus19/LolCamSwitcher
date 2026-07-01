@echo off
REM Build Windows client agent .exe (for gaming PCs)
pip install -r requirements.txt
pyinstaller build-client.spec --noconfirm
echo.
echo Done! Client executable: dist\LolCamSwitcherClient.exe
pause
