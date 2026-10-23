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

# It does not touch the user's real data (history, configuration):
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="dup_appdata_")

from tests.check_perceptual import build            # noqa: E402
from ui import styles, icons, similar_photos_tab             # noqa: E402
from ui.main_window import MainWindow                 # noqa: E402
from core.quarantine import move_to_quarantine              # noqa: E402
from core.selection import KEEP                        # noqa: E402

R = {}


def main():
    styles.apply_theme()
    tmp = tempfile.mkdtemp(prefix="dup_parui_")
    base = Path(tmp) / "fotos"
    build(base)
    quarantine = Path(tmp) / "CUARENTENA"

    app = MainWindow()
    app._mode = "avanzado"
    app._apply_mode()
    app.geometry("1200x860")
    app.tabs.set(f"{icons.CAT_IMAGES}  Fotos parecidas")
    app.similar.entry_folder.insert(0, str(base))
    app.similar.sensitivity_slider.set(12)

    def when_done():
        if app.similar._selection is None:
            app.after(200, when_done)
            return
        sel = app.similar._selection
        res = app.similar._result
        R["grupos"] = res.total_groups
        R["tiles"] = len(app.similar._tiles)
        R["errores"] = len(res.errors)

        # the "playa" group must have 5 photos and the best one marked to keep
        beach_gi = next(
            i for i, g in enumerate(res.groups)
            if any("playa_original" in a.path for a in g.files))
        g = res.groups[beach_gi]
        R["playa_5"] = g.count == 5
        R["mejor_es_png"] = g.files[0].path.endswith("playa_original.png")
        R["mejor_conservar"] = sel.decision(beach_gi, g.files[0].path) == KEEP
        R["resto_mover"] = all(
            sel.decision(beach_gi, a.path) != KEEP for a in g.files[1:])

        # manual toggle: choose another one as the one to keep
        other = g.files[1].path
        app.similar._choose_keep(beach_gi, other)
        R["toggle_ok"] = (
            sel.decision(beach_gi, other) == KEEP
            and sel.decision(beach_gi, g.files[0].path) != KEEP
            and sel.group_state(beach_gi) == "ok")
        # put the best one back
        app.similar._choose_keep(beach_gi, g.files[0].path)

        R["todo_listo"] = sel.all_ready()
        R["boton_cuarentena"] = str(app.similar.btn_quarantine.cget("state")) == "normal"
        to_move = sel.count_to_move()

        # paged gallery: with 1 group per page there is one page per group, and when
        # changing page only the widgets of the visible page exist.
        p = app.similar
        similar_photos_tab.MAX_GROUPS_PER_PAGE = 1
        p._build_gallery()
        app.update()
        R["paginas"] = len(p._pages) == res.total_groups
        R["pager_visible"] = bool(p.pager.winfo_ismapped())
        R["pag1_tiles"] = {gi for gi, _ in p._tiles} == {0}
        R["pag1_anterior_apagado"] = str(p.btn_page_prev.cget("state")) == "disabled"
        p._change_page(1)
        app.update()
        R["pag2_tiles"] = {gi for gi, _ in p._tiles} == {1}
        R["pag2_siguiente_apagado"] = str(p.btn_page_next.cget("state")) == "disabled"
        p._change_page(1)                       # it is already the last: it does nothing
        R["no_pasa_de_la_ultima"] = p._page == 1
        R["seleccion_intacta"] = sel.decision(beach_gi, g.files[0].path) == KEEP
        R["alto_galeria_ok"] = p.gallery.winfo_reqheight() < 32767
        similar_photos_tab.MAX_GROUPS_PER_PAGE = 40
        p._build_gallery()
        app.update()
        R["una_pagina_sin_pager"] = len(p._pages) == 1 and not p.pager.winfo_ismapped()

        move_res = move_to_quarantine(sel, str(base), str(quarantine))
        R["movidas"] = len(move_res.moved)
        R["movidas_ok"] = len(move_res.moved) == to_move and not move_res.failed
        R["mejor_intacta"] = (base / "playa_original.png").exists()
        R["log"] = bool(move_res.log_path) and Path(move_res.log_path).exists()

        app.after(300, app.destroy)

    app.after(400, app.similar._start)
    app.after(900, when_done)
    app.after(15000, app.destroy)
    app.mainloop()

    for k, v in R.items():
        print(f"  {k:22} {v}")

    ok = (
        R.get("grupos") == 2
        and R.get("tiles") == 7          # 5 playa + 2 montaña
        and R.get("errores") == 1
        and R.get("playa_5") is True
        and R.get("mejor_es_png") is True
        and R.get("mejor_conservar") is True
        and R.get("resto_mover") is True
        and R.get("toggle_ok") is True
        and R.get("todo_listo") is True
        and R.get("boton_cuarentena") is True
        and all(R.get(k) is True for k in (
            "paginas", "pager_visible", "pag1_tiles", "pag1_anterior_apagado",
            "pag2_tiles", "pag2_siguiente_apagado", "no_pasa_de_la_ultima",
            "seleccion_intacta", "alto_galeria_ok", "una_pagina_sin_pager"))
        and R.get("movidas") == 5       # 4 extra playa + 1 montaña
        and R.get("movidas_ok") is True
        and R.get("mejor_intacta") is True
        and R.get("log") is True
    )
    print("\n" + ("HUMO PARECIDAS OK" if ok else "HUMO PARECIDAS FALLA"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
