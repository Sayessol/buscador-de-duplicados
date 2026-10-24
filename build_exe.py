"""Builds the app for Windows with PyInstaller.

    python build_exe.py              # single file:  dist/duplicados.exe
    python build_exe.py --folder     # folder:       dist/Buscador-de-duplicados/
    python build_exe.py --folder --zip   # ...and also   dist/Buscador-de-duplicados.zip

It is equivalent to `pyinstaller build.spec --noconfirm` but prints clear
messages and checks the result. It has to be run on Windows.

Which one to choose? The single .exe is convenient (one file), but it unpacks into
a temporary folder every time it is opened and some antivirus programs hold it
for a few minutes the first time. The folder does not extract anything at startup.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FOLDER_NAME = "Buscador-de-duplicados"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Builds the app for Windows.")
    parser.add_argument(
        "--folder", action="store_true", help="folder format (instead of a single .exe)"
    )
    parser.add_argument(
        "--zip", action="store_true", help="with --folder: compress the result into a ZIP"
    )
    return parser


def parse_args(argv=None) -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.zip and not args.folder:
        parser.error("--zip can only be used together with --folder")
    return args


def main():
    args = parse_args()

    if sys.platform != "win32":
        print(
            "WARNING: a Windows .exe can only be built on Windows (or with Wine). You are on:",
            sys.platform,
        )

    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller is missing. Install the dependencies:  pip install -r requirements.txt")
        sys.exit(1)

    # Cleaning of previous builds: only what is going to be regenerated, so that
    # both formats can be built one after the other without deleting the first.
    destination = ROOT / "dist" / (FOLDER_NAME if args.folder else "duplicados.exe")
    to_delete = [ROOT / "build", destination]
    if args.zip:
        to_delete.append(ROOT / "dist" / f"{FOLDER_NAME}.zip")
    for path in to_delete:
        if path.is_dir():
            shutil.rmtree(path)
            print(f"Deleted the previous {path.relative_to(ROOT)}/.")
        elif path.exists():
            path.unlink()
            print(f"Deleted the previous {path.relative_to(ROOT)}.")

    print("\nBuilding the app (this takes 1-3 minutes)...\n")
    environment = dict(os.environ)
    if args.folder:
        environment["BUILD_FORMAT"] = "folder"
    else:
        environment.pop("BUILD_FORMAT", None)
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "build.spec",
        "--noconfirm",
        "--clean",
        "--log-level",
        "WARN",
    ]
    result = subprocess.run(cmd, cwd=ROOT, env=environment, check=False)
    if result.returncode != 0:
        print("\nPyInstaller failed.")
        sys.exit(result.returncode)

    if args.folder:
        exe = destination / "Buscador-de-duplicados.exe"
        if sys.platform != "win32":
            exe = destination / "Buscador-de-duplicados"
    else:
        exe = destination if sys.platform == "win32" else ROOT / "dist" / "duplicados"
    if not exe.exists():
        print(f"\nThe expected executable was not found at {exe}")
        sys.exit(1)

    print("\n" + "=" * 55)
    if args.folder:
        mb = sum(f.stat().st_size for f in destination.rglob("*") if f.is_file()) / (1024 * 1024)
        print(f"Done:   {destination}")
        print(f"Folder size: {mb:.1f} MB (the .exe is inside)")
        if args.zip:
            zip_path = shutil.make_archive(
                str(ROOT / "dist" / FOLDER_NAME),
                "zip",
                root_dir=ROOT / "dist",
                base_dir=FOLDER_NAME,
            )
            print(f"ZIP:    {zip_path}  ({Path(zip_path).stat().st_size / (1024 * 1024):.1f} MB)")
    else:
        print(f"Done:   {exe}")
        print(f"Size:   {exe.stat().st_size / (1024 * 1024):.1f} MB")
    print("Try it on a Windows machine without Python installed.")
    print("=" * 55)


if __name__ == "__main__":
    main()
