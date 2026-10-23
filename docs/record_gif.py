"""Graba docs/img/demo.gif: escanear -> mover a cuarentena -> deshacer.

    python docs/record_gif.py

Abre la propia app con carpetas de ejemplo y hace capturas de SU ventana
(nunca del escritorio entero) cada pocas décimas de segundo. Los diálogos del
sistema se simulan para que el guion corra solo. Necesita escritorio de Windows.
Usa una ruta neutra (C:/Demo) para que no salga tu nombre de usuario.
"""

import os
import random
import shutil
import sys
import tempfile
import time
from pathlib import Path
from tkinter import filedialog, messagebox

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path(__file__).resolve().parent / "img" / "demo.gif"
GIF_WIDTH = 960                    # ancho final del GIF (más pequeño = menos MB)
INTERVAL_MS = 90                  # cada cuánto se captura un fotograma

BASE_DEMO = Path(os.environ.get("CAPTURAS_BASE", "C:/Demo"))
BASE_DEMO.mkdir(parents=True, exist_ok=True)
tmp = Path(tempfile.mkdtemp(prefix="", dir=BASE_DEMO))
os.environ["APPDATA"] = str(tmp / "appdata")        # no toca tu configuración real
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageChops, ImageDraw, ImageGrab     # noqa: E402

from core import history                                  # noqa: E402
from ui import styles                                       # noqa: E402
from ui.history_window import HistoryWindow              # noqa: E402
from ui.main_window import MainWindow                 # noqa: E402


def photo(seed, size=(240, 160)):
    rnd = random.Random(seed)
    im = Image.new("RGB", size, (24, 28, 36))
    d = ImageDraw.Draw(im)
    for _ in range(9):
        x, y = rnd.randint(0, size[0]), rnd.randint(0, size[1])
        col = (rnd.randint(40, 235), rnd.randint(40, 235), rnd.randint(60, 235))
        box = [x, y, x + rnd.randint(30, 90), y + rnd.randint(30, 90)]
        (d.ellipse if rnd.random() < .5 else d.rectangle)(box, fill=col)
    return im


# ---- carpetas de ejemplo --------------------------------------------------
base = tmp / "Fotos"
names = {"2023/verano/playa.png": 1, "2023/verano/atardecer.png": 2,
           "2023/cumple.png": 3, "Descargas/montaña.png": 4, "Escritorio/portada.png": 5}
for rel, seed in names.items():
    path = base / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    photo(seed).save(path)
for source, copy in [("2023/verano/playa.png", "Descargas/playa.png"),
                      ("2023/verano/atardecer.png", "Descargas/atardecer (1).png"),
                      ("2023/cumple.png", "Escritorio/cumple - copia.png")]:
    (base / copy).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(base / source, base / copy)
quarantine = tmp / "Cuarentena"
quarantine.mkdir()

# ---- diálogos simulados -----------------------------------------------------
filedialog.askdirectory = lambda *a, **k: str(quarantine)
messagebox.askyesno = lambda *a, **k: True
os.startfile = lambda *a, **k: None   # sin esto se abriría el Explorador de verdad
messagebox.showinfo = lambda *a, **k: None
messagebox.showwarning = lambda *a, **k: None
messagebox.showerror = lambda *a, **k: None

styles.apply_theme("oscuro")
app = MainWindow()
app._mode = "sencillo"
app._apply_mode()
app.geometry("1280x860+12+6")

frames = []                    # (instante, imagen)


def capture():
    app.update_idletasks()
    x, y = app.winfo_rootx(), app.winfo_rooty()
    w, h = app.winfo_width(), app.winfo_height()
    im = ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True).convert("RGB")
    frames.append((time.perf_counter(), im))
    app.after(INTERVAL_MS, capture)


# ---- guion ---------------------------------------------------------------------
text_path = str(base)
state = {"i": 0}


def write_path():
    if state["i"] < len(text_path):
        state["i"] += 3
        app.exact.entry_folder.delete(0, "end")
        app.exact.entry_folder.insert(0, text_path[:state["i"]])
        app.after(45, write_path)
    else:
        app.after(500, scan)


def scan():
    app.exact._start_scan()
    wait(lambda: app.exact._selection is not None, choose_row)


def wait(condition, next, attempts=200):
    if condition() or attempts == 0:
        app.after(900, next)
    else:
        app.after(100, lambda: wait(condition, next, attempts - 1))


def choose_row():
    for iid, meta in app.exact.table._meta.items():
        if meta[0] == "archivo" and meta[2].endswith("playa.png"):
            app.exact.table.tree.selection_set(iid)
            app.exact.table.tree.see(iid)
            break
    app.after(1700, move)


def move():
    app.exact._move_to_quarantine()
    wait(lambda: bool(history.list_all()), open_history)


def open_history():
    app._mode = "avanzado"
    app._apply_mode()
    app.mode_selector.set("Avanzada")
    app._hv = HistoryWindow(app)
    app._hv.geometry("720x520+300+120")
    app.after(1800, undo)


def undo():
    app._hv._undo(history.list_all()[0])
    app.after(2200, close)


def close():
    app._hv.destroy()
    app.after(600, rescan)


def rescan():
    # Tras deshacer, los archivos están otra vez en su sitio: se vuelve a escanear.
    previous = app.exact._result
    app.exact._start_scan()
    wait(lambda: app.exact._result is not previous, lambda: app.after(2200, app.destroy))


app.after(300, capture)
app.after(1200, write_path)
app.after(60000, app.destroy)
app.mainloop()

# ---- montar el GIF ------------------------------------------------------------
height = round(frames[0][1].height * GIF_WIDTH / frames[0][1].width)
imgs, durations, previous = [], [], None
for (t0, im), next in zip(frames, frames[1:] + [(frames[-1][0] + .6, None)]):
    dur = max(int((next[0] - t0) * 1000), 40)
    small = im.resize((GIF_WIDTH, height), Image.LANCZOS)
    if previous is not None and ImageChops.difference(small, previous).getbbox() is None:
        durations[-1] += dur                     # fotograma igual: se alarga el anterior
        continue
    imgs.append(small.quantize(colors=128, method=Image.Quantize.MEDIANCUT,
                               dither=Image.Dither.NONE))
    durations.append(dur)
    previous = small
imgs[0].save(OUTPUT, save_all=True, append_images=imgs[1:], duration=durations,
             loop=0, optimize=True, disposal=1)
print(f"{OUTPUT.name}: {len(imgs)} fotogramas, {OUTPUT.stat().st_size / 1e6:.1f} MB, "
      f"{sum(durations) / 1000:.1f} s")

# Limpieza: borra solo la carpeta de ejemplo que creó este script.
shutil.rmtree(tmp, ignore_errors=True)
try:
    BASE_DEMO.rmdir()
except OSError:
    pass
