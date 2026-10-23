"""Use case: export the result of a scan to CSV.

The columns are those of the report of the original console script
(`buscar_duplicados.py`); their names are in the language of the interface (in Spanish
they are exactly the original ones, so whoever used that CSV does not have to change anything).
"""

import os

from duplicate_finder.application.ports import FileSystem
from duplicate_finder.domain.duplicates import ScanResult
from duplicate_finder.domain.formatting import format_size
from duplicate_finder.i18n import tr


def columns() -> list[str]:
    """The column names, in the language of the interface."""
    return [tr(key) for key in (
        "csv.duplicate_group", "csv.full_path", "csv.size", "csv.size_bytes", "csv.hash")]


class ExportReport:
    def __init__(self, fs: FileSystem) -> None:
        self._fs = fs

    def __call__(self, result: ScanResult, csv_path: str | os.PathLike[str]) -> int:
        """Writes `result.groups` to `csv_path`.

        Returns the number of groups written. Raises OSError if the file cannot be written.
        """
        rows: list[list[object]] = [list(columns())]
        for number, group in enumerate(result.groups, start=1):
            for file in group.files:
                rows.append([
                    tr("report.group_label", number=number),
                    file.path,
                    format_size(file.size),
                    file.size,
                    group.hash,
                ])
        self._fs.write_csv(os.fspath(csv_path), rows)
        return len(result.groups)
