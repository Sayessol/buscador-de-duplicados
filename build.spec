# PyInstaller spec. It builds the app in one of two formats:
#
#   pyinstaller build.spec --noconfirm
#       -> dist/duplicados.exe : ONE single file, no console. It unpacks
#          into a temporary folder every time it is opened.
#
#   BUILD_FORMAT=folder pyinstaller build.spec --noconfirm   (in PowerShell: $env:BUILD_FORMAT="folder")
#       -> dist/Buscador-de-duplicados/ : a FOLDER with the .exe and its
#          libraries (_internal/). It extracts nothing at startup, so antivirus
#          programs bother it much less. This is what is published in the ZIP.
#
# (Normally `python build_exe.py [--folder]` is used instead of this.)

import os

from PyInstaller.utils.hooks import collect_data_files

FOLDER = os.environ.get("BUILD_FORMAT") == "folder"

# CustomTkinter ships theme files (.json) and assets that have to be
# packaged apart from the code.
data = collect_data_files("customtkinter")

a = Analysis(
    ["app.py"],
    pathex=["."],
    binaries=[],
    datas=data,
    hiddenimports=["customtkinter"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # None of this is used; it trims the size of the exe.
        # (PIL/Pillow IS used: similar photos + thumbnails.)
        "numpy", "pandas", "matplotlib", "scipy",
        "pytest", "setuptools", "pip", "unittest", "pydoc",
        "PIL.ImageQt",  # Qt backend: not used (ImageTk is, for CTkImage)
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    # In folder format, libraries and data go apart (in COLLECT).
    [] if FOLDER else a.binaries,
    [] if FOLDER else a.datas,
    [],
    exclude_binaries=FOLDER,
    name="Buscador-de-duplicados" if FOLDER else "duplicados",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,          # windowed app, no black console behind it
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="icon.ico",   # generated with: python gen_icon.py
)

if FOLDER:
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        name="Buscador-de-duplicados",
    )
