import time
import requests
import logging

log = logging.getLogger(__name__)


class HueController:
    def __init__(self, settings):
        self._settings = settings

    def _url(self, path: str) -> str:
        ip = self._settings.get("hue_bridge_ip")
        user = self._settings.get("hue_username")
        return f"http://{ip}/api/{user}{path}"

    def _get(self, path: str):
        r = requests.get(self._url(path), timeout=5)
        r.raise_for_status()
        return r.json()

    def _put(self, path: str, body: dict):
        r = requests.put(self._url(path), json=body, timeout=5)
        r.raise_for_status()
        return r.json()

    # ------ health ------
    def is_reachable(self) -> bool:
        try:
            self._get("/lights")
            return True
        except Exception:
            return False

    # ------ light helpers ------
    def _get_all_light_ids(self) -> list:
        g0 = self._get("/groups/0")
        return g0.get("lights", [])

    def snapshot_lights(self, light_ids: list) -> dict:
        snap = {}
        for lid in light_ids:
            state = self._get(f"/lights/{lid}")["state"]
            snap[lid] = {
                "on": state.get("on"),
                "bri": state.get("bri"),
                "colormode": state.get("colormode"),
                "hue": state.get("hue"),
                "sat": state.get("sat"),
                "ct": state.get("ct"),
                "xy": state.get("xy"),
                "effect": state.get("effect"),
            }
        return snap

    def restore_lights(self, snapshot: dict):
        for lid, s in snapshot.items():
            body = {"alert": "none"}
            if s.get("on") is not None:
                body["on"] = s["on"]
            if s.get("bri") is not None:
                body["bri"] = s["bri"]
            cm = s.get("colormode")
            if cm == "hs" and s.get("hue") is not None and s.get("sat") is not None:
                body["hue"] = s["hue"]
                body["sat"] = s["sat"]
            elif cm == "ct" and s.get("ct") is not None:
                body["ct"] = s["ct"]
            elif cm == "xy" and s.get("xy") is not None:
                body["xy"] = s["xy"]
            if s.get("effect") is not None:
                body["effect"] = s["effect"]
            self._put(f"/lights/{lid}/state", body)

    def set_group_off(self):
        self._put("/groups/0/action", {"on": False, "transitiontime": 0})

    def set_group_on_red_full(self):
        self._put("/groups/0/action", {"on": True, "bri": 254, "hue": 0, "sat": 254, "transitiontime": 0})

    def alarm_blink_then_restore(self, stop_event):
        light_seconds = float(self._settings.get("alarm_light_seconds", 20.0))
        blink_interval = float(self._settings.get("blink_interval", 0.8))
        off_delay = float(self._settings.get("off_delay", 0.3))

        lights = self._get_all_light_ids()
        if not lights:
            log.warning("Hue: Keine Lampen in groups/0 gefunden.")
            return

        snapshot = self.snapshot_lights(lights)
        try:
            self.set_group_off()
            time.sleep(off_delay)

            end = time.time() + light_seconds
            is_on = False
            while time.time() < end and not stop_event.is_set():
                is_on = not is_on
                if is_on:
                    self.set_group_on_red_full()
                else:
                    self.set_group_off()
                time.sleep(blink_interval)
        finally:
            self.restore_lights(snapshot)
