"""Punto de entrada de la app de duplicados.

    python app.py
"""

import os
import sys

# Permite ejecutar tanto `python app.py` como otros lanzadores.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _asegurar_salidas():
    """Evita que la app se caiga por un simple aviso en el .exe sin consola.

    En un .exe de ventana (sin consola) sys.stdout y sys.stderr valen None. Si
    una librería intenta escribir un aviso (por ejemplo CustomTkinter cuando no
    puede cargar una fuente porque la ruta de la carpeta es demasiado larga),
    daría «'NoneType' object has no attribute 'write'» y la app no abriría.
    Se sustituyen por un destino que descarta lo escrito.
    """
    for nombre in ("stdout", "stderr"):
        if getattr(sys, nombre) is None:
            setattr(sys, nombre, open(os.devnull, "w", encoding="utf-8"))  # noqa: SIM115


_asegurar_salidas()

from core import registro  # noqa: E402

registro.iniciar()              # empieza a anotar en %APPDATA%\BuscadorDuplicados\registro
registro.instalar_ganchos()     # y anota también los errores que nadie ha capturado

from ui.main_window import lanzar  # noqa: E402


if __name__ == "__main__":
    lanzar()
