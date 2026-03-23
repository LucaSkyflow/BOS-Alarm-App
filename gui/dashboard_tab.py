import customtkinter as ctk

from gui.alarm_card import AlarmCard
from gui.helicopter_banner import HelicopterBanner
from gui.statistics_panel import StatisticsPanel


class DashboardTab(ctk.CTkFrame):
    def __init__(self, parent, alarm_store, settings, on_finish_trip=None):
        super().__init__(parent)
        self._store = alarm_store
        self._settings = settings
        self._on_finish_trip = on_finish_trip

        self._card_map: dict[str, AlarmCard] = {}
        self._alarm_blink_active = False
        self._alarm_blink_job = None
        self._alarm_blink_stop_job = None
        self._build_ui()

    def _build_ui(self):
        # ---- Helicopter Banner (hidden by default) ----
        self.helicopter_banner = HelicopterBanner(self)

        # ---- Status bar ----
        status_frame = ctk.CTkFrame(self)
        status_frame.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(status_frame, text="Production:").pack(side="left", padx=(10, 2))
        self.mqtt_prod_status = ctk.CTkLabel(status_frame, text="Getrennt", text_color="red", font=("", 13, "bold"))
        self.mqtt_prod_status.pack(side="left", padx=(0, 15))

        ctk.CTkLabel(status_frame, text="Staging:").pack(side="left", padx=(0, 2))
        self.mqtt_stg_status = ctk.CTkLabel(status_frame, text="Aus", text_color="gray", font=("", 13, "bold"))
        self.mqtt_stg_status.pack(side="left", padx=(0, 15))

        ctk.CTkLabel(status_frame, text="Hue:").pack(side="left", padx=(0, 2))
        self.hue_status = ctk.CTkLabel(status_frame, text="Unbekannt", text_color="gray", font=("", 13, "bold"))
        self.hue_status.pack(side="left", padx=(0, 15))

        # ---- Update Banner (hidden by default) ----
        # ---- Statistics Panel ----
        self.stats_panel = StatisticsPanel(self, self._store)
        self.stats_panel.pack(fill="x", padx=10, pady=(5, 5))

        # ---- Alarm History Label ----
        ctk.CTkLabel(self, text="Alarm Historie", font=("", 14, "bold")).pack(anchor="w", padx=10, pady=(5, 2))

        # ---- Scrollable Alarm Cards ----
        self._cards_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._cards_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def set_update_status(self, message: str, color: str = "#aaaaaa"):
        pass  # Update status only shown in settings tab

    def set_mqtt_status(self, source: str, connected: bool | None, reason: str = ""):
        if source == "production":
            label = self.mqtt_prod_status
        else:
            label = self.mqtt_stg_status

        if connected is None:
            label.configure(text="Aus", text_color="gray")
        elif connected:
            label.configure(text="Verbunden", text_color="#00cc00")
        else:
            text = "Getrennt"
            if reason and reason != "Normal disconnection":
                text = f"Getrennt ({reason})"
            label.configure(text=text, text_color="red")

    def set_hue_status(self, reachable: bool):
        if reachable:
            self.hue_status.configure(text="Erreichbar", text_color="#00cc00")
        else:
            self.hue_status.configure(text="Nicht erreichbar", text_color="red")

    def load_history(self):
        records = self._store.get_all(limit=200)
        for record in records:
            card = AlarmCard(self._cards_container, record, on_finish=self._on_finish_trip, on_delete=self._delete_alarm)
            card.pack(fill="x", pady=(0, 8))
            self._card_map[record.trip_id] = card

    def add_alarm(self, record):
        # Insert new card at the top
        card = AlarmCard(self._cards_container, record, on_finish=self._on_finish_trip, on_delete=self._delete_alarm)
        card.pack(fill="x", pady=(0, 8))
        self._card_map[record.trip_id] = card

        # Move to top — repack all children with new card first
        children = self._cards_container.winfo_children()
        for child in children:
            child.pack_forget()
        card.pack(fill="x", pady=(0, 8))
        for child in children:
            if child is not card:
                child.pack(fill="x", pady=(0, 8))

        # Show helicopter banner if incoming
        if record.incoming_helicopter:
            self.helicopter_banner.show()

        # Refresh statistics
        self.stats_panel.refresh()

    def _delete_alarm(self, trip_id: str):
        self._store.delete_alarm(trip_id)
        card = self._card_map.pop(trip_id, None)
        if card:
            card.destroy()
        self.stats_panel.refresh()

    def update_card_status(self, trip_id: str, status: str):
        card = self._card_map.get(trip_id)
        if card:
            card.update_status(status)

    def update_card_helicopter(self, trip_id: str, incoming: bool):
        card = self._card_map.get(trip_id)
        if card:
            card.update_helicopter(incoming)

    def clear_and_refresh(self):
        for child in self._cards_container.winfo_children():
            child.destroy()
        self._card_map.clear()
        self.stats_panel.refresh()

    def show_helicopter_banner(self, trip_id: str = None):
        self.helicopter_banner.show(trip_id)

    def dismiss_helicopter_banner(self, trip_id: str = None):
        self.helicopter_banner.dismiss(trip_id)

    # ---- Alarm blink (blue flash on cards container) ----
    def start_alarm_blink(self):
        if self._alarm_blink_active:
            return
        self._alarm_blink_active = True
        duration = self._settings.get("alarm_light_seconds", 20.0)
        interval_sec = self._settings.get("dashboard_blink_interval", 0.15)
        interval_ms = max(int(float(interval_sec) * 1000), 50)
        self._blink_tick(interval_ms)
        self._alarm_blink_stop_job = self.after(int(float(duration) * 1000), self.stop_alarm_blink)

    def _blink_tick(self, interval_ms: int = 150):
        if not self._alarm_blink_active:
            return
        current = self._cards_container.cget("fg_color")
        next_color = "#1a1a2e" if current == "#0044aa" else "#0044aa"
        self._cards_container.configure(fg_color=next_color)
        self._alarm_blink_job = self.after(interval_ms, self._blink_tick, interval_ms)

    def stop_alarm_blink(self):
        self._alarm_blink_active = False
        if self._alarm_blink_job:
            self.after_cancel(self._alarm_blink_job)
            self._alarm_blink_job = None
        if self._alarm_blink_stop_job:
            self.after_cancel(self._alarm_blink_stop_job)
            self._alarm_blink_stop_job = None
        self._cards_container.configure(fg_color="transparent")
