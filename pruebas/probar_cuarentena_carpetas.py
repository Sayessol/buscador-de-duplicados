"""Reproduce el caso que reportó el usuario: fotos repartidas en varias
subcarpetas dentro de una carpeta, movidas a una cuarentena externa.

Comprueba explícitamente que se MUEVEN LOS ARCHIVOS y NO LAS CARPETAS:

  * las subcarpetas del origen siguen existiendo después de mover,
  * en la cuarentena hay ARCHIVOS (no carpetas sueltas movidas enteras),
  * cada cosa movida es un archivo regular, nunca un directorio,
  * las copias marcadas para conservar no se tocan.

Prueba tanto el flujo de "Duplicados exactos" como el de "Fotos parecidas".

    python pruebas/probar_cuarentena_carpetas.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image                                          # noqa: E402

from core.scanner import escanear                              # noqa: E402
from core.seleccion import SeleccionDuplicados, CONSERVAR      # noqa: E402
from core.perceptual import analizar_carpeta                   # noqa: E402
from core.quarantine import mover_a_cuarentena, planear_movimientos  # noqa: E402

fallos = []


def check(cond, msg):
    print(f"  [{'OK  ' if cond else 'FALLA'}] {msg}")
    if not cond:
        fallos.append(msg)


def _foto(semilla, size=(600, 400)):
    import random
    rnd = random.Random(semilla)
    im = Image.new("RGB", size, (10, 10, 10))
    for _ in range(12):
        x0, y0 = rnd.randint(0, size[0]), rnd.randint(0, size[1])
        im.paste((rnd.randint(0, 255), rnd.randint(0, 255), rnd.randint(0, 255)),
                 (x0, y0, x0 + 120, y0 + 120))
    return im


def construir(raiz: Path):
    (raiz / "vacaciones").mkdir(parents=True)
    (raiz / "familia" / "recortes").mkdir(parents=True)
    (raiz / "descargas").mkdir(parents=True)

    _foto(1).save(raiz / "vacaciones" / "playa.png")
    _foto(2).save(raiz / "familia" / "retrato.png")
    _foto(3).save(raiz / "unica.png")

    # Grupo A EXACTO: mismos bytes en vacaciones y descargas
    bytes_a = (raiz / "vacaciones" / "playa.png").read_bytes()
    (raiz / "descargas" / "playa.png").write_bytes(bytes_a)
    # Grupo B EXACTO: mismos bytes en familia y familia/recortes
    bytes_b = (raiz / "familia" / "retrato.png").read_bytes()
    (raiz / "familia" / "recortes" / "retrato.png").write_bytes(bytes_b)
    # Versiones PARECIDAS (JPEG recomprimido) para el otro flujo
    _foto(1).save(raiz / "descargas" / "playa_baja.jpg", quality=35)
    _foto(2).save(raiz / "familia" / "recortes" / "retrato_baja.jpg", quality=35)


def _arbol(p: Path):
    return sorted(str(x.relative_to(p)).replace("\\", "/") + ("/" if x.is_dir() else "")
                  for x in p.rglob("*"))


def _probar(nombre, hacer_seleccion):
    print(f"\n=== {nombre} ===")
    with tempfile.TemporaryDirectory(prefix="dup_cc_") as tmp:
        raiz = Path(tmp) / "MisFotos"
        cuarentena = Path(tmp) / "Escritorio" / "Cuarentena fotos"
        construir(raiz)

        carpetas_antes = {str(x.relative_to(raiz))
                          for x in raiz.rglob("*") if x.is_dir()}
        archivos_antes = sum(1 for x in raiz.rglob("*") if x.is_file())

        sel, raiz_arg = hacer_seleccion(raiz)

        # Inspeccionar el PLAN antes de ejecutar.
        plan = planear_movimientos(sel, raiz_arg, str(cuarentena))
        print("  plan de movimientos:")
        for m in plan:
            tipo = ("CARPETA!!!" if Path(m.origen).is_dir()
                    else "archivo" if Path(m.origen).is_file() else "??")
            print(f"    [{tipo}] {Path(m.origen).relative_to(raiz)}  ->  "
                  f"{Path(m.destino).relative_to(cuarentena.parent)}")
            check(Path(m.origen).is_file(),
                  f"el origen a mover es un archivo, no una carpeta: {m.origen}")

        res = mover_a_cuarentena(sel, raiz_arg, str(cuarentena))
        check(not res.fallidos, "ningún movimiento falló")

        # Las carpetas del origen SIGUEN existiendo.
        carpetas_despues = {str(x.relative_to(raiz))
                            for x in raiz.rglob("*") if x.is_dir()}
        check(carpetas_antes == carpetas_despues,
              f"las subcarpetas del origen no se han movido "
              f"(antes={sorted(carpetas_antes)}, después={sorted(carpetas_despues)})")

        # Las copias 'conservar' siguen en su sitio.
        for gi, grupo in enumerate(sel.resultado.grupos):
            for a in grupo.archivos:
                if sel.decision(gi, a.ruta) == CONSERVAR:
                    check(Path(a.ruta).is_file(),
                          f"la copia a conservar sigue existaste: "
                          f"{Path(a.ruta).name}")

        # En la cuarentena solo hay ARCHIVOS (+ el CSV de log), colgando de
        # la estructura recreada; ninguna carpeta entera del origen.
        movidos_reales = [x for x in cuarentena.rglob("*")
                          if x.is_file() and not x.name.endswith(".csv")]
        check(len(movidos_reales) == len(res.movidos),
              f"en la cuarentena hay {len(res.movidos)} archivos movidos")
        print("  árbol de la cuarentena:")
        for linea in _arbol(cuarentena):
            print(f"    {linea}")

        # Nada perdido: (quedan en origen) + (movidos a cuarentena) == (antes)
        quedan = [x for x in raiz.rglob("*") if x.is_file()]
        check(len(quedan) + len(movidos_reales) == archivos_antes,
              f"no se ha perdido nada ({len(quedan)} quedan + "
              f"{len(movidos_reales)} movidos == {archivos_antes} antes)")
        check(len(res.movidos) >= 1, "se ha movido al menos un archivo")


def seleccion_exacta(raiz):
    r = escanear(str(raiz))
    sel = SeleccionDuplicados(r)
    sel.preseleccionar_principales()
    return sel, str(raiz)


def seleccion_parecidas(raiz):
    r = analizar_carpeta(str(raiz), umbral_hamming=12)
    sel = SeleccionDuplicados(r)
    for gi, g in enumerate(r.grupos):
        sel.conservar_solo(gi, g.archivos[0].ruta)
    return sel, str(raiz)


def main():
    _probar("Duplicados exactos", seleccion_exacta)
    _probar("Fotos parecidas", seleccion_parecidas)

    print()
    if fallos:
        print(f"FALLARON {len(fallos)} comprobaciones.")
        sys.exit(1)
    print("MUEVE ARCHIVOS, NO CARPETAS: OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
