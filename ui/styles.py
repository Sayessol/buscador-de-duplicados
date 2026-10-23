"""Colores, fuentes y tema de la interfaz.

Todo centralizado para que la app tenga un aspecto coherente y sea fácil
de retocar en un solo sitio.

Tema claro / oscuro
-------------------
La app puede ir en modo **claro**, **oscuro** o **automático** (sigue al
sistema). Cada color se define como una tupla ``(claro, oscuro)``:

* Los widgets de CustomTkinter aceptan esa tupla tal cual y cambian solos
  cuando cambia el tema.
* Para lo que NO es CustomTkinter (la tabla ``ttk.Treeview`` y algún
  ``tk.Canvas``) se usa ``col(tupla)``, que devuelve el color que toca
  según el tema activo. Esos elementos se re-pintan a mano cuando el tema
  cambia (ver ``_set_appearance_mode`` en main_window y results_table).

Contraste
---------
Los colores de texto están elegidos para cumplir contraste WCAG AA
(>= 4.5:1) sobre su fondo real, en los dos temas.
"""

import tkinter.font as tkfont

import customtkinter as ctk

THEME_COLOR = "blue"        # tema base de CustomTkinter para los botones

# "auto" (sistema) | "claro" | "oscuro"  ->  valor interno de CustomTkinter
_THEME_MAP = {"auto": "system", "claro": "light", "oscuro": "dark"}
THEMES = ("auto", "claro", "oscuro")

# ----------------------------------------------------------------------
# Paleta   (claro, oscuro)
# ----------------------------------------------------------------------
# Superficies
COLOR_BACKGROUND        = ("#f2f4f7", "#242424")   # fondo de la ventana
COLOR_HEADER     = ("#e7eaef", "#1e1e1e")   # barra de título de la app
COLOR_CARD      = ("#ffffff", "#2b2b2b")   # tarjetas de sección
COLOR_TILE      = ("#eef1f5", "#333333")   # baldosas de estadística
COLOR_TABLE_BACKGROUND  = ("#ffffff", "#2b2b2b")   # fondo de la tabla ttk
COLOR_ALTERNATE_ROW = ("#eef1f5", "#323232")
COLOR_BORDER        = ("#c9d0d9", "#4a4d52")   # borde de botones "secundarios"

# Texto
COLOR_TEXT        = ("#1e2227", "#e6ebf2")   # texto principal
COLOR_MUTED_TEXT  = ("#586069", "#a9b0ba")   # texto secundario / pistas

# Acentos (como color de TEXTO; ya contrastan sobre tarjeta y fondo)
COLOR_ACCENT       = ("#1f6aa5", "#4aa3df")
COLOR_OK           = ("#1c7c4a", "#57c98b")   # "conservar" / validación correcta
COLOR_WARNING  = ("#8a5a00", "#e6bf49")   # "mover" / avisos
COLOR_DANGER      = ("#b5372c", "#ea6f66")   # errores (texto)

# Rellenos de botón (llevan texto BLANCO encima en los dos temas)
COLOR_SELECTION     = ("#1f6aa5", "#1f6aa5")  # fila seleccionada de la tabla
COLOR_OK_BUTTON      = ("#1e7850", "#25805a")  # botón de acción (mover, reunir)
COLOR_DANGER_BUTTON = ("#c0392b", "#b5372c")  # botón peligroso (cancelar)

# Botón DESHABILITADO: relleno y texto grises, para que se entienda que
# está apagado y no se confunda con un color de error o de acción.
COLOR_BUTTON_OFF        = ("#dfe3e8", "#3a3d42")
COLOR_BUTTON_OFF_TEXT  = ("#98a0aa", "#6b7078")

# Fila de un grupo todavía sin resolver (fondo suave).
COLOR_PENDING_GROUP = ("#fbf1d5", "#4a3a12")


