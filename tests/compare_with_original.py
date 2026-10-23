"""Prueba de paridad: el núcleo nuevo detecta los mismos duplicados que
el script de consola original `buscar_duplicados.py`.

Qué hace:
  1. Crea un árbol de carpetas de prueba con duplicados conocidos
     (y varias trampas: mismo tamaño pero distinto contenido, archivos
     vacíos, archivos grandes que solo difieren al final, etc.).
  2. Lo escanea con el núcleo nuevo (core.scanner.escanear).
  3. Lo escanea con la lógica del script original.
  4. Compara los grupos de duplicados de ambos: deben ser idénticos
     (mismos conjuntos de rutas). El valor del hash puede diferir
     (uno usa BLAKE2b, el otro SHA-256); lo que importa es la
     agrupación.
  5. Si se pasa una ruta como argumento, repite la comparación sobre
     esa carpeta real además del árbol sintético.

Uso:
    python tests/compare_with_original.py
    python tests/compare_with_original.py "D:\\CarpetaReal"
"""

import importlib.util
import os
import sys
import tempfile
from pathlib import Path

# --- imports del proyecto ------------------------------------------------
APP_ROOT = Path(__file__).resolve().parents[1]          # raíz del repo
REPO_ROOT = APP_ROOT / "docs" / "origin"                 # aquí está el script original
sys.path.insert(0, str(APP_ROOT))

from core.scanner import scan                        # noqa: E402


def _load_original_script():
    """Importa buscar_duplicados.py desde docs/origin/ como módulo."""
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
# Normalización de resultados a "conjunto de grupos", donde cada grupo
# es un frozenset de rutas absolutas normalizadas.
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
# Árbol de prueba sintético.
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
    large_2 = b"X" * 200_000 + b"final-2"   # mismo tamaño, difiere al final
    large_3 = b"X" * 200_000 + b"final-1"   # duplicado real de grande_1

    # Grupo duplicado 1: 3 copias del mismo contenido en carpetas distintas
    write("originales/doc.txt", content_a)
    write("copias/doc (1).txt", content_a)
    write("backup/sub/doc.txt", content_a)

    # Grupo duplicado 2: 2 copias de otro contenido
    write("fotos/img.dat", content_b)
    write("fotos/respaldo/img.dat", content_b)

    # Trampa: mismo tamaño que contenido_b pero distinto contenido -> NO dup
    write("fotos/casi.dat", b"z" * len(content_b))

    # Archivos grandes: grande_1 y grande_3 son duplicados; grande_2 no.
    write("grandes/a.bin", large_1)
    write("grandes/b.bin", large_2)
    write("grandes/c.bin", large_3)

    # Trampa: dos archivos vacíos (mismo contenido: ninguno) -> SÍ son dup
    write("vacios/uno.txt", b"")
    write("vacios/dos.txt", b"")

    # Archivo único sin pareja
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
