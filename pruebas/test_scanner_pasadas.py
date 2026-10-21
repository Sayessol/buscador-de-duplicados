"""Cada pasada del escáner por separado (core/scanner.py).

`escanear()` encadena tres funciones; aquí se prueba cada una con casos pequeños
y fáciles de entender. La función entera ya se compara con el script original
en pruebas/comparar_con_original.py.
"""

from pathlib import Path

import pytest

from core.filtros import FiltroEscaneo
from core.hashing import TAMANO_HASH_PARCIAL
from core.scanner import (
    EscaneoCancelado,
    _pasada_hash_completo,
    _pasada_hash_parcial,
    _pasada_tamanos,
    escanear,
)

GRANDE = TAMANO_HASH_PARCIAL * 3            # más de 64 KB: obliga al hash completo


def _nada(_progreso):
    pass


def _no_cancelar():
    return False


@pytest.fixture
def carpeta(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "a" / "foto.jpg").write_bytes(b"x" * 100)
    (tmp_path / "b" / "foto copia.jpg").write_bytes(b"x" * 100)      # idéntico al anterior
    (tmp_path / "a" / "otro.txt").write_bytes(b"y" * 100)            # mismo tamaño, otro contenido
    (tmp_path / "a" / "unico.png").write_bytes(b"z" * 7)             # tamaño único
    (tmp_path / "a" / "vacio.log").write_bytes(b"")
    return tmp_path


def test_pasada_1_agrupa_por_tamano(carpeta):
    errores = []
    por_tamano, total, excluidos = _pasada_tamanos(
        str(carpeta), FiltroEscaneo.sin_filtro(), _nada, _no_cancelar, errores)
    assert total == 5 and excluidos == 0 and errores == []
    assert len(por_tamano[100]) == 3 and len(por_tamano[7]) == 1 and len(por_tamano[0]) == 1


def test_pasada_1_respeta_el_filtro(carpeta):
    filtro = FiltroEscaneo(extensiones_excluidas={"log"}, tamano_minimo=10)
    por_tamano, total, excluidos = _pasada_tamanos(
        str(carpeta), filtro, _nada, _no_cancelar, [])
    assert set(por_tamano) == {100}                   # el .log y el de 7 bytes quedan fuera
    assert total == 3 and excluidos == 2


def test_pasada_1_se_puede_cancelar(carpeta):
    with pytest.raises(EscaneoCancelado):
        _pasada_tamanos(str(carpeta), FiltroEscaneo.sin_filtro(), _nada, lambda: True, [])


def test_pasada_2_descarta_los_que_difieren_al_principio(carpeta):
    de_100_bytes = [str(p) for p in carpeta.rglob("*") if p.is_file() and p.stat().st_size == 100]
    candidatos = {100: sorted(de_100_bytes)}
    finalistas = _pasada_hash_parcial(candidatos, _nada, _no_cancelar, [])
    # Solo sobreviven los dos idénticos; el .txt (mismo tamaño, otro contenido) se descarta.
    assert len(finalistas) == 1
    (rutas,) = finalistas.values()
    assert sorted(Path(r).name for r in rutas) == ["foto copia.jpg", "foto.jpg"]


def test_pasada_2_anota_un_archivo_que_ha_desaparecido(tmp_path):
    errores = []
    _pasada_hash_parcial({5: [str(tmp_path / "no_existe_1"), str(tmp_path / "no_existe_2")]},
                         _nada, _no_cancelar, errores)
    assert len(errores) == 2 and all("no_existe" in ruta for ruta, _ in errores)


def test_pasada_3_pequenos_se_dan_por_identicos_sin_releerlos(tmp_path):
    a, b = tmp_path / "a.bin", tmp_path / "b.bin"
    a.write_bytes(b"1" * 50)
    b.write_bytes(b"1" * 50)
    finalistas = {(50, "hash_parcial_falso"): [str(a), str(b)]}
    grupos = _pasada_hash_completo(finalistas, _nada, _no_cancelar, [])
    assert len(grupos) == 1 and grupos[0].hash == "hash_parcial_falso" and grupos[0].cantidad == 2


def test_pasada_3_separa_los_que_solo_difieren_al_final(tmp_path):
    """Mismo tamaño y mismos primeros 64 KB, pero distinto final: no son duplicados."""
    base = bytes(range(256)) * (GRANDE // 256)
    iguales = [tmp_path / "x1.bin", tmp_path / "x2.bin"]
    distinto = tmp_path / "x3.bin"
    for ruta in iguales:
        ruta.write_bytes(base)
    assert base[-1] != 0
    distinto.write_bytes(base[:-1] + b"\x00")      # solo cambia el último byte
    res = escanear(str(tmp_path))
    assert res.total_grupos == 1
    assert sorted(a.ruta for a in res.grupos[0].archivos) == sorted(str(r) for r in iguales)


def test_escanear_no_carpeta_lanza(tmp_path):
    with pytest.raises(NotADirectoryError):
        escanear(str(tmp_path / "no_existe"))
