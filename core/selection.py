"""Which copy is kept and which ones are moved, in each group of duplicates.

The `DuplicateSelection` is the "editable state" between the
scan result (immutable) and the move-to-quarantine step.

Rule the app enforces: when moving, every group must end up with
**exactly one** copy marked as KEEP. Until that holds
in all groups, nothing can be moved.

Initial state: everything on KEEP (that is, nothing would be moved). This way
the app never "proposes to move" anything unless the user decides it, either
by hand or by applying the preferred-folder rule.
"""

import os
import re
from collections.abc import Sequence
from typing import Protocol

from .scanner import DuplicateFile

KEEP = "conservar"
MOVE = "mover"

# Names that "smell" like a copy and not like the original.
_LOOKS_LIKE_COPY = re.compile(
    r"cop(?:y|ia)\b|duplicad|\bnew\b|\(\d+\)|[ _-]copy|[ _-]copia|[ _-]\d+$",
    re.IGNORECASE)

# Possible states of a group with respect to the "single copy" rule.
GROUP_OK = "ok"                 # exactly one copy on KEEP
GROUP_NOTHING_KEPT = "sin_conservar"   # no copy on KEEP
GROUP_MULTIPLE = "multiple"     # two or more copies on KEEP (undecided)


def _is_inside(path: str, folder: str) -> bool:
    """True if `path` is inside `folder` (normalized comparison)."""
    try:
        abs_path = os.path.normcase(os.path.abspath(path))
        abs_folder = os.path.normcase(os.path.abspath(folder))
    except (OSError, ValueError):
        return False
    if abs_folder.endswith(os.sep):
        abs_folder = abs_folder.rstrip(os.sep)
    return abs_path == abs_folder or abs_path.startswith(abs_folder + os.sep)


class _Group(Protocol):
    """The minimum asked of a group: a list of files (exact duplicates
    and similar photos both meet it, which is why they share this class)."""

    @property
    def files(self) -> list[DuplicateFile]: ...


class _Result(Protocol):
    """The minimum asked of a result: a list of groups."""

    @property
    def groups(self) -> Sequence[_Group]: ...


class DuplicateSelection:
    def __init__(self, result: _Result) -> None:
        self.result = result
        # _decision[(group_index, path)] -> KEEP | MOVE
        self._decision: dict[tuple[int, str], str] = {}
        for gi, group in enumerate(result.groups):
            for file in group.files:
                self._decision[(gi, file.path)] = KEEP

    # ------------------------------------------------------------------
    # Queries and changes on a file
    # ------------------------------------------------------------------
    def decision(self, group_index: int, path: str) -> str:
        return self._decision.get((group_index, path), KEEP)

    def mark(self, group_index: int, path: str, decision: str) -> None:
        assert decision in (KEEP, MOVE)
        if (group_index, path) in self._decision:
            self._decision[(group_index, path)] = decision

    def toggle(self, group_index: int, path: str) -> str:
        current = self.decision(group_index, path)
        new = MOVE if current == KEEP else KEEP
        self.mark(group_index, path, new)
        return new

    def keep_only(self, group_index: int, kept_path: str) -> None:
        """Marks `kept_path` as KEEP and the rest of the group as MOVE."""
        group = self.result.groups[group_index]
        for file in group.files:
            self.mark(
                group_index, file.path,
                KEEP if file.path == kept_path else MOVE,
            )

    # ------------------------------------------------------------------
    # Automatic rule by preferred folder
    # ------------------------------------------------------------------
    def apply_folder_rule(self, preferred_folder: str | None) -> tuple[int, int]:
        """For each group: if any copy is inside `preferred_folder`,
        keeps that one (the one with the shortest path if there are several) and marks the
        rest as MOVE. If no copy is inside, the group is left
        entirely on KEEP (it stays "undecided" so the user can
        resolve it by hand).

        Returns (resolved_groups, unmatched_groups).
        """
        preferred_folder = (preferred_folder or "").strip()
        resolved = 0
        no_match = 0

        for gi, group in enumerate(self.result.groups):
            inside = [a.path for a in group.files
                      if preferred_folder and _is_inside(a.path, preferred_folder)]
            if inside:
                kept = min(inside, key=len)
                self.keep_only(gi, kept)
                resolved += 1
            else:
                for a in group.files:
                    self.mark(gi, a.path, KEEP)
                no_match += 1

        return resolved, no_match

    # ------------------------------------------------------------------
    # State of the groups and global validation
    # ------------------------------------------------------------------
    def _kept_in(self, group_index: int) -> list[DuplicateFile]:
        group = self.result.groups[group_index]
        return [a for a in group.files
                if self.decision(group_index, a.path) == KEEP]

    def group_state(self, group_index: int) -> str:
        n = len(self._kept_in(group_index))
        if n == 1:
            return GROUP_OK
        if n == 0:
            return GROUP_NOTHING_KEPT
        return GROUP_MULTIPLE

    def pending_groups(self) -> list[int]:
        return [gi for gi in range(len(self.result.groups))
                if self.group_state(gi) != GROUP_OK]

    def all_ready(self) -> bool:
        return not self.pending_groups()

    # ------------------------------------------------------------------
    # Summary of what would be moved
    # ------------------------------------------------------------------
    def files_to_move(self) -> list[tuple[int, DuplicateFile]]:
        """List of (group_index, DuplicateFile) marked as MOVE."""
        output: list[tuple[int, DuplicateFile]] = []
        for gi, group in enumerate(self.result.groups):
            for file in group.files:
                if self.decision(gi, file.path) == MOVE:
                    output.append((gi, file))
        return output

    def count_to_move(self) -> int:
        return len(self.files_to_move())

    def space_to_free(self) -> int:
        return sum(a.size for _gi, a in self.files_to_move())

    # ------------------------------------------------------------------
    # Automatic preselection (Simple mode, or a button in Advanced)
    # ------------------------------------------------------------------
    def preselect_primary(self) -> None:
        """In each group, keeps the "primary" copy and marks the rest
        to be moved.

        Primary = the one that looks least like a copy by its name, then the
        least nested, then the oldest, then the one with the shortest path.
        """
        for gi, group in enumerate(self.result.groups):
            best = min(group.files, key=_primary_score)
            self.keep_only(gi, best.path)


def _primary_score(file: DuplicateFile) -> tuple[int, int, float, int]:
    """Score to choose the "primary" copy: min() keeps the smallest
    tuple, so each field goes from "best" (lower) to "worst".
    """
    path = file.path
    name = os.path.basename(path)
    looks_like_copy = 1 if _LOOKS_LIKE_COPY.search(name) else 0  # 0 = does not look like a copy
    depth = os.path.normpath(path).count(os.sep)        # less nested is better
    try:
        mtime = os.path.getmtime(path)                        # older is better
    except OSError:
        mtime = float("inf")
    return (looks_like_copy, depth, mtime, len(path))      # shorter path breaks the tie
