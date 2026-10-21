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
from ui import styles, icons                                # noqa: E402
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
        and R.get("movidas") == 5        # 4 sobrantes de playa + 1 de montaña
        and R.get("movidas_ok") is True
        and R.get("mejor_intacta") is True
        and R.get("log") is True
    )
    print("\n" + ("HUMO PARECIDAS OK" if ok else "HUMO PARECIDAS FALLA"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
