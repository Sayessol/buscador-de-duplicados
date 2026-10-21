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
EXTENSIONES_BASURA = [
    "tmp", "temp", "bak", "old", "log", "cache", "dmp", "chk",
    "crdownload", "part", "partial", "download", "!ut", "aria2",
    "swp", "swo", "swn", "~lock",
]

# Nombres de archivo completos a ignorar (no tienen extensión útil).
NOMBRES_BASURA = [
    "thumbs.db", "desktop.ini", ".ds_store", ".localized", "$recycle.bin",
]

# Nombres de carpeta a no entrar (se podan del recorrido entero).
CARPETAS_BASURA = [
    "$recycle.bin", "system volume information",
    "node_modules", ".git", ".svn", ".hg", "__pycache__",
    ".cache", ".tmp", ".trash", ".trash-1000",
]

# Categorías rápidas para "buscar solo estos tipos de archivo". Cada una
# marca sus extensiones en el campo de inclusión; el usuario puede
# combinar varias (p. ej. Imágenes + Vídeo) o añadir las suyas a mano.
CATEGORIAS_EXTENSIONES = {
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


def _tokens(texto: str | None) -> list[str]:
    """Parte 'tmp, .log; bak  old' en ['tmp', '.log', 'bak', 'old']."""
    if not texto:
        return []
    return [
        t for t in texto.replace(",", " ").replace(";", " ").replace("\n", " ").split()
        if t
    ]


def parsear_extensiones(texto: str | None) -> set[str]:
    """Texto libre -> set de extensiones normalizadas sin punto ni mayúsculas."""
    return {t.lower().lstrip(".") for t in _tokens(texto) if t.strip(".")}


def parsear_nombres(texto: str | None) -> set[str]:
    return {t.lower() for t in _tokens(texto)}


def texto_de(conjunto: Iterable[str]) -> str:
    """set -> texto ordenado para mostrar en un campo de la interfaz."""
    return "  ".join(sorted(conjunto))


@dataclass
class FiltroEscaneo:
    """Reglas de inclusión/exclusión aplicadas durante la Pasada 1 del escaneo."""

    extensiones_excluidas: set[str] = field(default_factory=set)   # {'tmp', 'log'}
    extensiones_incluidas: set[str] = field(default_factory=set)   # {'jpg', 'png'} — lista blanca
    nombres_excluidos: set[str] = field(default_factory=set)        # {'thumbs.db'}
    carpetas_excluidas: set[str] = field(default_factory=set)       # {'node_modules'}
    tamano_minimo: int = 0     # bytes; poné 1 para ignorar archivos vacíos

    @classmethod
    def sin_filtro(cls) -> Self:
        return cls()

    @classmethod
    def por_defecto(cls) -> Self:
        return cls(
            extensiones_excluidas=set(EXTENSIONES_BASURA),
            nombres_excluidos=set(NOMBRES_BASURA),
            carpetas_excluidas=set(CARPETAS_BASURA),
            tamano_minimo=1,
        )

    # -- consultas que usa el escáner ---------------------------------
    def excluye_carpeta(self, nombre_carpeta: str) -> bool:
        return nombre_carpeta.lower() in self.carpetas_excluidas

    def excluye_nombre(self, nombre_archivo: str) -> bool:
        bajo = nombre_archivo.lower()
        if bajo in self.nombres_excluidos:
            return True
        ext = os.path.splitext(bajo)[1].lstrip(".")
        # Si hay lista blanca de extensiones, solo esas pasan (p. ej.
        # "buscar solo imágenes"); todo lo demás se descarta aquí mismo.
        if self.extensiones_incluidas and ext not in self.extensiones_incluidas:
            return True
        return bool(ext) and ext in self.extensiones_excluidas

    def excluye_tamano(self, tamano_bytes: int) -> bool:
        return tamano_bytes < self.tamano_minimo

    def esta_vacio(self) -> bool:
        return not (
            self.extensiones_excluidas
            or self.extensiones_incluidas
            or self.nombres_excluidos
            or self.carpetas_excluidas
            or self.tamano_minimo > 0
        )
