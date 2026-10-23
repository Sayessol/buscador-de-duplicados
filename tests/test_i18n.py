"""The two catalogs must stay in step, and the code must only ask for texts that exist."""

import ast
import re
from pathlib import Path

import pytest

from core import config, i18n
from core.locales import en, es

ROOT = Path(__file__).resolve().parents[1]
CODE_FOLDERS = ("core", "ui")
PLACEHOLDER = re.compile(r"\{(\w+)")


@pytest.fixture(autouse=True)
def _english():
    i18n.set_language("en")
    yield
    i18n.set_language("en")


def _placeholders(text: str) -> set[str]:
    return set(PLACEHOLDER.findall(text.replace("{{", "").replace("}}", "")))


def _code_files():
    return [p for folder in CODE_FOLDERS for p in sorted((ROOT / folder).glob("*.py"))
            if p.name != "i18n.py"]


def _tr_calls():
    """(file, line, key or None, keyword names) of every tr(...) call in the code."""
    calls = []
    for path in _code_files():
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "tr"):
                key = node.args[0] if node.args else None
                keys = [n.value for n in ast.walk(key)
                        if isinstance(n, ast.Constant) and isinstance(n.value, str)] if key else []
                dynamic = key is not None and not isinstance(key, ast.Constant)
                names = {k.arg for k in node.keywords}
                calls.append((path.name, node.lineno, keys, dynamic, names))
    return calls


def test_both_languages_have_the_same_keys():
    assert set(en.MESSAGES) == set(es.MESSAGES)


def test_both_languages_use_the_same_placeholders():
    different = {key: (_placeholders(en.MESSAGES[key]), _placeholders(es.MESSAGES[key]))
                 for key in en.MESSAGES
                 if _placeholders(en.MESSAGES[key]) != _placeholders(es.MESSAGES[key])}
    assert not different


def test_no_text_is_empty():
    for catalog in (en.MESSAGES, es.MESSAGES):
        assert all(text.strip() for text in catalog.values())


def test_every_key_the_code_asks_for_exists():
    missing = [f"{name}:{line} {key}" for name, line, keys, dynamic, _ in _tr_calls()
               for key in keys if "." in key and not dynamic and key not in en.MESSAGES]
    assert not missing


def test_every_call_passes_exactly_the_placeholders_of_its_text():
    wrong = []
    for name, line, keys, dynamic, names in _tr_calls():
        for key in keys:
            if key in en.MESSAGES and not dynamic and _placeholders(en.MESSAGES[key]) != names:
                wrong.append(f"{name}:{line} {key}")
    assert not wrong


def test_every_key_is_used_by_the_code():
    sources = "\n".join(p.read_text(encoding="utf-8") for p in _code_files())
    # category.<name> is built from the category keys of core/filters.py
    unused = [key for key in en.MESSAGES
              if f'"{key}"' not in sources and not key.startswith("category.")]
    assert not unused


def test_every_category_has_a_name():
    from core.filters import CATEGORY_EXTENSIONS
    assert all(f"category.{name}" in en.MESSAGES for name in CATEGORY_EXTENSIONS)


def test_tr_fills_placeholders_in_each_language():
    assert i18n.tr("scan.step_sizes", total_files=3) == "Step 1/2: checking sizes... (3 files)"
    i18n.set_language("es")
    assert i18n.tr("scan.step_sizes", total_files=3) == (
        "Paso 1/2: revisando tamaños... (3 archivos)")


def test_a_missing_key_shows_the_key():
    assert i18n.tr("no.such.key") == "no.such.key"


def test_an_unknown_language_falls_back_to_english():
    i18n.set_language("fr")
    assert i18n.get_language() == "en"


def test_the_saved_language_wins_over_the_system():
    assert i18n.resolve_language("es") == "es"
    assert i18n.resolve_language("en") == "en"


def test_without_a_saved_language_the_system_decides(monkeypatch):
    monkeypatch.setattr(i18n, "detect_system_language", lambda: "es")
    assert i18n.resolve_language(config.LANGUAGE_AUTO) == "es"
    assert i18n.resolve_language("fr") == "es"


@pytest.mark.parametrize("variable", ["LC_ALL", "LC_MESSAGES", "LANG"])
@pytest.mark.parametrize("value, expected",
                         [("es_ES.UTF-8", "es"), ("en_US.UTF-8", "en"), ("de_DE", "en")])
def test_language_of_the_environment(monkeypatch, variable, value, expected):
    monkeypatch.setattr(i18n.sys, "platform", "linux")
    for name in ("LC_ALL", "LC_MESSAGES", "LANG"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(variable, value)
    assert i18n.detect_system_language() == expected


def test_the_language_is_saved_in_the_configuration(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert config.get_language() == config.LANGUAGE_AUTO
    config.set_language("es")
    assert config.get_language() == "es"
    config.set_language("fr")             # not a language of the app: ignored
    assert config.get_language() == "es"


@pytest.mark.parametrize("lang_id, expected", [(0x0C0A, "es"), (0x040A, "es"), (0x2C0A, "es"),
                                               (0x0409, "en"), (0x0407, "en")])
def test_language_of_windows(monkeypatch, lang_id, expected):
    class FakeKernel:
        class kernel32:
            GetUserDefaultUILanguage = staticmethod(lambda: lang_id)

    monkeypatch.setattr(i18n.sys, "platform", "win32")
    monkeypatch.setattr(i18n.ctypes, "windll", FakeKernel, raising=False)
    assert i18n.detect_system_language() == expected
