"""Escaneo recursivo de una carpeta en busca de archivos duplicados.

Este módulo SOLO LEE el sistema de archivos. No mueve, renombra ni
borra nada.

El escaneo va en pasadas, de lo más barato a lo más caro:

  Pasada 1  -  agrupar todos los archivos por tamaño en bytes.
               Un archivo con un tamaño único no puede tener duplicados,
               así que se descarta sin leer su contenido.

  Pasada 2  -  para los que comparten tamaño, calcular el hash de los
               primeros 64 KB (hash parcial). Rápido y descarta casi
               todos los falsos positivos.

  Pasada 3  -  para los que además comparten hash parcial, calcular el
               hash del archivo completo. Los que aquí coinciden son
               duplicados reales byte a byte.

El resultado es una lista de `GrupoDuplicado`, cada uno con 2 o más
archivos de contenido idéntico.
"""

import os
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field

from .hashing import hash_parcial, hash_completo, TAMANO_HASH_PARCIAL
from .filtros import FiltroEscaneo


class EscaneoCancelado(Exception):
    """Se lanza cuando el que llama pide cancelar el escaneo a mitad."""


@dataclass
class ArchivoDup:
    """Un archivo concreto dentro de un grupo de duplicados."""

    ruta: str
    tamano: int


@dataclass
class GrupoDuplicado:
    """Conjunto de 2+ archivos con contenido idéntico."""

    hash: str          # el hash que comparten (identifica el grupo)
    tamano: int        # bytes de cada copia (todas pesan lo mismo)
    archivos: list[ArchivoDup]   # las copias del grupo

    @property
    def cantidad(self) -> int:
        return len(self.archivos)

    @property
    def espacio_recuperable(self) -> int:
        """Bytes que se liberarían si se conservara solo una copia."""
        return self.tamano * (len(self.archivos) - 1)


@dataclass
class ResultadoEscaneo:
    """Todo lo que produjo un escaneo."""

    grupos: list[GrupoDuplicado]
    total_archivos: int
    errores: list[tuple[str, str]] = field(default_factory=list)  # (ruta, mensaje)
    total_excluidos: int = 0  # archivos saltados por el filtro

    @property
    def total_grupos(self) -> int:
        return len(self.grupos)

    def resumen_por_extension(self) -> list[tuple[str, int, int]]:
        """Desglose de los archivos duplicados por extensión.

        Devuelve una lista de tuplas (extension, cantidad, bytes),
        ordenada de mayor a menor espacio ocupado. Útil para que el
        usuario decida qué tipos agregar al filtro de exclusión.
        """
        # acc[extension] = [cantidad, bytes_totales]
        acc: defaultdict[str, list[int]] = defaultdict(lambda: [0, 0])
        for g in self.grupos:
            for a in g.archivos:
                ext = os.path.splitext(a.ruta)[1].lower().lstrip(".")
                clave = ext if ext else "(sin extensión)"
                acc[clave][0] += 1
                acc[clave][1] += a.tamano
        filas = [(ext, c, b) for ext, (c, b) in acc.items()]
        filas.sort(key=lambda f: (-f[2], f[0]))   # más bytes primero; a igualdad, alfabético
        return filas

    @property
    def total_archivos_duplicados(self) -> int:
        """Cantidad de archivos que están en algún grupo de duplicados."""
        return sum(g.cantidad for g in self.grupos)

    @property
    def copias_sobrantes(self) -> int:
        """Archivos que se podrían mover (todas las copias menos una por grupo)."""
        return sum(g.cantidad - 1 for g in self.grupos)

    @property
    def espacio_recuperable_total(self) -> int:
        return sum(g.espacio_recuperable for g in self.grupos)


@dataclass
class Progreso:
    """Notificación de avance para que la interfaz muestre una barra.

    fase:
      "tamanos"        -> Pasada 1, contando y midiendo archivos.
      "hash_parcial"   -> Pasada 2, hasheando los primeros 64 KB.
      "hash_completo"  -> Pasada 3, hasheando archivos completos.
    total == 0 significa "todavía no sé cuántos hay en total" (Pasada 1).
    """

    fase: str
    actual: int
    total: int
    mensaje: str


