# Contributing

Thanks for your interest in Duplicate Finder. This is a learning project that is kept to a clear
standard, so this page explains how to set it up and what a change has to meet. Issues and
pull requests are welcome in English or Spanish.

> **The golden rule:** the app never deletes or modifies a user's original files. It only reads,
> and *moves* files to a quarantine folder when the user confirms; everything can be undone. A
> change that breaks this rule will not be accepted.

## Set up

You need Windows and Python 3.12.

```bash
git clone https://github.com/Sayessol/buscador-de-duplicados.git
cd buscador-de-duplicados
pip install -r requirements-dev.txt     # or: pip install -e .[dev]
python app.py                           # run the app
pre-commit install                      # optional: run the checks before every commit
```

## What every change has to pass

The CI runs these on every pull request (`lint`, `types` and `tests` jobs). Run them locally first:

```bash
ruff check .                # lint (also sorts imports)
ruff format .               # formatting (use `--check` to only look)
python -m mypy              # types, whole package
pytest                      # all tests (the window tests need a Windows desktop)
pytest -m "not gui"         # logic only, no windows
pytest --cov                # with coverage: at least 90 % for the logic layers, 70 % for the UI
```

Tests never touch the real data of the app (they run with a temporary `%APPDATA%`).

## Where things go

The code lives in `src/duplicate_finder/`, in layers that only depend inwards:

| Layer | What it holds | May import |
|---|---|---|
| `domain/` | Pure rules and data, no input or output | nothing from the package |
| `application/` | Use cases (one class each) and the ports (interfaces) they need | `domain`, `i18n` |
| `infrastructure/` | Adapters that implement the ports: disk, hashes, Pillow, JSON, logging | `domain`, `application` |
| `presentation/` | The CustomTkinter interface | `application`, `domain`, `i18n` |
| `i18n/` | English and Spanish texts | nothing |

`bootstrap.py` is the composition root: the only place that builds the adapters and wires them
into the use cases. `tests/test_architecture.py` checks these rules, so a change in the wrong
layer fails the tests. The [code guide](docs/code-guide.pdf) explains the design and has a
recipe for adding a feature.

A few conventions:

- **Texts.** Every text the user sees goes through `tr("key")` and is added to **both** catalogs
  (`i18n/locales/en.py` and `es.py`) with the same placeholders; `tests/test_i18n.py` checks it.
  Never write an interface text in the code.
- **Code in English:** names, comments, docstrings and tests. Files and folders the app creates
  inside the user's folders have fixed English names.
- **Disk access** goes through the `FileSystem` port (and the other ports), not `os`/`open` in
  `domain/` or `application/`. Use the in-memory fakes in `tests/fakes.py` to test use cases.
- **Long tasks** run with `BackgroundJob` (thread + queue + polling); Tkinter widgets are only
  touched from the main thread.
- **Moving or copying files** goes through `FileTransfers` and is recorded in the history so it can
  be undone.

## Branches, commits and pull requests

- `main` is the published version; `develop` is where work is integrated. Branch from `develop`
  with a short name that describes the change (`fix/...`, `feat/...`, `refactor/...`, `docs/...`,
  `test/...`, `ci/...`) and open the pull request against `develop`.
- Write commit messages and PR titles in the
  [Conventional Commits](https://www.conventionalcommits.org/) style:
  `feat: ...`, `fix: ...`, `refactor: ...`, `docs: ...`, `test: ...`, `ci: ...`.
  Describe the change, not the conversation that led to it.
- Pull requests are merged with **squash**, so the PR title becomes the commit message; keep one
  topic per PR. The CI must be green.
- Add a line to the `[Unreleased]` section of [CHANGELOG.md](CHANGELOG.md) for anything a user or
  a developer would notice.
- If you change the interface, regenerate the screenshots and PDFs that show it
  (see [docs/README.md](docs/README.md)); a change that should not alter the look can be checked
  by comparing the screenshots before and after.

## Reporting a problem or suggesting something

Use the [issue templates](https://github.com/Sayessol/buscador-de-duplicados/issues/new/choose).
For a security problem, read [SECURITY.md](SECURITY.md) instead.
