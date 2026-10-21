"""Prueba de humo del registro de errores con la ventana de verdad.

Provoca dos fallos y comprueba que quedan anotados en el archivo de registro:
  1. un error dentro de una función de la interfaz (un temporizador de Tkinter);
  2. un error en el hilo que escanea (se le pasa una carpeta que no existe).
Y que el aviso al usuario sale UNA sola vez aunque el fallo se repita.

    python pruebas/humo_registro.py
"""

import os
import sys
import tempfile
from pathlib import Path
from tkinter import messagebox

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

TMP = Path(tempfile.mkdtemp(prefix="dup_reg_"))
os.environ["APPDATA"] = str(TMP / "appdata")          # no toca el registro real

from core import registro                              # noqa: E402
from core.filtros import FiltroEscaneo                  # noqa: E402
from ui import styles                                   # noqa: E402
from ui.main_window import VentanaPrincipal             # noqa: E402

fallos = []
avisos = []


def check(cond, msg):
    print(f"  [{'OK  ' if cond else 'FALLA'}] {msg}")
    if not cond:
        fallos.append(msg)


def main():
    messagebox.showerror = lambda *a, **k: avisos.append(a)
    styles.aplicar_tema()
    ruta_log = registro.iniciar()
    check(ruta_log is not None and ruta_log.exists(), "el archivo de registro se crea al iniciar")

    app = VentanaPrincipal()

    def fallo_en_la_interfaz():
        raise RuntimeError("fallo provocado en la interfaz")

    def fallo_en_el_escaneo():
        # El mismo método que corre en el hilo del escaneo; con una carpeta inexistente.
        app.exactos._trabajo_escaneo(str(TMP / "no_existe"), FiltroEscaneo.sin_filtro())

    app.after(200, fallo_en_la_interfaz)
    app.after(300, fallo_en_la_interfaz)                 # repetido: solo debe avisar una vez
    app.after(400, fallo_en_el_escaneo)
    app.after(1200, app.destroy)
    app.mainloop()

    for h in registro.log.handlers:
        h.flush()
    texto = ruta_log.read_text(encoding="utf-8")
    check("fallo provocado en la interfaz" in texto, "el error de la interfaz queda en el registro")
    check(texto.count("Error inesperado en la interfaz") == 2, "los dos fallos repetidos se anotan")
    check(len(avisos) == 1, "pero el aviso al usuario sale una sola vez")
    check("Falló el escaneo" in texto and "NotADirectoryError" in texto,
          "el error del hilo de escaneo queda en el registro, con su traceback")
    check(str(ruta_log) in avisos[0][1] if avisos else False,
          "el aviso dice dónde está el registro")

    registro.detener()
    print()
    if fallos:
        print(f"FALLARON {len(fallos)} comprobaciones.")
        sys.exit(1)
    print("HUMO REGISTRO OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
