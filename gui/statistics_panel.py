import customtkinter as ctk


class StatisticsPanel(ctk.CTkFrame):
    def __init__(self, parent, alarm_store):
        super().__init__(parent, fg_color="#1e1e1e", corner_radius=8)
        self._store = alarm_store

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        # ---- Counts row ----
        counts_frame = ctk.CTkFrame(self, fg_color="transparent")
        counts_frame.pack(fill="x", padx=10, pady=(8, 4))

        ctk.CTkLabel(counts_frame, text="Statistik:", font=("", 13, "bold")).pack(side="left", padx=(0, 10))

        self._today_label = ctk.CTkLabel(counts_frame, text="Heute: 0", font=("", 12))
        self._today_label.pack(side="left", padx=(0, 15))

        self._week_label = ctk.CTkLabel(counts_frame, text="Diese Woche: 0", font=("", 12))
        self._week_label.pack(side="left", padx=(0, 15))

        self._month_label = ctk.CTkLabel(counts_frame, text="Dieser Monat: 0", font=("", 12))
        self._month_label.pack(side="left")

        # ---- Top organizations row ----
        self._org_label = ctk.CTkLabel(self, text="Top Organisationen: -", font=("", 11), text_color="#aaaaaa", anchor="w")
        self._org_label.pack(fill="x", padx=10, pady=(0, 8))

    def refresh(self):
        try:
            today = self._store.count_today()
            week = self._store.count_this_week()
            month = self._store.count_this_month()
            top_orgs = self._store.top_organizations(limit=3)

            self._today_label.configure(text=f"Heute: {today}")
            self._week_label.configure(text=f"Diese Woche: {week}")
            self._month_label.configure(text=f"Dieser Monat: {month}")

            if top_orgs:
                org_text = "Top Organisationen: " + " | ".join(
                    f"{name} ({count})" for name, count in top_orgs
                )
            else:
                org_text = "Top Organisationen: -"
            self._org_label.configure(text=org_text)
        except Exception:
            pass
