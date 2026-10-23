"""Tests of the "Gather images" tab (core/gather.py):

  * list images: first level only vs recursive,
  * the per-file-kind dialog: leave / move / group,
  * "By files" preserves subfolders, with move and with copy,
  * "Whole folder" moves/copies the complete folder,
  * name collisions -> suffix (1),
  * destination inside the source -> rejected.

    python tests/check_gather.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.file_moves import InvalidDestination, MOVE, COPY                  # noqa: E402
from core.gather import (                                             # noqa: E402
    list_all, non_image_kinds, NonImageRules, plan_by_files,
    gather_by_files, gather_whole_folder, validate_destination,
)

failures = []


def check(cond, msg):
    print(f"  [{'OK  ' if cond else 'FALLA'}] {msg}")
    if not cond:
        failures.append(msg)


def build(root: Path):
    (root / "vacaciones").mkdir(parents=True)
    (root / "2024" / "bodas").mkdir(parents=True)
    (root / "vacaciones" / "playa.jpg").write_bytes(b"img1")
    (root / "vacaciones" / "montana.png").write_bytes(b"img2")
    (root / "2024" / "retrato.jpg").write_bytes(b"img3")
    (root / "2024" / "bodas" / "grupo.jpeg").write_bytes(b"img4")
    (root / "portada.png").write_bytes(b"img5")            # first level
    # non-images
    (root / "notas.txt").write_bytes(b"texto")
    (root / "vacaciones" / "info.pdf").write_bytes(b"pdf")
    (root / "2024" / "gastos.pdf").write_bytes(b"pdf2")
    (root / "2024" / "musica.mp3").write_bytes(b"mp3")


def _rel(paths, base):
    return sorted(str(Path(r).relative_to(base)).replace("\\", "/") for r in paths)


def main():
    # ---- list -----------------------------------------------------
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "Fotos"
        build(root)

        img_r, others_r = list_all(str(root), recursive=True)
        check(_rel(img_r, root) == ["2024/bodas/grupo.jpeg", "2024/retrato.jpg",
                                    "portada.png", "vacaciones/montana.png",
                                    "vacaciones/playa.jpg"],
              "recursivo lista las 5 imágenes de todos los niveles")
        check(_rel(others_r, root) == ["2024/gastos.pdf", "2024/musica.mp3",
                                      "notas.txt", "vacaciones/info.pdf"],
              "recursivo lista los 4 no-imagen")

        img_n, others_n = list_all(str(root), recursive=False)
        check(_rel(img_n, root) == ["portada.png"],
              "primer nivel: solo portada.png")
        check(_rel(others_n, root) == ["notas.txt"],
              "primer nivel: solo notas.txt")

        kinds = non_image_kinds(others_r)
        check(set(kinds) == {"pdf", "mp3", "txt"} and len(kinds["pdf"]) == 2,
              "tipos_no_imagen agrupa por extensión (pdf x2, mp3, txt)")

    # ---- plan_by_files with rules -------------------------
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "Fotos"
        build(root)
        destination = Path(tmp) / "Reunidas"
        img, others = list_all(str(root), recursive=True)

        rules = NonImageRules(
            action_by_ext={"pdf": "agrupar", "mp3": "mover", "txt": "dejar"},
            folder_by_ext={"pdf": "Documentos"})
        plan = plan_by_files(img, others, str(root), str(destination), rules)
        destinations = _rel([t.destination for t in plan], destination)
        print("  destinos planeados:", destinations)
        check("vacaciones/playa.jpg" in destinations,
              "imagen -> destino/<misma subruta>")
        check("Documentos/vacaciones/info.pdf" in destinations
              and "Documentos/2024/gastos.pdf" in destinations,
              "pdf 'agrupar' -> destino/Documentos/<subruta>")
        check("2024/musica.mp3" in destinations,
              "mp3 'mover' -> destino/<subruta> (sin agrupar)")
        check(not any("notas.txt" in d for d in destinations),
              "txt 'dejar' -> no se planea")

    # ---- gather_by_files: MOVE ------------------------------
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "Fotos"
        build(root)
        destination = Path(tmp) / "Reunidas"
        img, others = list_all(str(root), recursive=True)
        res = gather_by_files(img, others, str(root), str(destination),
                                  action=MOVE, rules=NonImageRules())
        check(len(res.done) == 5 and not res.failed,
              "mover: se trasladan las 5 imágenes, ningún fallo")
        check((destination / "vacaciones" / "playa.jpg").exists()
              and not (root / "vacaciones" / "playa.jpg").exists(),
              "la imagen está en el destino y ya no en el origen")
        check((root / "vacaciones" / "info.pdf").exists(),
              "el pdf ('dejar' por defecto) sigue en el origen")
        check((root / "vacaciones").is_dir() and (root / "2024" / "bodas").is_dir(),
              "las subcarpetas del origen NO se han movido")
        check(res.log_path and Path(res.log_path).exists(),
              "se escribe el CSV de registro")

    # ---- gather_by_files: COPY ----------------------------
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "Fotos"
        build(root)
        destination = Path(tmp) / "Reunidas"
        img, others = list_all(str(root), recursive=True)
        res = gather_by_files(img, others, str(root), str(destination),
                                  action=COPY)
        check(len(res.done) == 5, "copiar: 5 traslados")
        check((destination / "portada.png").exists()
              and (root / "portada.png").exists(),
              "copiar deja el original intacto")

    # ---- name collision -----------------------------------
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "Fotos"
        (root / "a").mkdir(parents=True)
        (root / "b").mkdir(parents=True)
        (root / "a" / "foto.jpg").write_bytes(b"A")
        (root / "b" / "foto.jpg").write_bytes(b"B")
        destination = Path(tmp) / "Reunidas"
        # we flatten on purpose with odd rules: we use the normal relpath,
        # but force a collision by moving both to the same place.
        from core.file_moves import Transfer, execute
        plan = [Transfer(str(root / "a" / "foto.jpg"), str(destination / "foto.jpg")),
                Transfer(str(root / "b" / "foto.jpg"), str(destination / "foto.jpg"))]
        execute(plan, action=MOVE)
        check((destination / "foto.jpg").exists() and (destination / "foto (1).jpg").exists(),
              "la segunda colisión se guarda como 'foto (1).jpg', sin pisar")

    # ---- whole folder ----------------------------------------
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "AlbumViaje"
        build(root)
        destination = Path(tmp) / "Destino"
        res = gather_whole_folder(str(root), str(destination), action=MOVE)
        check(res.done and (destination / "AlbumViaje" / "vacaciones" / "playa.jpg").exists(),
              "carpeta entera: destino/AlbumViaje/... con todo dentro")
        check((destination / "AlbumViaje" / "notas.txt").exists(),
              "carpeta entera incluye los no-imagen")
        check(not root.exists(), "mover: la carpeta original ya no está")

    # ---- invalid destination -----------------------------------
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "Fotos"
        root.mkdir()
        try:
            validate_destination(str(root / "sub"), str(root))
            check(False, "destino dentro del origen debe lanzar InvalidDestination")
        except InvalidDestination:
            check(True, "destino dentro del origen -> InvalidDestination")

    print()
    if failures:
        print(f"FALLARON {len(failures)} comprobaciones.")
        sys.exit(1)
    print("REUNIR OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
