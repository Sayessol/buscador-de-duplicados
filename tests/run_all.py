"""Runs all the tests from the console, one after another.

    python tests/run_all.py
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

TESTS = [
    "compare_with_original.py",   # parity with the original script
    "check_filters.py",          # exclusion filter + breakdown by extension
    "check_selection.py",        # keep/move, folder rule, validation
    "check_quarantine.py",       # really moves, CSV log, invalid cases
    "check_quarantine_folders.py",  # moves FILES, not folders (subfolders)
    "check_perceptual.py",       # similar photos: grouping by perceptual hash
    "check_gather.py",           # "Gather images" tab: strategies and rules
    "check_history.py",        # operation history + undo
    "smoke_window.py",            # window assembly from end to end
    "smoke_similar.py",          # "Similar photos" tab from end to end
    "smoke_simple.py",           # Simple / Advanced mode
    "smoke_quarantine_ui.py",      # move to quarantine from the UI: files, not folders
    "smoke_gather_ui.py",          # "Gather images" tab + history + undo
    "smoke_logging.py",           # unexpected errors end up in the log
    "smoke_dialogs.py",           # viewer, history, dialogs, CSV and thumbnails
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
        print("TESTS THAT FAILED:", ", ".join(failures))
        sys.exit(1)
    print("ALL TESTS PASSED")


if __name__ == "__main__":
    main()
