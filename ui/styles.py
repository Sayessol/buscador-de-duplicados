"""Colours, fonts and theme of the interface.

Everything is centralized so the app has a coherent look and is easy
to tweak in a single place.

Light / dark theme
------------------
The app can run in **light**, **dark** or **automatic** mode (it follows the
system). Each colour is defined as a ``(light, dark)`` tuple:

* CustomTkinter widgets accept that tuple as it is and switch on their own
  when the theme changes.
* For what is NOT CustomTkinter (the ``ttk.Treeview`` table and some
  ``tk.Canvas``) ``col(tuple)`` is used, which returns the colour that applies
  for the active theme. Those elements are repainted by hand when the theme
  changes (see ``_set_appearance_mode`` in main_window and results_table).

Contrast
--------
The text colours are chosen to meet WCAG AA contrast
(>= 4.5:1) against their real background, in both themes.
"""

import tkinter.font as tkfont

import customtkinter as ctk

THEME_COLOR = "blue"        # base CustomTkinter theme for the buttons

# "auto" (system) | "light" | "dark"  ->  internal CustomTkinter value
_THEME_MAP = {"auto": "system", "light": "light", "dark": "dark"}
THEMES = ("auto", "light", "dark")

# ----------------------------------------------------------------------
# Palette   (light, dark)
# ----------------------------------------------------------------------
# Surfaces
COLOR_BACKGROUND        = ("#f2f4f7", "#242424")   # window background
COLOR_HEADER     = ("#e7eaef", "#1e1e1e")   # title bar of the app
COLOR_CARD      = ("#ffffff", "#2b2b2b")   # section cards
COLOR_TILE      = ("#eef1f5", "#333333")   # statistics tiles
COLOR_TABLE_BACKGROUND  = ("#ffffff", "#2b2b2b")   # background of the ttk table
COLOR_ALTERNATE_ROW = ("#eef1f5", "#323232")
COLOR_BORDER        = ("#c9d0d9", "#4a4d52")   # border of "secondary" buttons

# Text
COLOR_TEXT        = ("#1e2227", "#e6ebf2")   # main text
COLOR_MUTED_TEXT  = ("#586069", "#a9b0ba")   # secondary text / hints

# Accents (as TEXT colour; they already contrast on card and background)
COLOR_ACCENT       = ("#1f6aa5", "#4aa3df")
COLOR_OK           = ("#1c7c4a", "#57c98b")   # "keep" / validation passed
COLOR_WARNING  = ("#8a5a00", "#e6bf49")   # "move" / warnings
COLOR_DANGER      = ("#b5372c", "#ea6f66")   # errors (text)

# Button fills (they carry WHITE text on top in both themes)
COLOR_SELECTION     = ("#1f6aa5", "#1f6aa5")  # selected row of the table
COLOR_OK_BUTTON      = ("#1e7850", "#25805a")  # action button (move, gather)
COLOR_DANGER_BUTTON = ("#c0392b", "#b5372c")  # dangerous button (cancel)

# DISABLED button: grey fill and text, so it is understood that it
# is switched off and not mistaken for an error or action colour.
COLOR_BUTTON_OFF        = ("#dfe3e8", "#3a3d42")
COLOR_BUTTON_OFF_TEXT  = ("#98a0aa", "#6b7078")

# Row of a group that is still unresolved (soft background).
COLOR_PENDING_GROUP = ("#fbf1d5", "#4a3a12")


def col(t):
    """From a (light, dark) tuple returns the colour of the active theme.

    For elements that are not CustomTkinter (ttk, tk.Canvas).
    """
    if isinstance(t, (list, tuple)):
        return t[0] if ctk.get_appearance_mode() == "Light" else t[1]
    return t


# ----------------------------------------------------------------------
# Theme
# ----------------------------------------------------------------------
# Blue of the controls and the text on top of them. The base CustomTkinter theme
# uses #3B8ED0 in light mode (white text on it = 3.5:1) and #DCE4EE text (2.7:1):
# it does not reach AA. With #1F6AA5 and pure white the contrast is 5.7:1 in both themes.
_BLUE = "#1F6AA5"
_BLUE_HOVER = "#144870"
_WHITE = "#FFFFFF"
_TAB_GRAY = "#6B7078"        # unselected tabs in light mode (4.98:1 with white)
_TAB_GRAY_HOVER = "#565B5E"


