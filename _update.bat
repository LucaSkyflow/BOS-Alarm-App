@echo off
:: BOS Alarm — Auto-Update Script
:: Usage: _update.bat <source_dir> <app_dir>
:: Called by updater.py after downloading + extracting the new version.
:: This script is copied to %TEMP% before execution so it won't be
:: overwritten during the update.

set SOURCE=%~1
set TARGET=%~2

echo ============================================
echo   BOS Alarm — Update wird installiert...
echo ============================================
echo.
echo   Quelle: %SOURCE%
echo   Ziel:   %TARGET%
echo.

:: Wait for the app to fully exit (check if exe is still locked)
echo   Warte auf App-Beendigung...
set RETRIES=0
:wait_loop
if %RETRIES% GEQ 30 (
    echo   WARNUNG: App konnte nicht beendet werden.
    goto do_copy
)
timeout /t 1 /nobreak >nul
:: Try to rename the exe - if it works, the file is not locked
ren "%TARGET%\BOS Alarm.exe" "BOS Alarm.exe" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   App beendet.
    goto do_copy
)
set /a RETRIES+=1
goto wait_loop

:do_copy
echo   Kopiere Update...
xcopy "%SOURCE%\*" "%TARGET%\" /E /Y /Q >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo   FEHLER beim Kopieren! Errorlevel: %ERRORLEVEL%
    echo   Bitte das Update manuell installieren.
    pause
    exit /b 1
)

echo   Update erfolgreich!
echo.
echo   Starte App neu...
start "" "%TARGET%\BOS Alarm.exe"

:: Clean up temp files
if exist "%SOURCE%" rmdir /S /Q "%SOURCE%" >nul 2>&1

echo   Fertig.
exit /b 0
