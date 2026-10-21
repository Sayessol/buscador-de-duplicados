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
TAMANO_BLOQUE = 65536

# Cuántos bytes del inicio del archivo mira el hash parcial (64 KB).
# Si el archivo es más chico que esto, el hash parcial cubre todo el
# archivo y es idéntico al hash completo.
TAMANO_HASH_PARCIAL = 65536


def hash_parcial(ruta_archivo: str, nbytes: int = TAMANO_HASH_PARCIAL) -> str:
    """Hash BLAKE2b de los primeros `nbytes` bytes del archivo.

    Lanza OSError / PermissionError si el archivo no se puede leer;
    el que llama decide qué hacer con eso.
    """
    h = hashlib.blake2b()
    with open(ruta_archivo, "rb") as f:
        h.update(f.read(nbytes))     # una sola lectura: los primeros nbytes
    return h.hexdigest()             # el hash en hexadecimal (texto)


def hash_completo(ruta_archivo: str, tamano_bloque: int = TAMANO_BLOQUE) -> str:
    """Hash BLAKE2b del contenido completo del archivo.

    Lee en bloques para no cargar archivos grandes enteros en memoria.
    Lanza OSError / PermissionError si el archivo no se puede leer.
    """
    h = hashlib.blake2b()
    with open(ruta_archivo, "rb") as f:
        while True:
            bloque = f.read(tamano_bloque)   # lee de 64 KB en 64 KB
            if not bloque:                    # cadena vacía = fin del archivo
                break
            h.update(bloque)                  # va acumulando en el hash
    return h.hexdigest()


def formatear_tamano(bytes_: float) -> str:
    """Convierte una cantidad de bytes a texto legible (B, KB, MB, GB...).

    Mismo comportamiento que el script de consola original: divide entre
    1024 y muestra un decimal.
    """
    valor = float(bytes_)
    # Va subiendo de unidad mientras el número no quepa por debajo de 1024.
    for unidad in ["B", "KB", "MB", "GB", "TB"]:
        if valor < 1024:
            return f"{valor:.1f} {unidad}"
        valor /= 1024
    return f"{valor:.1f} PB"        # por si acaso (petabytes)
