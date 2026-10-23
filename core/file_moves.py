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

from .callbacks import CancelledCallback, ProgressCallback

MOVE = "mover"
COPY = "copiar"


class InvalidDestination(Exception):
    """El destino elegido no sirve (p. ej. está dentro del origen)."""


def _norm(p: str) -> str:
    return os.path.normcase(os.path.abspath(p))


def validate_destination(destination: str, source: str) -> str | None:
    """None si todo bien, un str de aviso si conviene avisar, o lanza
    InvalidDestination si no se puede continuar."""
    d, o = _norm(destination), _norm(source)
    if d == o:
        raise InvalidDestination(
            "El destino no puede ser la misma carpeta que el origen.")
    if d.startswith(o + os.sep):
        raise InvalidDestination(
            "El destino está dentro de la carpeta de origen. "
            "Elige una carpeta fuera de ella.")
    if o.startswith(d + os.sep):
        return ("Atención: la carpeta de origen está dentro del destino. "
                "Se puede continuar, pero revisa que sea lo que quieres.")
    return None


def collision_free_path(destination: str) -> str:
    """Si `destino` ya existe -> 'nombre (1).ext', 'nombre (2).ext'..."""
    if not os.path.exists(destination):
        return destination
    base, ext = os.path.splitext(destination)
    i = 1
    while os.path.exists(f"{base} ({i}){ext}"):
        i += 1
    return f"{base} ({i}){ext}"


def size(path: str) -> int:
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


@dataclass
class Transfer:
    source: str
    destination: str
    size: int = 0
    ok: bool = False
    error: str = ""


@dataclass
class TransferResult:
    transfers: list[Transfer] = field(default_factory=list)
    action: str = MOVE
    log_path: str = ""

    @property
    def done(self) -> list[Transfer]:
        return [t for t in self.transfers if t.ok]

    @property
    def failed(self) -> list[Transfer]:
        return [t for t in self.transfers if not t.ok]

    @property
    def bytes_done(self) -> int:
        return sum(t.size for t in self.done)


def execute(
    transfers: list[Transfer],
    action: str = MOVE,
    progress: ProgressCallback | None = None,
    cancelled: CancelledCallback | None = None,
) -> TransferResult:
    """Ejecuta una lista de Traslado (mueve o copia cada archivo)."""
    progress = progress or (lambda *_: None)
    cancelled = cancelled or (lambda: False)
    total = len(transfers)
    verb = "Copiando" if action == COPY else "Moviendo"

    for i, t in enumerate(transfers, start=1):
        if cancelled():
            break
        progress(i, total, f"{verb} {i}/{total}: {os.path.basename(t.source)}")
        try:
            if not os.path.exists(t.source):
                raise FileNotFoundError("el archivo ya no está en su sitio")
            os.makedirs(os.path.dirname(t.destination), exist_ok=True)
            t.destination = collision_free_path(t.destination)
            if action == COPY:
                shutil.copy2(t.source, t.destination)
            else:
                shutil.move(t.source, t.destination)
            t.ok = True
        except (OSError, shutil.Error) as e:
            t.ok, t.error = False, str(e)

    progress(total, total, "Listo.")
    return TransferResult(transfers=transfers, action=action)


def write_log(
    transfers: list[Transfer], destination_folder: str, prefix: str, root_source: str, action: str,
) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(destination_folder, f"_log_{prefix}_{stamp}.csv")
    try:
        os.makedirs(destination_folder, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["Fecha", "Accion", "Origen_Raiz", "Origen", "Destino",
                        "Tamano_Bytes", "Estado", "Error"])
            now = datetime.now().isoformat(timespec="seconds")
            for t in transfers:
                w.writerow([now, action, root_source, t.source, t.destination,
                            t.size, "hecho" if t.ok else "ERROR", t.error])
        return path
    except OSError:
        return ""
