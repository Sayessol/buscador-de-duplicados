"""Thumbnails and previews of files.

Returns PIL.Image objects (they can be created in a secondary thread); the
conversion to CTkImage / ImageTk.PhotoImage is done later in the
interface thread.

- Image files   -> real thumbnail.
- Anything else -> a box with the extension (".pdf", ".mp3"…)
                   and a colour according to the category.
"""

import logging
import os
import threading

from PIL import Image, ImageDraw, ImageFont, ImageOps

from duplicate_finder.domain.filters import CATEGORY_EXTENSIONS
from duplicate_finder.i18n import tr

log = logging.getLogger(__name__)

THUMBNAIL_SIDE = 150
ROW_THUMBNAIL_SIDE = 40          # small thumbnail for each row of the table
PREVIEW_SIDE = 250        # large preview panel

# Background colour of the placeholder according to the category of the file.
_COLOR_CATEGORY = {
    "images": "#3f6d52",
    "audio": "#54487a",
    "video": "#7a4a4a",
    "documents": "#3a5a7a",
    "archives": "#7a6234",
}
_COLOR_OTHER = "#454545"
_COLOR_TEXT = "#eaeef4"

IMAGE_EXT = CATEGORY_EXTENSIONS["images"] | {"jpe", "ppm", "pgm"}

# In-memory cache: (path, side) -> PIL.Image. Cleared on rescan.
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

    text = f".{ext}" if ext else tr("thumbs.no_extension")
    font = _font(max(10, int(side * (0.30 if len(text) <= 4 else 0.20))))
    left, up, right, down = d.textbbox((0, 0), text, font=font)
    d.text(((side - (right - left)) / 2 - left, (side - (down - up)) / 2 - up),
           text, fill=_COLOR_TEXT, font=font)
    return im


def load_thumbnail(path, side=THUMBNAIL_SIDE):
    """Square PIL.Image `side`x`side` (centred crop) of an image.

    Raises if the file cannot be opened as an image.
    """
    with Image.open(path) as im:
        try:
            im.draft("RGB", (side * 2, side * 2))
        except (ValueError, OSError):  # draft is optional
            pass
        im = ImageOps.exif_transpose(im).convert("RGB")
        return ImageOps.fit(im, (side, side), Image.BOX)


def thumbnail_or_placeholder(path, side=ROW_THUMBNAIL_SIDE):
    """Real thumbnail if it is an image; otherwise (or if it fails), a placeholder."""
    key = (path, side)
    with _cache_lock:
        if key in _cache:
            return _cache[key]

    ext = os.path.splitext(path)[1].lower().lstrip(".")
    img = None
    if ext in IMAGE_EXT:
        try:
            img = load_thumbnail(path, side)
        except Exception as e:  # a broken file must not break the list
            log.info("Could not create the thumbnail of %s: %s", path, e)
            img = None
    if img is None:
        img = placeholder_extension(path, side)

    with _cache_lock:
        _cache[key] = img
    return img


def large_preview(path, side=PREVIEW_SIDE):
    """PIL.Image for the preview panel: image at size (not
    cropped, fitted into a square) or a large placeholder."""
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    if ext in IMAGE_EXT:
        try:
            with Image.open(path) as im:
                try:
                    im.draft("RGB", (side * 2, side * 2))
                except (ValueError, OSError):  # draft is optional
                    pass
                im = ImageOps.exif_transpose(im).convert("RGB")
                im = im.copy()
            im.thumbnail((side, side), Image.LANCZOS)
            return im
        except Exception as e:  # if it fails, the box with the extension is shown
            log.info("Could not load the preview of %s: %s", path, e)
    return placeholder_extension(path, side)
