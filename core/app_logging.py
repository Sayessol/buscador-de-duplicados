"""Registro de errores en un archivo, para saber qué falló cuando algo va mal.

La app, empaquetada como .exe, no tiene consola: si algo falla, el mensaje
desaparecía. Aquí se guarda en un archivo de texto que se puede abrir con el
Bloc de notas:

    %APPDATA%\\BuscadorDuplicados\\registro\\buscador.log

(o en ~/.buscador_duplicados/registro/ si no hay APPDATA). El archivo es
pequeño: al llegar a 512 KB se archiva y se conservan 2 copias antiguas.

Cómo se usa desde el resto del código:

    from core.app_logging import log
    log.info("algo normal pero útil")
    log.warning("algo raro, la app sigue", exc_info=True)   # añade el traceback
    log.exception("algo falló")                             # dentro de un except

Si no se puede crear el archivo (disco de solo lectura, etc.), la app sigue
funcionando igual, simplemente sin registro.
"""

import logging
import os
import sys
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path
from types import TracebackType

from . import __version__

# Logger común de toda la app. Sin configurar (en las pruebas, por ejemplo) no escribe nada.
log = logging.getLogger("buscador")
log.addHandler(logging.NullHandler())

_MAX_SIZE = 512 * 1024
_OLD_COPIES = 2

_handler: RotatingFileHandler | None = None   # el que escribe en el archivo (None = no iniciado)
_path_file: Path | None = None               # ruta del archivo, si se pudo crear


def log_folder() -> Path:
    base = os.environ.get("APPDATA")
    if base:
        return Path(base) / "BuscadorDuplicados" / "registro"
    return Path.home() / ".buscador_duplicados" / "registro"


def file_path() -> Path | None:
    """Ruta del archivo de registro, o None si no está activo."""
    return _path_file


def start() -> Path | None:
    """Activa el registro en archivo. Se puede llamar varias veces sin duplicar nada.

    Nivel normal: INFO. Con la variable de entorno BUSCADOR_DEBUG=1 se anotan
    también los detalles (DEBUG), útil para investigar un problema.
    """
    global _handler, _path_file
    if _handler is not None:
        return _path_file
    log.setLevel(logging.DEBUG if os.environ.get("BUSCADOR_DEBUG") else logging.INFO)
    try:
        folder = log_folder()
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "buscador.log"
        handler = RotatingFileHandler(
            path, maxBytes=_MAX_SIZE, backupCount=_OLD_COPIES, encoding="utf-8")
    except OSError:
        return None          # sin registro: la app sigue funcionando igual
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)-8s %(message)s", "%Y-%m-%d %H:%M:%S"))
    log.addHandler(handler)
    _handler, _path_file = handler, path
    log.info("Arranca Buscador de duplicados %s (Python %s)",
             __version__, sys.version.split()[0])
    return path


def stop() -> None:
    """Cierra el archivo de registro (lo usan las pruebas y al cerrar la app)."""
    global _handler, _path_file
    if _handler is not None:
        log.removeHandler(_handler)
        _handler.close()
    _handler = _path_file = None


def install_hooks() -> None:
    """Anota también los errores que nadie ha capturado (hilo principal y otros hilos)."""
    previous_primary = sys.excepthook
    previous_thread_hook = threading.excepthook

    def primary(kind: type[BaseException], value: BaseException,
                  trace: TracebackType | None) -> None:
        log.critical("Error no controlado", exc_info=(kind, value, trace))
        previous_primary(kind, value, trace)

    def threads(args: threading.ExceptHookArgs) -> None:
        info = ((args.exc_type, args.exc_value, args.exc_traceback)
                if args.exc_value is not None else None)
        log.critical("Error no controlado en el hilo %s", getattr(args.thread, "name", "?"),
                     exc_info=info)
        previous_thread_hook(args)

    sys.excepthook = primary
    threading.excepthook = threads
