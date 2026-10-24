# Documentación

[English](README.md) · **Español**

Tres PDF, con portada, índice y contenido, cada uno en español y en inglés:

- [`manual-de-usuario.pdf`](manual-de-usuario.pdf) / [`user-manual.pdf`](user-manual.pdf): para quien usa la app.
- [`proceso-de-creacion.pdf`](proceso-de-creacion.pdf) / [`creation-process.pdf`](creation-process.pdf): fases y decisiones del proyecto.
- [`guia-del-codigo.pdf`](guia-del-codigo.pdf) / [`code-guide.pdf`](code-guide.pdf): cómo funciona el código por dentro.

`origin/` guarda el script de consola original (`buscar_duplicados.py`), el primer paso del proyecto.

## Regenerarlos

Solo hace falta si cambias algo de la app o de los textos. Desde la raíz del repositorio:

```bash
pip install -r requirements.txt -r requirements-docs.txt
python docs/capture.py dark es     # capturas, tema oscuro, interfaz en español (docs/img/es/)
python docs/capture.py light es    # ... y el tema claro
python docs/capture.py dark en     # lo mismo con la interfaz en inglés (docs/img/en/)
python docs/capture.py light en
python docs/record_gif.py es       # el GIF del README (docs/img/es/demo.gif); `en` para inglés
python docs/gen_cover.py           # la imagen para compartir el repositorio (inglés; `es` para español)
python docs/gen_manual.py          # los dos idiomas; `es` o `en` para generar uno solo
python docs/gen_process.py
python docs/gen_code_guide.py
```

- `content/`: el texto de cada PDF, un módulo por idioma (`manual_es.py`, `manual_en.py`...).
- `_pdf_common.py`: portada, índice (con números de página) y estilos compartidos.
- `capture.py`: abre la app, monta carpetas de ejemplo en `C:\Demo` (cámbialo con la variable `CAPTURE_BASE`; la carpeta de salida, con `CAPTURE_OUTPUT`) y hace las capturas. Los archivos de ejemplo tienen nombres en el idioma de la interfaz, y usa una ruta neutra para que no salga tu nombre de usuario de Windows.
- `record_gif.py`: graba `img/<idioma>/demo.gif` (escanear → mover → deshacer) sobre carpetas de ejemplo.
- `gen_cover.py`: crea `img/social-preview.png`, la imagen que se ve al compartir el repositorio.
- `img/es/`, `img/en/`: capturas usadas por el manual y los README (`*_light.png` es el tema claro).

Los scripts de imagen abren la app de verdad y capturan **solo su ventana**. Hacen falta Pillow y escritorio de Windows.
