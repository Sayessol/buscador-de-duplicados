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

TEMA_COLOR = "blue"        # tema base de CustomTkinter para los botones

# "auto" (sistema) | "claro" | "oscuro"  ->  valor interno de CustomTkinter
_MAPA_TEMA = {"auto": "system", "claro": "light", "oscuro": "dark"}
TEMAS = ("auto", "claro", "oscuro")

# ----------------------------------------------------------------------
# Paleta   (claro, oscuro)
# ----------------------------------------------------------------------
# Superficies
COLOR_FONDO        = ("#f2f4f7", "#242424")   # fondo de la ventana
COLOR_CABECERA     = ("#e7eaef", "#1e1e1e")   # barra de título de la app
COLOR_TARJETA      = ("#ffffff", "#2b2b2b")   # tarjetas de sección
COLOR_BALDOSA      = ("#eef1f5", "#333333")   # baldosas de estadística
COLOR_FONDO_TABLA  = ("#ffffff", "#2b2b2b")   # fondo de la tabla ttk
COLOR_FILA_ALTERNA = ("#eef1f5", "#323232")
COLOR_BORDE        = ("#c9d0d9", "#4a4d52")   # borde de botones "secundarios"

# Texto
COLOR_TEXTO        = ("#1e2227", "#e6ebf2")   # texto principal
COLOR_TEXTO_TENUE  = ("#586069", "#a9b0ba")   # texto secundario / pistas

# Acentos (como color de TEXTO; ya contrastan sobre tarjeta y fondo)
COLOR_ACENTO       = ("#1f6aa5", "#4aa3df")
COLOR_OK           = ("#1c7c4a", "#57c98b")   # "conservar" / validación correcta
COLOR_ADVERTENCIA  = ("#8a5a00", "#e6bf49")   # "mover" / avisos
COLOR_PELIGRO      = ("#b5372c", "#ea6f66")   # errores (texto)

# Rellenos de botón (llevan texto BLANCO encima en los dos temas)
COLOR_SELECCION     = ("#1f6aa5", "#1f6aa5")  # fila seleccionada de la tabla
COLOR_OK_BOTON      = ("#1e7850", "#25805a")  # botón de acción (mover, reunir)
COLOR_PELIGRO_BOTON = ("#c0392b", "#b5372c")  # botón peligroso (cancelar)

# Botón DESHABILITADO: relleno y texto grises, para que se entienda que
# está apagado y no se confunda con un color de error o de acción.
COLOR_BOTON_OFF        = ("#dfe3e8", "#3a3d42")
COLOR_BOTON_OFF_TEXTO  = ("#98a0aa", "#6b7078")

# Fila de un grupo todavía sin resolver (fondo suave).
COLOR_GRUPO_PENDIENTE = ("#fbf1d5", "#4a3a12")


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
_AZUL = "#1F6AA5"
_AZUL_HOVER = "#144870"
_BLANCO = "#FFFFFF"
_GRIS_PESTANA = "#6B7078"        # pestañas sin seleccionar en modo claro (4,98:1 con blanco)
_GRIS_PESTANA_HOVER = "#565B5E"


def _retocar_contraste():
    """Sustituye los colores por defecto de CustomTkinter que no alcanzan AA."""
    t = ctk.ThemeManager.theme

    def par(c):                      # mismo color en modo claro y oscuro
        return [c, c]

    for nombre in ("CTkButton", "CTkOptionMenu", "CTkSegmentedButton"):
        t[nombre]["text_color"] = par(_BLANCO)

    t["CTkButton"]["fg_color"] = par(_AZUL)
    t["CTkButton"]["hover_color"] = par(_AZUL_HOVER)

    om = t["CTkOptionMenu"]
    om["fg_color"] = par(_AZUL)
    om["button_color"] = par(_AZUL_HOVER)
    om["button_hover_color"] = ["#0F3553", "#203A4F"]

    sb = t["CTkSegmentedButton"]
    sb["selected_color"] = par(_AZUL)
    sb["selected_hover_color"] = par(_AZUL_HOVER)
    sb["fg_color"] = [_GRIS_PESTANA, "gray29"]
    sb["unselected_color"] = [_GRIS_PESTANA, "gray29"]
    sb["unselected_hover_color"] = [_GRIS_PESTANA_HOVER, "gray41"]

    for nombre, clave in (("CTkCheckBox", "fg_color"), ("CTkCheckBox", "hover_color"),
                          ("CTkSlider", "button_color"), ("CTkProgressBar", "progress_color")):
        t[nombre][clave] = par(_AZUL)
    t["CTkCheckBox"]["checkmark_color"] = par(_BLANCO)


