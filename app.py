import re
import sys
import threading
import logging

from settings_manager import SettingsManager
from updater import check_for_update, download_and_apply
from mqtt_client import MQTTManager
from hue_controller import HueController
from sound_player import SoundPlayer
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
        self.sound = SoundPlayer(self.settings)
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
        )

        # start tray
        self.tray.start()

        # start MQTT
        self._start_mqtt()

        # start health check thread
        self._health_stop.clear()
        threading.Thread(target=self._health_loop, daemon=True).start()

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
            record = self.alarm_store.insert_alarm(payload, raw)
            if record and self.window:
                self.window.after(0, lambda r=record: self.window.dashboard.add_alarm(r))
                self.notifications.send_alarm_notification(record)

        # Helicopter detection from trip_updated
        if payload is not None and payload.get("name") == "trip_updated":
            trip = payload.get("trip", {})
            if trip.get("status") == "CONFIRMED":
                trip_id = trip.get("id") or self._extract_trip_id_from_topic(topic)
                if trip_id:
                    log.info(f"TRIP CONFIRMED [{trip_id}]")
                    self.alarm_store.update_trip_status(trip_id, "confirmed")
                    if self.window:
                        self.window.after(0, lambda tid=trip_id: self.window.dashboard.update_card_status(tid, "confirmed"))
                    self.alarm_engine.stop_alarm_for_trip(trip_id)
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
                    log.info(f"TRIP COMPLETED [{trip_id}]")
                    self.alarm_store.update_trip_status(trip_id, "finished")
                    if self.window:
                        self.window.after(0, lambda tid=trip_id: self.window.dashboard.update_card_status(tid, "finished"))
                    self.alarm_engine.stop_alarm_for_trip(trip_id)
                    if self.window and not self.alarm_engine.has_active_alarms():
                        self.window.after(0, self.window.dashboard.stop_alarm_blink)
            notification = payload.get("notification")
            if notification is not None:
                message = notification.get("message", "")
                if "Incoming helicopter" in message:
                    log.info("HELICOPTER INCOMING")
                    threading.Thread(target=self.sound.play_helicopter_alarm, daemon=True).start()
                    if self.window:
                        self.window.after(0, self.window.dashboard.show_helicopter_banner)
                elif "Helicopter canceled" in message:
                    log.info("HELICOPTER CANCELED")
                    if self.window:
                        self.window.after(0, self.window.dashboard.dismiss_helicopter_banner)
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

        # Trip deleted: trip_deleted event -> mark as deleted
        if payload is not None and payload.get("name") == "trip_deleted":
            trip_id = self._extract_trip_id_from_topic(topic)
            if trip_id:
                log.info(f"TRIP DELETED [{trip_id}]")
                self.alarm_store.update_trip_status(trip_id, "deleted")
                if self.window:
                    self.window.after(0, lambda tid=trip_id: self.window.dashboard.update_card_status(tid, "deleted"))

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
        self.sound.play_alarm()

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
        log.info("Settings applied, reconnecting MQTT...")
        self.mqtt_prod.disconnect()
        self.mqtt_staging.disconnect()
        self._start_mqtt()

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
        self.alarm_engine.stop()
        self.mqtt_prod.disconnect()
        self.mqtt_staging.disconnect()
        self.tray.stop()
        if self.window:
            self.window.after(0, self.window.destroy)
