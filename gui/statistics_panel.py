import customtkinter as ctk
from gui.theme import (
    BG_SURFACE, BORDER_SUBTLE, STAT_CARD_RADIUS,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY,
    ACCENT_BLUE, GREEN_CONNECTED, RED_DANGER,
    FONT_STAT_NUMBER, FONT_STAT_TITLE, FONT_STAT_SUB,
    FONT_BODY, FONT_BODY_BOLD, FONT_CAPTION,
    PAD_CARD_GAP, PAD_CARD_INTERNAL, PAD_INNER, PAD_TIGHT,
)


class StatisticsPanel(ctk.CTkFrame):
    def __init__(self, parent, alarm_store):
        super().__init__(parent, fg_color="transparent")
        self._store = alarm_store

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        # ── 4-card grid ──
        cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        cards_frame.pack(fill="x")
        for i in range(4):
            cards_frame.grid_columnconfigure(i, weight=1, uniform="stat")

        # Stat card: Heute
        card_today, self._today_val = self._stat_card(cards_frame, "Heute", "Alarme")
        card_today.grid(row=0, column=0, padx=(0, PAD_CARD_GAP // 2), sticky="nsew")

        # Stat card: Woche
        card_week, self._week_val = self._stat_card(cards_frame, "Diese Woche", "Alarme")
        card_week.grid(row=0, column=1, padx=(PAD_CARD_GAP // 2,), sticky="nsew")

        # Stat card: Monat
        card_month, self._month_val = self._stat_card(cards_frame, "Dieser Monat", "Alarme")
        card_month.grid(row=0, column=2, padx=(PAD_CARD_GAP // 2,), sticky="nsew")

        # Status card: Connection status
        self._status_card = ctk.CTkFrame(
            cards_frame, fg_color=BG_SURFACE,
            corner_radius=STAT_CARD_RADIUS,
            border_width=1, border_color=BORDER_SUBTLE,
        )
        self._status_card.grid(row=0, column=3, padx=(PAD_CARD_GAP // 2, 0), sticky="nsew")

        ctk.CTkLabel(
            self._status_card, text="Status",
            font=FONT_STAT_TITLE, text_color=TEXT_SECONDARY, anchor="w",
        ).pack(anchor="w", padx=PAD_CARD_INTERNAL, pady=(PAD_CARD_INTERNAL, PAD_TIGHT))

        # Connection rows
        self._prod_dot, self.mqtt_prod_status = self._status_row(self._status_card, "Production", RED_DANGER, "Getrennt")
        self._stg_dot, self.mqtt_stg_status = self._status_row(self._status_card, "Staging", TEXT_TERTIARY, "Aus")
        self._hue_dot, self.hue_status = self._status_row(self._status_card, "Hue", TEXT_TERTIARY, "Unbekannt")
        self._kasa_dot, self.kasa_status = self._status_row(self._status_card, "Kasa", TEXT_TERTIARY, "Unbekannt")

        # ── Top organizations row ──
        self._org_label = ctk.CTkLabel(
            self, text="Top Organisationen: -",
            font=FONT_CAPTION, text_color=TEXT_TERTIARY, anchor="w",
        )
        self._org_label.pack(fill="x", pady=(PAD_INNER, 0))

    def _stat_card(self, parent, title: str, subtitle: str):
        card = ctk.CTkFrame(
            parent, fg_color=BG_SURFACE,
            corner_radius=STAT_CARD_RADIUS,
            border_width=1, border_color=BORDER_SUBTLE,
        )

        ctk.CTkLabel(
            card, text=title,
            font=FONT_STAT_TITLE, text_color=TEXT_SECONDARY,
        ).pack(padx=PAD_CARD_INTERNAL, pady=(PAD_CARD_INTERNAL, 0))

        val_label = ctk.CTkLabel(
            card, text="0",
            font=FONT_STAT_NUMBER, text_color=ACCENT_BLUE,
        )
        val_label.pack(padx=PAD_CARD_INTERNAL, pady=(PAD_TIGHT, PAD_TIGHT))

        ctk.CTkLabel(
            card, text=subtitle,
            font=FONT_STAT_SUB, text_color=TEXT_TERTIARY,
        ).pack(padx=PAD_CARD_INTERNAL, pady=(0, PAD_CARD_INTERNAL))

        return card, val_label

    def _status_row(self, parent, label: str, dot_color: str, text: str):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=PAD_CARD_INTERNAL, pady=(0, PAD_TIGHT))

        dot = ctk.CTkLabel(row, text="\u25cf", font=FONT_BODY, text_color=dot_color, width=16)
        dot.pack(side="left")

        status_label = ctk.CTkLabel(
            row, text=f"{label}: {text}",
            font=FONT_CAPTION, text_color=TEXT_SECONDARY, anchor="w",
        )
        status_label.pack(side="left", padx=(PAD_TIGHT, 0))

        return dot, status_label

    # ── Public API: status updates (delegated from DashboardTab) ──

    def set_mqtt_status(self, source: str, connected: bool | None, reason: str = ""):
        if source == "production":
            dot = self._prod_dot
            label = self.mqtt_prod_status
            name = "Production"
        else:
            dot = self._stg_dot
            label = self.mqtt_stg_status
            name = "Staging"

        if connected is None:
            dot.configure(text_color=TEXT_TERTIARY)
            label.configure(text=f"{name}: Aus")
        elif connected:
            dot.configure(text_color=GREEN_CONNECTED)
            label.configure(text=f"{name}: Verbunden")
        else:
            text = "Getrennt"
            if reason and reason != "Normal disconnection":
                text = f"Getrennt ({reason})"
            dot.configure(text_color=RED_DANGER)
            label.configure(text=f"{name}: {text}")

    def set_hue_status(self, reachable: bool):
        if reachable:
            self._hue_dot.configure(text_color=GREEN_CONNECTED)
            self.hue_status.configure(text="Hue: Erreichbar")
        else:
            self._hue_dot.configure(text_color=RED_DANGER)
            self.hue_status.configure(text="Hue: Nicht erreichbar")

    def set_kasa_status(self, reachable: bool):
        if reachable:
            self._kasa_dot.configure(text_color=GREEN_CONNECTED)
            self.kasa_status.configure(text="Kasa: Erreichbar")
        else:
            self._kasa_dot.configure(text_color=RED_DANGER)
            self.kasa_status.configure(text="Kasa: Nicht erreichbar")

    # ── Public API: statistics refresh ──

    def refresh(self):
        try:
            today = self._store.count_today()
            week = self._store.count_this_week()
            month = self._store.count_this_month()
            top_orgs = self._store.top_organizations(limit=3)

            self._today_val.configure(text=str(today))
            self._week_val.configure(text=str(week))
            self._month_val.configure(text=str(month))

            if top_orgs:
                org_text = "Top Organisationen: " + " | ".join(
                    f"{name} ({count})" for name, count in top_orgs
                )
            else:
                org_text = "Top Organisationen: -"
            self._org_label.configure(text=org_text)
        except Exception:
            pass
