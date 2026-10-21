"""Mover los duplicados descartados a una carpeta de cuarentena.

Reglas de seguridad (heredadas del script de consola):

* NUNCA se borra ni se sobrescribe nada. Solo se **mueve**.
* El original solo desaparece de su sitio cuando su copia ya está a
  salvo en la cuarentena (lo garantiza `shutil.move`).
* Se preserva la estructura de subcarpetas relativa a la carpeta
  escaneada, para poder devolver cada archivo a su lugar si hace falta.
* Si en el destino ya hay un archivo con ese nombre, el nuevo se guarda
  con un sufijo `(1)`, `(2)`... en vez de pisarlo.
* Al terminar se escribe un CSV de log con cada movimiento (origen,
  destino, estado), para poder deshacer a mano.
"""

import csv
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime

from .seleccion import SeleccionDuplicados
from .tipos import FuncCancelado, FuncProgreso


@dataclass
class Movimiento:
    grupo: int
    origen: str
    destino: str
    tamano: int
    ok: bool = False
    error: str = ""


@dataclass
class ResultadoCuarentena:
    movimientos: list[Movimiento] = field(default_factory=list)
    ruta_log: str = ""

    @property
    def movidos(self) -> list[Movimiento]:
        return [m for m in self.movimientos if m.ok]

    @property
    def fallidos(self) -> list[Movimiento]:
        return [m for m in self.movimientos if not m.ok]

    @property
    def bytes_movidos(self) -> int:
        return sum(m.tamano for m in self.movidos)


class CuarentenaInvalida(Exception):
    """La carpeta de cuarentena elegida no sirve (p. ej. está dentro de
    la carpeta escaneada)."""


def _norm(p: str) -> str:
    return os.path.normcase(os.path.abspath(p))


def validar_carpeta_cuarentena(carpeta_cuarentena: str, carpeta_raiz: str) -> str | None:
    """Devuelve un mensaje de advertencia (str) o None si todo bien.

    Lanza CuarentenaInvalida si la carpeta de cuarentena está dentro de
    la carpeta escaneada (provocaría que el próximo escaneo vuelva a
    encontrar los archivos ya movidos, o mover una carpeta dentro de sí
    misma).
    """
    cq = _norm(carpeta_cuarentena)
    cr = _norm(carpeta_raiz)

    if cq == cr:
        raise CuarentenaInvalida(
            "La carpeta de cuarentena no puede ser la misma que la carpeta escaneada.")
    if cq.startswith(cr + os.sep):
        raise CuarentenaInvalida(
            "La carpeta de cuarentena está dentro de la carpeta escaneada. "
            "Elige una carpeta fuera de ella.")
    if cr.startswith(cq + os.sep):
        return ("Atención: la carpeta escaneada está dentro de la carpeta de "
                "cuarentena. Se puede continuar, pero revisa que sea lo que quieres.")
    return None


def _destino_para(origen: str, carpeta_raiz: str, carpeta_cuarentena: str) -> str:
    """Ruta destino preservando la estructura relativa a la carpeta escaneada."""
    try:
        rel = os.path.relpath(origen, carpeta_raiz)
    except ValueError:
        rel = os.path.basename(origen)
    if rel.startswith(".." + os.sep) or rel == "..":
        # El archivo está fuera de la carpeta escaneada: lo colgamos de
        # una subcarpeta "_fuera_de_la_carpeta" con su nombre.
        rel = os.path.join("_fuera_de_la_carpeta", os.path.basename(origen))
    return os.path.join(carpeta_cuarentena, rel)


def _evitar_colision(destino: str) -> str:
    """Si `destino` ya existe, devuelve 'nombre (1).ext', 'nombre (2).ext'..."""
    if not os.path.exists(destino):
        return destino
    base, ext = os.path.splitext(destino)
    i = 1
    while os.path.exists(f"{base} ({i}){ext}"):
        i += 1
    return f"{base} ({i}){ext}"


def planear_movimientos(
    seleccion: SeleccionDuplicados, carpeta_raiz: str, carpeta_cuarentena: str,
) -> list[Movimiento]:
    """Lista de Movimiento (sin ejecutar) para los archivos marcados como MOVER."""
    plan: list[Movimiento] = []
    for gi, archivo in seleccion.archivos_a_mover():
        destino = _destino_para(archivo.ruta, carpeta_raiz, carpeta_cuarentena)
        plan.append(Movimiento(
            grupo=gi + 1, origen=archivo.ruta, destino=destino,
            tamano=archivo.tamano))
    return plan


def mover_a_cuarentena(
    seleccion: SeleccionDuplicados,
    carpeta_raiz: str,
    carpeta_cuarentena: str,
    progreso: FuncProgreso | None = None,
    cancelado: FuncCancelado | None = None,
) -> ResultadoCuarentena:
    """Ejecuta el movimiento. Devuelve un ResultadoCuarentena.

    progreso : callable(actual, total, mensaje) opcional.
    cancelado: callable() -> bool opcional. Si pasa a True, se deja de
               mover (lo ya movido queda movido) y se escribe el log
               igual.
    """
    if not seleccion.todo_listo():
        raise ValueError(
            "Hay grupos sin resolver: cada grupo debe tener exactamente una "
            "copia marcada como conservar antes de mover.")

    validar_carpeta_cuarentena(carpeta_cuarentena, carpeta_raiz)

    progreso = progreso or (lambda *_: None)
    cancelado = cancelado or (lambda: False)

    plan = planear_movimientos(seleccion, carpeta_raiz, carpeta_cuarentena)
    total = len(plan)
    os.makedirs(carpeta_cuarentena, exist_ok=True)

    for i, mov in enumerate(plan, start=1):
        if cancelado():
            break
        progreso(i, total, f"Moviendo {i}/{total}: {os.path.basename(mov.origen)}")
        try:
            if not os.path.exists(mov.origen):
                raise FileNotFoundError("el archivo ya no está en su sitio")
            os.makedirs(os.path.dirname(mov.destino), exist_ok=True)
            mov.destino = _evitar_colision(mov.destino)
            shutil.move(mov.origen, mov.destino)
            mov.ok = True
        except (OSError, shutil.Error) as e:
            mov.ok = False
            mov.error = str(e)

    resultado = ResultadoCuarentena(movimientos=plan)
    resultado.ruta_log = _escribir_log(plan, carpeta_cuarentena, carpeta_raiz)
    progreso(total, total, "Listo.")
    return resultado


def _escribir_log(
    movimientos: list[Movimiento], carpeta_cuarentena: str, carpeta_raiz: str,
) -> str:
    sello = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta_log = os.path.join(carpeta_cuarentena, f"_log_cuarentena_{sello}.csv")
    try:
        os.makedirs(carpeta_cuarentena, exist_ok=True)
        with open(ruta_log, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["Fecha", "Carpeta_Escaneada", "Grupo", "Origen",
                        "Destino", "Tamano_Bytes", "Estado", "Error"])
            ahora = datetime.now().isoformat(timespec="seconds")
            for m in movimientos:
                w.writerow([
                    ahora, carpeta_raiz, m.grupo, m.origen, m.destino,
                    m.tamano, "movido" if m.ok else "ERROR", m.error,
                ])
        return ruta_log
    except OSError:
        return ""
