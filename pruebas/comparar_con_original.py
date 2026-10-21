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
    python pruebas/comparar_con_original.py
    python pruebas/comparar_con_original.py "D:\\CarpetaReal"
"""

import importlib.util
import os
import sys
import tempfile
from pathlib import Path

# --- imports del proyecto ------------------------------------------------
RAIZ_APP = Path(__file__).resolve().parents[1]          # raíz del repo
RAIZ_REPO = RAIZ_APP / "docs" / "origen"                 # aquí está el script original
sys.path.insert(0, str(RAIZ_APP))

from core.scanner import escanear                        # noqa: E402


def _cargar_script_original():
    """Importa buscar_duplicados.py desde docs/origen/ como módulo."""
    ruta = RAIZ_REPO / "buscar_duplicados.py"
    if not ruta.exists():
        raise FileNotFoundError(
            f"No encuentro el script original en {ruta}. "
            "Colócalo ahí para poder comparar."
        )
    spec = importlib.util.spec_from_file_location("buscar_duplicados_orig", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


# ----------------------------------------------------------------------
# Normalización de resultados a "conjunto de grupos", donde cada grupo
# es un frozenset de rutas absolutas normalizadas.
# ----------------------------------------------------------------------
def _norm(ruta):
    return os.path.normcase(os.path.abspath(ruta))


def grupos_nucleo_nuevo(carpeta):
    resultado = escanear(carpeta)
    return {
        frozenset(_norm(a.ruta) for a in g.archivos)
        for g in resultado.grupos
    }, resultado


def grupos_script_original(carpeta, orig):
    archivos_por_hash = orig.escanear_carpeta(carpeta)
    return {
        frozenset(_norm(ruta) for ruta, _tam in lista)
        for lista in archivos_por_hash.values()
        if len(lista) > 1
    }


# ----------------------------------------------------------------------
# Árbol de prueba sintético.
# ----------------------------------------------------------------------
def construir_arbol_de_prueba(base: Path):
    def escribir(rel, data: bytes):
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return p

    contenido_a = b"contenido identico A\n" * 10
    contenido_b = b"otra cosa totalmente distinta B\n" * 7
    grande_1 = b"X" * 200_000 + b"final-1"
    grande_2 = b"X" * 200_000 + b"final-2"   # mismo tamaño, difiere al final
    grande_3 = b"X" * 200_000 + b"final-1"   # duplicado real de grande_1

    # Grupo duplicado 1: 3 copias del mismo contenido en carpetas distintas
    escribir("originales/doc.txt", contenido_a)
    escribir("copias/doc (1).txt", contenido_a)
    escribir("backup/sub/doc.txt", contenido_a)

    # Grupo duplicado 2: 2 copias de otro contenido
    escribir("fotos/img.dat", contenido_b)
    escribir("fotos/respaldo/img.dat", contenido_b)

    # Trampa: mismo tamaño que contenido_b pero distinto contenido -> NO dup
    escribir("fotos/casi.dat", b"z" * len(contenido_b))

    # Archivos grandes: grande_1 y grande_3 son duplicados; grande_2 no.
    escribir("grandes/a.bin", grande_1)
    escribir("grandes/b.bin", grande_2)
    escribir("grandes/c.bin", grande_3)

    # Trampa: dos archivos vacíos (mismo contenido: ninguno) -> SÍ son dup
    escribir("vacios/uno.txt", b"")
    escribir("vacios/dos.txt", b"")

    # Archivo único sin pareja
    escribir("solo/unico.txt", b"nadie mas tiene esto\n")


def comparar_carpeta(carpeta, orig, etiqueta):
    print(f"\n=== Comparando: {etiqueta} ===")
    print(f"    Ruta: {carpeta}")

    nuevos, resultado = grupos_nucleo_nuevo(carpeta)
    viejos = grupos_script_original(carpeta, orig)

    print(f"    Núcleo nuevo:    {len(nuevos)} grupos, "
          f"{resultado.total_archivos_duplicados} archivos duplicados, "
          f"recuperable {resultado.espacio_recuperable_total} bytes")
    print(f"    Script original: {len(viejos)} grupos")

    if resultado.errores:
        print(f"    (avisos de lectura: {len(resultado.errores)})")

    if nuevos == viejos:
        print("    RESULTADO: IDENTICO  [OK]")
        return True

    print("    RESULTADO: DIFERENCIAS  [FALLA]")
    solo_nuevo = nuevos - viejos
    solo_viejo = viejos - nuevos
    for g in solo_nuevo:
        print("      + solo lo detecta el núcleo nuevo:")
        for r in sorted(g):
            print(f"          {r}")
    for g in solo_viejo:
        print("      - solo lo detecta el script original:")
        for r in sorted(g):
            print(f"          {r}")
    return False


def main():
    orig = _cargar_script_original()
    ok = True

    with tempfile.TemporaryDirectory(prefix="dup_prueba_") as tmp:
        base = Path(tmp) / "arbol"
        construir_arbol_de_prueba(base)
        ok &= comparar_carpeta(str(base), orig, "árbol sintético")

    for ruta_real in sys.argv[1:]:
        if os.path.isdir(ruta_real):
            ok &= comparar_carpeta(ruta_real, orig, "carpeta real")
        else:
            print(f"\n[AVISO] No es una carpeta, se ignora: {ruta_real}")

    print()
    if ok:
        print("TODO OK: el núcleo nuevo agrupa los duplicados igual que el original.")
        sys.exit(0)
    else:
        print("HAY DIFERENCIAS: revisar arriba.")
        sys.exit(1)


if __name__ == "__main__":
    main()
