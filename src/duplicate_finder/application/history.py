"""Use cases: the history of the operations that move or copy files, and undoing them.

Undo:
* "move" -> returns each file/folder from the destination to its source.
* "copy" -> DELETES the copies in the destination. It is the ONLY place where the
  app deletes anything, and only files it created itself; the caller must
  ask for explicit confirmation first.
"""

import os
from datetime import datetime
from typing import Any

from duplicate_finder.application.callbacks import ProgressCallback
from duplicate_finder.application.ports import FileSystem, HistoryStore
from duplicate_finder.domain.transfers import COPY
from duplicate_finder.i18n import tr


class OperationHistory:
    def __init__(self, store: HistoryStore, fs: FileSystem) -> None:
        self._store = store
        self._fs = fs

    def record(
        self,
        kind: str,
        action: str,
        root_source: str,
        destination: str,
        moves: list[tuple[str, str]],
        description: str = "",
    ) -> str:
        """`moves`: list of (source, destination) already carried out successfully.

        Returns the id of the recorded operation.
        """
        items = self._store.load()
        now = datetime.now()
        op: dict[str, Any] = {
            "id": now.strftime("%Y%m%d%H%M%S%f"),
            "date": now.isoformat(timespec="seconds"),
            "kind": kind,
            "action": action,  # "move" | "copy"
            "source_root": root_source,
            "destination": destination,
            "description": description,
            "moves": [{"source": s, "destination": d} for s, d in moves],
            "undone": False,
        }
        items.append(op)
        self._store.save(items)
        return str(op["id"])

    def list_all(self) -> list[dict[str, Any]]:
        """Operations, from the most recent to the oldest."""
        return list(reversed(self._store.load()))

    def _mark_undone(self, op_id: str) -> None:
        items = self._store.load()
        for op in items:
            if op["id"] == op_id:
                op["undone"] = True
        self._store.save(items)

    def undo(self, op_id: str, progress: ProgressCallback | None = None) -> dict[str, Any]:
        """Reverts the operation `op_id`.

        Returns a dict: {"reverted": n_reverted, "failures": [(path, message), ...],
        "op": operation}. Marks the operation as undone if there were no failures.
        """
        progress = progress or (lambda *_: None)
        op = next((o for o in self._store.load() if o["id"] == op_id), None)
        if op is None:
            return {"reverted": 0, "failures": [("", tr("history.op_not_found"))], "op": None}
        if op.get("undone"):
            return {"reverted": 0, "failures": [("", tr("history.already_undone"))], "op": op}

        op_moves = op["moves"]  # each one: {"source": ..., "destination": ...}
        total = len(op_moves)
        ok = 0
        failures: list[tuple[str, str]] = []

        for i, m in enumerate(op_moves, start=1):
            source, destination = m["source"], m["destination"]
            progress(i, total, os.path.basename(destination) or destination)
            try:
                if op["action"] == COPY:
                    # Undoing a copy = deleting what the app copied into the
                    # destination. The original is never touched.
                    self._fs.remove(destination)
                    ok += 1
                else:  # "move" -> take the file back to its source
                    if not self._fs.exists(destination):
                        raise FileNotFoundError(tr("history.gone_from_destination"))
                    if self._fs.exists(source):
                        # someone has put something there again: we do not overwrite it
                        raise FileExistsError(tr("history.original_path_taken"))
                    self._fs.make_dirs(os.path.dirname(source))
                    self._fs.move(destination, source)
                    ok += 1
            except OSError as e:
                failures.append((destination, str(e)))

        # It is only marked "undone" if EVERYTHING could be reverted; otherwise it can be
        # retried later (the ones that already went back will not be moved twice
        # because their destination no longer exists).
        if not failures:
            self._mark_undone(op_id)
        return {"reverted": ok, "failures": failures, "op": op}
