"""Prueba de humo de la ventana: la abre, escanea un árbol de prueba,
ejercita el panel de filtros, el desglose por tipos y la decisión
conservar/mover (regla automática + validación), y cierra sola.

No requiere interacción.

    python pruebas/humo_ventana.py
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# No toca los datos reales del usuario (historial, configuración):
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="dup_appdata_")

from pruebas.comparar_con_original import construir_arbol_de_prueba  # noqa: E402
from ui import styles  # noqa: E402
from ui.main_window import VentanaPrincipal  # noqa: E402
from ui.tipos_duplicados_dialog import VentanaTipos  # noqa: E402

R = {}


def main():
    styles.aplicar_tema()

    tmp = tempfile.mkdtemp(prefix="dup_humo_")
    base = Path(tmp) / "arbol"
    construir_arbol_de_prueba(base)
    csv_salida = Path(tmp) / "reporte.csv"

    cuarentena = Path(tmp) / "CUARENTENA"

    app = VentanaPrincipal()
    app._modo = "avanzado"         # esta prueba ejercita el flujo avanzado
    app._aplicar_modo()           # (sin persistir en la config real)
    app.exactos.entry_carpeta.insert(0, str(base))
    app.exactos._filtros_vacios()          # sin exclusiones -> 4 grupos
    carpeta_buena = str(base / "originales")  # contiene una copia del grupo doc.txt

    def cuando_termine():
        if app.exactos._seleccion is None:
            app.after(150, cuando_termine)
            return
        sel = app.exactos._seleccion
        R["grupos"] = sel.resultado.total_grupos
        R["nodos_tabla"] = len(app.exactos.tabla.tree.get_children())
        R["pendientes_inicio"] = len(sel.grupos_pendientes())
        estado_boton = str(app.exactos.btn_cuarentena.cget("state"))
        R["cuarentena_bloqueada_inicio"] = estado_boton == "disabled"

        # Poner la carpeta preferida (ya habilitada tras el escaneo) y aplicar regla
        app.exactos.entry_carpeta_buena.delete(0, "end")
        app.exactos.entry_carpeta_buena.insert(0, carpeta_buena)
        assert app.exactos.entry_carpeta_buena.get() == carpeta_buena
        resueltos, sin_coinc = sel.aplicar_regla_carpeta(app.exactos.entry_carpeta_buena.get())
        app.exactos.tabla.refrescar_todo()
        app.exactos._al_cambiar_seleccion()
        R["resueltos_regla"] = resueltos
        R["sin_coincidencia"] = sin_coinc
        R["pendientes_tras_regla"] = len(sel.grupos_pendientes())

        # Resolver a mano lo que quede
        for gi in list(sel.grupos_pendientes()):
            primera = sel.resultado.grupos[gi].archivos[0].ruta
            sel.conservar_solo(gi, primera)
        app.exactos.tabla.refrescar_todo()
        app.exactos._al_cambiar_seleccion()
        R["todo_listo"] = sel.todo_listo()
        R["cuarentena_habilitada_final"] = str(app.exactos.btn_cuarentena.cget("state")) == "normal"
        R["a_mover"] = sel.cantidad_a_mover()

        from core.reporte import exportar_csv
        R["grupos_csv"] = exportar_csv(sel.resultado, str(csv_salida))

        # Mover a cuarentena de verdad (misma lógica que usa el botón)
        from core.quarantine import mover_a_cuarentena
        a_mover_antes = sel.cantidad_a_mover()
        res = mover_a_cuarentena(sel, app.exactos._carpeta_escaneada, str(cuarentena))
        R["movidos"] = len(res.movidos)
        R["movidos_ok"] = (len(res.movidos) == a_mover_antes and not res.fallidos)
        R["log_existe"] = bool(res.ruta_log) and Path(res.ruta_log).exists()
        R["conservados_intactos"] = (base / "originales" / "doc.txt").exists()
        R["movido_en_cuarentena"] = any(cuarentena.rglob("img.dat"))

        app.exactos._alternar_opciones()

        # Categorías rápidas: marcar "Imágenes" rellena el campo y el filtro
        app.exactos._filtros_vacios()
        app.exactos.chk_categorias["Imágenes"].select()
        app.exactos._alternar_categoria("Imágenes")
        incl = app.exactos._filtro_actual().extensiones_incluidas
        R["cat_imagenes_jpg"] = "jpg" in incl and "png" in incl
        R["cat_imagenes_no_mp3"] = "mp3" not in incl
        app.exactos.chk_categorias["Audio"].select()
        app.exactos._alternar_categoria("Audio")
        R["cat_combina_audio"] = "mp3" in app.exactos._filtro_actual().extensiones_incluidas
        app.exactos.chk_categorias["Imágenes"].deselect()
        app.exactos._alternar_categoria("Imágenes")
        incl2 = app.exactos._filtro_actual().extensiones_incluidas
        R["cat_desmarca_imagenes"] = "jpg" not in incl2 and "mp3" in incl2
        app.exactos._filtros_vacios()
        R["cat_vacio"] = app.exactos._filtro_actual().extensiones_incluidas == set()

        top = VentanaTipos(app, sel.resultado, app.exactos._agregar_extension_al_filtro)
        R["extensiones"] = len(sel.resultado.resumen_por_extension())
        app.after(150, top.destroy)
        app.after(400, app.destroy)

    app.after(300, app.exactos._iniciar_escaneo)
    app.after(700, cuando_termine)
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
        and csv_salida.exists()
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
