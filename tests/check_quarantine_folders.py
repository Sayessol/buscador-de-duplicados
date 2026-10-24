"""Reproduces the case the user reported: photos spread across several
subfolders inside a folder, moved to an external quarantine.

It explicitly checks that FILES are MOVED and NOT FOLDERS:

  * the subfolders of the source still exist after moving,
  * the quarantine contains FILES (not whole folders moved loose),
  * everything moved is a regular file, never a directory,
  * the copies marked to keep are not touched.

It tests both the "Exact duplicates" flow and the "Similar photos" one.

    python tests/check_quarantine_folders.py
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

# It does not touch the user's real data: the history these scripts record is temporary.
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="dup_appdata_")

from PIL import Image

from duplicate_finder.bootstrap import build_services

SERVICES = build_services()
scan = SERVICES.scan_duplicates
from duplicate_finder.domain.selection import KEEP  # noqa: E402

analyze_folder = SERVICES.find_similar_photos
from duplicate_finder.application.quarantine import plan_moves  # noqa: E402

move_to_quarantine = SERVICES.move_to_quarantine

failures = []


def check(cond, msg):
    print(f"  [{'OK  ' if cond else 'FAIL'}] {msg}")
    if not cond:
        failures.append(msg)


def _photo(seed, size=(600, 400)):
    import random

    rnd = random.Random(seed)
    im = Image.new("RGB", size, (10, 10, 10))
    for _ in range(12):
        x0, y0 = rnd.randint(0, size[0]), rnd.randint(0, size[1])
        im.paste(
            (rnd.randint(0, 255), rnd.randint(0, 255), rnd.randint(0, 255)),
            (x0, y0, x0 + 120, y0 + 120),
        )
    return im


def build(root: Path):
    (root / "holidays").mkdir(parents=True)
    (root / "family" / "crops").mkdir(parents=True)
    (root / "downloads").mkdir(parents=True)

    _photo(1).save(root / "holidays" / "beach.png")
    _photo(2).save(root / "family" / "portrait.png")
    _photo(3).save(root / "unica.png")

    # Group A EXACT: same bytes in holidays and downloads
    bytes_a = (root / "holidays" / "beach.png").read_bytes()
    (root / "downloads" / "beach.png").write_bytes(bytes_a)
    # Group B EXACT: same bytes in familia and familia/recortes
    bytes_b = (root / "family" / "portrait.png").read_bytes()
    (root / "family" / "crops" / "portrait.png").write_bytes(bytes_b)
    # SIMILAR versions (recompressed JPEG) for the other flow
    _photo(1).save(root / "downloads" / "beach_baja.jpg", quality=35)
    _photo(2).save(root / "family" / "crops" / "portrait_baja.jpg", quality=35)


def _tree(p: Path):
    return sorted(
        str(x.relative_to(p)).replace("\\", "/") + ("/" if x.is_dir() else "") for x in p.rglob("*")
    )


def _run_case(name, make_selection):
    print(f"\n=== {name} ===")
    with tempfile.TemporaryDirectory(prefix="dup_cc_") as tmp:
        root = Path(tmp) / "MyPhotos"
        quarantine = Path(tmp) / "Desktop" / "Photos quarantine"
        build(root)

        folders_before = {str(x.relative_to(root)) for x in root.rglob("*") if x.is_dir()}
        files_before = sum(1 for x in root.rglob("*") if x.is_file())

        sel, root_arg = make_selection(root)

        # Inspect the PLAN before running it.
        plan = plan_moves(sel, root_arg, str(quarantine))
        print("  move plan:")
        for m in plan:
            kind = (
                "FOLDER!!!"
                if Path(m.source).is_dir()
                else "file"
                if Path(m.source).is_file()
                else "??"
            )
            print(
                f"    [{kind}] {Path(m.source).relative_to(root)}  ->  "
                f"{Path(m.destination).relative_to(quarantine.parent)}"
            )
            check(
                Path(m.source).is_file(), f"the source to move is a file, not a folder: {m.source}"
            )

        res = move_to_quarantine(sel, root_arg, str(quarantine))
        check(not res.failed, "no move failed")

        # The source folders STILL exist.
        folders_after = {str(x.relative_to(root)) for x in root.rglob("*") if x.is_dir()}
        check(
            folders_before == folders_after,
            f"the source subfolders were not moved (before={sorted(folders_before)}, "
            f"after={sorted(folders_after)})",
        )

        # The 'keep' copies stay in their place.
        for gi, group in enumerate(sel.result.groups):
            for a in group.files:
                if sel.decision(gi, a.path) == KEEP:
                    check(
                        Path(a.path).is_file(),
                        f"the file to keep still exists: {Path(a.path).name}",
                    )

        # In the quarantine there are only FILES (+ the CSV log), hanging from
        # the recreated structure; no whole folder from the source.
        actually_moved = [
            x for x in quarantine.rglob("*") if x.is_file() and not x.name.endswith(".csv")
        ]
        check(
            len(actually_moved) == len(res.moved),
            f"the quarantine has {len(res.moved)} files moved",
        )
        print("  quarantine tree:")
        for line in _tree(quarantine):
            print(f"    {line}")

        # Nothing lost: (left in the source) + (moved to quarantine) == (before)
        remain = [x for x in root.rglob("*") if x.is_file()]
        check(
            len(remain) + len(actually_moved) == files_before,
            f"nothing was lost ({len(remain)} left + {len(actually_moved)} moved "
            f"== {files_before} before)",
        )
        check(len(res.moved) >= 1, "at least one file was moved")


def exact_selection(root):
    r = scan(str(root))
    sel = SERVICES.start_selection(r)
    sel.preselect_primary()
    return sel, str(root)


def similar_selection(root):
    r = analyze_folder(str(root), hamming_threshold=12)
    sel = SERVICES.start_selection(r)
    for gi, g in enumerate(r.groups):
        sel.keep_only(gi, g.files[0].path)
    return sel, str(root)


def main():
    _run_case("Exact duplicates", exact_selection)
    _run_case("Similar photos", similar_selection)

    print()
    if failures:
        print(f"{len(failures)} CHECKS FAILED.")
        sys.exit(1)
    print("MOVES FILES, NOT FOLDERS: OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
