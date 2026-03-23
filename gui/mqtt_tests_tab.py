import time
import customtkinter as ctk

MAX_FEED_ENTRIES = 500


class MqttTestsTab(ctk.CTkFrame):
    def __init__(self, parent, on_test_hue=None, on_test_sound=None, on_test_full_alarm=None, on_test_heli_sound=None):
        super().__init__(parent)
        self._on_test_hue = on_test_hue
        self._on_test_sound = on_test_sound
        self._on_test_full_alarm = on_test_full_alarm
        self._on_test_heli_sound = on_test_heli_sound
        self._feed_count = 0

        self._build_ui()

    def _build_ui(self):
        # ---- Test buttons ----
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkButton(btn_frame, text="Test Hue Alarm", command=self._test_hue, width=140).pack(side="left", padx=10, pady=5)
        ctk.CTkButton(btn_frame, text="Test Sound", command=self._test_sound, width=140).pack(side="left", padx=10, pady=5)
        ctk.CTkButton(btn_frame, text="Test Heli Sound", command=self._test_heli_sound, width=140).pack(side="left", padx=10, pady=5)
        ctk.CTkButton(
            btn_frame,
            text="Vollständiger Alarm Test",
            command=self._test_full_alarm,
            width=200,
            fg_color="#cc3333",
            hover_color="#aa2222",
            font=("", 13, "bold"),
        ).pack(side="left", padx=10, pady=5)

        # ---- Live MQTT Feed ----
        feed_header = ctk.CTkFrame(self, fg_color="transparent")
        feed_header.pack(fill="x", padx=10, pady=(10, 2))
        ctk.CTkLabel(feed_header, text="Live MQTT Feed", font=("", 14, "bold")).pack(side="left")
        ctk.CTkButton(feed_header, text="Leeren", width=70, height=24,
                      fg_color="#555", hover_color="#444",
                      command=self._clear_feed).pack(side="right")

        self.feed_box = ctk.CTkTextbox(self, height=200, state="disabled", font=("Consolas", 11))
        self.feed_box.pack(fill="both", expand=True, padx=10, pady=(0, 5))

        # ---- Raw Alarm History ----
        alarm_header = ctk.CTkFrame(self, fg_color="transparent")
        alarm_header.pack(fill="x", padx=10, pady=(5, 2))
        ctk.CTkLabel(alarm_header, text="Raw Alarm History", font=("", 14, "bold")).pack(side="left")
        ctk.CTkButton(alarm_header, text="Leeren", width=70, height=24,
                      fg_color="#555", hover_color="#444",
                      command=self._clear_alarm_history).pack(side="right")

        self.alarm_box = ctk.CTkTextbox(self, height=120, state="disabled", font=("Consolas", 11))
        self.alarm_box.pack(fill="both", expand=False, padx=10, pady=(0, 10))

    def append_mqtt_message(self, topic: str, raw: str, is_alarm: bool = False):
        ts = time.strftime("%H:%M:%S")
        line = f"[{ts}] {topic}\n{raw}\n\n"

        self.feed_box.configure(state="normal")
        self.feed_box.insert("end", line)
        self._feed_count += 1

        # trim oldest entries if over limit
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
