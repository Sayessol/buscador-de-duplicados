"""Real test of moving to quarantine: creates a tree, really moves the marked
duplicates and checks that:

  * the "keep" files stay in their place,
  * the "move" ones are no longer in the source and are in the quarantine,
  * the subfolder structure is preserved,
  * the CSV log is written,
  * invalid situations are rejected (unresolved groups,
    quarantine inside the scanned folder),
  * names that collide are not overwritten.

    python tests/check_quarantine.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from duplicate_finder.bootstrap import build_services  # noqa: E402

SERVICES = build_services()
scan = SERVICES.scan_duplicates
from duplicate_finder.domain.selection import DuplicateSelection  # noqa: E402
from duplicate_finder.application.quarantine import (  # noqa: E402
    validate_quarantine_folder,
    InvalidQuarantine,
)

move_to_quarantine = SERVICES.move_to_quarantine

failures = []


def check(cond, msg):
    print(f"  [{'OK  ' if cond else 'FAIL'}] {msg}")
    if not cond:
        failures.append(msg)


def build(base: Path):
    def write(rel, data: bytes):
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    a = b"content A\n" * 30
    b = b"content B different\n" * 20

    write("good/photo.jpg", a)          # keep
    write("downloads/photo.jpg", a)      # move
    write("downloads/sub/photo.jpg", a)  # move (its name collides with the previous one)
    write("good/doc.txt", b)           # keep
    write("old/doc.txt", b)           # move


def main():
    with tempfile.TemporaryDirectory(prefix="dup_cuar_") as tmp:
        base = Path(tmp) / "scanned"
        quarantine = Path(tmp) / "QUARANTINE"
        build(base)

        r = scan(str(base))
        sel = DuplicateSelection(r)

        # --- validations that must fail --------------------------
        try:
            move_to_quarantine(sel, str(base), str(quarantine))
            check(False, "moving with unresolved groups must raise ValueError")
        except ValueError:
            check(True, "moving with unresolved groups raises ValueError")

        try:
            validate_quarantine_folder(str(base / "sub"), str(base))
            check(False, "a quarantine inside the scanned folder must fail")
        except InvalidQuarantine:
            check(True, "a quarantine inside the scanned folder raises InvalidQuarantine")

        # --- resolve with the preferred-folder rule -------------
        resolved, without_c = sel.apply_folder_rule(str(base / "good"))
        check(resolved == 2 and without_c == 0, "the rule resolves the 2 groups")
        check(sel.all_ready(), "everything is ready to move")

        expected_to_move = sel.count_to_move()
        bytes_expected = sel.space_to_free()

        # Force a collision: there is already a file at the destination of downloads/photo.jpg
        (quarantine / "downloads").mkdir(parents=True, exist_ok=True)
        (quarantine / "downloads" / "photo.jpg").write_bytes(b"otro file different")

        # --- really move ---------------------------------------
        res = move_to_quarantine(sel, str(base), str(quarantine))

        check(len(res.moved) == expected_to_move,
              f"{expected_to_move} files were moved")
        check(len(res.failed) == 0, "no move failed")
        check(res.bytes_moved == bytes_expected, "the bytes moved are correct")

        # keep: they stay in their place
        check((base / "good" / "photo.jpg").exists(), "the good copy of photo.jpg is still there")
        check((base / "good" / "doc.txt").exists(), "the good copy of doc.txt is still there")

        # move: they are no longer in the source
        check(not (base / "downloads" / "photo.jpg").exists(),
              "downloads/photo.jpg left the source")
        check(not (base / "old" / "doc.txt").exists(),
              "old/doc.txt left the source")

        # move: they are in the quarantine with the structure preserved
        check((quarantine / "old" / "doc.txt").exists(),
              "old/doc.txt is in the quarantine with its path")
        check((quarantine / "downloads" / "sub" / "photo.jpg").exists(),
              "downloads/sub/photo.jpg is in the quarantine with its path")
        check((quarantine / "downloads" / "photo (1).jpg").exists(),
              "the collision with an existing file was resolved as 'photo (1).jpg'")
        check((quarantine / "downloads" / "photo.jpg").read_bytes() == b"otro file different",
              "the file that was already in the quarantine was NOT overwritten")

        # CSV log
        check(res.log_path and Path(res.log_path).exists(), "the log CSV was written")
        if res.log_path:
            content = Path(res.log_path).read_text(encoding="utf-8-sig")
            check("moved" in content and "Source" in content,
                  "the log CSV has a header and 'moved' rows")

        # nothing was deleted: 2 remain in the source and 3 were moved (+ the earlier decoy)
        n_orig = sum(1 for _ in base.rglob("*") if _.is_file())
        n_quar = sum(1 for _ in quarantine.rglob("*")
                     if _.is_file() and not _.name.endswith(".csv"))
        check(n_orig == 2, "2 files are left in the scanned folder")
        check(n_quar == 4, "the quarantine has 4 files (1 earlier decoy + 3 moved)")

    print()
    if failures:
        print(f"{len(failures)} CHECKS FAILED.")
        sys.exit(1)
    print("THE WHOLE QUARANTINE OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
