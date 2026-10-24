"""Generates the screenshots for the documentation.

    python docs/capture.py                 # dark theme, Spanish -> docs/img/es/01_simple.png ...
    python docs/capture.py light           # light theme -> docs/img/es/01_simple_light.png ...
    python docs/capture.py dark en         # the second argument is the language: es (default) or en

It saves PNGs in docs/img/<language>/ (or under the folder of the CAPTURE_OUTPUT variable).
Each capture limits the crop to the window of the app itself (never to the whole desktop). The
sample folders and files get names in the language of the interface, so the screenshots read
naturally.

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
THEME = sys.argv[1] if len(sys.argv) > 1 else "dark"
SUFFIX = "" if THEME == "dark" else "_light"
LANGUAGE = sys.argv[2] if len(sys.argv) > 2 else "es"
assert THEME in ("dark", "light") and LANGUAGE in ("es", "en"), \
    "usage: capture.py [dark|light] [es|en]"
IMG = Path(os.environ.get("CAPTURE_OUTPUT") or Path(__file__).resolve().parent / "img") / LANGUAGE
IMG.mkdir(parents=True, exist_ok=True)


def T(es, en):
    """The sample name in the language of the screenshots."""
    return es if LANGUAGE == "es" else en



# Sample folder with a neutral path, so that the Windows user name
# does not appear in the screenshots (as it would with the temporary folder).
BASE_DEMO = Path(os.environ.get("CAPTURE_BASE", "C:/Demo"))
BASE_DEMO.mkdir(parents=True, exist_ok=True)
tmp = BASE_DEMO / T("muestra", "sample")
shutil.rmtree(tmp, ignore_errors=True)       # only this script's sample folder
tmp.mkdir()
os.environ["APPDATA"] = str(tmp / "appdata")
sys.path.insert(0, str(APP))
sys.path.insert(0, str(APP / "src"))

from PIL import Image, ImageDraw, ImageGrab            # noqa: E402
from duplicate_finder.presentation import styles  # noqa: E402
from duplicate_finder.presentation.main_window import MainWindow  # noqa: E402
from duplicate_finder.presentation.image_viewer import ImageViewer  # noqa: E402
from duplicate_finder.presentation.history_window import HistoryWindow  # noqa: E402
from duplicate_finder.presentation.non_image_kinds_dialog import NonImageKindsWindow  # noqa: E402
from duplicate_finder import i18n  # noqa: E402
from duplicate_finder.application import history as history_module  # noqa: E402
from duplicate_finder.domain.operations import KIND_GATHER, KIND_QUARANTINE  # noqa: E402
from duplicate_finder.bootstrap import build_services  # noqa: E402

SERVICES = build_services()
history = SERVICES.history

FIXED_DATE = datetime(2026, 1, 15, 12, 0, 0)


class _FixedNow(datetime):
    """datetime.now() with fixed dates (one more per call, so that the ids do not clash)."""

    _n = 0

    @classmethod
    def now(cls, tz=None):
        cls._n += 1
        return FIXED_DATE + timedelta(seconds=cls._n)


history_module.datetime = _FixedNow


i18n.set_language(LANGUAGE)


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
BEACH, SUNSET = T("playa.png", "beach.png"), T("atardecer.png", "sunset.png")
SUMMER, DOWNLOADS = T("verano", "summer"), T("Descargas", "Downloads")
SUNSET_COPY = T("atardecer (1).png", "sunset (1).png")
base_dup = tmp / T("Fotos", "Photos")
for rel in (f"2023/{SUMMER}/{BEACH}", f"2023/{SUMMER}/{SUNSET}",
            f"{DOWNLOADS}/{BEACH}", f"{DOWNLOADS}/{SUNSET_COPY}",
            f"{T('Escritorio', 'Desktop')}/{T('portada.png', 'cover.png')}"):
    p = base_dup / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    photo(zlib.crc32(rel.encode()) % 999).save(p)
# EXACT duplicates
b = (base_dup / f"2023/{SUMMER}/{BEACH}").read_bytes()
(base_dup / f"{DOWNLOADS}/{BEACH}").write_bytes(b)
b2 = (base_dup / f"2023/{SUMMER}/{SUNSET}").read_bytes()
(base_dup / f"{DOWNLOADS}/{SUNSET_COPY}").write_bytes(b2)

gather_base = tmp / T("Movil", "Phone")
CAMERA = T("Camara", "Camera")
PHOTO = T("foto", "photo")
for rel in ("WhatsApp/img1.jpg", "WhatsApp/img2.jpg", f"{CAMERA}/DCIM/{PHOTO}.jpg",
            f"{CAMERA}/DCIM/{PHOTO}2.jpg", f"{DOWNLOADS}/meme.png",
            f"{T('captura', 'screenshot')}.png"):
    p = gather_base / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    photo(zlib.crc32(rel.encode()) % 999).save(p)
(gather_base / f"{CAMERA}/{T('notas', 'notes')}.txt").write_text("x")
(gather_base / f"{DOWNLOADS}/{T('factura', 'invoice')}.pdf").write_bytes(b"%PDF")

# Fixed modification dates (the preview shows them).
for _f in tmp.rglob('*'):
    os.utime(_f, (FIXED_DATE.timestamp(), FIXED_DATE.timestamp()))

# sample history
quarantine_folder = tmp / T("Cuarentena", "Quarantine")
history.record(KIND_QUARANTINE, "move", str(base_dup), str(quarantine_folder),
               [(str(base_dup / "x"), str(quarantine_folder / "x"))] * 4,
               i18n.tr("history.description_exact", count=4))
history.record(KIND_GATHER, "copy", str(gather_base), str(tmp / "Album"),
               [(str(gather_base / "y"), str(tmp / "Album" / "y"))] * 12,
               i18n.tr("gather.description_files", count=12))

styles.apply_theme(THEME)
app = MainWindow(SERVICES)
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
    app.mode_selector.set_key("simple")
    app.exact.entry_folder.insert(0, str(base_dup))
    app.exact._start_scan()


def p_simple_shot():
    for iid, meta in app.exact.table._meta.items():
        if meta[0] == "file" and meta[2].endswith(BEACH):
            app.exact.table.tree.selection_set(iid)
            app.exact.table.tree.see(iid)
            break
    snap(app, "01_simple.png")


# --- Advanced --------------------------------------------------
def p_advanced():
    app._mode = "advanced"
    app._apply_mode()
    app.mode_selector.set_key("advanced")
    app.exact._on_selection_change()


def p_advanced_shot():
    snap(app, "02_advanced.png")


def p_options():
    app.exact.options.toggle()
    app.exact.options.reset_to_defaults()
    app.exact.options.chk_categories["images"].select()
    app.exact.options.toggle_category("images")


def p_options_shot():
    snap(app, "03_options.png")
    app.exact.options.toggle()


# --- Similar ------------------------------------------------
def p_similar():
    app.show_tab("similar")
    app.similar.entry_folder.insert(0, str(base_dup))
    app.similar.sensitivity_slider.set(13)
    app.similar._start()


def p_similar_shot():
    snap(app, "04_similar.png")


# --- Gather --------------------------------------------------
def p_gather():
    app.show_tab("gather")
    app.gather.entry_folder.insert(0, str(gather_base))
    app.gather.entry_destination.insert(0, str(tmp / T("Todas mis fotos", "All my photos")))
    app.gather._search()


def p_gather_shot():
    snap(app, "05_gather.png")


# --- Dialogs -----------------------------------------------
def p_kinds():
    from duplicate_finder.application.gather import non_image_kinds

    list_all = SERVICES.gather.list_all
    _img, others = list_all(str(gather_base))
    dlg = NonImageKindsWindow(app, non_image_kinds(others))
    dlg.geometry("620x420+200+140")
    app._dlg = dlg


def p_kinds_shot():
    snap(app._dlg, "06_types.png")
    app._dlg.destroy()


def p_history():
    hv = HistoryWindow(app, history)
    hv.geometry("720x520+160+90")
    app._hv = hv


def p_history_shot():
    snap(app._hv, "07_history.png")
    app._hv.destroy()


def p_viewer():
    img = tmp / T("detalle.png", "detail.png")
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
    snap(app._v, "08_viewer.png")
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
print("Screenshots in", IMG)

# Cleanup: deletes only the sample folder created by this script.
shutil.rmtree(tmp, ignore_errors=True)
try:
    BASE_DEMO.rmdir()          # only if it has been left empty
except OSError:
    pass
