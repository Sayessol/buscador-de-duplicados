"""Generates the screenshots for the documentation.

    python docs/capture.py             # dark theme   -> 01_sencilla.png ...
    python docs/capture.py light       # light theme  -> 01_sencilla_claro.png ...

It saves PNGs in docs/img/ (or in the folder of the CAPTURAS_SALIDA variable). Each
capture limits the crop to the window of the app itself (never to the whole desktop).

It is DETERMINISTIC: sample folder with a fixed name, photos always generated the same, and
fixed dates. Two runs in a row give pixel-identical images, and that is useful
to check that an internal change to the app has not altered its appearance.
"""

import os
import shutil
import sys
import zlib
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT
IMG = Path(os.environ.get("CAPTURAS_SALIDA") or Path(__file__).resolve().parent / "img")
IMG.mkdir(exist_ok=True)

# "light" / "dark" (the old "claro" / "oscuro" are still accepted)
THEME = {"claro": "light", "oscuro": "dark"}.get(sys.argv[1], sys.argv[1]) \
    if len(sys.argv) > 1 else "dark"
SUFFIX = "" if THEME == "dark" else "_claro"      # the image names keep their Spanish suffix

# Sample folder with a neutral path, so that the Windows user name
# does not appear in the screenshots (as it would with the temporary folder).
BASE_DEMO = Path(os.environ.get("CAPTURAS_BASE", "C:/Demo"))
BASE_DEMO.mkdir(parents=True, exist_ok=True)
tmp = BASE_DEMO / "muestra"
shutil.rmtree(tmp, ignore_errors=True)       # only this script's sample folder
tmp.mkdir()
os.environ["APPDATA"] = str(tmp / "appdata")
sys.path.insert(0, str(APP))

from PIL import Image, ImageDraw, ImageGrab            # noqa: E402
from ui import styles, icons                            # noqa: E402
from ui.main_window import MainWindow             # noqa: E402
from ui.image_viewer import ImageViewer                 # noqa: E402
from ui.history_window import HistoryWindow          # noqa: E402
from ui.non_image_kinds_dialog import NonImageKindsWindow        # noqa: E402
from core import history                              # noqa: E402

FIXED_DATE = datetime(2026, 1, 15, 12, 0, 0)


class _FixedNow(datetime):
    """datetime.now() with fixed dates (one more per call, so that the ids do not clash)."""

    _n = 0

    @classmethod
    def now(cls, tz=None):
        cls._n += 1
        return FIXED_DATE + timedelta(seconds=cls._n)


history.datetime = _FixedNow


def photo(seed, size=(220, 150)):
    rnd = __import__("random").Random(seed)
    im = Image.new("RGB", size, (24, 28, 36))
    d = ImageDraw.Draw(im)
    for _ in range(9):
        x, y = rnd.randint(0, size[0]), rnd.randint(0, size[1])
        col = (rnd.randint(40, 235), rnd.randint(40, 235), rnd.randint(60, 235))
        if rnd.random() < 0.5:
            d.ellipse([x, y, x + rnd.randint(30, 90), y + rnd.randint(30, 90)], fill=col)
        else:
            d.rectangle([x, y, x + rnd.randint(30, 90), y + rnd.randint(30, 90)], fill=col)
    return im


def snap(widget, name):
    widget.update_idletasks()
    widget.update()
    x, y = widget.winfo_rootx(), widget.winfo_rooty()
    w, h = widget.winfo_width(), widget.winfo_height()
    destination = IMG / name.replace(".png", f"{SUFFIX}.png")
    ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True).save(destination)
    print("  ", name)


# ---- set up sample folders -----------------------------------
base_dup = tmp / "Fotos"
for rel in ("2023/verano/playa.png", "2023/verano/atardecer.png",
            "Descargas/playa.png", "Descargas/atardecer (1).png",
            "Escritorio/portada.png"):
    p = base_dup / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    photo(zlib.crc32(rel.encode()) % 999).save(p)
# EXACT duplicates
b = (base_dup / "2023/verano/playa.png").read_bytes()
(base_dup / "Descargas/playa.png").write_bytes(b)
b2 = (base_dup / "2023/verano/atardecer.png").read_bytes()
(base_dup / "Descargas/atardecer (1).png").write_bytes(b2)

gather_base = tmp / "Movil"
for rel in ("WhatsApp/img1.jpg", "WhatsApp/img2.jpg", "Camara/DCIM/foto.jpg",
            "Camara/DCIM/foto2.jpg", "Descargas/meme.png", "captura.png"):
    p = gather_base / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    photo(zlib.crc32(rel.encode()) % 999).save(p)
(gather_base / "Camara/notas.txt").write_text("x")
(gather_base / "Descargas/factura.pdf").write_bytes(b"%PDF")

# Fixed modification dates (the preview shows them).
for _f in tmp.rglob('*'):
    os.utime(_f, (FIXED_DATE.timestamp(), FIXED_DATE.timestamp()))

