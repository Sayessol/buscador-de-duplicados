"""Prueba de humo de la ventana: la abre, escanea un árbol de prueba,
ejercita el panel de filtros, el desglose por tipos y la decisión
conservar/mover (regla automática + validación), y cierra sola.

No requiere interacción.

    python tests/smoke_window.py
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# No toca los datos reales del usuario (historial, configuración):
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="dup_appdata_")

from tests.compare_with_original import build_test_tree  # noqa: E402
from ui import styles  # noqa: E402
from ui.main_window import MainWindow  # noqa: E402
from ui.extension_breakdown_dialog import ExtensionBreakdownWindow  # noqa: E402

R = {}


def main():
    styles.apply_theme()

    tmp = tempfile.mkdtemp(prefix="dup_humo_")
    base = Path(tmp) / "arbol"
    build_test_tree(base)
    csv_output = Path(tmp) / "reporte.csv"

    quarantine = Path(tmp) / "CUARENTENA"

    app = MainWindow()
    app._mode = "avanzado"         # esta prueba ejercita el flujo avanzado
    app._apply_mode()           # (sin persistir en la config real)
    app.exact.entry_folder.insert(0, str(base))
    app.exact._empty_filters()          # sin exclusiones -> 4 grupos
    preferred_folder = str(base / "originales")  # contiene una copia del grupo doc.txt

    def when_done():
        if app.exact._selection is None:
            app.after(150, when_done)
            return
        sel = app.exact._selection
        R["grupos"] = sel.result.total_groups
        R["nodos_tabla"] = len(app.exact.table.tree.get_children())
        R["pendientes_inicio"] = len(sel.pending_groups())
        button_state = str(app.exact.btn_quarantine.cget("state"))
        R["cuarentena_bloqueada_inicio"] = button_state == "disabled"

        # Poner la carpeta preferida (ya habilitada tras el escaneo) y aplicar regla
        app.exact.entry_preferred_folder.delete(0, "end")
        app.exact.entry_preferred_folder.insert(0, preferred_folder)
        assert app.exact.entry_preferred_folder.get() == preferred_folder
        resolved, unmatched = sel.apply_folder_rule(app.exact.entry_preferred_folder.get())
        app.exact.table.refresh_all()
        app.exact._on_selection_change()
        R["resueltos_regla"] = resolved
        R["sin_coincidencia"] = unmatched
        R["pendientes_tras_regla"] = len(sel.pending_groups())

        # Resolver a mano lo que quede
        for gi in list(sel.pending_groups()):
            first = sel.result.groups[gi].files[0].path
            sel.keep_only(gi, first)
        app.exact.table.refresh_all()
        app.exact._on_selection_change()
        R["todo_listo"] = sel.all_ready()
        R["cuarentena_habilitada_final"] = str(app.exact.btn_quarantine.cget("state")) == "normal"
        R["a_mover"] = sel.count_to_move()

        from core.report import export_csv
        R["grupos_csv"] = export_csv(sel.result, str(csv_output))

        # Mover a cuarentena de verdad (misma lógica que usa el botón)
        from core.quarantine import move_to_quarantine
        to_move_before = sel.count_to_move()
        res = move_to_quarantine(sel, app.exact._scanned_folder, str(quarantine))
        R["movidos"] = len(res.moved)
        R["movidos_ok"] = (len(res.moved) == to_move_before and not res.failed)
        R["log_existe"] = bool(res.log_path) and Path(res.log_path).exists()
        R["conservados_intactos"] = (base / "originales" / "doc.txt").exists()
        R["movido_en_cuarentena"] = any(quarantine.rglob("img.dat"))

        app.exact._toggle_options()

        # Categorías rápidas: marcar "Imágenes" rellena el campo y el filtro
        app.exact._empty_filters()
        app.exact.chk_categories["Imágenes"].select()
        app.exact._toggle_category("Imágenes")
        incl = app.exact._current_filter().included_extensions
        R["cat_imagenes_jpg"] = "jpg" in incl and "png" in incl
        R["cat_imagenes_no_mp3"] = "mp3" not in incl
        app.exact.chk_categories["Audio"].select()
        app.exact._toggle_category("Audio")
        R["cat_combina_audio"] = "mp3" in app.exact._current_filter().included_extensions
        app.exact.chk_categories["Imágenes"].deselect()
        app.exact._toggle_category("Imágenes")
        incl2 = app.exact._current_filter().included_extensions
        R["cat_desmarca_imagenes"] = "jpg" not in incl2 and "mp3" in incl2
        app.exact._empty_filters()
        R["cat_vacio"] = app.exact._current_filter().included_extensions == set()

        top = ExtensionBreakdownWindow(app, sel.result, app.exact._add_extension_to_filter)
        R["extensiones"] = len(sel.result.summary_by_extension())
        app.after(150, top.destroy)
        app.after(400, app.destroy)

    app.after(300, app.exact._start_scan)
    app.after(700, when_done)
    app.after(8000, app.destroy)  # tope de seguridad
    app.mainloop()

    for k, v in R.items():
        print(f"  {k:32} {v}")

    ok = (
        R.get("grupos") == 4
        and R.get("nodos_tabla") == 4
        and R.get("pendientes_inicio") == 4          # todo arranca sin decidir
        and R.get("cuarentena_bloqueada_inicio") is True
        and R.get("resueltos_regla") == 1            # solo el grupo con copia en /originales
        and R.get("pendientes_tras_regla") == 3
        and R.get("todo_listo") is True
        and R.get("cuarentena_habilitada_final") is True
        and R.get("a_mover") == 5                    # 9 duplicados - 4 conservados
        and R.get("grupos_csv") == 4
        and csv_output.exists()
        and R.get("movidos") == 5
        and R.get("movidos_ok") is True
        and R.get("log_existe") is True
        and R.get("conservados_intactos") is True
        and R.get("movido_en_cuarentena") is True
        and R.get("cat_imagenes_jpg") is True
        and R.get("cat_imagenes_no_mp3") is True
        and R.get("cat_combina_audio") is True
        and R.get("cat_desmarca_imagenes") is True
        and R.get("cat_vacio") is True
    )
    print("\n" + ("HUMO OK" if ok else "HUMO FALLA"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