def _adjust_contrast():
    """Replaces the default CustomTkinter colours that do not reach AA."""
    t = ctk.ThemeManager.theme

    def par(c):                      # same colour in light and dark mode
        return [c, c]

    for name in ("CTkButton", "CTkOptionMenu", "CTkSegmentedButton"):
        t[name]["text_color"] = par(_WHITE)

    t["CTkButton"]["fg_color"] = par(_BLUE)
    t["CTkButton"]["hover_color"] = par(_BLUE_HOVER)

    om = t["CTkOptionMenu"]
    om["fg_color"] = par(_BLUE)
    om["button_color"] = par(_BLUE_HOVER)
    om["button_hover_color"] = ["#0F3553", "#203A4F"]

    sb = t["CTkSegmentedButton"]
    sb["selected_color"] = par(_BLUE)
    sb["selected_hover_color"] = par(_BLUE_HOVER)
    sb["fg_color"] = [_TAB_GRAY, "gray29"]
    sb["unselected_color"] = [_TAB_GRAY, "gray29"]
    sb["unselected_hover_color"] = [_TAB_GRAY_HOVER, "gray41"]

    for name, key in (("CTkCheckBox", "fg_color"), ("CTkCheckBox", "hover_color"),
                          ("CTkSlider", "button_color"), ("CTkProgressBar", "progress_color")):
        t[name][key] = par(_BLUE)
    t["CTkCheckBox"]["checkmark_color"] = par(_WHITE)


def apply_theme(theme="auto"):
    """Call once at startup, before creating the window."""
    ctk.set_default_color_theme(THEME_COLOR)

    # Tweaks to the base CustomTkinter theme so that all the buttons
    # are consistent:
    # · visible border on "secondary" buttons (the transparent ones),
    # · clearly dimmed text when they are disabled (so that it is
    # understood they are switched off and that it is not an error).
    b = ctk.ThemeManager.theme["CTkButton"]
    b["border_color"] = list(COLOR_BORDER)
    b["text_color_disabled"] = list(COLOR_BUTTON_OFF_TEXT)
    _adjust_contrast()

    ctk.set_appearance_mode(_THEME_MAP.get(theme, "system"))


def change_theme(theme):
    """Switches the theme on the fly. CustomTkinter repaints its widgets by itself;
    the rest is repainted by _set_appearance_mode in the windows."""
    ctk.set_appearance_mode(_THEME_MAP.get(theme, "system"))


# ----------------------------------------------------------------------
# Buttons: enable / disable making the state clear
# ----------------------------------------------------------------------
def _button_theme(key):
    return ctk.ThemeManager.theme["CTkButton"][key]


def activate_button(btn, active, *, fg=None, hover=None, text=None):
    """Enables or disables a button.

    When disabling: grey fill and text + a "no" cursor. This way it is clear that it
    is switched off and it does not look like an error or an available action.
    When enabling: optional `fg`/`hover`/`text`. If the fill is
    "transparent" the text becomes the normal text colour (dark in
    light, light in dark); if it is a colour fill, light text.
    """
    if active:
        if text is None:
            text = COLOR_TEXT if fg == "transparent" else _button_theme("text_color")
        btn.configure(
            state="normal",
            fg_color=fg if fg is not None else _button_theme("fg_color"),
            hover_color=hover if hover is not None else _button_theme("hover_color"),
            text_color=text)
    else:
        btn.configure(state="disabled", fg_color=COLOR_BUTTON_OFF,
                      hover_color=COLOR_BUTTON_OFF,
                      text_color=COLOR_BUTTON_OFF_TEXT)


# Green on mouse hover of the action button (move to quarantine, gather).
ACTION_HOVER = ("#16623f", "#1f6b47")


def action_button(btn, active):
    """Green action button (move to quarantine, gather): when disabled it
    turns grey so it is clear it is switched off."""
    activate_button(btn, active, fg=COLOR_OK_BUTTON, hover=ACTION_HOVER)


# ----------------------------------------------------------------------
# Fonts
# ----------------------------------------------------------------------
def base_font(size=13, weight="normal"):
    return ctk.CTkFont(size=size, weight=weight)


def title_font(size=15):
    return ctk.CTkFont(size=size, weight="bold")


def number_font(size=22):
    return ctk.CTkFont(size=size, weight="bold")


def table_font():
    """Font for the ttk table (it does not accept CTkFont, it needs tkfont)."""
    return tkfont.Font(family="Segoe UI", size=10)


def table_heading_font():
    return tkfont.Font(family="Segoe UI", size=10, weight="bold")
