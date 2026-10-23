"""Entry point of the duplicates app.

    python app.py
"""

import os
import sys

# Allows running both `python app.py` and other launchers.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _ensure_outputs():
    """Keeps the app from crashing over a simple warning in the .exe without a console.

    In a windowed .exe (no console) sys.stdout and sys.stderr are None. If
    a library tries to write a warning (for example CustomTkinter when it
    cannot load a font because the folder path is too long),
    it would raise "'NoneType' object has no attribute 'write'" and the app would not open.
    They are replaced by a destination that discards what is written.
    """
    for name in ("stdout", "stderr"):
        if getattr(sys, name) is None:
            setattr(sys, name, open(os.devnull, "w", encoding="utf-8"))  # noqa: SIM115


_ensure_outputs()

from core import app_logging  # noqa: E402

app_logging.start()              # starts logging to %APPDATA%\BuscadorDuplicados\registro
app_logging.install_hooks()     # and also log the errors nobody has caught

from ui.main_window import launch  # noqa: E402


if __name__ == "__main__":
    launch()
