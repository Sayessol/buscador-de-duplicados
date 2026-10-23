"""Common safety net: the tests must not touch the user's real data.

If a test writes to the real history or configuration of the app
(in %APPDATA%\\BuscadorDuplicados), an error is raised at the end of the whole session.
This used to happen without anyone noticing; that is why this check exists.
"""

import os
import tempfile
from pathlib import Path

import pytest

_REAL = (Path(os.environ.get("APPDATA") or Path.home() / ".buscador_duplicados")
         / "BuscadorDuplicados")
_FILES = ("history.json", "historial.json", "config.json")

# The whole session works on a temporary data folder: the use cases record their own history, so
# no test may ever find (or leave something in) the real one.
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="dup_session_appdata_")


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
