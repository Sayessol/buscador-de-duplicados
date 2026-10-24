"""The use cases with fakes in place of the disk: nothing here reads or writes a real file."""

import os

import pytest

from duplicate_finder.application.file_transfers import FileTransfers
from duplicate_finder.application.gather import GatherImages
from duplicate_finder.application.history import OperationHistory
from duplicate_finder.application.quarantine import MoveToQuarantine
from duplicate_finder.application.scan_duplicates import ScanDuplicates
from duplicate_finder.application.start_selection import StartSelection
from duplicate_finder.domain.operations import KIND_GATHER, KIND_QUARANTINE
from duplicate_finder.domain.transfers import COPY, MOVE
from tests.fakes import FakeFileSystem, FakeHasher, InMemoryHistoryStore

ROOT = os.path.join("C:\\", "photos")


def path(*parts):
    return os.path.join(ROOT, *parts)


@pytest.fixture
def fs():
    return FakeFileSystem(
        {
            path("a", "beach.jpg"): b"0123456789",
            path("b", "beach copy.jpg"): b"0123456789",  # identical to the previous one
            path("c", "tricky.jpg"): b"0123abcdef",  # same size and start, different end
            path("d", "other.txt"): b"short",  # unique size
        }
    )


def test_scan_finds_the_identical_files_and_only_those(fs):
    result = ScanDuplicates(fs, FakeHasher(fs))(ROOT)

    assert [[f.path for f in g.files] for g in result.groups] == [
        [path("a", "beach.jpg"), path("b", "beach copy.jpg")]
    ]
    assert result.total_files == 4 and result.errors == []


def test_scan_reports_a_file_that_cannot_be_read(fs):
    class Failing(FakeHasher):
        def full_hash(self, path):
            raise PermissionError(13, "denied")

    result = ScanDuplicates(fs, Failing(fs))(ROOT)

    assert result.groups == [] and len(result.errors) >= 2


def test_scan_of_something_that_is_not_a_folder_raises(fs):
    with pytest.raises(NotADirectoryError):
        ScanDuplicates(fs, FakeHasher(fs))(path("a", "beach.jpg"))


@pytest.fixture
def history(fs):
    return OperationHistory(InMemoryHistoryStore(), fs)


def _ready_selection(fs):
    result = ScanDuplicates(fs, FakeHasher(fs))(ROOT)
    selection = StartSelection(fs)(result)
    selection.preselect_primary()
    return selection


def test_quarantine_moves_the_copy_and_writes_the_log(fs, history):
    selection = _ready_selection(fs)
    quarantine = os.path.join("C:\\", "quarantine")

    result = MoveToQuarantine(fs, history)(selection, ROOT, quarantine)

    assert len(result.moved) == 1 and not result.failed
    assert fs.exists(path("a", "beach.jpg"))  # the one to keep stays
    assert not fs.exists(path("b", "beach copy.jpg"))
    assert fs.exists(os.path.join(quarantine, "b", "beach copy.jpg"))
    (log,) = fs.csv_files.values()
    assert len(log) == 2 and "moved" in log[1]  # header + one row


def test_quarantine_records_what_it_moved_in_the_history(fs, history):
    selection = _ready_selection(fs)
    quarantine = os.path.join("C:\\", "quarantine")

    MoveToQuarantine(fs, history)(selection, ROOT, quarantine)

    (op,) = history.list_all()
    assert op["kind"] == KIND_QUARANTINE and op["action"] == MOVE
    assert op["moves"] == [
        {
            "source": path("b", "beach copy.jpg"),
            "destination": os.path.join(quarantine, "b", "beach copy.jpg"),
        }
    ]
    assert "1" in op["description"]


def test_quarantine_reports_a_failed_move_and_goes_on(fs, history):
    selection = _ready_selection(fs)
    fs.fail_moves_of.add(os.path.normpath(path("b", "beach copy.jpg")))

    result = MoveToQuarantine(fs, history)(selection, ROOT, os.path.join("C:\\", "quarantine"))

    assert len(result.failed) == 1 and "locked" in result.failed[0].error
    assert fs.exists(path("b", "beach copy.jpg"))  # nothing was lost
    assert history.list_all() == []  # and nothing to undo


def test_quarantine_does_not_start_with_unresolved_groups(fs, history):
    result = ScanDuplicates(fs, FakeHasher(fs))(ROOT)
    selection = StartSelection(fs)(result)
    selection.mark(0, path("a", "beach.jpg"), "move")
    selection.mark(0, path("b", "beach copy.jpg"), "move")  # nothing kept

    with pytest.raises(ValueError):
        MoveToQuarantine(fs, history)(selection, ROOT, os.path.join("C:\\", "quarantine"))


def test_history_records_and_undoes_a_move(fs):
    store = InMemoryHistoryStore()
    history = OperationHistory(store, fs)
    source, destination = path("b", "beach copy.jpg"), os.path.join("C:\\", "q", "beach copy.jpg")
    fs.move(source, destination)

    op_id = history.record(
        KIND_QUARANTINE, MOVE, ROOT, os.path.dirname(destination), [(source, destination)]
    )
    result = history.undo(op_id)

    assert result["reverted"] == 1 and result["failures"] == []
    assert fs.exists(source) and not fs.exists(destination)
    assert history.list_all()[0]["undone"] is True


def test_history_undo_of_a_copy_deletes_only_the_copy(fs):
    history = OperationHistory(InMemoryHistoryStore(), fs)
    original, copy = path("a", "beach.jpg"), path("copies", "beach.jpg")
    fs.copy_file(original, copy)
    op_id = history.record(KIND_QUARANTINE, COPY, ROOT, path("copies"), [(original, copy)])

    history.undo(op_id)

    assert fs.exists(original) and not fs.exists(copy)


def test_gather_plans_the_images_under_the_destination(fs, history):
    gather = GatherImages(fs, FileTransfers(fs), history)
    images, others = gather.list_all(ROOT)

    plan = gather.plan_by_files(images, others, ROOT, os.path.join("C:\\", "all"))

    assert sorted(os.path.relpath(t.destination, os.path.join("C:\\", "all")) for t in plan) == [
        os.path.join("a", "beach.jpg"),
        os.path.join("b", "beach copy.jpg"),
        os.path.join("c", "tricky.jpg"),
    ]


def test_gather_moves_the_images_and_records_them_in_the_history(fs, history):
    gather = GatherImages(fs, FileTransfers(fs), history)
    images, others = gather.list_all(ROOT)
    destination = os.path.join("C:\\", "all")

    result = gather.gather_by_files(images, others, ROOT, destination, description="3 images")

    assert len(result.done) == 3 and not result.failed
    (op,) = history.list_all()
    assert op["kind"] == KIND_GATHER and op["description"] == "3 images"
    assert len(op["moves"]) == 3


def test_gather_records_nothing_when_nothing_was_done(fs, history):
    gather = GatherImages(fs, FileTransfers(fs), history)
    fs.fail_moves_of.update(os.path.normpath(p) for p in fs.files)

    result = gather.gather_by_files(gather.list_all(ROOT)[0], [], ROOT, os.path.join("C:\\", "all"))

    assert len(result.failed) == 3 and history.list_all() == []
