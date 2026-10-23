"""The composition root: the only place that knows every layer.

It builds the use cases with the real infrastructure (the disk, Pillow, the JSON files) and starts
the interface. Nothing else in the package creates an adapter.
"""

from duplicate_finder.application.file_transfers import FileTransfers
from duplicate_finder.application.find_similar_photos import FindSimilarPhotos
from duplicate_finder.application.gather import GatherImages
from duplicate_finder.application.history import OperationHistory
from duplicate_finder.application.quarantine import MoveToQuarantine
from duplicate_finder.application.report import ExportReport
from duplicate_finder.application.scan_duplicates import ScanDuplicates
from duplicate_finder.application.services import Services
from duplicate_finder.application.settings import AppSettings
from duplicate_finder.application.start_selection import StartSelection
from duplicate_finder.infrastructure import app_logging
from duplicate_finder.infrastructure.hashing import Blake2Hasher
from duplicate_finder.infrastructure.history_store import JsonHistoryStore
from duplicate_finder.infrastructure.image_fingerprints import PillowFingerprintReader
from duplicate_finder.infrastructure.local_file_system import LocalFileSystem
from duplicate_finder.infrastructure.settings import JsonSettingsStore


def build_services() -> Services:
    """The use cases wired with the real disk, hashes, images and files of the user."""
    fs = LocalFileSystem()
    history = OperationHistory(JsonHistoryStore(), fs)
    return Services(
        scan_duplicates=ScanDuplicates(fs, Blake2Hasher()),
        find_similar_photos=FindSimilarPhotos(fs, PillowFingerprintReader()),
        start_selection=StartSelection(fs),
        move_to_quarantine=MoveToQuarantine(fs, history),
        gather=GatherImages(fs, FileTransfers(fs), history),
        history=history,
        export_report=ExportReport(fs),
        settings=AppSettings(JsonSettingsStore()),
        log_file_path=app_logging.file_path,
    )


def main() -> None:
    """Starts the app: logging first, then the window."""
    app_logging.start()               # logging to %APPDATA%\\BuscadorDuplicados\\logs
    app_logging.install_hooks()       # and also log the errors nobody has caught

    from duplicate_finder.presentation.main_window import launch
    launch(build_services())
