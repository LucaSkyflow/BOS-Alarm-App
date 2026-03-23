@echo off
echo === BOS Alarm Build ===
echo.
echo Installing dependencies...
pip install -r requirements.txt pyinstaller
echo.
echo Building EXE...
pyinstaller bos_alarm_v2.spec --noconfirm
echo.
echo Done! EXE is in dist\BOS Alarm\
pause
