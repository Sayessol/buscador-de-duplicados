"""Punto de entrada de la app de duplicados.

    python app.py
"""

import os
import sys

# Permite ejecutar tanto `python app.py` como otros lanzadores.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _ensure_outputs():
    """Evita que la app se caiga por un simple aviso en el .exe sin consola.

    En un .exe de ventana (sin consola) sys.stdout y sys.stderr valen None. Si
    una librería intenta escribir un aviso (por ejemplo CustomTkinter cuando no
    puede cargar una fuente porque la ruta de la carpeta es demasiado larga),
    daría «'NoneType' object has no attribute 'write'» y la app no abriría.
    Se sustituyen por un destino que descarta lo escrito.
    """
    for name in ("stdout", "stderr"):
        if getattr(sys, name) is None:
            setattr(sys, name, open(os.devnull, "w", encoding="utf-8"))  # noqa: SIM115


_ensure_outputs()

from core import app_logging  # noqa: E402

app_logging.start()              # empieza a anotar en %APPDATA%\BuscadorDuplicados\registro
app_logging.install_hooks()     # y anota también los errores que nadie ha capturado

from ui.main_window import launch  # noqa: E402


if __name__ == "__main__":
    launch()
