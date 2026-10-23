"""Núcleo de la app de duplicados: lógica pura, sin interfaz gráfica.

Todo lo de este paquete se puede probar por consola sin abrir ninguna
ventana. La regla de oro se mantiene en todas las funciones que tocan
el sistema de archivos: **nunca borrar, nunca modificar el original,
solo leer y (cuando el usuario lo confirma) mover.**
"""

# Única fuente de la versión: la usan la ventana y el nombre de la release.
# Al publicar una versión nueva, se cambia aquí y se añade su apartado en CHANGELOG.md
# (una prueba comprueba que los dos coinciden).
__version__ = "1.0.0"

from .hashing import (
    partial_hash,
    full_hash,
    format_size,
    BLOCK_SIZE,
    PARTIAL_HASH_SIZE,
)
from .scanner import (
    DuplicateFile,
    DuplicateGroup,
    ScanResult,
    Progress,
    ScanCancelled,
    scan,
)
from .filters import (
    ScanFilter,
    parse_extensions,
    parse_names,
    set_to_text,
    JUNK_EXTENSIONS,
    JUNK_NAMES,
    JUNK_FOLDERS,
    CATEGORY_EXTENSIONS,
)
from .selection import (
    DuplicateSelection,
    KEEP,
    MOVE,
    GROUP_OK,
    GROUP_NOTHING_KEPT,
    GROUP_MULTIPLE,
)
from .quarantine import (
    Move,
    QuarantineResult,
    InvalidQuarantine,
    validate_quarantine_folder,
    plan_moves,
    move_to_quarantine,
)
from .report import export_csv

__all__ = [
    "partial_hash",
    "full_hash",
    "format_size",
    "BLOCK_SIZE",
    "PARTIAL_HASH_SIZE",
    "DuplicateFile",
    "DuplicateGroup",
    "ScanResult",
    "Progress",
    "ScanCancelled",
    "scan",
    "ScanFilter",
    "parse_extensions",
    "parse_names",
    "set_to_text",
    "JUNK_EXTENSIONS",
    "JUNK_NAMES",
    "JUNK_FOLDERS",
    "CATEGORY_EXTENSIONS",
    "DuplicateSelection",
    "KEEP",
    "MOVE",
    "GROUP_OK",
    "GROUP_NOTHING_KEPT",
    "GROUP_MULTIPLE",
    "Move",
    "QuarantineResult",
    "InvalidQuarantine",
    "validate_quarantine_folder",
    "plan_moves",
    "move_to_quarantine",
    "export_csv",
]
