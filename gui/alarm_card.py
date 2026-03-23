import customtkinter as ctk


class AlarmCard(ctk.CTkFrame):
    def __init__(self, parent, record, on_finish=None, on_delete=None):
        super().__init__(parent, fg_color="#2b2b2b", corner_radius=10, border_width=1, border_color="#3a3a3a")
        self.trip_id = record.trip_id
        self._on_finish = on_finish
        self._on_delete = on_delete
        self._build_ui(record)

    def _build_ui(self, record):
        status = getattr(record, "status", "active")
        badge_text, badge_color = self._status_style(status)

        # ---- Row 1: badge + org (left) + distance (right) ----
        top_row = ctk.CTkFrame(self, fg_color="transparent")
        top_row.pack(fill="x", padx=12, pady=(10, 2))

        self._status_badge = ctk.CTkLabel(
            top_row, text=badge_text, font=("", 11, "bold"),
            text_color="#ffffff", fg_color=badge_color,
            corner_radius=4, width=60,
        )
        self._status_badge.pack(side="left")

        # Distance right-aligned, large, highlighted
        if record.distance:
            dist_km = record.distance / 1000
            dist_str = f"{dist_km:.1f} km" if dist_km >= 1 else f"{record.distance:.0f} m"
        else:
            dist_str = "N/A"
        ctk.CTkLabel(
            top_row, text=dist_str,
            font=("", 15, "bold"), text_color="#ffcc00",
        ).pack(side="right")

        ctk.CTkLabel(
            top_row, text=record.organization,
            font=("", 14, "bold"), text_color="#ffffff",
        ).pack(side="left", padx=(10, 0))

        # ---- Row 2: time + address ----
        info_row = ctk.CTkFrame(self, fg_color="transparent")
        info_row.pack(fill="x", padx=12, pady=(1, 2))

        ctk.CTkLabel(
            info_row, text=f"[{record.local_time}]",
            font=("Consolas", 11), text_color="#777777",
        ).pack(side="left")

        if record.address:
            ctk.CTkLabel(
                info_row, text=record.address,
                font=("", 12), text_color="#aaaaaa", anchor="w",
            ).pack(side="left", padx=(8, 0))

        # ---- Row 3: actions ----
        bottom_row = ctk.CTkFrame(self, fg_color="transparent")
        bottom_row.pack(fill="x", padx=12, pady=(2, 8))

        # Delete button — subtle, text-only style
        self._delete_btn = ctk.CTkButton(
            bottom_row, text="Löschen", width=50, height=22,
            font=("", 10), text_color="#666666",
            fg_color="transparent", hover_color="#3a3a3a",
            command=self._request_delete,
        )
        self._delete_btn.pack(side="right")

        self._finish_btn = ctk.CTkButton(
            bottom_row, text="Beendet", width=80,
            fg_color="#2d8a4e", hover_color="#1e6b39",
            command=self._mark_finished,
        )
        if status in ("active", "confirmed", "return", "in_progress"):
            self._finish_btn.pack(side="right", padx=(0, 5))

    @staticmethod
    def _status_style(status: str) -> tuple[str, str]:
        if status == "rejected":
            return "Abgelehnt", "#aa2222"
        if status == "finished":
            return "Beendet", "#2d8a4e"
        if status == "deleted":
            return "Gelöscht", "#555555"
        if status == "confirmed":
            return "Angenommen", "#1a6ab5"
        if status == "in_progress":
            return "Aktiv", "#cc8800"
        if status == "return":
            return "Rückflug", "#4caf50"
        return "ALARM", "#cc2222"

    def _mark_finished(self):
        self.update_status("finished")
        if self._on_finish:
            self._on_finish(self.trip_id)

    def _request_delete(self):
        if self._on_delete:
            self._on_delete(self.trip_id)

    def update_status(self, new_status: str):
        badge_text, badge_color = self._status_style(new_status)
        self._status_badge.configure(text=badge_text, fg_color=badge_color)
        if new_status in ("rejected", "finished", "deleted"):
            self._finish_btn.pack_forget()
