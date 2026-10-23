"""Genera las capturas de pantalla para la documentación.

    python docs/capture.py             # tema oscuro  -> 01_sencilla.png ...
    python docs/capture.py claro       # tema claro   -> 01_sencilla_claro.png ...

Guarda PNG en docs/img/ (o en la carpeta de la variable CAPTURAS_SALIDA). Cada
captura acota el recorte a la ventana de la propia app (nunca al escritorio completo).

Es DETERMINISTA: carpeta de ejemplo con nombre fijo, fotos generadas siempre iguales y
fechas fijas. Dos ejecuciones seguidas dan imágenes idénticas píxel a píxel, y eso sirve
para comprobar que un cambio interno de la app no ha alterado su aspecto.
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

THEME = sys.argv[1] if len(sys.argv) > 1 else "oscuro"
SUFFIX = "" if THEME == "oscuro" else f"_{THEME}"

# Carpeta de ejemplo con ruta neutra, para que en las capturas no salga el
# nombre de usuario de Windows (como pasaría con la carpeta temporal).
BASE_DEMO = Path(os.environ.get("CAPTURAS_BASE", "C:/Demo"))
BASE_DEMO.mkdir(parents=True, exist_ok=True)
tmp = BASE_DEMO / "muestra"
shutil.rmtree(tmp, ignore_errors=True)       # solo la carpeta de ejemplo de este script
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
    """datetime.now() con fechas fijas (una más por llamada, para que los ids no choquen)."""

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


# ---- montar carpetas de ejemplo -----------------------------------
base_dup = tmp / "Fotos"
for rel in ("2023/verano/playa.png", "2023/verano/atardecer.png",
            "Descargas/playa.png", "Descargas/atardecer (1).png",
            "Escritorio/portada.png"):
    p = base_dup / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    photo(zlib.crc32(rel.encode()) % 999).save(p)
# duplicados EXACTOS
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

# Fechas de modificación fijas (la vista previa las enseña).
for _f in tmp.rglob('*'):
    os.utime(_f, (FIXED_DATE.timestamp(), FIXED_DATE.timestamp()))

# historial de ejemplo
history.record("cuarentena", "mover", str(base_dup), str(tmp / "Cuarentena"),
                    [(str(base_dup / "x"), str(tmp / "Cuarentena" / "x"))] * 4,
                    "4 duplicados exactos")
history.record("reunir", "copiar", str(gather_base), str(tmp / "Album"),
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


# --- Sencilla ----------------------------------------------------
def p_simple_scan():
    app._mode = "sencillo"
    app._apply_mode()
    app.mode_selector.set("Sencilla")
    app.exact.entry_folder.insert(0, str(base_dup))
    app.exact._start_scan()


def p_simple_shot():
    for iid, meta in app.exact.table._meta.items():
        if meta[0] == "archivo" and meta[2].endswith("playa.png"):
            app.exact.table.tree.selection_set(iid)
            app.exact.table.tree.see(iid)
            break
    snap(app, "01_sencilla.png")


# --- Avanzada --------------------------------------------------
def p_advanced():
    app._mode = "avanzado"
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


# --- Parecidas ------------------------------------------------
def p_similar():
    app.tabs.set(f"{icons.CAT_IMAGES}  Fotos parecidas")
    app.similar.entry_folder.insert(0, str(base_dup))
    app.similar.sensitivity_slider.set(13)
    app.similar._start()


def p_similar_shot():
    snap(app, "04_parecidas.png")


# --- Reunir --------------------------------------------------
def p_gather():
    app.tabs.set(f"{icons.GATHER}  Reunir imágenes")
    app.gather.entry_folder.insert(0, str(gather_base))
    app.gather.entry_destination.insert(0, str(tmp / "Todas mis fotos"))
    app.gather._search()


def p_gather_shot():
    snap(app, "05_reunir.png")


# --- Diálogos -----------------------------------------------
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

# Limpieza: borra solo la carpeta de ejemplo que creó este script.
shutil.rmtree(tmp, ignore_errors=True)
try:
    BASE_DEMO.rmdir()          # solo si ha quedado vacía
except OSError:
    pass
