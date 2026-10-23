"""Content hash computation and size formatting.

BLAKE2b is used (it ships with Python's standard library, is faster than
SHA-256 and more than secure enough to detect identical files).

Two-level strategy, so huge files are not read in full unnecessarily:

1. `partial_hash` -> hashes only the first 64 KB of the file.
2. `full_hash`    -> hashes the whole file, reading in blocks.

The scanner first groups by size, then by partial hash, and only
computes the full hash of the few candidates that survive the two
previous filters.
"""

import hashlib

# Read block size for the full hash (64 KB).
BLOCK_SIZE = 65536

# How many bytes from the start of the file the partial hash looks at (64 KB).
# If the file is smaller than this, the partial hash covers the whole
# file and is identical to the full hash.
PARTIAL_HASH_SIZE = 65536


def partial_hash(file_path: str, nbytes: int = PARTIAL_HASH_SIZE) -> str:
    """BLAKE2b hash of the first `nbytes` bytes of the file.

    Raises OSError / PermissionError if the file cannot be read;
    the caller decides what to do about it.
    """
    h = hashlib.blake2b()
    with open(file_path, "rb") as f:
        h.update(f.read(nbytes))     # a single read: the first nbytes
    return h.hexdigest()             # the hash in hexadecimal (text)


def full_hash(file_path: str, block_size: int = BLOCK_SIZE) -> str:
    """BLAKE2b hash of the whole content of the file.

    Reads in blocks so large files are never loaded into memory in full.
    Raises OSError / PermissionError if the file cannot be read.
    """
    h = hashlib.blake2b()
    with open(file_path, "rb") as f:
        while True:
            block = f.read(block_size)   # reads 64 KB at a time
            if not block:                    # empty bytes = end of file
                break
            h.update(block)                  # accumulates into the hash
    return h.hexdigest()


def format_size(bytes_: float) -> str:
    """Converts a number of bytes to readable text (B, KB, MB, GB...).

    Same behaviour as the original console script: divides by
    1024 and shows one decimal.
    """
    value = float(bytes_)
    # Moves up a unit while the number does not fit below 1024.
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} PB"        # just in case (petabytes)
