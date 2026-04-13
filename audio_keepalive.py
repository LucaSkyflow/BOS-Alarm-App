import threading
import time
import logging

log = logging.getLogger(__name__)

try:
    import sounddevice as sd
    import numpy as np
    _SD_AVAILABLE = True
except Exception as e:
    sd = None
    np = None
    _SD_AVAILABLE = False
    log.warning(f"sounddevice/numpy not available: {e}")


class AudioKeepAlive:
    """Periodically plays a near-inaudible signal on a chosen audio device
    to prevent auto-sleep / auto-disconnect (e.g. Bluetooth headphones)."""

    # Signal parameters
    _SAMPLE_RATE = 44100
    _DURATION_S = 0.1          # 100 ms
    _FREQUENCY_HZ = 1.0        # 1 Hz  (well below audible range)
    _AMPLITUDE = 0.001          # ~ -60 dBFS

    def __init__(self, settings):
        self._settings = settings
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._running = False
        self._last_play_time: float | None = None
        self._last_error: str | None = None

    # ── public API ──

    def start(self):
        if self._running:
            return
        if not _SD_AVAILABLE:
            log.warning("Audio Keep-Alive kann nicht starten: sounddevice/numpy nicht verfuegbar.")
            self._last_error = "sounddevice nicht verfuegbar"
            return
        self._stop_event.clear()
        self._running = True
        self._last_error = None
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        log.info("Audio Keep-Alive gestartet.")

    def stop(self):
        if not self._running:
            return
        self._running = False
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        log.info("Audio Keep-Alive gestoppt.")

    def is_running(self) -> bool:
        return self._running

    def get_status(self) -> tuple[bool, str]:
        if not _SD_AVAILABLE:
            return False, "Nicht verfuegbar (sounddevice fehlt)"
        if not self._running:
            return False, "Gestoppt"
        if self._last_error:
            return True, f"Fehler: {self._last_error}"
        if self._last_play_time:
            t = time.strftime("%H:%M:%S", time.localtime(self._last_play_time))
            return True, f"Aktiv \u2014 letztes Signal {t}"
        return True, "Aktiv \u2014 warte auf erstes Signal"

    @staticmethod
    def is_available() -> bool:
        return _SD_AVAILABLE

    @staticmethod
    def query_output_devices() -> list[str]:
        if not _SD_AVAILABLE:
            return ["Standard (Windows-Standard)"]
        try:
            devices = sd.query_devices()
            result = ["Standard (Windows-Standard)"]
            seen = set()
            for d in devices:
                if d["max_output_channels"] > 0:
                    name = d["name"]
                    if name not in seen:
                        seen.add(name)
                        result.append(name)
            return result
        except Exception as e:
            log.warning(f"Fehler beim Auflisten der Audio-Geraete: {e}")
            return ["Standard (Windows-Standard)"]

    def play_test_tone(self, device_name: str = ""):
        """Play a short audible beep on the given device so the user can verify it."""
        if not _SD_AVAILABLE:
            log.warning("Test-Ton nicht moeglich: sounddevice/numpy nicht verfuegbar.")
            return
        try:
            device_index = self._resolve_device(device_name)
            duration = 0.4
            freq = 440.0  # A4, clearly audible
            samples = int(self._SAMPLE_RATE * duration)
            t = np.linspace(0, duration, samples, endpoint=False, dtype=np.float32)
            # Sine with fade-in/fade-out to avoid click
            fade = int(self._SAMPLE_RATE * 0.02)
            signal = (0.3 * np.sin(2 * np.pi * freq * t)).astype(np.float32)
            signal[:fade] *= np.linspace(0, 1, fade, dtype=np.float32)
            signal[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)
            sd.play(signal, samplerate=self._SAMPLE_RATE, device=device_index)
            sd.wait()
            log.info(f"Test-Ton abgespielt (device={device_name or 'Standard'})")
        except Exception as e:
            log.error(f"Test-Ton Fehler: {e}")

    # ── internal ──

    def _loop(self):
        while not self._stop_event.is_set():
            try:
                self._play_silent_signal()
            except Exception as e:
                self._last_error = str(e)
                log.warning(f"Keep-Alive Signal-Fehler: {e}")

            interval = int(self._settings.get("keepalive_interval_seconds", 120))
            interval = max(10, interval)
            self._stop_event.wait(timeout=interval)

    def _play_silent_signal(self):
        device_name = self._settings.get("keepalive_audio_device", "")
        device_index = self._resolve_device(device_name)

        samples = int(self._SAMPLE_RATE * self._DURATION_S)
        t = np.linspace(0, self._DURATION_S, samples, endpoint=False, dtype=np.float32)
        signal = (self._AMPLITUDE * np.sin(2 * np.pi * self._FREQUENCY_HZ * t)).astype(np.float32)

        sd.play(signal, samplerate=self._SAMPLE_RATE, device=device_index)
        sd.wait()

        self._last_play_time = time.time()
        self._last_error = None
        log.debug(f"Keep-Alive Signal abgespielt (device={device_name or 'Standard'})")

    def _resolve_device(self, device_name: str) -> int | None:
        if not device_name or device_name.startswith("Standard"):
            return None
        try:
            devices = sd.query_devices()
            for i, d in enumerate(devices):
                if d["max_output_channels"] > 0 and d["name"] == device_name:
                    return i
        except Exception:
            pass
        log.warning(f"Audio-Geraet '{device_name}' nicht gefunden, nutze Standard.")
        self._last_error = f"Geraet '{device_name}' nicht gefunden"
        return None
