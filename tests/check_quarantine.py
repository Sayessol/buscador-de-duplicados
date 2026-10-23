"""Real test of moving to quarantine: creates a tree, really moves the marked
duplicates and checks that:

  * the "keep" files stay in their place,
  * the "move" ones are no longer in the source and are in the quarantine,
  * the subfolder structure is preserved,
  * the CSV log is written,
  * invalid situations are rejected (unresolved groups,
    quarantine inside the scanned folder),
  * names that collide are not overwritten.

    python tests/check_quarantine.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.scanner import scan                                  # noqa: E402
from core.selection import DuplicateSelection                      # noqa: E402
from core.quarantine import (                                       # noqa: E402
    move_to_quarantine, validate_quarantine_folder, InvalidQuarantine,
)

failures = []


def check(cond, msg):
    print(f"  [{'OK  ' if cond else 'FALLA'}] {msg}")
    if not cond:
        failures.append(msg)


def build(base: Path):
    def write(rel, data: bytes):
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    a = b"contenido A\n" * 30
    b = b"contenido B distinto\n" * 20

    write("bueno/foto.jpg", a)          # keep
    write("descargas/foto.jpg", a)      # move
    write("descargas/sub/foto.jpg", a)  # move (its name collides with the previous one)
    write("bueno/doc.txt", b)           # keep
    write("viejo/doc.txt", b)           # move


def main():
    with tempfile.TemporaryDirectory(prefix="dup_cuar_") as tmp:
        base = Path(tmp) / "escaneado"
        quarantine = Path(tmp) / "CUARENTENA"
        build(base)

        r = scan(str(base))
        sel = DuplicateSelection(r)

        # --- validations that must fail --------------------------
        try:
            move_to_quarantine(sel, str(base), str(quarantine))
            check(False, "mover con grupos sin resolver debe lanzar ValueError")
        except ValueError:
            check(True, "mover con grupos sin resolver lanza ValueError")

        try:
            validate_quarantine_folder(str(base / "sub"), str(base))
            check(False, "cuarentena dentro de la carpeta escaneada debe fallar")
        except InvalidQuarantine:
            check(True, "cuarentena dentro de la carpeta escaneada lanza InvalidQuarantine")

        # --- resolve with the preferred-folder rule -------------
        resolved, without_c = sel.apply_folder_rule(str(base / "bueno"))
        check(resolved == 2 and without_c == 0, "la regla resuelve los 2 grupos")
        check(sel.all_ready(), "todo listo para mover")

        expected_to_move = sel.count_to_move()
        bytes_expected = sel.space_to_free()

        # Force a collision: there is already a file at the destination of descargas/foto.jpg
        (quarantine / "descargas").mkdir(parents=True, exist_ok=True)
        (quarantine / "descargas" / "foto.jpg").write_bytes(b"otro archivo distinto")

        # --- really move ---------------------------------------
        res = move_to_quarantine(sel, str(base), str(quarantine))

        check(len(res.moved) == expected_to_move,
              f"se movieron {expected_to_move} archivos")
        check(len(res.failed) == 0, "ningún movimiento falló")
        check(res.bytes_moved == bytes_expected, "bytes movidos correctos")

        # keep: they stay in their place
        check((base / "bueno" / "foto.jpg").exists(), "la copia buena de foto.jpg sigue")
        check((base / "bueno" / "doc.txt").exists(), "la copia buena de doc.txt sigue")

        # move: they are no longer in the source
        check(not (base / "descargas" / "foto.jpg").exists(),
              "descargas/foto.jpg salió del origen")
        check(not (base / "viejo" / "doc.txt").exists(),
              "viejo/doc.txt salió del origen")

        # move: they are in the quarantine with the structure preserved
        check((quarantine / "viejo" / "doc.txt").exists(),
              "viejo/doc.txt está en la cuarentena con su ruta")
        check((quarantine / "descargas" / "sub" / "foto.jpg").exists(),
              "descargas/sub/foto.jpg está en la cuarentena con su ruta")
        check((quarantine / "descargas" / "foto (1).jpg").exists(),
              "la colisión con un archivo existente se resolvió como 'foto (1).jpg'")
        check((quarantine / "descargas" / "foto.jpg").read_bytes() == b"otro archivo distinto",
              "el archivo que ya estaba en la cuarentena NO se pisó")

        # CSV log
        check(res.log_path and Path(res.log_path).exists(), "se escribió el CSV de log")
        if res.log_path:
            content = Path(res.log_path).read_text(encoding="utf-8-sig")
            check("moved" in content and "Source" in content,
                  "el CSV de log tiene encabezado y filas 'movido'")

        # nothing was deleted: 2 remain in the source and 3 were moved (+ the earlier decoy)
        n_orig = sum(1 for _ in base.rglob("*") if _.is_file())
        n_quar = sum(1 for _ in quarantine.rglob("*")
                     if _.is_file() and not _.name.endswith(".csv"))
        check(n_orig == 2, "quedan 2 archivos en la carpeta escaneada")
        check(n_quar == 4, "en la cuarentena hay 4 archivos (1 señuelo previo + 3 movidos)")

    print()
    if failures:
        print(f"FALLARON {len(failures)} comprobaciones.")
        sys.exit(1)
    print("TODA LA CUARENTENA OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
