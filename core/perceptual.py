"""Detección de fotos PARECIDAS (no idénticas).

Pilla: la misma foto recomprimida, redimensionada, con un filtro de
color/brillo o una marca de agua en una esquina.

NO pilla: recortes ni rotaciones fuertes (para eso haría falta match de
features tipo OpenCV, que multiplicaría el tamaño de la app).

Cómo funciona
-------------
Por cada imagen se calcula una "huella" barata:

* **dHash (64 bits)** — mide la ESTRUCTURA (gradientes horizontales de una
  miniatura 9×8 en gris). Es muy estable frente a recompresión, cambio de
  tamaño y filtros de color, porque esos no mueven los bordes de sitio.
* **Firma de color (4×4 celdas, RGB medio)** — señal secundaria para no
  juntar dos fotos distintas que por casualidad tienen gradientes
  parecidos (un cielo y una pared lisa, p. ej.).

Dos imágenes son "parecidas" si la distancia de Hamming de sus dHash es
pequeña Y su color no se dispara. El umbral lo decide quien llama
(en la app, un deslizador de sensibilidad).

Agrupación
----------
* Un **BK-tree** sobre los dHash permite buscar vecinos por distancia de
  Hamming sin comparar todas las imágenes contra todas.
* **Union-Find** une las cadenas de parecidos: si A~B y B~C, el grupo es
  {A, B, C} aunque A y C no se parezcan directamente.

Requiere Pillow. Solo este módulo (y el de miniaturas) dependen de él.
"""

import os
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import cast

from PIL import Image, ImageOps

from .filters import ScanFilter
from .app_logging import log
from .scanner import DuplicateFile
from .callbacks import CancelledCallback, ProgressCallback

# Firma de color: una tupla de colores (r, g, b), uno por celda de la cuadrícula de 4×4.
Color = tuple[tuple[int, int, int], ...]

# Extensiones que Pillow abre sin plugins extra.
IMAGE_EXTENSIONS = {
    "jpg", "jpeg", "jpe", "png", "gif", "bmp", "webp",
    "tif", "tiff", "ppm", "pgm",
}
# HEIC/HEIF quedan fuera: Pillow no los abre sin pillow-heif.

_DHASH_SIDE = 8            # -> hash de 8*8 = 64 bits
_COLOR_SIDE = 4            # -> firma de 4*4 celdas RGB

# Formatos sin pérdida: a igualdad de resolución se prefieren como
# "mejor copia" (suelen ser el archivo original, no un reguardado).
_LOSSLESS_EXT = {"png", "tif", "tiff", "bmp", "ppm", "pgm"}


def _is_lossless(path: str) -> bool:
    return os.path.splitext(path)[1].lower().lstrip(".") in _LOSSLESS_EXT


class ComparisonCancelled(Exception):
    """El que llama pidió abortar a mitad."""


@dataclass
class ImageFingerprint:
    path: str
    size: int
    width: int
    height: int
    dhash: int
    color: Color  # longitud _COLOR_SIDE**2

    @property
    def megapixels(self) -> float:
        return (self.width * self.height) / 1_000_000


@dataclass
class SimilarGroup:
    """Conjunto de 2+ imágenes visualmente parecidas.

    `archivos` son DuplicateFile (ruta + tamaño) para poder reutilizar tal
    cual la selección conservar/mover y el movimiento a cuarentena.
    `huellas` lleva los datos extra (resolución, similitud) para la
    interfaz. Ambas listas van en el mismo orden; la primera es la
    "mejor" copia (más resolución, y a igualdad, archivo más grande).
    """

    fingerprints: list[ImageFingerprint]
    files: list[DuplicateFile]      # mismo orden que huellas
    similarity: list[float]          # 0..1 de cada foto respecto a la mejor

    @property
    def count(self) -> int:
        return len(self.files)

    @property
    def size(self) -> int:
        # Para compatibilidad con DuplicateGroup. No todas las copias
        # pesan lo mismo, así que damos el tamaño de la mejor.
        return self.files[0].size

    @property
    def reclaimable_space(self) -> int:
        return sum(a.size for a in self.files[1:])


