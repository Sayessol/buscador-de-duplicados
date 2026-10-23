"""Each pass of the scanner on its own (application/scan_duplicates.py).

`scan()` chains three functions; here each one is tested with small, easy-to-understand
cases. The whole function is already compared with the original script
in tests/compare_with_original.py.
"""

from pathlib import Path

import pytest

from duplicate_finder.domain.filters import ScanFilter
from duplicate_finder.infrastructure.hashing import PARTIAL_HASH_SIZE
from duplicate_finder.application.scan_duplicates import (
    ScanCancelled,
    _full_hash_pass,
    _partial_hash_pass,
    _size_pass,
    scan,
)

LARGE = PARTIAL_HASH_SIZE * 3            # over 64 KB: forces the full hash


def _nothing(_progress):
    pass


def _dont_cancel():
    return False


@pytest.fixture
def folder(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "a" / "photo.jpg").write_bytes(b"x" * 100)
    (tmp_path / "b" / "photo copy.jpg").write_bytes(b"x" * 100)      # identical to the previous one
    (tmp_path / "a" / "otro.txt").write_bytes(b"y" * 100)            # same size, other content
    (tmp_path / "a" / "unico.png").write_bytes(b"z" * 7)             # unique size
    (tmp_path / "a" / "empty.log").write_bytes(b"")
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
    assert set(by_size) == {100}                   # the .log and the 7-byte one are left out
    assert total == 3 and excluded == 2


def test_pass_1_can_be_cancelled(folder):
    with pytest.raises(ScanCancelled):
        _size_pass(str(folder), ScanFilter.no_filter(), _nothing, lambda: True, [])


def test_pass_2_discards_those_that_differ_at_the_start(folder):
    of_100_bytes = [str(p) for p in folder.rglob("*") if p.is_file() and p.stat().st_size == 100]
    candidates = {100: sorted(of_100_bytes)}
    finalists = _partial_hash_pass(candidates, _nothing, _dont_cancel, [])
    # Only the two identical ones survive; the .txt (same size, other content) is discarded.
    assert len(finalists) == 1
    (paths,) = finalists.values()
    assert sorted(Path(r).name for r in paths) == ["photo copy.jpg", "photo.jpg"]


def test_pass_2_logs_a_file_that_disappeared(tmp_path):
    errors = []
    missing = [str(tmp_path / "does_not_exist_1"), str(tmp_path / "does_not_exist_2")]
    _partial_hash_pass({5: missing}, _nothing, _dont_cancel, errors)
    assert len(errors) == 2 and all("does_not_exist" in path for path, _ in errors)


def test_pass_3_small_ones_are_identical_without_rereading(tmp_path):
    a, b = tmp_path / "a.bin", tmp_path / "b.bin"
    a.write_bytes(b"1" * 50)
    b.write_bytes(b"1" * 50)
    finalists = {(50, "false_partial_hash"): [str(a), str(b)]}
    groups = _full_hash_pass(finalists, _nothing, _dont_cancel, [])
    assert len(groups) == 1 and groups[0].hash == "false_partial_hash" and groups[0].count == 2


def test_pass_3_separates_those_that_only_differ_at_the_end(tmp_path):
    """Same size and same first 64 KB, but a different end: they are not duplicates."""
    base = bytes(range(256)) * (LARGE // 256)
    equal = [tmp_path / "x1.bin", tmp_path / "x2.bin"]
    different = tmp_path / "x3.bin"
    for path in equal:
        path.write_bytes(base)
    assert base[-1] != 0
    different.write_bytes(base[:-1] + b"\x00")      # only the last byte changes
    res = scan(str(tmp_path))
    assert res.total_groups == 1
    assert sorted(a.path for a in res.groups[0].files) == sorted(str(r) for r in equal)


def test_scan_non_folder_raises(tmp_path):
    with pytest.raises(NotADirectoryError):
        scan(str(tmp_path / "does_not_exist"))
