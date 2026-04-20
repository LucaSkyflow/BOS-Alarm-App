import os
import re
import sys
import customtkinter as ctk
from gui.dashboard_tab import DashboardTab
from gui.mqtt_tests_tab import MqttTestsTab
from gui.settings_tab import SettingsTab
from gui.sidebar import Sidebar
from gui.theme import BG_ROOT, BG_BASE
from version import VERSION

_GEOMETRY_RE = re.compile(r"^(\d+)x(\d+)([+-]\d+)([+-]\d+)$")


class MainWindow(ctk.CTk):
    def __init__(self, settings, alarm_store, on_test_hue=None, on_test_sound=None, on_apply_settings=None, on_quit=None, on_reset_statistics=None, on_test_full_alarm=None, on_finish_trip=None, on_check_update=None, on_test_heli_sound=None, on_volume_change=None, on_test_kasa=None, on_keepalive_toggle=None, on_keepalive_test=None):
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

        self._settings = settings
        self._on_quit = on_quit
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._apply_saved_geometry(settings.get("window_geometry"))

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
            on_keepalive_toggle=on_keepalive_toggle,
            on_keepalive_test=on_keepalive_test,
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
        self._save_geometry()
        self.withdraw()

    def show(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def quit_app(self):
        self._save_geometry()
        if self._on_quit:
            self._on_quit()
        self.destroy()

    def _save_geometry(self):
        try:
            geom = self.geometry()
            if not _GEOMETRY_RE.match(geom):
                return
            self._settings.set("window_geometry", geom)
            self._settings.save()
        except Exception:
            pass

    def _apply_saved_geometry(self, geom_str):
        if not geom_str:
            return
        match = _GEOMETRY_RE.match(geom_str)
        if not match:
            return
        try:
            w, h = int(match.group(1)), int(match.group(2))
            x, y = int(match.group(3)), int(match.group(4))

            # On Windows, clamp against the full virtual desktop (spans all
            # attached monitors). If the saved center lies outside, the
            # referenced monitor is no longer attached — fall back to default
            # rather than opening off-screen. winfo_vroot* on Win32 reports
            # only the primary monitor, so we use GetSystemMetrics directly.
            bounds = self._virtual_desktop_bounds()
            if bounds is not None:
                vx, vy, vw, vh = bounds
                cx, cy = x + w // 2, y + h // 2
                if not (vx <= cx <= vx + vw and vy <= cy <= vy + vh):
                    return

            self.geometry(geom_str)
        except Exception:
            pass

    def _virtual_desktop_bounds(self):
        if not sys.platform.startswith("win"):
            return None
        try:
            import ctypes
            user32 = ctypes.windll.user32
            left = user32.GetSystemMetrics(76)    # SM_XVIRTUALSCREEN
            top = user32.GetSystemMetrics(77)     # SM_YVIRTUALSCREEN
            width = user32.GetSystemMetrics(78)   # SM_CXVIRTUALSCREEN
            height = user32.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN
            if width > 0 and height > 0:
                return (left, top, width, height)
        except Exception:
            pass
        return None
