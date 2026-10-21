"""Prueba de humo del modo Sencilla: los controles avanzados se ocultan,
la app preselecciona sola la copia principal de cada grupo y el botón de
cuarentena queda listo sin que el usuario elija nada. Cambiar a Avanzada
vuelve a mostrarlo todo.

    python pruebas/humo_sencilla.py
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# No toca los datos reales del usuario (historial, configuración):
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="dup_appdata_")

from ui import styles                            # noqa: E402
from ui.main_window import VentanaPrincipal      # noqa: E402

R = {}


def construir(base: Path):
    datos = b"foto identica\n" * 50
    (base / "Fotos" / "Backup").mkdir(parents=True)
    (base / "Descargas").mkdir(parents=True)
    (base / "Fotos" / "boda.jpg").write_bytes(datos)
    (base / "Fotos" / "Backup" / "boda.jpg").write_bytes(datos)
    (base / "Descargas" / "boda (1).jpg").write_bytes(datos)
    otros = b"otro archivo\n" * 30
    (base / "a.txt").write_bytes(otros)
    (base / "Descargas" / "a.txt").write_bytes(otros)


def main():
    styles.aplicar_tema()
    tmp = tempfile.mkdtemp(prefix="dup_senc_")
    base = Path(tmp) / "raiz"
    construir(base)

    app = VentanaPrincipal()
    app._modo = "sencillo"
    app._aplicar_modo()
    app.geometry("1200x820")
    app.exactos.entry_carpeta.insert(0, str(base))
    app.update()

    R["opciones_ocultas"] = not app.exactos._opciones_cont.winfo_ismapped()
    R["decision_fila_oculta"] = not app.exactos.tarjeta_decision_fila.winfo_ismapped()
    R["btn_tipos_oculto"] = not app.exactos.btn_tipos.winfo_ismapped()

    def cuando_termine():
        if app.exactos._seleccion is None:
            app.after(200, cuando_termine)
            return
        sel = app.exactos._seleccion
        R["grupos"] = sel.resultado.total_grupos
        R["todo_listo"] = sel.todo_listo()
        R["cuarentena_lista"] = str(app.exactos.btn_cuarentena.cget("state")) == "normal"
        R["a_mover"] = sel.cantidad_a_mover()

        # la copia conservada del grupo de la boda no es la de Backup ni la (1)
        gi = next(i for i, g in enumerate(sel.resultado.grupos)
                  if any("boda" in a.ruta for a in g.archivos))
        from core.seleccion import CONSERVAR
        conservada = [a for a in sel.resultado.grupos[gi].archivos
                      if sel.decision(gi, a.ruta) == CONSERVAR][0]
        R["principal_ok"] = (Path(conservada.ruta).name == "boda.jpg"
                             and "Backup" not in conservada.ruta)

        # cambiar a Avanzada muestra los controles otra vez
        app._modo = "avanzado"
        app._aplicar_modo()
        app.update()
        R["opciones_visibles_avanzada"] = app.exactos._opciones_cont.winfo_ismapped() == 1
        R["decision_visible_avanzada"] = app.exactos.tarjeta_decision_fila.winfo_ismapped() == 1

        app.after(300, app.destroy)

    app.after(300, app.exactos._iniciar_escaneo)
    app.after(800, cuando_termine)
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
