"""Use case: start choosing which copy to keep in each group of a result.

The selection (domain) decides with the name, the depth and the age of the files; the age comes
from the disk, so this use case gives the selection the way to ask for it.
"""

from duplicate_finder.application.ports import FileSystem
from duplicate_finder.domain.selection import DuplicateSelection, ResultLike


class StartSelection:
    def __init__(self, fs: FileSystem) -> None:
        self._fs = fs

    def __call__(self, result: ResultLike) -> DuplicateSelection:
        """A new selection for `result`: everything kept, nothing to move yet."""
        return DuplicateSelection(result, self._fs.modified_time)
