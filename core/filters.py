"""Scan filters: which files and folders to ignore.

They let the user discard up front what they do not want to
deduplicate (temporary files, caches, half-finished downloads, system
files...). What is excluded here is not even hashed, so it also
speeds up the scan.
"""

import os
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Self

# Extensions that are almost never worth deduplicating. The user can
# edit this list from the interface.
JUNK_EXTENSIONS = [
    "tmp", "temp", "bak", "old", "log", "cache", "dmp", "chk",
    "crdownload", "part", "partial", "download", "!ut", "aria2",
    "swp", "swo", "swn", "~lock",
]

# Full file names to ignore (they have no useful extension).
JUNK_NAMES = [
    "thumbs.db", "desktop.ini", ".ds_store", ".localized", "$recycle.bin",
]

# Folder names not to enter (pruned from the whole walk).
JUNK_FOLDERS = [
    "$recycle.bin", "system volume information",
    "node_modules", ".git", ".svn", ".hg", "__pycache__",
    ".cache", ".tmp", ".trash", ".trash-1000",
]

# Quick categories for "search only these kinds of file". Each one
# ticks its extensions in the inclusion field; the user can combine
# several (e.g. Images + Video) or add their own by hand.
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
    """Splits 'tmp, .log; bak  old' into ['tmp', '.log', 'bak', 'old']."""
    if not text:
        return []
    return [
        t for t in text.replace(",", " ").replace(";", " ").replace("\n", " ").split()
        if t
    ]


def parse_extensions(text: str | None) -> set[str]:
    """Free text -> set of normalized extensions, without dot or capitals."""
    return {t.lower().lstrip(".") for t in _tokens(text) if t.strip(".")}


def parse_names(text: str | None) -> set[str]:
    return {t.lower() for t in _tokens(text)}


def set_to_text(values: Iterable[str]) -> str:
    """set -> sorted text to show in an interface field."""
    return "  ".join(sorted(values))


@dataclass
class ScanFilter:
    """Include/exclude rules applied during pass 1 of the scan."""

    excluded_extensions: set[str] = field(default_factory=set)   # {'tmp', 'log'}
    included_extensions: set[str] = field(default_factory=set)   # {'jpg', 'png'} — whitelist
    excluded_names: set[str] = field(default_factory=set)        # {'thumbs.db'}
    excluded_folders: set[str] = field(default_factory=set)       # {'node_modules'}
    min_size: int = 0     # bytes; use 1 to ignore empty files

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

    # -- queries used by the scanner ---------------------------------
    def excludes_folder(self, folder_name: str) -> bool:
        return folder_name.lower() in self.excluded_folders

    def excludes_name(self, file_name: str) -> bool:
        low = file_name.lower()
        if low in self.excluded_names:
            return True
        ext = os.path.splitext(low)[1].lstrip(".")
        # If there is a whitelist of extensions, only those pass (e.g.
        # "search only images"); everything else is discarded right here.
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
