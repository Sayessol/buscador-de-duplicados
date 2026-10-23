"""Colour contrast (WCAG 2.x): text must be readable on its background.

It checks, in the light and the dark theme, every "text on background" pair that the
interface uses. The criterion is WCAG level AA: **4.5:1** for normal text.

Exception: the disabled button. WCAG does not require contrast for disabled
controls, and here it is also intentional that it looks "switched off"; what is
checked is that it stays readable (≥ 2:1) and that it can be told apart from an active button.

    pytest tests/test_contrast.py
"""

import pytest

from ui import styles

THEMES = {"claro": 0, "oscuro": 1}
AA_TEXT = 4.5           # WCAG AA, normal text
WHITE = "#ffffff"


def _luminance(hex_):
    """Relative luminance of a #rrggbb colour (WCAG formula)."""
    hex_ = hex_.lstrip("#")
    channels = []
    for i in (0, 2, 4):
        c = int(hex_[i:i + 2], 16) / 255
        channels.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = channels
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    """Contrast ratio between two colours: from 1 (equal) to 21 (black on white)."""
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


# Text of colour X on background Y (names from ui/styles.py)
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

# WHITE text on button or selection fills
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
    # And it is not mistaken for an active button or an error one:
    for active in (styles.COLOR_OK_BUTTON, styles.COLOR_DANGER_BUTTON, styles.COLOR_SELECTION):
        assert background.lower() != active[i].lower()
        assert contrast(background, active[i]) >= 1.5, "deshabilitado y activo se parecen demasiado"
    assert contrast(background, styles.COLOR_CARD[i]) >= 1.08, "el botón se funde con la tarjeta"


def test_contrast_meter_is_correct():
    """Check of the meter itself, with WCAG reference values."""
    assert contrast("#000000", "#ffffff") == pytest.approx(21.0)
    assert contrast("#ffffff", "#ffffff") == pytest.approx(1.0)
    assert contrast("#767676", "#ffffff") == pytest.approx(4.54, abs=0.01)   # lightest AA grey
    assert contrast("#777777", "#ffffff") < AA_TEXT                          # no longer enough
