"""Mover los duplicados descartados a una carpeta de cuarentena.

Reglas de seguridad (heredadas del script de consola):

* NUNCA se borra ni se sobrescribe nada. Solo se **mueve**.
* El original solo desaparece de su sitio cuando su copia ya está a
  salvo en la cuarentena (lo garantiza `shutil.move`).
* Se preserva la estructura de subcarpetas relativa a la carpeta
  escaneada, para poder devolver cada archivo a su lugar si hace falta.
* Si en el destino ya hay un archivo con ese nombre, el nuevo se guarda
  con un sufijo `(1)`, `(2)`... en vez de pisarlo.
* Al terminar se escribe un CSV de log con cada movimiento (origen,
  destino, estado), para poder deshacer a mano.
"""

import csv
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime

from .selection import DuplicateSelection
from .callbacks import CancelledCallback, ProgressCallback


@dataclass
class Move:
    group: int
    source: str
    destination: str
    size: int
    ok: bool = False
    error: str = ""


@dataclass
class QuarantineResult:
    moves: list[Move] = field(default_factory=list)
    log_path: str = ""

    @property
    def moved(self) -> list[Move]:
        return [m for m in self.moves if m.ok]

    @property
    def failed(self) -> list[Move]:
        return [m for m in self.moves if not m.ok]

    @property
    def bytes_moved(self) -> int:
        return sum(m.size for m in self.moved)


class InvalidQuarantine(Exception):
    """La carpeta de cuarentena elegida no sirve (p. ej. está dentro de
    la carpeta escaneada)."""


def _norm(p: str) -> str:
    return os.path.normcase(os.path.abspath(p))


def validate_quarantine_folder(quarantine_folder: str, root_folder: str) -> str | None:
    """Devuelve un mensaje de advertencia (str) o None si todo bien.

    Lanza InvalidQuarantine si la carpeta de cuarentena está dentro de
    la carpeta escaneada (provocaría que el próximo escaneo vuelva a
    encontrar los archivos ya movidos, o mover una carpeta dentro de sí
    misma).
    """
    cq = _norm(quarantine_folder)
    cr = _norm(root_folder)

    if cq == cr:
        raise InvalidQuarantine(
            "La carpeta de cuarentena no puede ser la misma que la carpeta escaneada.")
    if cq.startswith(cr + os.sep):
        raise InvalidQuarantine(
            "La carpeta de cuarentena está dentro de la carpeta escaneada. "
            "Elige una carpeta fuera de ella.")
    if cr.startswith(cq + os.sep):
        return ("Atención: la carpeta escaneada está dentro de la carpeta de "
                "cuarentena. Se puede continuar, pero revisa que sea lo que quieres.")
    return None


def _destination_for(source: str, root_folder: str, quarantine_folder: str) -> str:
    """Ruta destino preservando la estructura relativa a la carpeta escaneada."""
    try:
        rel = os.path.relpath(source, root_folder)
    except ValueError:
        rel = os.path.basename(source)
    if rel.startswith(".." + os.sep) or rel == "..":
        # El archivo está fuera de la carpeta escaneada: lo colgamos de
        # una subcarpeta "_fuera_de_la_carpeta" con su nombre.
        rel = os.path.join("_fuera_de_la_carpeta", os.path.basename(source))
    return os.path.join(quarantine_folder, rel)


def _avoid_collision(destination: str) -> str:
    """Si `destino` ya existe, devuelve 'nombre (1).ext', 'nombre (2).ext'..."""
    if not os.path.exists(destination):
        return destination
    base, ext = os.path.splitext(destination)
    i = 1
    while os.path.exists(f"{base} ({i}){ext}"):
        i += 1
    return f"{base} ({i}){ext}"


def plan_moves(
    selection: DuplicateSelection, root_folder: str, quarantine_folder: str,
) -> list[Move]:
    """Lista de Movimiento (sin ejecutar) para los archivos marcados como MOVER."""
    plan: list[Move] = []
    for gi, file in selection.files_to_move():
        destination = _destination_for(file.path, root_folder, quarantine_folder)
        plan.append(Move(
            group=gi + 1, source=file.path, destination=destination,
            size=file.size))
    return plan


def move_to_quarantine(
    selection: DuplicateSelection,
    root_folder: str,
    quarantine_folder: str,
    progress: ProgressCallback | None = None,
    cancelled: CancelledCallback | None = None,
) -> QuarantineResult:
    """Ejecuta el movimiento. Devuelve un QuarantineResult.

    progreso : callable(actual, total, mensaje) opcional.
    cancelado: callable() -> bool opcional. Si pasa a True, se deja de
               mover (lo ya movido queda movido) y se escribe el log
               igual.
    """
    if not selection.all_ready():
        raise ValueError(
            "Hay grupos sin resolver: cada grupo debe tener exactamente una "
            "copia marcada como conservar antes de mover.")

    validate_quarantine_folder(quarantine_folder, root_folder)

    progress = progress or (lambda *_: None)
    cancelled = cancelled or (lambda: False)

    plan = plan_moves(selection, root_folder, quarantine_folder)
    total = len(plan)
    os.makedirs(quarantine_folder, exist_ok=True)

    for i, move in enumerate(plan, start=1):
        if cancelled():
            break
        progress(i, total, f"Moviendo {i}/{total}: {os.path.basename(move.source)}")
        try:
            if not os.path.exists(move.source):
                raise FileNotFoundError("el archivo ya no está en su sitio")
            os.makedirs(os.path.dirname(move.destination), exist_ok=True)
            move.destination = _avoid_collision(move.destination)
            shutil.move(move.source, move.destination)
            move.ok = True
        except (OSError, shutil.Error) as e:
            move.ok = False
            move.error = str(e)

    result = QuarantineResult(moves=plan)
    result.log_path = _write_log(plan, quarantine_folder, root_folder)
    progress(total, total, "Listo.")
    return result


def _write_log(
    moves: list[Move], quarantine_folder: str, root_folder: str,
) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(quarantine_folder, f"_log_cuarentena_{stamp}.csv")
    try:
        os.makedirs(quarantine_folder, exist_ok=True)
        with open(log_path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["Fecha", "Carpeta_Escaneada", "Grupo", "Origen",
                        "Destino", "Tamano_Bytes", "Estado", "Error"])
            now = datetime.now().isoformat(timespec="seconds")
            for m in moves:
                w.writerow([
                    now, root_folder, m.group, m.source, m.destination,
                    m.size, "movido" if m.ok else "ERROR", m.error,
                ])
        return log_path
    except OSError:
        return ""
