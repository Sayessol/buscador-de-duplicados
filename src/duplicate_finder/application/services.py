"""The use cases of the app, together, ready to be handed to the interface.

`bootstrap.py` builds one `Services` with the real infrastructure; a test can build another
with fakes. The interface only ever sees this object, never the disk or the history file.
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from duplicate_finder.application.find_similar_photos import FindSimilarPhotos
from duplicate_finder.application.gather import GatherImages
from duplicate_finder.application.history import OperationHistory
from duplicate_finder.application.quarantine import MoveToQuarantine
from duplicate_finder.application.report import ExportReport
from duplicate_finder.application.scan_duplicates import ScanDuplicates
from duplicate_finder.application.settings import AppSettings
from duplicate_finder.application.start_selection import StartSelection


@dataclass
class Services:
    scan_duplicates: ScanDuplicates
    find_similar_photos: FindSimilarPhotos
    start_selection: StartSelection
    move_to_quarantine: MoveToQuarantine
    gather: GatherImages
    history: OperationHistory
    export_report: ExportReport
    settings: AppSettings
    log_file_path: Callable[[], Path | None]
    """Where the error log is being written (None if there is no log file)."""
