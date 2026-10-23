"""Cada pasada del escáner por separado (core/scanner.py).

`escanear()` encadena tres funciones; aquí se prueba cada una con casos pequeños
y fáciles de entender. La función entera ya se compara con el script original
en tests/compare_with_original.py.
"""

from pathlib import Path

import pytest

from core.filters import ScanFilter
from core.hashing import PARTIAL_HASH_SIZE
from core.scanner import (
    ScanCancelled,
    _full_hash_pass,
    _partial_hash_pass,
    _size_pass,
    scan,
)

LARGE = PARTIAL_HASH_SIZE * 3            # más de 64 KB: obliga al hash completo


def _nothing(_progress):
    pass


def _dont_cancel():
    return False


@pytest.fixture
def folder(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "a" / "foto.jpg").write_bytes(b"x" * 100)
    (tmp_path / "b" / "foto copia.jpg").write_bytes(b"x" * 100)      # idéntico al anterior
    (tmp_path / "a" / "otro.txt").write_bytes(b"y" * 100)            # mismo tamaño, otro contenido
    (tmp_path / "a" / "unico.png").write_bytes(b"z" * 7)             # tamaño único
    (tmp_path / "a" / "vacio.log").write_bytes(b"")
    return tmp_path


def test_pass_1_groups_by_size(folder):
    errors = []
    by_size, total, excluded = _size_pass(
        str(folder), ScanFilter.no_filter(), _nothing, _dont_cancel, errors)
    assert total == 5 and excluded == 0 and errors == []
    assert len(by_size[100]) == 3 and len(by_size[7]) == 1 and len(by_size[0]) == 1


def test_pass_1_respects_the_filter(folder):
    filter = ScanFilter(excluded_extensions={"log"}, min_size=10)
    by_size, total, excluded = _size_pass(
        str(folder), filter, _nothing, _dont_cancel, [])
    assert set(by_size) == {100}                   # el .log y el de 7 bytes quedan fuera
    assert total == 3 and excluded == 2


def test_pass_1_can_be_cancelled(folder):
    with pytest.raises(ScanCancelled):
        _size_pass(str(folder), ScanFilter.no_filter(), _nothing, lambda: True, [])


def test_pass_2_discards_those_that_differ_at_the_start(folder):
    of_100_bytes = [str(p) for p in folder.rglob("*") if p.is_file() and p.stat().st_size == 100]
    candidates = {100: sorted(of_100_bytes)}
    finalists = _partial_hash_pass(candidates, _nothing, _dont_cancel, [])
    # Solo sobreviven los dos idénticos; el .txt (mismo tamaño, otro contenido) se descarta.
    assert len(finalists) == 1
    (paths,) = finalists.values()
    assert sorted(Path(r).name for r in paths) == ["foto copia.jpg", "foto.jpg"]


def test_pass_2_logs_a_file_that_disappeared(tmp_path):
    errors = []
    _partial_hash_pass({5: [str(tmp_path / "no_existe_1"), str(tmp_path / "no_existe_2")]},
                         _nothing, _dont_cancel, errors)
    assert len(errors) == 2 and all("no_existe" in path for path, _ in errors)


def test_pass_3_small_ones_are_identical_without_rereading(tmp_path):
    a, b = tmp_path / "a.bin", tmp_path / "b.bin"
    a.write_bytes(b"1" * 50)
    b.write_bytes(b"1" * 50)
    finalists = {(50, "hash_parcial_falso"): [str(a), str(b)]}
    groups = _full_hash_pass(finalists, _nothing, _dont_cancel, [])
    assert len(groups) == 1 and groups[0].hash == "hash_parcial_falso" and groups[0].count == 2


def test_pass_3_separates_those_that_only_differ_at_the_end(tmp_path):
    """Mismo tamaño y mismos primeros 64 KB, pero distinto final: no son duplicados."""
    base = bytes(range(256)) * (LARGE // 256)
    equal = [tmp_path / "x1.bin", tmp_path / "x2.bin"]
    different = tmp_path / "x3.bin"
    for path in equal:
        path.write_bytes(base)
    assert base[-1] != 0
    different.write_bytes(base[:-1] + b"\x00")      # solo cambia el último byte
    res = scan(str(tmp_path))
    assert res.total_groups == 1
    assert sorted(a.path for a in res.groups[0].files) == sorted(str(r) for r in equal)


def test_scan_non_folder_raises(tmp_path):
    with pytest.raises(NotADirectoryError):
        scan(str(tmp_path / "no_existe"))
