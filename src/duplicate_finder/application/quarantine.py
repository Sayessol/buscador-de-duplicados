"""Use case: move the discarded duplicates to a quarantine folder.

Safety rules (inherited from the console script):

* NOTHING is ever deleted or overwritten. Files are only **moved**.
* The original only leaves its place once its copy is already safe in
  the quarantine (the file system port guarantees that).
* The structure of subfolders relative to the scanned folder is preserved,
  so every file can be put back in its place if needed.
* If the destination already has a file with that name, the new one is
  saved with a suffix `(1)`, `(2)`... instead of overwriting it.
* When finished, a CSV log is written with every move (source,
  destination, status), so it can be undone by hand.
"""

import os
from datetime import datetime

from duplicate_finder.application.callbacks import CancelledCallback, ProgressCallback
from duplicate_finder.application.file_transfers import collision_free_path
from duplicate_finder.application.history import OperationHistory
from duplicate_finder.application.ports import FileSystem
from duplicate_finder.domain.operations import KIND_QUARANTINE
from duplicate_finder.domain.selection import DuplicateSelection
from duplicate_finder.domain.transfers import MOVE, Move, QuarantineResult
from duplicate_finder.i18n import tr


class InvalidQuarantine(Exception):
    """The chosen quarantine folder is not valid (e.g. it is inside
    the scanned folder)."""


def _norm(p: str) -> str:
    return os.path.normcase(os.path.abspath(p))


def validate_quarantine_folder(quarantine_folder: str, root_folder: str) -> str | None:
    """Returns a warning message (str) or None if all is well.

    Raises InvalidQuarantine if the quarantine folder is inside the
    scanned folder (the next scan would find the files already moved
    again, or a folder would be moved into itself).
    """
    cq = _norm(quarantine_folder)
    cr = _norm(root_folder)

    if cq == cr:
        raise InvalidQuarantine(tr("quarantine.same_as_scanned"))
    if cq.startswith(cr + os.sep):
        raise InvalidQuarantine(tr("quarantine.inside_scanned"))
    if cr.startswith(cq + os.sep):
        return tr("quarantine.scanned_inside_quarantine")
    return None


def _destination_for(source: str, root_folder: str, quarantine_folder: str) -> str:
    """Destination path preserving the structure relative to the scanned folder."""
    try:
        rel = os.path.relpath(source, root_folder)
    except ValueError:
        rel = os.path.basename(source)
    if rel.startswith(".." + os.sep) or rel == "..":
        # The file is outside the scanned folder: we hang it from a
        # "_outside_scanned_folder" subfolder with its name.
        rel = os.path.join("_outside_scanned_folder", os.path.basename(source))
    return os.path.join(quarantine_folder, rel)


def plan_moves(
    selection: DuplicateSelection,
    root_folder: str,
    quarantine_folder: str,
) -> list[Move]:
    """List of Move (not executed) for the files marked as MOVE."""
    plan: list[Move] = []
    for gi, file in selection.files_to_move():
        destination = _destination_for(file.path, root_folder, quarantine_folder)
        plan.append(Move(group=gi + 1, source=file.path, destination=destination, size=file.size))
    return plan


class MoveToQuarantine:
    def __init__(self, fs: FileSystem, history: OperationHistory) -> None:
        self._fs = fs
        self._history = history

    def __call__(
        self,
        selection: DuplicateSelection,
        root_folder: str,
        quarantine_folder: str,
        progress: ProgressCallback | None = None,
        cancelled: CancelledCallback | None = None,
        description_key: str = "history.description_exact",
    ) -> QuarantineResult:
        """Carries out the move and records it in the history. Returns a QuarantineResult.

        progress : optional callable(current, total, message).
        cancelled: optional callable() -> bool. If it turns True, moving stops
                   (what was already moved stays moved) and the log is
                   still written.
        description_key: catalog text for the history entry (it receives `count`).
        """
        if not selection.all_ready():
            raise ValueError(tr("quarantine.unresolved_groups"))

        validate_quarantine_folder(quarantine_folder, root_folder)

        progress = progress or (lambda *_: None)
        cancelled = cancelled or (lambda: False)

        plan = plan_moves(selection, root_folder, quarantine_folder)
        total = len(plan)
        self._fs.make_dirs(quarantine_folder)

        for i, move in enumerate(plan, start=1):
            if cancelled():
                break
            progress(
                i,
                total,
                tr("quarantine.progress", i=i, total=total, basename=os.path.basename(move.source)),
            )
            try:
                if not self._fs.exists(move.source):
                    raise FileNotFoundError(tr("common.file_gone"))
                self._fs.make_dirs(os.path.dirname(move.destination))
                move.destination = collision_free_path(self._fs, move.destination)
                self._fs.move(move.source, move.destination)
                move.ok = True
            except OSError as e:
                move.ok = False
                move.error = str(e)

        result = QuarantineResult(moves=plan)
        result.log_path = self._write_log(plan, quarantine_folder, root_folder)
        if result.moved:
            self._history.record(
                KIND_QUARANTINE,
                MOVE,
                root_folder,
                quarantine_folder,
                [(m.source, m.destination) for m in result.moved],
                tr(description_key, count=len(result.moved)),
            )
        progress(total, total, tr("common.done"))
        return result

    def _write_log(self, moves: list[Move], quarantine_folder: str, root_folder: str) -> str:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = os.path.join(quarantine_folder, f"_log_quarantine_{stamp}.csv")
        status_moved, status_error = tr("csv.status_moved"), tr("csv.status_error")
        now = datetime.now().isoformat(timespec="seconds")
        rows: list[list[object]] = [
            [
                tr(key)
                for key in (
                    "csv.date",
                    "csv.scanned_folder",
                    "csv.group",
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
                root_folder,
                m.group,
                m.source,
                m.destination,
                m.size,
                status_moved if m.ok else status_error,
                m.error,
            ]
            for m in moves
        ]
        try:
            self._fs.make_dirs(quarantine_folder)
            self._fs.write_csv(log_path, rows)
        except OSError:
            return ""
        return log_path