def aplicar_tema(tema="auto"):
    """Llamar una vez al arrancar, antes de crear la ventana."""
    ctk.set_default_color_theme(TEMA_COLOR)

    # Retoques al tema base de CustomTkinter para que todos los botones
    # sean coherentes:
    #  · borde visible en los botones "secundarios" (los transparentes),
    #  · texto claramente atenuado cuando están deshabilitados (que se
    #    entienda que están apagados y no que hay un error).
    b = ctk.ThemeManager.theme["CTkButton"]
    b["border_color"] = list(COLOR_BORDE)
    b["text_color_disabled"] = list(COLOR_BOTON_OFF_TEXTO)
    _retocar_contraste()

    ctk.set_appearance_mode(_MAPA_TEMA.get(tema, "system"))


def cambiar_tema(tema):
    """Cambia el tema en caliente. CustomTkinter re-pinta sus widgets solo;
    lo demás lo re-pinta _set_appearance_mode en las ventanas."""
    ctk.set_appearance_mode(_MAPA_TEMA.get(tema, "system"))


# ----------------------------------------------------------------------
# Botones: activar / desactivar dejando claro el estado
# ----------------------------------------------------------------------
def _tema_boton(clave):
    return ctk.ThemeManager.theme["CTkButton"][clave]


def activar_boton(btn, activo, *, fg=None, hover=None, texto=None):
    """Activa o desactiva un botón.

    Al desactivar: relleno y texto grises + cursor de "no". Así se ve que
    está apagado y no parece un error ni una acción disponible.
    Al activar: `fg`/`hover`/`texto` opcionales. Si el relleno es
    "transparent" el texto pasa a ser el color de texto normal (oscuro en
    claro, claro en oscuro); si es un relleno de color, texto claro.
    """
    if activo:
        if texto is None:
            texto = COLOR_TEXTO if fg == "transparent" else _tema_boton("text_color")
        btn.configure(
            state="normal",
            fg_color=fg if fg is not None else _tema_boton("fg_color"),
            hover_color=hover if hover is not None else _tema_boton("hover_color"),
            text_color=texto)
    else:
        btn.configure(state="disabled", fg_color=COLOR_BOTON_OFF,
                      hover_color=COLOR_BOTON_OFF,
                      text_color=COLOR_BOTON_OFF_TEXTO)


# Verde «al pasar el ratón» del botón de acción (mover a cuarentena, reunir).
HOVER_ACCION = ("#16623f", "#1f6b47")


def boton_accion(btn, activo):
    """Botón verde de acción (mover a cuarentena, reunir): al desactivar se
    pone gris para que se vea que está apagado."""
    activar_boton(btn, activo, fg=COLOR_OK_BOTON, hover=HOVER_ACCION)


# ----------------------------------------------------------------------
# Fuentes
# ----------------------------------------------------------------------
def fuente_base(size=13, weight="normal"):
    return ctk.CTkFont(size=size, weight=weight)


def fuente_titulo(size=15):
    return ctk.CTkFont(size=size, weight="bold")


def fuente_numero(size=22):
    return ctk.CTkFont(size=size, weight="bold")


def fuente_tabla():
    """Fuente para la tabla ttk (no acepta CTkFont, necesita tkfont)."""
    return tkfont.Font(family="Segoe UI", size=10)


def fuente_tabla_encabezado():
    return tkfont.Font(family="Segoe UI", size=10, weight="bold")
