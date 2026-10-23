"""Puente con pytest: cada suite de esta carpeta aparece como una prueba.

    pytest                          # todo
    pytest -m "not gui"             # solo lógica (rápido, sin ventanas)
    pytest --cov                    # cobertura de core/ (ver pyproject.toml)

Los scripts siguen funcionando solos (`python tests/check_filters.py`) y
con `python tests/run_all.py`; esto solo los ejecuta desde pytest.

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

FOLDER = Path(__file__).resolve().parent

LOGIC = [
    "compare_with_original",      # paridad con el script original
    "check_filters",             # filtro de exclusión + desglose por extensión
    "check_selection",           # conservar/mover, regla de carpeta, validación
    "check_quarantine",          # mover de verdad, log CSV, casos inválidos
    "check_quarantine_folders",  # mueve ARCHIVOS, no carpetas
    "check_perceptual",          # fotos parecidas: agrupación por hash perceptual
    "check_gather",              # "Reunir imágenes": estrategias y reglas
    "check_history",           # historial de operaciones + deshacer
]

WINDOW = [
    "smoke_window",               # ventana de punta a punta (flujo avanzado)
    "smoke_similar",             # pestaña "Fotos parecidas"
    "smoke_simple",              # modo Sencilla / Avanzada
    "smoke_quarantine_ui",         # cuarentena desde la UI: archivos, no carpetas
    "smoke_gather_ui",             # pestaña "Reunir imágenes" + historial + deshacer
    "smoke_logging",              # errores inesperados quedan en el registro
    "smoke_dialogs",              # visor, historial, diálogos, CSV y miniaturas
]


@pytest.fixture(autouse=True)
def clean_env():
    """Algunas suites cambian APPDATA o sys.path; se restaura al terminar."""
    env, path = dict(os.environ), list(sys.path)
    yield
    os.environ.clear()
    os.environ.update(env)
    sys.path[:] = path


@pytest.mark.parametrize("name", LOGIC)
def test_logic(name):
    module = importlib.import_module(f"tests.{name}")
    code = 0
    try:
        module.main()
    except SystemExit as output:
        code = output.code or 0
    assert code == 0, f"{name} terminó con código {code} (mira la salida de arriba)"


@pytest.mark.gui
@pytest.mark.parametrize("name", WINDOW)
def test_window(name, tmp_path):
    # Cada suite corre con su propio APPDATA: nunca toca el historial ni la config reales.
    environment = {**os.environ, "APPDATA": str(tmp_path / "appdata")}
    r = subprocess.run([sys.executable, str(FOLDER / f"{name}.py")],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=300, check=False, env=environment)
    assert r.returncode == 0, f"{name} falló:\n{r.stdout}\n{r.stderr}"
