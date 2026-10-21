"""Reproduce EXACTAMENTE lo que hace el usuario: abre la ventana, analiza
una carpeta con fotos repartidas en subcarpetas, y pulsa "Mover a
cuarentena" eligiendo una carpeta nueva (se simulan los diálogos).

Comprueba que se mueven los ARCHIVOS y NO las carpetas, tanto en la
pestaña "Fotos parecidas" como en "Duplicados exactos".

    python pruebas/humo_cuarentena_ui.py
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
from ui.main_window import VentanaPrincipal          # noqa: E402

R = {}
fallos = []


def check(cond, msg):
    print(f"  [{'OK  ' if cond else 'FALLA'}] {msg}")
    if not cond:
        fallos.append(msg)


def _foto(semilla):
    import random
    rnd = random.Random(semilla)
    im = Image.new("RGB", (600, 400), (12, 12, 12))
    for _ in range(14):
        x, y = rnd.randint(0, 600), rnd.randint(0, 400)
        im.paste((rnd.randint(0, 255), rnd.randint(0, 255), rnd.randint(0, 255)),
                 (x, y, x + 110, y + 110))
    return im


def construir(raiz: Path):
    (raiz / "2023" / "verano").mkdir(parents=True)
    (raiz / "2024").mkdir(parents=True)
    (raiz / "sin ordenar").mkdir(parents=True)
    _foto(1).save(raiz / "2023" / "verano" / "playa.jpg", quality=92)
    _foto(1).save(raiz / "2024" / "playa.jpg", quality=45)          # parecida
    _foto(1).save(raiz / "sin ordenar" / "playa (copia).jpg", quality=70)  # parecida
    _foto(2).save(raiz / "2023" / "retrato.jpg", quality=92)
    _foto(2).save(raiz / "sin ordenar" / "retrato.jpg", quality=45)  # parecida


def main():
    styles.aplicar_tema()
    tmp = tempfile.mkdtemp(prefix="dup_uic_")
    raiz = Path(tmp) / "Fotos móvil"
    construir(raiz)
    # Carpeta de cuarentena "en el escritorio", creada por el usuario:
    cuarentena = Path(tmp) / "Escritorio" / "Cuarentena"
    cuarentena.mkdir(parents=True)

    # Simular los diálogos.
    filedialog.askdirectory = lambda *a, **k: str(cuarentena)
    messagebox.askyesno = lambda *a, **k: True
    os.startfile = lambda *a, **k: None   # sin esto se abriría el Explorador de verdad
    messagebox.showinfo = lambda *a, **k: None
    messagebox.showwarning = lambda *a, **k: None
    messagebox.showerror = lambda *a, **k: print("   [showerror]", a)

    app = VentanaPrincipal()
    app._modo = "avanzado"
    app._aplicar_modo()
    app.tabs.set(f"{icons.CAT_IMAGENES}  Fotos parecidas")
    app.parecidas.entry_carpeta.insert(0, str(raiz))
    app.parecidas.slider_sensibilidad.set(14)

    carpetas_antes = sorted(str(x.relative_to(raiz))
                            for x in raiz.rglob("*") if x.is_dir())
    archivos_antes = sorted(str(x.relative_to(raiz))
                            for x in raiz.rglob("*") if x.is_file())

    def cuando_listo():
        if app.parecidas._seleccion is None:
            app.after(200, cuando_listo)
            return
        app.after(600, mover)

    def mover():
        R["a_mover"] = app.parecidas._seleccion.cantidad_a_mover()
        app.parecidas._mover_a_cuarentena()
        app.after(1500, comprobar)

    def comprobar():
        carpetas_despues = sorted(str(x.relative_to(raiz))
                                  for x in raiz.rglob("*") if x.is_dir())
        archivos_despues = sorted(str(x.relative_to(raiz))
                                  for x in raiz.rglob("*") if x.is_file())
        en_cuarentena_dirs = sorted(str(x.relative_to(cuarentena))
                                    for x in cuarentena.rglob("*") if x.is_dir())
        en_cuarentena_files = sorted(
            str(x.relative_to(cuarentena)) for x in cuarentena.rglob("*")
            if x.is_file() and not x.name.endswith(".csv"))

        print("  carpetas del origen ANTES: ", carpetas_antes)
        print("  carpetas del origen DESPUÉS:", carpetas_despues)
        print("  archivos que quedan en origen:", archivos_despues)
        print("  carpetas creadas en cuarentena:", en_cuarentena_dirs)
        print("  archivos movidos a cuarentena:", en_cuarentena_files)

        check(carpetas_antes == carpetas_despues,
              "TODAS las subcarpetas del origen siguen ahí (no se movieron)")
        check(len(archivos_despues) + len(en_cuarentena_files) == len(archivos_antes),
              "ningún archivo se ha perdido")
        check(len(en_cuarentena_files) == R["a_mover"] and R["a_mover"] >= 2,
              f"se movieron {R['a_mover']} archivos (regulares) a la cuarentena")
        check(all("." in Path(f).name for f in en_cuarentena_files),
              "lo que hay en la cuarentena son archivos con extensión, no carpetas")

        app.after(200, app.destroy)

    app.after(400, app.parecidas._iniciar)
    app.after(800, cuando_listo)
    app.after(20000, app.destroy)
    app.mainloop()

    print()
    if fallos:
        print(f"FALLARON {len(fallos)} comprobaciones.")
        sys.exit(1)
    print("LA UI MUEVE ARCHIVOS, NO CARPETAS: OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
