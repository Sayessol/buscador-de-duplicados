"""Manual console test of the core, without a graphical interface.

It does the same as the original script from the user's point of view:
asks for a folder, scans it and leaves a CSV. It is useful to try the core
on real folders before building the window.

Usage:
    python tests/check_scan.py
    python tests/check_scan.py "D:\\Photos"
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
    # \r to overwrite the same line
    print(f"  {p.message}".ljust(70), end="\r", flush=True)


def main():
    if len(sys.argv) > 1:
        folder = sys.argv[1].strip()
    else:
        folder = input("Path of the folder to scan (e.g. D:\\Photos): ").strip()

    if not os.path.isdir(folder):
        print(f"\n[ERROR] The path '{folder}' does not exist or is not a folder.")
        return

    print(f"\nScanning: {folder}\n")
    start = time.time()
    try:
        result = scan(folder, progress=_print_progress)
    except ScanCancelled:
        print("\nScan cancelled.")
        return
    duration = time.time() - start
    print()  # line break after the \r

    report_path = os.path.join(os.getcwd(), REPORT_NAME)
    export_csv(result, report_path)

    print("\n" + "=" * 55)
    print(f"Files reviewed:                {result.total_files}")
    print(f"Duplicate groups:              {result.total_groups}")
    print(f"Duplicate files in total:      {result.total_files_duplicates}")
    print(f"Copies that could be moved:    {result.extra_copies}")
    print(f"Recoverable space:            {format_size(result.total_reclaimable_space)} "
          f"({result.total_reclaimable_space} bytes)")
    if result.errors:
        print(f"Read warnings:                {len(result.errors)}")
    print(f"Time:                         {duration:.1f} s")
    print(f"CSV report:                   {report_path}")
    print("No file was moved or deleted.")
    print("=" * 55)

    for number, group in enumerate(result.groups[:10], start=1):
        print(f"\nGroup {number}  ({group.count} copies, {format_size(group.size)} each, "
              f"frees {format_size(group.reclaimable_space)}):")
        for file in group.files:
            print(f"    {file.path}")
    if result.total_groups > 10:
        print(f"\n... and {result.total_groups - 10} more groups (see the CSV).")


if __name__ == "__main__":
    main()
