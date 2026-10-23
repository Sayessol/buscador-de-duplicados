"""Window smoke test: opens it, scans a test tree,
exercises the filter panel, the breakdown by kinds and the keep/move
decision (automatic rule + validation), and closes by itself.

It needs no interaction.

    python tests/smoke_window.py
"""

import os
import sys
import tempfile
from pathlib import Path
from tkinter import messagebox

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
# It does not touch the user's real data (history, configuration):
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="dup_appdata_")

from duplicate_finder.infrastructure import settings  # noqa: E402
from tests.compare_with_original import build_test_tree  # noqa: E402
from duplicate_finder.presentation import styles  # noqa: E402
from duplicate_finder.presentation.main_window import MainWindow  # noqa: E402
from duplicate_finder.presentation.extension_breakdown_dialog import ExtensionBreakdownWindow  # noqa: E402

R = {}


def main():
    styles.apply_theme()

    tmp = tempfile.mkdtemp(prefix="dup_humo_")
    base = Path(tmp) / "tree"
    build_test_tree(base)
    csv_output = Path(tmp) / "reporte.csv"

    quarantine = Path(tmp) / "QUARANTINE"

    app = MainWindow()
    app._mode = "advanced"         # this test exercises the advanced flow
    app._apply_mode()           # (without persisting to the real config)
    app.exact.entry_folder.insert(0, str(base))
    app.exact._empty_filters()          # no exclusions -> 4 groups
    preferred_folder = str(base / "originals")  # contains one copy of the doc.txt group

    def when_done():
        if app.exact._selection is None:
            app.after(150, when_done)
            return
        sel = app.exact._selection
        R["groups"] = sel.result.total_groups
        R["table_nodes"] = len(app.exact.table.tree.get_children())
        R["pending_at_start"] = len(sel.pending_groups())
        button_state = str(app.exact.btn_quarantine.cget("state"))
        R["quarantine_locked_at_start"] = button_state == "disabled"

        # Set the preferred folder (already enabled after the scan) and apply the rule
        app.exact.entry_preferred_folder.delete(0, "end")
        app.exact.entry_preferred_folder.insert(0, preferred_folder)
        assert app.exact.entry_preferred_folder.get() == preferred_folder
        resolved, unmatched = sel.apply_folder_rule(app.exact.entry_preferred_folder.get())
        app.exact.table.refresh_all()
        app.exact._on_selection_change()
        R["resolved_by_rule"] = resolved
        R["no_match"] = unmatched
        R["pending_after_rule"] = len(sel.pending_groups())

        # Resolve by hand whatever is left
        for gi in list(sel.pending_groups()):
            first = sel.result.groups[gi].files[0].path
            sel.keep_only(gi, first)
        app.exact.table.refresh_all()
        app.exact._on_selection_change()
        R["all_ready"] = sel.all_ready()
        R["quarantine_enabled_at_end"] = str(app.exact.btn_quarantine.cget("state")) == "normal"
        R["to_move"] = sel.count_to_move()

        from duplicate_finder.application.report import export_csv
        R["csv_groups"] = export_csv(sel.result, str(csv_output))

        # Really move to quarantine (same logic the button uses)
        from duplicate_finder.application.quarantine import move_to_quarantine
        to_move_before = sel.count_to_move()
        res = move_to_quarantine(sel, app.exact._scanned_folder, str(quarantine))
        R["moved"] = len(res.moved)
        R["moved_ok"] = (len(res.moved) == to_move_before and not res.failed)
        R["log_exists"] = bool(res.log_path) and Path(res.log_path).exists()
        R["kept_intact"] = (base / "originals" / "doc.txt").exists()
        R["moved_in_quarantine"] = any(quarantine.rglob("img.dat"))

        app.exact._toggle_options()

        # Quick categories: ticking "Images" fills in the field and the filter
        app.exact._empty_filters()
        app.exact.chk_categories["images"].select()
        app.exact._toggle_category("images")
        incl = app.exact._current_filter().included_extensions
        R["cat_images_jpg"] = "jpg" in incl and "png" in incl
        R["cat_images_no_mp3"] = "mp3" not in incl
        app.exact.chk_categories["audio"].select()
        app.exact._toggle_category("audio")
        R["cat_combines_audio"] = "mp3" in app.exact._current_filter().included_extensions
        app.exact.chk_categories["images"].deselect()
        app.exact._toggle_category("images")
        incl2 = app.exact._current_filter().included_extensions
        R["cat_unticks_images"] = "jpg" not in incl2 and "mp3" in incl2
        app.exact._empty_filters()
        R["cat_empty"] = app.exact._current_filter().included_extensions == set()

        # Header selectors: each choice is saved (the language also warns that it applies later).
        shown = []
        messagebox.showinfo = lambda *a, **k: shown.append(a)
        app._change_language("English")          # already the current one: nothing happens
        R["language_same_is_silent"] = settings.get_language() == "auto" and not shown
        app._change_language("Español")
        R["language_saved"] = settings.get_language() == "es" and len(shown) == 1
        app.theme_selector.set_key("dark")
        app._change_theme(app.theme_selector.get())
        R["theme_saved"] = settings.get_theme() == "dark"
        app.mode_selector.set_key("simple")
        app._change_mode(app.mode_selector.get())
        R["mode_saved"] = settings.get_mode() == "simple"

        top = ExtensionBreakdownWindow(app, sel.result, app.exact._add_extension_to_filter)
        R["extensions"] = len(sel.result.summary_by_extension())
        app.after(150, top.destroy)
        app.after(400, app.destroy)

    app.after(300, app.exact._start_scan)
    app.after(700, when_done)
    app.after(8000, app.destroy)  # safety cap
    app.mainloop()

    for k, v in R.items():
        print(f"  {k:32} {v}")

    ok = (
        R.get("groups") == 4
        and R.get("table_nodes") == 4
        and R.get("pending_at_start") == 4          # everything starts undecided
        and R.get("quarantine_locked_at_start") is True
        and R.get("resolved_by_rule") == 1            # only the group with a copy in /originales
        and R.get("pending_after_rule") == 3
        and R.get("all_ready") is True
        and R.get("quarantine_enabled_at_end") is True
        and R.get("to_move") == 5                    # 9 duplicates - 4 kept
        and R.get("csv_groups") == 4
        and csv_output.exists()
        and R.get("moved") == 5
        and R.get("moved_ok") is True
        and R.get("log_exists") is True
        and R.get("kept_intact") is True
        and R.get("moved_in_quarantine") is True
        and R.get("cat_images_jpg") is True
        and R.get("cat_images_no_mp3") is True
        and R.get("cat_combines_audio") is True
        and R.get("cat_unticks_images") is True
        and R.get("cat_empty") is True
        and R.get("language_same_is_silent") is True
        and R.get("language_saved") is True
        and R.get("theme_saved") is True
        and R.get("mode_saved") is True
    )
    print("\n" + ("SMOKE OK" if ok else "SMOKE FAILED"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
