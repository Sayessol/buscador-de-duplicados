"""Exportar el resultado de un escaneo a CSV.

El formato de columnas es compatible con el reporte del script de
consola original (`buscar_duplicados.py`), para que quien ya usaba
ese CSV no tenga que cambiar nada.
"""

import csv
import os

from .hashing import formatear_tamano
from .scanner import ResultadoEscaneo

COLUMNAS = [
    "Grupo_Duplicado",
    "Ruta_Completa",
    "Tamano",
    "Tamano_Bytes",
    "Hash",
]


def exportar_csv(resultado: ResultadoEscaneo, ruta_csv: str | os.PathLike[str]) -> int:
    """Escribe `resultado.grupos` en `ruta_csv`.

    Devuelve la cantidad de grupos escritos.
    """
    with open(ruta_csv, "w", newline="", encoding="utf-8-sig") as f:
        escritor = csv.writer(f)
        escritor.writerow(COLUMNAS)

        for numero, grupo in enumerate(resultado.grupos, start=1):
            for archivo in grupo.archivos:
                escritor.writerow([
                    f"Grupo {numero}",
                    archivo.ruta,
                    formatear_tamano(archivo.tamano),
                    archivo.tamano,
                    grupo.hash,
                ])

    return len(resultado.grupos)
