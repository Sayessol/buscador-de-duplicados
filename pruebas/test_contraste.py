"""Contraste de color (WCAG 2.x): el texto debe poder leerse sobre su fondo.

Comprueba, en el tema claro y en el oscuro, cada pareja «texto sobre fondo» que
usa la interfaz. El criterio es el nivel AA de WCAG: **4,5:1** para texto normal.

Excepción: el botón deshabilitado. WCAG no exige contraste a los controles
deshabilitados, y aquí además es intencionado que se vea «apagado»; lo que se
comprueba es que siga siendo legible (≥ 2:1) y que se distinga de un botón activo.

    pytest pruebas/test_contraste.py
"""

import pytest

from ui import styles

TEMAS = {"claro": 0, "oscuro": 1}
AA_TEXTO = 4.5           # WCAG AA, texto normal
BLANCO = "#ffffff"


def _luminancia(hex_):
    """Luminancia relativa de un color #rrggbb (fórmula de WCAG)."""
    hex_ = hex_.lstrip("#")
    canales = []
    for i in (0, 2, 4):
        c = int(hex_[i:i + 2], 16) / 255
        canales.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = canales
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(a, b):
    """Razón de contraste entre dos colores: de 1 (iguales) a 21 (negro sobre blanco)."""
    la, lb = sorted((_luminancia(a), _luminancia(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


# Texto del color X sobre el fondo Y (nombres de ui/styles.py)
TEXTO_SOBRE_FONDO = [
    (texto, fondo)
    for texto, fondos in {
        "COLOR_TEXTO": ["COLOR_FONDO", "COLOR_CABECERA", "COLOR_TARJETA", "COLOR_BALDOSA",
                        "COLOR_FONDO_TABLA", "COLOR_FILA_ALTERNA", "COLOR_GRUPO_PENDIENTE"],
        "COLOR_TEXTO_TENUE": ["COLOR_FONDO", "COLOR_CABECERA", "COLOR_TARJETA", "COLOR_BALDOSA",
                              "COLOR_FONDO_TABLA", "COLOR_FILA_ALTERNA"],
        "COLOR_OK": ["COLOR_TARJETA", "COLOR_BALDOSA", "COLOR_FONDO_TABLA", "COLOR_FILA_ALTERNA"],
        "COLOR_ADVERTENCIA": ["COLOR_TARJETA", "COLOR_BALDOSA", "COLOR_FONDO_TABLA",
                              "COLOR_FILA_ALTERNA"],
        "COLOR_PELIGRO": ["COLOR_FONDO", "COLOR_TARJETA"],
        "COLOR_ACENTO": ["COLOR_FONDO", "COLOR_CABECERA", "COLOR_TARJETA"],
    }.items()
    for fondo in fondos
]

# Texto BLANCO sobre rellenos de botón o de selección
RELLENOS_CON_TEXTO_BLANCO = {
    "selección de la tabla": styles.COLOR_SELECCION,
    "botón de acción (verde)": styles.COLOR_OK_BOTON,
    "botón de acción, al pasar el ratón": styles.HOVER_ACCION,
    "botón peligroso (rojo)": styles.COLOR_PELIGRO_BOTON,
    "botón azul": (styles._AZUL, styles._AZUL),
    "botón azul, al pasar el ratón": (styles._AZUL_HOVER, styles._AZUL_HOVER),
    "pestaña sin seleccionar": (styles._GRIS_PESTANA, "#4a4a4a"),
    "pestaña sin seleccionar, al pasar el ratón": (styles._GRIS_PESTANA_HOVER, "#696969"),
}


@pytest.mark.parametrize("tema", TEMAS)
@pytest.mark.parametrize("texto, fondo", TEXTO_SOBRE_FONDO)
def test_texto_legible_sobre_su_fondo(tema, texto, fondo):
    i = TEMAS[tema]
    c = contraste(getattr(styles, texto)[i], getattr(styles, fondo)[i])
    assert c >= AA_TEXTO, f"{texto} sobre {fondo} ({tema}): {c:.2f}:1, hace falta {AA_TEXTO}:1"


@pytest.mark.parametrize("tema", TEMAS)
@pytest.mark.parametrize("nombre", RELLENOS_CON_TEXTO_BLANCO)
def test_texto_blanco_legible_sobre_rellenos(tema, nombre):
    relleno = RELLENOS_CON_TEXTO_BLANCO[nombre][TEMAS[tema]]
    c = contraste(BLANCO, relleno)
    assert c >= AA_TEXTO, f"Texto blanco sobre «{nombre}» ({tema}, {relleno}): {c:.2f}:1"


@pytest.mark.parametrize("tema", TEMAS)
def test_boton_deshabilitado_se_ve_apagado_pero_legible(tema):
    i = TEMAS[tema]
    fondo, texto = styles.COLOR_BOTON_OFF[i], styles.COLOR_BOTON_OFF_TEXTO[i]
    assert contraste(texto, fondo) >= 2.0, "el texto deshabilitado casi no se ve"
    # Y no se confunde con un botón activo ni con uno de error:
    for activo in (styles.COLOR_OK_BOTON, styles.COLOR_PELIGRO_BOTON, styles.COLOR_SELECCION):
        assert fondo.lower() != activo[i].lower()
        assert contraste(fondo, activo[i]) >= 1.5, "deshabilitado y activo se parecen demasiado"
    assert contraste(fondo, styles.COLOR_TARJETA[i]) >= 1.08, "el botón se funde con la tarjeta"


def test_el_medidor_de_contraste_es_correcto():
    """Comprobación del propio medidor, con los valores de referencia de WCAG."""
    assert contraste("#000000", "#ffffff") == pytest.approx(21.0)
    assert contraste("#ffffff", "#ffffff") == pytest.approx(1.0)
    assert contraste("#767676", "#ffffff") == pytest.approx(4.54, abs=0.01)   # el gris AA más claro
    assert contraste("#777777", "#ffffff") < AA_TEXTO                          # ya no llega