def _noop(*_args: object, **_kwargs: object) -> None:
    return None


def _nunca_cancelar() -> bool:
    return False


def _pasada_tamanos(
    carpeta_raiz: str,
    filtro: FiltroEscaneo,
    progreso: Callable[[Progreso], None],
    cancelado: Callable[[], bool],
    errores: list[tuple[str, str]],
) -> tuple[dict[int, list[str]], int, int]:
    """Pasada 1: recorre el árbol y agrupa los archivos por tamaño en bytes.

    Devuelve (rutas_por_tamano, total_archivos, total_excluidos). Los archivos
    que el filtro excluye ni se miden ni cuentan como revisados.
    """
    por_tamano: defaultdict[int, list[str]] = defaultdict(list)
    total_archivos = 0
    total_excluidos = 0

    for dir_actual, subdirs, nombres in os.walk(carpeta_raiz):
        if cancelado():
            raise EscaneoCancelado()

        # Podar carpetas excluidas: os.walk no entra en las que quitamos aquí.
        subdirs[:] = [d for d in subdirs if not filtro.excluye_carpeta(d)]

        for nombre in nombres:
            if filtro.excluye_nombre(nombre):
                total_excluidos += 1
                continue

            ruta = os.path.join(dir_actual, nombre)
            try:
                if not os.path.isfile(ruta):
                    # enlaces simbólicos rotos, dispositivos, etc.
                    continue
                tamano = os.path.getsize(ruta)
            except OSError as e:
                errores.append((ruta, str(e)))
                continue

            if filtro.excluye_tamano(tamano):
                total_excluidos += 1
                continue

            total_archivos += 1
            por_tamano[tamano].append(ruta)

            if total_archivos % 200 == 0:
                progreso(Progreso(
                    "tamanos", total_archivos, 0,
                    f"Paso 1/2: revisando tamaños... ({total_archivos} archivos)",
                ))

    return por_tamano, total_archivos, total_excluidos


def _pasada_hash_parcial(
    candidatos_por_tamano: dict[int, list[str]],
    progreso: Callable[[Progreso], None],
    cancelado: Callable[[], bool],
    errores: list[tuple[str, str]],
) -> dict[tuple[int, str], list[str]]:
    """Pasada 2: hash de los primeros 64 KB de los archivos que comparten tamaño.

    Devuelve solo los «finalistas»: las claves (tamaño, hash_parcial) que
    comparten 2 o más archivos.
    """
    total_candidatos = sum(len(r) for r in candidatos_por_tamano.values())
    por_parcial: defaultdict[tuple[int, str], list[str]] = defaultdict(list)
    procesados = 0

    for tamano, rutas in candidatos_por_tamano.items():
        for ruta in rutas:
            if cancelado():
                raise EscaneoCancelado()
            procesados += 1
            try:
                hp = hash_parcial(ruta)
            except OSError as e:
                errores.append((ruta, str(e)))
                continue
            # La clave incluye el tamaño: dos archivos con el mismo hash
            # parcial pero distinto tamaño nunca son el mismo archivo.
            por_parcial[(tamano, hp)].append(ruta)

            if procesados % 50 == 0:
                progreso(Progreso(
                    "hash_parcial", procesados, total_candidatos,
                    f"Paso 2/2: calculando hashes... "
                    f"({procesados}/{total_candidatos})",
                ))

    return {clave: rutas for clave, rutas in por_parcial.items() if len(rutas) > 1}


