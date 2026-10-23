"""Recursive scan of a folder looking for duplicate files.

This module ONLY READS the file system. It does not move, rename or
delete anything.

The scan goes in passes, from the cheapest to the most expensive:

  Pass 1  -  group all files by size in bytes.
             A file with a unique size cannot have duplicates,
             so it is discarded without reading its content.

  Pass 2  -  for those that share a size, compute the hash of the
             first 64 KB (partial hash). Fast, and it discards almost
             all the false positives.

  Pass 3  -  for those that also share a partial hash, compute the
             hash of the whole file. The ones that match here are
             real duplicates, byte for byte.

The result is a list of `DuplicateGroup`, each one with 2 or more
files of identical content.
"""

import os
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field

from .hashing import partial_hash, full_hash, PARTIAL_HASH_SIZE
from .filters import ScanFilter


class ScanCancelled(Exception):
    """Raised when the caller asks to cancel the scan halfway through."""


@dataclass
class DuplicateFile:
    """A specific file inside a group of duplicates."""

    path: str
    size: int


@dataclass
class DuplicateGroup:
    """Set of 2+ files with identical content."""

    hash: str          # the hash they share (identifies the group)
    size: int        # bytes of each copy (they all weigh the same)
    files: list[DuplicateFile]   # the copies in the group

    @property
    def count(self) -> int:
        return len(self.files)

    @property
    def reclaimable_space(self) -> int:
        """Bytes that would be freed if only one copy were kept."""
        return self.size * (len(self.files) - 1)


@dataclass
class ScanResult:
    """Everything a scan produced."""

    groups: list[DuplicateGroup]
    total_files: int
    errors: list[tuple[str, str]] = field(default_factory=list)  # (path, message)
    total_excluded: int = 0  # files skipped by the filter

    @property
    def total_groups(self) -> int:
        return len(self.groups)

    def summary_by_extension(self) -> list[tuple[str, int, int]]:
        """Breakdown of the duplicate files by extension.

        Returns a list of tuples (extension, count, bytes),
        sorted from the most to the least space taken. Useful for the
        user to decide which kinds to add to the exclusion filter.
        """
        # acc[extension] = [count, total_bytes]
        acc: defaultdict[str, list[int]] = defaultdict(lambda: [0, 0])
        for g in self.groups:
            for a in g.files:
                ext = os.path.splitext(a.path)[1].lower().lstrip(".")
                key = ext if ext else "(sin extensión)"
                acc[key][0] += 1
                acc[key][1] += a.size
        rows = [(ext, c, b) for ext, (c, b) in acc.items()]
        rows.sort(key=lambda f: (-f[2], f[0]))   # most bytes first; on a tie, alphabetical
        return rows

    @property
    def total_files_duplicates(self) -> int:
        """Number of files that are in some group of duplicates."""
        return sum(g.count for g in self.groups)

    @property
    def extra_copies(self) -> int:
        """Files that could be moved (all the copies but one per group)."""
        return sum(g.count - 1 for g in self.groups)

    @property
    def total_reclaimable_space(self) -> int:
        return sum(g.reclaimable_space for g in self.groups)


@dataclass
class Progress:
    """Progress notification so the interface can show a bar.

    phase:
      "tamanos"        -> Pass 1, counting and measuring files.
      "hash_parcial"   -> Pass 2, hashing the first 64 KB.
      "hash_completo"  -> Pass 3, hashing whole files.
    total == 0 means "I do not know yet how many there are in total" (Pass 1).
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
    """Pass 1: walks the tree and groups the files by size in bytes.

    Returns (paths_by_size, total_files, total_excluded). Files that the
    filter excludes are neither measured nor counted as reviewed.
    """
    by_size: defaultdict[int, list[str]] = defaultdict(list)
    total_files = 0
    total_excluded = 0

    for current_dir, subdirs, names in os.walk(root_folder):
        if cancelled():
            raise ScanCancelled()

        # Prune excluded folders: os.walk does not enter the ones we remove here.
        subdirs[:] = [d for d in subdirs if not filter.excludes_folder(d)]

        for name in names:
            if filter.excludes_name(name):
                total_excluded += 1
                continue

            path = os.path.join(current_dir, name)
            try:
                if not os.path.isfile(path):
                    # broken symbolic links, devices, etc.
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
    """Pass 2: hash of the first 64 KB of the files that share a size.

    Returns only the "finalists": the keys (size, partial_hash) that
    are shared by 2 or more files.
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
            # The key includes the size: two files with the same partial
            # hash but a different size are never the same file.
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
    """Pass 3: hash of the whole file for the finalists.

    The ones that match here are real duplicates, byte for byte. If a file
    weighs less than 64 KB, its partial hash already covered the whole content and this
    pass is skipped for it.
    """
    total_finalists = sum(len(r) for r in finalists.values())
    groups: list[DuplicateGroup] = []
    full_processed = 0

    for (size, hp), paths in finalists.items():
        if size <= PARTIAL_HASH_SIZE:
            # The partial hash already covered the whole file: they are identical.
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
    """Scans `root_folder` recursively and returns a ScanResult.

    progress : optional callable(Progress), called to report progress.
    cancelled: optional callable() -> bool. If at any moment it returns
               True, the scan aborts by raising ScanCancelled.
    filter   : optional ScanFilter. The files and folders it excludes
               are neither read nor counted as reviewed.

    The work is split into three functions, one per pass
    (_size_pass, _partial_hash_pass and _full_hash_pass); this one
    only chains them together and sorts the result.
    """
    progress = progress or _noop
    cancelled = cancelled or _never_cancel
    if filter is None:
        filter = ScanFilter.no_filter()

    if not os.path.isdir(root_folder):
        raise NotADirectoryError(f"No es una carpeta: {root_folder}")

    errors: list[tuple[str, str]] = []

    # Pass 1: group by size. Only the sizes shared by 2+ files continue.
    by_size, total_files, total_excluded = _size_pass(
        root_folder, filter, progress, cancelled, errors)
    candidates_by_size = {t: paths for t, paths in by_size.items() if len(paths) > 1}

    # Pass 2: hash of the first 64 KB. Only the ones that also match continue.
    finalists = _partial_hash_pass(candidates_by_size, progress, cancelled, errors)

    # Pass 3: full hash of the finalists.
    groups = _full_hash_pass(finalists, progress, cancelled, errors)

    # Stable and useful order: first the groups that free the most space,
    # and within each group, the files by path.
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
