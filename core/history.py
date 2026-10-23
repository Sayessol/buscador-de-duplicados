"""Historial persistente de operaciones que mueven o copian archivos
(mover a cuarentena, reunir imágenes), con posibilidad de deshacer.

Se guarda en %APPDATA%\\BuscadorDuplicados\\historial.json (o en
~/.buscador_duplicados/ si no hay APPDATA). Solo librería estándar.

Deshacer:
* "mover"  -> devuelve cada archivo/carpeta del destino a su origen.
* "copiar" -> BORRA las copias del destino. Es el ÚNICO sitio donde la
  app borra algo, y solo archivos que ella misma creó; el que llama debe
  pedir confirmación explícita antes.
"""

import json
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from .app_logging import log
from .callbacks import ProgressCallback

_MAX_OPERATIONS = 80

# Windows (antivirus, indexer) can lock a freshly created file for a moment, and
# `os.remove` then fails with PermissionError: retry for a few tenths of a second.
_REMOVE_ATTEMPTS = 5
_REMOVE_DELAY = 0.1     # seconds, growing with each attempt (0.1 + 0.2 + 0.3 + 0.4)

KIND_QUARANTINE = "cuarentena"
KIND_GATHER = "reunir"
KIND_GATHER_FOLDER = "reunir_carpeta"


def _path() -> Path:
    base = os.environ.get("APPDATA")
    if base:
        return Path(base) / "BuscadorDuplicados" / "historial.json"
    return Path.home() / ".buscador_duplicados" / "historial.json"


def _load() -> list[dict[str, Any]]:
    try:
        data = json.loads(_path().read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def _save(items: list[dict[str, Any]]) -> None:
    path = _path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(items[-_MAX_OPERATIONS:], indent=2, ensure_ascii=False),
            encoding="utf-8")
    except OSError:
        log.warning("No se pudo guardar el historial en %s", path, exc_info=True)


def record(
    kind: str,
    action: str,
    root_source: str,
    destination: str,
    moves: list[tuple[str, str]],
    description: str = "",
) -> str:
    """`movimientos`: lista de (origen, destino) ya ejecutados con éxito.

    Devuelve el id de la operación registrada.
    """
    items = _load()
    now = datetime.now()
    op: dict[str, Any] = {
        "id": now.strftime("%Y%m%d%H%M%S%f"),
        "fecha": now.isoformat(timespec="seconds"),
        "tipo": kind,
        "accion": action,          # "mover" | "copiar"
        "origen_raiz": root_source,
        "destino": destination,
        "descripcion": description,
        "movimientos": [{"origen": o, "destino": d} for o, d in moves],
        "deshecha": False,
    }
    items.append(op)
    _save(items)
    return str(op["id"])


def list_all() -> list[dict[str, Any]]:
    """Operaciones, de la más reciente a la más antigua."""
    return list(reversed(_load()))


def _mark_undone(op_id: str) -> None:
    items = _load()
    for op in items:
        if op["id"] == op_id:
            op["deshecha"] = True
    _save(items)


def _remove_with_retries(path: str) -> None:
    """Delete a file or folder, retrying briefly if Windows reports it as in use.

    If it is still locked after the last attempt, the PermissionError (an OSError) is
    raised again and the caller records it as a failure, like any other undo error.
    """
    for attempt in range(1, _REMOVE_ATTEMPTS + 1):
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            elif os.path.exists(path):
                os.remove(path)
            return
        except PermissionError:
            if attempt == _REMOVE_ATTEMPTS:
                raise
            time.sleep(_REMOVE_DELAY * attempt)


def undo(op_id: str, progress: ProgressCallback | None = None) -> dict[str, Any]:
    """Revierte la operación `op_id`.

    Devuelve dict: {"ok": n_revertidos, "fallos": [(ruta, mensaje), ...],
    "op": operacion}. Marca la operación como deshecha si no hubo fallos.
    """
    progress = progress or (lambda *_: None)
    op = next((o for o in _load() if o["id"] == op_id), None)
    if op is None:
        return {"ok": 0, "fallos": [("", "operación no encontrada")], "op": None}
    if op.get("deshecha"):
        return {"ok": 0, "fallos": [("", "esta operación ya se deshizo")], "op": op}

    op_moves = op["movimientos"]        # cada uno: {"origen": ..., "destino": ...}
    total = len(op_moves)
    ok = 0
    failures: list[tuple[str, str]] = []

    for i, m in enumerate(op_moves, start=1):
        source, destination = m["origen"], m["destino"]
        progress(i, total, os.path.basename(destination) or destination)
        try:
            if op["accion"] == "copiar":
                # Deshacer una copia = borrar lo que la app copió en el
                # destino. El original nunca se toca.
                _remove_with_retries(destination)
                ok += 1
            else:  # "mover" -> llevar el archivo de vuelta a su origen
                if not os.path.exists(destination):
                    raise FileNotFoundError("ya no está en el destino")
                if os.path.exists(source):
                    # alguien ha vuelto a poner algo ahí: no lo pisamos
                    raise FileExistsError("ya hay algo en la ruta original")
                os.makedirs(os.path.dirname(source), exist_ok=True)
                shutil.move(destination, source)
                ok += 1
        except OSError as e:
            failures.append((destination, str(e)))

    # Solo se marca "deshecha" si TODO se pudo revertir; si no, se puede
    # reintentar más tarde (los que ya volvieron no se moverán dos veces
    # porque su destino ya no existe).
    if not failures:
        _mark_undone(op_id)
    return {"ok": ok, "fallos": failures, "op": op}
