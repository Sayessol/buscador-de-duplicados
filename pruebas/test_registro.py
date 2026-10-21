"""Registro de errores en archivo (core/registro.py) y aviso de errores inesperados."""

import sys
import threading
from types import SimpleNamespace

import pytest

from core import registro


@pytest.fixture
def appdata(tmp_path, monkeypatch):
    """Aísla el registro en una carpeta temporal y lo cierra al terminar."""
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.delenv("BUSCADOR_DEBUG", raising=False)
    registro.detener()
    yield tmp_path
    registro.detener()


def _leer(ruta):
    for h in registro.log.handlers:
        h.flush()
    return ruta.read_text(encoding="utf-8")


def test_crea_el_archivo_y_anota_el_arranque(appdata):
    ruta = registro.iniciar()
    assert ruta == appdata / "BuscadorDuplicados" / "registro" / "buscador.log"
    assert registro.ruta_archivo() == ruta
    texto = _leer(ruta)
    assert "Arranca Buscador de duplicados" in texto and registro.__version__ in texto


def test_iniciar_dos_veces_no_duplica_lineas(appdata):
    registro.iniciar()
    registro.iniciar()
    registro.log.info("una sola vez")
    assert _leer(registro.ruta_archivo()).count("una sola vez") == 1


def test_anota_excepciones_con_su_traceback(appdata):
    registro.iniciar()
    try:
        _ = 1 / 0
    except ZeroDivisionError:
        registro.log.exception("Falló una cuenta")
    texto = _leer(registro.ruta_archivo())
    assert "Falló una cuenta" in texto
    assert "ZeroDivisionError" in texto and "Traceback" in texto


def test_el_detalle_solo_se_anota_con_buscador_debug(appdata, monkeypatch):
    registro.iniciar()
    registro.log.debug("detalle-oculto")
    assert "detalle-oculto" not in _leer(registro.ruta_archivo())
    registro.detener()
    monkeypatch.setenv("BUSCADOR_DEBUG", "1")
    registro.iniciar()
    registro.log.debug("detalle-visible")
    assert "detalle-visible" in _leer(registro.ruta_archivo())


def test_sin_permiso_para_escribir_la_app_sigue(tmp_path, monkeypatch):
    # APPDATA apunta a un FICHERO: no se puede crear la carpeta del registro.
    fichero = tmp_path / "soy_un_fichero"
    fichero.write_text("x")
    monkeypatch.setenv("APPDATA", str(fichero))
    registro.detener()
    assert registro.iniciar() is None
    registro.log.error("esto no debe lanzar nada")     # sigue funcionando, sin archivo
    assert registro.ruta_archivo() is None


def test_ganchos_anotan_errores_no_controlados(appdata, monkeypatch):
    anterior = (sys.excepthook, threading.excepthook)
    llamadas = []
    monkeypatch.setattr(sys, "excepthook", lambda *a: llamadas.append("principal"))
    monkeypatch.setattr(threading, "excepthook", lambda a: llamadas.append("hilo"))
    registro.iniciar()
    registro.instalar_ganchos()
    try:
        raise ValueError("fallo en el hilo principal")
    except ValueError:
        sys.excepthook(*sys.exc_info())
    try:
        raise KeyError("fallo en otro hilo")
    except KeyError:
        tipo, valor, traza = sys.exc_info()
        threading.excepthook(SimpleNamespace(
            exc_type=tipo, exc_value=valor, exc_traceback=traza,
            thread=SimpleNamespace(name="Hilo-prueba")))
    texto = _leer(registro.ruta_archivo())
    assert "fallo en el hilo principal" in texto
    assert "Hilo-prueba" in texto and "KeyError" in texto
    assert llamadas == ["principal", "hilo"]                 # también se llama al gancho anterior
    sys.excepthook, threading.excepthook = anterior


def test_error_inesperado_en_la_interfaz_se_anota_y_se_avisa_una_vez(appdata, monkeypatch):
    from tkinter import messagebox

    from ui.main_window import VentanaPrincipal

    avisos = []
    monkeypatch.setattr(messagebox, "showerror", lambda *a, **k: avisos.append(a))
    registro.iniciar()
    ventana = SimpleNamespace(_error_avisado=False)          # basta con el atributo que usa
    for _ in range(3):                                       # el mismo fallo, tres veces
        try:
            _ = {}["no existe"]
        except KeyError:
            VentanaPrincipal.report_callback_exception(ventana, *sys.exc_info())
    texto = _leer(registro.ruta_archivo())
    assert texto.count("Error inesperado en la interfaz") == 3   # las tres se anotan
    assert len(avisos) == 1                                      # pero solo se avisa una vez
    assert str(registro.ruta_archivo()) in avisos[0][1]          # y se dice dónde está el registro
