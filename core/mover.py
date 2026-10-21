"""Primitivas para mover o copiar lotes de archivos.

Reglas comunes:
* NUNCA se pisa un archivo del destino: si ya existe, el nuevo se guarda
  con sufijo `(1)`, `(2)`...
* El destino no puede estar dentro de la carpeta de origen.
* Se puede **mover** (quita del origen) o **copiar** (deja el original).
* Se escribe un CSV de registro.

Lo usa la pestaña "Reunir imágenes". La cuarentena tiene su propia
implementación (`core/quarantine.py`) con estas mismas reglas.
"""

import csv
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime

from .tipos import FuncCancelado, FuncProgreso

MOVER = "mover"
COPIAR = "copiar"


class DestinoInvalido(Exception):
    """El destino elegido no sirve (p. ej. está dentro del origen)."""


def _norm(p: str) -> str:
    return os.path.normcase(os.path.abspath(p))


def validar_destino(destino: str, origen: str) -> str | None:
    """None si todo bien, un str de aviso si conviene avisar, o lanza
    DestinoInvalido si no se puede continuar."""
    d, o = _norm(destino), _norm(origen)
    if d == o:
        raise DestinoInvalido(
            "El destino no puede ser la misma carpeta que el origen.")
    if d.startswith(o + os.sep):
        raise DestinoInvalido(
            "El destino está dentro de la carpeta de origen. "
            "Elige una carpeta fuera de ella.")
    if o.startswith(d + os.sep):
        return ("Atención: la carpeta de origen está dentro del destino. "
                "Se puede continuar, pero revisa que sea lo que quieres.")
    return None


def ruta_sin_colision(destino: str) -> str:
    """Si `destino` ya existe -> 'nombre (1).ext', 'nombre (2).ext'..."""
    if not os.path.exists(destino):
        return destino
    base, ext = os.path.splitext(destino)
    i = 1
    while os.path.exists(f"{base} ({i}){ext}"):
        i += 1
    return f"{base} ({i}){ext}"


def tamano(ruta: str) -> int:
    try:
        return os.path.getsize(ruta)
    except OSError:
        return 0


@dataclass
class Traslado:
    origen: str
    destino: str
    tamano: int = 0
    ok: bool = False
    error: str = ""


@dataclass
class ResultadoTraslado:
    traslados: list[Traslado] = field(default_factory=list)
    accion: str = MOVER
    ruta_log: str = ""

    @property
    def hechos(self) -> list[Traslado]:
        return [t for t in self.traslados if t.ok]

    @property
    def fallidos(self) -> list[Traslado]:
        return [t for t in self.traslados if not t.ok]

    @property
    def bytes_hechos(self) -> int:
        return sum(t.tamano for t in self.hechos)


def ejecutar(
    traslados: list[Traslado],
    accion: str = MOVER,
    progreso: FuncProgreso | None = None,
    cancelado: FuncCancelado | None = None,
) -> ResultadoTraslado:
    """Ejecuta una lista de Traslado (mueve o copia cada archivo)."""
    progreso = progreso or (lambda *_: None)
    cancelado = cancelado or (lambda: False)
    total = len(traslados)
    verbo = "Copiando" if accion == COPIAR else "Moviendo"

    for i, t in enumerate(traslados, start=1):
        if cancelado():
            break
        progreso(i, total, f"{verbo} {i}/{total}: {os.path.basename(t.origen)}")
        try:
            if not os.path.exists(t.origen):
                raise FileNotFoundError("el archivo ya no está en su sitio")
            os.makedirs(os.path.dirname(t.destino), exist_ok=True)
            t.destino = ruta_sin_colision(t.destino)
            if accion == COPIAR:
                shutil.copy2(t.origen, t.destino)
            else:
                shutil.move(t.origen, t.destino)
            t.ok = True
        except (OSError, shutil.Error) as e:
            t.ok, t.error = False, str(e)

    progreso(total, total, "Listo.")
    return ResultadoTraslado(traslados=traslados, accion=accion)


def escribir_log(
    traslados: list[Traslado], carpeta_destino: str, prefijo: str, origen_raiz: str, accion: str,
) -> str:
    sello = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta = os.path.join(carpeta_destino, f"_log_{prefijo}_{sello}.csv")
    try:
        os.makedirs(carpeta_destino, exist_ok=True)
        with open(ruta, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["Fecha", "Accion", "Origen_Raiz", "Origen", "Destino",
                        "Tamano_Bytes", "Estado", "Error"])
            ahora = datetime.now().isoformat(timespec="seconds")
            for t in traslados:
                w.writerow([ahora, accion, origen_raiz, t.origen, t.destino,
                            t.tamano, "hecho" if t.ok else "ERROR", t.error])
        return ruta
    except OSError:
        return ""
