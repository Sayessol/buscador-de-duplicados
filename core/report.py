"""Exportar el resultado de un escaneo a CSV.

El formato de columnas es compatible con el reporte del script de
consola original (`buscar_duplicados.py`), para que quien ya usaba
ese CSV no tenga que cambiar nada.
"""

import csv
import os

from .hashing import format_size
from .scanner import ScanResult

COLUMNS = [
    "Grupo_Duplicado",
    "Ruta_Completa",
    "Tamano",
    "Tamano_Bytes",
    "Hash",
]


def export_csv(result: ScanResult, csv_path: str | os.PathLike[str]) -> int:
    """Escribe `resultado.grupos` en `ruta_csv`.

    Devuelve la cantidad de grupos escritos.
    """
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)

        for number, group in enumerate(result.groups, start=1):
            for file in group.files:
                writer.writerow([
                    f"Grupo {number}",
                    file.path,
                    format_size(file.size),
                    file.size,
                    group.hash,
                ])

    return len(result.groups)
