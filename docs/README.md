# Documentation

**English** · [Español](README.es.md)

Three PDFs, with cover, table of contents and content (currently in Spanish):

- [`manual-de-usuario.pdf`](manual-de-usuario.pdf): for people who use the app.
- [`proceso-de-creacion.pdf`](proceso-de-creacion.pdf): phases and decisions of the project.
- [`guia-del-codigo.pdf`](guia-del-codigo.pdf): how the code works inside.

`origin/` keeps the original console script (`buscar_duplicados.py`), the first step of the project.

## Regenerating them

Only needed if you change something in the app or in the texts. From the repository root:

```bash
pip install -r requirements.txt -r requirements-docs.txt
python docs/capture.py          # redo the dark screenshots (docs/img/)
python docs/capture.py light    # and the light-theme ones
python docs/record_gif.py       # the README GIF
python docs/gen_manual.py
python docs/gen_process.py
python docs/gen_code_guide.py
```

- `_pdf_common.py`: cover, table of contents (with page numbers) and shared styles.
- `capture.py`: opens the app, builds sample folders in `C:\Demo` (change it with the `CAPTURAS_BASE` variable) and takes the screenshots. It uses a neutral path so your Windows user name does not show up.
- `capture.py light`: the same with the light theme (`*_claro.png`).
- `record_gif.py`: records `img/demo.gif` (scan → move → undo) on sample folders.
- `gen_cover.py`: creates `img/social-preview.png`, the image shown when the repository is shared.
- `img/`: screenshots used by the manual and the README.

The three image scripts open the real app and capture **only its window**. They need Pillow and a Windows desktop.
