"""The real disk: the implementation of the `FileSystem` port with `os` and `shutil`."""

import csv
import os
import shutil
import time
from collections.abc import Iterable, Iterator, Sequence

# Windows (antivirus, indexer) can lock a freshly created file for a moment, and
# `os.remove` then fails with PermissionError: retry for a few tenths of a second.
_REMOVE_ATTEMPTS = 5
_REMOVE_DELAY = 0.1  # seconds, growing with each attempt (0.1 + 0.2 + 0.3 + 0.4)


class LocalFileSystem:
    def exists(self, path: str) -> bool:
        return os.path.exists(path)

    def is_dir(self, path: str) -> bool:
        return os.path.isdir(path)

    def is_file(self, path: str) -> bool:
        return os.path.isfile(path)

    def size(self, path: str) -> int:
        return os.path.getsize(path)

    def modified_time(self, path: str) -> float:
        return os.path.getmtime(path)

    def list_dir(self, path: str) -> list[str]:
        return os.listdir(path)

    def walk(self, root: str) -> Iterator[tuple[str, list[str], list[str]]]:
        return os.walk(root)

    def make_dirs(self, path: str) -> None:
        os.makedirs(path, exist_ok=True)

    def move(self, source: str, destination: str) -> None:
        shutil.move(source, destination)

    def copy_file(self, source: str, destination: str) -> None:
        shutil.copy2(source, destination)

    def copy_tree(self, source: str, destination: str) -> None:
        shutil.copytree(source, destination)

    def remove(self, path: str) -> None:
        """Deletes a file or folder, retrying briefly if Windows reports it as in use.

        If it is still locked after the last attempt, the PermissionError (an OSError) is
        raised again and the caller records it as a failure, like any other error.
        """
        for attempt in range(1, _REMOVE_ATTEMPTS + 1):
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                elif os.path.exists(path):
                    os.remove(path)
                return
            except PermissionError:
                if attempt == _REMOVE_ATTEMPTS:
                    raise
                time.sleep(_REMOVE_DELAY * attempt)

    def write_csv(self, path: str, rows: Iterable[Sequence[object]]) -> None:
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerows(rows)
