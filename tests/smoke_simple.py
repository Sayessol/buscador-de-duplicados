"""Smoke test of Simple mode: the advanced controls are hidden,
the app preselects the primary copy of each group by itself and the
quarantine button is ready without the user choosing anything. Switching to Advanced
shows everything again.

    python tests/smoke_simple.py
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# It does not touch the user's real data (history, configuration):
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="dup_appdata_")

from ui import styles                            # noqa: E402
from ui.main_window import MainWindow      # noqa: E402

R = {}


def build(base: Path):
    data = b"photo identica\n" * 50
    (base / "Photos" / "Backup").mkdir(parents=True)
    (base / "Downloads").mkdir(parents=True)
    (base / "Photos" / "wedding.jpg").write_bytes(data)
    (base / "Photos" / "Backup" / "wedding.jpg").write_bytes(data)
    (base / "Downloads" / "wedding (1).jpg").write_bytes(data)
    others = b"otro file\n" * 30
    (base / "a.txt").write_bytes(others)
    (base / "Downloads" / "a.txt").write_bytes(others)


def main():
    styles.apply_theme()
    tmp = tempfile.mkdtemp(prefix="dup_senc_")
    base = Path(tmp) / "root"
    build(base)

    app = MainWindow()
    app._mode = "simple"
    app._apply_mode()
    app.geometry("1200x820")
    app.exact.entry_folder.insert(0, str(base))
    app.update()

    R["options_hidden"] = not app.exact._options_container.winfo_ismapped()
    R["decision_row_hidden"] = not app.exact.decision_card_row.winfo_ismapped()
    R["kinds_button_hidden"] = not app.exact.btn_kinds.winfo_ismapped()

    def when_done():
        if app.exact._selection is None:
            app.after(200, when_done)
            return
        sel = app.exact._selection
        R["groups"] = sel.result.total_groups
        R["all_ready"] = sel.all_ready()
        R["quarantine_ready"] = str(app.exact.btn_quarantine.cget("state")) == "normal"
        R["to_move"] = sel.count_to_move()

        # the copy kept in the "boda" group is neither the Backup one nor the (1) one
        gi = next(i for i, g in enumerate(sel.result.groups)
                  if any("wedding" in a.path for a in g.files))
        from core.selection import KEEP
        kept = [a for a in sel.result.groups[gi].files
                      if sel.decision(gi, a.path) == KEEP][0]
        R["main_ok"] = (Path(kept.path).name == "wedding.jpg"
                             and "Backup" not in kept.path)

        # switching to Advanced shows the controls again
        app._mode = "advanced"
        app._apply_mode()
        app.update()
        R["options_visible_advanced"] = app.exact._options_container.winfo_ismapped() == 1
        R["decision_visible_advanced"] = app.exact.decision_card_row.winfo_ismapped() == 1

        app.after(300, app.destroy)

    app.after(300, app.exact._start_scan)
    app.after(800, when_done)
    app.after(12000, app.destroy)
    app.mainloop()

    for k, v in R.items():
        print(f"  {k:28} {v}")

    ok = (
        R.get("options_hidden") is True
        and R.get("decision_row_hidden") is True
        and R.get("kinds_button_hidden") is True
        and R.get("groups") == 2
        and R.get("all_ready") is True
        and R.get("quarantine_ready") is True
        and R.get("to_move") == 3
        and R.get("main_ok") is True
        and R.get("options_visible_advanced") is True
        and R.get("decision_visible_advanced") is True
    )
    print("\n" + ("SIMPLE SMOKE OK" if ok else "SIMPLE SMOKE FAILED"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
