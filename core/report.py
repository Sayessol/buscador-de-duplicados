"""Export the result of a scan to CSV.

The column format is compatible with the report of the original
console script (`buscar_duplicados.py`), so that whoever already used
that CSV does not have to change anything.
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
    """Writes `result.groups` to `csv_path`.

    Returns the number of groups written.
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
