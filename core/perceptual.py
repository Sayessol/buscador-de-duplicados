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

from .filtros import FiltroEscaneo
from .registro import log
from .scanner import ArchivoDup
from .tipos import FuncCancelado, FuncProgreso

# Firma de color: una tupla de colores (r, g, b), uno por celda de la cuadrícula de 4×4.
Color = tuple[tuple[int, int, int], ...]

# Extensiones que Pillow abre sin plugins extra.
EXTENSIONES_IMAGEN = {
    "jpg", "jpeg", "jpe", "png", "gif", "bmp", "webp",
    "tif", "tiff", "ppm", "pgm",
}
# HEIC/HEIF quedan fuera: Pillow no los abre sin pillow-heif.

_LADO_DHASH = 8            # -> hash de 8*8 = 64 bits
_LADO_COLOR = 4            # -> firma de 4*4 celdas RGB

# Formatos sin pérdida: a igualdad de resolución se prefieren como
# "mejor copia" (suelen ser el archivo original, no un reguardado).
_EXT_SIN_PERDIDA = {"png", "tif", "tiff", "bmp", "ppm", "pgm"}


def _es_sin_perdida(ruta: str) -> bool:
    return os.path.splitext(ruta)[1].lower().lstrip(".") in _EXT_SIN_PERDIDA


class ComparacionCancelada(Exception):
    """El que llama pidió abortar a mitad."""


@dataclass
class HuellaImagen:
    ruta: str
    tamano: int
    ancho: int
    alto: int
    dhash: int
    color: Color  # longitud _LADO_COLOR**2

    @property
    def megapixeles(self) -> float:
        return (self.ancho * self.alto) / 1_000_000


@dataclass
class GrupoParecidas:
    """Conjunto de 2+ imágenes visualmente parecidas.

    `archivos` son ArchivoDup (ruta + tamaño) para poder reutilizar tal
    cual la selección conservar/mover y el movimiento a cuarentena.
    `huellas` lleva los datos extra (resolución, similitud) para la
    interfaz. Ambas listas van en el mismo orden; la primera es la
    "mejor" copia (más resolución, y a igualdad, archivo más grande).
    """

    huellas: list[HuellaImagen]
    archivos: list[ArchivoDup]      # mismo orden que huellas
    similitud: list[float]          # 0..1 de cada foto respecto a la mejor

    @property
    def cantidad(self) -> int:
        return len(self.archivos)

    @property
    def tamano(self) -> int:
        # Para compatibilidad con GrupoDuplicado. No todas las copias
        # pesan lo mismo, así que damos el tamaño de la mejor.
        return self.archivos[0].tamano

    @property
    def espacio_recuperable(self) -> int:
        return sum(a.tamano for a in self.archivos[1:])


@dataclass
class ResultadoParecidas:
    grupos: list[GrupoParecidas]
    total_imagenes: int
    errores: list[tuple[str, str]] = field(default_factory=list)   # (ruta, mensaje)
    total_excluidas: int = 0

    @property
    def total_grupos(self) -> int:
        return len(self.grupos)

    @property
    def total_fotos_en_grupos(self) -> int:
        return sum(g.cantidad for g in self.grupos)

    @property
    def copias_sobrantes(self) -> int:
        return sum(g.cantidad - 1 for g in self.grupos)

    @property
    def espacio_recuperable_total(self) -> int:
        return sum(g.espacio_recuperable for g in self.grupos)


# ----------------------------------------------------------------------
# Huella de una imagen
# ----------------------------------------------------------------------
def _cargar_miniaturas(
    ruta: str,
) -> tuple[list[int], list[tuple[int, int, int]], tuple[int, int]]:
    """Abre la imagen una sola vez y devuelve (gris_9x8, rgb_4x4, (w, h))."""
    with Image.open(ruta) as im:
        ancho, alto = im.size          # tamaño real, antes de tocar nada
        # draft acelera muchísimo el decode de JPEG grandes (pero cambia
        # im.size, por eso se lee antes).
        try:
            im.draft("L", (64, 64))
        except (ValueError, OSError):  # draft es opcional: si no se puede, se decodifica entero
            pass
        derecha = ImageOps.exif_transpose(im)     # respeta la orientación EXIF
        gris = derecha.convert("L").resize(
            (_LADO_DHASH + 1, _LADO_DHASH), Image.Resampling.BOX)
        rgb = derecha.convert("RGB").resize(
            (_LADO_COLOR, _LADO_COLOR), Image.Resampling.BOX)
    # Pillow devuelve un tipo amplio (según el modo de la imagen); aquí sabemos
    # que «L» da enteros y «RGB» da tuplas (r, g, b).
    datos_gris = cast(tuple[int, ...], gris.get_flattened_data())
    datos_rgb = cast(tuple[tuple[int, int, int], ...], rgb.get_flattened_data())
    return list(datos_gris), list(datos_rgb), (ancho, alto)


