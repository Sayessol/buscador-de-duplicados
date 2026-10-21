"""Genera la app para Windows con PyInstaller.

    python construir_exe.py              # un solo archivo:  dist/duplicados.exe
    python construir_exe.py --carpeta    # carpeta:          dist/Buscador-de-duplicados/
    python construir_exe.py --carpeta --zip   # ...y además   dist/Buscador-de-duplicados.zip

Equivale a `pyinstaller build.spec --noconfirm` pero deja mensajes
claros y comprueba el resultado. Hay que correrlo en Windows.

¿Cuál elegir? El .exe único es cómodo (un archivo), pero se descomprime en
una carpeta temporal cada vez que se abre y algunos antivirus lo retienen
unos minutos la primera vez. La carpeta no extrae nada al arrancar.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
NOMBRE_CARPETA = "Buscador-de-duplicados"


def main():
    ap = argparse.ArgumentParser(description="Genera la app para Windows.")
    ap.add_argument("--carpeta", action="store_true",
                    help="formato carpeta (en vez de un solo .exe)")
    ap.add_argument("--zip", action="store_true",
                    help="con --carpeta: comprime el resultado en un ZIP")
    args = ap.parse_args()
    if args.zip and not args.carpeta:
        ap.error("--zip solo se usa junto con --carpeta")

    if sys.platform != "win32":
        print("AVISO: un .exe de Windows solo se puede generar en Windows "
              "(o con Wine). Estás en:", sys.platform)

    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("Falta PyInstaller. Instala las dependencias:  pip install -r requirements.txt")
        sys.exit(1)

    # Limpieza de builds anteriores: solo lo que se va a regenerar, para poder
    # construir los dos formatos uno detrás de otro sin borrar el primero.
    destino = RAIZ / "dist" / (NOMBRE_CARPETA if args.carpeta else "duplicados.exe")
    a_borrar = [RAIZ / "build", destino]
    if args.zip:
        a_borrar.append(RAIZ / "dist" / f"{NOMBRE_CARPETA}.zip")
    for ruta in a_borrar:
        if ruta.is_dir():
            shutil.rmtree(ruta)
            print(f"Borrado {ruta.relative_to(RAIZ)}/ anterior.")
        elif ruta.exists():
            ruta.unlink()
            print(f"Borrado {ruta.relative_to(RAIZ)} anterior.")

    print("\nGenerando la app (esto tarda 1-3 minutos)...\n")
    entorno = dict(os.environ)
    if args.carpeta:
        entorno["FORMATO"] = "carpeta"
    else:
        entorno.pop("FORMATO", None)
    cmd = [sys.executable, "-m", "PyInstaller", "build.spec", "--noconfirm",
           "--clean", "--log-level", "WARN"]
    resultado = subprocess.run(cmd, cwd=RAIZ, env=entorno, check=False)
    if resultado.returncode != 0:
        print("\nPyInstaller falló.")
        sys.exit(resultado.returncode)

    if args.carpeta:
        exe = destino / "Buscador-de-duplicados.exe"
        if sys.platform != "win32":
            exe = destino / "Buscador-de-duplicados"
    else:
        exe = destino if sys.platform == "win32" else RAIZ / "dist" / "duplicados"
    if not exe.exists():
        print(f"\nNo se encontró el ejecutable esperado en {exe}")
        sys.exit(1)

    print("\n" + "=" * 55)
    if args.carpeta:
        mb = sum(f.stat().st_size for f in destino.rglob("*") if f.is_file()) / (1024 * 1024)
        print(f"Listo:  {destino}")
        print(f"Tamaño de la carpeta: {mb:.1f} MB (el .exe está dentro)")
        if args.zip:
            zip_ruta = shutil.make_archive(str(RAIZ / "dist" / NOMBRE_CARPETA), "zip",
                                           root_dir=RAIZ / "dist", base_dir=NOMBRE_CARPETA)
            print(f"ZIP:    {zip_ruta}  ({Path(zip_ruta).stat().st_size / (1024 * 1024):.1f} MB)")
    else:
        print(f"Listo:  {exe}")
        print(f"Tamaño: {exe.stat().st_size / (1024 * 1024):.1f} MB")
    print("Pruébalo en una máquina Windows sin Python instalado.")
    print("=" * 55)


if __name__ == "__main__":
    main()
