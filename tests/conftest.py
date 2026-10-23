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
_FILES = ("historial.json", "config.json")


def _fingerprint():
    state = {}
    for name in _FILES:
        f = _REAL / name
        state[name] = (f.stat().st_mtime_ns, f.stat().st_size) if f.exists() else None
    return state


@pytest.fixture(autouse=True, scope="session")
def real_data_untouched():
    before = _fingerprint()
    yield
    after = _fingerprint()
    assert before == after, (
        "Alguna prueba ha modificado los datos REALES de la app "
        f"({_REAL}). Deben usar un APPDATA temporal.")
