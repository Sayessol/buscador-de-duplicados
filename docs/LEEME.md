# Documentación

Tres PDF, con portada, índice y contenido (en español):

- [`manual-de-usuario.pdf`](manual-de-usuario.pdf): para quien usa la app.
- [`proceso-de-creacion.pdf`](proceso-de-creacion.pdf): fases y decisiones del proyecto.
- [`guia-del-codigo.pdf`](guia-del-codigo.pdf): cómo funciona el código por dentro.

`origen/` guarda el script de consola original (`buscar_duplicados.py`), el primer paso del proyecto.

## Regenerarlos

Solo hace falta si cambias algo de la app o de los textos. Desde la raíz del repositorio:

```bash
pip install -r requirements.txt -r requirements-docs.txt
python docs/capturar.py          # rehace las capturas oscuras (docs/img/)
python docs/capturar.py claro    # y las del tema claro
python docs/grabar_gif.py        # el GIF del README
python docs/gen_manual.py
python docs/gen_proceso.py
python docs/gen_guia_codigo.py
```

- `_pdf_comun.py`: portada, índice (con números de página) y estilos compartidos.
- `capturar.py`: abre la app, monta carpetas de ejemplo en `C:\Demo` (cámbialo con la variable `CAPTURAS_BASE`) y hace las capturas. Usa una ruta neutra para que no salga tu nombre de usuario de Windows.
- `capturar.py claro`: lo mismo con el tema claro (`*_claro.png`).
- `grabar_gif.py`: graba `img/demo.gif` (escanear → mover → deshacer) sobre carpetas de ejemplo.
- `generar_portada.py`: crea `img/social-preview.png`, la imagen que se ve al compartir el repositorio.
- `img/`: capturas usadas por el manual y el README.

Los tres scripts de imagen abren la app de verdad y capturan **solo su ventana**. Hacen falta Pillow y escritorio de Windows.
