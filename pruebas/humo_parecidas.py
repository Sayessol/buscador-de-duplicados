"""Prueba de humo de la pestaña "Fotos parecidas": abre la ventana,
genera fotos sintéticas, cambia de pestaña, lanza el análisis, espera,
y comprueba que la galería se llena, que el toggle conservar/mover
funciona y que mover a cuarentena de verdad respeta la regla de oro.

    python pruebas/humo_parecidas.py
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# No toca los datos reales del usuario (historial, configuración):
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="dup_appdata_")

from pruebas.probar_perceptual import construir            # noqa: E402
from ui import styles, icons, pestana_parecidas             # noqa: E402
from ui.main_window import VentanaPrincipal                 # noqa: E402
from core.quarantine import mover_a_cuarentena              # noqa: E402
from core.seleccion import CONSERVAR                        # noqa: E402

R = {}


def main():
    styles.aplicar_tema()
    tmp = tempfile.mkdtemp(prefix="dup_parui_")
    base = Path(tmp) / "fotos"
    construir(base)
    cuarentena = Path(tmp) / "CUARENTENA"

    app = VentanaPrincipal()
    app._modo = "avanzado"
    app._aplicar_modo()
    app.geometry("1200x860")
    app.tabs.set(f"{icons.CAT_IMAGENES}  Fotos parecidas")
    app.parecidas.entry_carpeta.insert(0, str(base))
    app.parecidas.slider_sensibilidad.set(12)

    def cuando_termine():
        if app.parecidas._seleccion is None:
            app.after(200, cuando_termine)
            return
        sel = app.parecidas._seleccion
        res = app.parecidas._resultado
        R["grupos"] = res.total_grupos
        R["tiles"] = len(app.parecidas._tiles)
        R["errores"] = len(res.errores)

        # el grupo "playa" debe tener 5 fotos y la mejor marcada conservar
        gi_playa = next(
            i for i, g in enumerate(res.grupos)
            if any("playa_original" in a.ruta for a in g.archivos))
        g = res.grupos[gi_playa]
        R["playa_5"] = g.cantidad == 5
        R["mejor_es_png"] = g.archivos[0].ruta.endswith("playa_original.png")
        R["mejor_conservar"] = sel.decision(gi_playa, g.archivos[0].ruta) == CONSERVAR
        R["resto_mover"] = all(
            sel.decision(gi_playa, a.ruta) != CONSERVAR for a in g.archivos[1:])

        # toggle manual: elegir otra como la que se conserva
        otra = g.archivos[1].ruta
        app.parecidas._elegir_conservar(gi_playa, otra)
        R["toggle_ok"] = (
            sel.decision(gi_playa, otra) == CONSERVAR
            and sel.decision(gi_playa, g.archivos[0].ruta) != CONSERVAR
            and sel.estado_grupo(gi_playa) == "ok")
        # volver a dejar la mejor
        app.parecidas._elegir_conservar(gi_playa, g.archivos[0].ruta)

        R["todo_listo"] = sel.todo_listo()
        R["boton_cuarentena"] = str(app.parecidas.btn_cuarentena.cget("state")) == "normal"
        a_mover = sel.cantidad_a_mover()

        # galería en páginas: con 1 grupo por página hay una por grupo, y al
        # cambiar de página solo existen los widgets de la página visible.
        p = app.parecidas
        pestana_parecidas.GRUPOS_MAX_PAGINA = 1
        p._construir_galeria()
        app.update()
        R["paginas"] = len(p._paginas) == res.total_grupos
        R["pager_visible"] = bool(p.pager.winfo_ismapped())
        R["pag1_tiles"] = {gi for gi, _ in p._tiles} == {0}
        R["pag1_anterior_apagado"] = str(p.btn_pag_ant.cget("state")) == "disabled"
        p._cambiar_pagina(1)
        app.update()
        R["pag2_tiles"] = {gi for gi, _ in p._tiles} == {1}
        R["pag2_siguiente_apagado"] = str(p.btn_pag_sig.cget("state")) == "disabled"
        p._cambiar_pagina(1)                       # ya es la última: no hace nada
        R["no_pasa_de_la_ultima"] = p._pagina == 1
        R["seleccion_intacta"] = sel.decision(gi_playa, g.archivos[0].ruta) == CONSERVAR
        R["alto_galeria_ok"] = p.galeria.winfo_reqheight() < 32767
        pestana_parecidas.GRUPOS_MAX_PAGINA = 40
        p._construir_galeria()
        app.update()
        R["una_pagina_sin_pager"] = len(p._paginas) == 1 and not p.pager.winfo_ismapped()

        res_mov = mover_a_cuarentena(sel, str(base), str(cuarentena))
        R["movidas"] = len(res_mov.movidos)
        R["movidas_ok"] = len(res_mov.movidos) == a_mover and not res_mov.fallidos
        R["mejor_intacta"] = (base / "playa_original.png").exists()
        R["log"] = bool(res_mov.ruta_log) and Path(res_mov.ruta_log).exists()

        app.after(300, app.destroy)

    app.after(400, app.parecidas._iniciar)
    app.after(900, cuando_termine)
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
        and R.get("movidas") == 5       # 4 sobrantes de playa + 1 de montaña
        and R.get("movidas_ok") is True
        and R.get("mejor_intacta") is True
        and R.get("log") is True
    )
    print("\n" + ("HUMO PARECIDAS OK" if ok else "HUMO PARECIDAS FALLA"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
