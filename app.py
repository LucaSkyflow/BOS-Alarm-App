import os
import re
import sys
import threading
import logging

from settings_manager import SettingsManager
from updater import check_for_update, download_and_apply
from mqtt_client import MQTTManager
from hue_controller import HueController
from kasa_controller import KasaController
from sound_player import SoundPlayer
from audio_keepalive import AudioKeepAlive
from alarm_engine import AlarmEngine
from tray_manager import TrayManager
from alarm_store import AlarmStore
from notification_manager import NotificationManager
from gui.main_window import MainWindow
from gui.password_dialog import PasswordDialog

log = logging.getLogger(__name__)


class App:
    def __init__(self):
        self.settings = SettingsManager()
        self.hue = HueController(self.settings)
        self.kasa = KasaController(self.settings)
        self.sound = SoundPlayer(self.settings)
        self.keepalive = AudioKeepAlive(self.settings)
        self.alarm_store = AlarmStore()
        self.notifications = NotificationManager()

        self.tray = TrayManager(
            on_show_window=self._show_window,
            on_test_alarm=self._test_alarm,
            on_test_sound=self._test_sound,
            on_quit=self._quit,
        )

        self.alarm_engine = AlarmEngine(
            hue=self.hue,
            sound=self.sound,
            tray=self.tray,
            on_alarm_triggered=self._on_alarm_triggered,
            kasa=self.kasa,
            settings=self.settings,
            on_all_alarms_cleared=self._on_all_alarms_cleared,
        )

        # Dual MQTT: Production (always on) + Staging (optional)
        self.mqtt_prod = MQTTManager(
            broker=self.settings.get("mqtt_broker", ""),
            port=self.settings.get("mqtt_port", 8883),
            username=self.settings.get("mqtt_username", ""),
            password=self.settings.get("mqtt_password", ""),
            use_tls=self.settings.get("mqtt_tls", True),
            topic=self.settings.get("mqtt_topic", "sf/organizations/#"),
            label="production",
            on_message_callback=self._on_mqtt_message,
            on_connect_callback=self._on_mqtt_connect,
            on_disconnect_callback=self._on_mqtt_disconnect,
        )

        self.mqtt_staging = MQTTManager(
            broker=self.settings.get("staging_mqtt_broker", ""),
            port=self.settings.get("staging_mqtt_port", 8883),
            username=self.settings.get("staging_mqtt_username", ""),
            password=self.settings.get("staging_mqtt_password", ""),
            use_tls=self.settings.get("staging_mqtt_tls", True),
            topic=self.settings.get("staging_mqtt_topic", "sf/organizations/#"),
            label="staging",
            on_message_callback=self._on_mqtt_message,
            on_connect_callback=self._on_mqtt_connect,
            on_disconnect_callback=self._on_mqtt_disconnect,
        )

        self.window: MainWindow | None = None
        self._health_stop = threading.Event()

    def run(self):
        self.window = MainWindow(
            settings=self.settings,
            alarm_store=self.alarm_store,
            on_test_hue=self._test_hue_only,
            on_test_sound=self._test_sound,
            on_apply_settings=self._apply_settings,
            on_quit=self._quit,
            on_reset_statistics=self._reset_statistics,
            on_test_full_alarm=self._test_full_alarm,
            on_finish_trip=self._on_finish_trip,
            on_check_update=self._manual_update_check,
            on_test_heli_sound=self._test_heli_sound,
            on_volume_change=self._on_volume_change,
            on_test_kasa=self._test_kasa,
            on_keepalive_toggle=self._toggle_keepalive,
            on_keepalive_test=self._test_keepalive_device,
        )

        # start tray
        self.tray.start()

        # start MQTT
        self._start_mqtt()

        # start health check thread
        self._health_stop.clear()
        threading.Thread(target=self._health_loop, daemon=True).start()

        # Auto-start audio keep-alive if configured
        if self.settings.get("keepalive_enabled", False) and self.settings.get("keepalive_auto_start", False):
            self.keepalive.start()
            self._update_keepalive_ui()

        # load alarm history from DB after GUI is ready
        self.window.after(100, self.window.dashboard.load_history)

        # initial staging status
        if not self.settings.get("staging_enabled", False):
            self.window.after(0, lambda: self.window.dashboard.set_mqtt_status("staging", None))

        # check for updates in background
        threading.Thread(target=self._check_for_updates, daemon=True).start()

        # run GUI mainloop (blocks until window destroyed)
        self.window.mainloop()

    def _start_mqtt(self):
        # Production always connects
        try:
            self.mqtt_prod.connect()
        except Exception as e:
            log.error(f"MQTT Production connect error: {e}")

        # Staging only if enabled
        if self.settings.get("staging_enabled", False):
            try:
                self.mqtt_staging.connect()
            except Exception as e:
                log.error(f"MQTT Staging connect error: {e}")
        else:
            self.mqtt_staging.disconnect()
            if self.window:
                self.window.after(0, lambda: self.window.dashboard.set_mqtt_status("staging", None))

    # ---- MQTT callbacks (called from paho thread) ----
    def _on_mqtt_message(self, topic: str, payload: dict | None, raw: str, source: str):
        log.info(f"MQTT [{source}] [{topic}]: {raw[:500]}")
        is_alarm = payload is not None and payload.get("name") == "trip_created"

        if is_alarm:
            log.info(f"ALARM EVENT [{source}]: {raw[:1000]}")

        # MQTT feed -> mqtt_tab on main thread
        if self.window:
            self.window.after(0, lambda: self.window.mqtt_tab.append_mqtt_message(topic, raw, is_alarm))

        # If alarm, store in DB and show card on dashboard
        if is_alarm and payload:
            record = self.alarm_store.insert_alarm(payload, raw, source=source)
            if record and self.window:
                self.window.after(0, lambda r=record: self.window.dashboard.add_alarm(r))
                self.notifications.send_alarm_notification(record)

        # trip_confirmed → BESTÄTIGT + stop alarm
        if payload is not None and payload.get("name") == "trip_confirmed":
            trip = payload.get("trip", {})
            trip_id = trip.get("id") or self._extract_trip_id_from_topic(topic)
            if trip_id:
                log.info(f"TRIP CONFIRMED [{trip_id}]")
                self.alarm_store.update_trip_status(trip_id, "confirmed")
                if self.window:
                    self.window.after(0, lambda tid=trip_id: self.window.dashboard.update_card_status(tid, "confirmed"))
                desc = trip.get("description", "")
                if desc:
                    self.alarm_store.update_trip_description(trip_id, desc)
                    if self.window:
                        self.window.after(0, lambda tid=trip_id, d=desc: self.window.dashboard.update_card_description(tid, d))
                self.alarm_engine.stop_alarm_for_trip(trip_id, sound_only=True)
                if self.window and not self.alarm_engine.has_active_alarms():
                    self.window.after(0, self.window.dashboard.stop_alarm_blink)

        # trip_completed → BEENDET
        if payload is not None and payload.get("name") == "trip_completed":
            trip = payload.get("trip", {})
            trip_id = trip.get("id") or self._extract_trip_id_from_topic(topic)
            if trip_id:
                log.info(f"TRIP COMPLETED [{trip_id}]")
                self.alarm_store.update_trip_status(trip_id, "finished")
                if self.window:
                    self.window.after(0, lambda tid=trip_id: self.window.dashboard.update_card_status(tid, "finished"))
                desc = trip.get("description", "")
                if desc:
                    self.alarm_store.update_trip_description(trip_id, desc)
                    if self.window:
                        self.window.after(0, lambda tid=trip_id, d=desc: self.window.dashboard.update_card_description(tid, d))
                self.alarm_engine.stop_alarm_for_trip(trip_id)
                if self.window and not self.alarm_engine.has_active_alarms():
                    self.window.after(0, self.window.dashboard.stop_alarm_blink)

        # trip_updated → status changes + helicopter detection
        if payload is not None and payload.get("name") == "trip_updated":
            trip = payload.get("trip", {})
            if trip.get("status") == "CONFIRMED":
                trip_id = trip.get("id") or self._extract_trip_id_from_topic(topic)
                if trip_id:
                    log.info(f"TRIP CONFIRMED (via update) [{trip_id}]")
                    self.alarm_store.update_trip_status(trip_id, "confirmed")
                    if self.window:
                        self.window.after(0, lambda tid=trip_id: self.window.dashboard.update_card_status(tid, "confirmed"))
                    self.alarm_engine.stop_alarm_for_trip(trip_id, sound_only=True)
                    if self.window and not self.alarm_engine.has_active_alarms():
                        self.window.after(0, self.window.dashboard.stop_alarm_blink)
            elif trip.get("status") == "IN_PROGRESS":
                trip_id = trip.get("id") or self._extract_trip_id_from_topic(topic)
                if trip_id:
                    log.info(f"TRIP IN_PROGRESS [{trip_id}]")
                    self.alarm_store.update_trip_status(trip_id, "in_progress")
                    if self.window:
                        self.window.after(0, lambda tid=trip_id: self.window.dashboard.update_card_status(tid, "in_progress"))
            elif trip.get("status") == "COMPLETED":
                trip_id = trip.get("id") or self._extract_trip_id_from_topic(topic)
                if trip_id:
                    log.info(f"TRIP COMPLETED (via update) [{trip_id}]")
                    self.alarm_store.update_trip_status(trip_id, "finished")
                    if self.window:
                        self.window.after(0, lambda tid=trip_id: self.window.dashboard.update_card_status(tid, "finished"))
                    self.alarm_engine.stop_alarm_for_trip(trip_id)
                    if self.window and not self.alarm_engine.has_active_alarms():
                        self.window.after(0, self.window.dashboard.stop_alarm_blink)
            # Extract description from trip object if present
            desc = trip.get("description", "")
            if desc:
                desc_trip_id = trip.get("id") or self._extract_trip_id_from_topic(topic)
                if desc_trip_id:
                    self.alarm_store.update_trip_description(desc_trip_id, desc)
                    if self.window:
                        self.window.after(0, lambda tid=desc_trip_id, d=desc: self.window.dashboard.update_card_description(tid, d))
            notification = payload.get("notification")
            if notification is not None:
                message = notification.get("message", "")
                if "Incoming helicopter" in message:
                    heli_trip_id = self._extract_trip_id_from_topic(topic)
                    log.info(f"HELICOPTER INCOMING [{heli_trip_id}]")
                    threading.Thread(target=self.sound.play_helicopter_alarm, daemon=True).start()
                    if self.window:
                        self.window.after(0, lambda tid=heli_trip_id: self.window.dashboard.show_helicopter_banner(tid))
                    if heli_trip_id:
                        self.alarm_store.update_trip_helicopter(heli_trip_id, True)
                        if self.window:
                            self.window.after(0, lambda tid=heli_trip_id: self.window.dashboard.update_card_helicopter(tid, True))
                elif "Helicopter canceled" in message:
                    heli_trip_id = self._extract_trip_id_from_topic(topic)
                    log.info(f"HELICOPTER CANCELED [{heli_trip_id}]")
                    if self.window:
                        self.window.after(0, lambda tid=heli_trip_id: self.window.dashboard.dismiss_helicopter_banner(tid))
                    if heli_trip_id:
                        self.alarm_store.update_trip_helicopter(heli_trip_id, False)
                        if self.window:
                            self.window.after(0, lambda tid=heli_trip_id: self.window.dashboard.update_card_helicopter(tid, False))
                elif "Aktion abgelehnt" in message:
                    trip_id = self._extract_trip_id_from_topic(topic)
                    if trip_id:
                        log.info(f"TRIP REJECTED [{trip_id}]: {message}")
                        self.alarm_store.update_trip_status(trip_id, "rejected")
                        if self.window:
                            self.window.after(0, lambda tid=trip_id: self.window.dashboard.update_card_status(tid, "rejected"))
                        self.alarm_engine.stop_alarm_for_trip(trip_id)
                        if self.window and not self.alarm_engine.has_active_alarms():
                            self.window.after(0, self.window.dashboard.stop_alarm_blink)
                elif message.startswith("Trip description updated to "):
                    desc_text = message[len("Trip description updated to "):]
                    desc_trip_id = self._extract_trip_id_from_topic(topic)
                    if desc_trip_id and desc_text:
                        log.info(f"TRIP DESCRIPTION [{desc_trip_id}]: {desc_text}")
                        self.alarm_store.update_trip_description(desc_trip_id, desc_text)
                        if self.window:
                            self.window.after(0, lambda tid=desc_trip_id, d=desc_text: self.window.dashboard.update_card_description(tid, d))

        # trip_deleted → GELÖSCHT
        if payload is not None and payload.get("name") == "trip_deleted":
            trip_id = self._extract_trip_id_from_topic(topic)
            if trip_id:
                log.info(f"TRIP DELETED [{trip_id}]")
                self.alarm_store.update_trip_status(trip_id, "deleted")
                if self.window:
                    self.window.after(0, lambda tid=trip_id: self.window.dashboard.update_card_status(tid, "deleted"))
                self.alarm_engine.stop_alarm_for_trip(trip_id)
                if self.window and not self.alarm_engine.has_active_alarms():
                    self.window.after(0, self.window.dashboard.stop_alarm_blink)

        # Return command: command_request_executed with value == "RETURN"
        if payload is not None and payload.get("name") == "command_request_executed":
            if payload.get("value") == "RETURN":
                trip_id = self._extract_trip_id_from_command_topic(topic)
                if trip_id:
                    log.info(f"TRIP RETURN [{trip_id}]")
                    self.alarm_store.update_trip_status(trip_id, "return")
                    if self.window:
                        self.window.after(0, lambda tid=trip_id: self.window.dashboard.update_card_status(tid, "return"))

        # Alarm engine + dashboard blink: only for production, or staging if staging_alarm_enabled
        trigger_alarm = (source == "production") or (source == "staging" and self.settings.get("staging_alarm_enabled", False))

        if is_alarm and trigger_alarm and self.window:
            self.window.after(0, self.window.dashboard.start_alarm_blink)

        if trigger_alarm:
            self.alarm_engine.handle_mqtt_event(topic, payload, raw)

    def _on_mqtt_connect(self, source: str):
        log.info(f"MQTT [{source}] connected callback")
        if self.window:
            self.window.after(0, lambda: self.window.dashboard.set_mqtt_status(source, True))
        if source == "production":
            self.tray.set_color("green")

    def _on_mqtt_disconnect(self, source: str, reason: str = ""):
        log.warning(f"MQTT [{source}] disconnected callback (reason={reason})")
        if self.window:
            self.window.after(0, lambda: self.window.dashboard.set_mqtt_status(source, False, reason))
        if source == "production":
            self.tray.set_color("blue")

    # ---- Alarm triggered callback ----
    def _on_alarm_triggered(self, topic: str, payload: dict | None, raw: str):
        log.info(f"Alarm triggered: {topic}")

    def _on_all_alarms_cleared(self):
        """Callback: alle Alarme (inkl. Nachlaufzeit) sind beendet."""
        if self.window:
            self.window.after(0, self.window.dashboard.stop_alarm_blink)

    def _on_finish_trip(self, trip_id: str):
        self.alarm_store.update_trip_status(trip_id, "finished")
        if self.window:
            self.window.after(0, lambda: self.window.dashboard.update_card_status(trip_id, "finished"))

    # ---- Health check ----
    def _health_loop(self):
        while not self._health_stop.is_set():
            try:
                reachable = self.hue.is_reachable()
                if self.window:
                    self.window.after(0, lambda r=reachable: self.window.dashboard.set_hue_status(r))
            except Exception:
                pass

            # Kasa plug status
            try:
                kasa_ok = self.kasa.is_reachable()
                if self.window:
                    self.window.after(0, lambda r=kasa_ok: self.window.dashboard.set_kasa_status(r))
            except Exception:
                pass

            # Production MQTT status
            try:
                connected = self.mqtt_prod.is_connected()
                if self.window:
                    self.window.after(0, lambda c=connected: self.window.dashboard.set_mqtt_status("production", c))
            except Exception:
                pass

            # Staging MQTT status
            try:
                if self.settings.get("staging_enabled", False):
                    connected = self.mqtt_staging.is_connected()
                    if self.window:
                        self.window.after(0, lambda c=connected: self.window.dashboard.set_mqtt_status("staging", c))
                else:
                    if self.window:
                        self.window.after(0, lambda: self.window.dashboard.set_mqtt_status("staging", None))
            except Exception:
                pass

            # Audio Keep-Alive status
            try:
                running, detail = self.keepalive.get_status()
                if self.window:
                    self.window.after(0, lambda r=running, d=detail: self.window.dashboard.set_keepalive_status(r, d))
                    self.window.after(0, lambda r=running, d=detail: self.window.settings_tab.set_keepalive_status(r, d))
            except Exception:
                pass

            self._health_stop.wait(15)

    # ---- GUI callbacks ----
    def _show_window(self):
        if self.window:
            self.window.after(0, self.window.show)

    def _test_alarm(self):
        self.alarm_engine.trigger_alarm("test", {"name": "trip_created"}, '{"name":"trip_created"}')
        if self.window:
            self.window.after(0, self.window.dashboard.start_alarm_blink)

    def _test_full_alarm(self):
        self.alarm_engine.trigger_alarm("test", {"name": "trip_created"}, '{"name":"trip_created"}')
        if self.window:
            self.window.after(0, self.window.dashboard.start_alarm_blink)

    def _test_hue_only(self):
        threading.Thread(target=self.hue.alarm_blink_then_restore, args=(threading.Event(),), daemon=True).start()

    def _test_sound(self):
        self.sound.stop()
        self.sound.play_alarm()

    def _on_volume_change(self, level: float):
        self.sound.set_volume(level)
        self.settings.set("volume", level)

    def _test_kasa(self):
        def _run():
            try:
                self.kasa.turn_on()
                import time
                time.sleep(3)
                self.kasa.turn_off()
            except Exception as e:
                log.error(f"Kasa test error: {e}")
        threading.Thread(target=_run, daemon=True).start()

    def _test_keepalive_device(self, device_name: str = ""):
        threading.Thread(target=self.keepalive.play_test_tone, args=(device_name,), daemon=True).start()

    def _toggle_keepalive(self):
        if self.keepalive.is_running():
            self.keepalive.stop()
        else:
            self.keepalive.start()
        self._update_keepalive_ui()

    def _update_keepalive_ui(self):
        running, detail = self.keepalive.get_status()
        if self.window:
            self.window.after(0, lambda r=running, d=detail: self.window.dashboard.set_keepalive_status(r, d))
            self.window.after(0, lambda r=running, d=detail: self.window.settings_tab.set_keepalive_status(r, d))

    def _test_heli_sound(self):
        self.sound.stop()
        # Play helicopter sound once (override loop count to 1)
        original = self.settings.get("helicopter_loop_count", 5)
        self.settings.set("helicopter_loop_count", 1)
        self.sound.play_helicopter_alarm()
        self.settings.set("helicopter_loop_count", original)

    @staticmethod
    def _extract_trip_id_from_topic(topic: str) -> str | None:
        # Topic format: sf/organizations/{org}/trips/{trip_id}/events
        m = re.search(r"trips/([^/]+)/events", topic)
        return m.group(1) if m else None

    @staticmethod
    def _extract_trip_id_from_command_topic(topic: str) -> str | None:
        # Topic format: sf/organizations/{org}/trips/{trip_id}/command-requests
        m = re.search(r"trips/([^/]+)/command-requests", topic)
        return m.group(1) if m else None

    def _reset_statistics(self):
        self.alarm_store.clear_all()
        if self.window:
            self.window.after(0, self.window.dashboard.clear_and_refresh)

    def _check_for_updates(self):
        def on_status(msg, color="#aaaaaa"):
            if self.window:
                self.window.after(0, lambda: self.window.dashboard.set_update_status(msg, color))
                self.window.after(0, lambda: self.window.settings_tab.set_update_status(msg, color))

        result = check_for_update(on_status=on_status)
        if result:
            new_version, asset_url = result
            success = download_and_apply(asset_url, new_version, on_status=on_status)
            if success:
                on_status(f"Update auf v{new_version} wird installiert — App startet neu...")
                # Give the UI a moment to show the message, then quit
                if self.window:
                    self.window.after(2000, self._do_quit)

    def _manual_update_check(self):
        threading.Thread(target=self._check_for_updates, daemon=True).start()

    def _apply_settings(self):
        log.info("Settings applied, recreating MQTT connections...")
        self.mqtt_prod.disconnect()
        self.mqtt_staging.disconnect()

        # Recreate with current settings (credentials may have changed)
        self.mqtt_prod = MQTTManager(
            broker=self.settings.get("mqtt_broker", ""),
            port=self.settings.get("mqtt_port", 8883),
            username=self.settings.get("mqtt_username", ""),
            password=self.settings.get("mqtt_password", ""),
            use_tls=self.settings.get("mqtt_tls", True),
            topic=self.settings.get("mqtt_topic", "sf/organizations/#"),
            label="production",
            on_message_callback=self._on_mqtt_message,
            on_connect_callback=self._on_mqtt_connect,
            on_disconnect_callback=self._on_mqtt_disconnect,
        )

        self.mqtt_staging = MQTTManager(
            broker=self.settings.get("staging_mqtt_broker", ""),
            port=self.settings.get("staging_mqtt_port", 8883),
            username=self.settings.get("staging_mqtt_username", ""),
            password=self.settings.get("staging_mqtt_password", ""),
            use_tls=self.settings.get("staging_mqtt_tls", True),
            topic=self.settings.get("staging_mqtt_topic", "sf/organizations/#"),
            label="staging",
            on_message_callback=self._on_mqtt_message,
            on_connect_callback=self._on_mqtt_connect,
            on_disconnect_callback=self._on_mqtt_disconnect,
        )

        self._start_mqtt()

        # Restart keep-alive if it was running (device or interval may have changed)
        if self.keepalive.is_running():
            self.keepalive.stop()
            self.keepalive.start()
            self._update_keepalive_ui()

    def _quit(self):
        if self.window:
            self.window.after(0, self._quit_with_password)
        else:
            self._do_quit()

    def _quit_with_password(self):
        enabled = self.settings.get("quit_password_enabled", True)
        password = self.settings.get("quit_password", "")
        if not enabled or not password:
            self._do_quit()
            return

        # Show window so the dialog has a parent
        self.window.deiconify()
        dlg = PasswordDialog(self.window)
        self.window.wait_window(dlg)

        if dlg.result is None:
            return
        if dlg.result != password:
            from tkinter import messagebox
            messagebox.showerror("Fehler", "Falsches Passwort!", parent=self.window)
            return
        self._do_quit()

    def _do_quit(self):
        log.info("Quitting application")
        self._health_stop.set()
        try:
            self.keepalive.stop()
        except Exception:
            pass
        try:
            self.alarm_engine.stop()
        except Exception:
            pass
        try:
            self.mqtt_prod.disconnect()
        except Exception:
            pass
        try:
            self.mqtt_staging.disconnect()
        except Exception:
            pass
        try:
            self.kasa.stop()
        except Exception:
            pass
        try:
            self.tray.stop()
        except Exception:
            pass
        log.info("Cleanup done, exiting process")
        os._exit(0)
