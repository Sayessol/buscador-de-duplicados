"""Translations of every text the user sees: English (default) and Spanish.

The texts live in `core/locales/en.py` and `core/locales/es.py`, one dictionary each, with
the same keys and the same `{placeholders}` (a test checks both). Code asks for a text with
`tr("scan.finished")` or `tr("scan.step_sizes", total_files=n)`; nothing else in the
program contains text meant for the user.

The language is chosen at start-up (see `resolve_language`) and kept in the configuration;
changing it from the header takes effect the next time the app is opened.
"""

import ctypes
import locale
import os
import sys
from typing import Any

from .locales import en, es

LANGUAGES = ("en", "es")
LANGUAGE_NAMES = {"en": "English", "es": "Español"}
DEFAULT_LANGUAGE = "en"

_CATALOGS: dict[str, dict[str, str]] = {"en": en.MESSAGES, "es": es.MESSAGES}
_LANG_SPANISH = 0x0A      # primary language id of Spanish in Windows

_current = DEFAULT_LANGUAGE


def detect_system_language() -> str:
    """Language of the system: Spanish if Windows (or the environment) is Spanish, else English."""
    code = ""
    if sys.platform == "win32":
        try:
            windll = ctypes.windll
            lang_id = windll.kernel32.GetUserDefaultUILanguage()
            return "es" if (lang_id & 0x3FF) == _LANG_SPANISH else "en"
        except (AttributeError, OSError):
            pass
    for variable in ("LC_ALL", "LC_MESSAGES", "LANG"):
        code = os.environ.get(variable, "")
        if code:
            break
    else:
        try:
            code = locale.getlocale()[0] or ""
        except ValueError:
            code = ""
    return "es" if code.lower().startswith("es") else "en"


def resolve_language(saved: str) -> str:
    """The language to use: the saved one, or the system's when nothing valid was saved."""
    return saved if saved in LANGUAGES else detect_system_language()


def set_language(code: str) -> None:
    global _current
    _current = code if code in LANGUAGES else DEFAULT_LANGUAGE


def get_language() -> str:
    return _current


def tr(key: str, **params: Any) -> str:
    """The text for `key` in the current language, with `{placeholders}` filled from `params`.

    A key missing from the current language falls back to English; a key missing from both is a
    programming error, shown as the key itself so it is visible instead of crashing the window.
    """
    text = _CATALOGS[_current].get(key)
    if text is None:
        text = _CATALOGS[DEFAULT_LANGUAGE].get(key, key)
    return text.format(**params)
