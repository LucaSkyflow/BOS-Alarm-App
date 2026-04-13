import customtkinter as ctk

from gui.alarm_card import AlarmCard
from gui.helicopter_banner import HelicopterBanner
from gui.statistics_panel import StatisticsPanel
from gui.theme import (
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY,
    ACCENT_BLUE, ALARM_BANNER_BRIGHT, ALARM_BANNER_DARK,
    FONT_H3, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL,
    PANEL_CORNER_RADIUS,
    PAD_PAGE, PAD_CARD_GAP, PAD_INNER, PAD_TIGHT,
)


class DashboardTab(ctk.CTkFrame):
    def __init__(self, parent, alarm_store, settings, on_finish_trip=None, on_volume_change=None):
        super().__init__(parent, fg_color="transparent")
        self._store = alarm_store
        self._settings = settings
        self._on_finish_trip = on_finish_trip
        self._on_volume_change = on_volume_change

        self._card_map: dict[str, AlarmCard] = {}
        self._alarm_blink_active = False
        self._alarm_blink_job = None
        self._alarm_blink_stop_job = None
        self._build_ui()

    def _build_ui(self):
        # ── Helicopter Banner (hidden by default) ──
        self.helicopter_banner = HelicopterBanner(self)

        # ── Statistics Panel ──
        self.stats_panel = StatisticsPanel(self, self._store)
        self.stats_panel.pack(fill="x", padx=PAD_PAGE, pady=(PAD_PAGE, PAD_CARD_GAP))

        # ── Volume slider row ──
        self._vol_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._vol_frame.pack(fill="x", padx=PAD_PAGE, pady=(0, PAD_CARD_GAP))

        ctk.CTkLabel(self._vol_frame, text="\U0001f50a", font=FONT_BODY, text_color=TEXT_SECONDARY).pack(side="left", padx=(0, PAD_INNER))

        initial_vol = float(self._settings.get("volume", 0.8))
        self._volume_slider = ctk.CTkSlider(
            self._vol_frame, from_=0, to=1, number_of_steps=100,
            command=self._on_volume_slider,
        )
        self._volume_slider.set(initial_vol)
        self._volume_slider.pack(side="left", fill="x", expand=True)

        self._vol_label = ctk.CTkLabel(self._vol_frame, text=f"{int(initial_vol * 100)}%", font=FONT_SMALL, text_color=TEXT_TERTIARY, width=40)
        self._vol_label.pack(side="left", padx=(PAD_INNER, 0))

        # ── Alarm active banner (created here but hidden) ──
        self._alarm_banner = ctk.CTkFrame(
            self, fg_color=ALARM_BANNER_BRIGHT,
            corner_radius=PANEL_CORNER_RADIUS, height=36,
        )
        self._alarm_banner_label = ctk.CTkLabel(
            self._alarm_banner, text="\u26a0  ALARM AKTIV",
            font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY,
        )
        self._alarm_banner_label.pack(expand=True, padx=PAD_INNER, pady=PAD_TIGHT)
        # Don't pack — will be shown via start_alarm_blink

        # ── Alarm History header ──
        self._history_header = ctk.CTkFrame(self, fg_color="transparent")
        self._history_header.pack(fill="x", padx=PAD_PAGE, pady=(0, PAD_INNER))
        ctk.CTkFrame(self._history_header, fg_color=ACCENT_BLUE, width=3, height=18, corner_radius=2).pack(side="left", padx=(0, PAD_INNER))
        ctk.CTkLabel(self._history_header, text="Alarm Historie", font=FONT_H3, text_color=TEXT_PRIMARY).pack(side="left")

        # ── Scrollable Alarm Cards ──
        self._cards_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._cards_container.pack(fill="both", expand=True, padx=PAD_PAGE, pady=(0, PAD_PAGE))

    def _on_volume_slider(self, value):
        self._vol_label.configure(text=f"{int(value * 100)}%")
        if self._on_volume_change:
            self._on_volume_change(value)

    # ── Status delegation ──

    def set_update_status(self, message: str, color: str = "#aaaaaa"):
        pass

    def set_mqtt_status(self, source: str, connected: bool | None, reason: str = ""):
        self.stats_panel.set_mqtt_status(source, connected, reason)

    def set_hue_status(self, reachable: bool):
        self.stats_panel.set_hue_status(reachable)

    def set_kasa_status(self, reachable: bool):
        self.stats_panel.set_kasa_status(reachable)

    def set_keepalive_status(self, active: bool, detail: str = ""):
        self.stats_panel.set_keepalive_status(active, detail)

    # ── Alarm card management ──

    def load_history(self):
        records = self._store.get_all(limit=200)
        for record in records:
            card = AlarmCard(self._cards_container, record, on_finish=self._on_finish_trip, on_delete=self._delete_alarm)
            card.pack(fill="x", pady=(0, PAD_TIGHT))
            self._card_map[record.trip_id] = card

    def add_alarm(self, record):
        card = AlarmCard(self._cards_container, record, on_finish=self._on_finish_trip, on_delete=self._delete_alarm)
        self._card_map[record.trip_id] = card
        self._resort_cards()

        if record.incoming_helicopter:
            self.helicopter_banner.show()
        self.stats_panel.refresh()

    def _resort_cards(self):
        """Re-sort all alarm cards by timestamp, newest first."""
        cards = [c for c in self._cards_container.winfo_children() if hasattr(c, "timestamp")]
        for c in cards:
            c.pack_forget()
        cards.sort(key=lambda c: c.timestamp, reverse=True)
        for c in cards:
            c.pack(fill="x", pady=(0, PAD_TIGHT))

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

    def update_card_description(self, trip_id: str, description: str):
        card = self._card_map.get(trip_id)
        if card:
            card.update_description(description)

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

    # ── Alarm blink: red pulsing "ALARM AKTIV" banner ──

    def start_alarm_blink(self):
        if self._alarm_blink_active:
            return
        self._alarm_blink_active = True
        duration = self._settings.get("alarm_light_seconds", 20.0)
        # Show banner between volume row and history header
        self._alarm_banner.pack(fill="x", padx=PAD_PAGE, pady=(0, PAD_INNER), after=self._vol_frame)
        self._blink_tick()
        self._alarm_blink_stop_job = self.after(int(float(duration) * 1000), self.stop_alarm_blink)

    def _blink_tick(self):
        if not self._alarm_blink_active:
            return
        current = self._alarm_banner.cget("fg_color")
        if isinstance(current, (list, tuple)):
            current = current[0]
        next_color = ALARM_BANNER_DARK if current == ALARM_BANNER_BRIGHT else ALARM_BANNER_BRIGHT
        self._alarm_banner.configure(fg_color=next_color)
        self._alarm_blink_job = self.after(400, self._blink_tick)

    def stop_alarm_blink(self):
        self._alarm_blink_active = False
        if self._alarm_blink_job:
            self.after_cancel(self._alarm_blink_job)
            self._alarm_blink_job = None
        if self._alarm_blink_stop_job:
            self.after_cancel(self._alarm_blink_stop_job)
            self._alarm_blink_stop_job = None
        self._alarm_banner.pack_forget()
