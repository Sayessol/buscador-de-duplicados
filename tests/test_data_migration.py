"""Saved data written by version 1.0 (Spanish keys and values) is still understood.

history: historial.json is read and converted on the fly, and never modified.
config:  config.json is converted on load; a .bak-1.0 copy is kept before the first rewrite.
"""

import json

import pytest

from core import config, history


@pytest.fixture
def data_folder(tmp_path, monkeypatch):
    """APPDATA in a temporary folder: the real data of the app is never touched."""
    monkeypatch.setenv("APPDATA", str(tmp_path))
    folder = tmp_path / "BuscadorDuplicados"
    folder.mkdir()
    return folder


def _legacy_operation(op_id, action, kind, source, destination, undone=False):
    return {
        "id": op_id, "fecha": "2026-10-21T10:00:00", "tipo": kind, "accion": action,
        "origen_raiz": str(source.parent), "destino": str(destination.parent),
        "descripcion": "1 archivo",
        "movimientos": [{"origen": str(source), "destino": str(destination)}],
        "deshecha": undone,
    }


# ------------------------------------------------------------------------- history

def test_history_reads_the_version_1_file_in_the_current_format(data_folder, tmp_path):
    source, destination = tmp_path / "a.txt", tmp_path / "q" / "a.txt"
    legacy = [_legacy_operation("1", "mover", "cuarentena", source, destination)]
    (data_folder / "historial.json").write_text(json.dumps(legacy), encoding="utf-8")

    (op,) = history.list_all()

    assert op["kind"] == history.KIND_QUARANTINE and op["action"] == "move"
    assert op["date"] == "2026-10-21T10:00:00" and op["undone"] is False
    assert op["moves"] == [{"source": str(source), "destination": str(destination)}]
    assert op["source_root"] == str(source.parent) and op["description"] == "1 archivo"
    assert not any(key in op for key in ("fecha", "tipo", "accion", "movimientos"))


@pytest.mark.parametrize("old, new", [
    ("cuarentena", history.KIND_QUARANTINE), ("reunir", history.KIND_GATHER),
    ("reunir_carpeta", history.KIND_GATHER_FOLDER)])
def test_history_converts_every_kind(data_folder, tmp_path, old, new):
    legacy = [_legacy_operation("1", "copiar", old, tmp_path / "a", tmp_path / "b")]
    (data_folder / "historial.json").write_text(json.dumps(legacy), encoding="utf-8")

    assert history.list_all()[0]["kind"] == new
    assert history.list_all()[0]["action"] == "copy"


def test_history_never_modifies_the_version_1_file(data_folder, tmp_path):
    legacy_file = data_folder / "historial.json"
    legacy_file.write_text(json.dumps(
        [_legacy_operation("1", "mover", "cuarentena", tmp_path / "a", tmp_path / "b")]),
        encoding="utf-8")
    before = legacy_file.read_bytes()

    history.record(history.KIND_GATHER, "copy", str(tmp_path), str(tmp_path / "d"), [])

    assert legacy_file.read_bytes() == before                    # the backup stays intact
    saved = json.loads((data_folder / "history.json").read_text(encoding="utf-8"))
    assert [op["kind"] for op in saved] == [history.KIND_QUARANTINE, history.KIND_GATHER]
    assert all("tipo" not in op and "fecha" not in op for op in saved)


def test_history_prefers_the_current_file_over_the_version_1_one(data_folder, tmp_path):
    (data_folder / "historial.json").write_text(json.dumps(
        [_legacy_operation("old", "mover", "cuarentena", tmp_path / "a", tmp_path / "b")]),
        encoding="utf-8")
    (data_folder / "history.json").write_text(json.dumps([{
        "id": "new", "date": "d", "kind": "gather", "action": "copy", "source_root": "r",
        "destination": "x", "description": "", "undone": False, "moves": []}]),
        encoding="utf-8")

    assert [op["id"] for op in history.list_all()] == ["new"]     # the old file is ignored


def test_the_first_save_carries_the_version_1_operations_over(data_folder, tmp_path):
    (data_folder / "historial.json").write_text(json.dumps(
        [_legacy_operation("old", "mover", "cuarentena", tmp_path / "a", tmp_path / "b")]),
        encoding="utf-8")

    history.record(history.KIND_GATHER, "copy", str(tmp_path), str(tmp_path / "d"), [])

    assert [op["kind"] for op in history.list_all()] == [
        history.KIND_GATHER, history.KIND_QUARANTINE]            # most recent first


def test_history_drops_entries_that_are_not_operations(data_folder, tmp_path):
    good = _legacy_operation("1", "mover", "cuarentena", tmp_path / "a", tmp_path / "b")
    (data_folder / "historial.json").write_text(
        json.dumps([good, "texto", 42, None, ["x"]]), encoding="utf-8")

    assert [op["id"] for op in history.list_all()] == ["1"]


@pytest.mark.parametrize("content", ["no es json", '{"a": 1}', "[]", ""])
def test_history_ignores_a_file_that_is_not_a_list_of_operations(data_folder, content):
    (data_folder / "historial.json").write_text(content, encoding="utf-8")
    assert history.list_all() == []


