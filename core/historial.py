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
from datetime import datetime
from pathlib import Path
from typing import Any

from .registro import log
from .tipos import FuncProgreso

_MAX_OPERACIONES = 80

TIPO_CUARENTENA = "cuarentena"
TIPO_REUNIR = "reunir"
TIPO_REUNIR_CARPETA = "reunir_carpeta"


def _ruta() -> Path:
    base = os.environ.get("APPDATA")
    if base:
        return Path(base) / "BuscadorDuplicados" / "historial.json"
    return Path.home() / ".buscador_duplicados" / "historial.json"


def _cargar() -> list[dict[str, Any]]:
    try:
        datos = json.loads(_ruta().read_text(encoding="utf-8"))
        return datos if isinstance(datos, list) else []
    except (OSError, ValueError):
        return []


def _guardar(lista: list[dict[str, Any]]) -> None:
    ruta = _ruta()
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(
            json.dumps(lista[-_MAX_OPERACIONES:], indent=2, ensure_ascii=False),
            encoding="utf-8")
    except OSError:
        log.warning("No se pudo guardar el historial en %s", ruta, exc_info=True)


def registrar(
    tipo: str,
    accion: str,
    origen_raiz: str,
    destino: str,
    movimientos: list[tuple[str, str]],
    descripcion: str = "",
) -> str:
    """`movimientos`: lista de (origen, destino) ya ejecutados con éxito.

    Devuelve el id de la operación registrada.
    """
    lista = _cargar()
    ahora = datetime.now()
    op: dict[str, Any] = {
        "id": ahora.strftime("%Y%m%d%H%M%S%f"),
        "fecha": ahora.isoformat(timespec="seconds"),
        "tipo": tipo,
        "accion": accion,          # "mover" | "copiar"
        "origen_raiz": origen_raiz,
        "destino": destino,
        "descripcion": descripcion,
        "movimientos": [{"origen": o, "destino": d} for o, d in movimientos],
        "deshecha": False,
    }
    lista.append(op)
    _guardar(lista)
    return str(op["id"])


def listar() -> list[dict[str, Any]]:
    """Operaciones, de la más reciente a la más antigua."""
    return list(reversed(_cargar()))


def _marcar_deshecha(op_id: str) -> None:
    lista = _cargar()
    for op in lista:
        if op["id"] == op_id:
            op["deshecha"] = True
    _guardar(lista)


def deshacer(op_id: str, progreso: FuncProgreso | None = None) -> dict[str, Any]:
    """Revierte la operación `op_id`.

    Devuelve dict: {"ok": n_revertidos, "fallos": [(ruta, mensaje), ...],
    "op": operacion}. Marca la operación como deshecha si no hubo fallos.
    """
    progreso = progreso or (lambda *_: None)
    op = next((o for o in _cargar() if o["id"] == op_id), None)
    if op is None:
        return {"ok": 0, "fallos": [("", "operación no encontrada")], "op": None}
    if op.get("deshecha"):
        return {"ok": 0, "fallos": [("", "esta operación ya se deshizo")], "op": op}

    movs = op["movimientos"]        # cada uno: {"origen": ..., "destino": ...}
    total = len(movs)
    ok = 0
    fallos: list[tuple[str, str]] = []

    for i, m in enumerate(movs, start=1):
        origen, destino = m["origen"], m["destino"]
        progreso(i, total, os.path.basename(destino) or destino)
        try:
            if op["accion"] == "copiar":
                # Deshacer una copia = borrar lo que la app copió en el
                # destino. El original nunca se toca.
                if os.path.isdir(destino):
                    shutil.rmtree(destino)
                elif os.path.exists(destino):
                    os.remove(destino)
                ok += 1
            else:  # "mover" -> llevar el archivo de vuelta a su origen
                if not os.path.exists(destino):
                    raise FileNotFoundError("ya no está en el destino")
                if os.path.exists(origen):
                    # alguien ha vuelto a poner algo ahí: no lo pisamos
                    raise FileExistsError("ya hay algo en la ruta original")
                os.makedirs(os.path.dirname(origen), exist_ok=True)
                shutil.move(destino, origen)
                ok += 1
        except OSError as e:
            fallos.append((destino, str(e)))

    # Solo se marca "deshecha" si TODO se pudo revertir; si no, se puede
    # reintentar más tarde (los que ya volvieron no se moverán dos veces
    # porque su destino ya no existe).
    if not fallos:
        _marcar_deshecha(op_id)
    return {"ok": ok, "fallos": fallos, "op": op}