def _pasada_hash_completo(
    finalistas: dict[tuple[int, str], list[str]],
    progreso: Callable[[Progreso], None],
    cancelado: Callable[[], bool],
    errores: list[tuple[str, str]],
) -> list[GrupoDuplicado]:
    """Pasada 3: hash del archivo entero de los finalistas.

    Los que coinciden aquí son duplicados reales, byte a byte. Si un archivo
    pesa menos de 64 KB, su hash parcial ya cubrió todo el contenido y esta
    pasada se salta para él.
    """
    total_finalistas = sum(len(r) for r in finalistas.values())
    grupos: list[GrupoDuplicado] = []
    procesados_completo = 0

    for (tamano, hp), rutas in finalistas.items():
        if tamano <= TAMANO_HASH_PARCIAL:
            # El hash parcial ya cubrió el archivo entero: son idénticos.
            grupos.append(GrupoDuplicado(
                hash=hp,
                tamano=tamano,
                archivos=[ArchivoDup(r, tamano) for r in rutas],
            ))
            continue

        por_completo: defaultdict[str, list[str]] = defaultdict(list)
        for ruta in rutas:
            if cancelado():
                raise EscaneoCancelado()
            procesados_completo += 1
            try:
                hc = hash_completo(ruta)
            except OSError as e:
                errores.append((ruta, str(e)))
                continue
            por_completo[hc].append(ruta)

            if procesados_completo % 50 == 0:
                progreso(Progreso(
                    "hash_completo", procesados_completo, total_finalistas,
                    f"Paso 2/2: verificando archivos completos... "
                    f"({procesados_completo}/{total_finalistas})",
                ))

        for hc, rutas_iguales in por_completo.items():
            if len(rutas_iguales) > 1:
                grupos.append(GrupoDuplicado(
                    hash=hc,
                    tamano=tamano,
                    archivos=[ArchivoDup(r, tamano) for r in rutas_iguales],
                ))

    return grupos


def escanear(
    carpeta_raiz: str,
    progreso: Callable[[Progreso], None] | None = None,
    cancelado: Callable[[], bool] | None = None,
    filtro: FiltroEscaneo | None = None,
) -> ResultadoEscaneo:
    """Escanea `carpeta_raiz` recursivamente y devuelve un ResultadoEscaneo.

    progreso : callable(Progreso) opcional, se llama para informar avance.
    cancelado: callable() -> bool opcional. Si en algún momento devuelve
               True, el escaneo aborta lanzando EscaneoCancelado.
    filtro   : FiltroEscaneo opcional. Los archivos y carpetas que excluye
               ni se leen ni se cuentan como revisados.

    El trabajo está repartido en tres funciones, una por pasada
    (_pasada_tamanos, _pasada_hash_parcial y _pasada_hash_completo); esta
    solo las encadena y ordena el resultado.
    """
    progreso = progreso or _noop
    cancelado = cancelado or _nunca_cancelar
    if filtro is None:
        filtro = FiltroEscaneo.sin_filtro()

    if not os.path.isdir(carpeta_raiz):
        raise NotADirectoryError(f"No es una carpeta: {carpeta_raiz}")

    errores: list[tuple[str, str]] = []

    # Pasada 1: agrupar por tamaño. Solo siguen los tamaños compartidos por 2+ archivos.
    por_tamano, total_archivos, total_excluidos = _pasada_tamanos(
        carpeta_raiz, filtro, progreso, cancelado, errores)
    candidatos_por_tamano = {t: rutas for t, rutas in por_tamano.items() if len(rutas) > 1}

    # Pasada 2: hash de los primeros 64 KB. Solo siguen los que además coinciden.
    finalistas = _pasada_hash_parcial(candidatos_por_tamano, progreso, cancelado, errores)

    # Pasada 3: hash completo de los finalistas.
    grupos = _pasada_hash_completo(finalistas, progreso, cancelado, errores)

    # Orden estable y útil: primero los grupos que liberan más espacio,
    # y dentro de cada grupo, los archivos por ruta.
    for g in grupos:
        g.archivos.sort(key=lambda a: a.ruta)
    grupos.sort(key=lambda g: (-g.espacio_recuperable, g.archivos[0].ruta))

    total_finalistas = sum(len(r) for r in finalistas.values())
    progreso(Progreso(
        "hash_completo", max(total_finalistas, 1), max(total_finalistas, 1),
        "Escaneo terminado.",
    ))

    return ResultadoEscaneo(
        grupos=grupos,
        total_archivos=total_archivos,
        errores=errores,
        total_excluidos=total_excluidos,
    )
