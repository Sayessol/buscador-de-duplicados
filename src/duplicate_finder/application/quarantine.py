"""Use case: move the discarded duplicates to a quarantine folder."""

import csv
import os
import shutil
from datetime import datetime
from duplicate_finder.domain.selection import DuplicateSelection
from duplicate_finder.application.callbacks import CancelledCallback, ProgressCallback
from duplicate_finder.i18n import tr
from duplicate_finder.domain.transfers import Move, QuarantineResult


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
        raise InvalidQuarantine(
            tr("quarantine.same_as_scanned"))
    if cq.startswith(cr + os.sep):
        raise InvalidQuarantine(
            tr("quarantine.inside_scanned"))
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


def _avoid_collision(destination: str) -> str:
    """If `destination` already exists, returns 'name (1).ext', 'name (2).ext'..."""
    if not os.path.exists(destination):
        return destination
    base, ext = os.path.splitext(destination)
    i = 1
    while os.path.exists(f"{base} ({i}){ext}"):
        i += 1
    return f"{base} ({i}){ext}"


def plan_moves(
    selection: DuplicateSelection, root_folder: str, quarantine_folder: str,
) -> list[Move]:
    """List of Move (not executed) for the files marked as MOVE."""
    plan: list[Move] = []
    for gi, file in selection.files_to_move():
        destination = _destination_for(file.path, root_folder, quarantine_folder)
        plan.append(Move(
            group=gi + 1, source=file.path, destination=destination,
            size=file.size))
    return plan


def move_to_quarantine(
    selection: DuplicateSelection,
    root_folder: str,
    quarantine_folder: str,
    progress: ProgressCallback | None = None,
    cancelled: CancelledCallback | None = None,
) -> QuarantineResult:
    """Carries out the move. Returns a QuarantineResult.

    progress : optional callable(current, total, message).
    cancelled: optional callable() -> bool. If it turns True, moving stops
               (what was already moved stays moved) and the log is
               still written.
    """
    if not selection.all_ready():
        raise ValueError(
            tr("quarantine.unresolved_groups"))

    validate_quarantine_folder(quarantine_folder, root_folder)

    progress = progress or (lambda *_: None)
    cancelled = cancelled or (lambda: False)

    plan = plan_moves(selection, root_folder, quarantine_folder)
    total = len(plan)
    os.makedirs(quarantine_folder, exist_ok=True)

    for i, move in enumerate(plan, start=1):
        if cancelled():
            break
        progress(i, total, tr("quarantine.progress", i=i, total=total,
                              basename=os.path.basename(move.source)))
        try:
            if not os.path.exists(move.source):
                raise FileNotFoundError(tr("common.file_gone"))
            os.makedirs(os.path.dirname(move.destination), exist_ok=True)
            move.destination = _avoid_collision(move.destination)
            shutil.move(move.source, move.destination)
            move.ok = True
        except (OSError, shutil.Error) as e:
            move.ok = False
            move.error = str(e)

    result = QuarantineResult(moves=plan)
    result.log_path = _write_log(plan, quarantine_folder, root_folder)
    progress(total, total, tr("common.done"))
    return result


def _write_log(
    moves: list[Move], quarantine_folder: str, root_folder: str,
) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(quarantine_folder, f"_log_quarantine_{stamp}.csv")
    try:
        os.makedirs(quarantine_folder, exist_ok=True)
        with open(log_path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow([tr(key) for key in (
                "csv.date", "csv.scanned_folder", "csv.group", "csv.source",
                "csv.destination", "csv.size_bytes", "csv.status", "csv.error")])
            status_moved, status_error = tr("csv.status_moved"), tr("csv.status_error")
            now = datetime.now().isoformat(timespec="seconds")
            for m in moves:
                w.writerow([
                    now, root_folder, m.group, m.source, m.destination,
                    m.size, status_moved if m.ok else status_error, m.error,
                ])
        return log_path
    except OSError:
        return ""
