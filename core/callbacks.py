"""Tipos que se repiten en varios módulos del núcleo (solo nombres, sin lógica)."""

from collections.abc import Callable

# Función que recibe el avance de una operación larga: (hechos, total, mensaje).
ProgressCallback = Callable[[int, int, str], None]

# Función que dice si el usuario ha pedido cancelar.
CancelledCallback = Callable[[], bool]
