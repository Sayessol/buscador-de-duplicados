"""Prueba de humo del registro de errores con la ventana de verdad.

Provoca dos fallos y comprueba que quedan anotados en el archivo de registro:
  1. un error dentro de una función de la interfaz (un temporizador de Tkinter);
  2. un error en el hilo que escanea (se le pasa una carpeta que no existe).
Y que el aviso al usuario sale UNA sola vez aunque el fallo se repita.

    python tests/smoke_logging.py
"""

import os
import sys
import tempfile
from pathlib import Path
from tkinter import messagebox

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

TMP = Path(tempfile.mkdtemp(prefix="dup_reg_"))
os.environ["APPDATA"] = str(TMP / "appdata")          # no toca el registro real

from core import app_logging                              # noqa: E402
from core.filters import ScanFilter                  # noqa: E402
from ui import styles                                   # noqa: E402
from ui.main_window import MainWindow             # noqa: E402

failures = []
warnings = []


def check(cond, msg):
    print(f"  [{'OK  ' if cond else 'FALLA'}] {msg}")
    if not cond:
        failures.append(msg)


def main():
    messagebox.showerror = lambda *a, **k: warnings.append(a)
    styles.apply_theme()
    log_path = app_logging.start()
    check(log_path is not None and log_path.exists(), "el archivo de registro se crea al iniciar")

    app = MainWindow()

    def ui_failure():
        raise RuntimeError("fallo provocado en la interfaz")

    def scan_failure():
        # El mismo método que corre en el hilo del escaneo; con una carpeta inexistente.
        app.exact._scan_job(str(TMP / "no_existe"), ScanFilter.no_filter())

    app.after(200, ui_failure)
    app.after(300, ui_failure)                 # repetido: solo debe avisar una vez
    app.after(400, scan_failure)
    app.after(1200, app.destroy)
    app.mainloop()

    for h in app_logging.log.handlers:
        h.flush()
    text = log_path.read_text(encoding="utf-8")
    check("fallo provocado en la interfaz" in text, "el error de la interfaz queda en el registro")
    check(text.count("Error inesperado en la interfaz") == 2, "los dos fallos repetidos se anotan")
    check(len(warnings) == 1, "pero el aviso al usuario sale una sola vez")
    check("Falló el escaneo" in text and "NotADirectoryError" in text,
          "el error del hilo de escaneo queda en el registro, con su traceback")
    check(str(log_path) in warnings[0][1] if warnings else False,
          "el aviso dice dónde está el registro")

    app_logging.stop()
    print()
    if failures:
        print(f"FALLARON {len(failures)} comprobaciones.")
        sys.exit(1)
    print("HUMO REGISTRO OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
