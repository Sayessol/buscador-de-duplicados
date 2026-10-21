# Duplicate Finder

**English** · [Español](README.md)

[![Tests](https://github.com/Sayessol/buscador-de-duplicados/actions/workflows/tests.yml/badge.svg)](https://github.com/Sayessol/buscador-de-duplicados/actions/workflows/tests.yml)
![Python 3.12](https://img.shields.io/badge/python-3.12-blue)
![Windows](https://img.shields.io/badge/platform-Windows-lightgrey)
![MIT License](https://img.shields.io/badge/license-MIT-green)
![Learning project](https://img.shields.io/badge/learning-project-2ea44f)
![Built with Claude](https://img.shields.io/badge/built%20with-Claude%20as%20copilot-D97757)

A Windows desktop app that **finds duplicate files and similar photos** and helps you tidy them up safely.

> **Golden rule: the app never deletes or modifies your original files.**
> It only reads, and only *moves* files to a quarantine folder when you confirm. Everything can be undone.
>
> The only time the app deletes anything is when you **undo a copy**: it removes the copies it created itself, and asks for confirmation first.

<p align="center">
  <img src="docs/img/demo.gif" alt="Demo: scan, move to quarantine and undo" width="860">
</p>

<p align="center">
  <a href="https://github.com/Sayessol/buscador-de-duplicados/releases/latest/download/Buscador-de-duplicados.exe"><b>⬇ Download for Windows (.exe)</b></a>
  · <a href="https://github.com/Sayessol/buscador-de-duplicados/releases/latest/download/Buscador-de-duplicados-portable.zip">ZIP version</a> if your antivirus blocks the <code>.exe</code> · no Python needed
</p>

It was born from a need of mine and from a 150-line script ([`docs/origen/buscar_duplicados.py`](docs/origen/buscar_duplicados.py)), and grew into a full application with a GUI, automated tests, continuous integration and a single-file `.exe`. [Here is how it started](#how-this-project-started).

> 📚 **Learning project.** I built it to go deeper into Python starting from a basic level, with Claude as a copilot. [Further down](#why-this-project-exists) I explain what that means.

> The interface and the PDF documentation are in Spanish (Spain).

## Features

| Tab | What it does |
|---|---|
| **Exact duplicates** (*Duplicados exactos*) | Finds files that are identical byte for byte, even with different names. Shows thumbnails and a preview, and picks the main copy for you. |
| **Similar photos** (*Fotos parecidas*) | Groups the same photo saved several times: recompressed, downscaled or with a filter applied. Keeps the best-quality copy. |
| **Gather images** (*Reunir imágenes*) | Collects photos scattered across many subfolders into one place (move or copy, file by file or whole folder). |

Also:

- **Simple / Advanced mode.** Starts in Simple (pick folder → scan → move) and remembers your choice.
- **History and undo.** Every move is logged and can be reverted.
- **Image viewer** with zoom and pan to compare details.
- **Light, dark or automatic theme** (follows Windows), WCAG AA contrast, and disabled buttons that are clearly different from error buttons.
- **Filters** by category (images, audio, video, documents, archives), extension, name, folder and size.

<details>
<summary>Screenshots (they follow your GitHub theme)</summary>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/img/02_avanzada.png">
  <img alt="Advanced mode" src="docs/img/02_avanzada_claro.png">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/img/04_parecidas.png">
  <img alt="Similar photos" src="docs/img/04_parecidas_claro.png">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/img/05_reunir.png">
  <img alt="Gather images" src="docs/img/05_reunir_claro.png">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/img/07_historial.png">
  <img alt="History and undo" src="docs/img/07_historial_claro.png">
</picture>

</details>

## How this project started

I have always kept backups of my old devices, such as phones or computers, on external hard drives of several terabytes. Over time, many files end up duplicated in subfolders, and that ends up eating the disk space.

Checking by hand is tedious, and it even gets confusing once you no longer know which folders you have already reviewed. My starting idea was to run quick, simple commands that compare images and other kinds of files and tell me right away whether there were duplicates. I found that the fastest way to do it was to use Python.

I started with a simple script of about 150 lines ([`docs/origen/buscar_duplicados.py`](docs/origen/buscar_duplicados.py)): I typed in a folder path and it told me whether there were duplicate files and how many it had analysed. After using it a few times I realised it was impractical: typing the path every time was slow. So I decided to build an interface to make it easier to use.

While building the interface I saw that I could add features that fitted the search better to what I wanted. That is how what began as a script became a complete desktop program with several features and filtering options.

| Stage | What existed |
|---|---|
| 1. A need | Backups with duplicate files eating the disk space |
| 2. A script | 150 lines: a path as input, and it told me whether there were duplicates and how many files it analysed |
| 3. An interface | So I would not have to type the path every time |
| 4. A desktop program | Several features and filtering options, made to fit what I wanted |

## Why this project exists

On top of solving that need, this is a **learning project**. I built it to **go deeper into Python and learn**, starting from a **basic level**: I wanted to tackle a real problem from start to finish, not just isolated exercises.

To get there, the project touches topics that rarely show up in first exercises: duplicate-detection algorithms (hashing, perceptual hashing, BK-tree), threads and queues so a window never freezes, graphical interfaces, automated tests, continuous integration and packaging a program for Windows.

**What this means for a reviewer:** this is not expert-level code, and I do not present it as such. It is a learning exercise taken seriously, with its limits in plain sight (see [Known limitations](#known-limitations)). The improvements I make from now on will be listed in the [CHANGELOG](CHANGELOG.md) and are part of that learning.

## What I learned

- **What was hardest:** how to split the code so that no file ended up too long. It shows in the current structure: the logic (`core/`) separate from the interface (`ui/`) and one component per tab.
- **What I learned most:** how versatile Python is for running scripts directly on files: with very few lines you can walk through a disk, compare contents and move files.

## How it was made: with Claude as a copilot

I built it **working with [Claude](https://claude.com/claude-code) (Anthropic) as a programming copilot**, and I want that to be clear:

- **I (Sayessol)** decided what to build and in which order, tested the app by hand, raised the doubts and problems I found along the way (for example, whether it moved folders instead of photos) and approved each step as we went.
- **Claude** wrote the code, tests and documentation, proposed alternatives and explained its decisions, always within the project's rules (such as never deleting the originals). The [code guide](docs/guia-del-codigo.pdf) (in Spanish) is written precisely so one can learn from that code.
- **That is why I do not present this code as written by me alone.** What is mine is the goal, what was decided to build, and the learning I am after.
- **The tests are the safety net**: no change counts as done without all 128 tests passing, and CI runs them again on every push.
- Commits carry a `Co-Authored-By: Claude` line so the shared authorship is visible in the history.

## Download and run

If you just want to use it, grab one of these files from **[Releases](https://github.com/Sayessol/buscador-de-duplicados/releases)**:

| File | When to use it |
|---|---|
| `Buscador-de-duplicados.exe` | A single file: double-click and go. The most convenient. |
| `Buscador-de-duplicados-portable.zip` | Unzip it into a folder with a **short path** (for example `C:\Apps`) and run the `.exe` inside. **Use it if your antivirus blocks or delays the single `.exe`.** |

> **Windows and antivirus warnings.** The program is not code-signed (certificates are paid), so SmartScreen may warn you. Also, the single-file `.exe` unpacks itself into a temp folder every time it starts, and some antivirus products (Avast, for instance) hold it for a few minutes the first time. The ZIP version extracts nothing at startup and gives far fewer problems.

From source (Python 3.12 on Windows):

```bash
pip install -r requirements.txt
python app.py
```

Build your own:

```bash
python construir_exe.py                  # single file:    dist/duplicados.exe
python construir_exe.py --carpeta --zip  # folder + ZIP:   dist/Buscador-de-duplicados.zip
```

## How it works

**Exact duplicates: 3 passes**, to read as little as possible:

1. **Size.** Files are grouped by byte size. A unique size cannot have a duplicate, so it is never read.
2. **Partial hash.** For files sharing a size, a BLAKE2b hash of the first 64 KB.
3. **Full hash.** Only for files that still match. A full-hash match means identical content.

**Similar photos** (`core/perceptual.py`): a **64-bit dHash** perceptual hash (compares adjacent pixels on a small grayscale thumbnail) plus a **4×4 colour signature**. Matching uses a **BK-tree** over Hamming distance, avoiding all-pairs comparison, and **Union-Find** to merge chains (A~B and B~C ⇒ {A, B, C}). It handles recompression, rescaling and filters; it does **not** detect crops or rotations.

**Responsive UI:** heavy work runs in a worker thread and posts messages to a `queue.Queue`; the main thread polls it with `after()` and is the only one touching widgets (Tkinter is not thread-safe).

**Safe moving:** `shutil.move`, name collisions resolved as `name (1).ext`, the quarantine folder cannot be inside the scanned folder, and a CSV log for every operation.

### Design decisions

| Decision | Why |
|---|---|
| **Never delete your originals; move to quarantine** | A bug in the app cannot cost you data. Whatever is moved can be put back. |
| **BLAKE2b** | In the standard library, faster than SHA-256 and more than reliable enough to detect identical files. |
| **Partial hash before full hash** | Most same-size files already differ in the first 64 KB, so they are never read in full. |
| **dHash instead of OpenCV** | Covers recompression, rescaling and filters at very low cost. OpenCV (for crops and rotations) would multiply the `.exe` size. |
| **Logic (`core/`) separate from UI (`ui/`)** | `core/` imports nothing from the window, so it can be tested entirely from the console and with pytest. |
| **One tab = one component** | `ui/main_window.py` is a ~200-line shell; each tab is a component with its own state (`PestanaExactos`, `PestanaParecidas`, `PestanaReunir`) and the window only passes it the mode and the close signal. |

### Performance

`python pruebas/benchmark.py` generates 4,000 files (830 MB, with exact copies and deliberate "near duplicates") and compares against hashing all content:

| Method | Time | Bytes read |
|---|---|---|
| Hash everything (naive) | 2.02 s | 830 MB (100 %) |
| **3 passes (this app)** | **0.90 s** | **284 MB (34 %)** |

Both find **exactly the same 386 groups**. It reads 66 % less data. Timings are with files in the OS cache; on a "cold" disk the gap in favour of the 3 passes is larger, because reading dominates.

## Code quality

- **128 pytest tests** (15 logic and window suites + 113 unit tests), with **93 % coverage of the core and 79 % of the interface**.
- **ruff** as linter and **mypy** to check the types of the core (`core/`, fully annotated), and everything runs on **GitHub Actions** on every push.
- **Error log** in a file (`%APPDATA%\BuscadorDuplicados\registro\buscador.log`), with rotation, and a clear notice to the user if something unexpected fails. Tests never touch the app's real data.
- Tests **use no mocks for the file system**: they create real files in temp folders and check the result on disk (including a check that *files* are moved, not folders).
- **WCAG AA contrast** in light and dark themes, verified by measurement.

```
core/      Pure logic, no UI (standard library + Pillow for photos)
ui/        CustomTkinter interface; one component per tab (pestana_*.py)
pruebas/   15 suites + unit tests + benchmark
docs/      User manual, code guide and build process (PDF, Spanish)
```

```bash
pip install -r requirements-dev.txt
pytest                    # everything (window tests need a Windows desktop)
pytest -m "not gui"       # logic only, no windows
pytest --cov              # with coverage (core and interface)
ruff check .
python -m mypy            # core type check
```

## Known limitations

- **Cannot read phones connected over USB** (MTP/PTP mode): Windows gives them no real folder path. Copy the photos to the PC first, or use a card reader.
- Similar photos do not detect crops or rotations.
- Windows only.

## Suggestions

There is no fixed roadmap: I will keep improving the application as I go, depending on which features I find it lacks in practice. **If you have ideas for future features, I would love to hear them**: open an issue with the "Sugerencia" template.

## License

[MIT](LICENSE) © 2026 Sayessol
