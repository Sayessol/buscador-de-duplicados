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

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image                                          # noqa: E402

from core.scanner import scan                              # noqa: E402
from core.selection import DuplicateSelection, KEEP      # noqa: E402
from core.perceptual import analyze_folder                   # noqa: E402
from core.quarantine import move_to_quarantine, plan_moves  # noqa: E402

failures = []


def check(cond, msg):
    print(f"  [{'OK  ' if cond else 'FALLA'}] {msg}")
    if not cond:
        failures.append(msg)


def _photo(seed, size=(600, 400)):
    import random
    rnd = random.Random(seed)
    im = Image.new("RGB", size, (10, 10, 10))
    for _ in range(12):
        x0, y0 = rnd.randint(0, size[0]), rnd.randint(0, size[1])
        im.paste((rnd.randint(0, 255), rnd.randint(0, 255), rnd.randint(0, 255)),
                 (x0, y0, x0 + 120, y0 + 120))
    return im


def build(root: Path):
    (root / "vacaciones").mkdir(parents=True)
    (root / "familia" / "recortes").mkdir(parents=True)
    (root / "descargas").mkdir(parents=True)

    _photo(1).save(root / "vacaciones" / "playa.png")
    _photo(2).save(root / "familia" / "retrato.png")
    _photo(3).save(root / "unica.png")

    # Group A EXACT: same bytes in vacaciones and descargas
    bytes_a = (root / "vacaciones" / "playa.png").read_bytes()
    (root / "descargas" / "playa.png").write_bytes(bytes_a)
    # Group B EXACT: same bytes in familia and familia/recortes
    bytes_b = (root / "familia" / "retrato.png").read_bytes()
    (root / "familia" / "recortes" / "retrato.png").write_bytes(bytes_b)
    # SIMILAR versions (recompressed JPEG) for the other flow
    _photo(1).save(root / "descargas" / "playa_baja.jpg", quality=35)
    _photo(2).save(root / "familia" / "recortes" / "retrato_baja.jpg", quality=35)


def _tree(p: Path):
    return sorted(str(x.relative_to(p)).replace("\\", "/") + ("/" if x.is_dir() else "")
                  for x in p.rglob("*"))


def _run_case(name, make_selection):
    print(f"\n=== {name} ===")
    with tempfile.TemporaryDirectory(prefix="dup_cc_") as tmp:
        root = Path(tmp) / "MisFotos"
        quarantine = Path(tmp) / "Escritorio" / "Cuarentena fotos"
        build(root)

        folders_before = {str(x.relative_to(root))
                          for x in root.rglob("*") if x.is_dir()}
        files_before = sum(1 for x in root.rglob("*") if x.is_file())

        sel, root_arg = make_selection(root)

        # Inspect the PLAN before running it.
        plan = plan_moves(sel, root_arg, str(quarantine))
        print("  plan de movimientos:")
        for m in plan:
            kind = ("CARPETA!!!" if Path(m.source).is_dir()
                    else "archivo" if Path(m.source).is_file() else "??")
            print(f"    [{kind}] {Path(m.source).relative_to(root)}  ->  "
                  f"{Path(m.destination).relative_to(quarantine.parent)}")
            check(Path(m.source).is_file(),
                  f"el origen a mover es un archivo, no una carpeta: {m.source}")

        res = move_to_quarantine(sel, root_arg, str(quarantine))
        check(not res.failed, "ningún movimiento falló")

        # The source folders STILL exist.
        folders_after = {str(x.relative_to(root))
                            for x in root.rglob("*") if x.is_dir()}
        check(folders_before == folders_after,
              f"las subcarpetas del origen no se han movido "
              f"(antes={sorted(folders_before)}, después={sorted(folders_after)})")

        # The 'keep' copies stay in their place.
        for gi, group in enumerate(sel.result.groups):
            for a in group.files:
                if sel.decision(gi, a.path) == KEEP:
                    check(Path(a.path).is_file(),
                          f"la copia a conservar sigue existaste: "
                          f"{Path(a.path).name}")

        # In the quarantine there are only FILES (+ the CSV log), hanging from
        # the recreated structure; no whole folder from the source.
        actually_moved = [x for x in quarantine.rglob("*")
                          if x.is_file() and not x.name.endswith(".csv")]
        check(len(actually_moved) == len(res.moved),
              f"en la cuarentena hay {len(res.moved)} archivos movidos")
        print("  árbol de la cuarentena:")
        for line in _tree(quarantine):
            print(f"    {line}")

        # Nothing lost: (left in the source) + (moved to quarantine) == (before)
        remain = [x for x in root.rglob("*") if x.is_file()]
        check(len(remain) + len(actually_moved) == files_before,
              f"no se ha perdido nada ({len(remain)} quedan + "
              f"{len(actually_moved)} movidos == {files_before} antes)")
        check(len(res.moved) >= 1, "se ha movido al menos un archivo")


def exact_selection(root):
    r = scan(str(root))
    sel = DuplicateSelection(r)
    sel.preselect_primary()
    return sel, str(root)


def similar_selection(root):
    r = analyze_folder(str(root), hamming_threshold=12)
    sel = DuplicateSelection(r)
    for gi, g in enumerate(r.groups):
        sel.keep_only(gi, g.files[0].path)
    return sel, str(root)


def main():
    _run_case("Duplicados exactos", exact_selection)
    _run_case("Fotos parecidas", similar_selection)

    print()
    if failures:
        print(f"FALLARON {len(failures)} comprobaciones.")
        sys.exit(1)
    print("MUEVE ARCHIVOS, NO CARPETAS: OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
