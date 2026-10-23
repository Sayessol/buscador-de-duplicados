"""Filtros de escaneo: qué archivos y carpetas ignorar.

Sirve para que el usuario descarte de entrada lo que no le interesa
deduplicar (temporales, cachés, descargas a medias, archivos de
sistema...). Lo que se excluye aquí ni siquiera se hashea, así que
además acelera el escaneo.
"""

import os
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Self

# Extensiones que casi nunca vale la pena deduplicar. El usuario puede
# editar esta lista desde la interfaz.
JUNK_EXTENSIONS = [
    "tmp", "temp", "bak", "old", "log", "cache", "dmp", "chk",
    "crdownload", "part", "partial", "download", "!ut", "aria2",
    "swp", "swo", "swn", "~lock",
]

# Nombres de archivo completos a ignorar (no tienen extensión útil).
JUNK_NAMES = [
    "thumbs.db", "desktop.ini", ".ds_store", ".localized", "$recycle.bin",
]

# Nombres de carpeta a no entrar (se podan del recorrido entero).
JUNK_FOLDERS = [
    "$recycle.bin", "system volume information",
    "node_modules", ".git", ".svn", ".hg", "__pycache__",
    ".cache", ".tmp", ".trash", ".trash-1000",
]

# Categorías rápidas para "buscar solo estos tipos de archivo". Cada una
# marca sus extensiones en el campo de inclusión; el usuario puede
# combinar varias (p. ej. Imágenes + Vídeo) o añadir las suyas a mano.
CATEGORY_EXTENSIONS = {
    "Imágenes": {
        "jpg", "jpeg", "png", "gif", "bmp", "webp", "tiff", "tif",
        "heic", "heif", "svg", "raw", "cr2", "nef", "arw", "dng", "ico",
    },
    "Audio": {
        "mp3", "wav", "flac", "aac", "ogg", "wma", "m4a", "opus", "aiff",
    },
    "Vídeo": {
        "mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "m4v",
        "mpg", "mpeg", "3gp",
    },
    "Documentos": {
        "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt",
        "odt", "ods", "odp", "rtf", "csv",
    },
    "Comprimidos": {
        "zip", "rar", "7z", "tar", "gz", "bz2", "xz",
    },
}


def _tokens(text: str | None) -> list[str]:
    """Parte 'tmp, .log; bak  old' en ['tmp', '.log', 'bak', 'old']."""
    if not text:
        return []
    return [
        t for t in text.replace(",", " ").replace(";", " ").replace("\n", " ").split()
        if t
    ]


def parse_extensions(text: str | None) -> set[str]:
    """Texto libre -> set de extensiones normalizadas sin punto ni mayúsculas."""
    return {t.lower().lstrip(".") for t in _tokens(text) if t.strip(".")}


def parse_names(text: str | None) -> set[str]:
    return {t.lower() for t in _tokens(text)}


def set_to_text(values: Iterable[str]) -> str:
    """set -> texto ordenado para mostrar en un campo de la interfaz."""
    return "  ".join(sorted(values))


@dataclass
class ScanFilter:
    """Reglas de inclusión/exclusión aplicadas durante la Pasada 1 del escaneo."""

    excluded_extensions: set[str] = field(default_factory=set)   # {'tmp', 'log'}
    included_extensions: set[str] = field(default_factory=set)   # {'jpg', 'png'} — lista blanca
    excluded_names: set[str] = field(default_factory=set)        # {'thumbs.db'}
    excluded_folders: set[str] = field(default_factory=set)       # {'node_modules'}
    min_size: int = 0     # bytes; poné 1 para ignorar archivos vacíos

    @classmethod
    def no_filter(cls) -> Self:
        return cls()

    @classmethod
    def by_default(cls) -> Self:
        return cls(
            excluded_extensions=set(JUNK_EXTENSIONS),
            excluded_names=set(JUNK_NAMES),
            excluded_folders=set(JUNK_FOLDERS),
            min_size=1,
        )

    # -- consultas que usa el escáner ---------------------------------
    def excludes_folder(self, folder_name: str) -> bool:
        return folder_name.lower() in self.excluded_folders

    def excludes_name(self, file_name: str) -> bool:
        low = file_name.lower()
        if low in self.excluded_names:
            return True
        ext = os.path.splitext(low)[1].lstrip(".")
        # Si hay lista blanca de extensiones, solo esas pasan (p. ej.
        # "buscar solo imágenes"); todo lo demás se descarta aquí mismo.
        if self.included_extensions and ext not in self.included_extensions:
            return True
        return bool(ext) and ext in self.excluded_extensions

    def excludes_size(self, size_bytes: int) -> bool:
        return size_bytes < self.min_size

    def is_empty(self) -> bool:
        return not (
            self.excluded_extensions
            or self.included_extensions
            or self.excluded_names
            or self.excluded_folders
            or self.min_size > 0
        )
