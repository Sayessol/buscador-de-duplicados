"""Red de seguridad común: las pruebas no deben tocar los datos reales del usuario.

Si una prueba escribe en el historial o en la configuración reales de la app
(en %APPDATA%\\BuscadorDuplicados), al terminar toda la sesión se da un error.
Antes pasaba sin que nadie se enterara; por eso existe esta comprobación.
"""

import os
from pathlib import Path

import pytest

_REAL = (Path(os.environ.get("APPDATA") or Path.home() / ".buscador_duplicados")
         / "BuscadorDuplicados")
_ARCHIVOS = ("historial.json", "config.json")


def _huella():
    estado = {}
    for nombre in _ARCHIVOS:
        f = _REAL / nombre
        estado[nombre] = (f.stat().st_mtime_ns, f.stat().st_size) if f.exists() else None
    return estado


@pytest.fixture(autouse=True, scope="session")
def datos_reales_intactos():
    antes = _huella()
    yield
    despues = _huella()
    assert antes == despues, (
        "Alguna prueba ha modificado los datos REALES de la app "
        f"({_REAL}). Deben usar un APPDATA temporal.")