def calcular_huella(ruta: str) -> HuellaImagen:
    """HuellaImagen de `ruta`. Lanza OSError/Image errors si no se puede abrir."""
    gris, rgb, (ancho, alto) = _cargar_miniaturas(ruta)

    # dHash: en una miniatura de 9x8 en gris, por cada fila comparamos
    # cada píxel con el de su derecha. Sale 1 si "sube" el brillo, 0 si
    # "baja". 8 comparaciones por fila x 8 filas = 64 bits. Lo que mide
    # es la forma de la imagen, no los colores, por eso aguanta bien la
    # recompresión y los filtros.
    ancho_g = _LADO_DHASH + 1        # la miniatura tiene 1 columna extra
    bits = 0
    for fila in range(_LADO_DHASH):
        base = fila * ancho_g       # primer píxel de esta fila en la lista plana
        for col in range(_LADO_DHASH):
            izq = gris[base + col]
            der = gris[base + col + 1]
            # desplaza el hash una posición e mete el bit nuevo al final
            bits = (bits << 1) | (1 if izq < der else 0)

    try:
        tamano = os.path.getsize(ruta)
    except OSError:
        tamano = 0

    return HuellaImagen(
        ruta=ruta, tamano=tamano, ancho=ancho, alto=alto,
        dhash=bits, color=tuple(rgb),
    )


def distancia_hamming(a: int, b: int) -> int:
    # XOR pone a 1 los bits en los que a y b difieren; contamos esos unos.
    # 0 = hash idéntico; 64 = opuestos por completo.
    return bin(a ^ b).count("1")


def distancia_color(c1: Sequence[Sequence[int]], c2: Sequence[Sequence[int]]) -> float:
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
type _Nodo = tuple[int, int, dict[int, _Nodo]]      # (clave, índice, {distancia: subnodo})


class _BKTree:
    def __init__(self) -> None:
        self._raiz: _Nodo | None = None

    def agregar(self, clave: int, indice: int) -> None:
        if self._raiz is None:
            self._raiz = (clave, indice, {})
            return
        nodo = self._raiz
        while True:
            d = distancia_hamming(clave, nodo[0])
            hijo = nodo[2].get(d)
            if hijo is None:
                # no hay hijo a esa distancia exacta: aquí va el nuevo
                nodo[2][d] = (clave, indice, {})
                return
            nodo = hijo          # ya había uno: seguimos bajando por él

    def vecinos(self, clave: int, radio: int) -> list[int]:
        """Índices cuyas claves están a <= `radio` de `clave`."""
        if self._raiz is None:
            return []
        salida: list[int] = []
        pila: list[_Nodo] = [self._raiz]
        while pila:
            nodo = pila.pop()
            d = distancia_hamming(clave, nodo[0])
            if d <= radio:
                salida.append(nodo[1])
            # Truco del BK-tree: solo puede haber vecinos en los hijos
            # cuya etiqueta de distancia esté en [d - radio, d + radio]
            # (desigualdad triangular). El resto se poda.
            for dist_hijo, hijo in nodo[2].items():
                if d - radio <= dist_hijo <= d + radio:
                    pila.append(hijo)
        return salida


# ----------------------------------------------------------------------
# Union-Find (conjuntos disjuntos): para unir cadenas de parecidos.
# _padre[i] apunta a "otro del mismo grupo"; siguiendo la cadena se
# llega al representante del grupo.
# ----------------------------------------------------------------------
class _UnionFind:
    def __init__(self, n: int) -> None:
        self._padre = list(range(n))   # al principio cada uno es su propio grupo

    def raiz(self, x: int) -> int:
        # sube hasta el representante; de paso "aplana" la cadena para
        # que la próxima vez sea más corto (compresión de caminos).
        while self._padre[x] != x:
            self._padre[x] = self._padre[self._padre[x]]
            x = self._padre[x]
        return x

    def unir(self, a: int, b: int) -> None:
        ra, rb = self.raiz(a), self.raiz(b)
        if ra != rb:
            self._padre[ra] = rb       # cuelga un grupo del otro

    def grupos(self) -> list[list[int]]:
        # agrupa los índices por su representante
        de_raiz: dict[int, list[int]] = {}
        for i in range(len(self._padre)):
            de_raiz.setdefault(self.raiz(i), []).append(i)
        return list(de_raiz.values())


