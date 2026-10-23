"""Reads an image with Pillow and computes its fingerprint (dHash + colour)."""

import os
from typing import cast
from PIL import Image, ImageOps
from duplicate_finder.domain.similarity import ImageFingerprint


_DHASH_SIDE = 8            # -> hash of 8*8 = 64 bits
_COLOR_SIDE = 4            # -> signature of 4*4 RGB cells


# ----------------------------------------------------------------------
# Fingerprint of an image
# ----------------------------------------------------------------------
def _load_thumbnails(
    path: str,
) -> tuple[list[int], list[tuple[int, int, int]], tuple[int, int]]:
    """Opens the image once and returns (gray_9x8, rgb_4x4, (w, h))."""
    with Image.open(path) as im:
        width, height = im.size          # real size, before touching anything
        # draft speeds up the decoding of large JPEGs a lot (but changes
        # im.size, which is why it is read beforehand).
        try:
            im.draft("L", (64, 64))
        except (ValueError, OSError):  # draft is optional: if unavailable, decode in full
            pass
        upright = ImageOps.exif_transpose(im)     # respects the EXIF orientation
        gray = upright.convert("L").resize(
            (_DHASH_SIDE + 1, _DHASH_SIDE), Image.Resampling.BOX)
        rgb = upright.convert("RGB").resize(
            (_COLOR_SIDE, _COLOR_SIDE), Image.Resampling.BOX)
    # Pillow returns a wide type (depending on the image mode); here we know
    # that "L" gives integers and "RGB" gives (r, g, b) tuples.
    gray_data = cast(tuple[int, ...], gray.get_flattened_data())
    rgb_data = cast(tuple[tuple[int, int, int], ...], rgb.get_flattened_data())
    return list(gray_data), list(rgb_data), (width, height)


def compute_fingerprint(path: str) -> ImageFingerprint:
    """ImageFingerprint of `path`. Raises OSError/Image errors if it cannot be opened."""
    gray, rgb, (width, height) = _load_thumbnails(path)

    # dHash: on a 9x8 grayscale thumbnail, for each row we compare
    # every pixel with the one to its right. It gives 1 if the brightness "goes up", 0 if it
    # "goes down". 8 comparisons per row x 8 rows = 64 bits. What it measures
    # is the shape of the image, not the colours, which is why it withstands
    # recompression and filters well.
    width_g = _DHASH_SIDE + 1        # the thumbnail has 1 extra column
    bits = 0
    for row in range(_DHASH_SIDE):
        base = row * width_g       # first pixel of this row in the flat list
        for col in range(_DHASH_SIDE):
            left = gray[base + col]
            right = gray[base + col + 1]
            # shifts the hash one position and appends the new bit at the end
            bits = (bits << 1) | (1 if left < right else 0)

    try:
        size = os.path.getsize(path)
    except OSError:
        size = 0

    return ImageFingerprint(
        path=path, size=size, width=width, height=height,
        dhash=bits, color=tuple(rgb),
    )
