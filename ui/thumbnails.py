"""Miniaturas y previsualizaciones de archivos.

Devuelve objetos PIL.Image (se pueden crear en un hilo secundario); la
conversión a CTkImage / ImageTk.PhotoImage se hace luego en el hilo de
la interfaz.

- Archivos de imagen  -> miniatura real.
- Cualquier otro       -> un recuadro con la extensión (".pdf", ".mp3"…)
                          y un color según la categoría.
"""

import os
import threading

from PIL import Image, ImageDraw, ImageFont, ImageOps

from core.filtros import CATEGORIAS_EXTENSIONES
from core.registro import log

LADO_MINIATURA = 150
LADO_FILA = 40          # miniatura pequeña de cada fila de la tabla
LADO_VISTA = 250        # panel de vista grande

# Color de fondo del placeholder según la categoría del archivo.
_COLOR_CATEGORIA = {
    "Imágenes": "#3f6d52",
    "Audio": "#54487a",
    "Vídeo": "#7a4a4a",
    "Documentos": "#3a5a7a",
    "Comprimidos": "#7a6234",
}
_COLOR_OTRO = "#454545"
_COLOR_TEXTO = "#eaeef4"

EXT_IMAGEN = CATEGORIAS_EXTENSIONES["Imágenes"] | {"jpe", "ppm", "pgm"}

# Caché en memoria: (ruta, lado) -> PIL.Image. Se limpia al reescanear.
_cache = {}
_cache_lock = threading.Lock()


def limpiar_cache():
    with _cache_lock:
        _cache.clear()


def _categoria_de(ext):
    for nombre, exts in CATEGORIAS_EXTENSIONES.items():
        if ext in exts:
            return nombre
    return None


def _fuente(tam):
    for nombre in ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(nombre, tam)
        except OSError:
            continue
    return ImageFont.load_default()


def placeholder_extension(ruta, lado=LADO_MINIATURA):
    ext = os.path.splitext(ruta)[1].lower().lstrip(".")
    color = _COLOR_CATEGORIA.get(_categoria_de(ext), _COLOR_OTRO)
    im = Image.new("RGB", (lado, lado), color)
    d = ImageDraw.Draw(im)

    texto = f".{ext}" if ext else "sin ext."
    fuente = _fuente(max(10, int(lado * (0.30 if len(texto) <= 4 else 0.20))))
    izq, arr, der, aba = d.textbbox((0, 0), texto, font=fuente)
    d.text(((lado - (der - izq)) / 2 - izq, (lado - (aba - arr)) / 2 - arr),
           texto, fill=_COLOR_TEXTO, font=fuente)
    return im


def cargar_miniatura(ruta, lado=LADO_MINIATURA):
    """PIL.Image cuadrada `lado`x`lado` (recorte centrado) de una imagen.

    Lanza si el archivo no se puede abrir como imagen.
    """
    with Image.open(ruta) as im:
        try:
            im.draft("RGB", (lado * 2, lado * 2))
        except (ValueError, OSError):  # draft es opcional
            pass
        im = ImageOps.exif_transpose(im).convert("RGB")
        return ImageOps.fit(im, (lado, lado), Image.BOX)


def miniatura_o_placeholder(ruta, lado=LADO_FILA):
    """Miniatura real si es imagen; si no (o si falla), placeholder."""
    clave = (ruta, lado)
    with _cache_lock:
        if clave in _cache:
            return _cache[clave]

    ext = os.path.splitext(ruta)[1].lower().lstrip(".")
    img = None
    if ext in EXT_IMAGEN:
        try:
            img = cargar_miniatura(ruta, lado)
        except Exception as e:  # un archivo roto no debe romper la lista
            log.info("No se pudo crear la miniatura de %s: %s", ruta, e)
            img = None
    if img is None:
        img = placeholder_extension(ruta, lado)

    with _cache_lock:
        _cache[clave] = img
    return img


def vista_grande(ruta, lado=LADO_VISTA):
    """PIL.Image para el panel de vista previa: imagen a tamaño (sin
    recortar, encajada en un cuadrado) o placeholder grande."""
    ext = os.path.splitext(ruta)[1].lower().lstrip(".")
    if ext in EXT_IMAGEN:
        try:
            with Image.open(ruta) as im:
                try:
                    im.draft("RGB", (lado * 2, lado * 2))
                except (ValueError, OSError):  # draft es opcional
                    pass
                im = ImageOps.exif_transpose(im).convert("RGB")
                im = im.copy()
            im.thumbnail((lado, lado), Image.LANCZOS)
            return im
        except Exception as e:  # si falla, se enseña el recuadro con la extensión
            log.info("No se pudo cargar la vista previa de %s: %s", ruta, e)
    return placeholder_extension(ruta, lado)
