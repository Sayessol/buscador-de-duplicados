"""Reparto de los grupos de «Fotos parecidas» en páginas.

Windows no dibuja ventanas de más de 32.767 px de alto: si la galería los
supera se corta y desaparece la barra de desplazamiento.
"""

import pytest

from ui.pestana_parecidas import (
    ALTO_CABECERA, ALTO_FILA, ALTO_MAX_PAGINA, COLUMNAS, GRUPOS_MAX_PAGINA,
    repartir_en_paginas,
)

LIMITE_WINDOWS = 32767


def _alto(n):
    return ALTO_CABECERA + ALTO_FILA * -(-n // COLUMNAS)


def test_sin_grupos_no_hay_paginas():
    assert repartir_en_paginas([]) == []


def test_pocos_grupos_caben_en_una_pagina():
    assert repartir_en_paginas([3, 2, 5]) == [(0, 3)]


@pytest.mark.parametrize("cantidades", [
    [2] * 500,                  # muchos grupos pequeños
    [12] * 200,                 # grupos de varias filas
    [3, 40, 2, 90, 2, 2, 7],    # mezcla
    [900, 2, 2],                # un grupo enorme y otros
])
def test_las_paginas_cubren_todos_los_grupos_sin_huecos(cantidades):
    paginas = repartir_en_paginas(cantidades)
    assert paginas[0][0] == 0 and paginas[-1][1] == len(cantidades)
    for (_, fin), (inicio, _) in zip(paginas, paginas[1:]):
        assert fin == inicio
    assert all(inicio < fin for inicio, fin in paginas)


@pytest.mark.parametrize("cantidades", [[2] * 500, [12] * 200, [3, 40, 2, 90, 2, 2, 7]])
def test_ninguna_pagina_se_acerca_al_limite_de_windows(cantidades):
    for inicio, fin in repartir_en_paginas(cantidades):
        assert fin - inicio <= GRUPOS_MAX_PAGINA
        assert sum(_alto(n) for n in cantidades[inicio:fin]) <= ALTO_MAX_PAGINA < LIMITE_WINDOWS


def test_un_grupo_enorme_ocupa_su_propia_pagina():
    assert repartir_en_paginas([900, 2, 2]) == [(0, 1), (1, 3)]


def test_el_caso_que_fallaba_ahora_se_reparte():
    """69 grupos de ~9 fotos medían unos 52.000 px de una sola vez."""
    assert sum(_alto(9) for _ in range(69)) > LIMITE_WINDOWS
    assert len(repartir_en_paginas([9] * 69)) > 1
