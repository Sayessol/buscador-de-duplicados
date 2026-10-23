"""Qué copia se conserva y cuáles se mueven, en cada grupo de duplicados.

La `DuplicateSelection` es el "estado editable" que hay entre el
resultado del escaneo (inmutable) y el paso de mover a cuarentena.

Regla que impone la app: al mover, cada grupo debe quedar con
**exactamente una** copia marcada como CONSERVAR. Mientras eso no se
cumpla en todos los grupos, no se puede mover nada.

Estado inicial: todo en CONSERVAR (es decir, no se movería nada). Así
la app nunca "propone mover" algo sin que el usuario lo decida, ya sea
a mano o aplicando la regla de carpeta preferida.
"""

import os
import re
from collections.abc import Sequence
from typing import Protocol

from .scanner import DuplicateFile

KEEP = "conservar"
MOVE = "mover"

# Nombres que "huelen" a copia y no al original.
_LOOKS_LIKE_COPY = re.compile(
    r"cop(?:y|ia)\b|duplicad|\bnew\b|\(\d+\)|[ _-]copy|[ _-]copia|[ _-]\d+$",
    re.IGNORECASE)

# Estados posibles de un grupo respecto de la regla "una sola copia".
GROUP_OK = "ok"                 # exactamente una copia en CONSERVAR
GROUP_NOTHING_KEPT = "sin_conservar"   # ninguna copia en CONSERVAR
GROUP_MULTIPLE = "multiple"     # dos o más copias en CONSERVAR (sin decidir)


def _is_inside(path: str, folder: str) -> bool:
    """True si `ruta` está dentro de `carpeta` (comparación normalizada)."""
    try:
        abs_path = os.path.normcase(os.path.abspath(path))
        abs_folder = os.path.normcase(os.path.abspath(folder))
    except (OSError, ValueError):
        return False
    if abs_folder.endswith(os.sep):
        abs_folder = abs_folder.rstrip(os.sep)
    return abs_path == abs_folder or abs_path.startswith(abs_folder + os.sep)


class _Group(Protocol):
    """Lo mínimo que se le pide a un grupo: una lista de archivos (los duplicados
    exactos y las fotos parecidas lo cumplen, por eso comparten esta clase)."""

    @property
    def files(self) -> list[DuplicateFile]: ...


class _Result(Protocol):
    """Lo mínimo que se le pide a un resultado: una lista de grupos."""

    @property
    def groups(self) -> Sequence[_Group]: ...


class DuplicateSelection:
    def __init__(self, result: _Result) -> None:
        self.result = result
        # _decision[(indice_grupo, ruta)] -> CONSERVAR | MOVER
        self._decision: dict[tuple[int, str], str] = {}
        for gi, group in enumerate(result.groups):
            for file in group.files:
                self._decision[(gi, file.path)] = KEEP

    # ------------------------------------------------------------------
    # Consultas y cambios sobre un archivo
    # ------------------------------------------------------------------
    def decision(self, group_index: int, path: str) -> str:
        return self._decision.get((group_index, path), KEEP)

    def mark(self, group_index: int, path: str, decision: str) -> None:
        assert decision in (KEEP, MOVE)
        if (group_index, path) in self._decision:
            self._decision[(group_index, path)] = decision

    def toggle(self, group_index: int, path: str) -> str:
        current = self.decision(group_index, path)
        new = MOVE if current == KEEP else KEEP
        self.mark(group_index, path, new)
        return new

    def keep_only(self, group_index: int, kept_path: str) -> None:
        """Marca `ruta_conservada` como CONSERVAR y el resto del grupo como MOVER."""
        group = self.result.groups[group_index]
        for file in group.files:
            self.mark(
                group_index, file.path,
                KEEP if file.path == kept_path else MOVE,
            )

    # ------------------------------------------------------------------
    # Regla automática por carpeta preferida
    # ------------------------------------------------------------------
    def apply_folder_rule(self, preferred_folder: str | None) -> tuple[int, int]:
        """Por cada grupo: si alguna copia está dentro de `carpeta_buena`,
        conserva esa (la de ruta más corta si hay varias) y marca el
        resto como MOVER. Si ninguna copia está dentro, el grupo se deja
        entero en CONSERVAR (queda "sin decidir" para que el usuario lo
        resuelva a mano).

        Devuelve (grupos_resueltos, grupos_sin_coincidencia).
        """
        preferred_folder = (preferred_folder or "").strip()
        resolved = 0
        no_match = 0

        for gi, group in enumerate(self.result.groups):
            inside = [a.path for a in group.files
                      if preferred_folder and _is_inside(a.path, preferred_folder)]
            if inside:
                kept = min(inside, key=len)
                self.keep_only(gi, kept)
                resolved += 1
            else:
                for a in group.files:
                    self.mark(gi, a.path, KEEP)
                no_match += 1

        return resolved, no_match

    # ------------------------------------------------------------------
    # Estado de los grupos y validación global
    # ------------------------------------------------------------------
    def _kept_in(self, group_index: int) -> list[DuplicateFile]:
        group = self.result.groups[group_index]
        return [a for a in group.files
                if self.decision(group_index, a.path) == KEEP]

    def group_state(self, group_index: int) -> str:
        n = len(self._kept_in(group_index))
        if n == 1:
            return GROUP_OK
        if n == 0:
            return GROUP_NOTHING_KEPT
        return GROUP_MULTIPLE

    def pending_groups(self) -> list[int]:
        return [gi for gi in range(len(self.result.groups))
                if self.group_state(gi) != GROUP_OK]

    def all_ready(self) -> bool:
        return not self.pending_groups()

    # ------------------------------------------------------------------
    # Resumen de lo que se movería
    # ------------------------------------------------------------------
    def files_to_move(self) -> list[tuple[int, DuplicateFile]]:
        """Lista de (indice_grupo, DuplicateFile) marcados como MOVER."""
        output: list[tuple[int, DuplicateFile]] = []
        for gi, group in enumerate(self.result.groups):
            for file in group.files:
                if self.decision(gi, file.path) == MOVE:
                    output.append((gi, file))
        return output

    def count_to_move(self) -> int:
        return len(self.files_to_move())

    def space_to_free(self) -> int:
        return sum(a.size for _gi, a in self.files_to_move())

    # ------------------------------------------------------------------
    # Preselección automática (modo Sencillo, o botón en Avanzado)
    # ------------------------------------------------------------------
    def preselect_primary(self) -> None:
        """En cada grupo, conserva la copia "principal" y marca el resto
        para mover.

        Principal = la que menos parece una copia por el nombre, luego la
        menos anidada, luego la más antigua, luego la de ruta más corta.
        """
        for gi, group in enumerate(self.result.groups):
            best = min(group.files, key=_primary_score)
            self.keep_only(gi, best.path)


def _primary_score(file: DuplicateFile) -> tuple[int, int, float, int]:
    """Puntuación para elegir la copia "principal": min() se queda con la
    tupla más pequeña, así que cada campo va de "mejor" (menor) a "peor".
    """
    path = file.path
    name = os.path.basename(path)
    looks_like_copy = 1 if _LOOKS_LIKE_COPY.search(name) else 0  # 0 = no parece copia
    depth = os.path.normpath(path).count(os.sep)        # menos anidada, mejor
    try:
        mtime = os.path.getmtime(path)                        # más antigua, mejor
    except OSError:
        mtime = float("inf")
    return (looks_like_copy, depth, mtime, len(path))      # ruta más corta desempata
