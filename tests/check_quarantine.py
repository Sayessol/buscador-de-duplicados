"""Prueba real de mover a cuarentena: crea un árbol, mueve de verdad los
duplicados marcados y comprueba que:

  * los archivos "conservar" siguen en su sitio,
  * los "mover" ya no están en el origen y sí en la cuarentena,
  * se preserva la estructura de subcarpetas,
  * se escribe el CSV de log,
  * se rechazan las situaciones inválidas (grupos sin resolver,
    cuarentena dentro de la carpeta escaneada),
  * los nombres que colisionan no se pisan.

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

    write("bueno/foto.jpg", a)          # conservar
    write("descargas/foto.jpg", a)      # mover
    write("descargas/sub/foto.jpg", a)  # mover (colisiona de nombre con el anterior)
    write("bueno/doc.txt", b)           # conservar
    write("viejo/doc.txt", b)           # mover


def main():
    with tempfile.TemporaryDirectory(prefix="dup_cuar_") as tmp:
        base = Path(tmp) / "escaneado"
        quarantine = Path(tmp) / "CUARENTENA"
        build(base)

        r = scan(str(base))
        sel = DuplicateSelection(r)

        # --- validaciones que deben fallar --------------------------
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

        # --- resolver con la regla de carpeta preferida -------------
        resolved, without_c = sel.apply_folder_rule(str(base / "bueno"))
        check(resolved == 2 and without_c == 0, "la regla resuelve los 2 grupos")
        check(sel.all_ready(), "todo listo para mover")

        expected_to_move = sel.count_to_move()
        bytes_expected = sel.space_to_free()

        # Forzar una colisión: ya hay un archivo en el destino de descargas/foto.jpg
        (quarantine / "descargas").mkdir(parents=True, exist_ok=True)
        (quarantine / "descargas" / "foto.jpg").write_bytes(b"otro archivo distinto")

        # --- mover de verdad ---------------------------------------
        res = move_to_quarantine(sel, str(base), str(quarantine))

        check(len(res.moved) == expected_to_move,
              f"se movieron {expected_to_move} archivos")
        check(len(res.failed) == 0, "ningún movimiento falló")
        check(res.bytes_moved == bytes_expected, "bytes movidos correctos")

        # conservar: siguen en su sitio
        check((base / "bueno" / "foto.jpg").exists(), "la copia buena de foto.jpg sigue")
        check((base / "bueno" / "doc.txt").exists(), "la copia buena de doc.txt sigue")

        # mover: ya no están en el origen
        check(not (base / "descargas" / "foto.jpg").exists(),
              "descargas/foto.jpg salió del origen")
        check(not (base / "viejo" / "doc.txt").exists(),
              "viejo/doc.txt salió del origen")

        # mover: están en la cuarentena con la estructura preservada
        check((quarantine / "viejo" / "doc.txt").exists(),
              "viejo/doc.txt está en la cuarentena con su ruta")
        check((quarantine / "descargas" / "sub" / "foto.jpg").exists(),
              "descargas/sub/foto.jpg está en la cuarentena con su ruta")
        check((quarantine / "descargas" / "foto (1).jpg").exists(),
              "la colisión con un archivo existente se resolvió como 'foto (1).jpg'")
        check((quarantine / "descargas" / "foto.jpg").read_bytes() == b"otro archivo distinto",
              "el archivo que ya estaba en la cuarentena NO se pisó")

        # log CSV
        check(res.log_path and Path(res.log_path).exists(), "se escribió el CSV de log")
        if res.log_path:
            content = Path(res.log_path).read_text(encoding="utf-8-sig")
            check("movido" in content and "Origen" in content,
                  "el CSV de log tiene encabezado y filas 'movido'")

        # nada se borró: quedan 2 en el origen y se movieron 3 (+ el señuelo previo)
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
