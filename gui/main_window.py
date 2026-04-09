import os
import sys
import customtkinter as ctk
from gui.dashboard_tab import DashboardTab
from gui.mqtt_tests_tab import MqttTestsTab
from gui.settings_tab import SettingsTab
from gui.sidebar import Sidebar
from gui.theme import BG_ROOT, BG_BASE
from version import VERSION


class MainWindow(ctk.CTk):
    def __init__(self, settings, alarm_store, on_test_hue=None, on_test_sound=None, on_apply_settings=None, on_quit=None, on_reset_statistics=None, on_test_full_alarm=None, on_finish_trip=None, on_check_update=None, on_test_heli_sound=None, on_volume_change=None, on_test_kasa=None):
        super().__init__()

        self.title(f"BOS Alarm \u2014 v{VERSION}")
        if getattr(sys, "frozen", False):
            _ico = os.path.join(sys._MEIPASS, "Blaulicht.ico")
        else:
            _ico = os.path.join(os.path.dirname(__file__), "..", "Blaulicht.ico")
        if os.path.exists(_ico):
            self.iconbitmap(_ico)
        self.geometry("1050x750")
        self.minsize(900, 600)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=BG_ROOT)

        self._on_quit = on_quit
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # ── Sidebar navigation ──
        self._sidebar = Sidebar(
            self,
            on_navigate=self._switch_page,
            on_quit=self._on_quit,
            version=VERSION,
        )
        self._sidebar.pack(side="left", fill="y")

        # ── Content area ──
        self._content_area = ctk.CTkFrame(self, fg_color=BG_BASE, corner_radius=0)
        self._content_area.pack(side="left", fill="both", expand=True)

        # ── Pages ──
        self.dashboard = DashboardTab(
            self._content_area,
            alarm_store=alarm_store,
            settings=settings,
            on_finish_trip=on_finish_trip,
            on_volume_change=on_volume_change,
        )

        self.mqtt_tab = MqttTestsTab(
            self._content_area,
            on_test_hue=on_test_hue,
            on_test_sound=on_test_sound,
            on_test_full_alarm=on_test_full_alarm,
            on_test_heli_sound=on_test_heli_sound,
            on_test_kasa=on_test_kasa,
        )

        self.settings_tab = SettingsTab(
            self._content_area,
            settings,
            on_apply=on_apply_settings,
            on_reset_statistics=on_reset_statistics,
            on_check_update=on_check_update,
        )

        self._pages = {
            "dashboard": self.dashboard,
            "mqtt": self.mqtt_tab,
            "settings": self.settings_tab,
        }
        self._active_page = None
        self._switch_page("dashboard")

    def _switch_page(self, page_name: str):
        if page_name == self._active_page:
            return
        for frame in self._pages.values():
            frame.pack_forget()
        self._pages[page_name].pack(fill="both", expand=True)
        self._active_page = page_name
        self._sidebar.set_active(page_name)

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
