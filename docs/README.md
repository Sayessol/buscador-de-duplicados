# Documentation

**English** · [Español](README.es.md)

Three PDFs, with cover, table of contents and content, each in English and in Spanish:

- [`user-manual.pdf`](user-manual.pdf) / [`manual-de-usuario.pdf`](manual-de-usuario.pdf): for people who use the app.
- [`creation-process.pdf`](creation-process.pdf) / [`proceso-de-creacion.pdf`](proceso-de-creacion.pdf): phases and decisions of the project.
- [`code-guide.pdf`](code-guide.pdf) / [`guia-del-codigo.pdf`](guia-del-codigo.pdf): how the code works inside.

`origin/` keeps the original console script (`buscar_duplicados.py`), the first step of the project.

## Regenerating them

Only needed if you change something in the app or in the texts. From the repository root:

```bash
pip install -r requirements.txt -r requirements-docs.txt
python docs/capture.py dark es     # screenshots, dark theme, Spanish interface (docs/img/es/)
python docs/capture.py light es    # ... and the light theme
python docs/capture.py dark en     # the same with the English interface (docs/img/en/)
python docs/capture.py light en
python docs/record_gif.py es       # the README GIF (docs/img/es/demo.gif); `en` for English
python docs/gen_cover.py           # the social preview image (English; `es` for Spanish)
python docs/gen_manual.py          # both languages; `es` or `en` to build just one
python docs/gen_process.py
python docs/gen_code_guide.py
```

- `content/`: the text of each PDF, one module per language (`manual_en.py`, `manual_es.py`...).
- `_pdf_common.py`: cover, table of contents (with page numbers) and shared styles.
- `capture.py`: opens the app, builds sample folders in `C:\Demo` (change it with the `CAPTURE_BASE` variable; the output folder with `CAPTURE_OUTPUT`) and takes the screenshots. The sample files have names in the language of the interface, and it uses a neutral path so your Windows user name does not show up.
- `record_gif.py`: records `img/<language>/demo.gif` (scan → move → undo) on sample folders.
- `gen_cover.py`: creates `img/social-preview.png`, the image shown when the repository is shared.
- `img/es/`, `img/en/`: screenshots used by the manual and the READMEs (`*_light.png` is the light theme).

The image scripts open the real app and capture **only its window**. They need Pillow and a Windows desktop.
