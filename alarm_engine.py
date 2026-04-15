import re
import time
import threading
import logging

log = logging.getLogger(__name__)


class AlarmEngine:
    def __init__(self, hue, sound, tray, on_alarm_triggered=None, kasa=None):
        self._hue = hue
        self._sound = sound
        self._tray = tray
        self._on_alarm_triggered = on_alarm_triggered
        self._kasa = kasa
        self._lock = threading.Lock()
        self._active: dict[str, threading.Event] = {}  # trip_id → stop_event
        self._sound_active: set = set()  # trip_ids mit aktivem Alarm-Ton

    # ---------- public API ----------

    def handle_mqtt_event(self, topic: str, payload: dict | None, raw: str):
        if payload is None:
            return
        if payload.get("name") == "trip_created":
            log.info(f"trip_created event received on {topic}")
            self.trigger_alarm(topic, payload, raw)

    def trigger_alarm(self, topic: str = "", payload: dict | None = None, raw: str = ""):
        trip_id = self._extract_trip_id(topic, payload)

        with self._lock:
            if trip_id in self._active:
                log.warning(f"Alarm for trip {trip_id} already running, skipping.")
                return
            stop_event = threading.Event()
            self._active[trip_id] = stop_event
            self._sound_active.add(trip_id)

        if self._on_alarm_triggered:
            self._on_alarm_triggered(topic, payload, raw)

        incoming_helicopter = bool((payload or {}).get("trip", {}).get("incomingHelicopter", False))

        if incoming_helicopter:
            threading.Thread(target=lambda: self._sound.play_helicopter_alarm(loop=True), daemon=True).start()
        else:
            threading.Thread(target=lambda: self._sound.play_alarm(loop=True), daemon=True).start()

        if self._tray:
            self._tray.set_color("red")

        def _run_hue():
            hue_ok = False
            try:
                self._hue.alarm_blink_then_restore(stop_event)
                hue_ok = True
            except Exception as e:
                log.error(f"Alarm Hue error: {e}")
            finally:
                with self._lock:
                    self._active.pop(trip_id, None)
                    still_active = bool(self._active) or bool(self._sound_active)
                if not still_active and self._tray:
                    self._tray.set_color("green")

        threading.Thread(target=_run_hue, daemon=True).start()

        def _run_kasa():
            try:
                self._kasa.alarm_on_then_off(stop_event)
            except Exception as e:
                log.error(f"Alarm Kasa error: {e}")

        if self._kasa:
            threading.Thread(target=_run_kasa, daemon=True).start()

    def stop_alarm_for_trip(self, trip_id: str, sound_only: bool = False):
        """Stoppt Alarm für einen bestimmten Einsatz.

        Args:
            trip_id: Trip-ID des Einsatzes.
            sound_only: Wenn True, wird nur der Ton gestoppt;
                        Lichter/Plug laufen für alarm_light_seconds weiter.
        """
        with self._lock:
            if not sound_only:
                stop_event = self._active.pop(trip_id, None)
            else:
                stop_event = None
            self._sound_active.discard(trip_id)
            still_active = bool(self._active) or bool(self._sound_active)
        if stop_event:
            stop_event.set()
        self._sound.stop()
        if not still_active and self._tray:
            self._tray.set_color("green")
        log.info(f"{'Sound' if sound_only else 'Alarm'} for trip {trip_id} stopped.")

    def has_active_alarms(self) -> bool:
        with self._lock:
            return bool(self._active) or bool(self._sound_active)

    def stop(self):
        """Alle Alarme stoppen (z.B. beim Beenden der App)."""
        with self._lock:
            events = list(self._active.values())
            self._sound_active.clear()
        for ev in events:
            ev.set()
        self._sound.stop()
        if self._kasa:
            try:
                self._kasa.turn_off()
            except Exception:
                pass

    # ---------- helpers ----------

    @staticmethod
    def _extract_trip_id(topic: str, payload: dict | None) -> str:
        m = re.search(r"trips/([^/]+)/events", topic)
        if m:
            return m.group(1)
        if payload:
            tid = (payload.get("trip") or {}).get("id", "")
            if tid:
                return tid
        return f"unknown_{time.time()}"
