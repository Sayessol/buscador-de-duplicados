"""Contraste de color (WCAG 2.x): el texto debe poder leerse sobre su fondo.

Comprueba, en el tema claro y en el oscuro, cada pareja «texto sobre fondo» que
usa la interfaz. El criterio es el nivel AA de WCAG: **4,5:1** para texto normal.

Excepción: el botón deshabilitado. WCAG no exige contraste a los controles
deshabilitados, y aquí además es intencionado que se vea «apagado»; lo que se
comprueba es que siga siendo legible (≥ 2:1) y que se distinga de un botón activo.

    pytest tests/test_contrast.py
"""

import pytest

from ui import styles

THEMES = {"claro": 0, "oscuro": 1}
AA_TEXT = 4.5           # WCAG AA, texto normal
WHITE = "#ffffff"


def _luminance(hex_):
    """Luminancia relativa de un color #rrggbb (fórmula de WCAG)."""
    hex_ = hex_.lstrip("#")
    channels = []
    for i in (0, 2, 4):
        c = int(hex_[i:i + 2], 16) / 255
        channels.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = channels
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    """Razón de contraste entre dos colores: de 1 (iguales) a 21 (negro sobre blanco)."""
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


# Texto del color X sobre el fondo Y (nombres de ui/styles.py)
TEXT_ON_BACKGROUND = [
    (text, background)
    for text, backgrounds in {
        "COLOR_TEXT": ["COLOR_BACKGROUND", "COLOR_HEADER", "COLOR_CARD", "COLOR_TILE",
                        "COLOR_TABLE_BACKGROUND", "COLOR_ALTERNATE_ROW", "COLOR_PENDING_GROUP"],
        "COLOR_MUTED_TEXT": ["COLOR_BACKGROUND", "COLOR_HEADER", "COLOR_CARD", "COLOR_TILE",
                              "COLOR_TABLE_BACKGROUND", "COLOR_ALTERNATE_ROW"],
        "COLOR_OK": ["COLOR_CARD", "COLOR_TILE", "COLOR_TABLE_BACKGROUND", "COLOR_ALTERNATE_ROW"],
        "COLOR_WARNING": ["COLOR_CARD", "COLOR_TILE", "COLOR_TABLE_BACKGROUND",
                              "COLOR_ALTERNATE_ROW"],
        "COLOR_DANGER": ["COLOR_BACKGROUND", "COLOR_CARD"],
        "COLOR_ACCENT": ["COLOR_BACKGROUND", "COLOR_HEADER", "COLOR_CARD"],
    }.items()
    for background in backgrounds
]

# Texto BLANCO sobre rellenos de botón o de selección
FILLS_WITH_WHITE_TEXT = {
    "selección de la tabla": styles.COLOR_SELECTION,
    "botón de acción (verde)": styles.COLOR_OK_BUTTON,
    "botón de acción, al pasar el ratón": styles.ACTION_HOVER,
    "botón peligroso (rojo)": styles.COLOR_DANGER_BUTTON,
    "botón azul": (styles._BLUE, styles._BLUE),
    "botón azul, al pasar el ratón": (styles._BLUE_HOVER, styles._BLUE_HOVER),
    "pestaña sin seleccionar": (styles._TAB_GRAY, "#4a4a4a"),
    "pestaña sin seleccionar, al pasar el ratón": (styles._TAB_GRAY_HOVER, "#696969"),
}


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("text, background", TEXT_ON_BACKGROUND)
def test_text_readable_on_its_background(theme, text, background):
    i = THEMES[theme]
    c = contrast(getattr(styles, text)[i], getattr(styles, background)[i])
    assert c >= AA_TEXT, f"{text} sobre {background} ({theme}): {c:.2f}:1, hace falta {AA_TEXT}:1"


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("name", FILLS_WITH_WHITE_TEXT)
def test_white_text_readable_on_fills(theme, name):
    fill = FILLS_WITH_WHITE_TEXT[name][THEMES[theme]]
    c = contrast(WHITE, fill)
    assert c >= AA_TEXT, f"Texto blanco sobre «{name}» ({theme}, {fill}): {c:.2f}:1"


@pytest.mark.parametrize("theme", THEMES)
def test_disabled_button_looks_off_but_readable(theme):
    i = THEMES[theme]
    background, text = styles.COLOR_BUTTON_OFF[i], styles.COLOR_BUTTON_OFF_TEXT[i]
    assert contrast(text, background) >= 2.0, "el texto deshabilitado casi no se ve"
    # Y no se confunde con un botón activo ni con uno de error:
    for active in (styles.COLOR_OK_BUTTON, styles.COLOR_DANGER_BUTTON, styles.COLOR_SELECTION):
        assert background.lower() != active[i].lower()
        assert contrast(background, active[i]) >= 1.5, "deshabilitado y activo se parecen demasiado"
    assert contrast(background, styles.COLOR_CARD[i]) >= 1.08, "el botón se funde con la tarjeta"


def test_contrast_meter_is_correct():
    """Comprobación del propio medidor, con los valores de referencia de WCAG."""
    assert contrast("#000000", "#ffffff") == pytest.approx(21.0)
    assert contrast("#ffffff", "#ffffff") == pytest.approx(1.0)
    assert contrast("#767676", "#ffffff") == pytest.approx(4.54, abs=0.01)   # el gris AA más claro
    assert contrast("#777777", "#ffffff") < AA_TEXT                          # ya no llega
