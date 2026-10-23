"""Undoing a copy deletes the copies the app made. Windows can lock a freshly
created file for a moment (antivirus, indexer), so removal retries briefly."""

import os

import pytest

from core import historial


@pytest.fixture
def isolated_appdata(tmp_path, monkeypatch):
    """Keeps the history file in a temporary folder (the real one is never touched)."""
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    return tmp_path


@pytest.fixture
def sleeps(monkeypatch):
    """Records the waits instead of really sleeping."""
    waited = []
    monkeypatch.setattr(historial.time, "sleep", waited.append)
    return waited


def _locked_for(monkeypatch, failures):
    """os.remove raises PermissionError `failures` times, then works."""
    real_remove = os.remove
    calls = []

    def remove(path):
        calls.append(path)
        if len(calls) <= failures:
            raise PermissionError(32, "The process cannot access the file")
        real_remove(path)

    monkeypatch.setattr(historial.os, "remove", remove)
    return calls


def test_removal_succeeds_when_the_lock_clears(tmp_path, monkeypatch, sleeps):
    target = tmp_path / "copy.txt"
    target.write_text("x")
    calls = _locked_for(monkeypatch, failures=2)

    historial._remove_with_retries(str(target))

    assert not target.exists()
    assert len(calls) == 3
    assert sleeps == pytest.approx([0.1, 0.2])


def test_removal_gives_up_after_the_last_attempt(tmp_path, monkeypatch, sleeps):
    target = tmp_path / "copy.txt"
    target.write_text("x")
    calls = _locked_for(monkeypatch, failures=99)

    with pytest.raises(PermissionError):
        historial._remove_with_retries(str(target))

    assert target.exists()
    assert len(calls) == historial._REMOVE_ATTEMPTS
    assert len(sleeps) == historial._REMOVE_ATTEMPTS - 1


def test_removal_of_a_missing_path_is_not_an_error(tmp_path, sleeps):
    historial._remove_with_retries(str(tmp_path / "not_there.txt"))
    assert sleeps == []


def test_removal_does_not_retry_other_errors(tmp_path, monkeypatch, sleeps):
    target = tmp_path / "copy.txt"
    target.write_text("x")

    def remove(path):
        raise FileNotFoundError(2, "gone")

    monkeypatch.setattr(historial.os, "remove", remove)

    with pytest.raises(FileNotFoundError):
        historial._remove_with_retries(str(target))
    assert sleeps == []


def test_undo_of_a_copy_survives_a_short_lock(isolated_appdata, monkeypatch, sleeps):
    origin = isolated_appdata / "origin.txt"
    copy = isolated_appdata / "copy.txt"
    origin.write_text("original")
    copy.write_text("original")
    op_id = historial.registrar("reunir", "copiar", str(isolated_appdata),
                                str(isolated_appdata), [(str(origin), str(copy))])
    _locked_for(monkeypatch, failures=2)

    result = historial.deshacer(op_id)

    assert result["fallos"] == []
    assert not copy.exists() and origin.exists()     # the original is never touched
    assert historial.listar()[0]["deshecha"] is True


def test_undo_of_a_copy_reports_a_lock_that_never_clears(isolated_appdata, monkeypatch, sleeps):
    origin = isolated_appdata / "origin.txt"
    copy = isolated_appdata / "copy.txt"
    origin.write_text("original")
    copy.write_text("original")
    op_id = historial.registrar("reunir", "copiar", str(isolated_appdata),
                                str(isolated_appdata), [(str(origin), str(copy))])
    _locked_for(monkeypatch, failures=99)

    result = historial.deshacer(op_id)

    assert len(result["fallos"]) == 1
    assert copy.exists() and origin.exists()
    assert historial.listar()[0]["deshecha"] is False   # it can be retried later
