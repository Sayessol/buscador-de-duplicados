"""Error log in a file, to know what failed when something goes wrong.

The app, packaged as an .exe, has no console: if something failed, the message
used to disappear. Here it is saved in a text file that can be opened with
Notepad:

    %APPDATA%\\BuscadorDuplicados\\logs\\app.log

(or in ~/.buscador_duplicados/logs/ when there is no APPDATA). The file is
small: when it reaches 512 KB it is archived and 2 old copies are kept.

How it is used from the rest of the code:

    from duplicate_finder.infrastructure.app_logging import log
    log.info("something normal but useful")
    log.warning("something odd, the app carries on", exc_info=True)   # adds the traceback
    log.exception("something failed")                                 # inside an except

If the file cannot be created (read-only disk, etc.), the app keeps
working the same, just without a log.
"""

import logging
import os
import sys
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path
from types import TracebackType

from duplicate_finder import __version__
from duplicate_finder.infrastructure.data_folder import data_folder

# Shared logger of the whole app. Unconfigured (in the tests, for example) it writes nothing.
log = logging.getLogger("duplicate_finder")
log.addHandler(logging.NullHandler())

_MAX_SIZE = 512 * 1024
_OLD_COPIES = 2

_handler: RotatingFileHandler | None = None  # the one that writes to the file (None = not started)
_path_file: Path | None = None  # path of the file, if it could be created


def log_folder() -> Path:
    return data_folder() / "logs"


def file_path() -> Path | None:
    """Path of the log file, or None if it is not active."""
    return _path_file


def start() -> Path | None:
    """Turns on logging to a file. It can be called several times without duplicating anything.

    Normal level: INFO. With the environment variable DUPLICATE_FINDER_DEBUG=1 (the old name
    BUSCADOR_DEBUG still works) the details (DEBUG) are logged too, which is useful to
    investigate a problem.
    """
    global _handler, _path_file
    if _handler is not None:
        return _path_file
    debug = os.environ.get("DUPLICATE_FINDER_DEBUG") or os.environ.get("BUSCADOR_DEBUG")
    log.setLevel(logging.DEBUG if debug else logging.INFO)
    try:
        folder = log_folder()
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "app.log"
        handler = RotatingFileHandler(
            path, maxBytes=_MAX_SIZE, backupCount=_OLD_COPIES, encoding="utf-8"
        )
    except OSError:
        return None  # no log: the app keeps working the same
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-8s %(message)s", "%Y-%m-%d %H:%M:%S")
    )
    log.addHandler(handler)
    _handler, _path_file = handler, path
    log.info("Starting Duplicate Finder %s (Python %s)", __version__, sys.version.split()[0])
    return path


def stop() -> None:
    """Closes the log file (used by the tests and when the app closes)."""
    global _handler, _path_file
    if _handler is not None:
        log.removeHandler(_handler)
        _handler.close()
    _handler = _path_file = None


def install_hooks() -> None:
    """Also logs the errors nobody has caught (main thread and other threads)."""
    previous_primary = sys.excepthook
    previous_thread_hook = threading.excepthook

    def primary(
        kind: type[BaseException], value: BaseException, trace: TracebackType | None
    ) -> None:
        log.critical("Unhandled error", exc_info=(kind, value, trace))
        previous_primary(kind, value, trace)

    def threads(args: threading.ExceptHookArgs) -> None:
        info = (
            (args.exc_type, args.exc_value, args.exc_traceback)
            if args.exc_value is not None
            else None
        )
        log.critical(
            "Unhandled error in thread %s", getattr(args.thread, "name", "?"), exc_info=info
        )
        previous_thread_hook(args)

    sys.excepthook = primary
    threading.excepthook = threads