@dataclass
class SimilarResult:
    groups: list[SimilarGroup]
    total_images: int
    errors: list[tuple[str, str]] = field(default_factory=list)   # (ruta, mensaje)
    total_excluded: int = 0

    @property
    def total_groups(self) -> int:
        return len(self.groups)

    @property
    def total_photos_in_groups(self) -> int:
        return sum(g.count for g in self.groups)

    @property
    def extra_copies(self) -> int:
        return sum(g.count - 1 for g in self.groups)

    @property
    def total_reclaimable_space(self) -> int:
        return sum(g.reclaimable_space for g in self.groups)


# ----------------------------------------------------------------------
# Huella de una imagen
# ----------------------------------------------------------------------
def _load_thumbnails(
    path: str,
) -> tuple[list[int], list[tuple[int, int, int]], tuple[int, int]]:
    """Abre la imagen una sola vez y devuelve (gris_9x8, rgb_4x4, (w, h))."""
    with Image.open(path) as im:
        width, height = im.size          # tamaño real, antes de tocar nada
        # draft acelera muchísimo el decode de JPEG grandes (pero cambia
        # im.size, por eso se lee antes).
        try:
            im.draft("L", (64, 64))
        except (ValueError, OSError):  # draft es opcional: si no se puede, se decodifica entero
            pass
        upright = ImageOps.exif_transpose(im)     # respeta la orientación EXIF
        gray = upright.convert("L").resize(
            (_DHASH_SIDE + 1, _DHASH_SIDE), Image.Resampling.BOX)
        rgb = upright.convert("RGB").resize(
            (_COLOR_SIDE, _COLOR_SIDE), Image.Resampling.BOX)
    # Pillow devuelve un tipo amplio (según el modo de la imagen); aquí sabemos
    # que «L» da enteros y «RGB» da tuplas (r, g, b).
    gray_data = cast(tuple[int, ...], gray.get_flattened_data())
    rgb_data = cast(tuple[tuple[int, int, int], ...], rgb.get_flattened_data())
    return list(gray_data), list(rgb_data), (width, height)


def compute_fingerprint(path: str) -> ImageFingerprint:
    """ImageFingerprint de `ruta`. Lanza OSError/Image errors si no se puede abrir."""
    gray, rgb, (width, height) = _load_thumbnails(path)

    # dHash: en una miniatura de 9x8 en gris, por cada fila comparamos
    # cada píxel con el de su derecha. Sale 1 si "sube" el brillo, 0 si
    # "baja". 8 comparaciones por fila x 8 filas = 64 bits. Lo que mide
    # es la forma de la imagen, no los colores, por eso aguanta bien la
    # recompresión y los filtros.
    width_g = _DHASH_SIDE + 1        # la miniatura tiene 1 columna extra
    bits = 0
    for row in range(_DHASH_SIDE):
        base = row * width_g       # primer píxel de esta fila en la lista plana
        for col in range(_DHASH_SIDE):
            left = gray[base + col]
            right = gray[base + col + 1]
            # desplaza el hash una posición e mete el bit nuevo al final
            bits = (bits << 1) | (1 if left < right else 0)

    try:
        size = os.path.getsize(path)
    except OSError:
        size = 0

    return ImageFingerprint(
        path=path, size=size, width=width, height=height,
        dhash=bits, color=tuple(rgb),
    )


def hamming_distance(a: int, b: int) -> int:
    # XOR pone a 1 los bits en los que a y b difieren; contamos esos unos.
    # 0 = hash idéntico; 64 = opuestos por completo.
    return bin(a ^ b).count("1")


