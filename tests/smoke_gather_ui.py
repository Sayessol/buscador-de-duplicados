"""Smoke test of the "Gather images" tab + History + Undo,
pressing the real buttons of the window (with the dialogs stubbed).

    python tests/smoke_gather_ui.py
"""

import os
import sys
import tempfile
from pathlib import Path
from tkinter import filedialog, messagebox

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

R = {}
failures = []


def check(cond, msg):
    print(f"  [{'OK  ' if cond else 'FAIL'}] {msg}")
    if not cond:
        failures.append(msg)


def build(root: Path):
    from PIL import Image
    (root / "2023").mkdir(parents=True)
    (root / "2024" / "wedding").mkdir(parents=True)
    for rel in ("cover.png", "2023/beach.jpg", "2024/portrait.jpg",
                "2024/wedding/group.jpeg"):
        Image.new("RGB", (64, 48), (90, 90, 90)).save(root / rel)
    (root / "notes.txt").write_text("hello")
    (root / "2023" / "info.pdf").write_bytes(b"%PDF")
    (root / "2024" / "expenses.pdf").write_bytes(b"%PDF")


def main():
    tmp = Path(tempfile.mkdtemp(prefix="dup_reunir_"))
    os.environ["APPDATA"] = str(tmp / "appdata")

    from ui import styles                         # noqa: E402
    from ui import main_window as MW                      # noqa: E402
    from core import history                            # noqa: E402
    from core.gather import NonImageRules                # noqa: E402
    import customtkinter as ctk

    styles.apply_theme()

    root = tmp / "Mixed photos"
    destination = tmp / "Desktop" / "All photos"
    build(root)

    # Stubbed dialogs
    filedialog.askdirectory = lambda *a, **k: str(destination)
    messagebox.askyesno = lambda *a, **k: True
    os.startfile = lambda *a, **k: None   # without this the real Explorer would open
    messagebox.showinfo = lambda *a, **k: None
    messagebox.showwarning = lambda *a, **k: None
    messagebox.showerror = lambda *a, **k: print("   [showerror]", a)

    class FakeKinds(ctk.CTkToplevel):
        def __init__(self, master, kinds):
            super().__init__(master)
            self.withdraw()
            self.rules = NonImageRules(
                action_by_ext={"pdf": "group", "txt": "leave"},
                folder_by_ext={"pdf": "Documents"})
            self.after(10, self.destroy)
    from ui import gather_images_tab as TR                      # noqa: E402
    TR.NonImageKindsWindow = FakeKinds   # the dialog is used from the Gather tab

    app = MW.MainWindow()
    app._mode = "advanced"
    app._apply_mode()
    app.show_tab("gather")
    app.gather.entry_folder.insert(0, str(root))
    app.gather.entry_destination.insert(0, str(destination))
    app.gather.seg_action.set_key("move")
    app.gather.seg_strategy.set_key("files")

    imgs_before = sorted(str(p.relative_to(root)).replace("\\", "/")
                        for p in root.rglob("*") if p.suffix.lower() in
                        (".png", ".jpg", ".jpeg"))

    def search_step():
        app.gather._search()
        app.after(800, run_step)

    def run_step():
        R["found"] = len(app.gather._images)
        R["marked"] = len(app.gather._included)
        R["otros"] = len(app.gather._others)
        app.gather._run()
        app.after(1800, verify)

    def verify():
        moved = sorted(str(p.relative_to(destination)).replace("\\", "/")
                         for p in destination.rglob("*")
                         if p.suffix.lower() in (".png", ".jpg", ".jpeg"))
        R["img_in_destination"] = moved
        R["left_in_source_img"] = [
            str(p.relative_to(root)) for p in root.rglob("*")
            if p.suffix.lower() in (".png", ".jpg", ".jpeg")]
        R["txt_stays"] = (root / "notes.txt").exists()
        R["pdf_grouped"] = (destination / "Documents" / "2023" / "info.pdf").exists()
        R["source_subfolders"] = sorted(
            str(p.relative_to(root)) for p in root.rglob("*") if p.is_dir())

        ops = history.list_all()
        R["history_n"] = len(ops)
        R["op_kind"] = ops[0]["kind"] if ops else None

        # Undo the operation
        res = history.undo(ops[0]["id"])
        R["undo_ok"] = res["reverted"]
        R["undo_failures"] = len(res["failures"])
        R["img_back"] = (root / "2023" / "beach.jpg").exists()
        R["destination_empty_img"] = not any(
            p.suffix.lower() in (".png", ".jpg", ".jpeg")
            for p in destination.rglob("*"))

        app.after(200, app.destroy)

    app.after(400, search_step)
    app.after(20000, app.destroy)
    app.mainloop()

    for k, v in R.items():
        print(f"  {k:24} {v}")

    ok = (
        R.get("found") == 4
        and R.get("marked") == 4
        and R.get("otros") == 3
        and sorted(R.get("img_in_destination", [])) == sorted(imgs_before)
        and R.get("left_in_source_img") == []
        and R.get("txt_stays") is True
        and R.get("pdf_grouped") is True
        and set(R.get("source_subfolders", [])) >= {"2023", "2024", "2024\\wedding"}
        and R.get("history_n") == 1
        and R.get("op_kind") == "gather"
        and R.get("undo_ok") == 6   # 4 images + 2 pdf grouped
        and R.get("undo_failures") == 0
        and R.get("img_back") is True
        and R.get("destination_empty_img") is True
    )
    print("\n" + ("GATHER SMOKE OK" if ok else "GATHER SMOKE FAILED"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
