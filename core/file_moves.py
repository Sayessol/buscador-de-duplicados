"""Primitives to move or copy batches of files.

Common rules:
* A file in the destination is NEVER overwritten: if it already exists, the new
  one is saved with a suffix `(1)`, `(2)`...
* The destination cannot be inside the source folder.
* It can **move** (removes from the source) or **copy** (leaves the original).
* A CSV log is written.

Used by the "Gather images" tab. Quarantine has its own
implementation (`core/quarantine.py`) with these same rules.
"""

import csv
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime

from .callbacks import CancelledCallback, ProgressCallback
from .i18n import tr

MOVE = "move"
COPY = "copy"


class InvalidDestination(Exception):
    """The chosen destination is not valid (e.g. it is inside the source)."""


def _norm(p: str) -> str:
    return os.path.normcase(os.path.abspath(p))


def validate_destination(destination: str, source: str) -> str | None:
    """None if all is well, a warning str if it is worth warning, or raises
    InvalidDestination if it cannot continue."""
    d, o = _norm(destination), _norm(source)
    if d == o:
        raise InvalidDestination(
            tr("moves.same_folder"))
    if d.startswith(o + os.sep):
        raise InvalidDestination(
            tr("moves.inside_source"))
    if o.startswith(d + os.sep):
        return tr("moves.source_inside_destination")
    return None


def collision_free_path(destination: str) -> str:
    """If `destination` already exists -> 'name (1).ext', 'name (2).ext'..."""
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
    """Runs a list of Transfer (moves or copies each file)."""
    progress = progress or (lambda *_: None)
    cancelled = cancelled or (lambda: False)
    total = len(transfers)
    verb = tr("common.copying") if action == COPY else tr("common.moving")

    for i, t in enumerate(transfers, start=1):
        if cancelled():
            break
        progress(i, total, tr("moves.progress", verb=verb, i=i, total=total,
                              basename=os.path.basename(t.source)))
        try:
            if not os.path.exists(t.source):
                raise FileNotFoundError(tr("common.file_gone"))
            os.makedirs(os.path.dirname(t.destination), exist_ok=True)
            t.destination = collision_free_path(t.destination)
            if action == COPY:
                shutil.copy2(t.source, t.destination)
            else:
                shutil.move(t.source, t.destination)
            t.ok = True
        except (OSError, shutil.Error) as e:
            t.ok, t.error = False, str(e)

    progress(total, total, tr("common.done"))
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
            w.writerow([tr(key) for key in (
                "csv.date", "csv.action", "csv.source_root", "csv.source", "csv.destination",
                "csv.size_bytes", "csv.status", "csv.error")])
            status_done, status_error = tr("csv.status_done"), tr("csv.status_error")
            now = datetime.now().isoformat(timespec="seconds")
            for t in transfers:
                w.writerow([now, action, root_source, t.source, t.destination,
                            t.size, status_done if t.ok else status_error, t.error])
        return path
    except OSError:
        return ""
