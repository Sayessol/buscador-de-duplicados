"""Core of the duplicates app: pure logic, no graphical interface.

Everything in this package can be tested from the console without opening
a window. The golden rule holds in every function that touches the file
system: **never delete, never modify the original, only read and (when
the user confirms) move.**
"""

# Single source of the version: the window and the release name use it.
# When publishing a new version, change it here and add its section to CHANGELOG.md
# (a test checks that the two match).
__version__ = "1.0.0"

from .hashing import (
    partial_hash,
    full_hash,
    format_size,
    BLOCK_SIZE,
    PARTIAL_HASH_SIZE,
)
from .scanner import (
    DuplicateFile,
    DuplicateGroup,
    ScanResult,
    Progress,
    ScanCancelled,
    scan,
)
from .filters import (
    ScanFilter,
    parse_extensions,
    parse_names,
    set_to_text,
    JUNK_EXTENSIONS,
    JUNK_NAMES,
    JUNK_FOLDERS,
    CATEGORY_EXTENSIONS,
)
from .selection import (
    DuplicateSelection,
    KEEP,
    MOVE,
    GROUP_OK,
    GROUP_NOTHING_KEPT,
    GROUP_MULTIPLE,
)
from .quarantine import (
    Move,
    QuarantineResult,
    InvalidQuarantine,
    validate_quarantine_folder,
    plan_moves,
    move_to_quarantine,
)
from .report import export_csv

__all__ = [
    "partial_hash",
    "full_hash",
    "format_size",
    "BLOCK_SIZE",
    "PARTIAL_HASH_SIZE",
    "DuplicateFile",
    "DuplicateGroup",
    "ScanResult",
    "Progress",
    "ScanCancelled",
    "scan",
    "ScanFilter",
    "parse_extensions",
    "parse_names",
    "set_to_text",
    "JUNK_EXTENSIONS",
    "JUNK_NAMES",
    "JUNK_FOLDERS",
    "CATEGORY_EXTENSIONS",
    "DuplicateSelection",
    "KEEP",
    "MOVE",
    "GROUP_OK",
    "GROUP_NOTHING_KEPT",
    "GROUP_MULTIPLE",
    "Move",
    "QuarantineResult",
    "InvalidQuarantine",
    "validate_quarantine_folder",
    "plan_moves",
    "move_to_quarantine",
    "export_csv",
]
