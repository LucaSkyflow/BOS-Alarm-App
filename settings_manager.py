import json
import os
import sys

# Two directories needed:
# _APP_DIR  = where config.json lives (next to the exe)
# _RES_DIR  = where bundled resources live (assets/, etc.)
#
# In PyInstaller frozen builds:
#   _APP_DIR = exe directory (e.g. C:\BOS Alarm\)
#   _RES_DIR = sys._MEIPASS  (e.g. C:\BOS Alarm\_internal\)
# In development:
#   Both are the script directory.
if getattr(sys, "frozen", False):
    _APP_DIR = os.path.dirname(sys.executable)
    _RES_DIR = sys._MEIPASS
else:
    _APP_DIR = os.path.dirname(os.path.abspath(__file__))
    _RES_DIR = _APP_DIR
CONFIG_PATH = os.path.join(_APP_DIR, "config.json")

MQTT_PRESETS = {
    "staging": {
        "mqtt_broker": "",
        "mqtt_port": 8883,
        "mqtt_username": "",
        "mqtt_password": "",
        "mqtt_topic": "sf/organizations/#",
        "mqtt_tls": True,
    },
    "production": {
        "mqtt_broker": "",
        "mqtt_port": 8883,
        "mqtt_username": "",
        "mqtt_password": "",
        "mqtt_topic": "sf/organizations/#",
        "mqtt_tls": True,
    },
}

DEFAULTS = {
    "mqtt_broker": "",
    "mqtt_port": 8883,
    "mqtt_username": "",
    "mqtt_password": "",
    "mqtt_topic": "sf/organizations/#",
    "mqtt_tls": True,
    "mqtt_preset": "production",
    "staging_mqtt_broker": "",
    "staging_mqtt_port": 8883,
    "staging_mqtt_username": "",
    "staging_mqtt_password": "",
    "staging_mqtt_topic": "sf/organizations/#",
    "staging_mqtt_tls": True,
    "hue_bridge_ip": "",
    "hue_username": "",
    "alarm_wav_file": "assets/Alarm.wav",
    "alarm_wav_helicopter": "assets/Helicopter_alert.wav",
    "helicopter_loop_count": 5,
    "alarm_light_seconds": 20.0,
    "blink_interval": 0.8,
    "off_delay": 0.3,
    "dashboard_blink_interval": 0.5,
    "quit_password": "",
    "quit_password_enabled": False,
    "staging_enabled": False,
    "staging_alarm_enabled": False,
    "kasa_enabled": False,
    "kasa_plug_ip": "",
}


class SettingsManager:
    def __init__(self):
        self._data: dict = {}
        self.load()

    def load(self):
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        # fill in any missing keys with defaults
        for k, v in DEFAULTS.items():
            self._data.setdefault(k, v)

    def save(self):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def get(self, key: str, fallback=None):
        return self._data.get(key, fallback)

    def set(self, key: str, value):
        self._data[key] = value

    def update(self, mapping: dict):
        self._data.update(mapping)
        self.save()

    def all(self) -> dict:
        return dict(self._data)

    def apply_mqtt_preset(self, preset_name: str):
        preset = MQTT_PRESETS.get(preset_name)
        if not preset:
            return
        self._data["mqtt_preset"] = preset_name
        for key, value in preset.items():
            self._data[key] = value
        self.save()

    def wav_path(self) -> str:
        raw = self.get("alarm_wav_file", "assets/Alarm.wav")
        if os.path.isabs(raw):
            return raw
        return os.path.join(_RES_DIR, raw)

    def wav_helicopter_path(self) -> str:
        raw = self.get("alarm_wav_helicopter", "")
        if raw and os.path.isabs(raw) and os.path.exists(raw):
            return raw
        if raw and not os.path.isabs(raw):
            full = os.path.join(_RES_DIR, raw)
            if os.path.exists(full):
                return full
        # Fallback to normal alarm WAV
        return self.wav_path()
