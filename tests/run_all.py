"""Corre todas las pruebas por consola, una detrás de otra.

    python tests/run_all.py
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

TESTS = [
    "compare_with_original.py",   # paridad con el script original
    "check_filters.py",          # filtro de exclusión + desglose por extensión
    "check_selection.py",        # conservar/mover, regla de carpeta, validación
    "check_quarantine.py",       # mover de verdad, log CSV, casos inválidos
    "check_quarantine_folders.py",  # mueve ARCHIVOS, no carpetas (subcarpetas)
    "check_perceptual.py",       # fotos parecidas: agrupación por hash perceptual
    "check_gather.py",           # pestaña "Reunir imágenes": estrategias y reglas
    "check_history.py",        # historial de operaciones + deshacer
    "smoke_window.py",            # montaje de la ventana de punta a punta
    "smoke_similar.py",          # pestaña "Fotos parecidas" de punta a punta
    "smoke_simple.py",           # modo Sencilla / Avanzada
    "smoke_quarantine_ui.py",      # mover a cuarentena desde la UI: archivos, no carpetas
    "smoke_gather_ui.py",          # pestaña "Reunir imágenes" + historial + deshacer
    "smoke_logging.py",           # errores inesperados quedan en el registro
    "smoke_dialogs.py",           # visor, historial, diálogos, CSV y miniaturas
]


def main():
    folder = Path(__file__).resolve().parent
    failures = []
    for name in TESTS:
        print(f"\n{'=' * 60}\n  {name}\n{'=' * 60}")
        environment = {**os.environ, "APPDATA": tempfile.mkdtemp(prefix="dup_appdata_")}
        r = subprocess.run([sys.executable, str(folder / name)], env=environment, check=False)
        if r.returncode != 0:
            failures.append(name)

    print(f"\n{'=' * 60}")
    if failures:
        print("PRUEBAS QUE FALLARON:", ", ".join(failures))
        sys.exit(1)
    print("TODAS LAS PRUEBAS PASARON")


if __name__ == "__main__":
    main()
