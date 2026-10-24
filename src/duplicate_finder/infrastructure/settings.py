"""The settings in a JSON file: the implementation of the `SettingsStore` port.

It is stored in %APPDATA%\\BuscadorDuplicados\\config.json (on Windows) or
in ~/.buscador_duplicados/config.json when there is no APPDATA. Standard
library only. Everything fails silently: if it cannot be read or written,
the app works the same with the default values.
"""

import json
import logging
import shutil
from pathlib import Path
from typing import Any

from duplicate_finder.infrastructure.data_folder import data_folder

log = logging.getLogger(__name__)

# Spanish keys and values written by version 1.0.
_LEGACY_KEYS = {"modo": "mode", "tema": "theme"}
_LEGACY_VALUES = {"sencillo": "simple", "avanzado": "advanced", "claro": "light", "oscuro": "dark"}


def _path() -> Path:
    return data_folder() / "config.json"


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
        if (
            isinstance(old, dict)
            and any(key in old for key in _LEGACY_KEYS)
            and not backup.exists()
        ):
            shutil.copy2(path, backup)
    except (OSError, ValueError):
        pass


class JsonSettingsStore:
    def load(self) -> dict[str, Any]:
        try:
            data = json.loads(_path().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        # A JSON that is valid but is not a dictionary (e.g. a list) is also ignored.
        return _upgrade(data) if isinstance(data, dict) else {}

    def save(self, data: dict[str, Any]) -> None:
        path = _path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            _backup_legacy(path)
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError:
            log.warning("Could not save the configuration to %s", path, exc_info=True)
