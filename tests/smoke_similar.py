"""Smoke test of the "Similar photos" tab: opens the window,
generates synthetic photos, switches tab, launches the analysis, waits,
and checks that the gallery fills up, that the keep/move toggle
works and that really moving to quarantine respects the golden rule.

    python tests/smoke_similar.py
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
# It does not touch the user's real data (history, configuration):
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="dup_appdata_")

from duplicate_finder.bootstrap import build_services
from duplicate_finder.presentation import similar_photos_tab, styles
from duplicate_finder.presentation.main_window import MainWindow
from tests.check_perceptual import build

SERVICES = build_services()
from duplicate_finder.domain.selection import KEEP  # noqa: E402

R = {}


def main():
    styles.apply_theme()
    tmp = tempfile.mkdtemp(prefix="dup_parui_")
    base = Path(tmp) / "photos"
    build(base)
    quarantine = Path(tmp) / "QUARANTINE"

    app = MainWindow(SERVICES)
    app._mode = "advanced"
    app._apply_mode()
    app.geometry("1200x860")
    app.show_tab("similar")
    app.similar.entry_folder.insert(0, str(base))
    app.similar.sensitivity_slider.set(12)

    def when_done():
        if app.similar._selection is None:
            app.after(200, when_done)
            return
        sel = app.similar._selection
        res = app.similar._result
        R["groups"] = res.total_groups
        R["tiles"] = len(app.similar._tiles)
        R["errors"] = len(res.errors)

        # the "beach" group must have 5 photos and the best one marked to keep
        beach_gi = next(
            i for i, g in enumerate(res.groups) if any("beach_original" in a.path for a in g.files)
        )
        g = res.groups[beach_gi]
        R["beach_5"] = g.count == 5
        R["best_is_png"] = g.files[0].path.endswith("beach_original.png")
        R["best_keep"] = sel.decision(beach_gi, g.files[0].path) == KEEP
        R["rest_to_move"] = all(sel.decision(beach_gi, a.path) != KEEP for a in g.files[1:])

        # manual toggle: choose another one as the one to keep
        other = g.files[1].path
        app.similar._choose_keep(beach_gi, other)
        R["toggle_ok"] = (
            sel.decision(beach_gi, other) == KEEP
            and sel.decision(beach_gi, g.files[0].path) != KEEP
            and sel.group_state(beach_gi) == "ok"
        )
        # put the best one back
        app.similar._choose_keep(beach_gi, g.files[0].path)

        R["all_ready"] = sel.all_ready()
        R["quarantine_button"] = str(app.similar.btn_quarantine.cget("state")) == "normal"
        to_move = sel.count_to_move()

        # paged gallery: with 1 group per page there is one page per group, and when
        # changing page only the widgets of the visible page exist.
        p = app.similar
        similar_photos_tab.MAX_GROUPS_PER_PAGE = 1
        p._build_gallery()
        app.update()
        R["pages"] = len(p._pages) == res.total_groups
        R["pager_visible"] = bool(p.pager.winfo_ismapped())
        R["pag1_tiles"] = {gi for gi, _ in p._tiles} == {0}
        R["page1_previous_off"] = str(p.btn_page_prev.cget("state")) == "disabled"
        p._change_page(1)
        app.update()
        R["pag2_tiles"] = {gi for gi, _ in p._tiles} == {1}
        R["page2_next_off"] = str(p.btn_page_next.cget("state")) == "disabled"
        p._change_page(1)  # it is already the last: it does nothing
        R["does_not_pass_the_last"] = p._page == 1
        R["selection_intact"] = sel.decision(beach_gi, g.files[0].path) == KEEP
        R["gallery_height_ok"] = p.gallery.winfo_reqheight() < 32767
        similar_photos_tab.MAX_GROUPS_PER_PAGE = 40
        p._build_gallery()
        app.update()
        R["one_page_no_pager"] = len(p._pages) == 1 and not p.pager.winfo_ismapped()

        move_res = SERVICES.move_to_quarantine(sel, str(base), str(quarantine))
        R["moved_photos"] = len(move_res.moved)
        R["moved_photos_ok"] = len(move_res.moved) == to_move and not move_res.failed
        R["best_intact"] = (base / "beach_original.png").exists()
        R["log"] = bool(move_res.log_path) and Path(move_res.log_path).exists()

        app.after(300, app.destroy)

    app.after(400, app.similar._start)
    app.after(900, when_done)
    app.after(15000, app.destroy)
    app.mainloop()

    for k, v in R.items():
        print(f"  {k:22} {v}")

    ok = (
        R.get("groups") == 2
        and R.get("tiles") == 7  # 5 beach + 2 mountain
        and R.get("errors") == 1
        and R.get("beach_5") is True
        and R.get("best_is_png") is True
        and R.get("best_keep") is True
        and R.get("rest_to_move") is True
        and R.get("toggle_ok") is True
        and R.get("all_ready") is True
        and R.get("quarantine_button") is True
        and all(
            R.get(k) is True
            for k in (
                "pages",
                "pager_visible",
                "pag1_tiles",
                "page1_previous_off",
                "pag2_tiles",
                "page2_next_off",
                "does_not_pass_the_last",
                "selection_intact",
                "gallery_height_ok",
                "one_page_no_pager",
            )
        )
        and R.get("moved_photos") == 5  # 4 extra beach + 1 mountain
        and R.get("moved_photos_ok") is True
        and R.get("best_intact") is True
        and R.get("log") is True
    )
    print("\n" + ("SIMILAR SMOKE OK" if ok else "SIMILAR SMOKE FAILED"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