def color_distance(c1: Sequence[Sequence[int]], c2: Sequence[Sequence[int]]) -> float:
    """Media de la diferencia por canal entre dos firmas de color (0..255)."""
    total = 0
    for (r1, g1, b1), (r2, g2, b2) in zip(c1, c2):
        total += abs(r1 - r2) + abs(g1 - g2) + abs(b1 - b2)
    return total / (len(c1) * 3)


# ----------------------------------------------------------------------
# BK-tree: árbol para buscar "los que están a menos de N de distancia"
# sin comparar todos contra todos. Cada nodo guarda una clave (un dHash)
# y sus hijos van etiquetados por la distancia exacta a ese nodo.
# ----------------------------------------------------------------------
type _Node = tuple[int, int, dict[int, _Node]]      # (clave, índice, {distancia: subnodo})


class _BKTree:
    def __init__(self) -> None:
        self._root: _Node | None = None

    def add(self, key: int, index: int) -> None:
        if self._root is None:
            self._root = (key, index, {})
            return
        node = self._root
        while True:
            d = hamming_distance(key, node[0])
            child = node[2].get(d)
            if child is None:
                # no hay hijo a esa distancia exacta: aquí va el nuevo
                node[2][d] = (key, index, {})
                return
            node = child          # ya había uno: seguimos bajando por él

    def neighbors(self, key: int, radius: int) -> list[int]:
        """Índices cuyas claves están a <= `radio` de `clave`."""
        if self._root is None:
            return []
        output: list[int] = []
        stack: list[_Node] = [self._root]
        while stack:
            node = stack.pop()
            d = hamming_distance(key, node[0])
            if d <= radius:
                output.append(node[1])
            # Truco del BK-tree: solo puede haber vecinos en los hijos
            # cuya etiqueta de distancia esté en [d - radio, d + radio]
            # (desigualdad triangular). El resto se poda.
            for child_dist, child in node[2].items():
                if d - radius <= child_dist <= d + radius:
                    stack.append(child)
        return output


# ----------------------------------------------------------------------
# Union-Find (conjuntos disjuntos): para unir cadenas de parecidos.
# _padre[i] apunta a "otro del mismo grupo"; siguiendo la cadena se
# llega al representante del grupo.
# ----------------------------------------------------------------------
class _UnionFind:
    def __init__(self, n: int) -> None:
        self._parent = list(range(n))   # al principio cada uno es su propio grupo

    def root(self, x: int) -> int:
        # sube hasta el representante; de paso "aplana" la cadena para
        # que la próxima vez sea más corto (compresión de caminos).
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]
            x = self._parent[x]
        return x

    def join(self, a: int, b: int) -> None:
        ra, rb = self.root(a), self.root(b)
        if ra != rb:
            self._parent[ra] = rb       # cuelga un grupo del otro

    def groups(self) -> list[list[int]]:
        # agrupa los índices por su representante
        by_root: dict[int, list[int]] = {}
        for i in range(len(self._parent)):
            by_root.setdefault(self.root(i), []).append(i)
        return list(by_root.values())


# ----------------------------------------------------------------------
# API principal
# ----------------------------------------------------------------------
def list_images(root_folder: str, filter: ScanFilter | None = None) -> list[str]:
    """Rutas de archivos de imagen bajo `carpeta_raiz` (recursivo).

    `filtro` es un ScanFilter opcional (se respetan sus carpetas y
    nombres excluidos; las extensiones se limitan siempre a imágenes).
    """
    paths: list[str] = []
    for current_dir, subdirs, names in os.walk(root_folder):
        if filter is not None:
            subdirs[:] = [d for d in subdirs if not filter.excludes_folder(d)]
        for name in names:
            ext = os.path.splitext(name)[1].lower().lstrip(".")
            if ext not in IMAGE_EXTENSIONS:
                continue
            if filter is not None and name.lower() in filter.excluded_names:
                continue
            paths.append(os.path.join(current_dir, name))
    return paths


