"""Reunir todas las imágenes de una carpeta en una carpeta común.

Dos estrategias:

* **por_archivos**: mueve/copia cada imagen a `destino/<misma subruta>`.
  Los archivos que no son imágenes se tratan según `ReglasNoImagen`
  (dejarlos, moverlos igual, o agruparlos por tipo en una carpeta con el
  nombre que elija el usuario).

* **carpeta_entera**: mueve/copia la carpeta a analizar completa (con
  todo lo que hay dentro) a `destino/<nombre de la carpeta>/`.
"""

import os
import shutil
from dataclasses import dataclass, field

from .filtros import CATEGORIAS_EXTENSIONES
from .tipos import FuncCancelado, FuncProgreso
from .mover import (
    MOVER, COPIAR, Traslado, ResultadoTraslado, ejecutar, escribir_log,
    validar_destino, ruta_sin_colision, tamano,
)

# Extensiones que se consideran "imagen" (más amplio que lo que Pillow
# puede previsualizar: incluye raw, heic, etc.).
EXT_IMAGEN = {e.lower() for e in CATEGORIAS_EXTENSIONES["Imágenes"]}

DEJAR = "dejar"
# (para no-imágenes: DEJAR | MOVER | "agrupar")
AGRUPAR = "agrupar"


def _ext(ruta: str) -> str:
    return os.path.splitext(ruta)[1].lower().lstrip(".")


def listar(carpeta_raiz: str, recursivo: bool = True) -> tuple[list[str], list[str]]:
    """Devuelve (imagenes, no_imagenes): dos listas de rutas absolutas."""
    imagenes: list[str] = []
    otros: list[str] = []
    if recursivo:
        for dir_actual, _sub, nombres in os.walk(carpeta_raiz):
            for n in nombres:
                ruta = os.path.join(dir_actual, n)
                (imagenes if _ext(n) in EXT_IMAGEN else otros).append(ruta)
    else:
        for n in sorted(os.listdir(carpeta_raiz)):
            ruta = os.path.join(carpeta_raiz, n)
            if os.path.isfile(ruta):
                (imagenes if _ext(n) in EXT_IMAGEN else otros).append(ruta)
    return sorted(imagenes), sorted(otros)


def tipos_no_imagen(otros: list[str]) -> dict[str, list[str]]:
    """dict: extensión -> lista de rutas, para el diálogo por tipo."""
    d: dict[str, list[str]] = {}
    for ruta in otros:
        d.setdefault(_ext(ruta) or "(sin extensión)", []).append(ruta)
    return dict(sorted(d.items()))


@dataclass
class ReglasNoImagen:
    """Qué hacer con cada tipo de archivo que no es imagen.

    accion_por_ext: ext -> "dejar" | "mover" | "agrupar"
    carpeta_por_ext: ext -> nombre de carpeta (solo si "agrupar")
    """

    accion_por_ext: dict[str, str] = field(default_factory=dict)
    carpeta_por_ext: dict[str, str] = field(default_factory=dict)

    def accion(self, ext: str) -> str:
        return self.accion_por_ext.get(ext, DEJAR)

    def carpeta(self, ext: str) -> str:
        return (self.carpeta_por_ext.get(ext) or ext).strip() or ext


def planear_por_archivos(
    imagenes: list[str],
    otros: list[str],
    carpeta_raiz: str,
    destino: str,
    reglas: ReglasNoImagen | None = None,
) -> list[Traslado]:
    """Lista de Traslado (sin ejecutar)."""
    reglas = reglas or ReglasNoImagen()
    plan: list[Traslado] = []

    # Imágenes: siempre a destino/<misma subruta que tenían en el origen>.
    for ruta in imagenes:
        rel = os.path.relpath(ruta, carpeta_raiz)   # p. ej. "vacaciones/playa.jpg"
        plan.append(Traslado(ruta, os.path.join(destino, rel), tamano(ruta)))

    # No imágenes: según lo que haya elegido el usuario para cada tipo.
    for ruta in otros:
        ext = _ext(ruta) or "(sin extensión)"
        acc = reglas.accion(ext)
        if acc == DEJAR:
            continue                                # no se toca
        rel = os.path.relpath(ruta, carpeta_raiz)
        if acc == AGRUPAR:
            # destino/<carpeta que nombró el usuario>/<subruta>
            destino_final = os.path.join(destino, reglas.carpeta(ext), rel)
        else:  # "mover": igual que las imágenes
            destino_final = os.path.join(destino, rel)
        plan.append(Traslado(ruta, destino_final, tamano(ruta)))

    return plan


def reunir_por_archivos(
    imagenes: list[str],
    otros: list[str],
    carpeta_raiz: str,
    destino: str,
    accion: str = MOVER,
    reglas: ReglasNoImagen | None = None,
    progreso: FuncProgreso | None = None,
    cancelado: FuncCancelado | None = None,
) -> ResultadoTraslado:
    validar_destino(destino, carpeta_raiz)
    os.makedirs(destino, exist_ok=True)
    plan = planear_por_archivos(imagenes, otros, carpeta_raiz, destino, reglas)
    res = ejecutar(plan, accion=accion, progreso=progreso, cancelado=cancelado)
    res.ruta_log = escribir_log(plan, destino, "reunir", carpeta_raiz, accion)
    return res


def reunir_carpeta_entera(
    carpeta_raiz: str, destino: str, accion: str = MOVER, progreso: FuncProgreso | None = None,
) -> ResultadoTraslado:
    """Mueve/copia la carpeta a analizar completa dentro del destino."""
    validar_destino(destino, carpeta_raiz)
    os.makedirs(destino, exist_ok=True)
    progreso = progreso or (lambda *_: None)

    nombre = os.path.basename(os.path.normpath(carpeta_raiz)) or "carpeta"
    final = ruta_sin_colision(os.path.join(destino, nombre))
    verbo = "Copiando" if accion == COPIAR else "Moviendo"
    progreso(0, 1, f"{verbo} la carpeta «{nombre}»…")

    t = Traslado(carpeta_raiz, final, 0)
    try:
        if accion == COPIAR:
            shutil.copytree(carpeta_raiz, final)
        else:
            shutil.move(carpeta_raiz, final)
        t.ok = True
    except (OSError, shutil.Error) as e:
        t.ok, t.error = False, str(e)

    progreso(1, 1, "Listo.")
    res = ResultadoTraslado(traslados=[t], accion=accion)
    res.ruta_log = escribir_log([t], destino, "reunir_carpeta", carpeta_raiz,
                                accion)
    return res
