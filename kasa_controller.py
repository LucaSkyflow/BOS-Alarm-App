import asyncio
import threading
import logging

from kasa import Discover

log = logging.getLogger(__name__)


class KasaController:
    def __init__(self, settings):
        self._settings = settings
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _run_async(self, coro):
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=10)

    async def _get_device(self):
        ip = self._settings.get("kasa_plug_ip", "")
        if not ip:
            return None
        return await Discover.discover_single(ip, discovery_timeout=5)

    # ------ health ------
    def is_reachable(self) -> bool:
        if not self._settings.get("kasa_enabled", False):
            return False
        try:
            dev = self._run_async(self._get_device())
            return dev is not None
        except Exception:
            return False

    # ------ switching ------
    def turn_on(self):
        dev = self._run_async(self._get_device())
        if not dev:
            return
        self._run_async(dev.turn_on())
        log.info(f"Kasa plug {dev.host} turned ON")

    def turn_off(self):
        dev = self._run_async(self._get_device())
        if not dev:
            return
        self._run_async(dev.turn_off())
        log.info(f"Kasa plug {dev.host} turned OFF")

    # ------ alarm lifecycle ------
    def alarm_on_then_off(self, stop_event: threading.Event):
        if not self._settings.get("kasa_enabled", False):
            return
        ip = self._settings.get("kasa_plug_ip", "")
        if not ip:
            return
        try:
            self.turn_on()
            stop_event.wait()  # bis Alarm beendet + Nachlaufzeit abgelaufen
        except Exception as e:
            log.error(f"Kasa alarm_on error: {e}")
        finally:
            try:
                self.turn_off()
            except Exception as e:
                log.error(f"Kasa alarm_off error: {e}")

    # ------ shutdown ------
    def stop(self):
        self._loop.call_soon_threadsafe(self._loop.stop)
