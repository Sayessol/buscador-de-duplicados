"""Smoke test of the auxiliary windows, with the real interface:

  · the image viewer (zoom, fit, wheel, broken image, a file that is not an image),
  · the history (undo a "move", undo a "copy", and an undo that fails),
  · the dialog about what to do with files that are not images (apply and cancel),
  · the breakdown by extension (excluding one),
  · the CSV export and the thumbnails / image preview.

    python tests/smoke_dialogs.py
"""

import csv
import os
import sys
import tempfile
from pathlib import Path
from tkinter import filedialog, messagebox

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# It does not touch the user's real data (history, configuration):
TMP = Path(tempfile.mkdtemp(prefix="dup_dlg_"))
os.environ["APPDATA"] = str(TMP / "appdata")

from PIL import Image                                   # noqa: E402

from core import history                              # noqa: E402
from core.file_moves import MOVE                            # noqa: E402
from core.gather import GROUP, LEAVE                  # noqa: E402
from core.scanner import scan                       # noqa: E402
from ui import icons, styles, thumbnails                # noqa: E402
from ui.history_window import HistoryWindow          # noqa: E402
from ui.image_viewer import ImageViewer, open_viewer    # noqa: E402
from ui.main_window import MainWindow             # noqa: E402
from ui.non_image_kinds_dialog import NonImageKindsWindow        # noqa: E402
from ui.extension_breakdown_dialog import ExtensionBreakdownWindow     # noqa: E402

failures = []
warnings = {"preguntas": 0, "info": 0, "aviso": 0, "error": 0}
warning_texts = []       # to explain a failure if a check is not met


def check(cond, msg):
    print(f"  [{'OK  ' if cond else 'FALLA'}] {msg}")
    if not cond:
        failures.append(msg)


def stub_dialogs():
    def count(key, returns=None):
        def f(*a, **_k):
            warnings[key] += 1
            if key in ("aviso", "error"):
                warning_texts.append(" ".join(str(x) for x in a[:2]))
            return returns
        return f
    messagebox.askyesno = count("preguntas", True)
    messagebox.showinfo = count("info")
    messagebox.showwarning = count("aviso")
    messagebox.showerror = count("error")


