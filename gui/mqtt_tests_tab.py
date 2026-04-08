import time
import customtkinter as ctk
from gui.theme import (
    BG_SURFACE, BORDER_SUBTLE, PANEL_CORNER_RADIUS,
    TEXT_PRIMARY, RED_DANGER, RED_DANGER_HOVER,
    BTN_SECONDARY_FG, BTN_SECONDARY_HOVER,
    FONT_H3, FONT_BODY, FONT_BODY_BOLD, FONT_CAPTION, FONT_MONO_SMALL,
    BUTTON_CORNER_RADIUS, BUTTON_HEIGHT,
    PAD_PAGE, PAD_CARD_GAP, PAD_INNER,
)

MAX_FEED_ENTRIES = 500


class MqttTestsTab(ctk.CTkFrame):
    def __init__(self, parent, on_test_hue=None, on_test_sound=None, on_test_full_alarm=None, on_test_heli_sound=None):
        super().__init__(parent, fg_color="transparent")
        self._on_test_hue = on_test_hue
        self._on_test_sound = on_test_sound
        self._on_test_full_alarm = on_test_full_alarm
        self._on_test_heli_sound = on_test_heli_sound
        self._feed_count = 0
        self._build_ui()

    def _build_ui(self):
        # ── Test buttons in card with grid ──
        btn_card = ctk.CTkFrame(
            self, fg_color=BG_SURFACE,
            corner_radius=PANEL_CORNER_RADIUS,
            border_width=1, border_color=BORDER_SUBTLE,
        )
        btn_card.pack(fill="x", padx=PAD_PAGE, pady=(PAD_PAGE, PAD_CARD_GAP))

        btn_inner = ctk.CTkFrame(btn_card, fg_color="transparent")
        btn_inner.pack(fill="x", padx=PAD_INNER, pady=PAD_INNER)
        for i in range(4):
            btn_inner.grid_columnconfigure(i, weight=1, uniform="btn")

        ctk.CTkButton(
            btn_inner, text="\u2600  Test Hue", command=self._test_hue,
            height=BUTTON_HEIGHT, corner_radius=BUTTON_CORNER_RADIUS,
            fg_color=BTN_SECONDARY_FG, hover_color=BTN_SECONDARY_HOVER, font=FONT_BODY,
        ).grid(row=0, column=0, padx=PAD_INNER // 2, sticky="ew")

        ctk.CTkButton(
            btn_inner, text="\u266b  Test Sound", command=self._test_sound,
            height=BUTTON_HEIGHT, corner_radius=BUTTON_CORNER_RADIUS,
            fg_color=BTN_SECONDARY_FG, hover_color=BTN_SECONDARY_HOVER, font=FONT_BODY,
        ).grid(row=0, column=1, padx=PAD_INNER // 2, sticky="ew")

        ctk.CTkButton(
            btn_inner, text="\u2708  Test Heli", command=self._test_heli_sound,
            height=BUTTON_HEIGHT, corner_radius=BUTTON_CORNER_RADIUS,
            fg_color=BTN_SECONDARY_FG, hover_color=BTN_SECONDARY_HOVER, font=FONT_BODY,
        ).grid(row=0, column=2, padx=PAD_INNER // 2, sticky="ew")

        ctk.CTkButton(
            btn_inner, text="Vollst\u00e4ndiger Alarm", command=self._test_full_alarm,
            height=BUTTON_HEIGHT, corner_radius=BUTTON_CORNER_RADIUS,
            fg_color=RED_DANGER, hover_color=RED_DANGER_HOVER, font=FONT_BODY_BOLD,
        ).grid(row=0, column=3, padx=PAD_INNER // 2, sticky="ew")

        # ── Live MQTT Feed ──
        feed_header = ctk.CTkFrame(self, fg_color="transparent")
        feed_header.pack(fill="x", padx=PAD_PAGE, pady=(PAD_INNER, PAD_INNER // 2))
        ctk.CTkLabel(feed_header, text="Live MQTT Feed", font=FONT_H3, text_color=TEXT_PRIMARY).pack(side="left")
        ctk.CTkButton(
            feed_header, text="Leeren", width=70, height=26,
            corner_radius=BUTTON_CORNER_RADIUS,
            fg_color=BTN_SECONDARY_FG, hover_color=BTN_SECONDARY_HOVER,
            font=FONT_CAPTION, command=self._clear_feed,
        ).pack(side="right")

        self.feed_box = ctk.CTkTextbox(
            self, height=200, state="disabled", font=FONT_MONO_SMALL,
            fg_color=BG_SURFACE, border_width=1, border_color=BORDER_SUBTLE,
            corner_radius=PANEL_CORNER_RADIUS,
        )
        self.feed_box.pack(fill="both", expand=True, padx=PAD_PAGE, pady=(0, PAD_CARD_GAP))

        # ── Raw Alarm History ──
        alarm_header = ctk.CTkFrame(self, fg_color="transparent")
        alarm_header.pack(fill="x", padx=PAD_PAGE, pady=(0, PAD_INNER // 2))
        ctk.CTkLabel(alarm_header, text="Raw Alarm History", font=FONT_H3, text_color=TEXT_PRIMARY).pack(side="left")
        ctk.CTkButton(
            alarm_header, text="Leeren", width=70, height=26,
            corner_radius=BUTTON_CORNER_RADIUS,
            fg_color=BTN_SECONDARY_FG, hover_color=BTN_SECONDARY_HOVER,
            font=FONT_CAPTION, command=self._clear_alarm_history,
        ).pack(side="right")

        self.alarm_box = ctk.CTkTextbox(
            self, height=120, state="disabled", font=FONT_MONO_SMALL,
            fg_color=BG_SURFACE, border_width=1, border_color=BORDER_SUBTLE,
            corner_radius=PANEL_CORNER_RADIUS,
        )
        self.alarm_box.pack(fill="both", expand=False, padx=PAD_PAGE, pady=(0, PAD_PAGE))

    def append_mqtt_message(self, topic: str, raw: str, is_alarm: bool = False):
        ts = time.strftime("%H:%M:%S")
        line = f"[{ts}] {topic}\n{raw}\n\n"

        self.feed_box.configure(state="normal")
        self.feed_box.insert("end", line)
        self._feed_count += 1

        if self._feed_count > MAX_FEED_ENTRIES:
            content = self.feed_box.get("1.0", "end")
            lines = content.split("\n\n", 1)
            if len(lines) > 1:
                self.feed_box.delete("1.0", "end")
                self.feed_box.insert("1.0", lines[1])
                self._feed_count -= 1

        self.feed_box.configure(state="disabled")
        self.feed_box.see("end")

        if is_alarm:
            self._append_alarm(topic, raw)

    def _append_alarm(self, topic: str, raw: str):
        ts = time.strftime("%H:%M:%S")
        line = f"[{ts}] ALARM  {topic}\n{raw}\n\n"
        self.alarm_box.configure(state="normal")
        self.alarm_box.insert("end", line)
        self.alarm_box.configure(state="disabled")
        self.alarm_box.see("end")

    def _clear_feed(self):
        self.feed_box.configure(state="normal")
        self.feed_box.delete("1.0", "end")
        self.feed_box.configure(state="disabled")
        self._feed_count = 0

    def _clear_alarm_history(self):
        self.alarm_box.configure(state="normal")
        self.alarm_box.delete("1.0", "end")
        self.alarm_box.configure(state="disabled")

    def _test_hue(self):
        if self._on_test_hue:
            self._on_test_hue()

    def _test_sound(self):
        if self._on_test_sound:
            self._on_test_sound()

    def _test_heli_sound(self):
        if self._on_test_heli_sound:
            self._on_test_heli_sound()

    def _test_full_alarm(self):
        if self._on_test_full_alarm:
            self._on_test_full_alarm()
