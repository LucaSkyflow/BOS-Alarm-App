import customtkinter as ctk
from gui.theme import (
    BG_OVERLAY, BG_SURFACE, BORDER_SUBTLE, TEXT_PRIMARY,
    ACCENT_BLUE, ACCENT_BLUE_HOVER,
    BTN_SECONDARY_FG, BTN_SECONDARY_HOVER,
    FONT_H3, FONT_BODY, FONT_BODY_BOLD,
    ENTRY_CORNER_RADIUS, BUTTON_CORNER_RADIUS, BUTTON_HEIGHT,
    CARD_CORNER_RADIUS, PAD_PAGE, PAD_INNER,
)


class PasswordDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Passwort eingeben")
        self.geometry("420x220")
        self.resizable(False, False)
        self.grab_set()
        self.transient(parent)
        self.configure(fg_color=BG_OVERLAY)

        self.result: str | None = None

        # Inner card
        card = ctk.CTkFrame(
            self, fg_color=BG_SURFACE,
            corner_radius=CARD_CORNER_RADIUS,
            border_width=1, border_color=BORDER_SUBTLE,
        )
        card.pack(fill="both", expand=True, padx=PAD_PAGE, pady=PAD_PAGE)

        ctk.CTkLabel(
            card, text="Passwort zum Beenden:",
            font=FONT_H3, text_color=TEXT_PRIMARY,
        ).pack(pady=(PAD_PAGE, PAD_INNER))

        self._entry = ctk.CTkEntry(
            card, show="*", width=280, height=40,
            corner_radius=ENTRY_CORNER_RADIUS, font=FONT_BODY,
        )
        self._entry.pack(pady=PAD_INNER)
        self._entry.focus_set()
        self._entry.bind("<Return>", lambda e: self._ok())

        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(pady=(PAD_INNER, PAD_PAGE))

        ctk.CTkButton(
            btn_frame, text="OK", width=110, height=BUTTON_HEIGHT,
            corner_radius=BUTTON_CORNER_RADIUS,
            fg_color=ACCENT_BLUE, hover_color=ACCENT_BLUE_HOVER,
            font=FONT_BODY_BOLD, command=self._ok,
        ).pack(side="left", padx=PAD_INNER)
        ctk.CTkButton(
            btn_frame, text="Abbrechen", width=110, height=BUTTON_HEIGHT,
            corner_radius=BUTTON_CORNER_RADIUS,
            fg_color=BTN_SECONDARY_FG, hover_color=BTN_SECONDARY_HOVER,
            font=FONT_BODY, command=self._cancel,
        ).pack(side="left", padx=PAD_INNER)

        self.protocol("WM_DELETE_WINDOW", self._cancel)

    def _ok(self):
        self.result = self._entry.get()
        self.grab_release()
        self.destroy()

    def _cancel(self):
        self.result = None
        self.grab_release()
        self.destroy()
