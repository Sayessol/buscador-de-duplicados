"""Genera icono.ico a partir del dibujo de core/ui/icons.py.

No depende de Pillow: usa tkinter (librería estándar) para renderizar
cada tamaño como PNG y arma el contenedor .ico a mano con `struct`
(formato ICO con frames PNG, soportado desde Windows Vista).

    python gen_icon.py

Genera icono.ico, que build.spec usa para el .exe final.
Hace falta volver a correr esto solo si se cambia el dibujo del icono
en ui/icons.py.
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
    """frames: lista de (tamano, bytes_png) -> bytes del .ico completo."""
    n = len(frames)
    header = struct.pack("<HHH", 0, 1, n)

    entries = b""
    offset = 6 + 16 * n
    for size, data in frames:
        side = size if size < 256 else 0  # 0 significa 256 en formato ICO
        entries += struct.pack(
            "<BBBBHHII",
            side, side, 0, 0,      # ancho, alto, paleta, reservado
            1, 32,                  # planos, bits por pixel
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
