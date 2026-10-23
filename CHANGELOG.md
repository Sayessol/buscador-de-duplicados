# Registro de cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## [Unreleased]

### Changed
- Code, comments and docstrings are in English (`pruebas/` is now `tests/`, modules and names renamed). The interface text is unchanged.
- The data the app saves is in English too. `history.json` replaces `historial.json`: the old file is still read, converted on the fly, and never modified, so it stays as a backup. `config.json` keys and values are converted on load and a `config.json.bak-1.0` copy is kept before the first rewrite.
- The error log is `%APPDATA%\BuscadorDuplicados\logs\app.log`, and `DUPLICATE_FINDER_DEBUG` turns on the detailed log (the old `BUSCADOR_DEBUG` still works).
- The build flag `--carpeta` is now `--folder` (and the `FORMATO` variable is `BUILD_FORMAT`), the icon file is `icon.ico`, the CI workflows and the GitHub issue templates are in English (the templates are `Bug report` and `Suggestion`).
- Files and folders the app creates inside the user's folders have fixed English names: `_log_quarantine_<date>.csv`, `_log_gather_<date>.csv`, `_outside_scanned_folder` and the default `duplicates_report.csv`.

### Fixed
- Undoing a copy now retries for a moment when Windows reports the copied file as in use (antivirus, indexer) before reporting a failure.

## [1.0.0] - 2026-10-21

Primera versión pública.

### Funciones
- **Duplicados exactos** en 3 pasadas (tamaño → hash parcial → hash completo, BLAKE2b), con miniaturas, vista previa y elección automática de la copia principal.
- **Fotos parecidas** (dHash + firma de color, BK-tree y Union-Find): la misma foto recomprimida, reescalada o con un filtro. Los grupos se reparten en páginas (con «Anterior» / «Siguiente») para que, con miles de fotos, la galería se vea entera y mantenga su barra de desplazamiento.
- **Reunir imágenes**: por archivos o carpeta entera, mover o copiar, con un diálogo para los archivos que no son imágenes.
- Mover a cuarentena con confirmación y CSV de registro; historial y deshacer.
- Modo Sencilla / Avanzada, tema claro / oscuro / automático con contraste AA, filtros por categoría, extensión, nombre, carpeta y tamaño, y visor de imagen con zoom.
- Interfaz en español de España. La versión se muestra en el título de la ventana y en la cabecera.
- Lema: «Nunca se borran tus originales». La única vez que la app borra algo es al deshacer una copia: elimina las copias que ella misma creó, tras pedir confirmación.

### Descarga
- `.exe` de un solo archivo y ZIP portable con carpeta (los antivirus retienen mucho menos el ZIP).

### Calidad
- **169 pruebas con pytest**: 15 suites que ejercitan la lógica y la ventana de verdad, más 154 pruebas unitarias (71 de ellas de contraste WCAG AA, 4,5:1, para cada pareja de texto y fondo en los dos temas).
- **Cobertura**: 93 % del núcleo y 79 % de la interfaz; el CI exige un mínimo del 90 % y del 70 %.
- **ruff** (estilo) y **mypy** (tipos del núcleo, completamente anotado), en el CI con GitHub Actions. Dependabot avisa de actualizaciones.
- **Registro de errores** en un archivo con rotación (`%APPDATA%\BuscadorDuplicados\logs\app.log`): los hilos de trabajo y la interfaz anotan sus errores con el traceback, y la app avisa una vez de dónde está el registro.
- Las pruebas usan un `%APPDATA%` temporal, y una comprobación común avisa si alguna toca los datos reales de la app.
- **Arquitectura**: la lógica (`core/`) está separada de la interfaz (`ui/`); cada pestaña es un componente con su propio estado y la ventana principal es una carcasa de ~200 líneas. El escaneo está repartido en una función por pasada.
- Benchmark (`tests/benchmark.py`): las 3 pasadas leen un 66 % menos de datos que hashear todo y encuentran exactamente los mismos grupos.
- Si la aplicación se ejecuta sin consola y una librería escribe un aviso, no se cae.

### Documentación
- README en español e inglés (con «Cómo nació este proyecto», «Por qué existe», «Qué he aprendido», «Lo que encontré probándola» y «Sugerencias»); manual de usuario, guía del código y proceso de creación en PDF, en primera persona.
