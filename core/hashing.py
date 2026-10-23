"""Cálculo de hashes de contenido y formateo de tamaños.

Se usa BLAKE2b (viene en la librería estándar de Python, es más rápido
que SHA-256 y de sobra seguro para detectar archivos idénticos).

Estrategia en dos niveles, para no leer archivos gigantes enteros sin
necesidad:

1. `hash_parcial`  -> hashea solo los primeros 64 KB del archivo.
2. `hash_completo` -> hashea el archivo entero, leyendo en bloques.

El escáner primero agrupa por tamaño, luego por hash parcial, y solo
calcula el hash completo de los pocos candidatos que sobreviven a los
dos filtros anteriores.
"""

import hashlib

# Tamaño del bloque de lectura para el hash completo (64 KB).
BLOCK_SIZE = 65536

# Cuántos bytes del inicio del archivo mira el hash parcial (64 KB).
# Si el archivo es más chico que esto, el hash parcial cubre todo el
# archivo y es idéntico al hash completo.
PARTIAL_HASH_SIZE = 65536


def partial_hash(file_path: str, nbytes: int = PARTIAL_HASH_SIZE) -> str:
    """Hash BLAKE2b de los primeros `nbytes` bytes del archivo.

    Lanza OSError / PermissionError si el archivo no se puede leer;
    el que llama decide qué hacer con eso.
    """
    h = hashlib.blake2b()
    with open(file_path, "rb") as f:
        h.update(f.read(nbytes))     # una sola lectura: los primeros nbytes
    return h.hexdigest()             # el hash en hexadecimal (texto)


def full_hash(file_path: str, block_size: int = BLOCK_SIZE) -> str:
    """Hash BLAKE2b del contenido completo del archivo.

    Lee en bloques para no cargar archivos grandes enteros en memoria.
    Lanza OSError / PermissionError si el archivo no se puede leer.
    """
    h = hashlib.blake2b()
    with open(file_path, "rb") as f:
        while True:
            block = f.read(block_size)   # lee de 64 KB en 64 KB
            if not block:                    # cadena vacía = fin del archivo
                break
            h.update(block)                  # va acumulando en el hash
    return h.hexdigest()


def format_size(bytes_: float) -> str:
    """Convierte una cantidad de bytes a texto legible (B, KB, MB, GB...).

    Mismo comportamiento que el script de consola original: divide entre
    1024 y muestra un decimal.
    """
    value = float(bytes_)
    # Va subiendo de unidad mientras el número no quepa por debajo de 1024.
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} PB"        # por si acaso (petabytes)
