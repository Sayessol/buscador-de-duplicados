"""In-memory stand-ins for the ports, so the use cases can be tested without touching the disk."""

import hashlib
import os
from collections.abc import Iterable, Iterator, Sequence
from typing import Any


def _norm(path: str) -> str:
    return os.path.normpath(path)


class FakeFileSystem:
    """A tiny file system in a dictionary: path -> content. Implements the `FileSystem` port."""

    def __init__(self, files: dict[str, bytes] | None = None) -> None:
        self.files: dict[str, bytes] = {_norm(p): data for p, data in (files or {}).items()}
        self.folders: set[str] = set()
        self.mtimes: dict[str, float] = {}
        self.csv_files: dict[str, list[list[object]]] = {}
        self.fail_moves_of: set[str] = set()     # moving these paths raises OSError

    # ---- queries
    def _all_folders(self) -> set[str]:
        found = set(self.folders)
        for path in self.files:
            parent = os.path.dirname(path)
            while parent and parent not in found and parent != os.path.dirname(parent):
                found.add(parent)
                parent = os.path.dirname(parent)
        return found

    def exists(self, path: str) -> bool:
        return _norm(path) in self.files or _norm(path) in self._all_folders()

    def is_dir(self, path: str) -> bool:
        return _norm(path) in self._all_folders()

    def is_file(self, path: str) -> bool:
        return _norm(path) in self.files

    def size(self, path: str) -> int:
        try:
            return len(self.files[_norm(path)])
        except KeyError:
            raise FileNotFoundError(path) from None

    def modified_time(self, path: str) -> float:
        return self.mtimes.get(_norm(path), 0.0)

    def list_dir(self, path: str) -> list[str]:
        base = _norm(path)
        names = {os.path.basename(p) for p in list(self.files) + list(self._all_folders())
                 if os.path.dirname(p) == base}
        return sorted(names)

    def walk(self, root: str) -> Iterator[tuple[str, list[str], list[str]]]:
        base = _norm(root)
        folders = self._all_folders()
        subdirs = sorted(os.path.basename(f) for f in folders if os.path.dirname(f) == base)
        names = sorted(os.path.basename(p) for p in self.files if os.path.dirname(p) == base)
        yield base, subdirs, names
        for sub in subdirs:                     # the caller may have pruned `subdirs`
            yield from self.walk(os.path.join(base, sub))

    # ---- changes
    def make_dirs(self, path: str) -> None:
        self.folders.add(_norm(path))

    def move(self, source: str, destination: str) -> None:
        src, dst = _norm(source), _norm(destination)
        if src in self.fail_moves_of:
            raise PermissionError(13, "locked", source)
        if src not in self.files:
            raise FileNotFoundError(source)
        self.files[dst] = self.files.pop(src)

    def copy_file(self, source: str, destination: str) -> None:
        self.files[_norm(destination)] = self.files[_norm(source)]

    def copy_tree(self, source: str, destination: str) -> None:
        src = _norm(source)
        for path in [p for p in self.files if p.startswith(src + os.sep)]:
            relative = os.path.relpath(path, src)
            self.files[os.path.join(_norm(destination), relative)] = self.files[path]

    def remove(self, path: str) -> None:
        target = _norm(path)
        self.files.pop(target, None)
        for inside in [p for p in self.files if p.startswith(target + os.sep)]:
            del self.files[inside]

    def write_csv(self, path: str, rows: Iterable[Sequence[object]]) -> None:
        self.csv_files[_norm(path)] = [list(row) for row in rows]


class FakeHasher:
    """Hashes that read from the fake file system. The partial hash covers only 4 bytes."""

    partial_size = 4

    def __init__(self, fs: FakeFileSystem) -> None:
        self._fs = fs

    def partial_hash(self, path: str) -> str:
        return hashlib.md5(self._fs.files[_norm(path)][:self.partial_size]).hexdigest()

    def full_hash(self, path: str) -> str:
        return hashlib.md5(self._fs.files[_norm(path)]).hexdigest()


class InMemoryHistoryStore:
    """The `HistoryStore` port in a list."""

    def __init__(self) -> None:
        self.operations: list[dict[str, Any]] = []

    def load(self) -> list[dict[str, Any]]:
        return [dict(op) for op in self.operations]

    def save(self, operations: list[dict[str, Any]]) -> None:
        self.operations = [dict(op) for op in operations]
