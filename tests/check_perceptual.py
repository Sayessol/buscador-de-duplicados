"""Test of the similar-photos core.

It generates a set of synthetic images (an "original" photo and several
altered versions: recompressed, resized, with a colour filter,
with a watermark) plus unrelated images, and checks that the
grouping:

  * puts all the versions of the same photo in one group,
  * does NOT put together images that have nothing to do with each other,
  * picks the one with the most resolution as "best".

With a path as an argument, it also analyzes that real folder and lists
the groups found (useful to calibrate the threshold with your own photos):

    python tests/check_perceptual.py
    python tests/check_perceptual.py "D:\\Photos" 10
"""

import random
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image, ImageDraw, ImageEnhance   # noqa: E402

from core.perceptual import analyze_folder  # noqa: E402
from core.hashing import format_size                       # noqa: E402

failures = []


def check(cond, msg):
    print(f"  [{'OK  ' if cond else 'FAIL'}] {msg}")
    if not cond:
        failures.append(msg)


def photo_base(seed, size=(900, 600)):
    """Image with coloured shapes: enough structure for the dHash."""
    rnd = random.Random(seed)
    im = Image.new("RGB", size, (rnd.randint(0, 60),) * 3)
    d = ImageDraw.Draw(im)
    for _ in range(18):
        x0, y0 = rnd.randint(0, size[0]), rnd.randint(0, size[1])
        x1, y1 = x0 + rnd.randint(40, 300), y0 + rnd.randint(40, 300)
        col = (rnd.randint(0, 255), rnd.randint(0, 255), rnd.randint(0, 255))
        if rnd.random() < 0.5:
            d.rectangle([x0, y0, x1, y1], fill=col)
        else:
            d.ellipse([x0, y0, x1, y1], fill=col)
    return im


def build(base: Path):
    base.mkdir(parents=True, exist_ok=True)
    original = photo_base(1)

    # --- versions of the SAME photo (they must end up in one group) --------
    original.save(base / "beach_original.png")
    original.save(base / "beach_calidad_baja.jpg", quality=25)
    original.resize((450, 300)).save(base / "beach_pequena.jpg", quality=80)

    filtered = ImageEnhance.Color(original).enhance(1.8)
    filtered = ImageEnhance.Brightness(filtered).enhance(1.15)
    filtered.save(base / "beach_con_filtro.jpg", quality=85)

    mark = original.copy()
    d = ImageDraw.Draw(mark)
    d.rectangle([740, 550, 890, 590], fill=(255, 255, 255))
    d.text((748, 560), "©2024", fill=(0, 0, 0))
    mark.save(base / "beach_marca_agua.jpg", quality=85)

    # --- another, different photo, also with a couple of versions ----------
    other = photo_base(99)
    other.save(base / "mountain_original.png")
    other.save(base / "mountain_recomprimida.jpg", quality=30)

    # --- loose, unrelated photos ---------------------------------
    for s in (7, 21, 42):
        photo_base(s).save(base / f"suelta_{s}.jpg", quality=80)

    # a corrupt image (it must go to 'errors', not break anything)
    (base / "rota.jpg").write_bytes(b"esto no es una image")


def names(group):
    return sorted(Path(a.path).name for a in group.files)


def main():
    with tempfile.TemporaryDirectory(prefix="dup_perc_") as tmp:
        base = Path(tmp) / "photos"
        build(base)

        r = analyze_folder(str(base), hamming_threshold=12)
        print(f"\n  {r.total_images} images analyzed, {r.total_groups} groups, "
              f"{len(r.errors)} unreadable\n")
        for i, g in enumerate(r.groups, 1):
            best = g.fingerprints[0]
            print(f"  Group {i}  (best: {Path(g.files[0].path).name}, {best.width}x{best.height}):")
            for a, s in zip(g.files, g.similarity):
                print(f"      {s * 100:5.1f}%  {Path(a.path).name}")

        groups_by_name = {tuple(names(g)) for g in r.groups}

        beach = {"beach_original.png", "beach_calidad_baja.jpg",
                 "beach_pequena.jpg", "beach_con_filtro.jpg",
                 "beach_marca_agua.jpg"}
        mountain = {"mountain_original.png", "mountain_recomprimida.jpg"}

        beach_group = next((g for g in groups_by_name if "beach_original.png" in g), None)
        mountain_group = next((g for g in groups_by_name if "mountain_original.png" in g), None)

        check(beach_group is not None and beach.issubset(set(beach_group)),
              "the 5 versions of the photo 'beach' fall in the same group")
        check(mountain_group is not None and set(mountain_group) == mountain,
              "the 2 versions of 'mountain' form their own group")
        check(all(not any(n.startswith("loose_") for n in g)
                  for g in groups_by_name),
              "no loose photo slipped into a group")
        check(len(r.errors) == 1 and "rota.jpg" in r.errors[0][0],
              "the corrupt image is reported as an error, it does not break the analysis")

        if beach_group:
            g = next(g for g in r.groups if "beach_original.png" in names(g))
            check(Path(g.files[0].path).name == "beach_original.png",
                  "the 'best' copy of beach is the original PNG (higher resolution)")
            check(g.reclaimable_space > 0, "the group reports recoverable space")

    # --- optional real folder --------------------------------------
    if len(sys.argv) > 1 and Path(sys.argv[1]).is_dir():
        threshold = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        print(f"\n=== Real folder: {sys.argv[1]}  (threshold {threshold}) ===")
        rr = analyze_folder(sys.argv[1], hamming_threshold=threshold,
                              progress=lambda a, t, m: print(f"  {m}", end="\r"))
        print(f"\n  {rr.total_images} images, {rr.total_groups} groups of similar ones, "
              f"recoverable {format_size(rr.total_reclaimable_space)}")
        for i, g in enumerate(rr.groups[:15], 1):
            print(f"\n  Group {i} ({g.count} photos):")
            for a, s in zip(g.files, g.similarity):
                print(f"      {s * 100:5.1f}%  {a.path}")

    print()
    if failures:
        print(f"{len(failures)} CHECKS FAILED.")
        sys.exit(1)
    print("PERCEPTUAL CORE OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
