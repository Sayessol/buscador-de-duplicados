"""Mide cuánto ahorra el escaneo en 3 pasadas frente a hashear todo el contenido.

    python tests/benchmark.py            # 4.000 archivos (~1 GB temporal)
    python tests/benchmark.py 10000      # otro tamaño

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
from core.hashing import PARTIAL_HASH_SIZE, format_size  # noqa: E402

SEED = 2026
REPETITIONS = 3


def create_data(base: Path, n: int) -> int:
    rnd = random.Random(SEED)
    base.mkdir(parents=True)
    folders = [base / f"c{i:02d}" / f"s{j}" for i in range(20) for j in range(5)]
    for c in folders:
        c.mkdir(parents=True)

    paths = []                      # (ruta, tamaño) de los originales ya creados
    total = 0

    def write(name, data):
        nonlocal total
        path = rnd.choice(folders) / name
        path.write_bytes(data)
        total += len(data)
        return path

    n_copies, n_same_size, n_same_start = int(n * .10), int(n * .05), int(n * .03)
    n_unique = n - n_copies - n_same_size - n_same_start

    for i in range(n_unique):
        size = int(8_192 * (128 ** rnd.random()))          # 8 KB .. 1 MB, más pequeños que grandes
        data = rnd.randbytes(size)
        paths.append((write(f"f{i:05d}.bin", data), data))

    for i in range(n_copies):                               # copias exactas
        _, data = rnd.choice(paths)
        write(f"copia{i:05d}.bin", data)

    for i in range(n_same_size):                            # mismo tamaño, otro contenido
        _, data = rnd.choice(paths)
        write(f"mismotam{i:05d}.bin", rnd.randbytes(len(data)))

    large = [d for _, d in paths if len(d) > PARTIAL_HASH_SIZE * 2]
    for i in range(n_same_start):                            # mismo inicio, otro final
        data = rnd.choice(large)
        queue = bytearray(data[PARTIAL_HASH_SIZE:])
        queue[0] ^= 0xFF
        write(f"mismoini{i:05d}.bin", data[:PARTIAL_HASH_SIZE] + bytes(queue))
    return total


def naive_method(base: Path):
    """Hashea el contenido ENTERO de todos los archivos (como el script original)."""
    groups, read, count = defaultdict(list), 0, 0
    for folder, _subs, files in os.walk(base):
        for name in files:
            path = os.path.join(folder, name)
            h = hashlib.blake2b()
            with open(path, "rb") as f:
                while block := f.read(65536):
                    h.update(block)
                    read += len(block)
            groups[h.hexdigest()].append(path)
            count += 1
    return {frozenset(v) for v in groups.values() if len(v) > 1}, read, count


def three_pass_method(base: Path):
    """Usa el escáner de la app, contando los bytes que de verdad lee."""
    read = 0
    partial, full = scanner.partial_hash, scanner.full_hash

    def partial_counted(path, *a, **k):
        nonlocal read
        read += min(os.path.getsize(path), PARTIAL_HASH_SIZE)
        return partial(path, *a, **k)

    def full_counted(path, *a, **k):
        nonlocal read
        read += os.path.getsize(path)
        return full(path, *a, **k)

    scanner.partial_hash, scanner.full_hash = partial_counted, full_counted
    try:
        res = scanner.scan(str(base))
    finally:
        scanner.partial_hash, scanner.full_hash = partial, full
    groups = {frozenset(a.path for a in g.files) for g in res.groups}
    return groups, read, res.total_files


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")   # la consola de Windows suele ser cp1252
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
    tmp = Path(tempfile.mkdtemp(prefix="bench_"))
    try:
        base = tmp / "datos"
        print(f"Creando {n} archivos de prueba...")
        total = create_data(base, n)
        print(f"  {n} archivos, {format_size(total)} en total\n")

        # Se repite cada método y se toma el MEJOR tiempo: así el primero no paga
        # en solitario el coste de "calentar" la caché del disco y el antivirus.
        t_naive = t_app = float("inf")
        for _ in range(REPETITIONS):
            t = time.perf_counter()
            g_naive, b_naive, _ = naive_method(base)
            t_naive = min(t_naive, time.perf_counter() - t)

            t = time.perf_counter()
            g_app, b_app, _ = three_pass_method(base)
            t_app = min(t_app, time.perf_counter() - t)

        equal = g_naive == g_app
        print(f"{'Método':<28}{'Tiempo':>10}{'Bytes leídos':>16}{'% del total':>13}")
        print("-" * 67)
        print(f"{'Hashear todo (ingenuo)':<28}{t_naive:>9.2f}s{format_size(b_naive):>16}"
              f"{100 * b_naive / total:>12.1f}%")
        print(f"{'3 pasadas (esta app)':<28}{t_app:>9.2f}s{format_size(b_app):>16}"
              f"{100 * b_app / total:>12.1f}%")
        print(f"\nGrupos de duplicados: {len(g_app)}  ·  "
              f"mismos grupos que el método ingenuo: {'SÍ' if equal else 'NO'}")
        print(f"Ahorro de lectura: {100 * (1 - b_app / b_naive):.0f} %  ·  "
              f"tiempo {t_naive / t_app:.1f}x más rápido (mejor de {REPETITIONS})")
        if not equal:
            sys.exit(1)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