# sample history
history.record(history.KIND_QUARANTINE, "move", str(base_dup), str(tmp / "Cuarentena"),
                    [(str(base_dup / "x"), str(tmp / "Cuarentena" / "x"))] * 4,
                    "4 duplicados exactos")
history.record(history.KIND_GATHER, "copy", str(gather_base), str(tmp / "Album"),
                    [(str(gather_base / "y"), str(tmp / "Album" / "y"))] * 12,
                    "12 imágenes")

styles.apply_theme(THEME)
app = MainWindow()
app.geometry("1280x860+12+6")

STEPS = []


def add(fn, delay=700):
    STEPS.append((fn, delay))


def run():
    if not STEPS:
        app.after(200, app.destroy)
        return
    fn, delay = STEPS.pop(0)
    fn()
    app.after(delay, run)


# --- Simple --------------------------------------------------------
def p_simple_scan():
    app._mode = "simple"
    app._apply_mode()
    app.mode_selector.set("Sencilla")
    app.exact.entry_folder.insert(0, str(base_dup))
    app.exact._start_scan()


def p_simple_shot():
    for iid, meta in app.exact.table._meta.items():
        if meta[0] == "file" and meta[2].endswith("playa.png"):
            app.exact.table.tree.selection_set(iid)
            app.exact.table.tree.see(iid)
            break
    snap(app, "01_sencilla.png")


# --- Advanced --------------------------------------------------
def p_advanced():
    app._mode = "advanced"
    app._apply_mode()
    app.mode_selector.set("Avanzada")
    app.exact._on_selection_change()


def p_advanced_shot():
    snap(app, "02_avanzada.png")


def p_options():
    app.exact._toggle_options()
    app.exact._default_filters()
    app.exact.chk_categories["Imágenes"].select()
    app.exact._toggle_category("Imágenes")


def p_options_shot():
    snap(app, "03_opciones.png")
    app.exact._toggle_options()


# --- Similar ------------------------------------------------
def p_similar():
    app.tabs.set(f"{icons.CAT_IMAGES}  Fotos parecidas")
    app.similar.entry_folder.insert(0, str(base_dup))
    app.similar.sensitivity_slider.set(13)
    app.similar._start()


def p_similar_shot():
    snap(app, "04_parecidas.png")


# --- Gather --------------------------------------------------
def p_gather():
    app.tabs.set(f"{icons.GATHER}  Reunir imágenes")
    app.gather.entry_folder.insert(0, str(gather_base))
    app.gather.entry_destination.insert(0, str(tmp / "Todas mis fotos"))
    app.gather._search()


def p_gather_shot():
    snap(app, "05_reunir.png")


# --- Dialogs -----------------------------------------------
def p_kinds():
    from core.gather import non_image_kinds, list_all
    _img, others = list_all(str(gather_base))
    dlg = NonImageKindsWindow(app, non_image_kinds(others))
    dlg.geometry("620x420+200+140")
    app._dlg = dlg


def p_kinds_shot():
    snap(app._dlg, "06_tipos.png")
    app._dlg.destroy()


def p_history():
    hv = HistoryWindow(app)
    hv.geometry("720x520+160+90")
    app._hv = hv


def p_history_shot():
    snap(app._hv, "07_historial.png")
    app._hv.destroy()


def p_viewer():
    img = tmp / "detalle.png"
    Image.new("RGB", (1200, 820), (18, 22, 30))
    im = Image.new("RGB", (1200, 820), (18, 22, 30))
    d = ImageDraw.Draw(im)
    for i in range(0, 1200, 48):
        d.line([(i, 0), (i, 820)], fill=(42, 48, 60))
    for i in range(0, 820, 48):
        d.line([(0, i), (1200, i)], fill=(42, 48, 60))
    d.ellipse([260, 180, 620, 540], fill=(70, 160, 220))
    d.rectangle([720, 260, 1080, 620], fill=(230, 180, 70))
    im.save(img)
    v = ImageViewer(app, str(img))
    v.geometry("1040x720+80+40")
    v._set_scale(0.9)
    app._v = v


def p_viewer_shot():
    snap(app._v, "08_visor.png")
    app._v.destroy()


add(p_simple_scan, 1700)
add(p_simple_shot, 900)
add(p_advanced, 500)
add(p_advanced_shot, 700)
add(p_options, 500)
add(p_options_shot, 700)
add(p_similar, 2600)
add(p_similar_shot, 700)
add(p_gather, 1500)
add(p_gather_shot, 800)
add(p_kinds, 500)
add(p_kinds_shot, 600)
add(p_history, 500)
add(p_history_shot, 600)
add(p_viewer, 700)
add(p_viewer_shot, 700)

app.after(600, run)
app.after(40000, app.destroy)
app.mainloop()
print("Capturas en", IMG)

# Cleanup: deletes only the sample folder created by this script.
shutil.rmtree(tmp, ignore_errors=True)
try:
    BASE_DEMO.rmdir()          # only if it has been left empty
except OSError:
    pass
