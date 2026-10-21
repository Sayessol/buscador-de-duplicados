"""Genera icono.ico a partir del dibujo de core/ui/icons.py.

No depende de Pillow: usa tkinter (librería estándar) para renderizar
cada tamaño como PNG y arma el contenedor .ico a mano con `struct`
(formato ICO con frames PNG, soportado desde Windows Vista).

    python generar_icono.py

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

from ui.icons import icono_ventana  # noqa: E402

TAMANOS = [16, 24, 32, 48, 64, 128, 256]
SALIDA = Path(__file__).resolve().parent / "icono.ico"


def png_bytes(photo):
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        ruta = Path(f.name)
    try:
        photo.write(str(ruta), format="png")
        return ruta.read_bytes()
    finally:
        ruta.unlink(missing_ok=True)


def construir_ico(frames):
    """frames: lista de (tamano, bytes_png) -> bytes del .ico completo."""
    n = len(frames)
    cabecera = struct.pack("<HHH", 0, 1, n)

    entradas = b""
    offset = 6 + 16 * n
    for tam, datos in frames:
        lado = tam if tam < 256 else 0  # 0 significa 256 en formato ICO
        entradas += struct.pack(
            "<BBBBHHII",
            lado, lado, 0, 0,      # ancho, alto, paleta, reservado
            1, 32,                  # planos, bits por pixel
            len(datos), offset,
        )
        offset += len(datos)

    return cabecera + entradas + b"".join(d for _t, d in frames)


def main():
    raiz = tk.Tk()
    raiz.withdraw()

    frames = []
    for tam in TAMANOS:
        img = icono_ventana(tam)
        frames.append((tam, png_bytes(img)))
        print(f"  renderizado {tam}x{tam}")

    SALIDA.write_bytes(construir_ico(frames))
    raiz.destroy()

    print(f"\nGenerado: {SALIDA}  ({SALIDA.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