# ----------------------------------------------------------------------
# API principal
# ----------------------------------------------------------------------
def listar_imagenes(carpeta_raiz: str, filtro: FiltroEscaneo | None = None) -> list[str]:
    """Rutas de archivos de imagen bajo `carpeta_raiz` (recursivo).

    `filtro` es un FiltroEscaneo opcional (se respetan sus carpetas y
    nombres excluidos; las extensiones se limitan siempre a imágenes).
    """
    rutas: list[str] = []
    for dir_actual, subdirs, nombres in os.walk(carpeta_raiz):
        if filtro is not None:
            subdirs[:] = [d for d in subdirs if not filtro.excluye_carpeta(d)]
        for nombre in nombres:
            ext = os.path.splitext(nombre)[1].lower().lstrip(".")
            if ext not in EXTENSIONES_IMAGEN:
                continue
            if filtro is not None and nombre.lower() in filtro.nombres_excluidos:
                continue
            rutas.append(os.path.join(dir_actual, nombre))
    return rutas


def agrupar_parecidas(
    rutas: list[str],
    umbral_hamming: int = 10,
    umbral_color: float = 32,
    progreso: FuncProgreso | None = None,
    cancelado: FuncCancelado | None = None,
) -> ResultadoParecidas:
    """Agrupa las imágenes de `rutas` por parecido visual.

    umbral_hamming : 0..64. Más alto = más tolerante (junta más).
                     ~6 estricto, ~10 normal, ~16 muy tolerante.
    umbral_color   : 0..255. Diferencia media de color permitida.
    progreso       : callable(actual, total, mensaje) opcional.
    cancelado      : callable() -> bool opcional.
    """
    progreso = progreso or (lambda *_: None)
    cancelado = cancelado or (lambda: False)

    # 1) Calcular la huella (dHash + color) de cada imagen. Las que no se
    #    puedan abrir van a `errores` y no rompen el análisis.
    huellas: list[HuellaImagen] = []
    errores: list[tuple[str, str]] = []
    total = len(rutas)
    for i, ruta in enumerate(rutas, 1):
        if cancelado():
            raise ComparacionCancelada()
        if i % 25 == 0 or i == total:
            progreso(i, total, f"Analizando imágenes… ({i}/{total})")
        try:
            huellas.append(calcular_huella(ruta))
        except Exception as e:  # un archivo roto o raro no debe parar el análisis entero
            log.info("No se pudo analizar la imagen %s: %s", ruta, e)
            errores.append((ruta, str(e)))

    # 2) Meter todos los dHash en un BK-tree para buscar vecinos rápido.
    arbol = _BKTree()
    for idx, h in enumerate(huellas):
        arbol.agregar(h.dhash, idx)

    # 3) Por cada imagen, buscar sus vecinos por estructura (Hamming) y,
    #    si además el color encaja, unirlas en el mismo grupo.
    uf = _UnionFind(len(huellas))
    for idx, h in enumerate(huellas):
        if cancelado():
            raise ComparacionCancelada()
        for vecino in arbol.vecinos(h.dhash, umbral_hamming):
            if vecino == idx:
                continue
            if distancia_color(h.color, huellas[vecino].color) <= umbral_color:
                uf.unir(idx, vecino)

    # 4) Armar los grupos finales (solo los de 2+ fotos).
    grupos: list[GrupoParecidas] = []
    for indices in uf.grupos():
        if len(indices) < 2:
            continue
        miembros = [huellas[i] for i in indices]
        # La "mejor" copia: más megapíxeles; a igualdad, formato sin
        # pérdida antes que JPEG; y a igualdad, archivo más grande.
        miembros.sort(
            key=lambda h: (h.ancho * h.alto, _es_sin_perdida(h.ruta), h.tamano),
            reverse=True)
        mejor = miembros[0]
        similitud = [
            1.0 - distancia_hamming(m.dhash, mejor.dhash) / 64.0
            for m in miembros
        ]
        grupos.append(GrupoParecidas(
            huellas=miembros,
            archivos=[ArchivoDup(m.ruta, m.tamano) for m in miembros],
            similitud=similitud,
        ))

    # Los grupos que más espacio liberan, primero.
    grupos.sort(key=lambda g: -g.espacio_recuperable)

    progreso(total, total, "Comparación terminada.")
    return ResultadoParecidas(
        grupos=grupos,
        total_imagenes=len(huellas),
        errores=errores,
    )


def analizar_carpeta(
    carpeta_raiz: str,
    umbral_hamming: int = 10,
    umbral_color: float = 32,
    filtro: FiltroEscaneo | None = None,
    progreso: FuncProgreso | None = None,
    cancelado: FuncCancelado | None = None,
) -> ResultadoParecidas:
    """Atajo: listar imágenes de una carpeta y agruparlas por parecido."""
    if not os.path.isdir(carpeta_raiz):
        raise NotADirectoryError(f"No es una carpeta: {carpeta_raiz}")
    rutas = listar_imagenes(carpeta_raiz, filtro=filtro)
    return agrupar_parecidas(
        rutas, umbral_hamming=umbral_hamming, umbral_color=umbral_color,
        progreso=progreso, cancelado=cancelado)
