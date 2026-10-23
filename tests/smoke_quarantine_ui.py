"""Reproduce EXACTAMENTE lo que hace el usuario: abre la ventana, analiza
una carpeta con fotos repartidas en subcarpetas, y pulsa "Mover a
cuarentena" eligiendo una carpeta nueva (se simulan los diálogos).

Comprueba que se mueven los ARCHIVOS y NO las carpetas, tanto en la
pestaña "Fotos parecidas" como en "Duplicados exactos".

    python tests/smoke_quarantine_ui.py
"""

import os
import sys
import tempfile
from pathlib import Path
from tkinter import filedialog, messagebox

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# No toca los datos reales del usuario (historial, configuración):
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="dup_appdata_")

from PIL import Image                                # noqa: E402
from ui import styles, icons                         # noqa: E402
from ui.main_window import MainWindow          # noqa: E402

R = {}
failures = []


def check(cond, msg):
    print(f"  [{'OK  ' if cond else 'FALLA'}] {msg}")
    if not cond:
        failures.append(msg)


def _photo(seed):
    import random
    rnd = random.Random(seed)
    im = Image.new("RGB", (600, 400), (12, 12, 12))
    for _ in range(14):
        x, y = rnd.randint(0, 600), rnd.randint(0, 400)
        im.paste((rnd.randint(0, 255), rnd.randint(0, 255), rnd.randint(0, 255)),
                 (x, y, x + 110, y + 110))
    return im


def build(root: Path):
    (root / "2023" / "verano").mkdir(parents=True)
    (root / "2024").mkdir(parents=True)
    (root / "sin ordenar").mkdir(parents=True)
    _photo(1).save(root / "2023" / "verano" / "playa.jpg", quality=92)
    _photo(1).save(root / "2024" / "playa.jpg", quality=45)          # parecida
    _photo(1).save(root / "sin ordenar" / "playa (copia).jpg", quality=70)  # parecida
    _photo(2).save(root / "2023" / "retrato.jpg", quality=92)
    _photo(2).save(root / "sin ordenar" / "retrato.jpg", quality=45)  # parecida


def main():
    styles.apply_theme()
    tmp = tempfile.mkdtemp(prefix="dup_uic_")
    root = Path(tmp) / "Fotos móvil"
    build(root)
    # Carpeta de cuarentena "en el escritorio", creada por el usuario:
    quarantine = Path(tmp) / "Escritorio" / "Cuarentena"
    quarantine.mkdir(parents=True)

    # Simular los diálogos.
    filedialog.askdirectory = lambda *a, **k: str(quarantine)
    messagebox.askyesno = lambda *a, **k: True
    os.startfile = lambda *a, **k: None   # sin esto se abriría el Explorador de verdad
    messagebox.showinfo = lambda *a, **k: None
    messagebox.showwarning = lambda *a, **k: None
    messagebox.showerror = lambda *a, **k: print("   [showerror]", a)

    app = MainWindow()
    app._mode = "avanzado"
    app._apply_mode()
    app.tabs.set(f"{icons.CAT_IMAGES}  Fotos parecidas")
    app.similar.entry_folder.insert(0, str(root))
    app.similar.sensitivity_slider.set(14)

    folders_before = sorted(str(x.relative_to(root))
                            for x in root.rglob("*") if x.is_dir())
    files_before = sorted(str(x.relative_to(root))
                            for x in root.rglob("*") if x.is_file())

    def when_ready():
        if app.similar._selection is None:
            app.after(200, when_ready)
            return
        app.after(600, move)

    def move():
        R["a_mover"] = app.similar._selection.count_to_move()
        app.similar._move_to_quarantine()
        app.after(1500, verify)

    def verify():
        folders_after = sorted(str(x.relative_to(root))
                                  for x in root.rglob("*") if x.is_dir())
        files_after = sorted(str(x.relative_to(root))
                                  for x in root.rglob("*") if x.is_file())
        dirs_in_quarantine = sorted(str(x.relative_to(quarantine))
                                    for x in quarantine.rglob("*") if x.is_dir())
        files_in_quarantine = sorted(
            str(x.relative_to(quarantine)) for x in quarantine.rglob("*")
            if x.is_file() and not x.name.endswith(".csv"))

        print("  carpetas del origen ANTES: ", folders_before)
        print("  carpetas del origen DESPUÉS:", folders_after)
        print("  archivos que quedan en origen:", files_after)
        print("  carpetas creadas en cuarentena:", dirs_in_quarantine)
        print("  archivos movidos a cuarentena:", files_in_quarantine)

        check(folders_before == folders_after,
              "TODAS las subcarpetas del origen siguen ahí (no se movieron)")
        check(len(files_after) + len(files_in_quarantine) == len(files_before),
              "ningún archivo se ha perdido")
        check(len(files_in_quarantine) == R["a_mover"] and R["a_mover"] >= 2,
              f"se movieron {R['a_mover']} archivos (regulares) a la cuarentena")
        check(all("." in Path(f).name for f in files_in_quarantine),
              "lo que hay en la cuarentena son archivos con extensión, no carpetas")

        app.after(200, app.destroy)

    app.after(400, app.similar._start)
    app.after(800, when_ready)
    app.after(20000, app.destroy)
    app.mainloop()

    print()
    if failures:
        print(f"FALLARON {len(failures)} comprobaciones.")
        sys.exit(1)
    print("LA UI MUEVE ARCHIVOS, NO CARPETAS: OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
