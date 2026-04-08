import customtkinter as ctk
from gui.theme import (
    SIDEBAR_WIDTH, SIDEBAR_BG, SIDEBAR_ACTIVE_BG, SIDEBAR_HOVER_BG,
    BG_ROOT, BORDER_SUBTLE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY,
    ACCENT_BLUE, BTN_SECONDARY_FG, BTN_SECONDARY_HOVER,
    FONT_NAV_ITEM, FONT_NAV_ACTIVE, FONT_APP_TITLE, FONT_APP_VERSION,
    FONT_BODY_BOLD, BUTTON_CORNER_RADIUS, BUTTON_HEIGHT,
    PAD_INNER, PAD_SECTION, PAD_PAGE,
)


class Sidebar(ctk.CTkFrame):
    def __init__(self, parent, on_navigate, on_quit, version: str):
        super().__init__(parent, width=SIDEBAR_WIDTH, fg_color=SIDEBAR_BG)
        self.pack_propagate(False)

        self._on_navigate = on_navigate
        self._nav_items: dict[str, dict] = {}
        self._active = None

        self._build_ui(version, on_quit)

    def _build_ui(self, version: str, on_quit):
        # ── App title ──
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(fill="x", padx=PAD_PAGE, pady=(PAD_PAGE, PAD_INNER))

        ctk.CTkLabel(
            title_frame, text="BOS Alarm",
            font=FONT_APP_TITLE, text_color=TEXT_PRIMARY, anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_frame, text=f"v{version}",
            font=FONT_APP_VERSION, text_color=TEXT_TERTIARY, anchor="w",
        ).pack(anchor="w")

        # ── Separator ──
        ctk.CTkFrame(self, fg_color=BORDER_SUBTLE, height=1).pack(fill="x", padx=PAD_SECTION, pady=(PAD_INNER, PAD_SECTION))

        # ── Navigation items ──
        nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        nav_frame.pack(fill="both", expand=True, padx=0, pady=0)

        self._add_nav_item(nav_frame, "dashboard", "\U0001f6a8  Eins\u00e4tze")
        self._add_nav_item(nav_frame, "mqtt",      "\U0001f4e1  MQTT & Tests")
        self._add_nav_item(nav_frame, "settings",  "\u2699  Einstellungen")

        # ── Quit button at bottom ──
        quit_frame = ctk.CTkFrame(self, fg_color="transparent")
        quit_frame.pack(fill="x", side="bottom", padx=PAD_SECTION, pady=(0, PAD_PAGE))

        ctk.CTkButton(
            quit_frame,
            text="\u2715  Beenden",
            fg_color=BTN_SECONDARY_FG, hover_color=BTN_SECONDARY_HOVER,
            corner_radius=BUTTON_CORNER_RADIUS, height=BUTTON_HEIGHT,
            font=FONT_BODY_BOLD,
            command=on_quit,
        ).pack(fill="x")

    def _add_nav_item(self, parent, page_name: str, label: str):
        item_frame = ctk.CTkFrame(parent, fg_color="transparent", height=44, cursor="hand2")
        item_frame.pack(fill="x", pady=1)
        item_frame.pack_propagate(False)

        # Accent bar (hidden by default)
        accent = ctk.CTkFrame(item_frame, fg_color="transparent", width=3, corner_radius=2)
        accent.pack(side="left", fill="y", padx=(0, 0), pady=6)

        text_label = ctk.CTkLabel(
            item_frame, text=label,
            font=FONT_NAV_ITEM, text_color=TEXT_SECONDARY, anchor="w",
        )
        text_label.pack(side="left", padx=(PAD_SECTION, 0), fill="x", expand=True)

        self._nav_items[page_name] = {
            "frame": item_frame,
            "accent": accent,
            "label": text_label,
        }

        # Click binding on frame and label
        for widget in (item_frame, text_label):
            widget.bind("<Button-1>", lambda e, p=page_name: self._on_click(p))
            widget.bind("<Enter>", lambda e, p=page_name: self._on_enter(p))
            widget.bind("<Leave>", lambda e, p=page_name: self._on_leave(p))

    def _on_click(self, page_name: str):
        if self._on_navigate:
            self._on_navigate(page_name)

    def _on_enter(self, page_name: str):
        if page_name != self._active:
            self._nav_items[page_name]["frame"].configure(fg_color=SIDEBAR_HOVER_BG)

    def _on_leave(self, page_name: str):
        if page_name != self._active:
            self._nav_items[page_name]["frame"].configure(fg_color="transparent")

    def set_active(self, page_name: str):
        # Deactivate previous
        if self._active and self._active in self._nav_items:
            prev = self._nav_items[self._active]
            prev["frame"].configure(fg_color="transparent")
            prev["accent"].configure(fg_color="transparent")
            prev["label"].configure(font=FONT_NAV_ITEM, text_color=TEXT_SECONDARY)

        # Activate new
        self._active = page_name
        if page_name in self._nav_items:
            item = self._nav_items[page_name]
            item["frame"].configure(fg_color=SIDEBAR_ACTIVE_BG)
            item["accent"].configure(fg_color=ACCENT_BLUE)
            item["label"].configure(font=FONT_NAV_ACTIVE, text_color=TEXT_PRIMARY)
