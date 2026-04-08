import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from gui.theme import (
    BG_BASE, BG_SURFACE, BORDER_SUBTLE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY,
    ACCENT_BLUE, ACCENT_BLUE_HOVER,
    RED_DANGER, RED_DANGER_HOVER,
    BTN_DISABLED_FG, BTN_DISABLED_HOVER,
    BTN_SECONDARY_FG, BTN_SECONDARY_HOVER,
    BTN_SAVED_FG, BTN_SAVED_HOVER,
    FONT_H2, FONT_H3, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_MONO_SMALL,
    BUTTON_CORNER_RADIUS, BUTTON_HEIGHT, ENTRY_CORNER_RADIUS,
    SETTINGS_CARD_RADIUS,
    PAD_PAGE, PAD_CARD_GAP, PAD_CARD_INTERNAL, PAD_INNER, PAD_TIGHT,
)


class SettingsTab(ctk.CTkFrame):
    def __init__(self, parent, settings, on_apply=None, on_reset_statistics=None, on_check_update=None):
        super().__init__(parent, fg_color="transparent")
        self._settings = settings
        self._on_apply = on_apply
        self._on_reset_statistics = on_reset_statistics
        self._on_check_update = on_check_update
        self._entries: dict[str, ctk.CTkEntry | ctk.CTkCheckBox] = {}
        self._saved_snapshot: dict = {}
        self._build_ui()
        self._take_snapshot()

    def _build_ui(self):
        container = ctk.CTkScrollableFrame(self, fg_color=BG_BASE)
        container.pack(fill="both", expand=True, padx=PAD_PAGE, pady=(PAD_PAGE, PAD_INNER))

        # ── MQTT ──
        mqtt_card = self._section(container, "MQTT Einstellungen")
        self._field(mqtt_card, "mqtt_broker", "Production Broker")
        self._field(mqtt_card, "mqtt_username", "Production Username")
        self._field(mqtt_card, "mqtt_password", "Production Passwort")
        self._switch_field(mqtt_card, "staging_enabled", "Staging aktivieren")
        self._checkbox_field(mqtt_card, "staging_alarm_enabled", "Staging-Alarme ausl\u00f6sen")
        self._field(mqtt_card, "staging_mqtt_broker", "Staging Broker")
        self._field(mqtt_card, "staging_mqtt_username", "Staging Username")
        self._field(mqtt_card, "staging_mqtt_password", "Staging Passwort")

        # ── Hue ──
        hue_card = self._section(container, "Hue Einstellungen")
        self._field(hue_card, "hue_bridge_ip", "Bridge IP")
        self._field(hue_card, "hue_username", "Username")

        # ── Alarm ──
        alarm_card = self._section(container, "Alarm Einstellungen")
        self._file_field(alarm_card, "alarm_wav_file", "WAV Datei")
        self._file_field(
            alarm_card, "alarm_wav_helicopter", "Helikopter Audio-Datei",
            filetypes=[("Audio files", "*.wav *.mp3"), ("WAV files", "*.wav"), ("MP3 files", "*.mp3"), ("All files", "*.*")]
        )
        self._field(alarm_card, "helicopter_loop_count", "Helikopter Loops")
        self._field(alarm_card, "alarm_light_seconds", "Dauer (Sekunden)")
        self._field(alarm_card, "blink_interval", "Blink-Intervall (Sek.)")
        self._field(alarm_card, "off_delay", "Off-Delay (Sek.)")
        self._field(alarm_card, "dashboard_blink_interval", "Dashboard Blink-Intervall (Sek.)")

        # ── Sicherheit ──
        sec_card = self._section(container, "Sicherheit")
        self._switch_field(sec_card, "quit_password_enabled", "Passwort beim Beenden")
        self._field(sec_card, "quit_password", "Beenden-Passwort")
        self._update_quit_pw_state()

        # ── Apply button (outside scroll) ──
        self._apply_btn = ctk.CTkButton(
            self, text="Keine \u00c4nderungen", command=self._apply,
            height=44, font=FONT_H3, corner_radius=BUTTON_CORNER_RADIUS,
            fg_color=BTN_DISABLED_FG, hover_color=BTN_DISABLED_HOVER,
            state="disabled", width=300,
        )
        self._apply_btn.pack(pady=(PAD_INNER, PAD_INNER))

        # ── Auto-Update ──
        update_card = self._section(container, "Auto-Update")

        self._update_status_label = ctk.CTkLabel(
            update_card, text="", font=FONT_SMALL, text_color=TEXT_TERTIARY, anchor="w",
        )
        self._update_status_label.pack(fill="x", padx=PAD_CARD_INTERNAL, pady=(0, PAD_TIGHT))

        guide_frame = ctk.CTkFrame(update_card, fg_color=BG_BASE, corner_radius=ENTRY_CORNER_RADIUS)
        guide_frame.pack(fill="x", padx=PAD_CARD_INTERNAL, pady=(0, PAD_INNER))

        guide_text = (
            "Die App pr\u00fcft beim Start automatisch auf Updates.\n"
            "Neue Versionen werden automatisch heruntergeladen\n"
            "und installiert \u2014 es ist keine Einrichtung n\u00f6tig."
        )
        ctk.CTkLabel(
            guide_frame, text=guide_text,
            font=FONT_MONO_SMALL, text_color=TEXT_SECONDARY,
            anchor="nw", justify="left",
        ).pack(fill="x", padx=PAD_INNER, pady=PAD_INNER)

        ctk.CTkButton(
            update_card, text="Jetzt nach Updates suchen", width=220,
            corner_radius=BUTTON_CORNER_RADIUS, height=BUTTON_HEIGHT,
            fg_color=ACCENT_BLUE, hover_color=ACCENT_BLUE_HOVER, font=FONT_BODY,
            command=self._trigger_update_check,
        ).pack(anchor="w", padx=PAD_CARD_INTERNAL, pady=(0, PAD_CARD_INTERNAL))

        # ── Daten ──
        data_card = self._section(container, "Daten")
        ctk.CTkButton(
            data_card,
            text="Statistiken zur\u00fccksetzen",
            fg_color=RED_DANGER, hover_color=RED_DANGER_HOVER,
            corner_radius=BUTTON_CORNER_RADIUS, font=FONT_BODY_BOLD,
            command=self._confirm_reset_statistics,
            height=BUTTON_HEIGHT,
        ).pack(anchor="w", padx=PAD_CARD_INTERNAL, pady=(0, PAD_CARD_INTERNAL))

    # ── Card-based sections ──

    def _section(self, parent, title: str) -> ctk.CTkFrame:
        card = ctk.CTkFrame(
            parent, fg_color=BG_SURFACE,
            corner_radius=SETTINGS_CARD_RADIUS,
            border_width=1, border_color=BORDER_SUBTLE,
        )
        card.pack(fill="x", pady=(0, PAD_CARD_GAP))

        ctk.CTkLabel(
            card, text=title, font=FONT_H2, text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=PAD_CARD_INTERNAL, pady=(PAD_CARD_INTERNAL, PAD_INNER))

        return card

    # ── Vertical field: label above, entry below ──

    def _field(self, parent_card, key: str, label: str):
        wrapper = ctk.CTkFrame(parent_card, fg_color="transparent")
        wrapper.pack(fill="x", padx=PAD_CARD_INTERNAL, pady=(0, PAD_INNER))

        ctk.CTkLabel(
            wrapper, text=label, font=FONT_SMALL, text_color=TEXT_SECONDARY, anchor="w",
        ).pack(anchor="w", pady=(0, PAD_TIGHT))

        entry = ctk.CTkEntry(wrapper, corner_radius=ENTRY_CORNER_RADIUS, font=FONT_BODY, height=38)
        entry.pack(fill="x")

        val = self._settings.get(key, "")
        entry.insert(0, str(val))
        entry.bind("<KeyRelease>", self._on_change)
        self._entries[key] = entry

    def _file_field(self, parent_card, key: str, label: str, filetypes=None):
        if filetypes is None:
            filetypes = [("WAV files", "*.wav"), ("All files", "*.*")]

        wrapper = ctk.CTkFrame(parent_card, fg_color="transparent")
        wrapper.pack(fill="x", padx=PAD_CARD_INTERNAL, pady=(0, PAD_INNER))

        ctk.CTkLabel(
            wrapper, text=label, font=FONT_SMALL, text_color=TEXT_SECONDARY, anchor="w",
        ).pack(anchor="w", pady=(0, PAD_TIGHT))

        row = ctk.CTkFrame(wrapper, fg_color="transparent")
        row.pack(fill="x")

        entry = ctk.CTkEntry(row, corner_radius=ENTRY_CORNER_RADIUS, font=FONT_BODY, height=38)
        entry.pack(side="left", fill="x", expand=True)

        val = self._settings.get(key, "")
        entry.insert(0, str(val))
        entry.bind("<KeyRelease>", self._on_change)
        self._entries[key] = entry

        ctk.CTkButton(
            row, text="...", width=44, height=38,
            corner_radius=BUTTON_CORNER_RADIUS,
            fg_color=BTN_SECONDARY_FG, hover_color=BTN_SECONDARY_HOVER,
            font=FONT_BODY,
            command=lambda: self._browse_file(entry, filetypes),
        ).pack(side="left", padx=(PAD_INNER, 0))

    def _switch_field(self, parent_card, key: str, label: str):
        wrapper = ctk.CTkFrame(parent_card, fg_color="transparent")
        wrapper.pack(fill="x", padx=PAD_CARD_INTERNAL, pady=(0, PAD_INNER))

        ctk.CTkLabel(
            wrapper, text=label, font=FONT_SMALL, text_color=TEXT_SECONDARY, anchor="w",
        ).pack(anchor="w", pady=(0, PAD_TIGHT))

        var = tk.BooleanVar(value=self._settings.get(key, False))
        switch = ctk.CTkSwitch(wrapper, text="", variable=var, command=self._on_change)
        switch.pack(anchor="w")

        if key == "staging_enabled":
            self._staging_var = var
            self._staging_switch = switch
        elif key == "quit_password_enabled":
            self._quit_pw_enabled_var = var
            self._quit_pw_switch = switch

    def _checkbox_field(self, parent_card, key: str, label: str):
        wrapper = ctk.CTkFrame(parent_card, fg_color="transparent")
        wrapper.pack(fill="x", padx=PAD_CARD_INTERNAL, pady=(0, PAD_INNER))

        ctk.CTkLabel(
            wrapper, text=label, font=FONT_SMALL, text_color=TEXT_SECONDARY, anchor="w",
        ).pack(anchor="w", pady=(0, PAD_TIGHT))

        var = tk.BooleanVar(value=self._settings.get(key, False))
        cb = ctk.CTkCheckBox(wrapper, text="", variable=var, command=self._on_change)
        cb.pack(anchor="w")

        if key == "staging_alarm_enabled":
            self._staging_alarm_var = var
            self._staging_alarm_cb = cb
            self._update_staging_alarm_state()

    def _browse_file(self, entry: ctk.CTkEntry, filetypes):
        path = filedialog.askopenfilename(filetypes=filetypes)
        if path:
            entry.delete(0, "end")
            entry.insert(0, path)
            self._on_change()

    # ── Change tracking ──

    def _get_current_values(self) -> dict:
        data = {}
        for key, widget in self._entries.items():
            data[key] = widget.get()
        data["staging_enabled"] = self._staging_var.get()
        data["staging_alarm_enabled"] = self._staging_alarm_var.get()
        data["quit_password_enabled"] = self._quit_pw_enabled_var.get()
        return data

    def _take_snapshot(self):
        self._saved_snapshot = self._get_current_values()

    def _has_changes(self) -> bool:
        return self._get_current_values() != self._saved_snapshot

    def _on_change(self, _event=None):
        self._update_staging_alarm_state()
        self._update_quit_pw_state()
        if self._has_changes():
            self._apply_btn.configure(
                text="\u00dcbernehmen & Neu verbinden",
                fg_color=ACCENT_BLUE, hover_color=ACCENT_BLUE_HOVER,
                state="normal",
            )
        else:
            self._apply_btn.configure(
                text="Keine \u00c4nderungen",
                fg_color=BTN_DISABLED_FG, hover_color=BTN_DISABLED_HOVER,
                state="disabled",
            )

    def _on_quit_pw_toggle(self):
        self._update_quit_pw_state()
        self._on_change()

    def _update_quit_pw_state(self):
        state = "normal" if self._quit_pw_enabled_var.get() else "disabled"
        self._entries["quit_password"].configure(state=state)

    def _update_staging_alarm_state(self):
        if self._staging_var.get():
            self._staging_alarm_cb.configure(state="normal")
        else:
            self._staging_alarm_cb.configure(state="disabled")

    def _confirm_reset_statistics(self):
        result = messagebox.askyesno(
            "Statistiken zur\u00fccksetzen",
            "Alle gespeicherten Alarme und Statistiken werden unwiderruflich gel\u00f6scht.\n\nFortfahren?",
        )
        if result and self._on_reset_statistics:
            self._on_reset_statistics()

    def _trigger_update_check(self):
        if self._on_check_update:
            self._update_status_label.configure(text="Suche nach Updates...", text_color=TEXT_TERTIARY)
            self._on_check_update()

    def set_update_status(self, text, color="#aaaaaa"):
        self._update_status_label.configure(text=text, text_color=color)

    def _apply(self):
        data = {}
        for key, widget in self._entries.items():
            data[key] = widget.get()

        if "helicopter_loop_count" in data:
            try:
                data["helicopter_loop_count"] = max(1, int(data["helicopter_loop_count"]))
            except ValueError:
                pass

        for nk in ("alarm_light_seconds", "blink_interval", "off_delay", "dashboard_blink_interval"):
            if nk in data:
                try:
                    data[nk] = float(data[nk])
                except ValueError:
                    pass

        data["staging_enabled"] = self._staging_var.get()
        data["staging_alarm_enabled"] = self._staging_alarm_var.get()
        data["quit_password_enabled"] = self._quit_pw_enabled_var.get()

        self._settings.update(data)

        if self._on_apply:
            self._on_apply()

        self._take_snapshot()
        self._apply_btn.configure(
            text="Gespeichert",
            fg_color=BTN_SAVED_FG, hover_color=BTN_SAVED_HOVER,
            state="disabled",
        )

    def refresh_from_settings(self):
        for key, widget in self._entries.items():
            widget.delete(0, "end")
            widget.insert(0, str(self._settings.get(key, "")))
        self._staging_var.set(self._settings.get("staging_enabled", False))
        self._staging_alarm_var.set(self._settings.get("staging_alarm_enabled", False))
        self._update_staging_alarm_state()
        self._quit_pw_enabled_var.set(self._settings.get("quit_password_enabled", True))
        self._update_quit_pw_state()
        self._take_snapshot()
        self._on_change()
