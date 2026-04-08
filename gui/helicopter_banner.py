import customtkinter as ctk
from gui.theme import (
    HELI_BRIGHT, HELI_DARK, TEXT_PRIMARY,
    FONT_BANNER, PAD_INNER, PAD_PAGE,
)


class HelicopterBanner(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, height=80, corner_radius=0, fg_color=HELI_BRIGHT)
        self._blink_state = True
        self._blink_job = None
        self._active = False
        self._trip_id = None

        self._build_ui()
        self.pack_forget()

    def _build_ui(self):
        self._inner = ctk.CTkFrame(self, fg_color=HELI_DARK, corner_radius=10)
        self._inner.pack(fill="both", expand=True, padx=5, pady=5)

        self._label = ctk.CTkLabel(
            self._inner,
            text="\u26a0  HELIKOPTER IM ANFLUG  \u26a0",
            font=FONT_BANNER,
            text_color=TEXT_PRIMARY,
        )
        self._label.pack(expand=True, padx=PAD_PAGE, pady=PAD_INNER)

    def show(self, trip_id: str = None):
        self._trip_id = trip_id
        if self._active:
            return
        self._active = True
        self.pack(fill="x", padx=PAD_PAGE, pady=(PAD_PAGE, 0), before=self._get_first_sibling())
        self._start_blink()

    def dismiss(self, trip_id: str = None):
        if trip_id and self._trip_id and trip_id != self._trip_id:
            return
        if not self._active:
            return
        self._active = False
        self._trip_id = None
        if self._blink_job:
            self.after_cancel(self._blink_job)
            self._blink_job = None
        self.pack_forget()

    def _start_blink(self):
        if not self._active:
            return
        self._blink_state = not self._blink_state
        color = HELI_BRIGHT if self._blink_state else HELI_DARK
        self.configure(fg_color=color)
        self._blink_job = self.after(500, self._start_blink)

    def _get_first_sibling(self):
        parent = self.master
        children = parent.winfo_children()
        for child in children:
            if child is not self and child.winfo_manager():
                return child
        return None
