"""Configuración persistente mínima de la app.

Se guarda en %APPDATA%\\BuscadorDuplicados\\config.json (en Windows) o
en ~/.buscador_duplicados/config.json si no hay APPDATA. Solo librería
estándar. Todo falla en silencio: si no se puede leer/escribir, la app
funciona igual con los valores por defecto.
"""

import json
import os
from pathlib import Path
from typing import Any

from .registro import log

MODOS = ("sencillo", "avanzado")
MODO_POR_DEFECTO = "sencillo"

TEMAS = ("auto", "claro", "oscuro")   # auto = seguir al sistema
TEMA_POR_DEFECTO = "auto"


def _ruta() -> Path:
    base = os.environ.get("APPDATA")
    if base:
        return Path(base) / "BuscadorDuplicados" / "config.json"
    return Path.home() / ".buscador_duplicados" / "config.json"


def cargar() -> dict[str, Any]:
    try:
        datos = json.loads(_ruta().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    # Un JSON válido pero que no es un diccionario (p. ej. una lista) también se ignora.
    return datos if isinstance(datos, dict) else {}


def guardar(datos: dict[str, Any]) -> None:
    ruta = _ruta()
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(json.dumps(datos, indent=2, ensure_ascii=False),
                        encoding="utf-8")
    except OSError:
        log.warning("No se pudo guardar la configuración en %s", ruta, exc_info=True)


def get_modo() -> str:
    modo = cargar().get("modo")
    return modo if modo in MODOS else MODO_POR_DEFECTO


def set_modo(modo: str) -> None:
    if modo not in MODOS:
        return
    datos = cargar()
    datos["modo"] = modo
    guardar(datos)


def get_tema() -> str:
    tema = cargar().get("tema")
    return tema if tema in TEMAS else TEMA_POR_DEFECTO


def set_tema(tema: str) -> None:
    if tema not in TEMAS:
        return
    datos = cargar()
    datos["tema"] = tema
    guardar(datos)
