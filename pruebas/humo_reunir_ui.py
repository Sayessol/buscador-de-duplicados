"""Prueba de humo de la pestaña "Reunir imágenes" + Historial + Deshacer,
pulsando los botones reales de la ventana (con los diálogos simulados).

    python pruebas/humo_reunir_ui.py
"""

import os
import sys
import tempfile
from pathlib import Path
from tkinter import filedialog, messagebox

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

R = {}
fallos = []


def check(cond, msg):
    print(f"  [{'OK  ' if cond else 'FALLA'}] {msg}")
    if not cond:
        fallos.append(msg)


def construir(raiz: Path):
    from PIL import Image
    (raiz / "2023").mkdir(parents=True)
    (raiz / "2024" / "boda").mkdir(parents=True)
    for rel in ("portada.png", "2023/playa.jpg", "2024/retrato.jpg",
                "2024/boda/grupo.jpeg"):
        Image.new("RGB", (64, 48), (90, 90, 90)).save(raiz / rel)
    (raiz / "notas.txt").write_text("hola")
    (raiz / "2023" / "info.pdf").write_bytes(b"%PDF")
    (raiz / "2024" / "gastos.pdf").write_bytes(b"%PDF")


def main():
    tmp = Path(tempfile.mkdtemp(prefix="dup_reunir_"))
    os.environ["APPDATA"] = str(tmp / "appdata")

    from ui import styles, icons                         # noqa: E402
    from ui import main_window as MW                      # noqa: E402
    from core import historial                            # noqa: E402
    from core.reunir import ReglasNoImagen                # noqa: E402
    import customtkinter as ctk

    styles.aplicar_tema()

    raiz = tmp / "Fotos revueltas"
    destino = tmp / "Escritorio" / "Todas las fotos"
    construir(raiz)

    # Diálogos simulados
    filedialog.askdirectory = lambda *a, **k: str(destino)
    messagebox.askyesno = lambda *a, **k: True
    os.startfile = lambda *a, **k: None   # sin esto se abriría el Explorador de verdad
    messagebox.showinfo = lambda *a, **k: None
    messagebox.showwarning = lambda *a, **k: None
    messagebox.showerror = lambda *a, **k: print("   [showerror]", a)

    class FakeTipos(ctk.CTkToplevel):
        def __init__(self, master, tipos):
            super().__init__(master)
            self.withdraw()
            self.reglas = ReglasNoImagen(
                accion_por_ext={"pdf": "agrupar", "txt": "dejar"},
                carpeta_por_ext={"pdf": "Documentos"})
            self.after(10, self.destroy)
    from ui import pestana_reunir as TR                      # noqa: E402
    TR.VentanaTiposNoImagen = FakeTipos   # el diálogo se usa desde la pestaña Reunir

    app = MW.VentanaPrincipal()
    app._modo = "avanzado"
    app._aplicar_modo()
    app.tabs.set(f"{icons.REUNIR}  Reunir imágenes")
    app.reunir.entry_carpeta.insert(0, str(raiz))
    app.reunir.entry_destino.insert(0, str(destino))
    app.reunir.seg_accion.set("Mover")
    app.reunir.seg_estrategia.set("Por archivos")

    imgs_antes = sorted(str(p.relative_to(raiz)).replace("\\", "/")
                        for p in raiz.rglob("*") if p.suffix.lower() in
                        (".png", ".jpg", ".jpeg"))

    def paso_buscar():
        app.reunir._buscar()
        app.after(800, paso_ejecutar)

    def paso_ejecutar():
        R["encontradas"] = len(app.reunir._imagenes)
        R["marcadas"] = len(app.reunir._incluidas)
        R["otros"] = len(app.reunir._otros)
        app.reunir._ejecutar()
        app.after(1800, comprobar)

    def comprobar():
        movidas = sorted(str(p.relative_to(destino)).replace("\\", "/")
                         for p in destino.rglob("*")
                         if p.suffix.lower() in (".png", ".jpg", ".jpeg"))
        R["img_en_destino"] = movidas
        R["quedan_en_origen_img"] = [
            str(p.relative_to(raiz)) for p in raiz.rglob("*")
            if p.suffix.lower() in (".png", ".jpg", ".jpeg")]
        R["txt_sigue"] = (raiz / "notas.txt").exists()
        R["pdf_agrupado"] = (destino / "Documentos" / "2023" / "info.pdf").exists()
        R["subcarpetas_origen"] = sorted(
            str(p.relative_to(raiz)) for p in raiz.rglob("*") if p.is_dir())

        ops = historial.listar()
        R["historial_n"] = len(ops)
        R["op_tipo"] = ops[0]["tipo"] if ops else None

        # Deshacer la operación
        res = historial.deshacer(ops[0]["id"])
        R["deshacer_ok"] = res["ok"]
        R["deshacer_fallos"] = len(res["fallos"])
        R["img_vuelta"] = (raiz / "2023" / "playa.jpg").exists()
        R["destino_vacio_img"] = not any(
            p.suffix.lower() in (".png", ".jpg", ".jpeg")
            for p in destino.rglob("*"))

        app.after(200, app.destroy)

    app.after(400, paso_buscar)
    app.after(20000, app.destroy)
    app.mainloop()

    for k, v in R.items():
        print(f"  {k:24} {v}")

    ok = (
        R.get("encontradas") == 4
        and R.get("marcadas") == 4
        and R.get("otros") == 3
        and sorted(R.get("img_en_destino", [])) == sorted(imgs_antes)
        and R.get("quedan_en_origen_img") == []
        and R.get("txt_sigue") is True
        and R.get("pdf_agrupado") is True
        and set(R.get("subcarpetas_origen", [])) >= {"2023", "2024", "2024\\boda"}
        and R.get("historial_n") == 1
        and R.get("op_tipo") == "reunir"
        and R.get("deshacer_ok") == 6   # 4 imágenes + 2 pdf agrupados
        and R.get("deshacer_fallos") == 0
        and R.get("img_vuelta") is True
        and R.get("destino_vacio_img") is True
    )
    print("\n" + ("HUMO REUNIR OK" if ok else "HUMO REUNIR FALLA"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
