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
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
# It does not touch the user's real data (history, configuration):
TMP = Path(tempfile.mkdtemp(prefix="dup_dlg_"))
os.environ["APPDATA"] = str(TMP / "appdata")

from PIL import Image                                   # noqa: E402

from duplicate_finder.application import history  # noqa: E402
from duplicate_finder.domain.transfers import MOVE  # noqa: E402
from duplicate_finder.domain.transfers import GROUP, LEAVE  # noqa: E402
from duplicate_finder.application.scan_duplicates import scan  # noqa: E402
from duplicate_finder.presentation import icons, styles, thumbnails  # noqa: E402
from duplicate_finder.presentation.history_window import HistoryWindow  # noqa: E402
from duplicate_finder.presentation.image_viewer import ImageViewer, open_viewer  # noqa: E402
from duplicate_finder.presentation.main_window import MainWindow  # noqa: E402
from duplicate_finder.presentation.non_image_kinds_dialog import NonImageKindsWindow  # noqa: E402
from duplicate_finder.presentation.extension_breakdown_dialog import ExtensionBreakdownWindow  # noqa: E402

failures = []
warnings = {"questions": 0, "info": 0, "warning": 0, "error": 0}
warning_texts = []       # to explain a failure if a check is not met


def check(cond, msg):
    print(f"  [{'OK  ' if cond else 'FAIL'}] {msg}")
    if not cond:
        failures.append(msg)


def stub_dialogs():
    def count(key, returns=None):
        def f(*a, **_k):
            warnings[key] += 1
            if key in ("warning", "error"):
                warning_texts.append(" ".join(str(x) for x in a[:2]))
            return returns
        return f
    messagebox.askyesno = count("questions", True)
    messagebox.showinfo = count("info")
    messagebox.showwarning = count("warning")
    messagebox.showerror = count("error")


