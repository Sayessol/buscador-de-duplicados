"""Puente con pytest: cada suite de esta carpeta aparece como una prueba.

    pytest                          # todo
    pytest -m "not gui"             # solo lógica (rápido, sin ventanas)
    pytest --cov                    # cobertura de core/ (ver pyproject.toml)

Los scripts siguen funcionando solos (`python pruebas/probar_filtros.py`) y
con `python pruebas/todas.py`; esto solo los ejecuta desde pytest.

· Suites de lógica -> se importan y se llama a su main() DENTRO del proceso,
  así pytest-cov puede medir qué líneas de core/ se ejecutan.
· Suites con ventana (humo_*) -> un proceso aparte cada una: Tkinter no
  lleva bien crear y destruir varias ventanas principales en el mismo proceso.
"""

import importlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

CARPETA = Path(__file__).resolve().parent

LOGICA = [
    "comparar_con_original",      # paridad con el script original
    "probar_filtros",             # filtro de exclusión + desglose por extensión
    "probar_seleccion",           # conservar/mover, regla de carpeta, validación
    "probar_cuarentena",          # mover de verdad, log CSV, casos inválidos
    "probar_cuarentena_carpetas",  # mueve ARCHIVOS, no carpetas
    "probar_perceptual",          # fotos parecidas: agrupación por hash perceptual
    "probar_reunir",              # "Reunir imágenes": estrategias y reglas
    "probar_historial",           # historial de operaciones + deshacer
]

VENTANA = [
    "humo_ventana",               # ventana de punta a punta (flujo avanzado)
    "humo_parecidas",             # pestaña "Fotos parecidas"
    "humo_sencilla",              # modo Sencilla / Avanzada
    "humo_cuarentena_ui",         # cuarentena desde la UI: archivos, no carpetas
    "humo_reunir_ui",             # pestaña "Reunir imágenes" + historial + deshacer
    "humo_registro",              # errores inesperados quedan en el registro
    "humo_dialogos",              # visor, historial, diálogos, CSV y miniaturas
]


@pytest.fixture(autouse=True)
def entorno_limpio():
    """Algunas suites cambian APPDATA o sys.path; se restaura al terminar."""
    env, ruta = dict(os.environ), list(sys.path)
    yield
    os.environ.clear()
    os.environ.update(env)
    sys.path[:] = ruta


@pytest.mark.parametrize("nombre", LOGICA)
def test_logica(nombre):
    modulo = importlib.import_module(f"pruebas.{nombre}")
    codigo = 0
    try:
        modulo.main()
    except SystemExit as salida:
        codigo = salida.code or 0
    assert codigo == 0, f"{nombre} terminó con código {codigo} (mira la salida de arriba)"


@pytest.mark.gui
@pytest.mark.parametrize("nombre", VENTANA)
def test_ventana(nombre, tmp_path):
    # Cada suite corre con su propio APPDATA: nunca toca el historial ni la config reales.
    entorno = {**os.environ, "APPDATA": str(tmp_path / "appdata")}
    r = subprocess.run([sys.executable, str(CARPETA / f"{nombre}.py")],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=300, check=False, env=entorno)
    assert r.returncode == 0, f"{nombre} falló:\n{r.stdout}\n{r.stderr}"
