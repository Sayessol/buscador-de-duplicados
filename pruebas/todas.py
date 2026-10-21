"""Corre todas las pruebas por consola, una detrás de otra.

    python pruebas/todas.py
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

PRUEBAS = [
    "comparar_con_original.py",   # paridad con el script original
    "probar_filtros.py",          # filtro de exclusión + desglose por extensión
    "probar_seleccion.py",        # conservar/mover, regla de carpeta, validación
    "probar_cuarentena.py",       # mover de verdad, log CSV, casos inválidos
    "probar_cuarentena_carpetas.py",  # mueve ARCHIVOS, no carpetas (subcarpetas)
    "probar_perceptual.py",       # fotos parecidas: agrupación por hash perceptual
    "probar_reunir.py",           # pestaña "Reunir imágenes": estrategias y reglas
    "probar_historial.py",        # historial de operaciones + deshacer
    "humo_ventana.py",            # montaje de la ventana de punta a punta
    "humo_parecidas.py",          # pestaña "Fotos parecidas" de punta a punta
    "humo_sencilla.py",           # modo Sencilla / Avanzada
    "humo_cuarentena_ui.py",      # mover a cuarentena desde la UI: archivos, no carpetas
    "humo_reunir_ui.py",          # pestaña "Reunir imágenes" + historial + deshacer
    "humo_registro.py",           # errores inesperados quedan en el registro
    "humo_dialogos.py",           # visor, historial, diálogos, CSV y miniaturas
]


def main():
    carpeta = Path(__file__).resolve().parent
    fallos = []
    for nombre in PRUEBAS:
        print(f"\n{'=' * 60}\n  {nombre}\n{'=' * 60}")
        entorno = {**os.environ, "APPDATA": tempfile.mkdtemp(prefix="dup_appdata_")}
        r = subprocess.run([sys.executable, str(carpeta / nombre)], env=entorno, check=False)
        if r.returncode != 0:
            fallos.append(nombre)

    print(f"\n{'=' * 60}")
    if fallos:
        print("PRUEBAS QUE FALLARON:", ", ".join(fallos))
        sys.exit(1)
    print("TODAS LAS PRUEBAS PASARON")


if __name__ == "__main__":
    main()
