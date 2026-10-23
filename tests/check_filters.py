"""Test of the scan filter (exclusion by extension, name, folder
and minimum size) and of the breakdown by extension.

    python tests/check_filters.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.scanner import scan                       # noqa: E402
from core.filters import ScanFilter, CATEGORY_EXTENSIONS  # noqa: E402

failures = []


def check(cond, msg):
    state = "OK  " if cond else "FALLA"
    print(f"  [{state}] {msg}")
    if not cond:
        failures.append(msg)


def build(base: Path):
    def write(rel, data: bytes):
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    doc = b"contenido de documento\n" * 20
    tmp_data = b"basura temporal\n" * 20
    img_data = b"pixeles\n" * 50

    # Real .txt group (it must survive every filter unless .txt is excluded)
    write("a/doc.txt", doc)
    write("b/doc.txt", doc)

    # .tmp group (excluded by extension in the default filter)
    write("a/cache.tmp", tmp_data)
    write("b/otra.tmp", tmp_data)

    # Group inside node_modules (excluded by folder)
    write("proj/node_modules/x.txt", img_data)
    write("proj/node_modules/y.txt", img_data)
    write("proj/src/z.txt", img_data)   # copy outside node_modules -> left without a match

    # Duplicated Thumbs.db (excluded by name)
    write("a/Thumbs.db", b"thumbs\n")
    write("b/Thumbs.db", b"thumbs\n")

    # Two empty files (excluded with min_size=1)
    write("a/vacio.txt", b"")
    write("b/vacio.txt", b"")

    # Photo group (.jpg) and audio group (.mp3), for the whitelist
    photo_data = b"binario de foto\n" * 15
    audio_data = b"binario de audio\n" * 15
    write("fotos/img1.jpg", photo_data)
    write("fotos/img2.jpg", photo_data)
    write("musica/cancion1.mp3", audio_data)
    write("musica/cancion2.mp3", audio_data)


def paths_by_group(result):
    return sorted(
        sorted(Path(a.path).name for a in g.files)
        for g in result.groups
    )


def main():
    with tempfile.TemporaryDirectory(prefix="dup_filtro_") as tmp:
        base = Path(tmp) / "arbol"
        build(base)

        print("\n--- Sin filtro ---")
        r0 = scan(str(base))
        g0 = paths_by_group(r0)
        print("  grupos:", g0)
        check(len(r0.groups) == 7,
              "sin filtro detecta 7 grupos (txt, tmp, node_modules, Thumbs.db, "
              "vacios, jpg, mp3)")
        check(r0.total_excluded == 0, "sin filtro no excluye nada")

        print("\n--- Filtro por defecto ---")
        r1 = scan(str(base), filter=ScanFilter.by_default())
        g1 = paths_by_group(r1)
        print("  grupos:", g1)
        check(g1 == [["cancion1.mp3", "cancion2.mp3"], ["doc.txt", "doc.txt"],
                     ["img1.jpg", "img2.jpg"]],
              "filtro por defecto deja doc.txt, las fotos y el audio "
              "(la basura típica no incluye jpg/mp3)")
        check(r1.total_excluded > 0, "filtro por defecto reporta archivos excluidos")

        print("\n--- Filtro: excluir .txt ---")
        f2 = ScanFilter(excluded_extensions={"txt"})
        r2 = scan(str(base), filter=f2)
        exts = {e for e, _c, _b in r2.summary_by_extension()}
        print("  extensiones en resultado:", exts)
        check("txt" not in exts, "excluir .txt quita todos los .txt del resultado")

        print("\n--- Lista blanca: buscar solo imágenes ---")
        f3 = ScanFilter(included_extensions=CATEGORY_EXTENSIONS["images"])
        r3 = scan(str(base), filter=f3)
        g3 = paths_by_group(r3)
        print("  grupos:", g3)
        check(g3 == [["img1.jpg", "img2.jpg"]],
              "'solo imágenes' deja únicamente el grupo de fotos")
        check(r3.total_excluded > 0,
              "'solo imágenes' reporta como excluido todo lo que no es imagen")

        print("\n--- Lista blanca: imágenes + audio ---")
        combined = (CATEGORY_EXTENSIONS["images"]
                     | CATEGORY_EXTENSIONS["audio"])
        f4 = ScanFilter(included_extensions=combined)
        r4 = scan(str(base), filter=f4)
        g4 = paths_by_group(r4)
        print("  grupos:", g4)
        check(g4 == [["cancion1.mp3", "cancion2.mp3"], ["img1.jpg", "img2.jpg"]],
              "combinar 'imágenes' + 'audio' deja fotos y música, nada más")

        print("\n--- Desglose por extensión (sin filtro) ---")
        for ext, c, b in r0.summary_by_extension():
            print(f"    {ext:15} {c} archivos  {b} bytes")
        exts0 = {e for e, _c, _b in r0.summary_by_extension()}
        check({"txt", "tmp", "db", "jpg", "mp3"} <= exts0,
              "el desglose lista txt, tmp, db, jpg y mp3")

    print()
    if failures:
        print(f"FALLARON {len(failures)} comprobaciones.")
        sys.exit(1)
    print("TODOS LOS FILTROS OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
