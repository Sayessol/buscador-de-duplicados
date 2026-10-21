"""Qué copia se conserva y cuáles se mueven, en cada grupo de duplicados.

La `SeleccionDuplicados` es el "estado editable" que hay entre el
resultado del escaneo (inmutable) y el paso de mover a cuarentena.

Regla que impone la app: al mover, cada grupo debe quedar con
**exactamente una** copia marcada como CONSERVAR. Mientras eso no se
cumpla en todos los grupos, no se puede mover nada.

Estado inicial: todo en CONSERVAR (es decir, no se movería nada). Así
la app nunca "propone mover" algo sin que el usuario lo decida, ya sea
a mano o aplicando la regla de carpeta preferida.
"""

import os
import re
from collections.abc import Sequence
from typing import Protocol

from .scanner import ArchivoDup

CONSERVAR = "conservar"
MOVER = "mover"

# Nombres que "huelen" a copia y no al original.
_PARECE_COPIA = re.compile(
    r"cop(?:y|ia)\b|duplicad|\bnew\b|\(\d+\)|[ _-]copy|[ _-]copia|[ _-]\d+$",
    re.IGNORECASE)

# Estados posibles de un grupo respecto de la regla "una sola copia".
GRUPO_OK = "ok"                 # exactamente una copia en CONSERVAR
GRUPO_SIN_CONSERVAR = "sin_conservar"   # ninguna copia en CONSERVAR
GRUPO_MULTIPLE = "multiple"     # dos o más copias en CONSERVAR (sin decidir)


def _dentro_de(ruta: str, carpeta: str) -> bool:
    """True si `ruta` está dentro de `carpeta` (comparación normalizada)."""
    try:
        ruta_abs = os.path.normcase(os.path.abspath(ruta))
        carpeta_abs = os.path.normcase(os.path.abspath(carpeta))
    except (OSError, ValueError):
        return False
    if carpeta_abs.endswith(os.sep):
        carpeta_abs = carpeta_abs.rstrip(os.sep)
    return ruta_abs == carpeta_abs or ruta_abs.startswith(carpeta_abs + os.sep)


class _Grupo(Protocol):
    """Lo mínimo que se le pide a un grupo: una lista de archivos (los duplicados
    exactos y las fotos parecidas lo cumplen, por eso comparten esta clase)."""

    @property
    def archivos(self) -> list[ArchivoDup]: ...


class _Resultado(Protocol):
    """Lo mínimo que se le pide a un resultado: una lista de grupos."""

    @property
    def grupos(self) -> Sequence[_Grupo]: ...


