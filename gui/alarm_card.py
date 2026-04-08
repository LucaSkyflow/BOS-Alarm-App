import customtkinter as ctk
from gui.theme import (
    BG_SURFACE, BG_ELEVATED, BORDER_SUBTLE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY,
    YELLOW_HIGHLIGHT, HELI_BADGE, STAGING_BADGE,
    STATUS_REQUESTED, STATUS_CONFIRMED, STATUS_IN_PROGRESS,
    STATUS_REJECTED, STATUS_FINISHED, STATUS_DELETED, STATUS_RETURN,
    FONT_H3, FONT_BODY_BOLD, FONT_SMALL, FONT_MONO_SMALL, FONT_BADGE, FONT_CAPTION,
    CARD_BORDER_WIDTH, BADGE_CORNER_RADIUS, ACCENT_STRIP_WIDTH,
    PAD_INNER, PAD_TIGHT,
)


class AlarmCard(ctk.CTkFrame):
    """Compact alarm card with fixed height and clear info hierarchy."""

    CARD_HEIGHT = 66

    def __init__(self, parent, record, on_finish=None, on_delete=None):
        super().__init__(
            parent, fg_color=BG_SURFACE,
            corner_radius=8, height=self.CARD_HEIGHT,
            border_width=CARD_BORDER_WIDTH, border_color=BORDER_SUBTLE,
        )
        self.pack_propagate(False)
        self.trip_id = record.trip_id
        self.timestamp = record.timestamp
        self._on_delete = on_delete
        self._build_ui(record)

    def _build_ui(self, record):
        status = getattr(record, "status", "active")
        source = getattr(record, "source", "production")
        badge_text, badge_color = self._status_style(status)

        # ── Accent strip ──
        self._accent_strip = ctk.CTkFrame(
            self, fg_color=badge_color,
            width=ACCENT_STRIP_WIDTH, corner_radius=3,
        )
        self._accent_strip.pack(side="left", fill="y", padx=(5, 8), pady=6)

        # ── Content area ──
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=(6, 6))

        # ── Row 1: Status + Org + Distance ──
        row1 = ctk.CTkFrame(content, fg_color="transparent")
        row1.pack(fill="x")

        self._status_badge = ctk.CTkLabel(
            row1, text=badge_text, font=FONT_BADGE,
            text_color=TEXT_PRIMARY, fg_color=badge_color,
            corner_radius=BADGE_CORNER_RADIUS, width=78, height=22,
        )
        self._status_badge.pack(side="left")

        if source == "staging":
            ctk.CTkLabel(
                row1, text="STG", font=FONT_BADGE,
                text_color=TEXT_PRIMARY, fg_color=STAGING_BADGE,
                corner_radius=BADGE_CORNER_RADIUS, width=34, height=22,
            ).pack(side="left", padx=(4, 0))

        self._heli_label = ctk.CTkLabel(
            row1, text="\u2708 HELI", font=FONT_BADGE,
            text_color=TEXT_PRIMARY, fg_color=HELI_BADGE,
            corner_radius=BADGE_CORNER_RADIUS, width=48, height=22,
        )
        if record.incoming_helicopter:
            self._heli_label.pack(side="left", padx=(4, 0))

        ctk.CTkLabel(
            row1, text=record.organization,
            font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY, height=22,
        ).pack(side="left", padx=(10, 0))

        # Delete (rightmost)
        if self._on_delete:
            del_btn = ctk.CTkLabel(
                row1, text="\u2715", font=FONT_CAPTION,
                text_color=TEXT_TERTIARY, cursor="hand2", width=20, height=22,
            )
            del_btn.pack(side="right")
            del_btn.bind("<Button-1>", lambda e: self._on_delete(self.trip_id))

        # Distance
        if record.distance:
            dist_km = record.distance / 1000
            dist_str = f"{dist_km:.1f} km" if dist_km >= 1 else f"{record.distance:.0f} m"
        else:
            dist_str = ""
        if dist_str:
            ctk.CTkLabel(
                row1, text=dist_str,
                font=FONT_BODY_BOLD, text_color=YELLOW_HIGHLIGHT, height=22,
            ).pack(side="right", padx=(0, 6))

        # ── Row 2: Date/Time · Address ──
        row2 = ctk.CTkFrame(content, fg_color="transparent")
        row2.pack(fill="x", pady=(2, 0))

        # Ensure date+time is shown even for old DB entries that only have HH:MM
        time_text = record.local_time
        if time_text and len(time_text) <= 5 and record.timestamp:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(record.timestamp.replace("Z", "+00:00")).astimezone()
                time_text = dt.strftime("%d.%m.%Y %H:%M")
            except Exception:
                pass
        addr_text = record.address or ""
        if addr_text:
            info = f"{time_text}  \u00b7  {addr_text}"
        else:
            info = time_text

        ctk.CTkLabel(
            row2, text=info,
            font=FONT_SMALL, text_color=TEXT_SECONDARY, anchor="w", height=20,
        ).pack(side="left")

    @staticmethod
    def _status_style(status: str) -> tuple[str, str]:
        if status == "rejected":
            return "ABGELEHNT", STATUS_REJECTED
        if status == "finished":
            return "BEENDET", STATUS_FINISHED
        if status == "deleted":
            return "GEL\u00d6SCHT", STATUS_DELETED
        if status == "confirmed":
            return "BEST\u00c4TIGT", STATUS_CONFIRMED
        if status == "in_progress":
            return "IM EINSATZ", STATUS_IN_PROGRESS
        if status == "return":
            return "R\u00dcCKFLUG", STATUS_RETURN
        return "REQUESTED", STATUS_REQUESTED

    def update_status(self, new_status: str):
        badge_text, badge_color = self._status_style(new_status)
        self._status_badge.configure(text=badge_text, fg_color=badge_color)
        self._accent_strip.configure(fg_color=badge_color)

    def update_helicopter(self, incoming: bool):
        if incoming:
            self._heli_label.pack(side="left", padx=(4, 0))
            self._heli_label.pack_configure(after=self._status_badge)
        else:
            self._heli_label.pack_forget()
