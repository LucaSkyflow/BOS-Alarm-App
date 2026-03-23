import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk



class SettingsTab(ctk.CTkFrame):
    def __init__(self, parent, settings, on_apply=None, on_reset_statistics=None):
        super().__init__(parent)
        self._settings = settings
        self._on_apply = on_apply
        self._on_reset_statistics = on_reset_statistics
        self._entries: dict[str, ctk.CTkEntry | ctk.CTkCheckBox] = {}
        self._build_ui()

    def _build_ui(self):
        container = ctk.CTkScrollableFrame(self)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # ---- MQTT ----
        self._section(container, "MQTT Einstellungen")

        # Production MQTT fields
        self._field(container, "mqtt_broker", "Production Broker")
        self._field(container, "mqtt_username", "Production Username")
        self._field(container, "mqtt_password", "Production Passwort")

        # Staging switch
        staging_row = ctk.CTkFrame(container)
        staging_row.pack(fill="x", pady=5)
        ctk.CTkLabel(staging_row, text="Staging aktivieren", width=180, anchor="w").pack(side="left", padx=5)

        self._staging_var = tk.BooleanVar(value=self._settings.get("staging_enabled", False))
        self._staging_switch = ctk.CTkSwitch(
            staging_row,
            text="",
            variable=self._staging_var,
            command=self._on_staging_toggle,
        )
        self._staging_switch.pack(side="left", padx=5)

        # Staging alarm checkbox
        alarm_row = ctk.CTkFrame(container)
        alarm_row.pack(fill="x", pady=2)
        ctk.CTkLabel(alarm_row, text="Staging-Alarme ausloesen", width=180, anchor="w").pack(side="left", padx=5)

        self._staging_alarm_var = tk.BooleanVar(value=self._settings.get("staging_alarm_enabled", False))
        self._staging_alarm_cb = ctk.CTkCheckBox(
            alarm_row,
            text="",
            variable=self._staging_alarm_var,
        )
        self._staging_alarm_cb.pack(side="left", padx=5)
        self._update_staging_alarm_state()

        # Staging MQTT fields
        self._field(container, "staging_mqtt_broker", "Staging Broker")
        self._field(container, "staging_mqtt_username", "Staging Username")
        self._field(container, "staging_mqtt_password", "Staging Passwort")

        # ---- Hue ----
        self._section(container, "Hue Einstellungen")
        self._field(container, "hue_bridge_ip", "Bridge IP")
        self._field(container, "hue_username", "Username")

        # ---- Alarm ----
        self._section(container, "Alarm Einstellungen")
        self._file_field(container, "alarm_wav_file", "WAV Datei")
        self._file_field(
            container, "alarm_wav_helicopter", "Helikopter Audio-Datei",
            filetypes=[("Audio files", "*.wav *.mp3"), ("WAV files", "*.wav"), ("MP3 files", "*.mp3"), ("All files", "*.*")]
        )
        self._field(container, "helicopter_loop_count", "Helikopter Loops")
        self._field(container, "alarm_light_seconds", "Dauer (Sekunden)")
        self._field(container, "blink_interval", "Blink-Intervall (Sek.)")
        self._field(container, "off_delay", "Off-Delay (Sek.)")
        self._field(container, "dashboard_blink_interval", "Dashboard Blink-Intervall (Sek.)")

        # ---- Sicherheit ----
        self._section(container, "Sicherheit")

        # Passwort-Schutz Toggle
        pw_toggle_row = ctk.CTkFrame(container)
        pw_toggle_row.pack(fill="x", pady=5)
        ctk.CTkLabel(pw_toggle_row, text="Passwort beim Beenden", width=180, anchor="w").pack(side="left", padx=5)
        self._quit_pw_enabled_var = tk.BooleanVar(value=self._settings.get("quit_password_enabled", True))
        self._quit_pw_switch = ctk.CTkSwitch(
            pw_toggle_row,
            text="",
            variable=self._quit_pw_enabled_var,
            command=self._on_quit_pw_toggle,
        )
        self._quit_pw_switch.pack(side="left", padx=5)

        self._field(container, "quit_password", "Beenden-Passwort")
        self._update_quit_pw_state()

        # ---- Apply button ----
        ctk.CTkButton(self, text="Übernehmen & Neu verbinden", command=self._apply, height=40, font=("", 14, "bold")).pack(pady=15)

        # ---- Auto-Update ----
        self._section(container, "Auto-Update")

        self._update_status_label = ctk.CTkLabel(
            container, text="", font=("", 12), text_color="#aaaaaa", anchor="w",
        )
        self._update_status_label.pack(fill="x", padx=5, pady=(0, 5))
        self._check_gh_status()

        guide_frame = ctk.CTkFrame(container, fg_color="#1e1e2e", corner_radius=8)
        guide_frame.pack(fill="x", padx=5, pady=(0, 5))

        guide_text = (
            "Damit die App sich automatisch aktualisiert, muss einmalig\n"
            "die GitHub CLI eingerichtet werden:\n"
            "\n"
            "Schritt 1 — GitHub Account\n"
            "  Du brauchst einen GitHub-Account. Falls du noch\n"
            "  keinen hast, erstelle einen auf github.com.\n"
            "  Teile deinen GitHub-Benutzernamen dem Admin mit,\n"
            "  damit er dich zum Repository einladen kann.\n"
            "\n"
            "Schritt 2 — GitHub CLI installieren\n"
            "  Lade die GitHub CLI herunter und installiere sie:\n"
            "  https://cli.github.com\n"
            "\n"
            "Schritt 3 — Anmelden\n"
            "  Öffne ein Terminal (cmd oder PowerShell) und gib ein:\n"
            "  gh auth login\n"
            "  Wähle: GitHub.com → HTTPS → Login with a web browser\n"
            "  Folge den Anweisungen im Browser.\n"
            "\n"
            "Schritt 4 — Fertig!\n"
            "  Die App prüft beim Start automatisch auf Updates.\n"
            "  Du kannst dieses Fenster schließen."
        )

        ctk.CTkLabel(
            guide_frame, text=guide_text,
            font=("Consolas", 11), text_color="#cccccc",
            anchor="nw", justify="left",
        ).pack(fill="x", padx=12, pady=10)

        ctk.CTkButton(
            container, text="Verbindung prüfen", width=160,
            command=self._check_gh_status,
        ).pack(anchor="w", padx=5, pady=(0, 5))

        # ---- Data section ----
        self._section(container, "Daten")
        ctk.CTkButton(
            container,
            text="Statistiken zurücksetzen",
            fg_color="#cc3333",
            hover_color="#aa2222",
            command=self._confirm_reset_statistics,
            height=36,
        ).pack(anchor="w", padx=5, pady=5)

    def _section(self, parent, title: str):
        ctk.CTkLabel(parent, text=title, font=("", 15, "bold")).pack(anchor="w", pady=(15, 5))

    def _field(self, parent, key: str, label: str):
        row = ctk.CTkFrame(parent)
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(row, text=label, width=180, anchor="w").pack(side="left", padx=5)
        entry = ctk.CTkEntry(row, width=400)
        entry.pack(side="left", padx=5, fill="x", expand=True)
        val = self._settings.get(key, "")
        entry.insert(0, str(val))
        self._entries[key] = entry

    def _file_field(self, parent, key: str, label: str, filetypes=None):
        if filetypes is None:
            filetypes = [("WAV files", "*.wav"), ("All files", "*.*")]
        row = ctk.CTkFrame(parent)
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(row, text=label, width=180, anchor="w").pack(side="left", padx=5)
        entry = ctk.CTkEntry(row, width=350)
        entry.pack(side="left", padx=5, fill="x", expand=True)
        val = self._settings.get(key, "")
        entry.insert(0, str(val))
        self._entries[key] = entry
        ctk.CTkButton(row, text="...", width=40, command=lambda: self._browse_file(entry, filetypes)).pack(side="left", padx=5)

    def _browse_file(self, entry: ctk.CTkEntry, filetypes):
        path = filedialog.askopenfilename(filetypes=filetypes)
        if path:
            entry.delete(0, "end")
            entry.insert(0, path)

    def _on_staging_toggle(self):
        self._update_staging_alarm_state()

    def _on_quit_pw_toggle(self):
        self._update_quit_pw_state()

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
            "Statistiken zurücksetzen",
            "Alle gespeicherten Alarme und Statistiken werden unwiderruflich gelöscht.\n\nFortfahren?",
        )
        if result and self._on_reset_statistics:
            self._on_reset_statistics()

    def _apply(self):
        data = {}
        for key, widget in self._entries.items():
            data[key] = widget.get()

        # convert numeric fields
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

        # Staging settings from switches/checkboxes
        data["staging_enabled"] = self._staging_var.get()
        data["staging_alarm_enabled"] = self._staging_alarm_var.get()

        # Security settings
        data["quit_password_enabled"] = self._quit_pw_enabled_var.get()

        self._settings.update(data)

        if self._on_apply:
            self._on_apply()

    def _check_gh_status(self):
        try:
            result = subprocess.run(
                "gh auth status",
                capture_output=True, text=True, timeout=5,
                shell=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode == 0:
                self._update_status_label.configure(
                    text="GitHub CLI: Verbunden",
                    text_color="#00cc00",
                )
            else:
                self._update_status_label.configure(
                    text="GitHub CLI: Nicht angemeldet — siehe Anleitung unten",
                    text_color="#cc4444",
                )
        except FileNotFoundError:
            self._update_status_label.configure(
                text="GitHub CLI: Nicht installiert — siehe Anleitung unten",
                text_color="#cc4444",
            )
        except Exception:
            self._update_status_label.configure(
                text="GitHub CLI: Status unbekannt",
                text_color="#aaaaaa",
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
