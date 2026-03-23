import customtkinter as ctk


class AlarmCard(ctk.CTkFrame):
    def __init__(self, parent, record, on_finish=None, on_delete=None):
        super().__init__(parent, fg_color="#2b2b2b", corner_radius=10, border_width=1, border_color="#3a3a3a")
        self.trip_id = record.trip_id
        self._build_ui(record)

    def _build_ui(self, record):
        status = getattr(record, "status", "active")
        badge_text, badge_color = self._status_style(status)

        # ---- Row 1: badge + heli + org (left) + distance (right) ----
        top_row = ctk.CTkFrame(self, fg_color="transparent")
        top_row.pack(fill="x", padx=12, pady=(10, 2))

        self._status_badge = ctk.CTkLabel(
            top_row, text=badge_text, font=("", 11, "bold"),
            text_color="#ffffff", fg_color=badge_color,
            corner_radius=4, width=60,
        )
        self._status_badge.pack(side="left")

        # Helicopter indicator
        self._heli_label = ctk.CTkLabel(
            top_row, text="HELI", font=("", 10, "bold"),
            text_color="#ffffff", fg_color="#cc2222",
            corner_radius=4, width=40,
        )
        if record.incoming_helicopter:
            self._heli_label.pack(side="left", padx=(5, 0))

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
        info_row.pack(fill="x", padx=12, pady=(1, 8))

        ctk.CTkLabel(
            info_row, text=f"[{record.local_time}]",
            font=("Consolas", 11), text_color="#777777",
        ).pack(side="left")

        if record.address:
            ctk.CTkLabel(
                info_row, text=record.address,
                font=("", 12), text_color="#aaaaaa", anchor="w",
            ).pack(side="left", padx=(8, 0))

    @staticmethod
    def _status_style(status: str) -> tuple[str, str]:
        if status == "rejected":
            return "ABGELEHNT", "#aa2222"
        if status == "finished":
            return "BEENDET", "#555555"
        if status == "deleted":
            return "GELÖSCHT", "#555555"
        if status == "confirmed":
            return "BESTÄTIGT", "#2d8a4e"
        if status == "in_progress":
            return "IM EINSATZ", "#1a6ab5"
        if status == "return":
            return "RÜCKFLUG", "#555555"
        return "REQUESTED", "#cc8800"

    def update_status(self, new_status: str):
        badge_text, badge_color = self._status_style(new_status)
        self._status_badge.configure(text=badge_text, fg_color=badge_color)

    def update_helicopter(self, incoming: bool):
        if incoming:
            self._heli_label.pack(side="left", padx=(5, 0))
            # Re-pack after status badge
            self._heli_label.pack_configure(after=self._status_badge)
        else:
            self._heli_label.pack_forget()
