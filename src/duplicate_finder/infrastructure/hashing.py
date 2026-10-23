"""Content hashes of a file (BLAKE2b), read from disk in blocks."""

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
