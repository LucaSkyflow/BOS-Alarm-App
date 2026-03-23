@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

echo.
echo   ╔══════════════════════════════════════════════╗
echo   ║       BOS Alarm — Ersteinrichtung            ║
echo   ╚══════════════════════════════════════════════╝
echo.

set "CONFIG=%~dp0config.json"
set "EXAMPLE=%~dp0config.example.json"

if exist "%CONFIG%" (
    echo   Bestehende config.json gefunden.
    echo   Setup ueberschreibt die MQTT-Werte.
    echo.
)

echo   ── MQTT Verbindung ──
echo.
echo   Diese Daten bekommst du vom Administrator.
echo.

set /p BROKER="  MQTT Broker: "
set /p USERNAME="  MQTT Username: "
set /p PASSWORD="  MQTT Passwort: "

echo.
echo   ── Hue Bridge (optional) ──
echo.
echo   Fuer Alarm-Licht ueber Philips Hue.
echo   Enter druecken zum Ueberspringen.
echo.

set "HUE_IP="
set "HUE_USER="
set /p HUE_IP="  Hue Bridge IP: "
if defined HUE_IP (
    set /p HUE_USER="  Hue API Username: "
)

echo.
echo   ── Zusammenfassung ──
echo.
echo   Broker:   %BROKER%
echo   Username: %USERNAME%
echo   Passwort: %PASSWORD%
if defined HUE_IP (
    echo   Hue IP:   %HUE_IP%
    echo   Hue User: %HUE_USER%
)
echo.

:: Write config.json
(
echo {
echo   "mqtt_broker": "%BROKER%",
echo   "mqtt_port": 8883,
echo   "mqtt_username": "%USERNAME%",
echo   "mqtt_password": "%PASSWORD%",
echo   "mqtt_topic": "sf/organizations/#",
echo   "mqtt_tls": true,
echo   "mqtt_preset": "production",
echo   "staging_mqtt_broker": "",
echo   "staging_mqtt_port": 8883,
echo   "staging_mqtt_username": "",
echo   "staging_mqtt_password": "",
echo   "staging_mqtt_topic": "sf/organizations/#",
echo   "staging_mqtt_tls": true,
echo   "hue_bridge_ip": "%HUE_IP%",
echo   "hue_username": "%HUE_USER%",
echo   "alarm_wav_file": "assets/Alarm.wav",
echo   "alarm_wav_helicopter": "assets/Helicopter_alert.wav",
echo   "alarm_light_seconds": 20.0,
echo   "blink_interval": 0.8,
echo   "off_delay": 0.3,
echo   "dashboard_blink_interval": 0.5,
echo   "quit_password": "",
echo   "staging_enabled": false,
echo   "staging_alarm_enabled": true,
echo   "quit_password_enabled": false,
echo   "helicopter_loop_count": 10
echo }
) > "%CONFIG%"

echo   Config gespeichert!
echo.

if exist "%~dp0BOS Alarm.exe" (
    set /p STARTAPP="  App jetzt starten? (j/n) [j]: "
    if /i "!STARTAPP!"=="" set "STARTAPP=j"
    if /i "!STARTAPP!"=="j" (
        echo   App wird gestartet...
        start "" "%~dp0BOS Alarm.exe"
    )
) else (
    echo   Hinweis: 'BOS Alarm.exe' nicht gefunden.
)

echo.
echo   ╔══════════════════════════════════════════════╗
echo   ║  Einrichtung abgeschlossen!                  ║
echo   ╚══════════════════════════════════════════════╝
echo.
pause
