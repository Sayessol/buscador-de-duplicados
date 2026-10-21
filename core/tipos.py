"""Tipos que se repiten en varios módulos del núcleo (solo nombres, sin lógica)."""

from collections.abc import Callable

# Función que recibe el avance de una operación larga: (hechos, total, mensaje).
FuncProgreso = Callable[[int, int, str], None]

# Función que dice si el usuario ha pedido cancelar.
FuncCancelado = Callable[[], bool]
