"""Pruebas del historial de operaciones y del "deshacer" (core/history.py).

  * registrar y listar (más reciente primero),
  * deshacer un MOVER -> los archivos vuelven a su sitio,
  * deshacer un COPIAR -> se borran las copias del destino,
  * deshacer conflictivo (ya hay algo en el origen) -> reporta el fallo,
  * una operación ya deshecha no se deshace dos veces.

No toca el historial real: redirige %APPDATA% a una carpeta temporal.

    python tests/check_history.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

failures = []


def check(cond, msg):
    print(f"  [{'OK  ' if cond else 'FALLA'}] {msg}")
    if not cond:
        failures.append(msg)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        import os
        os.environ["APPDATA"] = str(tmp / "appdata")

        # importar DESPUÉS de fijar APPDATA
        from core import history
        from core.file_moves import execute, Transfer, MOVE, COPY

        # --- montar un caso: mover 2 archivos a un destino ----------
        source = tmp / "origen" / "sub"
        source.mkdir(parents=True)
        destination = tmp / "destino"
        (source / "a.txt").write_text("aaa")
        (source / "b.txt").write_text("bbb")

        plan = [Transfer(str(source / "a.txt"), str(destination / "sub" / "a.txt")),
                Transfer(str(source / "b.txt"), str(destination / "sub" / "b.txt"))]
        res = execute(plan, action=MOVE)
        op_id = history.record(
            history.KIND_GATHER, "mover", str(tmp / "origen"), str(destination),
            [(t.source, t.destination) for t in res.done], "2 archivos de prueba")

        ops = history.list_all()
        check(len(ops) == 1 and ops[0]["id"] == op_id, "la operación queda registrada")
        check(ops[0]["deshecha"] is False, "arranca como no deshecha")
        check(not (source / "a.txt").exists()
              and (destination / "sub" / "a.txt").exists(),
              "tras mover: los archivos están en el destino")

        # --- deshacer el MOVER ------------------------------------
        r = history.undo(op_id)
        check(r["ok"] == 2 and not r["fallos"], "deshacer mover: 2 revertidos")
        check((source / "a.txt").exists() and (source / "b.txt").exists()
              and not (destination / "sub" / "a.txt").exists(),
              "los archivos han vuelto a su carpeta original")
        check(history.list_all()[0]["deshecha"] is True,
              "la operación queda marcada como deshecha")

        r2 = history.undo(op_id)
        check(r2["ok"] == 0 and r2["fallos"], "no se puede deshacer dos veces")

        # --- COPIAR y deshacer (borra las copias) ----------------
        plan_c = [Transfer(str(source / "a.txt"), str(destination / "c" / "a.txt"))]
        rc = execute(plan_c, action=COPY)
        op_c = history.record(
            history.KIND_GATHER, "copiar", str(tmp / "origen"), str(destination),
            [(t.source, t.destination) for t in rc.done])
        check((destination / "c" / "a.txt").exists() and (source / "a.txt").exists(),
              "copiar: original y copia existen")
        rd = history.undo(op_c)
        check(rd["ok"] == 1 and not (destination / "c" / "a.txt").exists()
              and (source / "a.txt").exists(),
              "deshacer copia: se borra la copia, el original sigue")

        # --- deshacer con conflicto -----------------------------
        (source / "x.txt").write_text("x")
        plan_x = [Transfer(str(source / "x.txt"), str(destination / "x.txt"))]
        rx = execute(plan_x, action=MOVE)
        op_x = history.record(
            history.KIND_GATHER, "mover", str(tmp / "origen"), str(destination),
            [(t.source, t.destination) for t in rx.done])
        (source / "x.txt").write_text("otra cosa")  # ocupamos la ruta original
        rr = history.undo(op_x)
        check(rr["ok"] == 0 and rr["fallos"],
              "deshacer con la ruta original ocupada -> reporta fallo, no pisa")
        check((source / "x.txt").read_text() == "otra cosa",
              "el archivo que ocupaba la ruta original no se ha tocado")

    print()
    if failures:
        print(f"FALLARON {len(failures)} comprobaciones.")
        sys.exit(1)
    print("HISTORIAL OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