def test_current_format_is_left_as_it_is(tmp_path):
    op = {"id": "1", "date": "d", "kind": "gather", "action": "copy", "source_root": "r",
          "destination": "x", "description": "", "undone": False,
          "moves": [{"source": "a", "destination": "b"}]}
    assert history._upgrade(op) is op


def test_a_move_saved_by_version_1_can_still_be_undone(data_folder, tmp_path):
    source = tmp_path / "origin" / "photo.jpg"
    destination = tmp_path / "quarantine" / "photo.jpg"
    destination.parent.mkdir(parents=True)
    destination.write_text("photo")                        # it was moved there by version 1.0
    (data_folder / "historial.json").write_text(json.dumps(
        [_legacy_operation("1", "mover", "cuarentena", source, destination)]), encoding="utf-8")

    result = history.undo("1")

    assert result["failures"] == [] and result["reverted"] == 1
    assert source.read_text() == "photo" and not destination.exists()
    assert history.list_all()[0]["undone"] is True        # remembered in the current file
    assert json.loads((data_folder / "historial.json").read_text())[0]["deshecha"] is False


def test_a_copy_saved_by_version_1_can_still_be_undone(data_folder, tmp_path):
    original, copy = tmp_path / "a" / "x.txt", tmp_path / "b" / "x.txt"
    original.parent.mkdir()
    copy.parent.mkdir()
    original.write_text("x")
    copy.write_text("x")
    (data_folder / "historial.json").write_text(json.dumps(
        [_legacy_operation("1", "copiar", "reunir", original, copy)]), encoding="utf-8")

    result = history.undo("1")

    assert result["failures"] == [] and not copy.exists() and original.exists()


def test_an_operation_already_undone_by_version_1_is_not_undone_twice(data_folder, tmp_path):
    (data_folder / "historial.json").write_text(json.dumps(
        [_legacy_operation("1", "mover", "cuarentena", tmp_path / "a", tmp_path / "b",
                           undone=True)]), encoding="utf-8")

    result = history.undo("1")

    assert result["reverted"] == 0 and result["failures"]


# -------------------------------------------------------------------------- config

def test_config_reads_the_version_1_keys_and_values(data_folder):
    (data_folder / "config.json").write_text(
        json.dumps({"modo": "avanzado", "tema": "oscuro"}), encoding="utf-8")

    assert config.get_mode() == "advanced"
    assert config.get_theme() == "dark"


@pytest.mark.parametrize("old, new", [("sencillo", "simple"), ("avanzado", "advanced")])
def test_config_converts_every_mode(data_folder, old, new):
    (data_folder / "config.json").write_text(json.dumps({"modo": old}), encoding="utf-8")
    assert config.get_mode() == new


@pytest.mark.parametrize("old, new", [("auto", "auto"), ("claro", "light"), ("oscuro", "dark")])
def test_config_converts_every_theme(data_folder, old, new):
    (data_folder / "config.json").write_text(json.dumps({"tema": old}), encoding="utf-8")
    assert config.get_theme() == new


def test_config_keeps_a_backup_before_the_first_rewrite(data_folder):
    config_file = data_folder / "config.json"
    original = json.dumps({"modo": "avanzado", "tema": "claro"})
    config_file.write_text(original, encoding="utf-8")

    config.set_theme("dark")

    backup = data_folder / "config.json.bak-1.0"
    assert backup.read_text(encoding="utf-8") == original          # untouched copy
    assert json.loads(config_file.read_text(encoding="utf-8")) == {
        "mode": "advanced", "theme": "dark"}


def test_config_does_not_overwrite_an_existing_backup(data_folder):
    config_file = data_folder / "config.json"
    config_file.write_text(json.dumps({"modo": "avanzado"}), encoding="utf-8")
    config.set_theme("dark")                                       # first rewrite: backup
    backup = data_folder / "config.json.bak-1.0"
    first = backup.read_bytes()

    config_file.write_text(json.dumps({"modo": "sencillo"}), encoding="utf-8")
    config.set_theme("light")                                      # old keys again

    assert backup.read_bytes() == first


def test_config_in_the_current_format_gets_no_backup(data_folder):
    (data_folder / "config.json").write_text(
        json.dumps({"mode": "advanced", "theme": "dark"}), encoding="utf-8")

    config.set_theme("light")

    assert not (data_folder / "config.json.bak-1.0").exists()
    assert config.get_mode() == "advanced" and config.get_theme() == "light"


def test_config_ignores_values_it_does_not_know_even_with_old_keys(data_folder):
    (data_folder / "config.json").write_text(
        json.dumps({"modo": "turbo", "tema": "azul"}), encoding="utf-8")

    assert config.get_mode() == config.DEFAULT_MODE
    assert config.get_theme() == config.DEFAULT_THEME


def test_config_keeps_the_new_key_when_both_are_present(data_folder):
    (data_folder / "config.json").write_text(
        json.dumps({"modo": "avanzado", "mode": "simple"}), encoding="utf-8")

    assert config.get_mode() == "simple"
