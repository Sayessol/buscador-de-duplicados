"""Minimal persistent configuration of the app.

It is stored in %APPDATA%\\BuscadorDuplicados\\config.json (on Windows) or
in ~/.buscador_duplicados/config.json when there is no APPDATA. Standard
library only. Everything fails silently: if it cannot be read or written,
the app works the same with the default values.
"""

import json
import os
import shutil
from pathlib import Path
from typing import Any

from . import i18n
from .app_logging import log

LANGUAGE_AUTO = "auto"    # nothing chosen yet: follow the language of the system

MODES = ("simple", "advanced")
DEFAULT_MODE = "simple"

THEMES = ("auto", "light", "dark")   # auto = follow the system
DEFAULT_THEME = "auto"

# Spanish keys and values written by version 1.0.
_LEGACY_KEYS = {"modo": "mode", "tema": "theme"}
_LEGACY_VALUES = {"sencillo": "simple", "avanzado": "advanced", "claro": "light", "oscuro": "dark"}


def _path() -> Path:
    base = os.environ.get("APPDATA")
    if base:
        return Path(base) / "BuscadorDuplicados" / "config.json"
    return Path.home() / ".buscador_duplicados" / "config.json"


def _upgrade(data: dict[str, Any]) -> dict[str, Any]:
    """Converts the keys and values saved by version 1.0 to the current ones."""
    new = dict(data)
    for old_key, key in _LEGACY_KEYS.items():
        if old_key in new:
            value = new.pop(old_key)
            new.setdefault(key, _LEGACY_VALUES.get(value, value))
    return new


def _backup_legacy(path: Path) -> None:
    """Before the first rewrite of a version 1.0 file, keeps a copy of it next to it."""
    backup = path.with_name(path.name + ".bak-1.0")
    try:
        old = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(old, dict) and any(key in old for key in _LEGACY_KEYS) \
                and not backup.exists():
            shutil.copy2(path, backup)
    except (OSError, ValueError):
        pass


def load() -> dict[str, Any]:
    try:
        data = json.loads(_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    # A JSON that is valid but is not a dictionary (e.g. a list) is also ignored.
    return _upgrade(data) if isinstance(data, dict) else {}


def save(data: dict[str, Any]) -> None:
    path = _path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        _backup_legacy(path)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                        encoding="utf-8")
    except OSError:
        log.warning("Could not save the configuration to %s", path, exc_info=True)


def get_mode() -> str:
    mode = load().get("mode")
    return mode if mode in MODES else DEFAULT_MODE


def set_mode(mode: str) -> None:
    if mode not in MODES:
        return
    data = load()
    data["mode"] = mode
    save(data)


def get_theme() -> str:
    theme = load().get("theme")
    return theme if theme in THEMES else DEFAULT_THEME


def set_theme(theme: str) -> None:
    if theme not in THEMES:
        return
    data = load()
    data["theme"] = theme
    save(data)


def get_language() -> str:
    """The saved language ("en" | "es"), or "auto" when none was chosen yet."""
    language = load().get("language")
    return language if language in i18n.LANGUAGES else LANGUAGE_AUTO


def set_language(language: str) -> None:
    if language not in i18n.LANGUAGES:
        return
    data = load()
    data["language"] = language
    save(data)
