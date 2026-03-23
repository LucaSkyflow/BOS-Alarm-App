import customtkinter as ctk


class HelicopterBanner(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, height=60, corner_radius=0, fg_color="#cc0000")
        self._blink_state = True
        self._blink_job = None
        self._active = False
        self._trip_id = None

        self._build_ui()
        # Start hidden
        self.pack_forget()

    def _build_ui(self):
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="both", expand=True)

        self._label = ctk.CTkLabel(
            inner,
            text="!! HELIKOPTER IM ANFLUG !!",
            font=("", 22, "bold"),
            text_color="#ffffff",
        )
        self._label.pack(expand=True, padx=20, pady=10)

    def show(self, trip_id: str = None):
        self._trip_id = trip_id
        if self._active:
            return
        self._active = True

        self.pack(fill="x", padx=0, pady=0, before=self._get_first_sibling())
        self._start_blink()

    def dismiss(self, trip_id: str = None):
        # Only dismiss if it's for the same trip (or no trip specified)
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
        color = "#cc0000" if self._blink_state else "#660000"
        self.configure(fg_color=color)
        self._blink_job = self.after(500, self._start_blink)

    def _get_first_sibling(self):
        parent = self.master
        children = parent.winfo_children()
        for child in children:
            if child is not self and child.winfo_manager():
                return child
        return None
