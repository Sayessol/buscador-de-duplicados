"""What a scan finds: the files, the groups of identical files and the result."""

import os
from collections import defaultdict
from dataclasses import dataclass, field

from duplicate_finder.domain.filters import NO_EXTENSION


@dataclass
class DuplicateFile:
    """A specific file inside a group of duplicates."""

    path: str
    size: int


@dataclass
class DuplicateGroup:
    """Set of 2+ files with identical content."""

    hash: str  # the hash they share (identifies the group)
    size: int  # bytes of each copy (they all weigh the same)
    files: list[DuplicateFile]  # the copies in the group

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
                key = ext if ext else NO_EXTENSION
                acc[key][0] += 1
                acc[key][1] += a.size
        rows = [(ext, c, b) for ext, (c, b) in acc.items()]
        rows.sort(key=lambda f: (-f[2], f[0]))  # most bytes first; on a tie, alphabetical
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
