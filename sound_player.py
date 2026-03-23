import os
import wave
import threading
import logging

log = logging.getLogger(__name__)

try:
    import winsound
except ImportError:
    winsound = None

try:
    import pygame
    pygame.mixer.init()
except Exception:
    pygame = None


class SoundPlayer:
    def __init__(self, settings):
        self._settings = settings
        self._loop_timer: threading.Timer | None = None
        self._stop_event: threading.Event | None = None

    def play_alarm(self):
        log.debug("play_alarm() called")
        if winsound is None:
            log.warning("winsound not available on this platform.")
            return

        wav = self._settings.wav_path()
        if not os.path.exists(wav):
            log.warning(f"Alarm WAV not found: {wav}")
            return

        log.debug(f"Playing normal alarm: {wav!r}")
        self.stop()
        try:
            winsound.PlaySound(wav, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception as e:
            log.error(f"WAV sound error: {e}")
            return
        duration = self._get_wav_duration(wav)
        if duration:
            self._loop_timer = threading.Timer(duration, self.stop)
            self._loop_timer.daemon = True
            self._loop_timer.start()

    def play_helicopter_alarm(self):
        log.debug("play_helicopter_alarm() called")
        raw = self._settings.get("alarm_wav_helicopter", "")
        if not raw:
            log.warning("Kein Helikopter-Audio konfiguriert – Fallback auf Normal-Alarm.")
            self.play_alarm()
            return

        wav = self._settings.wav_helicopter_path()
        log.debug(f"Helicopter WAV path resolved: {wav!r}")
        if not os.path.exists(wav):
            log.warning("Helicopter audio not found, falling back to normal alarm.")
            self.play_alarm()
            return

        ext = os.path.splitext(wav)[1].lower()
        loop_count = int(self._settings.get("helicopter_loop_count", 1))
        log.debug(f"ext={ext!r}, loop_count={loop_count}")

        # Lazy pygame init (falls Modul-Level-Init fehlschlug)
        _pg = pygame
        if _pg is None:
            log.debug("pygame module-level init failed, attempting lazy init...")
            try:
                import pygame as _pygame_mod
                _pygame_mod.mixer.init()
                _pg = _pygame_mod
                log.debug("pygame lazy init succeeded")
            except Exception as ex:
                log.warning(f"pygame lazy init failed: {ex}")
                _pg = None

        if _pg is not None and ext in (".mp3", ".wav"):
            log.debug(f"Using pygame for playback (loops={loop_count - 1})")
            self.stop()
            try:
                _pg.mixer.music.load(wav)
                _pg.mixer.music.play(loops=loop_count - 1)
                log.debug("pygame.mixer.music.play() called successfully")
            except Exception as e:
                log.error(f"pygame playback error: {e}")
                self.play_alarm()
                return
        else:
            log.debug("pygame not available or ext not supported – using winsound fallback")
            if ext == ".mp3":
                log.error("pygame nicht verfügbar – MP3 kann nicht über winsound abgespielt werden. Falle zurück auf Normal-Alarm.")
                self.play_alarm()
                return
            # WAV fallback via winsound mit N-Loop-Thread
            if winsound is None:
                log.warning("winsound not available on this platform.")
                return
            self.stop()
            self._stop_event = threading.Event()
            stop_ev = self._stop_event

            def _loop():
                log.debug(f"winsound loop starting: {loop_count} iterations")
                for i in range(loop_count):
                    if stop_ev.is_set():
                        log.debug(f"winsound loop stopped at iteration {i}")
                        break
                    try:
                        winsound.PlaySound(wav, winsound.SND_FILENAME)
                        log.debug(f"winsound iteration {i+1}/{loop_count} done")
                    except Exception as e:
                        log.error(f"WAV loop error: {e}")
                        break

            threading.Thread(target=_loop, daemon=True).start()

    def _get_wav_duration(self, wav_path) -> float | None:
        try:
            with wave.open(wav_path, 'r') as wf:
                return wf.getnframes() / float(wf.getframerate())
        except Exception:
            return None

    def stop(self):
        log.debug("SoundPlayer.stop() called")
        if self._loop_timer:
            self._loop_timer.cancel()
            self._loop_timer = None
        if self._stop_event:
            self._stop_event.set()
            self._stop_event = None
        if pygame is not None:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
        if winsound is None:
            return
        try:
            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass
