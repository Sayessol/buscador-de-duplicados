"""Minimal persistent configuration of the app.

It is stored in %APPDATA%\\BuscadorDuplicados\\config.json (on Windows) or
in ~/.buscador_duplicados/config.json when there is no APPDATA. Standard
library only. Everything fails silently: if it cannot be read or written,
the app works the same with the default values.
"""

import json
import os
from pathlib import Path
from typing import Any

from .app_logging import log

MODES = ("sencillo", "avanzado")
DEFAULT_MODE = "sencillo"

THEMES = ("auto", "claro", "oscuro")   # auto = follow the system
DEFAULT_THEME = "auto"


def _path() -> Path:
    base = os.environ.get("APPDATA")
    if base:
        return Path(base) / "BuscadorDuplicados" / "config.json"
    return Path.home() / ".buscador_duplicados" / "config.json"


def load() -> dict[str, Any]:
    try:
        data = json.loads(_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    # A JSON that is valid but is not a dictionary (e.g. a list) is also ignored.
    return data if isinstance(data, dict) else {}


def save(data: dict[str, Any]) -> None:
    path = _path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                        encoding="utf-8")
    except OSError:
        log.warning("No se pudo guardar la configuración en %s", path, exc_info=True)


def get_mode() -> str:
    mode = load().get("modo")
    return mode if mode in MODES else DEFAULT_MODE


def set_mode(mode: str) -> None:
    if mode not in MODES:
        return
    data = load()
    data["modo"] = mode
    save(data)


def get_theme() -> str:
    theme = load().get("tema")
    return theme if theme in THEMES else DEFAULT_THEME


def set_theme(theme: str) -> None:
    if theme not in THEMES:
        return
    data = load()
    data["tema"] = theme
    save(data)