def col(t):
    """De una tupla (claro, oscuro) devuelve el color del tema activo.

    Para elementos que no son de CustomTkinter (ttk, tk.Canvas).
    """
    if isinstance(t, (list, tuple)):
        return t[0] if ctk.get_appearance_mode() == "Light" else t[1]
    return t


# ----------------------------------------------------------------------
# Tema
# ----------------------------------------------------------------------
# Azul de los controles y texto que llevan encima. El tema base de CustomTkinter
# usa #3B8ED0 en modo claro (texto blanco encima = 3,5:1) y texto #DCE4EE (2,7:1):
# no llega a AA. Con #1F6AA5 y blanco puro el contraste es 5,7:1 en los dos temas.
_BLUE = "#1F6AA5"
_BLUE_HOVER = "#144870"
_WHITE = "#FFFFFF"
_TAB_GRAY = "#6B7078"        # pestañas sin seleccionar en modo claro (4,98:1 con blanco)
_TAB_GRAY_HOVER = "#565B5E"


def _adjust_contrast():
    """Sustituye los colores por defecto de CustomTkinter que no alcanzan AA."""
    t = ctk.ThemeManager.theme

    def par(c):                      # mismo color en modo claro y oscuro
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
    """Llamar una vez al arrancar, antes de crear la ventana."""
    ctk.set_default_color_theme(THEME_COLOR)

    # Retoques al tema base de CustomTkinter para que todos los botones
    # sean coherentes:
    #  · borde visible en los botones "secundarios" (los transparentes),
    #  · texto claramente atenuado cuando están deshabilitados (que se
    #    entienda que están apagados y no que hay un error).
    b = ctk.ThemeManager.theme["CTkButton"]
    b["border_color"] = list(COLOR_BORDER)
    b["text_color_disabled"] = list(COLOR_BUTTON_OFF_TEXT)
    _adjust_contrast()

    ctk.set_appearance_mode(_THEME_MAP.get(theme, "system"))


def change_theme(theme):
    """Cambia el tema en caliente. CustomTkinter re-pinta sus widgets solo;
    lo demás lo re-pinta _set_appearance_mode en las ventanas."""
    ctk.set_appearance_mode(_THEME_MAP.get(theme, "system"))


# ----------------------------------------------------------------------
# Botones: activar / desactivar dejando claro el estado
# ----------------------------------------------------------------------
def _button_theme(key):
    return ctk.ThemeManager.theme["CTkButton"][key]


def activate_button(btn, active, *, fg=None, hover=None, text=None):
    """Activa o desactiva un botón.

    Al desactivar: relleno y texto grises + cursor de "no". Así se ve que
    está apagado y no parece un error ni una acción disponible.
    Al activar: `fg`/`hover`/`texto` opcionales. Si el relleno es
    "transparent" el texto pasa a ser el color de texto normal (oscuro en
    claro, claro en oscuro); si es un relleno de color, texto claro.
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


# Verde «al pasar el ratón» del botón de acción (mover a cuarentena, reunir).
ACTION_HOVER = ("#16623f", "#1f6b47")


def action_button(btn, active):
    """Botón verde de acción (mover a cuarentena, reunir): al desactivar se
    pone gris para que se vea que está apagado."""
    activate_button(btn, active, fg=COLOR_OK_BUTTON, hover=ACTION_HOVER)


# ----------------------------------------------------------------------
# Fuentes
# ----------------------------------------------------------------------
def base_font(size=13, weight="normal"):
    return ctk.CTkFont(size=size, weight=weight)


def title_font(size=15):
    return ctk.CTkFont(size=size, weight="bold")


def number_font(size=22):
    return ctk.CTkFont(size=size, weight="bold")


def table_font():
    """Fuente para la tabla ttk (no acepta CTkFont, necesita tkfont)."""
    return tkfont.Font(family="Segoe UI", size=10)


def table_heading_font():
    return tkfont.Font(family="Segoe UI", size=10, weight="bold")
