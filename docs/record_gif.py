"""Records docs/img/<language>/demo.gif: scan -> move to quarantine -> undo.

    python docs/record_gif.py        # Spanish (default)
    python docs/record_gif.py en     # English

It opens the app itself with sample folders and takes screenshots of ITS window
(never of the whole desktop) every few tenths of a second. The system dialogs
are simulated so the script runs on its own. It needs a Windows desktop.
It uses a neutral path (C:/Demo) so that your user name does not show up.
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
LANGUAGE = sys.argv[1] if len(sys.argv) > 1 else "es"
assert LANGUAGE in ("es", "en"), "usage: record_gif.py [es|en]"
OUTPUT = Path(__file__).resolve().parent / "img" / LANGUAGE / "demo.gif"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
GIF_WIDTH = 960                    # final width of the GIF (smaller = fewer MB)
INTERVAL_MS = 90                  # how often a frame is captured

BASE_DEMO = Path(os.environ.get("CAPTURE_BASE", "C:/Demo"))
BASE_DEMO.mkdir(parents=True, exist_ok=True)
tmp = Path(tempfile.mkdtemp(prefix="", dir=BASE_DEMO))
os.environ["APPDATA"] = str(tmp / "appdata")        # does not touch your real configuration
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from PIL import Image, ImageChops, ImageDraw, ImageGrab     # noqa: E402

from duplicate_finder import i18n  # noqa: E402
from duplicate_finder.bootstrap import build_services  # noqa: E402

i18n.set_language(LANGUAGE)
SERVICES = build_services()
history = SERVICES.history
from duplicate_finder.presentation import styles  # noqa: E402
from duplicate_finder.presentation.history_window import HistoryWindow  # noqa: E402
from duplicate_finder.presentation.main_window import MainWindow  # noqa: E402


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


# ---- sample folders --------------------------------------------------
def T(es, en):
    """The sample name in the language of the recording."""
    return es if LANGUAGE == "es" else en


BEACH, SUNSET = T("playa.png", "beach.png"), T("atardecer.png", "sunset.png")
BIRTHDAY = T("cumple.png", "birthday.png")
SUMMER, DOWNLOADS = T("verano", "summer"), T("Descargas", "Downloads")
DESKTOP = T("Escritorio", "Desktop")
base = tmp / T("Fotos", "Photos")
names = {f"2023/{SUMMER}/{BEACH}": 1, f"2023/{SUMMER}/{SUNSET}": 2,
         f"2023/{BIRTHDAY}": 3, f"{DOWNLOADS}/{T('montaña.png', 'mountain.png')}": 4,
         f"{DESKTOP}/{T('portada.png', 'cover.png')}": 5}
for rel, seed in names.items():
    path = base / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    photo(seed).save(path)
SUNSET_COPY = T("atardecer (1).png", "sunset (1).png")
BIRTHDAY_COPY = T("cumple - copia.png", "birthday - copy.png")
for source, copy in [(f"2023/{SUMMER}/{BEACH}", f"{DOWNLOADS}/{BEACH}"),
                     (f"2023/{SUMMER}/{SUNSET}", f"{DOWNLOADS}/{SUNSET_COPY}"),
                     (f"2023/{BIRTHDAY}", f"{DESKTOP}/{BIRTHDAY_COPY}")]:
    (base / copy).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(base / source, base / copy)
quarantine = tmp / T("Cuarentena", "Quarantine")
quarantine.mkdir()

# ---- simulated dialogs -----------------------------------------------------
filedialog.askdirectory = lambda *a, **k: str(quarantine)
messagebox.askyesno = lambda *a, **k: True
os.startfile = lambda *a, **k: None   # without this the real Explorer would open
messagebox.showinfo = lambda *a, **k: None
messagebox.showwarning = lambda *a, **k: None
messagebox.showerror = lambda *a, **k: None

styles.apply_theme("dark")
app = MainWindow(SERVICES)
app._mode = "simple"
app._apply_mode()
app.geometry("1280x860+12+6")

frames = []                    # (instant, image)


def capture():
    app.update_idletasks()
    x, y = app.winfo_rootx(), app.winfo_rooty()
    w, h = app.winfo_width(), app.winfo_height()
    im = ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True).convert("RGB")
    frames.append((time.perf_counter(), im))
    app.after(INTERVAL_MS, capture)


# ---- script ---------------------------------------------------------------------
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
        if meta[0] == "file" and meta[2].endswith(BEACH):
            app.exact.table.tree.selection_set(iid)
            app.exact.table.tree.see(iid)
            break
    app.after(1700, move)


def move():
    app.exact._move_to_quarantine()
    wait(lambda: bool(history.list_all()), open_history)


def open_history():
    app._mode = "advanced"
    app._apply_mode()
    app.mode_selector.set_key("advanced")
    app._hv = HistoryWindow(app, history)
    app._hv.geometry("720x520+300+120")
    app.after(1800, undo)


def undo():
    app._hv._undo(history.list_all()[0])
    app.after(2200, close)


def close():
    app._hv.destroy()
    app.after(600, rescan)


def rescan():
    # After undoing, the files are back in their place: scan again.
    previous = app.exact._result
    app.exact._start_scan()
    wait(lambda: app.exact._result is not previous, lambda: app.after(2200, app.destroy))


app.after(300, capture)
app.after(1200, write_path)
app.after(60000, app.destroy)
app.mainloop()

# ---- assemble the GIF ------------------------------------------------------------
height = round(frames[0][1].height * GIF_WIDTH / frames[0][1].width)
imgs, durations, previous = [], [], None
for (t0, im), next in zip(frames, frames[1:] + [(frames[-1][0] + .6, None)]):
    dur = max(int((next[0] - t0) * 1000), 40)
    small = im.resize((GIF_WIDTH, height), Image.LANCZOS)
    if previous is not None and ImageChops.difference(small, previous).getbbox() is None:
        durations[-1] += dur                     # same frame: the previous one is lengthened
        continue
    imgs.append(small.quantize(colors=128, method=Image.Quantize.MEDIANCUT,
                               dither=Image.Dither.NONE))
    durations.append(dur)
    previous = small
imgs[0].save(OUTPUT, save_all=True, append_images=imgs[1:], duration=durations,
             loop=0, optimize=True, disposal=1)
print(f"{OUTPUT.parent.name}/{OUTPUT.name}: {len(imgs)} frames, "
      f"{OUTPUT.stat().st_size / 1e6:.1f} MB, {sum(durations) / 1000:.1f} s")

# Cleanup: deletes only the sample folder created by this script.
shutil.rmtree(tmp, ignore_errors=True)
try:
    BASE_DEMO.rmdir()
except OSError:
    pass
