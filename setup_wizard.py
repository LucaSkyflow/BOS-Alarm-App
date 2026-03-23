"""BOS Alarm — Setup Wizard.

Standalone GUI installer that:
  1. Asks for install location
  2. Copies app files to the chosen directory
  3. Asks for MQTT credentials
  4. Creates config.json
  5. Creates desktop shortcut
  6. Starts the app
"""

import json
import os
import shutil
import sys
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


# ── Paths ────────────────────────────────────────────────────────────────────

def get_source_dir():
    """Directory where the setup exe / script lives (= extracted ZIP root)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_desktop_path():
    return os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")

DEFAULT_INSTALL_DIR = os.path.join(os.environ.get("LOCALAPPDATA", "C:\\"), "BOS Alarm")


# ── Shortcut Creation ────────────────────────────────────────────────────────

def create_shortcut(target_exe, shortcut_path, icon_path=None, description=""):
    """Create a Windows .lnk shortcut using PowerShell."""
    ps_script = f'''
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut("{shortcut_path}")
$sc.TargetPath = "{target_exe}"
$sc.WorkingDirectory = "{os.path.dirname(target_exe)}"
$sc.Description = "{description}"
'''
    if icon_path and os.path.exists(icon_path):
        ps_script += f'$sc.IconLocation = "{icon_path}"\n'
    ps_script += "$sc.Save()\n"

    subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_script],
        capture_output=True,
        creationflags=0x08000000,  # CREATE_NO_WINDOW
    )


# ── Wizard UI ────────────────────────────────────────────────────────────────

class SetupWizard:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("BOS Alarm — Einrichtung")
        self.root.geometry("520x480")
        self.root.resizable(False, False)
        self.root.configure(bg="#1a1a2e")

        # Try to set icon
        icon_path = os.path.join(get_source_dir(), "Blaulicht.ico")
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)

        # Center window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 520) // 2
        y = (self.root.winfo_screenheight() - 480) // 2
        self.root.geometry(f"+{x}+{y}")

        self.source_dir = get_source_dir()
        self.pages = []
        self.current_page = 0

        # Variables
        self.install_dir = tk.StringVar(value=DEFAULT_INSTALL_DIR)
        self.mqtt_broker = tk.StringVar()
        self.mqtt_username = tk.StringVar()
        self.mqtt_password = tk.StringVar()
        self.hue_ip = tk.StringVar()
        self.hue_username = tk.StringVar()
        self.create_desktop_shortcut = tk.BooleanVar(value=True)
        self.start_app = tk.BooleanVar(value=True)

        self._build_ui()
        self._show_page(0)

    def _build_ui(self):
        # Style
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"),
                         background="#1a1a2e", foreground="white")
        style.configure("Sub.TLabel", font=("Segoe UI", 10),
                         background="#1a1a2e", foreground="#cccccc")
        style.configure("Field.TLabel", font=("Segoe UI", 10),
                         background="#1a1a2e", foreground="#eeeeee")
        style.configure("Setup.TFrame", background="#1a1a2e")
        style.configure("Setup.TCheckbutton", background="#1a1a2e",
                         foreground="#eeeeee", font=("Segoe UI", 10))
        style.configure("Nav.TButton", font=("Segoe UI", 11))
        style.configure("Accent.TButton", font=("Segoe UI", 11, "bold"))

        # Main container
        self.container = ttk.Frame(self.root, style="Setup.TFrame")
        self.container.pack(fill="both", expand=True, padx=20, pady=15)

        # Page frames
        self.page_frame = ttk.Frame(self.container, style="Setup.TFrame")
        self.page_frame.pack(fill="both", expand=True)

        # Navigation
        nav = ttk.Frame(self.container, style="Setup.TFrame")
        nav.pack(fill="x", pady=(15, 0))

        self.btn_back = ttk.Button(nav, text="Zurück", style="Nav.TButton",
                                    command=self._prev_page)
        self.btn_back.pack(side="left")

        self.btn_next = ttk.Button(nav, text="Weiter", style="Accent.TButton",
                                    command=self._next_page)
        self.btn_next.pack(side="right")

        # Build pages
        self.pages = [
            self._page_welcome,
            self._page_install_dir,
            self._page_mqtt,
            self._page_hue,
            self._page_options,
            self._page_install,
        ]

    def _clear_page(self):
        for w in self.page_frame.winfo_children():
            w.destroy()

    def _show_page(self, idx):
        self.current_page = idx
        self._clear_page()
        self.pages[idx]()

        # Button states
        self.btn_back.configure(state="normal" if idx > 0 else "disabled")
        if idx == len(self.pages) - 1:
            self.btn_next.configure(text="Schliessen", command=self.root.destroy)
        elif idx == len(self.pages) - 2:
            self.btn_next.configure(text="Installieren", command=self._next_page)
        else:
            self.btn_next.configure(text="Weiter", command=self._next_page)

    def _next_page(self):
        # Validation
        if self.current_page == 2:  # MQTT page
            if not self.mqtt_broker.get().strip():
                messagebox.showwarning("Fehler", "Bitte MQTT Broker eingeben.",
                                        parent=self.root)
                return
            if not self.mqtt_username.get().strip():
                messagebox.showwarning("Fehler", "Bitte MQTT Username eingeben.",
                                        parent=self.root)
                return
            if not self.mqtt_password.get().strip():
                messagebox.showwarning("Fehler", "Bitte MQTT Passwort eingeben.",
                                        parent=self.root)
                return

        if self.current_page == len(self.pages) - 2:
            # Run installation
            self._show_page(self.current_page + 1)
            self.root.update()
            self._do_install()
            return

        if self.current_page < len(self.pages) - 1:
            self._show_page(self.current_page + 1)

    def _prev_page(self):
        if self.current_page > 0:
            self._show_page(self.current_page - 1)

    # ── Pages ────────────────────────────────────────────────────────────

    def _page_welcome(self):
        f = self.page_frame
        ttk.Label(f, text="Willkommen", style="Title.TLabel").pack(anchor="w", pady=(10, 5))
        ttk.Label(f, text=(
            "Dieser Assistent richtet BOS Alarm auf\n"
            "deinem Computer ein.\n\n"
            "Du benötigst die MQTT-Zugangsdaten, die\n"
            "du vom Administrator erhalten hast."
        ), style="Sub.TLabel").pack(anchor="w", pady=10)

    def _page_install_dir(self):
        f = self.page_frame
        ttk.Label(f, text="Installationsordner", style="Title.TLabel").pack(anchor="w", pady=(10, 5))
        ttk.Label(f, text="Wohin soll BOS Alarm installiert werden?",
                   style="Sub.TLabel").pack(anchor="w", pady=(5, 10))

        row = ttk.Frame(f, style="Setup.TFrame")
        row.pack(fill="x", pady=5)
        entry = ttk.Entry(row, textvariable=self.install_dir, font=("Segoe UI", 10))
        entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(row, text="...", width=4,
                    command=self._browse_dir).pack(side="right")

    def _page_mqtt(self):
        f = self.page_frame
        ttk.Label(f, text="MQTT Verbindung", style="Title.TLabel").pack(anchor="w", pady=(10, 5))
        ttk.Label(f, text="Diese Daten bekommst du vom Administrator.",
                   style="Sub.TLabel").pack(anchor="w", pady=(5, 15))

        self._labeled_entry(f, "Broker:", self.mqtt_broker)
        self._labeled_entry(f, "Username:", self.mqtt_username)
        self._labeled_entry(f, "Passwort:", self.mqtt_password)

    def _page_hue(self):
        f = self.page_frame
        ttk.Label(f, text="Philips Hue (optional)", style="Title.TLabel").pack(anchor="w", pady=(10, 5))
        ttk.Label(f, text=(
            "Für Alarm-Licht über Philips Hue.\n"
            "Leer lassen zum Überspringen."
        ), style="Sub.TLabel").pack(anchor="w", pady=(5, 15))

        self._labeled_entry(f, "Bridge IP:", self.hue_ip)
        self._labeled_entry(f, "API Username:", self.hue_username)

    def _page_options(self):
        f = self.page_frame
        ttk.Label(f, text="Optionen", style="Title.TLabel").pack(anchor="w", pady=(10, 5))

        ttk.Checkbutton(f, text="Desktop-Verknüpfung erstellen",
                         variable=self.create_desktop_shortcut,
                         style="Setup.TCheckbutton").pack(anchor="w", pady=8)
        ttk.Checkbutton(f, text="App nach Installation starten",
                         variable=self.start_app,
                         style="Setup.TCheckbutton").pack(anchor="w", pady=8)

        ttk.Label(f, text="\nZusammenfassung:", style="Field.TLabel").pack(anchor="w", pady=(15, 5))

        summary = (
            f"  Installationsordner:  {self.install_dir.get()}\n"
            f"  MQTT Broker:  {self.mqtt_broker.get()}\n"
            f"  MQTT Username:  {self.mqtt_username.get()}\n"
            f"  Hue Bridge:  {self.hue_ip.get() or '(nicht konfiguriert)'}"
        )
        ttk.Label(f, text=summary, style="Sub.TLabel", justify="left").pack(anchor="w")

    def _page_install(self):
        f = self.page_frame
        ttk.Label(f, text="Installation", style="Title.TLabel").pack(anchor="w", pady=(10, 5))

        self.progress_label = ttk.Label(f, text="Wird installiert...", style="Sub.TLabel")
        self.progress_label.pack(anchor="w", pady=(10, 5))

        self.progress = ttk.Progressbar(f, mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=10)

        self.status_label = ttk.Label(f, text="", style="Sub.TLabel")
        self.status_label.pack(anchor="w", pady=5)

    # ── Installation Logic ───────────────────────────────────────────────

    def _do_install(self):
        install_dir = self.install_dir.get().strip()
        steps = []

        def status(msg, pct):
            self.status_label.configure(text=f"  {msg}")
            self.progress.configure(value=pct)
            self.root.update()

        try:
            # Step 1: Create directory & copy files
            status("Dateien kopieren...", 10)
            source = self.source_dir
            if os.path.normpath(source) != os.path.normpath(install_dir):
                os.makedirs(install_dir, exist_ok=True)
                for item in os.listdir(source):
                    if item in ("setup.exe", "Setup.exe", "setup_wizard.exe"):
                        continue
                    s = os.path.join(source, item)
                    d = os.path.join(install_dir, item)
                    if os.path.isdir(s):
                        if os.path.exists(d):
                            shutil.rmtree(d)
                        shutil.copytree(s, d)
                    else:
                        shutil.copy2(s, d)

            # Step 2: Create config.json
            status("Konfiguration erstellen...", 50)
            config_path = os.path.join(install_dir, "config.json")
            example_path = os.path.join(install_dir, "config.example.json")

            if os.path.exists(example_path):
                with open(example_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            else:
                config = {}

            config["mqtt_broker"] = self.mqtt_broker.get().strip()
            config["mqtt_username"] = self.mqtt_username.get().strip()
            config["mqtt_password"] = self.mqtt_password.get().strip()
            config["hue_bridge_ip"] = self.hue_ip.get().strip()
            config["hue_username"] = self.hue_username.get().strip()

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            # Step 3: Desktop shortcut
            if self.create_desktop_shortcut.get():
                status("Desktop-Verknüpfung erstellen...", 75)
                exe_path = os.path.join(install_dir, "BOS Alarm.exe")
                icon_path = os.path.join(install_dir, "Blaulicht.ico")
                shortcut_path = os.path.join(get_desktop_path(), "BOS Alarm.lnk")
                if os.path.exists(exe_path):
                    create_shortcut(exe_path, shortcut_path, icon_path, "BOS Alarm")

            # Step 4: Start app
            status("Fertig!", 100)
            self.progress_label.configure(text="Installation abgeschlossen!")
            self.btn_back.configure(state="disabled")

            if self.start_app.get():
                exe_path = os.path.join(install_dir, "BOS Alarm.exe")
                if os.path.exists(exe_path):
                    subprocess.Popen(
                        [exe_path],
                        cwd=install_dir,
                        creationflags=0x00000008,  # DETACHED_PROCESS
                    )
                    status("Fertig! App wurde gestartet.", 100)
                else:
                    status("Fertig! (BOS Alarm.exe nicht gefunden)", 100)

        except Exception as e:
            self.progress_label.configure(text="Fehler bei der Installation")
            status(str(e), 0)
            messagebox.showerror("Fehler", str(e), parent=self.root)

    # ── UI Helpers ───────────────────────────────────────────────────────

    def _labeled_entry(self, parent, label, variable):
        row = ttk.Frame(parent, style="Setup.TFrame")
        row.pack(fill="x", pady=4)
        ttk.Label(row, text=label, width=14, style="Field.TLabel").pack(side="left")
        ttk.Entry(row, textvariable=variable, font=("Segoe UI", 10)).pack(
            side="left", fill="x", expand=True)

    def _browse_dir(self):
        path = filedialog.askdirectory(initialdir=self.install_dir.get())
        if path:
            self.install_dir.set(path)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    SetupWizard().run()
