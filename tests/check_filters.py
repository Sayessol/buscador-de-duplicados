"""Test of the scan filter (exclusion by extension, name, folder
and minimum size) and of the breakdown by extension.

    python tests/check_filters.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from duplicate_finder.application.scan_duplicates import scan  # noqa: E402
from duplicate_finder.domain.filters import ScanFilter, CATEGORY_EXTENSIONS  # noqa: E402

failures = []


def check(cond, msg):
    state = "OK  " if cond else "FAIL"
    print(f"  [{state}] {msg}")
    if not cond:
        failures.append(msg)


def build(base: Path):
    def write(rel, data: bytes):
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    doc = b"content de document\n" * 20
    tmp_data = b"basura temporal\n" * 20
    img_data = b"pixeles\n" * 50

    # Real .txt group (it must survive every filter unless .txt is excluded)
    write("a/doc.txt", doc)
    write("b/doc.txt", doc)

    # .tmp group (excluded by extension in the default filter)
    write("a/cache.tmp", tmp_data)
    write("b/other.tmp", tmp_data)

    # Group inside node_modules (excluded by folder)
    write("proj/node_modules/x.txt", img_data)
    write("proj/node_modules/y.txt", img_data)
    write("proj/src/z.txt", img_data)   # copy outside node_modules -> left without a match

    # Duplicated Thumbs.db (excluded by name)
    write("a/Thumbs.db", b"thumbs\n")
    write("b/Thumbs.db", b"thumbs\n")

    # Two empty files (excluded with min_size=1)
    write("a/empty.txt", b"")
    write("b/empty.txt", b"")

    # Photo group (.jpg) and audio group (.mp3), for the whitelist
    photo_data = b"binario de photo\n" * 15
    audio_data = b"binario de audio\n" * 15
    write("photos/img1.jpg", photo_data)
    write("photos/img2.jpg", photo_data)
    write("music/song1.mp3", audio_data)
    write("music/song2.mp3", audio_data)


def paths_by_group(result):
    return sorted(
        sorted(Path(a.path).name for a in g.files)
        for g in result.groups
    )


def main():
    with tempfile.TemporaryDirectory(prefix="dup_filtro_") as tmp:
        base = Path(tmp) / "tree"
        build(base)

        print("\n--- No filter ---")
        r0 = scan(str(base))
        g0 = paths_by_group(r0)
        print("  groups:", g0)
        check(len(r0.groups) == 7,
              "no filter finds 7 groups (txt, tmp, node_modules, Thumbs.db, empties, jpg, mp3)")
        check(r0.total_excluded == 0, "no filter excludes nothing")

        print("\n--- Default filter ---")
        r1 = scan(str(base), filter=ScanFilter.by_default())
        g1 = paths_by_group(r1)
        print("  groups:", g1)
        check(g1 == [["doc.txt", "doc.txt"], ["img1.jpg", "img2.jpg"],
                     ["song1.mp3", "song2.mp3"]],
              "default filter keeps doc.txt, the photos and the audio "
              "(typical junk does not include jpg/mp3)")
        check(r1.total_excluded > 0, "default filter reports excluded files")

        print("\n--- Filter: exclude .txt ---")
        f2 = ScanFilter(excluded_extensions={"txt"})
        r2 = scan(str(base), filter=f2)
        exts = {e for e, _c, _b in r2.summary_by_extension()}
        print("  extensions in the result:", exts)
        check("txt" not in exts, "excluding .txt removes every .txt from the result")

        print("\n--- Allow list: images only ---")
        f3 = ScanFilter(included_extensions=CATEGORY_EXTENSIONS["images"])
        r3 = scan(str(base), filter=f3)
        g3 = paths_by_group(r3)
        print("  groups:", g3)
        check(g3 == [["img1.jpg", "img2.jpg"]],
              "'images only' leaves just the photo group")
        check(r3.total_excluded > 0,
              "'images only' reports everything that is not an image as excluded")

        print("\n--- Allow list: images + audio ---")
        combined = (CATEGORY_EXTENSIONS["images"]
                     | CATEGORY_EXTENSIONS["audio"])
        f4 = ScanFilter(included_extensions=combined)
        r4 = scan(str(base), filter=f4)
        g4 = paths_by_group(r4)
        print("  groups:", g4)
        check(g4 == [["img1.jpg", "img2.jpg"], ["song1.mp3", "song2.mp3"]],
              "combining 'images' + 'audio' leaves photos and music, nothing else")

        print("\n--- Breakdown by extension (no filter) ---")
        for ext, c, b in r0.summary_by_extension():
            print(f"    {ext:15} {c} files  {b} bytes")
        exts0 = {e for e, _c, _b in r0.summary_by_extension()}
        check({"txt", "tmp", "db", "jpg", "mp3"} <= exts0,
              "the breakdown lists txt, tmp, db, jpg and mp3")

    print()
    if failures:
        print(f"{len(failures)} CHECKS FAILED.")
        sys.exit(1)
    print("ALL FILTERS OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
