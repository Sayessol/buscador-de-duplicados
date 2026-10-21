"""Prueba manual por consola del núcleo, sin interfaz gráfica.

Hace lo mismo que el script original desde el punto de vista del usuario:
pide una carpeta, la escanea y deja un CSV. Sirve para probar el núcleo
sobre carpetas reales antes de montar la ventana.

Uso:
    python pruebas/probar_escaneo.py
    python pruebas/probar_escaneo.py "D:\\Fotos"
"""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.scanner import escanear, EscaneoCancelado          # noqa: E402
from core.reporte import exportar_csv                         # noqa: E402
from core.hashing import formatear_tamano                     # noqa: E402

NOMBRE_REPORTE = "duplicados_reporte.csv"


def _imprimir_progreso(p):
    # \r para sobrescribir la misma línea
    print(f"  {p.mensaje}".ljust(70), end="\r", flush=True)


def main():
    if len(sys.argv) > 1:
        carpeta = sys.argv[1].strip()
    else:
        carpeta = input("Ruta de la carpeta a escanear (ej. D:\\Fotos): ").strip()

    if not os.path.isdir(carpeta):
        print(f"\n[ERROR] La ruta '{carpeta}' no existe o no es una carpeta.")
        return

    print(f"\nEscaneando: {carpeta}\n")
    inicio = time.time()
    try:
        resultado = escanear(carpeta, progreso=_imprimir_progreso)
    except EscaneoCancelado:
        print("\nEscaneo cancelado.")
        return
    duracion = time.time() - inicio
    print()  # salto de línea tras el \r

    ruta_reporte = os.path.join(os.getcwd(), NOMBRE_REPORTE)
    exportar_csv(resultado, ruta_reporte)

    print("\n" + "=" * 55)
    print(f"Archivos revisados:            {resultado.total_archivos}")
    print(f"Grupos de duplicados:          {resultado.total_grupos}")
    print(f"Archivos duplicados en total:  {resultado.total_archivos_duplicados}")
    print(f"Copias que se podrían mover:   {resultado.copias_sobrantes}")
    print(f"Espacio recuperable:           "
          f"{formatear_tamano(resultado.espacio_recuperable_total)} "
          f"({resultado.espacio_recuperable_total} bytes)")
    if resultado.errores:
        print(f"Avisos de lectura:            {len(resultado.errores)}")
    print(f"Tiempo:                       {duracion:.1f} s")
    print(f"Reporte CSV:                  {ruta_reporte}")
    print("No se movió ni se borró ningún archivo.")
    print("=" * 55)

    for numero, grupo in enumerate(resultado.grupos[:10], start=1):
        print(f"\nGrupo {numero}  ({grupo.cantidad} copias, "
              f"{formatear_tamano(grupo.tamano)} c/u, "
              f"libera {formatear_tamano(grupo.espacio_recuperable)}):")
        for archivo in grupo.archivos:
            print(f"    {archivo.ruta}")
    if resultado.total_grupos > 10:
        print(f"\n... y {resultado.total_grupos - 10} grupos más (ver CSV).")


if __name__ == "__main__":
    main()
