"""The history of operations in a JSON file: the implementation of the `HistoryStore` port.

It is stored in %APPDATA%\\BuscadorDuplicados\\history.json (or in ~/.buscador_duplicados/
when there is no APPDATA). Standard library only.

Version 1.0 kept it in historial.json with Spanish keys and values. That file is still
read when history.json does not exist yet (converted on the fly) and is never modified,
so it stays as a backup.
"""

import json
import logging
from pathlib import Path
from typing import Any

from duplicate_finder.domain.operations import KIND_GATHER, KIND_GATHER_FOLDER, KIND_QUARANTINE
from duplicate_finder.infrastructure.data_folder import data_folder

log = logging.getLogger(__name__)

_MAX_OPERATIONS = 80

# Spanish keys and values written by version 1.0.
_LEGACY_KEYS = {"fecha": "date", "tipo": "kind", "accion": "action",
                "origen_raiz": "source_root", "destino": "destination",
                "descripcion": "description", "movimientos": "moves", "deshecha": "undone"}
_LEGACY_VALUES = {"cuarentena": KIND_QUARANTINE, "reunir": KIND_GATHER,
                  "reunir_carpeta": KIND_GATHER_FOLDER, "mover": "move", "copiar": "copy"}


def _path() -> Path:
    return data_folder() / "history.json"


def _legacy_path() -> Path:
    return data_folder() / "historial.json"


def _upgrade(op: Any) -> dict[str, Any] | None:
    """Converts an operation saved by version 1.0 to the current format.

    Operations already in the current format are returned as they are; anything that is
    not an operation (a malformed entry) gives None and is dropped.
    """
    if not isinstance(op, dict):
        return None
    if not any(key in op for key in _LEGACY_KEYS):
        return op
    new: dict[str, Any] = {
        _LEGACY_KEYS[key] if key in _LEGACY_KEYS else str(key): value
        for key, value in op.items()}
    for field in ("kind", "action"):
        value = new.get(field)
        if isinstance(value, str):
            new[field] = _LEGACY_VALUES.get(value, value)
    moves = new.get("moves")
    new["moves"] = [
        move if "source" in move
        else {"source": move.get("origen"), "destination": move.get("destino")}
        for move in (moves if isinstance(moves, list) else []) if isinstance(move, dict)]
    return new


def _read(path: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    return [op for op in map(_upgrade, data) if op is not None]


class JsonHistoryStore:
    def load(self) -> list[dict[str, Any]]:
        """The history in the current format; falls back to the version 1.0 file."""
        if _path().exists():
            return _read(_path())
        return _read(_legacy_path())

    def save(self, operations: list[dict[str, Any]]) -> None:
        path = _path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(operations[-_MAX_OPERATIONS:], indent=2, ensure_ascii=False),
                encoding="utf-8")
        except OSError:
            log.warning("Could not save the history to %s", path, exc_info=True)