def main():
    styles.apply_theme()
    stub_dialogs()
    app = MainWindow()
    app.update()

    # ------------------------------------------------------------ image viewer
    print("Visor de imagen")
    photo = TMP / "foto.png"
    Image.new("RGB", (800, 600), (30, 120, 200)).save(photo)
    viewer = ImageViewer(app, str(photo))
    app.update()
    viewer._set_scale(1.0)
    check("800×600" in viewer._lbl_info.cget("text"), "enseña las dimensiones de la foto")
    viewer._zoom(1.25)
    check(abs(viewer._scale - 1.25) < 1e-9, "el botón + amplía un 25 %")
    viewer._zoom(1 / 1.25)
    viewer._fit()
    app.update()
    check(0.05 <= viewer._scale <= 1.0, "«Ajustar» deja la foto entera dentro de la ventana")
    previous = viewer._scale

    class Event:
        delta = 120
    viewer._wheel(Event())
    check(viewer._scale > previous, "la rueda del ratón hacia arriba amplía")
    viewer._set_scale(99)
    check(viewer._scale == 8.0, "el zoom tiene un máximo (8×)")
    viewer._set_appearance_mode("Light")
    viewer.destroy()

    broken = TMP / "rota.png"
    broken.write_bytes(b"esto no es una imagen")
    broken_viewer = ImageViewer(app, str(broken))
    app.update()
    check(broken_viewer._orig is None, "una imagen rota no hace caer el visor")
    broken_viewer.destroy()

    open_viewer(app, str(TMP / "notas.txt"))                      # not an image: it opens nothing
    open_viewer(app, str(TMP / "no_existe.png"))                  # does not exist: neither
    check(not any(isinstance(h, ImageViewer) for h in app.winfo_children()),
          "no abre el visor para archivos que no son imágenes o no existen")

    # ------------------------------------------------- thumbnails and preview
    print("Miniaturas")
    mini = thumbnails.thumbnail_or_placeholder(str(photo), 40)
    check(mini.size == (40, 40), "miniatura cuadrada de una imagen real")
    placeholder = thumbnails.thumbnail_or_placeholder(str(broken), 40)
    check(placeholder.size == (40, 40), "una imagen rota da un recuadro con la extensión")
    large = thumbnails.large_preview(str(photo), 250)
    check(max(large.size) <= 250, "vista previa grande encajada en el cuadrado")
    check(thumbnails.large_preview(str(broken), 250).size[0] > 0,
          "vista previa de imagen rota: recuadro")
    check(icons.window_icon(32).width() == 32, "el icono de la ventana se dibuja")

    # ------------------------------------------------------------------ history
    print("Historial")
    empty = HistoryWindow(app)
    app.update()
    check(len(empty.items.winfo_children()) == 1, "sin operaciones: aviso de «todavía no hay»")
    empty.destroy()

    source, destination = TMP / "origen", TMP / "destino"
    source.mkdir()
    destination.mkdir()
    moved = source / "movido.txt"
    moved.write_text("hola")
    (destination / "movido.txt").write_text("hola")     # simulates the file already moved
    moved.unlink()
    copied_source = source / "copiado.txt"
    copied_source.write_text("original")
    (destination / "copiado.txt").write_text("original")
    history.record(history.KIND_QUARANTINE, "move", str(source), str(destination),
                        [(str(moved), str(destination / "movido.txt"))], "1 duplicado")
    history.record(history.KIND_GATHER, "copy", str(source), str(destination),
                        [(str(copied_source), str(destination / "copiado.txt"))], "1 imagen")
    window = HistoryWindow(app)
    app.update()
    ops = history.list_all()
    check(len(ops) == 2, "el historial lista las dos operaciones")
    op_copy, op_move = ops[0], ops[1]          # the most recent first
    window._undo(op_move)
    check(moved.exists() and not (destination / "movido.txt").exists(),
          "deshacer un «mover» devuelve el archivo a su sitio")
    window._undo(op_copy)
    check(copied_source.exists() and not (destination / "copiado.txt").exists(),
          "deshacer un «copiar» borra la copia y NO toca el original"
          + (f"  [avisos: {warning_texts}]" if warning_texts else ""))
    check(all(o["undone"] for o in history.list_all()), "las dos quedan marcadas como deshechas")

    (destination / "otro.txt").write_text("x")
    history.record(history.KIND_QUARANTINE, "move", str(source), str(destination),
                        [(str(source / "otro.txt"), str(destination / "no_esta.txt"))], "falla")
    warnings_before = warnings["aviso"]
    window._undo(history.list_all()[0])
    check(warnings["aviso"] == warnings_before + 1,
          "si no se puede deshacer, se avisa y la operación sigue sin marcarse")
    window.destroy()

    # --------------------------------------- what to do with files that are not images
    print("Diálogo de tipos no imagen")
    kinds = {"pdf": ["a.pdf"], "txt": ["b.txt", "c.txt"], "mp3": ["d.mp3"]}
    dlg = NonImageKindsWindow(app, kinds)
    app.update()
    seg_pdf, pdf_input = dlg._rows["pdf"]
    seg_txt, _ = dlg._rows["txt"]
    seg_pdf.set_key(GROUP)
    dlg._toggle_entry("pdf")
    pdf_input.delete(0, "end")
    pdf_input.insert(0, "Mis documentos")
    seg_txt.set_key(MOVE)
    dlg._toggle_entry("txt")
    dlg._apply()
    rules = dlg.rules
    check(rules is not None and rules.action("pdf") == GROUP
          and rules.folder("pdf") == "Mis documentos", "«Agrupar» guarda el nombre de carpeta")
    check(rules is not None and rules.action("txt") == MOVE, "«Mover» se recoge")
    check(rules is not None and rules.action("mp3") == LEAVE,
          "lo que no se toca queda en «Dejar»")
    dlg2 = NonImageKindsWindow(app, kinds)
    app.update()
    dlg2._cancel()
    check(dlg2.rules is None, "cancelar devuelve None (no se hace nada)")

    # ---------------------------------------- breakdown by extension + export CSV
    print("Desglose por extensión y CSV")
    data = TMP / "datos"
    (data / "a").mkdir(parents=True)
    (data / "b").mkdir()
    for folder in ("a", "b"):
        (data / folder / "doc.txt").write_bytes(b"contenido del documento\n" * 20)
        (data / folder / "foto.jpg").write_bytes(b"pixeles\n" * 50)
    result = scan(str(data))
    excluded = []
    breakdown = ExtensionBreakdownWindow(app, result, excluded.append)
    app.update()
    breakdown._exclude("txt")
    check(excluded == ["txt"], "«Excluir» avisa de la extensión elegida")
    check("txt" in breakdown.title(), "y lo dice en el título de la ventana")
    breakdown.destroy()

    exact = app.exact
    exact._result = result
    report = TMP / "informe.csv"
    filedialog.asksaveasfilename = lambda *a, **k: str(report)
    exact._export_csv()
    rows = list(csv.reader(report.open(encoding="utf-8-sig", newline="")))
    check(len(rows) == 1 + 4 and rows[0][0] == "Duplicate_Group",
          "el CSV tiene cabecera y los 4 archivos duplicados")
    filedialog.asksaveasfilename = lambda *a, **k: ""
    exact._export_csv()                          # cancel: it does nothing and does not fail
    filedialog.asksaveasfilename = lambda *a, **k: str(TMP / "no" / "existe" / "i.csv")
    errors_before = warnings["error"]
    exact._export_csv()
    check(warnings["error"] == errors_before + 1,
          "si no se puede escribir, se avisa en vez de romperse")

    app.destroy()
    print()
    if failures:
        print(f"FALLARON {len(failures)} comprobaciones.")
        sys.exit(1)
    print("HUMO DIÁLOGOS OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
