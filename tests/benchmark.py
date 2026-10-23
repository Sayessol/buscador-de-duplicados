"""Measures how much the 3-pass scan saves compared with hashing all the content.

    python tests/benchmark.py            # 4,000 files (~1 GB temporary)
    python tests/benchmark.py 10000      # another size

It creates a temporary folder with files of random content (sizes between
8 KB and 1 MB) and three kinds of "near duplicates" that make each
pass work:

  · 10 %  exact copies of another file (the real duplicates)
  ·  5 %  same size as another but different content from the start
          -> discarded by the partial hash (pass 2)
  ·  3 %  same size and same first 64 KB, but different afterwards
          -> only discarded by the full hash (pass 3)

It compares with the "naive" method (the one from the original script: hashing the
whole file for all of them) and checks that both find EXACTLY the same groups.

Note: it is measured with freshly created files, so the operating system
has them cached and the times are more optimistic than on a "cold" disk. The
bytes read, on the other hand, do not depend on the cache.
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

    paths = []                      # (path, size) of the originals already created
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
        size = int(8_192 * (128 ** rnd.random()))          # 8 KB .. 1 MB, more small than large
        data = rnd.randbytes(size)
        paths.append((write(f"f{i:05d}.bin", data), data))

    for i in range(n_copies):                               # exact copies
        _, data = rnd.choice(paths)
        write(f"copia{i:05d}.bin", data)

    for i in range(n_same_size):                            # same size, other content
        _, data = rnd.choice(paths)
        write(f"mismotam{i:05d}.bin", rnd.randbytes(len(data)))

    large = [d for _, d in paths if len(d) > PARTIAL_HASH_SIZE * 2]
    for i in range(n_same_start):                            # same start, other end
        data = rnd.choice(large)
        queue = bytearray(data[PARTIAL_HASH_SIZE:])
        queue[0] ^= 0xFF
        write(f"mismoini{i:05d}.bin", data[:PARTIAL_HASH_SIZE] + bytes(queue))
    return total


def naive_method(base: Path):
    """Hashes the WHOLE content of all the files (like the original script)."""
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
    """Uses the app's scanner, counting the bytes it really reads."""
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
        sys.stdout.reconfigure(encoding="utf-8")   # the Windows console is usually cp1252
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
    tmp = Path(tempfile.mkdtemp(prefix="bench_"))
    try:
        base = tmp / "datos"
        print(f"Creando {n} archivos de prueba...")
        total = create_data(base, n)
        print(f"  {n} archivos, {format_size(total)} en total\n")

        # Each method is repeated and the BEST time is taken: that way the first one does not
        # pay alone the cost of "warming up" the disk cache and the antivirus.
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
