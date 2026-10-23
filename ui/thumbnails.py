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

from core.filters import CATEGORY_EXTENSIONS
from core.app_logging import log

THUMBNAIL_SIDE = 150
ROW_THUMBNAIL_SIDE = 40          # miniatura pequeña de cada fila de la tabla
PREVIEW_SIDE = 250        # panel de vista grande

# Color de fondo del placeholder según la categoría del archivo.
_COLOR_CATEGORY = {
    "Imágenes": "#3f6d52",
    "Audio": "#54487a",
    "Vídeo": "#7a4a4a",
    "Documentos": "#3a5a7a",
    "Comprimidos": "#7a6234",
}
_COLOR_OTHER = "#454545"
_COLOR_TEXT = "#eaeef4"

IMAGE_EXT = CATEGORY_EXTENSIONS["Imágenes"] | {"jpe", "ppm", "pgm"}

# Caché en memoria: (ruta, lado) -> PIL.Image. Se limpia al reescanear.
_cache = {}
_cache_lock = threading.Lock()


def clear_cache():
    with _cache_lock:
        _cache.clear()


def _category_of(ext):
    for name, exts in CATEGORY_EXTENSIONS.items():
        if ext in exts:
            return name
    return None


def _font(size):
    for name in ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def placeholder_extension(path, side=THUMBNAIL_SIDE):
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    color = _COLOR_CATEGORY.get(_category_of(ext), _COLOR_OTHER)
    im = Image.new("RGB", (side, side), color)
    d = ImageDraw.Draw(im)

    text = f".{ext}" if ext else "sin ext."
    font = _font(max(10, int(side * (0.30 if len(text) <= 4 else 0.20))))
    left, up, right, down = d.textbbox((0, 0), text, font=font)
    d.text(((side - (right - left)) / 2 - left, (side - (down - up)) / 2 - up),
           text, fill=_COLOR_TEXT, font=font)
    return im


def load_thumbnail(path, side=THUMBNAIL_SIDE):
    """PIL.Image cuadrada `lado`x`lado` (recorte centrado) de una imagen.

    Lanza si el archivo no se puede abrir como imagen.
    """
    with Image.open(path) as im:
        try:
            im.draft("RGB", (side * 2, side * 2))
        except (ValueError, OSError):  # draft es opcional
            pass
        im = ImageOps.exif_transpose(im).convert("RGB")
        return ImageOps.fit(im, (side, side), Image.BOX)


def thumbnail_or_placeholder(path, side=ROW_THUMBNAIL_SIDE):
    """Miniatura real si es imagen; si no (o si falla), placeholder."""
    key = (path, side)
    with _cache_lock:
        if key in _cache:
            return _cache[key]

    ext = os.path.splitext(path)[1].lower().lstrip(".")
    img = None
    if ext in IMAGE_EXT:
        try:
            img = load_thumbnail(path, side)
        except Exception as e:  # un archivo roto no debe romper la lista
            log.info("No se pudo crear la miniatura de %s: %s", path, e)
            img = None
    if img is None:
        img = placeholder_extension(path, side)

    with _cache_lock:
        _cache[key] = img
    return img


def large_preview(path, side=PREVIEW_SIDE):
    """PIL.Image para el panel de vista previa: imagen a tamaño (sin
    recortar, encajada en un cuadrado) o placeholder grande."""
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    if ext in IMAGE_EXT:
        try:
            with Image.open(path) as im:
                try:
                    im.draft("RGB", (side * 2, side * 2))
                except (ValueError, OSError):  # draft es opcional
                    pass
                im = ImageOps.exif_transpose(im).convert("RGB")
                im = im.copy()
            im.thumbnail((side, side), Image.LANCZOS)
            return im
        except Exception as e:  # si falla, se enseña el recuadro con la extensión
            log.info("No se pudo cargar la vista previa de %s: %s", path, e)
    return placeholder_extension(path, side)
