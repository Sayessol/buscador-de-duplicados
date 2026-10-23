"""Generates icono.ico from the drawing in ui/icons.py.

It does not depend on Pillow: it uses tkinter (standard library) to render
each size as a PNG and builds the .ico container by hand with `struct`
(ICO format with PNG frames, supported since Windows Vista).

    python gen_icon.py

It generates icono.ico, which build.spec uses for the final .exe.
This only needs to be run again if the drawing of the icon
in ui/icons.py changes.
"""

import struct
import sys
import tempfile
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ui.icons import window_icon  # noqa: E402

SIZES = [16, 24, 32, 48, 64, 128, 256]
OUTPUT = Path(__file__).resolve().parent / "icono.ico"


def png_bytes(photo):
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        path = Path(f.name)
    try:
        photo.write(str(path), format="png")
        return path.read_bytes()
    finally:
        path.unlink(missing_ok=True)


def build_ico(frames):
    """frames: list of (size, png_bytes) -> bytes of the complete .ico."""
    n = len(frames)
    header = struct.pack("<HHH", 0, 1, n)

    entries = b""
    offset = 6 + 16 * n
    for size, data in frames:
        side = size if size < 256 else 0  # 0 means 256 in ICO format
        entries += struct.pack(
            "<BBBBHHII",
            side, side, 0, 0,      # width, height, palette, reserved
            1, 32,                  # planes, bits per pixel
            len(data), offset,
        )
        offset += len(data)

    return header + entries + b"".join(d for _t, d in frames)


def main():
    root = tk.Tk()
    root.withdraw()

    frames = []
    for size in SIZES:
        img = window_icon(size)
        frames.append((size, png_bytes(img)))
        print(f"  renderizado {size}x{size}")

    OUTPUT.write_bytes(build_ico(frames))
    root.destroy()

    print(f"\nGenerado: {OUTPUT}  ({OUTPUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
