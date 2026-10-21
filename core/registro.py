"""Registro de errores en un archivo, para saber qué falló cuando algo va mal.

La app, empaquetada como .exe, no tiene consola: si algo falla, el mensaje
desaparecía. Aquí se guarda en un archivo de texto que se puede abrir con el
Bloc de notas:

    %APPDATA%\\BuscadorDuplicados\\registro\\buscador.log

(o en ~/.buscador_duplicados/registro/ si no hay APPDATA). El archivo es
pequeño: al llegar a 512 KB se archiva y se conservan 2 copias antiguas.

Cómo se usa desde el resto del código:

    from core.registro import log
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

_TAMANO_MAXIMO = 512 * 1024
_COPIAS_ANTIGUAS = 2

_manejador: RotatingFileHandler | None = None   # el que escribe en el archivo (None = no iniciado)
_ruta_archivo: Path | None = None               # ruta del archivo, si se pudo crear


def carpeta_registro() -> Path:
    base = os.environ.get("APPDATA")
    if base:
        return Path(base) / "BuscadorDuplicados" / "registro"
    return Path.home() / ".buscador_duplicados" / "registro"


def ruta_archivo() -> Path | None:
    """Ruta del archivo de registro, o None si no está activo."""
    return _ruta_archivo


def iniciar() -> Path | None:
    """Activa el registro en archivo. Se puede llamar varias veces sin duplicar nada.

    Nivel normal: INFO. Con la variable de entorno BUSCADOR_DEBUG=1 se anotan
    también los detalles (DEBUG), útil para investigar un problema.
    """
    global _manejador, _ruta_archivo
    if _manejador is not None:
        return _ruta_archivo
    log.setLevel(logging.DEBUG if os.environ.get("BUSCADOR_DEBUG") else logging.INFO)
    try:
        carpeta = carpeta_registro()
        carpeta.mkdir(parents=True, exist_ok=True)
        ruta = carpeta / "buscador.log"
        manejador = RotatingFileHandler(
            ruta, maxBytes=_TAMANO_MAXIMO, backupCount=_COPIAS_ANTIGUAS, encoding="utf-8")
    except OSError:
        return None          # sin registro: la app sigue funcionando igual
    manejador.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)-8s %(message)s", "%Y-%m-%d %H:%M:%S"))
    log.addHandler(manejador)
    _manejador, _ruta_archivo = manejador, ruta
    log.info("Arranca Buscador de duplicados %s (Python %s)",
             __version__, sys.version.split()[0])
    return ruta


def detener() -> None:
    """Cierra el archivo de registro (lo usan las pruebas y al cerrar la app)."""
    global _manejador, _ruta_archivo
    if _manejador is not None:
        log.removeHandler(_manejador)
        _manejador.close()
    _manejador = _ruta_archivo = None


def instalar_ganchos() -> None:
    """Anota también los errores que nadie ha capturado (hilo principal y otros hilos)."""
    anterior_principal = sys.excepthook
    anterior_hilos = threading.excepthook

    def principal(tipo: type[BaseException], valor: BaseException,
                  traza: TracebackType | None) -> None:
        log.critical("Error no controlado", exc_info=(tipo, valor, traza))
        anterior_principal(tipo, valor, traza)

    def hilos(args: threading.ExceptHookArgs) -> None:
        info = ((args.exc_type, args.exc_value, args.exc_traceback)
                if args.exc_value is not None else None)
        log.critical("Error no controlado en el hilo %s", getattr(args.thread, "name", "?"),
                     exc_info=info)
        anterior_hilos(args)

    sys.excepthook = principal
    threading.excepthook = hilos
