"""
Centralized theme constants for the BOS Alarm App.
All colors, fonts, spacing, and widget-style presets live here.
"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  BASE SURFACE PALETTE  (darkest → lightest, creates depth layers)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BG_ROOT     = "#0f1117"
BG_BASE     = "#161821"
BG_SURFACE  = "#1c1e2a"
BG_ELEVATED = "#242736"
BG_OVERLAY  = "#2c2f3e"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  BORDER COLORS  (lighter than surface = "raised" illusion)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BORDER_SUBTLE = "#2e3145"
BORDER_MEDIUM = "#3a3d52"
BORDER_STRONG = "#4a4e68"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TEXT COLORS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TEXT_PRIMARY   = "#e8eaf0"
TEXT_SECONDARY = "#a0a4b8"
TEXT_TERTIARY  = "#6b7084"
TEXT_DISABLED  = "#454860"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ACCENT / SEMANTIC COLORS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ACCENT_BLUE       = "#3b82f6"
ACCENT_BLUE_HOVER = "#2563eb"
ACCENT_BLUE_MUTED = "#1e40af"

GREEN_CONNECTED   = "#22c55e"
GREEN_DARK        = "#166534"
GREEN_HOVER       = "#15803d"

RED_DANGER        = "#ef4444"
RED_DANGER_HOVER  = "#dc2626"
RED_DARK          = "#991b1b"

YELLOW_HIGHLIGHT  = "#fbbf24"
YELLOW_MUTED      = "#ca8a04"

ORANGE_WARNING    = "#f97316"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  STATUS BADGE COLORS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STATUS_REQUESTED   = "#d97706"
STATUS_CONFIRMED   = "#16a34a"
STATUS_IN_PROGRESS = "#2563eb"
STATUS_REJECTED    = "#dc2626"
STATUS_FINISHED    = "#4b5563"
STATUS_DELETED     = "#4b5563"
STATUS_RETURN      = "#6b7280"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  HELICOPTER BANNER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HELI_BRIGHT = "#dc2626"
HELI_DARK   = "#7f1d1d"
HELI_BADGE  = "#b91c1c"

STAGING_BADGE = "#7c3aed"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ALARM BLINK (red pulse)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ALARM_BANNER_BRIGHT = "#dc2626"
ALARM_BANNER_DARK   = "#7f1d1d"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  BLINK COLORS  (dashboard alarm blink)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BLINK_ON  = "#1d4ed8"
BLINK_OFF = "#161821"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  BUTTON PRESETS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BTN_DISABLED_FG    = "#3a3d52"
BTN_DISABLED_HOVER = "#3a3d52"

BTN_SECONDARY_FG    = "#374151"
BTN_SECONDARY_HOVER = "#4b5563"

BTN_SAVED_FG    = GREEN_DARK
BTN_SAVED_HOVER = GREEN_DARK

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TYPOGRAPHY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FONT_FAMILY = "Segoe UI"
FONT_MONO   = "Consolas"

FONT_H1         = (FONT_FAMILY, 20, "bold")
FONT_H2         = (FONT_FAMILY, 16, "bold")
FONT_H3         = (FONT_FAMILY, 14, "bold")
FONT_BODY       = (FONT_FAMILY, 13)
FONT_BODY_BOLD  = (FONT_FAMILY, 13, "bold")
FONT_SMALL      = (FONT_FAMILY, 12)
FONT_CAPTION    = (FONT_FAMILY, 11)
FONT_MONO_SMALL = (FONT_MONO, 11)
FONT_BADGE      = (FONT_FAMILY, 10, "bold")
FONT_BANNER     = (FONT_FAMILY, 24, "bold")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SIDEBAR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SIDEBAR_WIDTH     = 220
SIDEBAR_BG        = "#111320"
SIDEBAR_ACTIVE_BG = "#1a1d2e"
SIDEBAR_HOVER_BG  = "#151828"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TYPOGRAPHY (additional)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FONT_STAT_NUMBER = (FONT_FAMILY, 32, "bold")
FONT_STAT_TITLE  = (FONT_FAMILY, 12)
FONT_STAT_SUB    = (FONT_FAMILY, 11)
FONT_NAV_ITEM    = (FONT_FAMILY, 14)
FONT_NAV_ACTIVE  = (FONT_FAMILY, 14, "bold")
FONT_APP_TITLE   = (FONT_FAMILY, 18, "bold")
FONT_APP_VERSION = (FONT_FAMILY, 11)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SPACING CONSTANTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PAD_OUTER   = 14
PAD_SECTION = 12
PAD_INNER   = 8
PAD_TIGHT   = 4
PAD_PAGE          = 24
PAD_CARD_GAP      = 12
PAD_CARD_INTERNAL = 20

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  WIDGET GEOMETRY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CARD_CORNER_RADIUS   = 12
CARD_BORDER_WIDTH    = 1
BADGE_CORNER_RADIUS  = 6
BADGE_HEIGHT         = 22
PANEL_CORNER_RADIUS  = 10
BUTTON_CORNER_RADIUS = 8
BUTTON_HEIGHT        = 36
ENTRY_CORNER_RADIUS  = 8
STAT_CARD_RADIUS     = 14
ACCENT_STRIP_WIDTH   = 4
SETTINGS_CARD_RADIUS = 12
SETTINGS_LABEL_WIDTH = 200
SETTINGS_ENTRY_WIDTH = 400
