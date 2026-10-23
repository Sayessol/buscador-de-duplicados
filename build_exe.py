"""Builds the app for Windows with PyInstaller.

    python build_exe.py              # single file:  dist/duplicados.exe
    python build_exe.py --carpeta    # folder:       dist/Buscador-de-duplicados/
    python build_exe.py --carpeta --zip   # ...and also   dist/Buscador-de-duplicados.zip

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


def main():
    ap = argparse.ArgumentParser(description="Genera la app para Windows.")
    ap.add_argument("--carpeta", action="store_true",
                    help="formato carpeta (en vez de un solo .exe)")
    ap.add_argument("--zip", action="store_true",
                    help="con --carpeta: comprime el resultado en un ZIP")
    args = ap.parse_args()
    if args.zip and not args.folder:
        ap.error("--zip solo se usa junto con --carpeta")

    if sys.platform != "win32":
        print("AVISO: un .exe de Windows solo se puede generar en Windows "
              "(o con Wine). Estás en:", sys.platform)

    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("Falta PyInstaller. Instala las dependencias:  pip install -r requirements.txt")
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
            print(f"Borrado {path.relative_to(ROOT)}/ anterior.")
        elif path.exists():
            path.unlink()
            print(f"Borrado {path.relative_to(ROOT)} anterior.")

    print("\nGenerando la app (esto tarda 1-3 minutos)...\n")
    environment = dict(os.environ)
    if args.folder:
        environment["FORMATO"] = "carpeta"
    else:
        environment.pop("FORMATO", None)
    cmd = [sys.executable, "-m", "PyInstaller", "build.spec", "--noconfirm",
           "--clean", "--log-level", "WARN"]
    result = subprocess.run(cmd, cwd=ROOT, env=environment, check=False)
    if result.returncode != 0:
        print("\nPyInstaller falló.")
        sys.exit(result.returncode)

    if args.folder:
        exe = destination / "Buscador-de-duplicados.exe"
        if sys.platform != "win32":
            exe = destination / "Buscador-de-duplicados"
    else:
        exe = destination if sys.platform == "win32" else ROOT / "dist" / "duplicados"
    if not exe.exists():
        print(f"\nNo se encontró el ejecutable esperado en {exe}")
        sys.exit(1)

    print("\n" + "=" * 55)
    if args.folder:
        mb = sum(f.stat().st_size for f in destination.rglob("*") if f.is_file()) / (1024 * 1024)
        print(f"Listo:  {destination}")
        print(f"Tamaño de la carpeta: {mb:.1f} MB (el .exe está dentro)")
        if args.zip:
            zip_path = shutil.make_archive(str(ROOT / "dist" / FOLDER_NAME), "zip",
                                           root_dir=ROOT / "dist", base_dir=FOLDER_NAME)
            print(f"ZIP:    {zip_path}  ({Path(zip_path).stat().st_size / (1024 * 1024):.1f} MB)")
    else:
        print(f"Listo:  {exe}")
        print(f"Tamaño: {exe.stat().st_size / (1024 * 1024):.1f} MB")
    print("Pruébalo en una máquina Windows sin Python instalado.")
    print("=" * 55)


if __name__ == "__main__":
    main()