def main():
    styles.apply_theme()
    stub_dialogs()
    app = MainWindow()
    app.update()

    # ------------------------------------------------------------ image viewer
    print("Image viewer")
    photo = TMP / "photo.png"
    Image.new("RGB", (800, 600), (30, 120, 200)).save(photo)
    viewer = ImageViewer(app, str(photo))
    app.update()
    viewer._set_scale(1.0)
    check("800×600" in viewer._lbl_info.cget("text"), "shows the dimensions of the photo")
    viewer._zoom(1.25)
    check(abs(viewer._scale - 1.25) < 1e-9, "the + button zooms in by 25 %")
    viewer._zoom(1 / 1.25)
    viewer._fit()
    app.update()
    check(0.05 <= viewer._scale <= 1.0, "\"Fit\" leaves the whole photo inside the window")
    previous = viewer._scale

    class Event:
        delta = 120
    viewer._wheel(Event())
    check(viewer._scale > previous, "mouse wheel up zooms in")
    viewer._set_scale(99)
    check(viewer._scale == 8.0, "the zoom has a maximum (8×)")
    viewer._set_appearance_mode("Light")
    viewer.destroy()

    broken = TMP / "rota.png"
    broken.write_bytes(b"esto no es una image")
    broken_viewer = ImageViewer(app, str(broken))
    app.update()
    check(broken_viewer._orig is None, "a broken image does not bring the viewer down")
    broken_viewer.destroy()

    open_viewer(app, str(TMP / "notes.txt"))                      # not an image: it opens nothing
    open_viewer(app, str(TMP / "no_existe.png"))                  # does not exist: neither
    check(not any(isinstance(h, ImageViewer) for h in app.winfo_children()),
          "it does not open the viewer for files that are not images or do not exist")

    # ------------------------------------------------- thumbnails and preview
    print("Thumbnails")
    mini = thumbnails.thumbnail_or_placeholder(str(photo), 40)
    check(mini.size == (40, 40), "square thumbnail of a real image")
    placeholder = thumbnails.thumbnail_or_placeholder(str(broken), 40)
    check(placeholder.size == (40, 40), "a broken image gives a box with the extension")
    large = thumbnails.large_preview(str(photo), 250)
    check(max(large.size) <= 250, "large preview fitted in the square")
    check(thumbnails.large_preview(str(broken), 250).size[0] > 0,
          "preview of a broken image: box")
    check(icons.window_icon(32).width() == 32, "the window icon is drawn")

    # ------------------------------------------------------------------ history
    print("History")
    empty = HistoryWindow(app)
    app.update()
    check(len(empty.items.winfo_children()) == 1, "no operations: the \"nothing yet\" notice")
    empty.destroy()

    source, destination = TMP / "source", TMP / "destination"
    source.mkdir()
    destination.mkdir()
    moved = source / "movido.txt"
    moved.write_text("hello")
    (destination / "movido.txt").write_text("hello")     # simulates the file already moved
    moved.unlink()
    copied_source = source / "copiado.txt"
    copied_source.write_text("original")
    (destination / "copiado.txt").write_text("original")
    history.record(history.KIND_QUARANTINE, "move", str(source), str(destination),
                        [(str(moved), str(destination / "movido.txt"))], "1 duplicado")
    history.record(history.KIND_GATHER, "copy", str(source), str(destination),
                        [(str(copied_source), str(destination / "copiado.txt"))], "1 image")
    window = HistoryWindow(app)
    app.update()
    ops = history.list_all()
    check(len(ops) == 2, "the history lists the two operations")
    op_copy, op_move = ops[0], ops[1]          # the most recent first
    window._undo(op_move)
    check(moved.exists() and not (destination / "movido.txt").exists(),
          "undoing a \"move\" puts the file back in place")
    window._undo(op_copy)
    check(copied_source.exists() and not (destination / "copiado.txt").exists(),
          "undoing a \"copy\" deletes the copy and does NOT touch the original"
          + (f"  [warnings: {warning_texts}]" if warning_texts else ""))
    check(all(o["undone"] for o in history.list_all()), "both are marked as undone")

    (destination / "otro.txt").write_text("x")
    history.record(history.KIND_QUARANTINE, "move", str(source), str(destination),
                        [(str(source / "otro.txt"), str(destination / "no_esta.txt"))], "falla")
    warnings_before = warnings["warning"]
    window._undo(history.list_all()[0])
    check(warnings["warning"] == warnings_before + 1,
          "if it cannot be undone, the user is warned and the operation stays unmarked")
    window.destroy()

    # --------------------------------------- what to do with files that are not images
    print("Dialog for the non-image types")
    kinds = {"pdf": ["a.pdf"], "txt": ["b.txt", "c.txt"], "mp3": ["d.mp3"]}
    dlg = NonImageKindsWindow(app, kinds)
    app.update()
    seg_pdf, pdf_input = dlg._rows["pdf"]
    seg_txt, _ = dlg._rows["txt"]
    seg_pdf.set_key(GROUP)
    dlg._toggle_entry("pdf")
    pdf_input.delete(0, "end")
    pdf_input.insert(0, "My documents")
    seg_txt.set_key(MOVE)
    dlg._toggle_entry("txt")
    dlg._apply()
    rules = dlg.rules
    check(rules is not None and rules.action("pdf") == GROUP
          and rules.folder("pdf") == "My documents", "\"Group\" keeps the folder name")
    check(rules is not None and rules.action("txt") == MOVE, "\"Move\" is picked up")
    check(rules is not None and rules.action("mp3") == LEAVE,
          "whatever is not touched stays on \"Leave\"")
    dlg2 = NonImageKindsWindow(app, kinds)
    app.update()
    dlg2._cancel()
    check(dlg2.rules is None, "cancelling returns None (nothing is done)")

    # ---------------------------------------- breakdown by extension + export CSV
    print("Breakdown by extension and CSV")
    data = TMP / "data"
    (data / "a").mkdir(parents=True)
    (data / "b").mkdir()
    for folder in ("a", "b"):
        (data / folder / "doc.txt").write_bytes(b"content del document\n" * 20)
        (data / folder / "photo.jpg").write_bytes(b"pixeles\n" * 50)
    result = scan(str(data))
    excluded = []
    breakdown = ExtensionBreakdownWindow(app, result, excluded.append)
    app.update()
    breakdown._exclude("txt")
    check(excluded == ["txt"], "\"Exclude\" warns about the chosen extension")
    check("txt" in breakdown.title(), "and says so in the window title")
    breakdown.destroy()

    exact = app.exact
    exact._result = result
    report = TMP / "report.csv"
    filedialog.asksaveasfilename = lambda *a, **k: str(report)
    exact._export_csv()
    rows = list(csv.reader(report.open(encoding="utf-8-sig", newline="")))
    check(len(rows) == 1 + 4 and rows[0][0] == "Duplicate_Group",
          "the CSV has a header and the 4 duplicate files")
    filedialog.asksaveasfilename = lambda *a, **k: ""
    exact._export_csv()                          # cancel: it does nothing and does not fail
    filedialog.asksaveasfilename = lambda *a, **k: str(TMP / "no" / "existe" / "i.csv")
    errors_before = warnings["error"]
    exact._export_csv()
    check(warnings["error"] == errors_before + 1,
          "if it cannot be written, the user is warned instead of crashing")

    app.destroy()
    print()
    if failures:
        print(f"{len(failures)} CHECKS FAILED.")
        sys.exit(1)
    print("DIALOGS SMOKE OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
