"""Use case helpers: move or copy batches of files without overwriting.

Common rules:
* A file in the destination is NEVER overwritten: if it already exists, the new
  one is saved with a suffix `(1)`, `(2)`...
* The destination cannot be inside the source folder.
* It can **move** (removes from the source) or **copy** (leaves the original).
* A CSV log is written.
"""

import os
from datetime import datetime

from duplicate_finder.application.callbacks import CancelledCallback, ProgressCallback
from duplicate_finder.application.ports import FileSystem
from duplicate_finder.domain.transfers import COPY, MOVE, Transfer, TransferResult
from duplicate_finder.i18n import tr


class InvalidDestination(Exception):
    """The chosen destination is not valid (e.g. it is inside the source)."""


def _norm(p: str) -> str:
    return os.path.normcase(os.path.abspath(p))


def validate_destination(destination: str, source: str) -> str | None:
    """None if all is well, a warning str if it is worth warning, or raises
    InvalidDestination if it cannot continue."""
    d, o = _norm(destination), _norm(source)
    if d == o:
        raise InvalidDestination(tr("moves.same_folder"))
    if d.startswith(o + os.sep):
        raise InvalidDestination(tr("moves.inside_source"))
    if o.startswith(d + os.sep):
        return tr("moves.source_inside_destination")
    return None


def collision_free_path(fs: FileSystem, destination: str) -> str:
    """If `destination` already exists -> 'name (1).ext', 'name (2).ext'..."""
    if not fs.exists(destination):
        return destination
    base, ext = os.path.splitext(destination)
    i = 1
    while fs.exists(f"{base} ({i}){ext}"):
        i += 1
    return f"{base} ({i}){ext}"


class FileTransfers:
    def __init__(self, fs: FileSystem) -> None:
        self._fs = fs

    def size(self, path: str) -> int:
        try:
            return self._fs.size(path)
        except OSError:
            return 0

    def execute(
        self,
        transfers: list[Transfer],
        action: str = MOVE,
        progress: ProgressCallback | None = None,
        cancelled: CancelledCallback | None = None,
    ) -> TransferResult:
        """Runs a list of Transfer (moves or copies each file)."""
        progress = progress or (lambda *_: None)
        cancelled = cancelled or (lambda: False)
        total = len(transfers)
        verb = tr("common.copying") if action == COPY else tr("common.moving")

        for i, t in enumerate(transfers, start=1):
            if cancelled():
                break
            progress(
                i,
                total,
                tr(
                    "moves.progress",
                    verb=verb,
                    i=i,
                    total=total,
                    basename=os.path.basename(t.source),
                ),
            )
            try:
                if not self._fs.exists(t.source):
                    raise FileNotFoundError(tr("common.file_gone"))
                self._fs.make_dirs(os.path.dirname(t.destination))
                t.destination = collision_free_path(self._fs, t.destination)
                if action == COPY:
                    self._fs.copy_file(t.source, t.destination)
                else:
                    self._fs.move(t.source, t.destination)
                t.ok = True
            except OSError as e:
                t.ok, t.error = False, str(e)

        progress(total, total, tr("common.done"))
        return TransferResult(transfers=transfers, action=action)

    def write_log(
        self,
        transfers: list[Transfer],
        destination_folder: str,
        prefix: str,
        root_source: str,
        action: str,
    ) -> str:
        """Writes the CSV log of a batch; returns its path ("" if it could not be written)."""
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(destination_folder, f"_log_{prefix}_{stamp}.csv")
        status_done, status_error = tr("csv.status_done"), tr("csv.status_error")
        now = datetime.now().isoformat(timespec="seconds")
        rows: list[list[object]] = [
            [
                tr(key)
                for key in (
                    "csv.date",
                    "csv.action",
                    "csv.source_root",
                    "csv.source",
                    "csv.destination",
                    "csv.size_bytes",
                    "csv.status",
                    "csv.error",
                )
            ]
        ]
        rows += [
            [
                now,
                action,
                root_source,
                t.source,
                t.destination,
                t.size,
                status_done if t.ok else status_error,
                t.error,
            ]
            for t in transfers
        ]
        try:
            self._fs.make_dirs(destination_folder)
            self._fs.write_csv(path, rows)
        except OSError:
            return ""
        return path
