"""Undoing a copy deletes the copies the app made. Windows can lock a freshly
created file for a moment (antivirus, indexer), so removal retries briefly."""

import os

import pytest

from duplicate_finder.application.history import OperationHistory
from duplicate_finder.domain.operations import KIND_GATHER
from duplicate_finder.infrastructure import local_file_system
from duplicate_finder.infrastructure.history_store import JsonHistoryStore
from duplicate_finder.infrastructure.local_file_system import LocalFileSystem

fs = LocalFileSystem()
history = OperationHistory(JsonHistoryStore(), fs)


@pytest.fixture
def isolated_appdata(tmp_path, monkeypatch):
    """Keeps the history file in a temporary folder (the real one is never touched)."""
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    return tmp_path


@pytest.fixture
def sleeps(monkeypatch):
    """Records the waits instead of really sleeping."""
    waited = []
    monkeypatch.setattr(local_file_system.time, "sleep", waited.append)
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

    monkeypatch.setattr(local_file_system.os, "remove", remove)
    return calls


def test_removal_succeeds_when_the_lock_clears(tmp_path, monkeypatch, sleeps):
    target = tmp_path / "copy.txt"
    target.write_text("x")
    calls = _locked_for(monkeypatch, failures=2)

    fs.remove(str(target))

    assert not target.exists()
    assert len(calls) == 3
    assert sleeps == pytest.approx([0.1, 0.2])


def test_removal_gives_up_after_the_last_attempt(tmp_path, monkeypatch, sleeps):
    target = tmp_path / "copy.txt"
    target.write_text("x")
    calls = _locked_for(monkeypatch, failures=99)

    with pytest.raises(PermissionError):
        fs.remove(str(target))

    assert target.exists()
    assert len(calls) == local_file_system._REMOVE_ATTEMPTS
    assert len(sleeps) == local_file_system._REMOVE_ATTEMPTS - 1


def test_removal_of_a_missing_path_is_not_an_error(tmp_path, sleeps):
    fs.remove(str(tmp_path / "not_there.txt"))
    assert sleeps == []


def test_removal_does_not_retry_other_errors(tmp_path, monkeypatch, sleeps):
    target = tmp_path / "copy.txt"
    target.write_text("x")

    def remove(path):
        raise FileNotFoundError(2, "gone")

    monkeypatch.setattr(local_file_system.os, "remove", remove)

    with pytest.raises(FileNotFoundError):
        fs.remove(str(target))
    assert sleeps == []


def test_undo_of_a_copy_survives_a_short_lock(isolated_appdata, monkeypatch, sleeps):
    origin = isolated_appdata / "origin.txt"
    copy = isolated_appdata / "copy.txt"
    origin.write_text("original")
    copy.write_text("original")
    op_id = history.record(
        KIND_GATHER,
        "copy",
        str(isolated_appdata),
        str(isolated_appdata),
        [(str(origin), str(copy))],
    )
    _locked_for(monkeypatch, failures=2)

    result = history.undo(op_id)

    assert result["failures"] == []
    assert not copy.exists() and origin.exists()  # the original is never touched
    assert history.list_all()[0]["undone"] is True


def test_undo_of_a_copy_reports_a_lock_that_never_clears(isolated_appdata, monkeypatch, sleeps):
    origin = isolated_appdata / "origin.txt"
    copy = isolated_appdata / "copy.txt"
    origin.write_text("original")
    copy.write_text("original")
    op_id = history.record(
        KIND_GATHER,
        "copy",
        str(isolated_appdata),
        str(isolated_appdata),
        [(str(origin), str(copy))],
    )
    _locked_for(monkeypatch, failures=99)

    result = history.undo(op_id)

    assert len(result["failures"]) == 1
    assert copy.exists() and origin.exists()
    assert history.list_all()[0]["undone"] is False  # it can be retried later
