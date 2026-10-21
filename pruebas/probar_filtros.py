"""Prueba del filtro de escaneo (exclusión por extensión, nombre, carpeta
y tamaño mínimo) y del desglose por extensión.

    python pruebas/probar_filtros.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.scanner import escanear                       # noqa: E402
from core.filtros import FiltroEscaneo, CATEGORIAS_EXTENSIONES  # noqa: E402

fallos = []


def check(cond, msg):
    estado = "OK  " if cond else "FALLA"
    print(f"  [{estado}] {msg}")
    if not cond:
        fallos.append(msg)


def construir(base: Path):
    def escribir(rel, data: bytes):
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    doc = b"contenido de documento\n" * 20
    tmpdata = b"basura temporal\n" * 20
    imgdata = b"pixeles\n" * 50

    # Grupo real de .txt (debe sobrevivir a todos los filtros salvo si se excluye .txt)
    escribir("a/doc.txt", doc)
    escribir("b/doc.txt", doc)

    # Grupo de .tmp (se excluye por extensión en el filtro por defecto)
    escribir("a/cache.tmp", tmpdata)
    escribir("b/otra.tmp", tmpdata)

    # Grupo dentro de node_modules (se excluye por carpeta)
    escribir("proj/node_modules/x.txt", imgdata)
    escribir("proj/node_modules/y.txt", imgdata)
    escribir("proj/src/z.txt", imgdata)   # copia fuera de node_modules -> queda sin pareja

    # Thumbs.db duplicado (se excluye por nombre)
    escribir("a/Thumbs.db", b"thumbs\n")
    escribir("b/Thumbs.db", b"thumbs\n")

    # Dos archivos vacíos (se excluyen con tamano_minimo=1)
    escribir("a/vacio.txt", b"")
    escribir("b/vacio.txt", b"")

    # Grupo de fotos (.jpg) y grupo de audio (.mp3), para la lista blanca
    fotodata = b"binario de foto\n" * 15
    audiodata = b"binario de audio\n" * 15
    escribir("fotos/img1.jpg", fotodata)
    escribir("fotos/img2.jpg", fotodata)
    escribir("musica/cancion1.mp3", audiodata)
    escribir("musica/cancion2.mp3", audiodata)


def rutas_por_grupo(resultado):
    return sorted(
        sorted(Path(a.ruta).name for a in g.archivos)
        for g in resultado.grupos
    )


def main():
    with tempfile.TemporaryDirectory(prefix="dup_filtro_") as tmp:
        base = Path(tmp) / "arbol"
        construir(base)

        print("\n--- Sin filtro ---")
        r0 = escanear(str(base))
        g0 = rutas_por_grupo(r0)
        print("  grupos:", g0)
        check(len(r0.grupos) == 7,
              "sin filtro detecta 7 grupos (txt, tmp, node_modules, Thumbs.db, "
              "vacios, jpg, mp3)")
        check(r0.total_excluidos == 0, "sin filtro no excluye nada")

        print("\n--- Filtro por defecto ---")
        r1 = escanear(str(base), filtro=FiltroEscaneo.por_defecto())
        g1 = rutas_por_grupo(r1)
        print("  grupos:", g1)
        check(g1 == [["cancion1.mp3", "cancion2.mp3"], ["doc.txt", "doc.txt"],
                     ["img1.jpg", "img2.jpg"]],
              "filtro por defecto deja doc.txt, las fotos y el audio "
              "(la basura típica no incluye jpg/mp3)")
        check(r1.total_excluidos > 0, "filtro por defecto reporta archivos excluidos")

        print("\n--- Filtro: excluir .txt ---")
        f2 = FiltroEscaneo(extensiones_excluidas={"txt"})
        r2 = escanear(str(base), filtro=f2)
        exts = {e for e, _c, _b in r2.resumen_por_extension()}
        print("  extensiones en resultado:", exts)
        check("txt" not in exts, "excluir .txt quita todos los .txt del resultado")

        print("\n--- Lista blanca: buscar solo imágenes ---")
        f3 = FiltroEscaneo(extensiones_incluidas=CATEGORIAS_EXTENSIONES["Imágenes"])
        r3 = escanear(str(base), filtro=f3)
        g3 = rutas_por_grupo(r3)
        print("  grupos:", g3)
        check(g3 == [["img1.jpg", "img2.jpg"]],
              "'solo imágenes' deja únicamente el grupo de fotos")
        check(r3.total_excluidos > 0,
              "'solo imágenes' reporta como excluido todo lo que no es imagen")

        print("\n--- Lista blanca: imágenes + audio ---")
        combinado = (CATEGORIAS_EXTENSIONES["Imágenes"]
                     | CATEGORIAS_EXTENSIONES["Audio"])
        f4 = FiltroEscaneo(extensiones_incluidas=combinado)
        r4 = escanear(str(base), filtro=f4)
        g4 = rutas_por_grupo(r4)
        print("  grupos:", g4)
        check(g4 == [["cancion1.mp3", "cancion2.mp3"], ["img1.jpg", "img2.jpg"]],
              "combinar 'imágenes' + 'audio' deja fotos y música, nada más")

        print("\n--- Desglose por extensión (sin filtro) ---")
        for ext, c, b in r0.resumen_por_extension():
            print(f"    {ext:15} {c} archivos  {b} bytes")
        exts0 = {e for e, _c, _b in r0.resumen_por_extension()}
        check({"txt", "tmp", "db", "jpg", "mp3"} <= exts0,
              "el desglose lista txt, tmp, db, jpg y mp3")

    print()
    if fallos:
        print(f"FALLARON {len(fallos)} comprobaciones.")
        sys.exit(1)
    print("TODOS LOS FILTROS OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
