# Buscador de duplicados

[English](README.md) · **Español**

[![Pruebas](https://github.com/Sayessol/buscador-de-duplicados/actions/workflows/tests.yml/badge.svg)](https://github.com/Sayessol/buscador-de-duplicados/actions/workflows/tests.yml)
![Python 3.12](https://img.shields.io/badge/python-3.12-blue)
![Windows](https://img.shields.io/badge/plataforma-Windows-lightgrey)
![Licencia MIT](https://img.shields.io/badge/licencia-MIT-green)
![Proyecto de aprendizaje](https://img.shields.io/badge/proyecto-de%20aprendizaje-2ea44f)
![Hecho con Claude](https://img.shields.io/badge/hecho%20con-Claude%20como%20copiloto-D97757)

App de escritorio para Windows que **encuentra archivos duplicados y fotos parecidas**, y te ayuda a ordenarlos sin riesgo.

> **Regla de oro: la app nunca borra ni modifica tus archivos originales.**
> Solo lee, y solo *mueve* a una carpeta de cuarentena cuando tú lo confirmas. Todo se puede deshacer.
>
> La única vez que la app borra algo es al **deshacer una copia**: elimina las copias que ella misma creó, y antes te pide confirmación.

<p align="center">
  <img src="docs/img/demo.gif" alt="Demo: escanear, mover a cuarentena y deshacer" width="860">
</p>

<p align="center">
  <a href="https://github.com/Sayessol/buscador-de-duplicados/releases/latest/download/Buscador-de-duplicados.exe"><b>⬇ Descargar para Windows (.exe)</b></a>
  · <a href="https://github.com/Sayessol/buscador-de-duplicados/releases/latest/download/Buscador-de-duplicados-portable.zip">versión ZIP</a> si tu antivirus bloquea el <code>.exe</code> · no necesita instalar Python
</p>

Nació de una necesidad mía y de un script de 150 líneas ([`docs/origin/buscar_duplicados.py`](docs/origin/buscar_duplicados.py)), y creció hasta ser una aplicación completa con interfaz gráfica, pruebas automáticas, integración continua y un `.exe` de un solo archivo. [Aquí cuento cómo nació](#cómo-nació-este-proyecto).

> 📚 **Proyecto de aprendizaje.** Lo hice para profundizar en Python partiendo de un nivel básico, con Claude como copiloto. [Más abajo](#por-qué-existe-este-proyecto) explico qué significa eso.

## Qué hace

| Pestaña | Para qué sirve |
|---|---|
| **Duplicados exactos** | Encuentra archivos idénticos byte a byte, aunque tengan nombres distintos. Muestra miniatura y vista previa, y elige sola la copia principal. |
| **Fotos parecidas** | Agrupa la misma foto guardada varias veces: recomprimida, en menor resolución o con un filtro. Conserva la de mejor calidad. |
| **Reunir imágenes** | Junta en una carpeta común las fotos repartidas por muchas subcarpetas (mover o copiar, por archivos o carpeta entera). |

Además:

- **Modo Sencilla / Avanzada.** Arranca en Sencilla (carpeta → escanear → mover) y recuerda tu elección.
- **Historial y deshacer.** Cada movimiento queda registrado y se puede revertir.
- **Visor de imagen** con zoom y desplazamiento para comparar detalles.
- **Tema claro, oscuro o automático** (sigue a Windows), con contraste WCAG AA y botones deshabilitados claramente distintos de los de error.
- **Filtros** por categoría (imágenes, audio, vídeo, documentos, comprimidos), extensión, nombre, carpeta y tamaño.
- **Interfaz en inglés y en español.** Sigue el idioma de Windows, y un selector en la cabecera permite cambiarlo (se aplica la próxima vez que se abra la app).

<details>
<summary>Capturas (se adaptan a tu tema de GitHub)</summary>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/img/02_avanzada.png">
  <img alt="Modo Avanzada" src="docs/img/02_avanzada_claro.png">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/img/04_parecidas.png">
  <img alt="Fotos parecidas" src="docs/img/04_parecidas_claro.png">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/img/05_reunir.png">
  <img alt="Reunir imágenes" src="docs/img/05_reunir_claro.png">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/img/07_historial.png">
  <img alt="Historial y deshacer" src="docs/img/07_historial_claro.png">
</picture>

</details>

## Descarga y ejecución

Si solo quieres usarla, baja uno de estos archivos desde **[Releases](https://github.com/Sayessol/buscador-de-duplicados/releases)**:

| Archivo | Cuándo usarlo |
|---|---|
| `Buscador-de-duplicados.exe` | Un solo archivo: doble clic y listo. Es lo más cómodo. |
| `Buscador-de-duplicados-portable.zip` | Descomprímelo en una carpeta con **ruta corta** (por ejemplo `C:\Apps`) y abre el `.exe` de dentro. **Úsalo si tu antivirus bloquea o retrasa el `.exe` único.** |

> **Avisos de Windows y antivirus.** El programa no está firmado digitalmente (el certificado es de pago), así que SmartScreen puede avisar. Además, el `.exe` de un solo archivo se descomprime en una carpeta temporal cada vez que se abre, y algunos antivirus (por ejemplo Avast) lo retienen unos minutos la primera vez. La versión ZIP no extrae nada al arrancar y da muchos menos problemas.

Desde el código (Python 3.12 en Windows):

```bash
pip install -r requirements.txt
python app.py
```

Para generar tu propia versión:

```bash
python build_exe.py                  # un solo archivo: dist/duplicados.exe
python build_exe.py --folder --zip   # carpeta + ZIP:   dist/Buscador-de-duplicados.zip
```

## Arquitectura

El código está en el paquete `src/duplicate_finder/`, dividido en cuatro capas (una Clean Architecture pragmática) más un paquete transversal `i18n`. Las dependencias solo apuntan hacia dentro:

```mermaid
flowchart LR
    P["presentation<br/>ventanas y pestañas CustomTkinter"] --> A["application<br/>casos de uso + puertos"]
    P --> D["domain<br/>reglas y datos, sin E/S"]
    A --> D
    I["infrastructure<br/>disco, hashes, Pillow, archivos JSON"] -. implementa los puertos .-> A
    I --> D
    B["bootstrap.py<br/>raíz de composición"] --> P
    B --> I
```

| Capa | Qué contiene | Puede importar |
|---|---|---|
| `domain/` | Reglas y datos puros: filtros, grupos de duplicados, el algoritmo de similitud (BK-tree, Union-Find), la selección de qué conservar, las reglas de las transferencias | nada del paquete |
| `application/` | Una clase por caso de uso (`ScanDuplicates`, `FindSimilarPhotos`, `MoveToQuarantine`, `GatherImages`, …) y los **puertos** que necesitan (`FileSystem`, `FileHasher`, `FingerprintReader`, `HistoryStore`, `SettingsStore`) | `domain`, `i18n` |
| `infrastructure/` | Los adaptadores que implementan los puertos: sistema de archivos local (con reintentos si Windows bloquea un archivo), hashing BLAKE2b, huellas con Pillow, historial y ajustes en JSON, registro de errores | `domain`, `application` |
| `presentation/` | La interfaz CustomTkinter: ventana principal, un componente por pestaña, paneles reutilizables y `BackgroundJob` (hilo + cola + sondeo) | `application`, `domain`, `i18n` |
| `i18n/` | Los catálogos en inglés y español y `tr("clave")` | nada |

`bootstrap.py` es la **raíz de composición**: el único módulo que conoce todas las capas. Construye los adaptadores, los inyecta en los casos de uso y le entrega el resultado a la ventana. Los casos de uso reciben sus puertos en el constructor, así que las pruebas los ejecutan con dobles en memoria (`tests/fakes.py`) sin tocar el disco.

Estas reglas no son solo una convención: `tests/test_architecture.py` lee cada módulo con `ast` y falla si una capa importa algo que no debe (por ejemplo, `domain` importando `tkinter`, o `presentation` importando `infrastructure`) o si el dominio o los casos de uso tocan el disco directamente.

```
src/duplicate_finder/
  domain/           Reglas y datos puros (solo librería estándar)
  application/      Casos de uso y puertos
  infrastructure/   Adaptadores: disco, hashes, imágenes, JSON, registro
  presentation/     Interfaz CustomTkinter
  i18n/             Catálogos (en, es) y tr()
  bootstrap.py      Raíz de composición
tests/              Pruebas unitarias, de casos de uso, de arquitectura y de ventana, más un benchmark
docs/               Manual de usuario, guía del código y proceso de creación (PDF), herramientas de capturas
```

## Cómo funciona por dentro

**Duplicados exactos: 3 pasadas**, para leer lo mínimo posible:

1. **Tamaño.** Se agrupan los archivos por tamaño en bytes. Si un tamaño es único, no puede tener duplicado y no se lee.
2. **Hash parcial.** Para los que comparten tamaño, BLAKE2b de los primeros 64 KB.
3. **Hash completo.** Solo para los que siguen coincidiendo. Si el hash completo coincide, son idénticos.

**Fotos parecidas** (`domain/similarity.py`): hash perceptual **dHash de 64 bits** (compara píxeles adyacentes en una miniatura en gris) más una **firma de color 4×4**. La búsqueda usa un **BK-tree** sobre la distancia de Hamming, para no comparar todas contra todas, y **Union-Find** para unir cadenas (A~B y B~C ⇒ {A, B, C}). Detecta recompresión, reescalado y filtros; **no** detecta recortes ni rotaciones.

**Interfaz sin bloqueos:** el trabajo pesado va en un hilo y manda mensajes por una `queue.Queue`; el hilo principal los lee con `after()` y es el único que toca los widgets (Tkinter no es seguro entre hilos). Ese patrón vive en un solo sitio, `presentation/background_job.py`, y lo usan todas las tareas largas.

**Seguridad al mover:** `shutil.move`, nombres con colisión resueltos como `nombre (1).ext`, la cuarentena no puede estar dentro de la carpeta escaneada, y CSV de registro de cada operación.

### Decisiones de diseño

| Decisión | Por qué |
|---|---|
| **Nunca borrar tus originales; mover a cuarentena** | Un error de la app no puede costarte datos. Lo que se mueve se puede devolver. |
| **BLAKE2b** | Está en la librería estándar, es más rápido que SHA-256 y de sobra fiable para detectar archivos idénticos. |
| **Hash parcial antes del completo** | La mayoría de archivos con el mismo tamaño ya difieren en los primeros 64 KB; así no se leen enteros. |
| **dHash y no OpenCV** | Cubre recompresión, reescalado y filtros con muy poco peso. OpenCV (para recortes y rotaciones) multiplicaría el tamaño del `.exe`. |
| **Capas con puertos y adaptadores** | Las reglas y los casos de uso nunca tocan directamente el disco ni una ventana, así que se prueban sin ninguno de los dos, y la interfaz podría sustituirse sin tocarlos. |
| **Puertos solo donde hay E/S real** | El disco, el hashing, las imágenes, el historial y los ajustes tienen puerto. Los cálculos puros (filtros, similitud, selección) son funciones normales: una interfaz ahí no aportaría nada. |
| **Una pestaña = un componente** | Cada pestaña es dueña de su estado (`ExactDuplicatesTab`, `SimilarPhotosTab`, `GatherImagesTab`) y comparte paneles y diálogos con las demás; la ventana solo le pasa el modo y el cierre. |
| **Textos en catálogos, no en el código** | Todo texto de la interfaz pasa por `tr("clave")`; una prueba comprueba que inglés y español tienen las mismas claves y marcadores. |

### Rendimiento

`python tests/benchmark.py` genera 4.000 archivos (830 MB, con copias exactas y «casi duplicados» a propósito) y compara con hashear todo el contenido:

| Método | Tiempo | Bytes leídos |
|---|---|---|
| Hashear todo (ingenuo) | 2,02 s | 830 MB (100 %) |
| **3 pasadas (esta app)** | **0,90 s** | **284 MB (34 %)** |

Encuentran **exactamente los mismos 386 grupos**. Lee un 66 % menos de datos. Los tiempos son con los archivos en caché del sistema; en un disco «frío» la diferencia a favor de las 3 pasadas es mayor, porque ahí manda la lectura.

## Calidad del código

- **Pruebas automáticas con pytest** a varios niveles: unitarias, casos de uso contra dobles en memoria, reglas de arquitectura, migración de datos, internacionalización y pruebas de ventana que manejan la interfaz real. El CI exige al menos un **90 % de cobertura en las capas de lógica** y un **70 % en la interfaz**.
- **ruff** como linter y **mypy** sobre `domain`, `application`, `infrastructure` e `i18n` (totalmente anotados), todo ejecutado en **GitHub Actions** en cada push y pull request.
- **Registro de errores** en un archivo (`%APPDATA%\BuscadorDuplicados\logs\app.log`), con rotación, y un aviso claro al usuario si algo inesperado falla. Las pruebas nunca tocan los datos reales de la app.
- El comportamiento sobre el sistema de archivos se prueba **con archivos reales** en carpetas temporales (incluida la comprobación de que se mueven *archivos* y no carpetas); los dobles en memoria solo sirven para probar la lógica propia de los casos de uso.
- **Contraste WCAG AA** en tema claro y oscuro, comprobado con medición.

```bash
pip install -r requirements-dev.txt
pytest                    # todo (las pruebas de ventana necesitan escritorio de Windows)
pytest -m "not gui"       # solo lógica, sin abrir ventanas
pytest --cov              # con cobertura
ruff check .
python -m mypy            # tipos de las capas de lógica
```

## Documentación

Tres PDF con portada e índice, en [`docs/`](docs/) (por ahora en español):

- [Manual de usuario](docs/manual-de-usuario.pdf)
- [Guía del código](docs/guia-del-codigo.pdf): cómo está construida, pensada para quien quiere aprender.
- [Proceso de creación](docs/proceso-de-creacion.pdf): fases y decisiones.

El [CHANGELOG](CHANGELOG.md) (en inglés) recoge lo que cambia en cada versión.

## Cómo nació este proyecto

Siempre he guardado copias de seguridad de mis dispositivos antiguos, como teléfonos u ordenadores, en discos duros externos de varios teras. Con el tiempo, muchos archivos acaban duplicados en subcarpetas, y eso termina comiéndose el espacio del disco.

Revisarlo a mano es tedioso, y se vuelve incluso un lío cuando ya no sabes qué carpetas has revisado y cuáles no. Mi idea de partida era poder lanzar órdenes rápidas y sencillas que compararan imágenes y otros tipos de archivos y me dijeran enseguida si había duplicados o no. Descubrí que la forma más rápida de conseguirlo era usar Python.

Empecé con un script sencillo de unas 150 líneas ([`docs/origin/buscar_duplicados.py`](docs/origin/buscar_duplicados.py)): le introducía la ruta de una carpeta y me decía si había archivos duplicados y cuántos había analizado. Tras usarlo varias veces me di cuenta de que era poco práctico: tener que escribir la ruta cada vez era lento. Así que decidí crearle una interfaz para que fuese más fácil de usar.

Al construir la interfaz vi que podía añadirle funciones que adaptaran mejor la búsqueda a lo que yo quería. Así, lo que empezó siendo un script pasó a ser un programa de escritorio completo, con varias funciones y opciones de filtrado.

| Etapa | Qué había |
|---|---|
| 1. Una necesidad | Copias de seguridad con archivos duplicados que se comen el espacio del disco |
| 2. Un script | 150 líneas: una ruta de entrada, y me decía si había duplicados y cuántos archivos analizó |
| 3. Una interfaz | Para no tener que escribir la ruta cada vez |
| 4. Un programa de escritorio | Varias funciones y opciones de filtrado, hechas a medida de lo que yo quería |

## Por qué existe este proyecto

Además de resolver esa necesidad, es un **proyecto de aprendizaje**. Lo hice para **profundizar en Python y aprender**, partiendo de un **nivel básico**: quería enfrentarme a un problema real de principio a fin, y no solo a ejercicios sueltos.

Para conseguirlo, el proyecto toca temas que no suelen aparecer en los primeros ejercicios: algoritmos de búsqueda de duplicados (hashing, hash perceptual, BK-tree), hilos y colas para que una ventana no se quede bloqueada, interfaces gráficas, arquitectura por capas, internacionalización, pruebas automáticas, integración continua y empaquetado de un programa para Windows.

**Qué significa para quien lo revise:** no es código de una persona experta, y no lo presento como tal. Es un ejercicio de aprendizaje hecho en serio, con sus límites a la vista (ver [Limitaciones conocidas](#limitaciones-conocidas)). Las mejoras que vaya haciendo quedarán anotadas en el [CHANGELOG](CHANGELOG.md) y forman parte de ese aprendizaje.

## Qué he aprendido

- **Lo que más me costó:** cómo dividir el código para que no quedaran archivos demasiado largos y cada parte tuviera una sola tarea. La primera versión separaba la lógica de la interfaz; más tarde fui más allá y la organicé en capas (dominio, aplicación, infraestructura y presentación) con puertos y adaptadores, y partí las pestañas más grandes en componentes más pequeños.
- **Lo que más he aprendido:** la versatilidad de Python para ejecutar scripts directamente sobre los archivos: con muy pocas líneas se puede recorrer un disco, comparar contenidos y mover archivos. Y que una regla escrita como prueba (como las reglas de arquitectura) aguanta mucho mejor que una escrita en un documento.

## Lo que encontré probándola

Probé la app yo mismo, con mis propios archivos, y estos fueron los problemas que encontré y que cambiaron el programa:

- **El `.exe` no arrancaba.** Al descargar el ejecutable de la release me salió el error «Failed to start embedded python interpreter». Era mi antivirus (Avast), que retiene unos minutos el archivo único la primera vez que se abre. Por eso cada versión incluye también un ZIP con carpeta, que no tiene ese problema.
- **La galería de «Fotos parecidas» se cortaba.** Con muchas fotos, algunas imágenes aparecían cortadas y a la derecha había un hueco con aspecto de barra de desplazamiento que no existía. Resultó ser un límite de Windows con las ventanas muy altas, y ahora los grupos se reparten en páginas.
- **«Reunir imágenes» movía carpetas en vez de fotos.** Lo vi probándola y se corrigió; hay una prueba automática que lo comprueba.
- **Mis móviles no aparecían.** Pregunté si la app podía leer un teléfono conectado por USB. No es posible: Windows no les da una ruta de carpeta normal. Quedó anotado en las [limitaciones](#limitaciones-conocidas), con la solución de copiar antes las fotos al PC.
- **Las capturas no debían mostrar mi usuario de Windows.** Pedí que las imágenes y el GIF del README usaran una carpeta de ejemplo, y no una ruta con mi nombre.

## Cómo se ha hecho: con Claude como copiloto

Lo construí **trabajando con [Claude](https://claude.com/claude-code) (Anthropic) como copiloto de programación**, y quiero que quede claro:

- **Yo (Sayessol)** decidí qué construir y en qué orden, probé la app a mano, planteé las dudas y los problemas que fui encontrando (por ejemplo, si movía carpetas en vez de fotos) y fui aprobando cada paso.
- **Claude** escribió el código, las pruebas y la documentación, propuso alternativas y explicó sus decisiones, siempre dentro de las reglas del proyecto (como la de no borrar nunca los originales). La [guía del código](docs/guia-del-codigo.pdf) está escrita precisamente para aprender de ese código.
- **Por eso no presento este código como escrito solo por mí.** Lo que sí es mío es el objetivo, lo que se decidió construir y el aprendizaje que busco con ello.
- **Las pruebas son la red de seguridad**: ningún cambio se da por bueno sin toda la batería en verde, y el CI la vuelve a ejecutar en cada push y pull request.
- Los commits llevan la línea `Co-Authored-By: Claude` para que la autoría compartida sea visible en el historial.

## Limitaciones conocidas

- **No lee móviles conectados por USB** (modo MTP/PTP): Windows no les da una ruta de carpeta real. Copia antes las fotos al PC o usa un lector de tarjetas.
- Las fotos parecidas no detectan recortes ni rotaciones.
- Solo Windows.

## Sugerencias

No hay una hoja de ruta cerrada: iré mejorando la aplicación sobre la marcha, según vea con la práctica qué funciones le faltan. **Si tienes ideas para funcionalidades futuras, me encantará conocerlas**: abre una *issue* con la plantilla «Suggestion».

## Licencia

[MIT](LICENSE) © 2026 Sayessol
