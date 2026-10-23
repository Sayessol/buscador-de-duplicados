"""Bridge to pytest: each suite in this folder shows up as one test.

    pytest                          # everything
    pytest -m "not gui"             # logic only (fast, no windows)
    pytest --cov                    # coverage of the package (see pyproject.toml)

The scripts still work on their own (`python tests/check_filters.py`) and
with `python tests/run_all.py`; this only runs them from pytest.

· Logic suites -> imported and their main() is called INSIDE the process,
  so pytest-cov can measure which lines of the package run.
· Window suites (smoke_*) -> a separate process each: Tkinter does not
  cope well with creating and destroying several main windows in the same process.
"""

import importlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

FOLDER = Path(__file__).resolve().parent

LOGIC = [
    "compare_with_original",      # parity with the original script
    "check_filters",             # exclusion filter + breakdown by extension
    "check_selection",           # keep/move, folder rule, validation
    "check_quarantine",          # really moves, CSV log, invalid cases
    "check_quarantine_folders",  # moves FILES, not folders
    "check_perceptual",          # similar photos: grouping by perceptual hash
    "check_gather",              # "Gather images": strategies and rules
    "check_history",           # operation history + undo
]

WINDOW = [
    "smoke_window",               # window from end to end (advanced flow)
    "smoke_similar",             # "Similar photos" tab
    "smoke_simple",              # Simple / Advanced mode
    "smoke_quarantine_ui",         # quarantine from the UI: files, not folders
    "smoke_gather_ui",             # "Gather images" tab + history + undo
    "smoke_logging",              # unexpected errors end up in the log
    "smoke_dialogs",              # viewer, history, dialogs, CSV and thumbnails
]


@pytest.fixture(autouse=True)
def clean_env():
    """Some suites change APPDATA or sys.path; it is restored when they finish."""
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
    assert code == 0, f"{name} finished with code {code} (see the output above)"


@pytest.mark.gui
@pytest.mark.parametrize("name", WINDOW)
def test_window(name, tmp_path):
    # Each suite runs with its own APPDATA: it never touches the real history or config.
    environment = {**os.environ, "APPDATA": str(tmp_path / "appdata")}
    r = subprocess.run([sys.executable, str(FOLDER / f"{name}.py")],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=300, check=False, env=environment)
    assert r.returncode == 0, f"{name} failed:\n{r.stdout}\n{r.stderr}"
