"""The doors of the application to the outside world.

A use case never touches the disk, an image library or a file of settings by itself: it asks one
of these ports. The infrastructure layer implements them for real (`infrastructure/`), and a
test can plug in a fake. Only the real input and output has a port: the disk, the hashes, the
images, the history file and the settings file.
"""

from collections.abc import Iterable, Iterator, Sequence
from typing import Any, Protocol

from duplicate_finder.domain.similarity import ImageFingerprint


class FileSystem(Protocol):
    """Everything the use cases need from the disk. Every method may raise OSError."""

    def exists(self, path: str) -> bool: ...

    def is_dir(self, path: str) -> bool: ...

    def is_file(self, path: str) -> bool: ...

    def size(self, path: str) -> int:
        """Size in bytes."""
        ...

    def modified_time(self, path: str) -> float:
        """Seconds since the epoch of the last modification."""
        ...

    def list_dir(self, path: str) -> list[str]:
        """Names (not paths) of what is inside a folder."""
        ...

    def walk(self, root: str) -> Iterator[tuple[str, list[str], list[str]]]:
        """Like `os.walk` from the top: (folder, subfolder names, file names). Removing names
        from the list of subfolders keeps the walk from entering them."""
        ...

    def make_dirs(self, path: str) -> None:
        """Creates the folder and its parents; it is fine if it already exists."""
        ...

    def move(self, source: str, destination: str) -> None:
        """Moves a file or a folder. The original only leaves its place once the copy is safe."""
        ...

    def copy_file(self, source: str, destination: str) -> None: ...

    def copy_tree(self, source: str, destination: str) -> None: ...

    def remove(self, path: str) -> None:
        """Deletes a file or a folder (and retries for a moment if it is in use)."""
        ...

    def write_csv(self, path: str, rows: Iterable[Sequence[object]]) -> None:
        """Writes a CSV file (UTF-8 with BOM, so Excel opens it well). The folder must exist."""
        ...


class FileHasher(Protocol):
    """Content hashes of a file."""

    partial_size: int
    """How many bytes from the start of the file the partial hash covers."""

    def partial_hash(self, path: str) -> str: ...

    def full_hash(self, path: str) -> str: ...


class FingerprintReader(Protocol):
    """Reads an image and gives its fingerprint (dHash and colour signature)."""

    def read(self, path: str) -> ImageFingerprint: ...


class HistoryStore(Protocol):
    """Where the history of operations is kept. Each operation is a dictionary."""

    def load(self) -> list[dict[str, Any]]: ...

    def save(self, operations: list[dict[str, Any]]) -> None: ...


class SettingsStore(Protocol):
    """Where the settings (view mode, theme, language) are kept."""

    def load(self) -> dict[str, Any]: ...

    def save(self, data: dict[str, Any]) -> None: ...
