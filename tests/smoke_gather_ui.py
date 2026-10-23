"""Smoke test of the "Gather images" tab + History + Undo,
pressing the real buttons of the window (with the dialogs stubbed).

    python tests/smoke_gather_ui.py
"""

import os
import sys
import tempfile
from pathlib import Path
from tkinter import filedialog, messagebox

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

R = {}
failures = []


def check(cond, msg):
    print(f"  [{'OK  ' if cond else 'FALLA'}] {msg}")
    if not cond:
        failures.append(msg)


def build(root: Path):
    from PIL import Image
    (root / "2023").mkdir(parents=True)
    (root / "2024" / "boda").mkdir(parents=True)
    for rel in ("portada.png", "2023/playa.jpg", "2024/retrato.jpg",
                "2024/boda/grupo.jpeg"):
        Image.new("RGB", (64, 48), (90, 90, 90)).save(root / rel)
    (root / "notas.txt").write_text("hola")
    (root / "2023" / "info.pdf").write_bytes(b"%PDF")
    (root / "2024" / "gastos.pdf").write_bytes(b"%PDF")


def main():
    tmp = Path(tempfile.mkdtemp(prefix="dup_reunir_"))
    os.environ["APPDATA"] = str(tmp / "appdata")

    from ui import styles, icons                         # noqa: E402
    from ui import main_window as MW                      # noqa: E402
    from core import history                            # noqa: E402
    from core.gather import NonImageRules                # noqa: E402
    import customtkinter as ctk

    styles.apply_theme()

    root = tmp / "Fotos revueltas"
    destination = tmp / "Escritorio" / "Todas las fotos"
    build(root)

    # Stubbed dialogs
    filedialog.askdirectory = lambda *a, **k: str(destination)
    messagebox.askyesno = lambda *a, **k: True
    os.startfile = lambda *a, **k: None   # without this the real Explorer would open
    messagebox.showinfo = lambda *a, **k: None
    messagebox.showwarning = lambda *a, **k: None
    messagebox.showerror = lambda *a, **k: print("   [showerror]", a)

    class FakeKinds(ctk.CTkToplevel):
        def __init__(self, master, kinds):
            super().__init__(master)
            self.withdraw()
            self.rules = NonImageRules(
                action_by_ext={"pdf": "group", "txt": "leave"},
                folder_by_ext={"pdf": "Documentos"})
            self.after(10, self.destroy)
    from ui import gather_images_tab as TR                      # noqa: E402
    TR.NonImageKindsWindow = FakeKinds   # the dialog is used from the Gather tab

    app = MW.MainWindow()
    app._mode = "advanced"
    app._apply_mode()
    app.tabs.set(f"{icons.GATHER}  Reunir imágenes")
    app.gather.entry_folder.insert(0, str(root))
    app.gather.entry_destination.insert(0, str(destination))
    app.gather.seg_action.set("Mover")
    app.gather.seg_strategy.set("Por archivos")

    imgs_before = sorted(str(p.relative_to(root)).replace("\\", "/")
                        for p in root.rglob("*") if p.suffix.lower() in
                        (".png", ".jpg", ".jpeg"))

    def search_step():
        app.gather._search()
        app.after(800, run_step)

    def run_step():
        R["encontradas"] = len(app.gather._images)
        R["marcadas"] = len(app.gather._included)
        R["otros"] = len(app.gather._others)
        app.gather._run()
        app.after(1800, verify)

    def verify():
        moved = sorted(str(p.relative_to(destination)).replace("\\", "/")
                         for p in destination.rglob("*")
                         if p.suffix.lower() in (".png", ".jpg", ".jpeg"))
        R["img_en_destino"] = moved
        R["quedan_en_origen_img"] = [
            str(p.relative_to(root)) for p in root.rglob("*")
            if p.suffix.lower() in (".png", ".jpg", ".jpeg")]
        R["txt_sigue"] = (root / "notas.txt").exists()
        R["pdf_agrupado"] = (destination / "Documentos" / "2023" / "info.pdf").exists()
        R["subcarpetas_origen"] = sorted(
            str(p.relative_to(root)) for p in root.rglob("*") if p.is_dir())

        ops = history.list_all()
        R["historial_n"] = len(ops)
        R["op_tipo"] = ops[0]["kind"] if ops else None

        # Undo the operation
        res = history.undo(ops[0]["id"])
        R["deshacer_ok"] = res["reverted"]
        R["deshacer_fallos"] = len(res["failures"])
        R["img_vuelta"] = (root / "2023" / "playa.jpg").exists()
        R["destino_vacio_img"] = not any(
            p.suffix.lower() in (".png", ".jpg", ".jpeg")
            for p in destination.rglob("*"))

        app.after(200, app.destroy)

    app.after(400, search_step)
    app.after(20000, app.destroy)
    app.mainloop()

    for k, v in R.items():
        print(f"  {k:24} {v}")

    ok = (
        R.get("encontradas") == 4
        and R.get("marcadas") == 4
        and R.get("otros") == 3
        and sorted(R.get("img_en_destino", [])) == sorted(imgs_before)
        and R.get("quedan_en_origen_img") == []
        and R.get("txt_sigue") is True
        and R.get("pdf_agrupado") is True
        and set(R.get("subcarpetas_origen", [])) >= {"2023", "2024", "2024\\boda"}
        and R.get("historial_n") == 1
        and R.get("op_tipo") == "gather"
        and R.get("deshacer_ok") == 6   # 4 images + 2 pdf grouped
        and R.get("deshacer_fallos") == 0
        and R.get("img_vuelta") is True
        and R.get("destino_vacio_img") is True
    )
    print("\n" + ("HUMO REUNIR OK" if ok else "HUMO REUNIR FALLA"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
