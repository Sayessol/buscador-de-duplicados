"""Pruebas de la pestaña "Reunir imágenes" (core/reunir.py):

  * listar imágenes: solo primer nivel vs recursivo,
  * el diálogo por tipo de archivo: dejar / mover / agrupar,
  * "Por archivos" preserva subcarpetas, con mover y con copiar,
  * "Carpeta entera" mueve/copia la carpeta completa,
  * colisiones de nombre -> sufijo (1),
  * destino dentro del origen -> se rechaza.

    python pruebas/probar_reunir.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.mover import DestinoInvalido, MOVER, COPIAR                  # noqa: E402
from core.reunir import (                                             # noqa: E402
    listar, tipos_no_imagen, ReglasNoImagen, planear_por_archivos,
    reunir_por_archivos, reunir_carpeta_entera, validar_destino,
)

fallos = []


def check(cond, msg):
    print(f"  [{'OK  ' if cond else 'FALLA'}] {msg}")
    if not cond:
        fallos.append(msg)


def construir(raiz: Path):
    (raiz / "vacaciones").mkdir(parents=True)
    (raiz / "2024" / "bodas").mkdir(parents=True)
    (raiz / "vacaciones" / "playa.jpg").write_bytes(b"img1")
    (raiz / "vacaciones" / "montana.png").write_bytes(b"img2")
    (raiz / "2024" / "retrato.jpg").write_bytes(b"img3")
    (raiz / "2024" / "bodas" / "grupo.jpeg").write_bytes(b"img4")
    (raiz / "portada.png").write_bytes(b"img5")            # primer nivel
    # no imágenes
    (raiz / "notas.txt").write_bytes(b"texto")
    (raiz / "vacaciones" / "info.pdf").write_bytes(b"pdf")
    (raiz / "2024" / "gastos.pdf").write_bytes(b"pdf2")
    (raiz / "2024" / "musica.mp3").write_bytes(b"mp3")


def _rel(rutas, base):
    return sorted(str(Path(r).relative_to(base)).replace("\\", "/") for r in rutas)


def main():
    # ---- listar ---------------------------------------------------
    with tempfile.TemporaryDirectory() as tmp:
        raiz = Path(tmp) / "Fotos"
        construir(raiz)

        img_r, otros_r = listar(str(raiz), recursivo=True)
        check(_rel(img_r, raiz) == ["2024/bodas/grupo.jpeg", "2024/retrato.jpg",
                                    "portada.png", "vacaciones/montana.png",
                                    "vacaciones/playa.jpg"],
              "recursivo lista las 5 imágenes de todos los niveles")
        check(_rel(otros_r, raiz) == ["2024/gastos.pdf", "2024/musica.mp3",
                                      "notas.txt", "vacaciones/info.pdf"],
              "recursivo lista los 4 no-imagen")

        img_n, otros_n = listar(str(raiz), recursivo=False)
        check(_rel(img_n, raiz) == ["portada.png"],
              "primer nivel: solo portada.png")
        check(_rel(otros_n, raiz) == ["notas.txt"],
              "primer nivel: solo notas.txt")

        tipos = tipos_no_imagen(otros_r)
        check(set(tipos) == {"pdf", "mp3", "txt"} and len(tipos["pdf"]) == 2,
              "tipos_no_imagen agrupa por extensión (pdf x2, mp3, txt)")

    # ---- planear_por_archivos con reglas -------------------------
    with tempfile.TemporaryDirectory() as tmp:
        raiz = Path(tmp) / "Fotos"
        construir(raiz)
        destino = Path(tmp) / "Reunidas"
        img, otros = listar(str(raiz), recursivo=True)

        reglas = ReglasNoImagen(
            accion_por_ext={"pdf": "agrupar", "mp3": "mover", "txt": "dejar"},
            carpeta_por_ext={"pdf": "Documentos"})
        plan = planear_por_archivos(img, otros, str(raiz), str(destino), reglas)
        destinos = _rel([t.destino for t in plan], destino)
        print("  destinos planeados:", destinos)
        check("vacaciones/playa.jpg" in destinos,
              "imagen -> destino/<misma subruta>")
        check("Documentos/vacaciones/info.pdf" in destinos
              and "Documentos/2024/gastos.pdf" in destinos,
              "pdf 'agrupar' -> destino/Documentos/<subruta>")
        check("2024/musica.mp3" in destinos,
              "mp3 'mover' -> destino/<subruta> (sin agrupar)")
        check(not any("notas.txt" in d for d in destinos),
              "txt 'dejar' -> no se planea")

    # ---- reunir_por_archivos: MOVER ------------------------------
    with tempfile.TemporaryDirectory() as tmp:
        raiz = Path(tmp) / "Fotos"
        construir(raiz)
        destino = Path(tmp) / "Reunidas"
        img, otros = listar(str(raiz), recursivo=True)
        res = reunir_por_archivos(img, otros, str(raiz), str(destino),
                                  accion=MOVER, reglas=ReglasNoImagen())
        check(len(res.hechos) == 5 and not res.fallidos,
              "mover: se trasladan las 5 imágenes, ningún fallo")
        check((destino / "vacaciones" / "playa.jpg").exists()
              and not (raiz / "vacaciones" / "playa.jpg").exists(),
              "la imagen está en el destino y ya no en el origen")
        check((raiz / "vacaciones" / "info.pdf").exists(),
              "el pdf ('dejar' por defecto) sigue en el origen")
        check((raiz / "vacaciones").is_dir() and (raiz / "2024" / "bodas").is_dir(),
              "las subcarpetas del origen NO se han movido")
        check(res.ruta_log and Path(res.ruta_log).exists(),
              "se escribe el CSV de registro")

    # ---- reunir_por_archivos: COPIAR ----------------------------
    with tempfile.TemporaryDirectory() as tmp:
        raiz = Path(tmp) / "Fotos"
        construir(raiz)
        destino = Path(tmp) / "Reunidas"
        img, otros = listar(str(raiz), recursivo=True)
        res = reunir_por_archivos(img, otros, str(raiz), str(destino),
                                  accion=COPIAR)
        check(len(res.hechos) == 5, "copiar: 5 traslados")
        check((destino / "portada.png").exists()
              and (raiz / "portada.png").exists(),
              "copiar deja el original intacto")

    # ---- colisión de nombres -----------------------------------
    with tempfile.TemporaryDirectory() as tmp:
        raiz = Path(tmp) / "Fotos"
        (raiz / "a").mkdir(parents=True)
        (raiz / "b").mkdir(parents=True)
        (raiz / "a" / "foto.jpg").write_bytes(b"A")
        (raiz / "b" / "foto.jpg").write_bytes(b"B")
        destino = Path(tmp) / "Reunidas"
        # aplanamos a propósito con reglas raras: usamos relpath normal,
        # pero forzamos colisión moviendo ambas al mismo sitio.
        from core.mover import Traslado, ejecutar
        plan = [Traslado(str(raiz / "a" / "foto.jpg"), str(destino / "foto.jpg")),
                Traslado(str(raiz / "b" / "foto.jpg"), str(destino / "foto.jpg"))]
        ejecutar(plan, accion=MOVER)
        check((destino / "foto.jpg").exists() and (destino / "foto (1).jpg").exists(),
              "la segunda colisión se guarda como 'foto (1).jpg', sin pisar")

    # ---- carpeta entera --------------------------------------
    with tempfile.TemporaryDirectory() as tmp:
        raiz = Path(tmp) / "AlbumViaje"
        construir(raiz)
        destino = Path(tmp) / "Destino"
        res = reunir_carpeta_entera(str(raiz), str(destino), accion=MOVER)
        check(res.hechos and (destino / "AlbumViaje" / "vacaciones" / "playa.jpg").exists(),
              "carpeta entera: destino/AlbumViaje/... con todo dentro")
        check((destino / "AlbumViaje" / "notas.txt").exists(),
              "carpeta entera incluye los no-imagen")
        check(not raiz.exists(), "mover: la carpeta original ya no está")

    # ---- destino inválido -----------------------------------
    with tempfile.TemporaryDirectory() as tmp:
        raiz = Path(tmp) / "Fotos"
        raiz.mkdir()
        try:
            validar_destino(str(raiz / "sub"), str(raiz))
            check(False, "destino dentro del origen debe lanzar DestinoInvalido")
        except DestinoInvalido:
            check(True, "destino dentro del origen -> DestinoInvalido")

    print()
    if fallos:
        print(f"FALLARON {len(fallos)} comprobaciones.")
        sys.exit(1)
    print("REUNIR OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
