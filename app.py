"""Entry point of the duplicates app.

    python app.py            (or  python -m duplicate_finder  with src/ on the path)
"""

import os
import sys

# The package lives in src/: this launcher makes `python app.py` work without installing it.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))


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

from duplicate_finder.__main__ import main  # noqa: E402

if __name__ == "__main__":
    main()
