import os
import customtkinter as ctk
from gui.dashboard_tab import DashboardTab
from gui.mqtt_tests_tab import MqttTestsTab
from gui.settings_tab import SettingsTab
from version import VERSION


class MainWindow(ctk.CTk):
    def __init__(self, settings, alarm_store, on_test_hue=None, on_test_sound=None, on_apply_settings=None, on_quit=None, on_reset_statistics=None, on_test_full_alarm=None, on_finish_trip=None):
        super().__init__()

        self.title(f"BOS Alarm — v{VERSION}")
        _ico = os.path.join(os.path.dirname(__file__), "..", "Blaulicht.ico")
        if os.path.exists(_ico):
            self.iconbitmap(_ico)
        self.geometry("900x700")
        self.minsize(700, 500)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._on_quit = on_quit

        # intercept window close -> hide to tray
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Top bar with quit button (right-aligned)
        top_bar = ctk.CTkFrame(self, height=36, fg_color="transparent")
        top_bar.pack(fill="x", padx=10, pady=(10, 0))

        quit_btn = ctk.CTkButton(
            top_bar,
            text="✕  Beenden",
            width=110,
            height=28,
            fg_color="#c0392b",
            hover_color="#922b21",
            command=self._on_quit,
        )
        quit_btn.pack(side="right")

        # Tabs (pady oben reduziert, da top_bar bereits pady=(10,0) hat)
        tabview = ctk.CTkTabview(self)
        tabview.pack(fill="both", expand=True, padx=10, pady=(4, 10))

        tabview.add("Dashboard")
        tabview.add("MQTT & Tests")
        tabview.add("Einstellungen")

        self.dashboard = DashboardTab(
            tabview.tab("Dashboard"),
            alarm_store=alarm_store,
            settings=settings,
            on_finish_trip=on_finish_trip,
        )
        self.dashboard.pack(fill="both", expand=True)

        self.mqtt_tab = MqttTestsTab(
            tabview.tab("MQTT & Tests"),
            on_test_hue=on_test_hue,
            on_test_sound=on_test_sound,
            on_test_full_alarm=on_test_full_alarm,
        )
        self.mqtt_tab.pack(fill="both", expand=True)

        self.settings_tab = SettingsTab(
            tabview.tab("Einstellungen"),
            settings,
            on_apply=on_apply_settings,
            on_reset_statistics=on_reset_statistics,
        )
        self.settings_tab.pack(fill="both", expand=True)

    def _on_close(self):
        self.withdraw()

    def show(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def quit_app(self):
        if self._on_quit:
            self._on_quit()
        self.destroy()
