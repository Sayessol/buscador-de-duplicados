"""Error log in a file (core/app_logging.py) and warning about unexpected errors."""

import sys
import threading
from types import SimpleNamespace

import pytest

from core import app_logging


@pytest.fixture
def appdata(tmp_path, monkeypatch):
    """Isolates the log in a temporary folder and closes it when done."""
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.delenv("BUSCADOR_DEBUG", raising=False)
    app_logging.stop()
    yield tmp_path
    app_logging.stop()


def _read(path):
    for h in app_logging.log.handlers:
        h.flush()
    return path.read_text(encoding="utf-8")


def test_creates_the_file_and_logs_the_startup(appdata):
    path = app_logging.start()
    assert path == appdata / "BuscadorDuplicados" / "registro" / "buscador.log"
    assert app_logging.file_path() == path
    text = _read(path)
    assert "Arranca Buscador de duplicados" in text and app_logging.__version__ in text


def test_starting_twice_does_not_duplicate_lines(appdata):
    app_logging.start()
    app_logging.start()
    app_logging.log.info("una sola vez")
    assert _read(app_logging.file_path()).count("una sola vez") == 1


def test_logs_exceptions_with_their_traceback(appdata):
    app_logging.start()
    try:
        _ = 1 / 0
    except ZeroDivisionError:
        app_logging.log.exception("Falló una cuenta")
    text = _read(app_logging.file_path())
    assert "Falló una cuenta" in text
    assert "ZeroDivisionError" in text and "Traceback" in text


def test_detail_is_only_logged_with_buscador_debug(appdata, monkeypatch):
    app_logging.start()
    app_logging.log.debug("detalle-oculto")
    assert "detalle-oculto" not in _read(app_logging.file_path())
    app_logging.stop()
    monkeypatch.setenv("BUSCADOR_DEBUG", "1")
    app_logging.start()
    app_logging.log.debug("detalle-visible")
    assert "detalle-visible" in _read(app_logging.file_path())


def test_without_write_permission_the_app_carries_on(tmp_path, monkeypatch):
    # APPDATA points to a FILE: the log folder cannot be created.
    file = tmp_path / "soy_un_fichero"
    file.write_text("x")
    monkeypatch.setenv("APPDATA", str(file))
    app_logging.stop()
    assert app_logging.start() is None
    app_logging.log.error("esto no debe lanzar nada")     # keeps working, without a file
    assert app_logging.file_path() is None


def test_hooks_log_unhandled_errors(appdata, monkeypatch):
    previous = (sys.excepthook, threading.excepthook)
    calls = []
    monkeypatch.setattr(sys, "excepthook", lambda *a: calls.append("principal"))
    monkeypatch.setattr(threading, "excepthook", lambda a: calls.append("hilo"))
    app_logging.start()
    app_logging.install_hooks()
    try:
        raise ValueError("fallo en el hilo principal")
    except ValueError:
        sys.excepthook(*sys.exc_info())
    try:
        raise KeyError("fallo en otro hilo")
    except KeyError:
        kind, value, trace = sys.exc_info()
        threading.excepthook(SimpleNamespace(
            exc_type=kind, exc_value=value, exc_traceback=trace,
            thread=SimpleNamespace(name="Hilo-prueba")))
    text = _read(app_logging.file_path())
    assert "fallo en el hilo principal" in text
    assert "Hilo-prueba" in text and "KeyError" in text
    assert calls == ["principal", "hilo"]                 # the previous hook is also called
    sys.excepthook, threading.excepthook = previous


def test_unexpected_ui_error_is_logged_and_warned_once(appdata, monkeypatch):
    from tkinter import messagebox

    from ui.main_window import MainWindow

    warnings = []
    monkeypatch.setattr(messagebox, "showerror", lambda *a, **k: warnings.append(a))
    app_logging.start()
    window = SimpleNamespace(_error_warned=False)          # the attribute it uses is enough
    for _ in range(3):                                       # the same failure, three times
        try:
            _ = {}["no existe"]
        except KeyError:
            MainWindow.report_callback_exception(window, *sys.exc_info())
    text = _read(app_logging.file_path())
    assert text.count("Error inesperado en la interfaz") == 3   # all three are logged
    assert len(warnings) == 1                                      # but warned only once
    assert str(app_logging.file_path()) in warnings[0][1]     # and it says where the log is
