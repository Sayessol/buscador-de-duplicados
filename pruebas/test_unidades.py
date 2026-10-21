"""Pruebas unitarias pequeñas (pytest puro): config, informe CSV y formato de tamaños."""

import csv
from types import SimpleNamespace

import pytest

from core import config
from core.hashing import formatear_tamano
from core.reporte import COLUMNAS, exportar_csv


@pytest.fixture
def appdata(tmp_path, monkeypatch):
    """Aísla la configuración en una carpeta temporal (no toca la real)."""
    monkeypatch.setenv("APPDATA", str(tmp_path))
    return tmp_path


def test_config_valores_por_defecto(appdata):
    assert config.get_modo() == "sencillo"
    assert config.get_tema() == "auto"


def test_config_guarda_y_recuerda(appdata):
    config.set_modo("avanzado")
    config.set_tema("oscuro")
    assert config.get_modo() == "avanzado"
    assert config.get_tema() == "oscuro"
    assert (appdata / "BuscadorDuplicados" / "config.json").exists()


def test_config_ignora_valores_invalidos(appdata):
    config.set_modo("avanzado")
    config.set_modo("loquesea")           # se ignora
    config.set_tema("fucsia")             # se ignora
    assert config.get_modo() == "avanzado"
    assert config.get_tema() == "auto"


def test_config_corrupta_no_rompe(appdata):
    ruta = appdata / "BuscadorDuplicados" / "config.json"
    ruta.parent.mkdir()
    ruta.write_text("{ esto no es json", encoding="utf-8")
    assert config.get_modo() == "sencillo"   # vuelve al valor por defecto


def test_config_guardar_sin_permiso_no_lanza(monkeypatch, tmp_path):
    # APPDATA apunta a un FICHERO, así que no se puede crear la carpeta debajo.
    fichero = tmp_path / "soy_un_fichero"
    fichero.write_text("x")
    monkeypatch.setenv("APPDATA", str(fichero))
    config.set_modo("avanzado")              # falla en silencio
    assert config.get_modo() == "sencillo"


def test_exportar_csv(tmp_path):
    a1 = SimpleNamespace(ruta=r"C:\a\foto.jpg", tamano=2048)
    a2 = SimpleNamespace(ruta=r"C:\b\foto.jpg", tamano=2048)
    resultado = SimpleNamespace(grupos=[SimpleNamespace(archivos=[a1, a2], hash="abc123")])
    destino = tmp_path / "informe.csv"

    assert exportar_csv(resultado, destino) == 1

    filas = list(csv.reader(destino.open(encoding="utf-8-sig", newline="")))
    assert filas[0] == COLUMNAS
    assert filas[1] == ["Grupo 1", r"C:\a\foto.jpg", "2.0 KB", "2048", "abc123"]
    assert len(filas) == 3


@pytest.mark.parametrize("bytes_, esperado", [
    (0, "0.0 B"),
    (1023, "1023.0 B"),
    (1024, "1.0 KB"),
    (1536, "1.5 KB"),
    (1024 ** 2, "1.0 MB"),
    (5 * 1024 ** 3, "5.0 GB"),
    (1024 ** 4, "1.0 TB"),
    (1024 ** 5, "1.0 PB"),
])
def test_formatear_tamano(bytes_, esperado):
    assert formatear_tamano(bytes_) == esperado


def test_app_sin_consola_no_se_cae_al_escribir(monkeypatch):
    """En el .exe sin consola stdout/stderr son None; la app lo corrige al arrancar."""
    import sys

    import app

    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)
    app._asegurar_salidas()
    sys.stderr.write("aviso de una librería\n")      # antes: AttributeError
    print("también con print")
    assert sys.stdout is not None and sys.stderr is not None


def test_version_coincide_con_el_changelog():
    """La versión del código tiene su apartado en CHANGELOG.md (así no se desfasan)."""
    import re
    from pathlib import Path

    from core import __version__

    assert re.fullmatch(r"\d+\.\d+\.\d+", __version__), __version__
    changelog = (Path(__file__).resolve().parents[1] / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{__version__}]" in changelog, (
        f"Falta el apartado «## [{__version__}]» en CHANGELOG.md")
