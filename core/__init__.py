"""Núcleo de la app de duplicados: lógica pura, sin interfaz gráfica.

Todo lo de este paquete se puede probar por consola sin abrir ninguna
ventana. La regla de oro se mantiene en todas las funciones que tocan
el sistema de archivos: **nunca borrar, nunca modificar el original,
solo leer y (cuando el usuario lo confirma) mover.**
"""

# Única fuente de la versión: la usan la ventana y el nombre de la release.
# Al publicar una versión nueva, se cambia aquí y se añade su apartado en CHANGELOG.md
# (una prueba comprueba que los dos coinciden).
__version__ = "1.0.0"

from .hashing import (
    hash_parcial,
    hash_completo,
    formatear_tamano,
    TAMANO_BLOQUE,
    TAMANO_HASH_PARCIAL,
)
from .scanner import (
    ArchivoDup,
    GrupoDuplicado,
    ResultadoEscaneo,
    Progreso,
    EscaneoCancelado,
    escanear,
)
from .filtros import (
    FiltroEscaneo,
    parsear_extensiones,
    parsear_nombres,
    texto_de,
    EXTENSIONES_BASURA,
    NOMBRES_BASURA,
    CARPETAS_BASURA,
    CATEGORIAS_EXTENSIONES,
)
from .seleccion import (
    SeleccionDuplicados,
    CONSERVAR,
    MOVER,
    GRUPO_OK,
    GRUPO_SIN_CONSERVAR,
    GRUPO_MULTIPLE,
)
from .quarantine import (
    Movimiento,
    ResultadoCuarentena,
    CuarentenaInvalida,
    validar_carpeta_cuarentena,
    planear_movimientos,
    mover_a_cuarentena,
)
from .reporte import exportar_csv

__all__ = [
    "hash_parcial",
    "hash_completo",
    "formatear_tamano",
    "TAMANO_BLOQUE",
    "TAMANO_HASH_PARCIAL",
    "ArchivoDup",
    "GrupoDuplicado",
    "ResultadoEscaneo",
    "Progreso",
    "EscaneoCancelado",
    "escanear",
    "FiltroEscaneo",
    "parsear_extensiones",
    "parsear_nombres",
    "texto_de",
    "EXTENSIONES_BASURA",
    "NOMBRES_BASURA",
    "CARPETAS_BASURA",
    "CATEGORIAS_EXTENSIONES",
    "SeleccionDuplicados",
    "CONSERVAR",
    "MOVER",
    "GRUPO_OK",
    "GRUPO_SIN_CONSERVAR",
    "GRUPO_MULTIPLE",
    "Movimiento",
    "ResultadoCuarentena",
    "CuarentenaInvalida",
    "validar_carpeta_cuarentena",
    "planear_movimientos",
    "mover_a_cuarentena",
    "exportar_csv",
]
