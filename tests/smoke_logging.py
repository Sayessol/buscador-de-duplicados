"""Smoke test of the error log with the real window.

It causes two failures and checks that they are recorded in the log file:
  1. an error inside an interface function (a Tkinter timer);
  2. an error in the thread that scans (it is given a folder that does not exist).
And that the warning to the user appears ONLY ONCE even if the failure repeats.

    python tests/smoke_logging.py
"""

import os
import sys
import tempfile
from pathlib import Path
from tkinter import messagebox

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
TMP = Path(tempfile.mkdtemp(prefix="dup_reg_"))
os.environ["APPDATA"] = str(TMP / "appdata")          # does not touch the real log

from duplicate_finder.infrastructure import app_logging  # noqa: E402
from duplicate_finder.domain.filters import ScanFilter  # noqa: E402
from duplicate_finder.presentation import styles  # noqa: E402
from duplicate_finder.presentation.main_window import MainWindow  # noqa: E402

failures = []
warnings = []


def check(cond, msg):
    print(f"  [{'OK  ' if cond else 'FAIL'}] {msg}")
    if not cond:
        failures.append(msg)


def main():
    messagebox.showerror = lambda *a, **k: warnings.append(a)
    styles.apply_theme()
    log_path = app_logging.start()
    check(log_path is not None and log_path.exists(), "the log file is created at start-up")

    app = MainWindow()

    def ui_failure():
        raise RuntimeError("failure triggered in the interface")

    def scan_failure():
        # The same method that runs in the scan thread; with a folder that does not exist.
        app.exact._scan_job(str(TMP / "does_not_exist"), ScanFilter.no_filter())

    app.after(200, ui_failure)
    app.after(300, ui_failure)                 # repeated: it must warn only once
    app.after(400, scan_failure)
    app.after(1200, app.destroy)
    app.mainloop()

    for h in app_logging.log.handlers:
        h.flush()
    text = log_path.read_text(encoding="utf-8")
    check("failure triggered in the interface" in text, "the interface error is in the log")
    check(text.count("Unexpected error in the interface") == 2,
          "both repeated failures are logged")
    check(len(warnings) == 1, "but the warning to the user appears only once")
    check("Scan of" in text and "NotADirectoryError" in text,
          "the scan thread error is in the log, with its traceback")
    check(str(log_path) in warnings[0][1] if warnings else False,
          "the warning says where the log is")

    app_logging.stop()
    print()
    if failures:
        print(f"{len(failures)} CHECKS FAILED.")
        sys.exit(1)
    print("LOG SMOKE OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
