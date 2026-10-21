# PyInstaller spec. Genera la app en uno de estos dos formatos:
#
#   pyinstaller build.spec --noconfirm
#       -> dist/duplicados.exe : UN solo archivo, sin consola. Se descomprime
#          en una carpeta temporal cada vez que se abre.
#
#   FORMATO=carpeta pyinstaller build.spec --noconfirm        (en PowerShell: $env:FORMATO="carpeta")
#       -> dist/Buscador-de-duplicados/ : una CARPETA con el .exe y sus
#          librerías (_internal/). No extrae nada al arrancar, así que los
#          antivirus la molestan mucho menos. Es lo que se publica en el ZIP.
#
# (Normalmente se usa  python construir_exe.py [--carpeta]  en vez de esto.)

import os

from PyInstaller.utils.hooks import collect_data_files

CARPETA = os.environ.get("FORMATO") == "carpeta"

# CustomTkinter trae archivos de tema (.json) y assets que hay que
# empaquetar aparte del código.
datos = collect_data_files("customtkinter")

a = Analysis(
    ["app.py"],
    pathex=["."],
    binaries=[],
    datas=datos,
    hiddenimports=["customtkinter"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Nada de esto se usa; recorta tamaño del exe.
        # (PIL/Pillow SÍ se usa ahora: fotos parecidas + miniaturas.)
        "numpy", "pandas", "matplotlib", "scipy",
        "pytest", "setuptools", "pip", "unittest", "pydoc",
        "PIL.ImageQt",  # backend Qt: no se usa (sí ImageTk, para CTkImage)
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    # En formato carpeta, las librerías y datos van aparte (en COLLECT).
    [] if CARPETA else a.binaries,
    [] if CARPETA else a.datas,
    [],
    exclude_binaries=CARPETA,
    name="Buscador-de-duplicados" if CARPETA else "duplicados",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,          # app de ventana, sin consola negra detrás
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="icono.ico",   # generado con: python generar_icono.py
)

if CARPETA:
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        name="Buscador-de-duplicados",
    )
