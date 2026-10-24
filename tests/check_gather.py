"""Tests of the "Gather images" tab (application/gather.py):

* list images: first level only vs recursive,
* the per-file-kind dialog: leave / move / group,
* "By files" preserves subfolders, with move and with copy,
* "Whole folder" moves/copies the complete folder,
* name collisions -> suffix (1),
* destination inside the source -> rejected.

  python tests/check_gather.py
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

# It does not touch the user's real data: the history these scripts record is temporary.
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="dup_appdata_")

from duplicate_finder.application.file_transfers import InvalidDestination, validate_destination
from duplicate_finder.application.gather import non_image_kinds
from duplicate_finder.bootstrap import build_services
from duplicate_finder.domain.transfers import COPY, MOVE

SERVICES = build_services()
list_all = SERVICES.gather.list_all
plan_by_files = SERVICES.gather.plan_by_files
gather_by_files = SERVICES.gather.gather_by_files
gather_whole_folder = SERVICES.gather.gather_whole_folder
from duplicate_finder.domain.transfers import NonImageRules  # noqa: E402

failures = []


def check(cond, msg):
    print(f"  [{'OK  ' if cond else 'FAIL'}] {msg}")
    if not cond:
        failures.append(msg)


def build(root: Path):
    (root / "holidays").mkdir(parents=True)
    (root / "2024" / "weddings").mkdir(parents=True)
    (root / "holidays" / "beach.jpg").write_bytes(b"img1")
    (root / "holidays" / "mountain.png").write_bytes(b"img2")
    (root / "2024" / "portrait.jpg").write_bytes(b"img3")
    (root / "2024" / "weddings" / "group.jpeg").write_bytes(b"img4")
    (root / "cover.png").write_bytes(b"img5")  # first level
    # non-images
    (root / "notes.txt").write_bytes(b"text")
    (root / "holidays" / "info.pdf").write_bytes(b"pdf")
    (root / "2024" / "expenses.pdf").write_bytes(b"pdf2")
    (root / "2024" / "music.mp3").write_bytes(b"mp3")


def _rel(paths, base):
    return sorted(str(Path(r).relative_to(base)).replace("\\", "/") for r in paths)


def main():
    # ---- list -----------------------------------------------------
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "Photos"
        build(root)

        img_r, others_r = list_all(str(root), recursive=True)
        check(
            _rel(img_r, root)
            == [
                "2024/portrait.jpg",
                "2024/weddings/group.jpeg",
                "cover.png",
                "holidays/beach.jpg",
                "holidays/mountain.png",
            ],
            "recursive lists the 5 images of every level",
        )
        check(
            _rel(others_r, root)
            == ["2024/expenses.pdf", "2024/music.mp3", "holidays/info.pdf", "notes.txt"],
            "recursive lists the 4 non-images",
        )

        img_n, others_n = list_all(str(root), recursive=False)
        check(_rel(img_n, root) == ["cover.png"], "first level: only cover.png")
        check(_rel(others_n, root) == ["notes.txt"], "first level: only notes.txt")

        kinds = non_image_kinds(others_r)
        check(
            set(kinds) == {"pdf", "mp3", "txt"} and len(kinds["pdf"]) == 2,
            "non_image_kinds groups by extension (pdf x2, mp3, txt)",
        )

    # ---- plan_by_files with rules -------------------------
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "Photos"
        build(root)
        destination = Path(tmp) / "Gathered"
        img, others = list_all(str(root), recursive=True)

        rules = NonImageRules(
            action_by_ext={"pdf": "group", "mp3": "move", "txt": "leave"},
            folder_by_ext={"pdf": "Documents"},
        )
        plan = plan_by_files(img, others, str(root), str(destination), rules)
        destinations = _rel([t.destination for t in plan], destination)
        print("  planned destinations:", destinations)
        check("holidays/beach.jpg" in destinations, "image -> destination/<same subpath>")
        check(
            "Documents/holidays/info.pdf" in destinations
            and "Documents/2024/expenses.pdf" in destinations,
            "pdf 'group' -> destination/Documents/<subpath>",
        )
        check("2024/music.mp3" in destinations, "mp3 'move' -> destination/<subpath> (not grouped)")
        check(not any("notes.txt" in d for d in destinations), "txt 'leave' -> not planned")

    # ---- gather_by_files: MOVE ------------------------------
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "Photos"
        build(root)
        destination = Path(tmp) / "Gathered"
        img, others = list_all(str(root), recursive=True)
        res = gather_by_files(
            img, others, str(root), str(destination), action=MOVE, rules=NonImageRules()
        )
        check(len(res.done) == 5 and not res.failed, "move: the 5 images are moved, no failure")
        check(
            (destination / "holidays" / "beach.jpg").exists()
            and not (root / "holidays" / "beach.jpg").exists(),
            "the image is in the destination and no longer in the source",
        )
        check(
            (root / "holidays" / "info.pdf").exists(),
            "the pdf ('leave' by default) is still in the source",
        )
        check(
            (root / "holidays").is_dir() and (root / "2024" / "weddings").is_dir(),
            "the subfolders of the source were NOT moved",
        )
        check(res.log_path and Path(res.log_path).exists(), "the log CSV is written")

    # ---- gather_by_files: COPY ----------------------------
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "Photos"
        build(root)
        destination = Path(tmp) / "Gathered"
        img, others = list_all(str(root), recursive=True)
        res = gather_by_files(img, others, str(root), str(destination), action=COPY)
        check(len(res.done) == 5, "copy: 5 transfers")
        check(
            (destination / "cover.png").exists() and (root / "cover.png").exists(),
            "copy leaves the original intact",
        )

    # ---- name collision -----------------------------------
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "Photos"
        (root / "a").mkdir(parents=True)
        (root / "b").mkdir(parents=True)
        (root / "a" / "photo.jpg").write_bytes(b"A")
        (root / "b" / "photo.jpg").write_bytes(b"B")
        destination = Path(tmp) / "Gathered"
        # we flatten on purpose with odd rules: we use the normal relpath,
        # but force a collision by moving both to the same place.
        execute = SERVICES.gather._transfers.execute
        from duplicate_finder.domain.transfers import Transfer

        plan = [
            Transfer(str(root / "a" / "photo.jpg"), str(destination / "photo.jpg")),
            Transfer(str(root / "b" / "photo.jpg"), str(destination / "photo.jpg")),
        ]
        execute(plan, action=MOVE)
        check(
            (destination / "photo.jpg").exists() and (destination / "photo (1).jpg").exists(),
            "the second collision is saved as 'photo (1).jpg', without overwriting",
        )

    # ---- whole folder ----------------------------------------
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "TripAlbum"
        build(root)
        destination = Path(tmp) / "Destination"
        res = gather_whole_folder(str(root), str(destination), action=MOVE)
        check(
            res.done and (destination / "TripAlbum" / "holidays" / "beach.jpg").exists(),
            "whole folder: destination/TripAlbum/... with everything inside",
        )
        check(
            (destination / "TripAlbum" / "notes.txt").exists(),
            "whole folder includes the non-images",
        )
        check(not root.exists(), "move: the original folder is gone")

    # ---- invalid destination -----------------------------------
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "Photos"
        root.mkdir()
        try:
            validate_destination(str(root / "sub"), str(root))
            check(False, "destination inside the source must raise InvalidDestination")
        except InvalidDestination:
            check(True, "destination inside the source -> InvalidDestination")

    print()
    if failures:
        print(f"{len(failures)} CHECKS FAILED.")
        sys.exit(1)
    print("GATHER OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
