"""Mide cuánto ahorra el escaneo en 3 pasadas frente a hashear todo el contenido.

    python pruebas/benchmark.py            # 4.000 archivos (~1 GB temporal)
    python pruebas/benchmark.py 10000      # otro tamaño

Crea una carpeta temporal con archivos de contenido aleatorio (tamaños entre
8 KB y 1 MB) y tres tipos de "casi duplicados" que obligan a trabajar a cada
pasada:

  · 10 %  copias exactas de otro archivo (los duplicados de verdad)
  ·  5 %  mismo tamaño que otro pero contenido distinto desde el principio
          -> los descarta el hash parcial (pasada 2)
  ·  3 %  mismo tamaño y mismos primeros 64 KB, pero distinto después
          -> solo los descarta el hash completo (pasada 3)

Compara con el método "ingenuo" (el del script original: hashear el archivo
entero de todos) y comprueba que ambos encuentran EXACTAMENTE los mismos grupos.

Ojo: se mide con los archivos recién creados, así que el sistema operativo los
tiene en caché y los tiempos son más optimistas que en un disco "frío". Los
bytes leídos, en cambio, no dependen de la caché.
"""

import hashlib
import os
import random
import shutil
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import scanner                                    # noqa: E402
from core.hashing import TAMANO_HASH_PARCIAL, formatear_tamano  # noqa: E402

SEMILLA = 2026
REPETICIONES = 3


def crear_datos(base: Path, n: int) -> int:
    rnd = random.Random(SEMILLA)
    base.mkdir(parents=True)
    carpetas = [base / f"c{i:02d}" / f"s{j}" for i in range(20) for j in range(5)]
    for c in carpetas:
        c.mkdir(parents=True)

    rutas = []                      # (ruta, tamaño) de los originales ya creados
    total = 0

    def escribir(nombre, datos):
        nonlocal total
        ruta = rnd.choice(carpetas) / nombre
        ruta.write_bytes(datos)
        total += len(datos)
        return ruta

    n_copias, n_mismo_tam, n_mismo_ini = int(n * .10), int(n * .05), int(n * .03)
    n_unicos = n - n_copias - n_mismo_tam - n_mismo_ini

    for i in range(n_unicos):
        tam = int(8_192 * (128 ** rnd.random()))          # 8 KB .. 1 MB, más pequeños que grandes
        datos = rnd.randbytes(tam)
        rutas.append((escribir(f"f{i:05d}.bin", datos), datos))

    for i in range(n_copias):                               # copias exactas
        _, datos = rnd.choice(rutas)
        escribir(f"copia{i:05d}.bin", datos)

    for i in range(n_mismo_tam):                            # mismo tamaño, otro contenido
        _, datos = rnd.choice(rutas)
        escribir(f"mismotam{i:05d}.bin", rnd.randbytes(len(datos)))

    grandes = [d for _, d in rutas if len(d) > TAMANO_HASH_PARCIAL * 2]
    for i in range(n_mismo_ini):                            # mismo inicio, otro final
        datos = rnd.choice(grandes)
        cola = bytearray(datos[TAMANO_HASH_PARCIAL:])
        cola[0] ^= 0xFF
        escribir(f"mismoini{i:05d}.bin", datos[:TAMANO_HASH_PARCIAL] + bytes(cola))
    return total


def metodo_ingenuo(base: Path):
    """Hashea el contenido ENTERO de todos los archivos (como el script original)."""
    grupos, leidos, cuenta = defaultdict(list), 0, 0
    for carpeta, _subs, archivos in os.walk(base):
        for nombre in archivos:
            ruta = os.path.join(carpeta, nombre)
            h = hashlib.blake2b()
            with open(ruta, "rb") as f:
                while bloque := f.read(65536):
                    h.update(bloque)
                    leidos += len(bloque)
            grupos[h.hexdigest()].append(ruta)
            cuenta += 1
    return {frozenset(v) for v in grupos.values() if len(v) > 1}, leidos, cuenta


def metodo_tres_pasadas(base: Path):
    """Usa el escáner de la app, contando los bytes que de verdad lee."""
    leidos = 0
    parcial, completo = scanner.hash_parcial, scanner.hash_completo

    def parcial_contado(ruta, *a, **k):
        nonlocal leidos
        leidos += min(os.path.getsize(ruta), TAMANO_HASH_PARCIAL)
        return parcial(ruta, *a, **k)

    def completo_contado(ruta, *a, **k):
        nonlocal leidos
        leidos += os.path.getsize(ruta)
        return completo(ruta, *a, **k)

    scanner.hash_parcial, scanner.hash_completo = parcial_contado, completo_contado
    try:
        res = scanner.escanear(str(base))
    finally:
        scanner.hash_parcial, scanner.hash_completo = parcial, completo
    grupos = {frozenset(a.ruta for a in g.archivos) for g in res.grupos}
    return grupos, leidos, res.total_archivos


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")   # la consola de Windows suele ser cp1252
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
    tmp = Path(tempfile.mkdtemp(prefix="bench_"))
    try:
        base = tmp / "datos"
        print(f"Creando {n} archivos de prueba...")
        total = crear_datos(base, n)
        print(f"  {n} archivos, {formatear_tamano(total)} en total\n")

        # Se repite cada método y se toma el MEJOR tiempo: así el primero no paga
        # en solitario el coste de "calentar" la caché del disco y el antivirus.
        t_ing = t_app = float("inf")
        for _ in range(REPETICIONES):
            t = time.perf_counter()
            g_ing, b_ing, _ = metodo_ingenuo(base)
            t_ing = min(t_ing, time.perf_counter() - t)

            t = time.perf_counter()
            g_app, b_app, _ = metodo_tres_pasadas(base)
            t_app = min(t_app, time.perf_counter() - t)

        iguales = g_ing == g_app
        print(f"{'Método':<28}{'Tiempo':>10}{'Bytes leídos':>16}{'% del total':>13}")
        print("-" * 67)
        print(f"{'Hashear todo (ingenuo)':<28}{t_ing:>9.2f}s{formatear_tamano(b_ing):>16}"
              f"{100 * b_ing / total:>12.1f}%")
        print(f"{'3 pasadas (esta app)':<28}{t_app:>9.2f}s{formatear_tamano(b_app):>16}"
              f"{100 * b_app / total:>12.1f}%")
        print(f"\nGrupos de duplicados: {len(g_app)}  ·  "
              f"mismos grupos que el método ingenuo: {'SÍ' if iguales else 'NO'}")
        print(f"Ahorro de lectura: {100 * (1 - b_app / b_ing):.0f} %  ·  "
              f"tiempo {t_ing / t_app:.1f}x más rápido (mejor de {REPETICIONES})")
        if not iguales:
            sys.exit(1)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
