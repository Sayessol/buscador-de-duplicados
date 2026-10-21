"""Graba docs/img/demo.gif: escanear -> mover a cuarentena -> deshacer.

    python docs/grabar_gif.py

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

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = Path(__file__).resolve().parent / "img" / "demo.gif"
ANCHO_GIF = 960                    # ancho final del GIF (más pequeño = menos MB)
INTERVALO_MS = 90                  # cada cuánto se captura un fotograma

BASE_DEMO = Path(os.environ.get("CAPTURAS_BASE", "C:/Demo"))
BASE_DEMO.mkdir(parents=True, exist_ok=True)
tmp = Path(tempfile.mkdtemp(prefix="", dir=BASE_DEMO))
os.environ["APPDATA"] = str(tmp / "appdata")        # no toca tu configuración real
sys.path.insert(0, str(RAIZ))

from PIL import Image, ImageChops, ImageDraw, ImageGrab     # noqa: E402

from core import historial                                  # noqa: E402
from ui import styles                                       # noqa: E402
from ui.history_window import VentanaHistorial              # noqa: E402
from ui.main_window import VentanaPrincipal                 # noqa: E402


def foto(semilla, size=(240, 160)):
    rnd = random.Random(semilla)
    im = Image.new("RGB", size, (24, 28, 36))
    d = ImageDraw.Draw(im)
    for _ in range(9):
        x, y = rnd.randint(0, size[0]), rnd.randint(0, size[1])
        col = (rnd.randint(40, 235), rnd.randint(40, 235), rnd.randint(60, 235))
        caja = [x, y, x + rnd.randint(30, 90), y + rnd.randint(30, 90)]
        (d.ellipse if rnd.random() < .5 else d.rectangle)(caja, fill=col)
    return im


# ---- carpetas de ejemplo --------------------------------------------------
base = tmp / "Fotos"
nombres = {"2023/verano/playa.png": 1, "2023/verano/atardecer.png": 2,
           "2023/cumple.png": 3, "Descargas/montaña.png": 4, "Escritorio/portada.png": 5}
for rel, semilla in nombres.items():
    ruta = base / rel
    ruta.parent.mkdir(parents=True, exist_ok=True)
    foto(semilla).save(ruta)
for origen, copia in [("2023/verano/playa.png", "Descargas/playa.png"),
                      ("2023/verano/atardecer.png", "Descargas/atardecer (1).png"),
                      ("2023/cumple.png", "Escritorio/cumple - copia.png")]:
    (base / copia).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(base / origen, base / copia)
cuarentena = tmp / "Cuarentena"
cuarentena.mkdir()

# ---- diálogos simulados -----------------------------------------------------
filedialog.askdirectory = lambda *a, **k: str(cuarentena)
messagebox.askyesno = lambda *a, **k: True
os.startfile = lambda *a, **k: None   # sin esto se abriría el Explorador de verdad
messagebox.showinfo = lambda *a, **k: None
messagebox.showwarning = lambda *a, **k: None
messagebox.showerror = lambda *a, **k: None

styles.aplicar_tema("oscuro")
app = VentanaPrincipal()
app._modo = "sencillo"
app._aplicar_modo()
app.geometry("1280x860+12+6")

fotogramas = []                    # (instante, imagen)


def capturar():
    app.update_idletasks()
    x, y = app.winfo_rootx(), app.winfo_rooty()
    w, h = app.winfo_width(), app.winfo_height()
    im = ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True).convert("RGB")
    fotogramas.append((time.perf_counter(), im))
    app.after(INTERVALO_MS, capturar)


# ---- guion ---------------------------------------------------------------------
ruta_texto = str(base)
estado = {"i": 0}


def escribir_ruta():
    if estado["i"] < len(ruta_texto):
        estado["i"] += 3
        app.exactos.entry_carpeta.delete(0, "end")
        app.exactos.entry_carpeta.insert(0, ruta_texto[:estado["i"]])
        app.after(45, escribir_ruta)
    else:
        app.after(500, escanear)


def escanear():
    app.exactos._iniciar_escaneo()
    esperar(lambda: app.exactos._seleccion is not None, elegir_fila)


def esperar(condicion, siguiente, intentos=200):
    if condicion() or intentos == 0:
        app.after(900, siguiente)
    else:
        app.after(100, lambda: esperar(condicion, siguiente, intentos - 1))


def elegir_fila():
    for iid, meta in app.exactos.tabla._meta.items():
        if meta[0] == "archivo" and meta[2].endswith("playa.png"):
            app.exactos.tabla.tree.selection_set(iid)
            app.exactos.tabla.tree.see(iid)
            break
    app.after(1700, mover)


def mover():
    app.exactos._mover_a_cuarentena()
    esperar(lambda: bool(historial.listar()), abrir_historial)


def abrir_historial():
    app._modo = "avanzado"
    app._aplicar_modo()
    app.selector_modo.set("Avanzada")
    app._hv = VentanaHistorial(app)
    app._hv.geometry("720x520+300+120")
    app.after(1800, deshacer)


def deshacer():
    app._hv._deshacer(historial.listar()[0])
    app.after(2200, cerrar)


def cerrar():
    app._hv.destroy()
    app.after(600, reescanear)


def reescanear():
    # Tras deshacer, los archivos están otra vez en su sitio: se vuelve a escanear.
    anterior = app.exactos._resultado
    app.exactos._iniciar_escaneo()
    esperar(lambda: app.exactos._resultado is not anterior, lambda: app.after(2200, app.destroy))


app.after(300, capturar)
app.after(1200, escribir_ruta)
app.after(60000, app.destroy)
app.mainloop()

# ---- montar el GIF ------------------------------------------------------------
alto = round(fotogramas[0][1].height * ANCHO_GIF / fotogramas[0][1].width)
imgs, duraciones, anterior = [], [], None
for (t0, im), siguiente in zip(fotogramas, fotogramas[1:] + [(fotogramas[-1][0] + .6, None)]):
    dur = max(int((siguiente[0] - t0) * 1000), 40)
    chica = im.resize((ANCHO_GIF, alto), Image.LANCZOS)
    if anterior is not None and ImageChops.difference(chica, anterior).getbbox() is None:
        duraciones[-1] += dur                     # fotograma igual: se alarga el anterior
        continue
    imgs.append(chica.quantize(colors=128, method=Image.Quantize.MEDIANCUT,
                               dither=Image.Dither.NONE))
    duraciones.append(dur)
    anterior = chica
imgs[0].save(SALIDA, save_all=True, append_images=imgs[1:], duration=duraciones,
             loop=0, optimize=True, disposal=1)
print(f"{SALIDA.name}: {len(imgs)} fotogramas, {SALIDA.stat().st_size / 1e6:.1f} MB, "
      f"{sum(duraciones) / 1000:.1f} s")

# Limpieza: borra solo la carpeta de ejemplo que creó este script.
shutil.rmtree(tmp, ignore_errors=True)
try:
    BASE_DEMO.rmdir()
except OSError:
    pass
