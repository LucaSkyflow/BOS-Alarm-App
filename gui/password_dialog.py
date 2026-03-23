import customtkinter as ctk


class PasswordDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Passwort eingeben")
        self.geometry("350x160")
        self.resizable(False, False)
        self.grab_set()
        self.transient(parent)

        self.result: str | None = None

        ctk.CTkLabel(self, text="Passwort zum Beenden:", font=("", 14)).pack(pady=(20, 5))

        self._entry = ctk.CTkEntry(self, show="*", width=250)
        self._entry.pack(pady=5)
        self._entry.focus_set()
        self._entry.bind("<Return>", lambda e: self._ok())

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15)

        ctk.CTkButton(btn_frame, text="OK", width=100, command=self._ok).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Abbrechen", width=100, command=self._cancel).pack(side="left", padx=10)

        self.protocol("WM_DELETE_WINDOW", self._cancel)

    def _ok(self):
        self.result = self._entry.get()
        self.grab_release()
        self.destroy()

    def _cancel(self):
        self.result = None
        self.grab_release()
        self.destroy()
