"""Prueba de humo del modo Sencilla: los controles avanzados se ocultan,
la app preselecciona sola la copia principal de cada grupo y el botón de
cuarentena queda listo sin que el usuario elija nada. Cambiar a Avanzada
vuelve a mostrarlo todo.

    python tests/smoke_simple.py
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# No toca los datos reales del usuario (historial, configuración):
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="dup_appdata_")

from ui import styles                            # noqa: E402
from ui.main_window import MainWindow      # noqa: E402

R = {}


def build(base: Path):
    data = b"foto identica\n" * 50
    (base / "Fotos" / "Backup").mkdir(parents=True)
    (base / "Descargas").mkdir(parents=True)
    (base / "Fotos" / "boda.jpg").write_bytes(data)
    (base / "Fotos" / "Backup" / "boda.jpg").write_bytes(data)
    (base / "Descargas" / "boda (1).jpg").write_bytes(data)
    others = b"otro archivo\n" * 30
    (base / "a.txt").write_bytes(others)
    (base / "Descargas" / "a.txt").write_bytes(others)


def main():
    styles.apply_theme()
    tmp = tempfile.mkdtemp(prefix="dup_senc_")
    base = Path(tmp) / "raiz"
    build(base)

    app = MainWindow()
    app._mode = "sencillo"
    app._apply_mode()
    app.geometry("1200x820")
    app.exact.entry_folder.insert(0, str(base))
    app.update()

    R["opciones_ocultas"] = not app.exact._options_container.winfo_ismapped()
    R["decision_fila_oculta"] = not app.exact.decision_card_row.winfo_ismapped()
    R["btn_tipos_oculto"] = not app.exact.btn_kinds.winfo_ismapped()

    def when_done():
        if app.exact._selection is None:
            app.after(200, when_done)
            return
        sel = app.exact._selection
        R["grupos"] = sel.result.total_groups
        R["todo_listo"] = sel.all_ready()
        R["cuarentena_lista"] = str(app.exact.btn_quarantine.cget("state")) == "normal"
        R["a_mover"] = sel.count_to_move()

        # la copia conservada del grupo de la boda no es la de Backup ni la (1)
        gi = next(i for i, g in enumerate(sel.result.groups)
                  if any("boda" in a.path for a in g.files))
        from core.selection import KEEP
        kept = [a for a in sel.result.groups[gi].files
                      if sel.decision(gi, a.path) == KEEP][0]
        R["principal_ok"] = (Path(kept.path).name == "boda.jpg"
                             and "Backup" not in kept.path)

        # cambiar a Avanzada muestra los controles otra vez
        app._mode = "avanzado"
        app._apply_mode()
        app.update()
        R["opciones_visibles_avanzada"] = app.exact._options_container.winfo_ismapped() == 1
        R["decision_visible_avanzada"] = app.exact.decision_card_row.winfo_ismapped() == 1

        app.after(300, app.destroy)

    app.after(300, app.exact._start_scan)
    app.after(800, when_done)
    app.after(12000, app.destroy)
    app.mainloop()

    for k, v in R.items():
        print(f"  {k:28} {v}")

    ok = (
        R.get("opciones_ocultas") is True
        and R.get("decision_fila_oculta") is True
        and R.get("btn_tipos_oculto") is True
        and R.get("grupos") == 2
        and R.get("todo_listo") is True
        and R.get("cuarentena_lista") is True
        and R.get("a_mover") == 3
        and R.get("principal_ok") is True
        and R.get("opciones_visibles_avanzada") is True
        and R.get("decision_visible_avanzada") is True
    )
    print("\n" + ("HUMO SENCILLA OK" if ok else "HUMO SENCILLA FALLA"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
