"""Small unit tests (plain pytest): config, CSV report and size formatting."""

import csv
from types import SimpleNamespace

import pytest

from duplicate_finder.application.report import ExportReport, columns
from duplicate_finder.application.settings import AppSettings
from duplicate_finder.domain.formatting import format_size
from duplicate_finder.infrastructure.local_file_system import LocalFileSystem
from duplicate_finder.infrastructure.settings import JsonSettingsStore

settings = AppSettings(JsonSettingsStore())
export_csv = ExportReport(LocalFileSystem())


@pytest.fixture
def appdata(tmp_path, monkeypatch):
    """Isolates the configuration in a temporary folder (it does not touch the real one)."""
    monkeypatch.setenv("APPDATA", str(tmp_path))
    return tmp_path


def test_config_default_values(appdata):
    assert settings.get_mode() == "simple"
    assert settings.get_theme() == "auto"


def test_config_saves_and_remembers(appdata):
    settings.set_mode("advanced")
    settings.set_theme("dark")
    assert settings.get_mode() == "advanced"
    assert settings.get_theme() == "dark"
    assert (appdata / "BuscadorDuplicados" / "config.json").exists()


def test_config_ignores_invalid_values(appdata):
    settings.set_mode("advanced")
    settings.set_mode("loquesea")  # ignored
    settings.set_theme("fuchsia")  # ignored
    assert settings.get_mode() == "advanced"
    assert settings.get_theme() == "auto"


def test_config_corrupt_does_not_break(appdata):
    path = appdata / "BuscadorDuplicados" / "config.json"
    path.parent.mkdir()
    path.write_text("{ this is not json", encoding="utf-8")
    assert settings.get_mode() == "simple"  # back to the default value


def test_config_save_without_permission_does_not_raise(monkeypatch, tmp_path):
    # APPDATA points to a FILE, so the folder underneath cannot be created.
    file = tmp_path / "i_am_a_file"
    file.write_text("x")
    monkeypatch.setenv("APPDATA", str(file))
    settings.set_mode("advanced")  # fails silently
    assert settings.get_mode() == "simple"


def test_export_csv(tmp_path):
    a1 = SimpleNamespace(path="C:\\a\\photo.jpg", size=2048)
    a2 = SimpleNamespace(path="C:\\b\\photo.jpg", size=2048)
    result = SimpleNamespace(groups=[SimpleNamespace(files=[a1, a2], hash="abc123")])
    destination = tmp_path / "report.csv"

    assert export_csv(result, destination) == 1

    rows = list(csv.reader(destination.open(encoding="utf-8-sig", newline="")))
    assert rows[0] == columns()
    assert rows[1] == ["Group 1", "C:\\a\\photo.jpg", "2.0 KB", "2048", "abc123"]
    assert len(rows) == 3


@pytest.mark.parametrize(
    "bytes_, expected",
    [
        (0, "0.0 B"),
        (1023, "1023.0 B"),
        (1024, "1.0 KB"),
        (1536, "1.5 KB"),
        (1024**2, "1.0 MB"),
        (5 * 1024**3, "5.0 GB"),
        (1024**4, "1.0 TB"),
        (1024**5, "1.0 PB"),
    ],
)
def test_format_size(bytes_, expected):
    assert format_size(bytes_) == expected


def test_app_without_console_survives_writing(monkeypatch):
    """In the .exe without a console stdout/stderr are None; the app fixes it at startup."""
    import sys

    import app

    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)
    app._ensure_outputs()
    sys.stderr.write("a library warning\n")  # before: AttributeError
    print("also with print")
    assert sys.stdout is not None and sys.stderr is not None


def test_version_matches_the_changelog():
    """The code version has its section in CHANGELOG.md (so they do not drift apart)."""
    import re
    from pathlib import Path

    from duplicate_finder import __version__

    assert re.fullmatch(r"\d+\.\d+\.\d+", __version__), __version__
    changelog = (Path(__file__).resolve().parents[1] / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{__version__}]" in changelog, (
        f"Missing section “## [{__version__}]” in CHANGELOG.md"
    )
