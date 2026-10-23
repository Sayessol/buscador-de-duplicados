"""Export the result of a scan to CSV.

The columns are those of the report of the original console script
(`buscar_duplicados.py`); their names are in the language of the interface (in Spanish
they are exactly the original ones, so whoever used that CSV does not have to change anything).
"""

import csv
import os

from .hashing import format_size
from .scanner import ScanResult
from .i18n import tr

def columns() -> list[str]:
    """The column names, in the language of the interface."""
    return [tr(key) for key in (
        "csv.duplicate_group", "csv.full_path", "csv.size", "csv.size_bytes", "csv.hash")]


def export_csv(result: ScanResult, csv_path: str | os.PathLike[str]) -> int:
    """Writes `result.groups` to `csv_path`.

    Returns the number of groups written.
    """
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(columns())

        for number, group in enumerate(result.groups, start=1):
            for file in group.files:
                writer.writerow([
                    tr("report.group_label", number=number),
                    file.path,
                    format_size(file.size),
                    file.size,
                    group.hash,
                ])

    return len(result.groups)
