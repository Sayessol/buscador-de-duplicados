"""Where the app keeps its own files (settings, history, logs)."""

import os
from pathlib import Path


def data_folder() -> Path:
    """%APPDATA%\\BuscadorDuplicados on Windows, ~/.buscador_duplicados when there is no APPDATA."""
    base = os.environ.get("APPDATA")
    if base:
        return Path(base) / "BuscadorDuplicados"
    return Path.home() / ".buscador_duplicados"
