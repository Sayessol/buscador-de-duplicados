"""Pruebas del historial de operaciones y del "deshacer" (core/historial.py).

  * registrar y listar (más reciente primero),
  * deshacer un MOVER -> los archivos vuelven a su sitio,
  * deshacer un COPIAR -> se borran las copias del destino,
  * deshacer conflictivo (ya hay algo en el origen) -> reporta el fallo,
  * una operación ya deshecha no se deshace dos veces.

No toca el historial real: redirige %APPDATA% a una carpeta temporal.

    python pruebas/probar_historial.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

fallos = []


def check(cond, msg):
    print(f"  [{'OK  ' if cond else 'FALLA'}] {msg}")
    if not cond:
        fallos.append(msg)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        import os
        os.environ["APPDATA"] = str(tmp / "appdata")

        # importar DESPUÉS de fijar APPDATA
        from core import historial
        from core.mover import ejecutar, Traslado, MOVER, COPIAR

        # --- montar un caso: mover 2 archivos a un destino ----------
        origen = tmp / "origen" / "sub"
        origen.mkdir(parents=True)
        destino = tmp / "destino"
        (origen / "a.txt").write_text("aaa")
        (origen / "b.txt").write_text("bbb")

        plan = [Traslado(str(origen / "a.txt"), str(destino / "sub" / "a.txt")),
                Traslado(str(origen / "b.txt"), str(destino / "sub" / "b.txt"))]
        res = ejecutar(plan, accion=MOVER)
        op_id = historial.registrar(
            historial.TIPO_REUNIR, "mover", str(tmp / "origen"), str(destino),
            [(t.origen, t.destino) for t in res.hechos], "2 archivos de prueba")

        ops = historial.listar()
        check(len(ops) == 1 and ops[0]["id"] == op_id, "la operación queda registrada")
        check(ops[0]["deshecha"] is False, "arranca como no deshecha")
        check(not (origen / "a.txt").exists()
              and (destino / "sub" / "a.txt").exists(),
              "tras mover: los archivos están en el destino")

        # --- deshacer el MOVER ------------------------------------
        r = historial.deshacer(op_id)
        check(r["ok"] == 2 and not r["fallos"], "deshacer mover: 2 revertidos")
        check((origen / "a.txt").exists() and (origen / "b.txt").exists()
              and not (destino / "sub" / "a.txt").exists(),
              "los archivos han vuelto a su carpeta original")
        check(historial.listar()[0]["deshecha"] is True,
              "la operación queda marcada como deshecha")

        r2 = historial.deshacer(op_id)
        check(r2["ok"] == 0 and r2["fallos"], "no se puede deshacer dos veces")

        # --- COPIAR y deshacer (borra las copias) ----------------
        plan_c = [Traslado(str(origen / "a.txt"), str(destino / "c" / "a.txt"))]
        rc = ejecutar(plan_c, accion=COPIAR)
        op_c = historial.registrar(
            historial.TIPO_REUNIR, "copiar", str(tmp / "origen"), str(destino),
            [(t.origen, t.destino) for t in rc.hechos])
        check((destino / "c" / "a.txt").exists() and (origen / "a.txt").exists(),
              "copiar: original y copia existen")
        rd = historial.deshacer(op_c)
        check(rd["ok"] == 1 and not (destino / "c" / "a.txt").exists()
              and (origen / "a.txt").exists(),
              "deshacer copia: se borra la copia, el original sigue")

        # --- deshacer con conflicto -----------------------------
        (origen / "x.txt").write_text("x")
        plan_x = [Traslado(str(origen / "x.txt"), str(destino / "x.txt"))]
        rx = ejecutar(plan_x, accion=MOVER)
        op_x = historial.registrar(
            historial.TIPO_REUNIR, "mover", str(tmp / "origen"), str(destino),
            [(t.origen, t.destino) for t in rx.hechos])
        (origen / "x.txt").write_text("otra cosa")  # ocupamos la ruta original
        rr = historial.deshacer(op_x)
        check(rr["ok"] == 0 and rr["fallos"],
              "deshacer con la ruta original ocupada -> reporta fallo, no pisa")
        check((origen / "x.txt").read_text() == "otra cosa",
              "el archivo que ocupaba la ruta original no se ha tocado")

    print()
    if fallos:
        print(f"FALLARON {len(fallos)} comprobaciones.")
        sys.exit(1)
    print("HISTORIAL OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