def group_similar(
    paths: list[str],
    hamming_threshold: int = 10,
    color_threshold: float = 32,
    progress: ProgressCallback | None = None,
    cancelled: CancelledCallback | None = None,
) -> SimilarResult:
    """Agrupa las imágenes de `rutas` por parecido visual.

    umbral_hamming : 0..64. Más alto = más tolerante (junta más).
                     ~6 estricto, ~10 normal, ~16 muy tolerante.
    umbral_color   : 0..255. Diferencia media de color permitida.
    progreso       : callable(actual, total, mensaje) opcional.
    cancelado      : callable() -> bool opcional.
    """
    progress = progress or (lambda *_: None)
    cancelled = cancelled or (lambda: False)

    # 1) Calcular la huella (dHash + color) de cada imagen. Las que no se
    #    puedan abrir van a `errores` y no rompen el análisis.
    fingerprints: list[ImageFingerprint] = []
    errors: list[tuple[str, str]] = []
    total = len(paths)
    for i, path in enumerate(paths, 1):
        if cancelled():
            raise ComparisonCancelled()
        if i % 25 == 0 or i == total:
            progress(i, total, f"Analizando imágenes… ({i}/{total})")
        try:
            fingerprints.append(compute_fingerprint(path))
        except Exception as e:  # un archivo roto o raro no debe parar el análisis entero
            log.info("No se pudo analizar la imagen %s: %s", path, e)
            errors.append((path, str(e)))

    # 2) Meter todos los dHash en un BK-tree para buscar vecinos rápido.
    tree = _BKTree()
    for idx, h in enumerate(fingerprints):
        tree.add(h.dhash, idx)

    # 3) Por cada imagen, buscar sus vecinos por estructura (Hamming) y,
    #    si además el color encaja, unirlas en el mismo grupo.
    uf = _UnionFind(len(fingerprints))
    for idx, h in enumerate(fingerprints):
        if cancelled():
            raise ComparisonCancelled()
        for neighbor in tree.neighbors(h.dhash, hamming_threshold):
            if neighbor == idx:
                continue
            if color_distance(h.color, fingerprints[neighbor].color) <= color_threshold:
                uf.join(idx, neighbor)

    # 4) Armar los grupos finales (solo los de 2+ fotos).
    groups: list[SimilarGroup] = []
    for indices in uf.groups():
        if len(indices) < 2:
            continue
        members = [fingerprints[i] for i in indices]
        # La "mejor" copia: más megapíxeles; a igualdad, formato sin
        # pérdida antes que JPEG; y a igualdad, archivo más grande.
        members.sort(
            key=lambda h: (h.width * h.height, _is_lossless(h.path), h.size),
            reverse=True)
        best = members[0]
        similarity = [
            1.0 - hamming_distance(m.dhash, best.dhash) / 64.0
            for m in members
        ]
        groups.append(SimilarGroup(
            fingerprints=members,
            files=[DuplicateFile(m.path, m.size) for m in members],
            similarity=similarity,
        ))

    # Los grupos que más espacio liberan, primero.
    groups.sort(key=lambda g: -g.reclaimable_space)

    progress(total, total, "Comparación terminada.")
    return SimilarResult(
        groups=groups,
        total_images=len(fingerprints),
        errors=errors,
    )


def analyze_folder(
    root_folder: str,
    hamming_threshold: int = 10,
    color_threshold: float = 32,
    filter: ScanFilter | None = None,
    progress: ProgressCallback | None = None,
    cancelled: CancelledCallback | None = None,
) -> SimilarResult:
    """Atajo: listar imágenes de una carpeta y agruparlas por parecido."""
    if not os.path.isdir(root_folder):
        raise NotADirectoryError(f"No es una carpeta: {root_folder}")
    paths = list_images(root_folder, filter=filter)
    return group_similar(
        paths, hamming_threshold=hamming_threshold, color_threshold=color_threshold,
        progress=progress, cancelled=cancelled)
