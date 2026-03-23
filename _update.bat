@echo off
:: BOS Alarm — Auto-Update Script
:: Usage: _update.bat <source_dir> <app_dir>
:: Called by updater.py after downloading + extracting the new version.

set SOURCE=%~1
set TARGET=%~2

echo Warte auf App-Beendigung...
timeout /t 3 /nobreak >nul

echo Kopiere Update...
xcopy "%SOURCE%\*" "%TARGET%\" /E /Y /Q >nul

echo Starte App neu...
start "" "%TARGET%\BOS Alarm.exe"

echo Update abgeschlossen.
