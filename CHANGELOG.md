# Changelog

Based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed
- Code, comments and docstrings are in English (`pruebas/` is now `tests/`, modules and names renamed).
- The data the app saves is in English too. `history.json` replaces `historial.json`: the old file is still read, converted on the fly, and never modified, so it stays as a backup. `config.json` keys and values are converted on load and a `config.json.bak-1.0` copy is kept before the first rewrite.
- The error log is `%APPDATA%\BuscadorDuplicados\logs\app.log`, and `DUPLICATE_FINDER_DEBUG` turns on the detailed log (the old `BUSCADOR_DEBUG` still works).
- The build flag `--carpeta` is now `--folder` (and the `FORMATO` variable is `BUILD_FORMAT`), the icon file is `icon.ico`, the CI workflows and the GitHub issue templates are in English (the templates are `Bug report` and `Suggestion`).
- Files and folders the app creates inside the user's folders have fixed English names: `_log_quarantine_<date>.csv`, `_log_gather_<date>.csv`, `_outside_scanned_folder` and the default `duplicates_report.csv`.

- The code lives in the package `src/duplicate_finder`, split into layers: `domain` (data and rules, no input or output), `application` (the use cases), `infrastructure` (disk, history, settings, logs, Pillow) and `presentation` (the interface), plus `i18n`. `python app.py` still starts the app, and so does `python -m duplicate_finder`. Nothing changes for the user.
- The use cases reach the disk, the file hashes, the images, the history and the settings through ports (interfaces) that the infrastructure implements; `bootstrap.py` is the only place that wires them. The domain no longer reads the disk. Nothing changes for the user.
- Moving to quarantine and gathering images now record their own history entry (the interface no longer does), and the three tabs that move files share their dialogs (choosing the quarantine folder, the warnings and the offer to open the folder). Nothing changes for the user.
- The biggest tab (`exact_duplicates_tab.py`, 900 lines) is split into components: the scan options panel and the preview panel are their own classes, and a `BackgroundJob` helper replaces the thread, queue and polling code that the scan, the quarantine, the analysis and the gather each wrote by hand. Nothing changes for the user.
- An automatic test (`tests/test_architecture.py`) checks the layer rules on every run: the domain imports nothing from the other layers and does no input or output, the use cases reach the disk only through ports, the interface never imports the infrastructure, and only `bootstrap.py` builds the adapters.
- The folders suggested for grouping the files that are not images (`Documents`, `Music`, `Videos`, `Archives`, `Other`) are English, like the other names the app creates inside your folders; you can still type your own.
- The README is in English (`README.md`) and Spanish (`README.es.md`) with a new Architecture section (layers, ports and adapters, the composition root and the test that enforces them). It no longer quotes exact test counts, which went stale with every change. The `docs/` guide is bilingual too, and this changelog is fully in English.
- The three PDFs (user manual, code guide, creation process) are available in English and Spanish, written from one content module per language, and they describe the current architecture instead of the old `core/` and `ui/` folders. The screenshots, the demo GIF and the social preview are generated per language (`docs/img/es`, `docs/img/en`).

### Added
- The interface is available in English and Spanish. The first time it follows the language of Windows; the header has a selector to change it (it applies the next time the app opens) and the choice is remembered. The texts live in `src/duplicate_finder/i18n/locales/` (one catalog per language) and a test checks that both have the same keys and placeholders, and that every text the code asks for exists.
- The column names of the CSV files follow the language of the interface (in Spanish they are the same as always).

### Security
- Pillow is updated from 12.3.0 to 13.0.0, which fixes the known vulnerabilities `pip-audit` reports for 12.3.0 (the app opens images the user chooses). Nothing changes for the user: the tests pass and the 32 documentation screenshots are pixel-identical.

### Fixed
- Undoing a copy now retries for a moment when Windows reports the copied file as in use (antivirus, indexer) before reporting a failure.

## [1.0.0] - 2026-10-21

First public version.

### Features
- **Exact duplicates** in 3 passes (size → partial hash → full hash, BLAKE2b), with thumbnails, preview and automatic choice of the main copy.
- **Similar photos** (dHash + colour signature, BK-tree and Union-Find): the same photo recompressed, rescaled or with a filter. Groups are split into pages ("Previous" / "Next") so that, with thousands of photos, the gallery shows in full and keeps its scrollbar.
- **Gather images**: by files or whole folder, move or copy, with a dialog for the files that are not images.
- Move to quarantine with confirmation and a CSV log; history and undo.
- Simple / Advanced mode, light / dark / automatic theme with AA contrast, filters by category, extension, name, folder and size, and an image viewer with zoom.
- Interface in Spanish (Spain). The version shows in the window title and in the header.
- Motto: "Your originals are never deleted". The only time the app deletes anything is when undoing a copy: it removes the copies it created itself, after asking for confirmation.

### Download
- Single-file `.exe` and a portable ZIP with a folder (antivirus products hold the ZIP far less).

### Quality
- **196 pytest tests**: 15 suites that exercise the logic and the real window, plus 181 unit tests (71 of them WCAG AA contrast checks, 4.5:1, for every text and background pair in both themes).
- **Coverage**: 93 % of the core and 79 % of the interface; CI requires a minimum of 90 % and 70 %.
- **ruff** (style) and **mypy** (types of the core, fully annotated), in CI with GitHub Actions. Dependabot warns about updates.
- **Error log** in a rotating file (`%APPDATA%\BuscadorDuplicados\logs\app.log`): the worker threads and the interface record their errors with the traceback, and the app tells you once where the log is.
- Tests use a temporary `%APPDATA%`, and a shared check warns if any of them touches the app's real data.
- **Architecture**: the logic (`core/`) is separate from the interface (`ui/`); each tab is a component with its own state and the main window is a ~200-line shell. The scan is split into one function per pass.
- Benchmark (`tests/benchmark.py`): the 3 passes read 66 % less data than hashing everything and find exactly the same groups.
- If the application runs without a console and a library writes a warning, it does not crash.

### Documentation
- README in Spanish and English (with "How this project started", "Why this project exists", "What I learned", "What I found while testing it" and "Suggestions"); user manual, code guide and build process as PDFs, in the first person.
