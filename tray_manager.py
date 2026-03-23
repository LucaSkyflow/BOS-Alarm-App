import threading
import logging
from PIL import Image, ImageDraw
import pystray

log = logging.getLogger(__name__)


def _make_icon(kind: str) -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((8, 8, 56, 56), outline=(30, 30, 30, 255), width=4)

    colors = {
        "green": (0, 170, 0, 255),
        "red": (220, 0, 0, 255),
        "blue": (0, 110, 255, 255),
        "gray": (120, 120, 120, 255),
    }
    fill = colors.get(kind, (120, 120, 120, 255))
    d.ellipse((16, 16, 48, 48), fill=fill)
    return img


class TrayManager:
    def __init__(self, on_show_window=None, on_test_alarm=None, on_test_sound=None, on_quit=None):
        self._on_show_window = on_show_window
        self._on_test_alarm = on_test_alarm
        self._on_test_sound = on_test_sound
        self._on_quit = on_quit
        self._icon: pystray.Icon | None = None
        self._current_color = "gray"

    def start(self):
        menu = pystray.Menu(
            pystray.MenuItem("Fenster zeigen", self._show_window, default=True),
            pystray.MenuItem("Test Alarm", self._test_alarm),
            pystray.MenuItem("Test Sound", self._test_sound),
            pystray.MenuItem("Beenden", self._quit),
        )

        self._icon = pystray.Icon(
            "bos_alarm_v2",
            _make_icon("gray"),
            "BOS Alarm",
            menu,
        )

        t = threading.Thread(target=self._icon.run, daemon=True)
        t.start()

    def stop(self):
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass

    def set_color(self, kind: str):
        self._current_color = kind
        if self._icon:
            self._icon.icon = _make_icon(kind)
            self._icon.title = f"BOS Alarm — {kind.capitalize()}"

    def _show_window(self, icon=None, item=None):
        if self._on_show_window:
            self._on_show_window()

    def _test_alarm(self, icon=None, item=None):
        if self._on_test_alarm:
            self._on_test_alarm()

    def _test_sound(self, icon=None, item=None):
        if self._on_test_sound:
            self._on_test_sound()

    def _quit(self, icon=None, item=None):
        if self._on_quit:
            self._on_quit()
