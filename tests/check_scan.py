"""Prueba manual por consola del núcleo, sin interfaz gráfica.

Hace lo mismo que el script original desde el punto de vista del usuario:
pide una carpeta, la escanea y deja un CSV. Sirve para probar el núcleo
sobre carpetas reales antes de montar la ventana.

Uso:
    python tests/check_scan.py
    python tests/check_scan.py "D:\\Fotos"
"""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.scanner import scan, ScanCancelled          # noqa: E402
from core.report import export_csv                         # noqa: E402
from core.hashing import format_size                     # noqa: E402

REPORT_NAME = "duplicados_reporte.csv"


def _print_progress(p):
    # \r para sobrescribir la misma línea
    print(f"  {p.message}".ljust(70), end="\r", flush=True)


def main():
    if len(sys.argv) > 1:
        folder = sys.argv[1].strip()
    else:
        folder = input("Ruta de la carpeta a escanear (ej. D:\\Fotos): ").strip()

    if not os.path.isdir(folder):
        print(f"\n[ERROR] La ruta '{folder}' no existe o no es una carpeta.")
        return

    print(f"\nEscaneando: {folder}\n")
    start = time.time()
    try:
        result = scan(folder, progress=_print_progress)
    except ScanCancelled:
        print("\nEscaneo cancelado.")
        return
    duration = time.time() - start
    print()  # salto de línea tras el \r

    report_path = os.path.join(os.getcwd(), REPORT_NAME)
    export_csv(result, report_path)

    print("\n" + "=" * 55)
    print(f"Archivos revisados:            {result.total_files}")
    print(f"Grupos de duplicados:          {result.total_groups}")
    print(f"Archivos duplicados en total:  {result.total_files_duplicates}")
    print(f"Copias que se podrían mover:   {result.extra_copies}")
    print(f"Espacio recuperable:           "
          f"{format_size(result.total_reclaimable_space)} "
          f"({result.total_reclaimable_space} bytes)")
    if result.errors:
        print(f"Avisos de lectura:            {len(result.errors)}")
    print(f"Tiempo:                       {duration:.1f} s")
    print(f"Reporte CSV:                  {report_path}")
    print("No se movió ni se borró ningún archivo.")
    print("=" * 55)

    for number, group in enumerate(result.groups[:10], start=1):
        print(f"\nGrupo {number}  ({group.count} copias, "
              f"{format_size(group.size)} c/u, "
              f"libera {format_size(group.reclaimable_space)}):")
        for file in group.files:
            print(f"    {file.path}")
    if result.total_groups > 10:
        print(f"\n... y {result.total_groups - 10} grupos más (ver CSV).")


if __name__ == "__main__":
    main()