class SeleccionDuplicados:
    def __init__(self, resultado: _Resultado) -> None:
        self.resultado = resultado
        # _decision[(indice_grupo, ruta)] -> CONSERVAR | MOVER
        self._decision: dict[tuple[int, str], str] = {}
        for gi, grupo in enumerate(resultado.grupos):
            for archivo in grupo.archivos:
                self._decision[(gi, archivo.ruta)] = CONSERVAR

    # ------------------------------------------------------------------
    # Consultas y cambios sobre un archivo
    # ------------------------------------------------------------------
    def decision(self, indice_grupo: int, ruta: str) -> str:
        return self._decision.get((indice_grupo, ruta), CONSERVAR)

    def marcar(self, indice_grupo: int, ruta: str, decision: str) -> None:
        assert decision in (CONSERVAR, MOVER)
        if (indice_grupo, ruta) in self._decision:
            self._decision[(indice_grupo, ruta)] = decision

    def alternar(self, indice_grupo: int, ruta: str) -> str:
        actual = self.decision(indice_grupo, ruta)
        nueva = MOVER if actual == CONSERVAR else CONSERVAR
        self.marcar(indice_grupo, ruta, nueva)
        return nueva

    def conservar_solo(self, indice_grupo: int, ruta_conservada: str) -> None:
        """Marca `ruta_conservada` como CONSERVAR y el resto del grupo como MOVER."""
        grupo = self.resultado.grupos[indice_grupo]
        for archivo in grupo.archivos:
            self.marcar(
                indice_grupo, archivo.ruta,
                CONSERVAR if archivo.ruta == ruta_conservada else MOVER,
            )

    # ------------------------------------------------------------------
    # Regla automática por carpeta preferida
    # ------------------------------------------------------------------
    def aplicar_regla_carpeta(self, carpeta_buena: str | None) -> tuple[int, int]:
        """Por cada grupo: si alguna copia está dentro de `carpeta_buena`,
        conserva esa (la de ruta más corta si hay varias) y marca el
        resto como MOVER. Si ninguna copia está dentro, el grupo se deja
        entero en CONSERVAR (queda "sin decidir" para que el usuario lo
        resuelva a mano).

        Devuelve (grupos_resueltos, grupos_sin_coincidencia).
        """
        carpeta_buena = (carpeta_buena or "").strip()
        resueltos = 0
        sin_coincidencia = 0

        for gi, grupo in enumerate(self.resultado.grupos):
            dentro = [a.ruta for a in grupo.archivos
                      if carpeta_buena and _dentro_de(a.ruta, carpeta_buena)]
            if dentro:
                conservada = min(dentro, key=len)
                self.conservar_solo(gi, conservada)
                resueltos += 1
            else:
                for a in grupo.archivos:
                    self.marcar(gi, a.ruta, CONSERVAR)
                sin_coincidencia += 1

        return resueltos, sin_coincidencia

    # ------------------------------------------------------------------
    # Estado de los grupos y validación global
    # ------------------------------------------------------------------
    def _conservadas_en(self, indice_grupo: int) -> list[ArchivoDup]:
        grupo = self.resultado.grupos[indice_grupo]
        return [a for a in grupo.archivos
                if self.decision(indice_grupo, a.ruta) == CONSERVAR]

    def estado_grupo(self, indice_grupo: int) -> str:
        n = len(self._conservadas_en(indice_grupo))
        if n == 1:
            return GRUPO_OK
        if n == 0:
            return GRUPO_SIN_CONSERVAR
        return GRUPO_MULTIPLE

    def grupos_pendientes(self) -> list[int]:
        return [gi for gi in range(len(self.resultado.grupos))
                if self.estado_grupo(gi) != GRUPO_OK]

    def todo_listo(self) -> bool:
        return not self.grupos_pendientes()

    # ------------------------------------------------------------------
    # Resumen de lo que se movería
    # ------------------------------------------------------------------
    def archivos_a_mover(self) -> list[tuple[int, ArchivoDup]]:
        """Lista de (indice_grupo, ArchivoDup) marcados como MOVER."""
        salida: list[tuple[int, ArchivoDup]] = []
        for gi, grupo in enumerate(self.resultado.grupos):
            for archivo in grupo.archivos:
                if self.decision(gi, archivo.ruta) == MOVER:
                    salida.append((gi, archivo))
        return salida

    def cantidad_a_mover(self) -> int:
        return len(self.archivos_a_mover())

    def espacio_a_liberar(self) -> int:
        return sum(a.tamano for _gi, a in self.archivos_a_mover())

    # ------------------------------------------------------------------
    # Preselección automática (modo Sencillo, o botón en Avanzado)
    # ------------------------------------------------------------------
    def preseleccionar_principales(self) -> None:
        """En cada grupo, conserva la copia "principal" y marca el resto
        para mover.

        Principal = la que menos parece una copia por el nombre, luego la
        menos anidada, luego la más antigua, luego la de ruta más corta.
        """
        for gi, grupo in enumerate(self.resultado.grupos):
            mejor = min(grupo.archivos, key=_puntua_principal)
            self.conservar_solo(gi, mejor.ruta)


def _puntua_principal(archivo: ArchivoDup) -> tuple[int, int, float, int]:
    """Puntuación para elegir la copia "principal": min() se queda con la
    tupla más pequeña, así que cada campo va de "mejor" (menor) a "peor".
    """
    ruta = archivo.ruta
    nombre = os.path.basename(ruta)
    parece_copia = 1 if _PARECE_COPIA.search(nombre) else 0  # 0 = no parece copia
    profundidad = os.path.normpath(ruta).count(os.sep)        # menos anidada, mejor
    try:
        mtime = os.path.getmtime(ruta)                        # más antigua, mejor
    except OSError:
        mtime = float("inf")
    return (parece_copia, profundidad, mtime, len(ruta))      # ruta más corta desempata
