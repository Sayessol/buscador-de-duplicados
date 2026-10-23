"""Use case: the settings of the user (view mode, theme and language), remembered between runs."""

from duplicate_finder import i18n
from duplicate_finder.application.ports import SettingsStore

LANGUAGE_AUTO = "auto"    # nothing chosen yet: follow the language of the system

MODES = ("simple", "advanced")
DEFAULT_MODE = "simple"

THEMES = ("auto", "light", "dark")   # auto = follow the system
DEFAULT_THEME = "auto"


class AppSettings:
    def __init__(self, store: SettingsStore) -> None:
        self._store = store

    def get_mode(self) -> str:
        mode = self._store.load().get("mode")
        return mode if mode in MODES else DEFAULT_MODE

    def set_mode(self, mode: str) -> None:
        self._set("mode", mode, MODES)

    def get_theme(self) -> str:
        theme = self._store.load().get("theme")
        return theme if theme in THEMES else DEFAULT_THEME

    def set_theme(self, theme: str) -> None:
        self._set("theme", theme, THEMES)

    def get_language(self) -> str:
        """The saved language ("en" | "es"), or "auto" when none was chosen yet."""
        language = self._store.load().get("language")
        return language if language in i18n.LANGUAGES else LANGUAGE_AUTO

    def set_language(self, language: str) -> None:
        self._set("language", language, i18n.LANGUAGES)

    def _set(self, key: str, value: str, allowed: tuple[str, ...]) -> None:
        if value not in allowed:
            return
        data = self._store.load()
        data[key] = value
        self._store.save(data)
