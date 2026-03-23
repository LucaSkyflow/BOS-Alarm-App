@echo off
:: BOS Alarm — Auto-Update Script
:: Usage: _update.bat <source_dir> <app_dir>
:: Called by updater.py after downloading + extracting the new version.
:: This script is copied to %TEMP% before execution so it won't be
:: overwritten during the update.

set SOURCE=%~1
set TARGET=%~2
set LOGFILE=%TARGET%\update.log

echo [%date% %time%] Update gestartet > "%LOGFILE%"
echo [%date% %time%] Quelle: %SOURCE% >> "%LOGFILE%"
echo [%date% %time%] Ziel: %TARGET% >> "%LOGFILE%"

:: Wait for the app process to exit
echo [%date% %time%] Warte auf App-Beendigung... >> "%LOGFILE%"
set RETRIES=0
:wait_loop
if %RETRIES% GEQ 30 (
    echo [%date% %time%] WARNUNG: Timeout nach 30s >> "%LOGFILE%"
    goto do_copy
)
timeout /t 1 /nobreak >nul
tasklist /FI "IMAGENAME eq BOS Alarm.exe" 2>nul | find /I "BOS Alarm.exe" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [%date% %time%] App beendet (nach %RETRIES%s) >> "%LOGFILE%"
    goto do_copy
)
set /a RETRIES+=1
goto wait_loop

:do_copy
:: Small extra delay to ensure file handles are released
timeout /t 2 /nobreak >nul

echo [%date% %time%] Kopiere Update... >> "%LOGFILE%"
xcopy "%SOURCE%\*" "%TARGET%\" /E /Y /Q >> "%LOGFILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [%date% %time%] FEHLER beim Kopieren! Errorlevel: %ERRORLEVEL% >> "%LOGFILE%"
    exit /b 1
)
echo [%date% %time%] Kopieren erfolgreich >> "%LOGFILE%"

:: Verify exe exists
if not exist "%TARGET%\BOS Alarm.exe" (
    echo [%date% %time%] FEHLER: BOS Alarm.exe nicht gefunden nach Update >> "%LOGFILE%"
    exit /b 1
)

:: Start app
echo [%date% %time%] Starte App neu... >> "%LOGFILE%"
start "" /D "%TARGET%" "%TARGET%\BOS Alarm.exe"
echo [%date% %time%] Start-Befehl ausgefuehrt (exitcode=%ERRORLEVEL%) >> "%LOGFILE%"

:: Clean up temp files
timeout /t 2 /nobreak >nul
if exist "%SOURCE%" rmdir /S /Q "%SOURCE%" >nul 2>&1

echo [%date% %time%] Update abgeschlossen >> "%LOGFILE%"
exit /b 0
