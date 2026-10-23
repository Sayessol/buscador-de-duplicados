"""Parity test: the new core detects the same duplicates as
the original console script `buscar_duplicados.py`.

What it does:
  1. Creates a tree of test folders with known duplicates
     (and several traps: same size but different content, empty
     files, large files that only differ at the end, etc.).
  2. Scans it with the new core (core.scanner.scan).
  3. Scans it with the logic of the original script.
  4. Compares the groups of duplicates from both: they must be identical
     (same sets of paths). The hash value may differ
     (one uses BLAKE2b, the other SHA-256); what matters is the
     grouping.
  5. If a path is passed as an argument, repeats the comparison on
     that real folder as well as on the synthetic tree.

Usage:
    python tests/compare_with_original.py
    python tests/compare_with_original.py "D:\\RealFolder"
"""

import importlib.util
import os
import sys
import tempfile
from pathlib import Path

# --- project imports ------------------------------------------------
APP_ROOT = Path(__file__).resolve().parents[1]          # root of the repo
REPO_ROOT = APP_ROOT / "docs" / "origin"                 # the original script is here
sys.path.insert(0, str(APP_ROOT))

from core.scanner import scan                        # noqa: E402


def _load_original_script():
    """Imports buscar_duplicados.py from docs/origin/ as a module."""
    path = REPO_ROOT / "buscar_duplicados.py"
    if not path.exists():
        raise FileNotFoundError(
            f"No encuentro el script original en {path}. "
            "Colócalo ahí para poder comparar."
        )
    spec = importlib.util.spec_from_file_location("buscar_duplicados_orig", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ----------------------------------------------------------------------
# Normalization of results to a "set of groups", where each group
# is a frozenset of normalized absolute paths.
# ----------------------------------------------------------------------
def _norm(path):
    return os.path.normcase(os.path.abspath(path))


def new_core_groups(folder):
    result = scan(folder)
    return {
        frozenset(_norm(a.path) for a in g.files)
        for g in result.groups
    }, result


def original_script_groups(folder, orig):
    files_by_hash = orig.escanear_carpeta(folder)
    return {
        frozenset(_norm(path) for path, _size in items)
        for items in files_by_hash.values()
        if len(items) > 1
    }


# ----------------------------------------------------------------------
# Synthetic test tree.
# ----------------------------------------------------------------------
def build_test_tree(base: Path):
    def write(rel, data: bytes):
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return p

    content_a = b"contenido identico A\n" * 10
    content_b = b"otra cosa totalmente distinta B\n" * 7
    large_1 = b"X" * 200_000 + b"final-1"
    large_2 = b"X" * 200_000 + b"final-2"   # same size, differs at the end
    large_3 = b"X" * 200_000 + b"final-1"   # real duplicate of large_1

    # Duplicate group 1: 3 copies of the same content in different folders
    write("originales/doc.txt", content_a)
    write("copias/doc (1).txt", content_a)
    write("backup/sub/doc.txt", content_a)

    # Duplicate group 2: 2 copies of other content
    write("fotos/img.dat", content_b)
    write("fotos/respaldo/img.dat", content_b)

    # Trap: same size as content_b but different content -> NOT a dup
    write("fotos/casi.dat", b"z" * len(content_b))

    # Large files: large_1 and large_3 are duplicates; large_2 is not.
    write("grandes/a.bin", large_1)
    write("grandes/b.bin", large_2)
    write("grandes/c.bin", large_3)

    # Trap: two empty files (same content: none) -> they ARE dups
    write("vacios/uno.txt", b"")
    write("vacios/dos.txt", b"")

    # Single file with no match
    write("solo/unico.txt", b"nadie mas tiene esto\n")


def compare_folder(folder, orig, label):
    print(f"\n=== Comparando: {label} ===")
    print(f"    Ruta: {folder}")

    new, result = new_core_groups(folder)
    old = original_script_groups(folder, orig)

    print(f"    Núcleo nuevo:    {len(new)} grupos, "
          f"{result.total_files_duplicates} archivos duplicados, "
          f"recuperable {result.total_reclaimable_space} bytes")
    print(f"    Script original: {len(old)} grupos")

    if result.errors:
        print(f"    (avisos de lectura: {len(result.errors)})")

    if new == old:
        print("    RESULTADO: IDENTICO  [OK]")
        return True

    print("    RESULTADO: DIFERENCIAS  [FALLA]")
    only_new = new - old
    only_old = old - new
    for g in only_new:
        print("      + solo lo detecta el núcleo nuevo:")
        for r in sorted(g):
            print(f"          {r}")
    for g in only_old:
        print("      - solo lo detecta el script original:")
        for r in sorted(g):
            print(f"          {r}")
    return False


def main():
    orig = _load_original_script()
    ok = True

    with tempfile.TemporaryDirectory(prefix="dup_prueba_") as tmp:
        base = Path(tmp) / "arbol"
        build_test_tree(base)
        ok &= compare_folder(str(base), orig, "árbol sintético")

    for real_path in sys.argv[1:]:
        if os.path.isdir(real_path):
            ok &= compare_folder(real_path, orig, "carpeta real")
        else:
            print(f"\n[AVISO] No es una carpeta, se ignora: {real_path}")

    print()
    if ok:
        print("TODO OK: el núcleo nuevo agrupa los duplicados igual que el original.")
        sys.exit(0)
    else:
        print("HAY DIFERENCIAS: revisar arriba.")
        sys.exit(1)


if __name__ == "__main__":
    main()
