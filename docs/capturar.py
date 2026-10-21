"""Genera las capturas de pantalla para la documentación.

    python docs/capturar.py             # tema oscuro  -> 01_sencilla.png ...
    python docs/capturar.py claro       # tema claro   -> 01_sencilla_claro.png ...

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

RAIZ = Path(__file__).resolve().parents[1]
APP = RAIZ
IMG = Path(os.environ.get("CAPTURAS_SALIDA") or Path(__file__).resolve().parent / "img")
IMG.mkdir(exist_ok=True)

TEMA = sys.argv[1] if len(sys.argv) > 1 else "oscuro"
SUFIJO = "" if TEMA == "oscuro" else f"_{TEMA}"

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
from ui.main_window import VentanaPrincipal             # noqa: E402
from ui.image_viewer import VisorImagen                 # noqa: E402
from ui.history_window import VentanaHistorial          # noqa: E402
from ui.tipos_dialog import VentanaTiposNoImagen        # noqa: E402
from core import historial                              # noqa: E402

FECHA_FIJA = datetime(2026, 1, 15, 12, 0, 0)


class _AhoraFijo(datetime):
    """datetime.now() con fechas fijas (una más por llamada, para que los ids no choquen)."""

    _n = 0

    @classmethod
    def now(cls, tz=None):
        cls._n += 1
        return FECHA_FIJA + timedelta(seconds=cls._n)


historial.datetime = _AhoraFijo


def foto(semilla, size=(220, 150)):
    rnd = __import__("random").Random(semilla)
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


def snap(widget, nombre):
    widget.update_idletasks()
    widget.update()
    x, y = widget.winfo_rootx(), widget.winfo_rooty()
    w, h = widget.winfo_width(), widget.winfo_height()
    destino = IMG / nombre.replace(".png", f"{SUFIJO}.png")
    ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True).save(destino)
    print("  ", nombre)


# ---- montar carpetas de ejemplo -----------------------------------
base_dup = tmp / "Fotos"
for rel in ("2023/verano/playa.png", "2023/verano/atardecer.png",
            "Descargas/playa.png", "Descargas/atardecer (1).png",
            "Escritorio/portada.png"):
    p = base_dup / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    foto(zlib.crc32(rel.encode()) % 999).save(p)
# duplicados EXACTOS
b = (base_dup / "2023/verano/playa.png").read_bytes()
(base_dup / "Descargas/playa.png").write_bytes(b)
b2 = (base_dup / "2023/verano/atardecer.png").read_bytes()
(base_dup / "Descargas/atardecer (1).png").write_bytes(b2)

base_reunir = tmp / "Movil"
for rel in ("WhatsApp/img1.jpg", "WhatsApp/img2.jpg", "Camara/DCIM/foto.jpg",
            "Camara/DCIM/foto2.jpg", "Descargas/meme.png", "captura.png"):
    p = base_reunir / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    foto(zlib.crc32(rel.encode()) % 999).save(p)
(base_reunir / "Camara/notas.txt").write_text("x")
(base_reunir / "Descargas/factura.pdf").write_bytes(b"%PDF")

# Fechas de modificación fijas (la vista previa las enseña).
for _f in tmp.rglob('*'):
    os.utime(_f, (FECHA_FIJA.timestamp(), FECHA_FIJA.timestamp()))

# historial de ejemplo
historial.registrar("cuarentena", "mover", str(base_dup), str(tmp / "Cuarentena"),
                    [(str(base_dup / "x"), str(tmp / "Cuarentena" / "x"))] * 4,
                    "4 duplicados exactos")
historial.registrar("reunir", "copiar", str(base_reunir), str(tmp / "Album"),
                    [(str(base_reunir / "y"), str(tmp / "Album" / "y"))] * 12,
                    "12 imágenes")

styles.aplicar_tema(TEMA)
app = VentanaPrincipal()
app.geometry("1280x860+12+6")

PASOS = []


def add(fn, retardo=700):
    PASOS.append((fn, retardo))


def correr():
    if not PASOS:
        app.after(200, app.destroy)
        return
    fn, retardo = PASOS.pop(0)
    fn()
    app.after(retardo, correr)


# --- Sencilla ----------------------------------------------------
def p_sencilla_scan():
    app._modo = "sencillo"
    app._aplicar_modo()
    app.selector_modo.set("Sencilla")
    app.exactos.entry_carpeta.insert(0, str(base_dup))
    app.exactos._iniciar_escaneo()


def p_sencilla_shot():
    for iid, meta in app.exactos.tabla._meta.items():
        if meta[0] == "archivo" and meta[2].endswith("playa.png"):
            app.exactos.tabla.tree.selection_set(iid)
            app.exactos.tabla.tree.see(iid)
            break
    snap(app, "01_sencilla.png")


# --- Avanzada --------------------------------------------------
def p_avanzada():
    app._modo = "avanzado"
    app._aplicar_modo()
    app.selector_modo.set("Avanzada")
    app.exactos._al_cambiar_seleccion()


def p_avanzada_shot():
    snap(app, "02_avanzada.png")


def p_opciones():
    app.exactos._alternar_opciones()
    app.exactos._filtros_por_defecto()
    app.exactos.chk_categorias["Imágenes"].select()
    app.exactos._alternar_categoria("Imágenes")


def p_opciones_shot():
    snap(app, "03_opciones.png")
    app.exactos._alternar_opciones()


# --- Parecidas ------------------------------------------------
def p_parecidas():
    app.tabs.set(f"{icons.CAT_IMAGENES}  Fotos parecidas")
    app.parecidas.entry_carpeta.insert(0, str(base_dup))
    app.parecidas.slider_sensibilidad.set(13)
    app.parecidas._iniciar()


def p_parecidas_shot():
    snap(app, "04_parecidas.png")


# --- Reunir --------------------------------------------------
def p_reunir():
    app.tabs.set(f"{icons.REUNIR}  Reunir imágenes")
    app.reunir.entry_carpeta.insert(0, str(base_reunir))
    app.reunir.entry_destino.insert(0, str(tmp / "Todas mis fotos"))
    app.reunir._buscar()


def p_reunir_shot():
    snap(app, "05_reunir.png")


# --- Diálogos -----------------------------------------------
def p_tipos():
    from core.reunir import tipos_no_imagen, listar
    _img, otros = listar(str(base_reunir))
    dlg = VentanaTiposNoImagen(app, tipos_no_imagen(otros))
    dlg.geometry("620x420+200+140")
    app._dlg = dlg


def p_tipos_shot():
    snap(app._dlg, "06_tipos.png")
    app._dlg.destroy()


def p_historial():
    hv = VentanaHistorial(app)
    hv.geometry("720x520+160+90")
    app._hv = hv


def p_historial_shot():
    snap(app._hv, "07_historial.png")
    app._hv.destroy()


def p_visor():
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
    v = VisorImagen(app, str(img))
    v.geometry("1040x720+80+40")
    v._set_escala(0.9)
    app._v = v


def p_visor_shot():
    snap(app._v, "08_visor.png")
    app._v.destroy()


add(p_sencilla_scan, 1700)
add(p_sencilla_shot, 900)
add(p_avanzada, 500)
add(p_avanzada_shot, 700)
add(p_opciones, 500)
add(p_opciones_shot, 700)
add(p_parecidas, 2600)
add(p_parecidas_shot, 700)
add(p_reunir, 1500)
add(p_reunir_shot, 800)
add(p_tipos, 500)
add(p_tipos_shot, 600)
add(p_historial, 500)
add(p_historial_shot, 600)
add(p_visor, 700)
add(p_visor_shot, 700)

app.after(600, correr)
app.after(40000, app.destroy)
app.mainloop()
print("Capturas en", IMG)

# Limpieza: borra solo la carpeta de ejemplo que creó este script.
shutil.rmtree(tmp, ignore_errors=True)
try:
    BASE_DEMO.rmdir()          # solo si ha quedado vacía
except OSError:
    pass
