"""Reunir todas las imágenes de una carpeta en una carpeta común.

Dos estrategias:

* **por_archivos**: mueve/copia cada imagen a `destino/<misma subruta>`.
  Los archivos que no son imágenes se tratan según `NonImageRules`
  (dejarlos, moverlos igual, o agruparlos por tipo en una carpeta con el
  nombre que elija el usuario).

* **carpeta_entera**: mueve/copia la carpeta a analizar completa (con
  todo lo que hay dentro) a `destino/<nombre de la carpeta>/`.
"""

import os
import shutil
from dataclasses import dataclass, field

from .filters import CATEGORY_EXTENSIONS
from .callbacks import CancelledCallback, ProgressCallback
from .file_moves import (
    MOVE, COPY, Transfer, TransferResult, execute, write_log,
    validate_destination, collision_free_path, size,
)

# Extensiones que se consideran "imagen" (más amplio que lo que Pillow
# puede previsualizar: incluye raw, heic, etc.).
IMAGE_EXT = {e.lower() for e in CATEGORY_EXTENSIONS["Imágenes"]}

LEAVE = "dejar"
# (para no-imágenes: DEJAR | MOVER | "agrupar")
GROUP = "agrupar"


def _ext(path: str) -> str:
    return os.path.splitext(path)[1].lower().lstrip(".")


def list_all(root_folder: str, recursive: bool = True) -> tuple[list[str], list[str]]:
    """Devuelve (imagenes, no_imagenes): dos listas de rutas absolutas."""
    images: list[str] = []
    others: list[str] = []
    if recursive:
        for current_dir, _sub, names in os.walk(root_folder):
            for n in names:
                path = os.path.join(current_dir, n)
                (images if _ext(n) in IMAGE_EXT else others).append(path)
    else:
        for n in sorted(os.listdir(root_folder)):
            path = os.path.join(root_folder, n)
            if os.path.isfile(path):
                (images if _ext(n) in IMAGE_EXT else others).append(path)
    return sorted(images), sorted(others)


def non_image_kinds(others: list[str]) -> dict[str, list[str]]:
    """dict: extensión -> lista de rutas, para el diálogo por tipo."""
    d: dict[str, list[str]] = {}
    for path in others:
        d.setdefault(_ext(path) or "(sin extensión)", []).append(path)
    return dict(sorted(d.items()))


@dataclass
class NonImageRules:
    """Qué hacer con cada tipo de archivo que no es imagen.

    accion_por_ext: ext -> "dejar" | "mover" | "agrupar"
    carpeta_por_ext: ext -> nombre de carpeta (solo si "agrupar")
    """

    action_by_ext: dict[str, str] = field(default_factory=dict)
    folder_by_ext: dict[str, str] = field(default_factory=dict)

    def action(self, ext: str) -> str:
        return self.action_by_ext.get(ext, LEAVE)

    def folder(self, ext: str) -> str:
        return (self.folder_by_ext.get(ext) or ext).strip() or ext


def plan_by_files(
    images: list[str],
    others: list[str],
    root_folder: str,
    destination: str,
    rules: NonImageRules | None = None,
) -> list[Transfer]:
    """Lista de Traslado (sin ejecutar)."""
    rules = rules or NonImageRules()
    plan: list[Transfer] = []

    # Imágenes: siempre a destino/<misma subruta que tenían en el origen>.
    for path in images:
        rel = os.path.relpath(path, root_folder)   # p. ej. "vacaciones/playa.jpg"
        plan.append(Transfer(path, os.path.join(destination, rel), size(path)))

    # No imágenes: según lo que haya elegido el usuario para cada tipo.
    for path in others:
        ext = _ext(path) or "(sin extensión)"
        acc = rules.action(ext)
        if acc == LEAVE:
            continue                                # no se toca
        rel = os.path.relpath(path, root_folder)
        if acc == GROUP:
            # destino/<carpeta que nombró el usuario>/<subruta>
            final_destination = os.path.join(destination, rules.folder(ext), rel)
        else:  # "mover": igual que las imágenes
            final_destination = os.path.join(destination, rel)
        plan.append(Transfer(path, final_destination, size(path)))

    return plan


def gather_by_files(
    images: list[str],
    others: list[str],
    root_folder: str,
    destination: str,
    action: str = MOVE,
    rules: NonImageRules | None = None,
    progress: ProgressCallback | None = None,
    cancelled: CancelledCallback | None = None,
) -> TransferResult:
    validate_destination(destination, root_folder)
    os.makedirs(destination, exist_ok=True)
    plan = plan_by_files(images, others, root_folder, destination, rules)
    res = execute(plan, action=action, progress=progress, cancelled=cancelled)
    res.log_path = write_log(plan, destination, "reunir", root_folder, action)
    return res


def gather_whole_folder(
    root_folder: str, destination: str, action: str = MOVE,
    progress: ProgressCallback | None = None,
) -> TransferResult:
    """Mueve/copia la carpeta a analizar completa dentro del destino."""
    validate_destination(destination, root_folder)
    os.makedirs(destination, exist_ok=True)
    progress = progress or (lambda *_: None)

    name = os.path.basename(os.path.normpath(root_folder)) or "carpeta"
    final = collision_free_path(os.path.join(destination, name))
    verb = "Copiando" if action == COPY else "Moviendo"
    progress(0, 1, f"{verb} la carpeta «{name}»…")

    t = Transfer(root_folder, final, 0)
    try:
        if action == COPY:
            shutil.copytree(root_folder, final)
        else:
            shutil.move(root_folder, final)
        t.ok = True
    except (OSError, shutil.Error) as e:
        t.ok, t.error = False, str(e)

    progress(1, 1, "Listo.")
    res = TransferResult(transfers=[t], action=action)
    res.log_path = write_log([t], destination, "reunir_carpeta", root_folder,
                                action)
    return res
