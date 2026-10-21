"""Prueba real de mover a cuarentena: crea un árbol, mueve de verdad los
duplicados marcados y comprueba que:

  * los archivos "conservar" siguen en su sitio,
  * los "mover" ya no están en el origen y sí en la cuarentena,
  * se preserva la estructura de subcarpetas,
  * se escribe el CSV de log,
  * se rechazan las situaciones inválidas (grupos sin resolver,
    cuarentena dentro de la carpeta escaneada),
  * los nombres que colisionan no se pisan.

    python pruebas/probar_cuarentena.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.scanner import escanear                                  # noqa: E402
from core.seleccion import SeleccionDuplicados                      # noqa: E402
from core.quarantine import (                                       # noqa: E402
    mover_a_cuarentena, validar_carpeta_cuarentena, CuarentenaInvalida,
)

fallos = []


def check(cond, msg):
    print(f"  [{'OK  ' if cond else 'FALLA'}] {msg}")
    if not cond:
        fallos.append(msg)


def construir(base: Path):
    def escribir(rel, data: bytes):
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    a = b"contenido A\n" * 30
    b = b"contenido B distinto\n" * 20

    escribir("bueno/foto.jpg", a)          # conservar
    escribir("descargas/foto.jpg", a)      # mover
    escribir("descargas/sub/foto.jpg", a)  # mover (colisiona de nombre con el anterior)
    escribir("bueno/doc.txt", b)           # conservar
    escribir("viejo/doc.txt", b)           # mover


def main():
    with tempfile.TemporaryDirectory(prefix="dup_cuar_") as tmp:
        base = Path(tmp) / "escaneado"
        cuarentena = Path(tmp) / "CUARENTENA"
        construir(base)

        r = escanear(str(base))
        sel = SeleccionDuplicados(r)

        # --- validaciones que deben fallar --------------------------
        try:
            mover_a_cuarentena(sel, str(base), str(cuarentena))
            check(False, "mover con grupos sin resolver debe lanzar ValueError")
        except ValueError:
            check(True, "mover con grupos sin resolver lanza ValueError")

        try:
            validar_carpeta_cuarentena(str(base / "sub"), str(base))
            check(False, "cuarentena dentro de la carpeta escaneada debe fallar")
        except CuarentenaInvalida:
            check(True, "cuarentena dentro de la carpeta escaneada lanza CuarentenaInvalida")

        # --- resolver con la regla de carpeta preferida -------------
        resueltos, sin_c = sel.aplicar_regla_carpeta(str(base / "bueno"))
        check(resueltos == 2 and sin_c == 0, "la regla resuelve los 2 grupos")
        check(sel.todo_listo(), "todo listo para mover")

        esperado_mover = sel.cantidad_a_mover()
        bytes_esperados = sel.espacio_a_liberar()

        # Forzar una colisión: ya hay un archivo en el destino de descargas/foto.jpg
        (cuarentena / "descargas").mkdir(parents=True, exist_ok=True)
        (cuarentena / "descargas" / "foto.jpg").write_bytes(b"otro archivo distinto")

        # --- mover de verdad ---------------------------------------
        res = mover_a_cuarentena(sel, str(base), str(cuarentena))

        check(len(res.movidos) == esperado_mover,
              f"se movieron {esperado_mover} archivos")
        check(len(res.fallidos) == 0, "ningún movimiento falló")
        check(res.bytes_movidos == bytes_esperados, "bytes movidos correctos")

        # conservar: siguen en su sitio
        check((base / "bueno" / "foto.jpg").exists(), "la copia buena de foto.jpg sigue")
        check((base / "bueno" / "doc.txt").exists(), "la copia buena de doc.txt sigue")

        # mover: ya no están en el origen
        check(not (base / "descargas" / "foto.jpg").exists(),
              "descargas/foto.jpg salió del origen")
        check(not (base / "viejo" / "doc.txt").exists(),
              "viejo/doc.txt salió del origen")

        # mover: están en la cuarentena con la estructura preservada
        check((cuarentena / "viejo" / "doc.txt").exists(),
              "viejo/doc.txt está en la cuarentena con su ruta")
        check((cuarentena / "descargas" / "sub" / "foto.jpg").exists(),
              "descargas/sub/foto.jpg está en la cuarentena con su ruta")
        check((cuarentena / "descargas" / "foto (1).jpg").exists(),
              "la colisión con un archivo existente se resolvió como 'foto (1).jpg'")
        check((cuarentena / "descargas" / "foto.jpg").read_bytes() == b"otro archivo distinto",
              "el archivo que ya estaba en la cuarentena NO se pisó")

        # log CSV
        check(res.ruta_log and Path(res.ruta_log).exists(), "se escribió el CSV de log")
        if res.ruta_log:
            contenido = Path(res.ruta_log).read_text(encoding="utf-8-sig")
            check("movido" in contenido and "Origen" in contenido,
                  "el CSV de log tiene encabezado y filas 'movido'")

        # nada se borró: quedan 2 en el origen y se movieron 3 (+ el señuelo previo)
        n_orig = sum(1 for _ in base.rglob("*") if _.is_file())
        n_cuar = sum(1 for _ in cuarentena.rglob("*")
                     if _.is_file() and not _.name.endswith(".csv"))
        check(n_orig == 2, "quedan 2 archivos en la carpeta escaneada")
        check(n_cuar == 4, "en la cuarentena hay 4 archivos (1 señuelo previo + 3 movidos)")

    print()
    if fallos:
        print(f"FALLARON {len(fallos)} comprobaciones.")
        sys.exit(1)
    print("TODA LA CUARENTENA OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
