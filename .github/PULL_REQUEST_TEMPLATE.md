## What and why

<!-- What changes, and why. The title should follow Conventional Commits (feat:, fix:, refactor:, docs:, test:, ci:) and describe the change. -->

## How it was checked

<!-- Tests added or changed, and anything you tried by hand. For interface changes: before/after screenshots or "the screenshots are pixel-identical". -->

## Checklist

- [ ] `ruff check .`, `ruff format --check .`, `python -m mypy` and `pytest` pass
- [ ] Each layer only imports what it may (the architecture test passes)
- [ ] New interface texts are in **both** catalogs (`en.py` and `es.py`)
- [ ] The original files of the user are still never deleted or modified
- [ ] `CHANGELOG.md` has a line under `[Unreleased]` (if a user or developer would notice)
- [ ] Docs, screenshots or PDFs updated if the change affects them
