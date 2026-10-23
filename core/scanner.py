"""Escaneo recursivo de una carpeta en busca de archivos duplicados.

Este módulo SOLO LEE el sistema de archivos. No mueve, renombra ni
borra nada.

El escaneo va en pasadas, de lo más barato a lo más caro:

  Pasada 1  -  agrupar todos los archivos por tamaño en bytes.
               Un archivo con un tamaño único no puede tener duplicados,
               así que se descarta sin leer su contenido.

  Pasada 2  -  para los que comparten tamaño, calcular el hash de los
               primeros 64 KB (hash parcial). Rápido y descarta casi
               todos los falsos positivos.

  Pasada 3  -  para los que además comparten hash parcial, calcular el
               hash del archivo completo. Los que aquí coinciden son
               duplicados reales byte a byte.

El resultado es una lista de `DuplicateGroup`, cada uno con 2 o más
archivos de contenido idéntico.
"""

import os
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field

from .hashing import partial_hash, full_hash, PARTIAL_HASH_SIZE
from .filters import ScanFilter


class ScanCancelled(Exception):
    """Se lanza cuando el que llama pide cancelar el escaneo a mitad."""


@dataclass
class DuplicateFile:
    """Un archivo concreto dentro de un grupo de duplicados."""

    path: str
    size: int


@dataclass
class DuplicateGroup:
    """Conjunto de 2+ archivos con contenido idéntico."""

    hash: str          # el hash que comparten (identifica el grupo)
    size: int        # bytes de cada copia (todas pesan lo mismo)
    files: list[DuplicateFile]   # las copias del grupo

    @property
    def count(self) -> int:
        return len(self.files)

    @property
    def reclaimable_space(self) -> int:
        """Bytes que se liberarían si se conservara solo una copia."""
        return self.size * (len(self.files) - 1)


@dataclass
class ScanResult:
    """Todo lo que produjo un escaneo."""

    groups: list[DuplicateGroup]
    total_files: int
    errors: list[tuple[str, str]] = field(default_factory=list)  # (ruta, mensaje)
    total_excluded: int = 0  # archivos saltados por el filtro

    @property
    def total_groups(self) -> int:
        return len(self.groups)

    def summary_by_extension(self) -> list[tuple[str, int, int]]:
        """Desglose de los archivos duplicados por extensión.

        Devuelve una lista de tuplas (extension, cantidad, bytes),
        ordenada de mayor a menor espacio ocupado. Útil para que el
        usuario decida qué tipos agregar al filtro de exclusión.
        """
        # acc[extension] = [cantidad, bytes_totales]
        acc: defaultdict[str, list[int]] = defaultdict(lambda: [0, 0])
        for g in self.groups:
            for a in g.files:
                ext = os.path.splitext(a.path)[1].lower().lstrip(".")
                key = ext if ext else "(sin extensión)"
                acc[key][0] += 1
                acc[key][1] += a.size
        rows = [(ext, c, b) for ext, (c, b) in acc.items()]
        rows.sort(key=lambda f: (-f[2], f[0]))   # más bytes primero; a igualdad, alfabético
        return rows

    @property
    def total_files_duplicates(self) -> int:
        """Cantidad de archivos que están en algún grupo de duplicados."""
        return sum(g.count for g in self.groups)

    @property
    def extra_copies(self) -> int:
        """Archivos que se podrían mover (todas las copias menos una por grupo)."""
        return sum(g.count - 1 for g in self.groups)

    @property
    def total_reclaimable_space(self) -> int:
        return sum(g.reclaimable_space for g in self.groups)


@dataclass
class Progress:
    """Notificación de avance para que la interfaz muestre una barra.

    fase:
      "tamanos"        -> Pasada 1, contando y midiendo archivos.
      "hash_parcial"   -> Pasada 2, hasheando los primeros 64 KB.
      "hash_completo"  -> Pasada 3, hasheando archivos completos.
    total == 0 significa "todavía no sé cuántos hay en total" (Pasada 1).
    """

    phase: str
    current: int
    total: int
    message: str


def _noop(*_args: object, **_kwargs: object) -> None:
    return None


def _never_cancel() -> bool:
    return False


def _size_pass(
    root_folder: str,
    filter: ScanFilter,
    progress: Callable[[Progress], None],
    cancelled: Callable[[], bool],
    errors: list[tuple[str, str]],
) -> tuple[dict[int, list[str]], int, int]:
    """Pasada 1: recorre el árbol y agrupa los archivos por tamaño en bytes.

    Devuelve (rutas_por_tamano, total_archivos, total_excluidos). Los archivos
    que el filtro excluye ni se miden ni cuentan como revisados.
    """
    by_size: defaultdict[int, list[str]] = defaultdict(list)
    total_files = 0
    total_excluded = 0

    for current_dir, subdirs, names in os.walk(root_folder):
        if cancelled():
            raise ScanCancelled()

        # Podar carpetas excluidas: os.walk no entra en las que quitamos aquí.
        subdirs[:] = [d for d in subdirs if not filter.excludes_folder(d)]

        for name in names:
            if filter.excludes_name(name):
                total_excluded += 1
                continue

            path = os.path.join(current_dir, name)
            try:
                if not os.path.isfile(path):
                    # enlaces simbólicos rotos, dispositivos, etc.
                    continue
                size = os.path.getsize(path)
            except OSError as e:
                errors.append((path, str(e)))
                continue

            if filter.excludes_size(size):
                total_excluded += 1
                continue

            total_files += 1
            by_size[size].append(path)

            if total_files % 200 == 0:
                progress(Progress(
                    "tamanos", total_files, 0,
                    f"Paso 1/2: revisando tamaños... ({total_files} archivos)",
                ))

    return by_size, total_files, total_excluded


