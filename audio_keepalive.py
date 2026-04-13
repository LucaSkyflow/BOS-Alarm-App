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
    """Keeps an audio output stream continuously open so that Bluetooth
    headphones (or similar devices) never detect silence and auto-sleep.

    Previous approach played short bursts via sd.play()/sd.wait() which
    opened and closed the PortAudio stream each time — headphones saw
    no active A2DP stream between bursts and slept anyway.

    This version uses sd.OutputStream in callback mode: a continuous,
    near-inaudible 20 Hz sine wave keeps the stream permanently active."""

    # Signal parameters
    _SAMPLE_RATE = 44100
    _FREQUENCY_HZ = 20.0        # 20 Hz — lowest freq reliably reproduced by all audio HW / BT codecs
    _AMPLITUDE = 0.005           # ~ -46 dBFS — imperceptible at 20 Hz but above HW noise floor
    _BLOCKSIZE = 1024            # ~23 ms per callback at 44100 Hz

    def __init__(self, settings):
        self._settings = settings
        self._stop_event = threading.Event()
        self._running = False
        self._last_play_time: float | None = None
        self._last_error: str | None = None
        self._stream: "sd.OutputStream | None" = None
        self._phase: float = 0.0
        self._lock = threading.Lock()
        self._watchdog_thread: threading.Thread | None = None

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
        self._open_stream()
        self._watchdog_thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self._watchdog_thread.start()
        log.info("Audio Keep-Alive gestartet (continuous stream).")

    def stop(self):
        if not self._running:
            return
        self._running = False
        self._stop_event.set()
        with self._lock:
            self._close_stream_unlocked()
        if self._watchdog_thread is not None:
            self._watchdog_thread.join(timeout=2.0)
            self._watchdog_thread = None
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
            return True, f"Aktiv \u2014 Stream laeuft seit {t}"
        return True, "Aktiv \u2014 Stream wird geoeffnet"

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
        # Pause keep-alive stream so sd.play() can use the same device
        was_streaming = False
        with self._lock:
            if self._stream is not None:
                was_streaming = True
                self._close_stream_unlocked()
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
        finally:
            if was_streaming and self._running:
                self._open_stream()

    # ── internal: stream lifecycle ──

    def _open_stream(self):
        with self._lock:
            self._close_stream_unlocked()
            device_name = self._settings.get("keepalive_audio_device", "")
            device_index = self._resolve_device(device_name)
            self._phase = 0.0
            try:
                self._stream = sd.OutputStream(
                    samplerate=self._SAMPLE_RATE,
                    blocksize=self._BLOCKSIZE,
                    device=device_index,
                    channels=1,
                    dtype="float32",
                    callback=self._audio_callback,
                )
                self._stream.start()
                self._last_play_time = time.time()
                self._last_error = None
                log.debug(f"OutputStream geoeffnet (device={device_name or 'Standard'})")
            except Exception as e:
                self._last_error = str(e)
                log.warning(f"OutputStream konnte nicht geoeffnet werden: {e}")
                self._stream = None

    def _close_stream_unlocked(self):
        """Close the stream. Caller must hold self._lock."""
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                log.debug(f"Fehler beim Schliessen des Streams: {e}")
            self._stream = None

    def _audio_callback(self, outdata, frames, time_info, status):
        """Called by PortAudio from an audio thread to fill output buffers."""
        if status:
            log.debug(f"OutputStream status: {status}")
        t = (np.arange(frames, dtype=np.float64) + self._phase) / self._SAMPLE_RATE
        outdata[:, 0] = (self._AMPLITUDE * np.sin(2 * np.pi * self._FREQUENCY_HZ * t)).astype(np.float32)
        self._phase += frames
        # Wrap phase at a full cycle boundary to prevent float precision loss
        period_samples = self._SAMPLE_RATE / self._FREQUENCY_HZ
        if self._phase >= period_samples:
            self._phase -= period_samples * int(self._phase / period_samples)

    def _watchdog_loop(self):
        """Monitors the stream and restarts it if it dies (e.g. device unplugged)."""
        while not self._stop_event.is_set():
            with self._lock:
                stream_active = self._stream is not None and self._stream.active

            if stream_active:
                self._last_play_time = time.time()
                self._last_error = None
            elif self._running:
                log.warning("OutputStream nicht aktiv, versuche Neustart...")
                try:
                    self._open_stream()
                except Exception as e:
                    self._last_error = str(e)
                    log.warning(f"Stream-Neustart fehlgeschlagen: {e}")

            self._stop_event.wait(timeout=5.0)

    # ── internal: device resolution ──

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
