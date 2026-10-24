"""The architecture rules, checked on every run: which layer may import which.

    presentation   ->  application, domain, i18n
    application    ->  domain, i18n        (the disk and the outside world only through ports)
    infrastructure ->  application, domain (it implements the ports)
    domain         ->  nothing             (data and rules, no input or output)
    i18n           ->  nothing

`bootstrap.py` (and `__main__.py`) is the composition root: it is the only module allowed to
know every layer. The rules read the source with `ast`, so they need no window and run in
a fraction of a second.
"""

import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[1] / "src" / "duplicate_finder"
NAME = "duplicate_finder"

# layer -> the layers of the package it may import
ALLOWED = {
    "domain": set(),
    "application": {"domain", "i18n"},
    "infrastructure": {"domain", "application", "i18n"},
    "presentation": {"application", "domain", "i18n"},
    "i18n": set(),
}

# What a layer may not import from the standard library or from outside, because it would be
# input/output or a graphical library in a place where there must be none.
FORBIDDEN_MODULES = {
    "domain": {"tkinter", "customtkinter", "PIL", "shutil", "csv", "json", "logging", "ctypes",
               "threading", "subprocess", "socket", "pathlib"},
    "application": {"tkinter", "customtkinter", "PIL", "shutil", "csv", "json", "ctypes",
                    "subprocess", "socket"},
    "presentation": {"shutil", "csv", "json"},
}

# Calls that touch the disk: not allowed in the domain nor in the use cases (they use a port).
DISK_CALLS = {
    "os": {"walk", "listdir", "makedirs", "mkdir", "remove", "rename", "replace", "rmdir",
           "scandir", "stat", "startfile", "unlink"},
    "os.path": {"exists", "isfile", "isdir", "getsize", "getmtime", "getctime", "realpath",
                "samefile", "islink"},
}


def _layer_of(path: Path) -> str | None:
    """The layer a module belongs to, or None for the composition root and the package files."""
    parts = path.relative_to(PACKAGE).parts
    return parts[0] if parts[0] in ALLOWED else None


def _imports(source: str) -> list[tuple[int, str]]:
    """(line, dotted module) of every absolute import in `source`.

    `from . import x` and `from .x import y` stay inside the layer, so they are fine; one that
    climbs out (`from .. import x`) is reported as the module "..".
    """
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found += [(node.lineno, alias.name) for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level > 1:
                found.append((node.lineno, ".."))
            elif node.level == 0:
                found.append((node.lineno, node.module or ""))
                if node.module == NAME:     # `from duplicate_finder import i18n` is a submodule
                    found += [(node.lineno, f"{NAME}.{alias.name}") for alias in node.names
                              if alias.name in ALLOWED]
    return found


def violations(source: str, layer: str) -> list[str]:
    """What `source`, a module of `layer`, does that the rules do not allow."""
    problems = []
    for line, module in _imports(source):
        top = module.split(".")[0]
        if module == "..":
            problems.append(f"line {line}: {layer} climbs out of its folder with a relative import")
        elif top == NAME:
            parts = module.split(".")
            target = parts[1] if len(parts) > 1 else None
            if target is None or target == layer:
                continue
            if target not in ALLOWED:
                problems.append(f"line {line}: {layer} imports {module}, which is not a layer")
            elif target not in ALLOWED[layer]:
                problems.append(f"line {line}: {layer} must not import {target} ({module})")
        elif top in FORBIDDEN_MODULES.get(layer, ()):
            problems.append(f"line {line}: {layer} must not import {top}")
    if layer in ("domain", "application"):
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Call):
                name = ast.unparse(node.func)
                if name == "open":
                    problems.append(f"line {node.lineno}: {layer} opens a file by itself")
                module, _, function = name.rpartition(".")
                if function in DISK_CALLS.get(module, ()):
                    problems.append(f"line {node.lineno}: {layer} touches the disk with {name}()")
    return problems


def _modules():
    return [(path, layer) for path in sorted(PACKAGE.rglob("*.py"))
            if (layer := _layer_of(path)) is not None]


def test_every_module_sits_in_a_known_layer_or_is_the_composition_root():
    root_files = {p.name for p in PACKAGE.glob("*.py")}
    assert root_files == {"__init__.py", "__main__.py", "bootstrap.py"}
    folders = {p.name for p in PACKAGE.iterdir() if p.is_dir() and p.name != "__pycache__"}
    assert folders == set(ALLOWED)


@pytest.mark.parametrize("path, layer", _modules(), ids=lambda v: getattr(v, "name", v))
def test_module_follows_the_layer_rules(path, layer):
    assert violations(path.read_text(encoding="utf-8"), layer) == []


def test_only_the_composition_root_builds_the_adapters():
    importers = [path.name for path, layer in _modules()
                 if any(module.startswith(f"{NAME}.infrastructure")
                        for _, module in _imports(path.read_text(encoding="utf-8")))
                 and layer != "infrastructure"]
    assert importers == []


# ---- the checker itself must notice a violation (otherwise the rules above prove nothing)
@pytest.mark.parametrize("layer, source, expected", [
    ("domain", "from duplicate_finder.infrastructure import hashing",
     "must not import infrastructure"),
    ("domain", "from duplicate_finder import i18n", "must not import i18n"),
    ("domain", "import tkinter", "must not import tkinter"),
    ("domain", "import os\nos.walk('.')", "touches the disk"),
    ("application", "from duplicate_finder.presentation import styles",
     "must not import presentation"),
    ("presentation", "from ..infrastructure import settings", "climbs out"),
    ("application", "import os\nos.path.exists('x')", "touches the disk"),
    ("application", "open('x')", "opens a file"),
    ("application", "import shutil", "must not import shutil"),
    ("presentation", "from duplicate_finder.infrastructure.settings import JsonSettingsStore",
     "must not import infrastructure"),
    ("infrastructure", "from duplicate_finder.presentation import styles",
     "must not import presentation"),
    ("i18n", "from duplicate_finder.domain import filters", "must not import domain"),
])
def test_the_checker_catches_a_violation(layer, source, expected):
    assert any(expected in problem for problem in violations(source, layer))


def test_the_checker_lets_a_legal_import_through():
    assert violations("from duplicate_finder.domain.filters import ScanFilter", "application") == []