def _partial_hash_pass(
    candidates_by_size: dict[int, list[str]],
    progress: Callable[[Progress], None],
    cancelled: Callable[[], bool],
    errors: list[tuple[str, str]],
) -> dict[tuple[int, str], list[str]]:
    """Pasada 2: hash de los primeros 64 KB de los archivos que comparten tamaño.

    Devuelve solo los «finalistas»: las claves (tamaño, hash_parcial) que
    comparten 2 o más archivos.
    """
    total_candidates = sum(len(r) for r in candidates_by_size.values())
    by_partial: defaultdict[tuple[int, str], list[str]] = defaultdict(list)
    processed = 0

    for size, paths in candidates_by_size.items():
        for path in paths:
            if cancelled():
                raise ScanCancelled()
            processed += 1
            try:
                hp = partial_hash(path)
            except OSError as e:
                errors.append((path, str(e)))
                continue
            # La clave incluye el tamaño: dos archivos con el mismo hash
            # parcial pero distinto tamaño nunca son el mismo archivo.
            by_partial[(size, hp)].append(path)

            if processed % 50 == 0:
                progress(Progress(
                    "hash_parcial", processed, total_candidates,
                    f"Paso 2/2: calculando hashes... "
                    f"({processed}/{total_candidates})",
                ))

    return {key: paths for key, paths in by_partial.items() if len(paths) > 1}


def _full_hash_pass(
    finalists: dict[tuple[int, str], list[str]],
    progress: Callable[[Progress], None],
    cancelled: Callable[[], bool],
    errors: list[tuple[str, str]],
) -> list[DuplicateGroup]:
    """Pasada 3: hash del archivo entero de los finalistas.

    Los que coinciden aquí son duplicados reales, byte a byte. Si un archivo
    pesa menos de 64 KB, su hash parcial ya cubrió todo el contenido y esta
    pasada se salta para él.
    """
    total_finalists = sum(len(r) for r in finalists.values())
    groups: list[DuplicateGroup] = []
    full_processed = 0

    for (size, hp), paths in finalists.items():
        if size <= PARTIAL_HASH_SIZE:
            # El hash parcial ya cubrió el archivo entero: son idénticos.
            groups.append(DuplicateGroup(
                hash=hp,
                size=size,
                files=[DuplicateFile(r, size) for r in paths],
            ))
            continue

        by_full: defaultdict[str, list[str]] = defaultdict(list)
        for path in paths:
            if cancelled():
                raise ScanCancelled()
            full_processed += 1
            try:
                hc = full_hash(path)
            except OSError as e:
                errors.append((path, str(e)))
                continue
            by_full[hc].append(path)

            if full_processed % 50 == 0:
                progress(Progress(
                    "hash_completo", full_processed, total_finalists,
                    f"Paso 2/2: verificando archivos completos... "
                    f"({full_processed}/{total_finalists})",
                ))

        for hc, equal_paths in by_full.items():
            if len(equal_paths) > 1:
                groups.append(DuplicateGroup(
                    hash=hc,
                    size=size,
                    files=[DuplicateFile(r, size) for r in equal_paths],
                ))

    return groups


def scan(
    root_folder: str,
    progress: Callable[[Progress], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
    filter: ScanFilter | None = None,
) -> ScanResult:
    """Escanea `carpeta_raiz` recursivamente y devuelve un ScanResult.

    progreso : callable(Progreso) opcional, se llama para informar avance.
    cancelado: callable() -> bool opcional. Si en algún momento devuelve
               True, el escaneo aborta lanzando ScanCancelled.
    filtro   : ScanFilter opcional. Los archivos y carpetas que excluye
               ni se leen ni se cuentan como revisados.

    El trabajo está repartido en tres funciones, una por pasada
    (_pasada_tamanos, _pasada_hash_parcial y _pasada_hash_completo); esta
    solo las encadena y ordena el resultado.
    """
    progress = progress or _noop
    cancelled = cancelled or _never_cancel
    if filter is None:
        filter = ScanFilter.no_filter()

    if not os.path.isdir(root_folder):
        raise NotADirectoryError(f"No es una carpeta: {root_folder}")

    errors: list[tuple[str, str]] = []

    # Pasada 1: agrupar por tamaño. Solo siguen los tamaños compartidos por 2+ archivos.
    by_size, total_files, total_excluded = _size_pass(
        root_folder, filter, progress, cancelled, errors)
    candidates_by_size = {t: paths for t, paths in by_size.items() if len(paths) > 1}

    # Pasada 2: hash de los primeros 64 KB. Solo siguen los que además coinciden.
    finalists = _partial_hash_pass(candidates_by_size, progress, cancelled, errors)

    # Pasada 3: hash completo de los finalistas.
    groups = _full_hash_pass(finalists, progress, cancelled, errors)

    # Orden estable y útil: primero los grupos que liberan más espacio,
    # y dentro de cada grupo, los archivos por ruta.
    for g in groups:
        g.files.sort(key=lambda a: a.path)
    groups.sort(key=lambda g: (-g.reclaimable_space, g.files[0].path))

    total_finalists = sum(len(r) for r in finalists.values())
    progress(Progress(
        "hash_completo", max(total_finalists, 1), max(total_finalists, 1),
        "Escaneo terminado.",
    ))

    return ScanResult(
        groups=groups,
        total_files=total_files,
        errors=errors,
        total_excluded=total_excluded,
    )
