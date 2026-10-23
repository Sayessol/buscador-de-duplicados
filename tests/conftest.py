"""Common safety net: the tests must not touch the user's real data.

If a test writes to the real history or configuration of the app
(in %APPDATA%\\BuscadorDuplicados), an error is raised at the end of the whole session.
This used to happen without anyone noticing; that is why this check exists.
"""

import os
from pathlib import Path

import pytest

_REAL = (Path(os.environ.get("APPDATA") or Path.home() / ".buscador_duplicados")
         / "BuscadorDuplicados")
_FILES = ("history.json", "historial.json", "config.json")


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
