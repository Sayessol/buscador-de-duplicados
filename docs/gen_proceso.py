"""Genera 'proceso-de-creacion.pdf'."""

from pathlib import Path

from _pdf_comun import (
    construir, h1, h2, p, nota, lista, tabla,
)

SALIDA = Path(__file__).resolve().parent / "proceso-de-creacion.pdf"

C = []

# ======================================================================
C += [h1("1. Punto de partida")]
C += [p(
    "Siempre he guardado copias de seguridad de mis dispositivos antiguos, "
    "como teléfonos u ordenadores, en discos duros externos de varios teras. "
    "Con el tiempo, muchos archivos acaban duplicados en subcarpetas, y eso "
    "termina comiéndose el espacio del disco. Revisarlo a mano es tedioso, y "
    "se vuelve incluso un lío cuando ya no sabes qué carpetas has revisado y "
    "cuáles no.")]
C += [p(
    "Mi idea de partida era poder lanzar órdenes rápidas y sencillas que "
    "compararan imágenes y otros tipos de archivos y me dijeran enseguida si "
    "había duplicados o no. Descubrí que la forma más rápida de conseguirlo "
    "era usar <b>Python</b>.")]
C += [p(
    "Empecé con un script sencillo de unas 150 líneas, "
    "<b>buscar_duplicados.py</b>: le introducía la ruta de una carpeta, la "
    "recorría de forma recursiva, calculaba un hash SHA-256 del contenido de "
    "cada archivo y me decía si había archivos duplicados y cuántos había "
    "analizado, además de generar un CSV con los grupos idénticos. Era seguro "
    "(solo leía), pero tras usarlo varias veces me di cuenta de que era poco "
    "práctico: tener que escribir la ruta cada vez era lento y no me ayudaba "
    "a decidir qué hacer con los duplicados.")]
C += [p(
    "Así que decidí crearle una <b>interfaz</b> para que fuese más fácil de "
    "usar. Al construirla vi que podía añadirle funciones que adaptaran mejor "
    "la búsqueda a lo que yo quería, y de ahí pasó de ser un script a un "
    "<b>programa de escritorio completo</b> para Windows, con varias funciones "
    "y opciones de filtrado, empaquetado como un único ejecutable que no exija "
    "instalar Python y manteniendo la filosofía de seguridad del script "
    "original.")]
C += [p(
    "<b>Objetivo del proyecto.</b> Además de resolver esa necesidad, este "
    "proyecto es un <b>ejercicio de aprendizaje</b>: lo hice para profundizar "
    "en Python partiendo de un <b>nivel básico</b>, enfrentándome a un "
    "problema real de principio a fin (algoritmos, hilos, interfaz gráfica, "
    "pruebas, integración continua y empaquetado). Lo hice con Claude como "
    "copiloto de programación, y este documento y la guía del código existen "
    "para poder aprender de lo construido.")]

C += [h2("1.1. Los principios que me marqué para toda la app")]
C += [lista([
    "<b>Nunca se borra ni se modifica un archivo original.</b> La app solo "
    "lee y, cuando el usuario lo confirma, <i>mueve</i> archivos a una "
    "carpeta aparte.",
    "<b>Todo es local.</b> Sin conexión a internet, sin servidor, sin base "
    "de datos. Lo que se guarda (configuración e historial) va a la carpeta "
    "del usuario en %APPDATA%.",
    "<b>Reversible.</b> Cada operación que mueve o copia archivos deja un "
    "registro CSV y una entrada en el historial, y se puede deshacer.",
])]

# ======================================================================
C += [h1("2. Stack tecnológico y decisiones")]
C += [tabla([
    ["Elemento", "Elección", "Motivo"],
    ["Lenguaje", "Python 3.12",
     "Reutiliza la lógica probada del script; multiplataforma; rápido de iterar."],
    ["Interfaz", "CustomTkinter 5.2",
     "Aspecto moderno sobre Tkinter, 100% local, liviano, fácil de empaquetar."],
    ["Hash de contenido", "BLAKE2b (librería estándar)",
     "Más rápido que SHA-256 y de sobra fiable para detectar archivos idénticos."],
    ["Fotos parecidas", "dHash + firma de color (con Pillow)",
     "Sin dependencias pesadas (nada de OpenCV ni redes neuronales)."],
    ["Empaquetado", "PyInstaller 6",
     "Genera un único .exe sin consola que corre sin Python instalado."],
], anchos_cm=[3.0, 4.6, 8.0])]

C += [h2("2.1. Arquitectura: núcleo separado de la interfaz")]
C += [p(
    "Desde el principio decidí separar la <b>lógica</b> (paquete "
    "<font face='Courier'>core/</font>) de la <b>interfaz</b> (paquete "
    "<font face='Courier'>ui/</font>). El núcleo no importa nada de la "
    "interfaz y se puede probar entero por consola, sin abrir ninguna "
    "ventana. Eso me permitió detectar los errores de lógica pronto, sin "
    "mezclarlos con errores de la interfaz.")]
C += [tabla([
    ["Módulo de core/", "Responsabilidad"],
    ["hashing.py", "hash parcial (primeros 64 KB) y completo; formatear tamaños."],
    ["scanner.py", "escaneo en 3 pasadas: tamaño → hash parcial → hash completo."],
    ["filtros.py", "qué archivos incluir/excluir (por tipo, carpeta, nombre, tamaño)."],
    ["seleccion.py", "qué copia se conserva y cuáles se mueven en cada grupo."],
    ["quarantine.py", "mover los descartados a cuarentena, con CSV de registro."],
    ["perceptual.py", "detección de fotos parecidas (dHash + color, BK-tree)."],
    ["mover.py / reunir.py", "mover o copiar lotes de archivos; «Reunir imágenes»."],
    ["historial.py", "registro persistente de operaciones + deshacer."],
    ["config.py", "configuración mínima persistente (recuerda el modo)."],
], anchos_cm=[3.8, 11.8])]

# ======================================================================
C += [h1("3. Fases de desarrollo")]
C += [p(
    "Desarrollé el proyecto siguiendo un plan por fases. Cada fase se "
    "probaba de forma aislada antes de pasar a la siguiente.")]

C += [h2("Fase 1 — Núcleo sin interfaz")]
C += [lista([
    "Pasé la lógica de escaneo a <font face='Courier'>core/</font>, sin interfaz.",
    "Cambié el hash a <b>BLAKE2b</b> con estrategia en dos niveles: primero "
    "un hash de los primeros 64 KB (rápido, descarta casi todo), y solo si "
    "coincide se calcula el hash del archivo completo.",
    "Organicé el escaneo en tres pasadas: (1) agrupar por tamaño en bytes — un "
    "tamaño único no puede tener duplicados; (2) hash parcial; (3) hash "
    "completo. Solo la última pasada lee archivos enteros.",
])]
C += [nota(
    "Para asegurarme de que el núcleo nuevo se comporta igual que el script "
    "original, añadí la prueba <font face='Courier'>comparar_con_original.py</font>, "
    "que construye un árbol de carpetas con trampas (mismo tamaño y distinto "
    "contenido, archivos que solo difieren al final, archivos vacíos...) y "
    "compara los grupos detectados por ambos. Resultado: idénticos.")]

C += [h2("Fase 2 — Ventana principal y escaneo")]
C += [lista([
    "Añadí el selector de carpeta, una barra de progreso en dos etapas y una "
    "tabla de resultados.",
    "El escaneo corre en un <b>hilo aparte</b> para que la ventana no se "
    "congele; la comunicación entre hilos va por una cola que la interfaz "
    "revisa periódicamente.",
    "La tabla muestra cada grupo de duplicados como un nodo desplegable con "
    "sus archivos dentro.",
])]

C += [h2("Fase 2b — Filtro por tipo de archivo")]
C += [p(
    "Quería poder descartar los archivos que no me interesan (temporales, "
    "extensiones inútiles...), así que añadí al panel «Opciones de escaneo» "
    "la posibilidad de <b>buscar solo ciertos tipos</b> (casillas de categoría: Imágenes, "
    "Audio, Vídeo, Documentos, Comprimidos, que rellenan una lista de "
    "extensiones) y además <b>ignorar</b> basura (temporales, "
    "<font face='Courier'>node_modules</font>, "
    "<font face='Courier'>Thumbs.db</font>, archivos de 0 bytes...). "
    "Lo que no pasa el filtro ni se lee ni se hashea, así que también "
    "acelera el escaneo.")]

C += [h2("Fase 3 — Decidir qué conservar")]
C += [lista([
    "Cada grupo empieza con todas sus copias en «conservar» (no se "
    "movería nada).",
    "<b>Regla automática por carpeta preferida</b>: se indica una carpeta y, "
    "en cada grupo, si hay una copia dentro de ella se conserva esa y se "
    "marcan las demás para mover.",
    "<b>Validación</b>: el botón de cuarentena permanece bloqueado hasta que "
    "cada grupo tiene exactamente una copia marcada como «conservar».",
])]

C += [h2("Fase 4 — Mover a cuarentena")]
C += [lista([
    "Se elige una carpeta de cuarentena (debe estar fuera de la carpeta "
    "escaneada; la app lo comprueba).",
    "Los archivos marcados se <b>mueven</b> preservando su estructura de "
    "subcarpetas, para poder localizarlos y devolverlos si hace falta.",
    "Si en el destino ya hay un archivo con ese nombre, el nuevo se guarda "
    "como <font face='Courier'>nombre (1).ext</font> — nunca se pisa nada.",
    "Al terminar se escribe un CSV con cada movimiento.",
])]

C += [h2("Fase 5 — Empaquetado")]
C += [lista([
    "PyInstaller genera <font face='Courier'>dist/duplicados.exe</font>: un "
    "único archivo, sin consola, que corre en Windows sin Python.",
    "El icono de la app es una lupa <b>dibujada por código</b> (sin archivos "
    "de imagen) y convertida a <font face='Courier'>icono.ico</font> "
    "multi-tamaño con la librería estándar.",
])]

C += [h2("Ampliación — Rediseño visual")]
C += [p(
    "Quise que la app resultara más atractiva, así que rehice la interfaz: "
    "cabecera con título, secciones numeradas con "
    "iconos (glifos Unicode, sin imágenes ni coste de tamaño), tarjetas, un "
    "panel de estadísticas con el resultado del escaneo, y un «estado "
    "vacío» ilustrado en lugar de una tabla en blanco. Toda la paleta de "
    "colores se ajustó para cumplir el contraste mínimo de accesibilidad.")]

C += [h2("Ampliación — Fotos parecidas")]
C += [p(
    "Me preguntaba si se podrían agrupar las fotos «parientes»: la misma foto "
    "con menos calidad, con un filtro... Añadí una segunda pestaña que detecta "
    "la <b>misma foto guardada varias veces</b>: "
    "recomprimida, en menor resolución o con un filtro de color. Por cada "
    "imagen calcula un <b>dHash de 64 bits</b> (mide la estructura, muy "
    "estable frente a recompresión y filtros) y una <b>firma de color</b>. "
    "Un BK-tree busca vecinos por distancia de Hamming sin comparar todas "
    "contra todas, y un Union-Find une las cadenas de parecidos. "
    "Elegí que <b>no</b> detecte recortes ni rotaciones, porque haría falta un "
    "motor de visión mucho más pesado.")]

C += [h2("Ampliación — Previsualización y visor")]
C += [p("Para decidir con seguridad quise ver lo que iba a mover:")]
C += [lista([
    "Miniatura en cada fila de la tabla (imagen real o un recuadro con la "
    "extensión, coloreado por categoría).",
    "Panel de vista grande a la derecha, con nombre, ruta, tamaño, fecha y "
    "resolución.",
    "Al pulsar la previsualización se abre un <b>visor a pantalla casi "
    "completa</b> con zoom (rueda del ratón) y desplazamiento arrastrando.",
])]

C += [h2("Ampliación — Modo Sencilla / Avanzada")]
C += [p(
    "Como ya había muchas opciones, decidí que la app arrancara en una versión "
    "simplificada, con un interruptor en la cabecera. Arranca en <b>Sencilla</b> "
    "(solo elegir carpeta, escanear y mover; la app preselecciona sola la "
    "copia principal de cada grupo) y recuerda la elección. En "
    "<b>Avanzada</b> aparece todo: opciones de escaneo, carpeta preferida, "
    "exportar CSV, deslizador de sensibilidad, historial...")]

C += [h2("Ampliación — Reunir imágenes e historial")]
C += [lista([
    "Añadí una tercera pestaña que junta en una carpeta común las fotos "
    "repartidas por una carpeta. Estrategias «por archivos» (preservando "
    "subcarpetas) o «carpeta entera»; mover o copiar.",
    "Diálogo para decidir qué hacer con los archivos que no son imágenes: "
    "dejarlos, moverlos, o agruparlos por tipo en una carpeta con el nombre "
    "que elija el usuario.",
    "<b>Historial</b> (botón en la cabecera, modo Avanzada): lista todas las "
    "operaciones de mover/copiar y permite <b>deshacer</b> cada una — al "
    "mover, devuelve los archivos; al copiar, borra las copias con "
    "confirmación.",
])]

# ======================================================================
C += [h1("4. Pruebas")]
C += [p(
    "Pruebo el proyecto con <font face='Courier'>pytest</font>: 128 pruebas "
    "(15 suites y 113 unitarias). No hay ningún test que «finja» el sistema de "
    "archivos: cada uno construye "
    "archivos de verdad en una carpeta temporal, ejecuta la lógica real y "
    "comprueba el resultado en disco.")]
C += [tabla([
    ["Suite", "Qué comprueba"],
    ["comparar_con_original", "El núcleo detecta los mismos duplicados que el script original."],
    ["probar_filtros", "Lista blanca por categoría + lista negra + desglose por extensión."],
    ["probar_seleccion", "Regla de carpeta, ajuste manual, preselección de la copia principal."],
    ["probar_cuarentena", "Mover de verdad, log CSV, colisiones, casos inválidos."],
    ["probar_cuarentena_carpetas", "Se mueven los ARCHIVOS, nunca las carpetas."],
    ["probar_perceptual", "Agrupación de fotos parecidas; corrupta no rompe nada."],
    ["probar_reunir", "Estrategias por archivos / carpeta entera; reglas por tipo."],
    ["probar_historial", "Registrar, listar y deshacer (mover y copiar)."],
    ["humo_ventana / humo_parecidas / humo_sencilla",
     "Montaje de la ventana y flujos de punta a punta."],
    ["humo_cuarentena_ui / humo_reunir_ui", "Pulsando los botones reales, con diálogos simulados."],
    ["humo_registro / humo_dialogos",
     "Errores inesperados en el registro; visor, historial, diálogos, CSV y miniaturas."],
    ["test_contraste (71)", "Contraste WCAG AA de cada pareja de texto y fondo, en los dos temas."],
    ["test_scanner_pasadas / test_registro / test_unidades",
     "Cada pasada del escáner, el registro de errores, la configuración, el CSV y la versión."],
], anchos_cm=[5.2, 10.4])]

# ======================================================================
C += [h1("5. Problemas que encontré y cómo se resolvieron")]
C += [tabla([
    ["Problema", "Solución"],
    ["CustomTkinter reaplicaba su propio icono 200 ms después de abrir la ventana.",
     "Fijar el icono con iconbitmap(.ico) en vez de iconphoto, para que la "
     "comprobación interna de la librería lo detecte y no lo pise."],
    ["Pasar varias imágenes a la vez a iconphoto() desdibujaba el icono.",
     "Usar una sola imagen bien elegida, o el .ico multi-tamaño en el .exe."],
    ["La resolución de las fotos salía mal en el visor y la lista.",
     "Leer im.size ANTES de im.draft(): draft reduce la imagen y cambia el "
     "tamaño reportado."],
    ["El «estado vacío» no tapaba la galería (CTkScrollableFrame).",
     "Alternar con grid()/grid_remove() en vez de tkraise()."],
    ["Pillow inflaba el .exe de 13 a 20 MB.",
     "Asumí el coste al añadir fotos parecidas y miniaturas; Pillow es "
     "necesario y va en requirements.txt (no así reportlab, que solo genera "
     "esta documentación)."],
    ["Una duda mía al probarlo: «¿mueve las carpetas en vez de las fotos?».",
     "Dos tests nuevos confirmaron que siempre se mueven archivos "
     "individuales; lo que se ve es la estructura recreada en el destino y "
     "las subcarpetas de origen que quedan vacías."],
    ["Tras mover a cuarentena, la vista previa conservaba la imagen anterior "
     "bajo el texto «selecciona un archivo».",
     "CTkLabel.configure(image=None) no la quita: hay que limpiar el Label "
     "interno de tkinter."],
    ["Con muchas fotos parecidas, la galería se cortaba y la barra de desplazamiento desaparecía.",
     "Windows no dibuja ventanas de más de 32.767 px de alto. Ahora los grupos "
     "se reparten en páginas (Anterior / Siguiente) y una prueba comprueba "
     "que ninguna se acerca a ese límite."],
    ["Mis pruebas de ventana escribían en el historial real de la app.",
     "Ahora usan un APPDATA temporal, y una comprobación común avisa si "
     "alguna vuelve a tocar los datos reales."],
    ["Dos pollers leyendo la misma cola se robaban mensajes.",
     "Colas separadas para las miniaturas y para la operación en curso."],
], anchos_cm=[7.2, 8.4])]

# ======================================================================
C += [h1("6. Estado final")]
C += [tabla([
    ["Métrica", "Valor"],
    ["Código Python (sin build ni dist)", "~8.800 líneas"],
    ["  · núcleo (core/)", "~2.100 líneas, 13 módulos"],
    ["  · interfaz (ui/)", "~3.500 líneas, 13 módulos"],
    ["  · pruebas", "~3.000 líneas: 15 suites + 113 unitarias"],
    ["Dependencias de la app", "customtkinter, pillow"],
    ["Ejecutable final",
     "duplicados.exe (~20 MB, un solo archivo) o ZIP con carpeta (~20 MB), sin consola"],
    ["Estado de las pruebas", "128/128 en verde; cobertura: núcleo 93 %, interfaz 79 %"],
], anchos_cm=[7.5, 8.1])]
C += [p(
    "La aplicación cubre tres necesidades relacionadas — encontrar "
    "duplicados exactos, encontrar fotos parecidas y reunir imágenes "
    "dispersas — y en las tres mantuve la misma regla: nunca borra tus "
    "originales y todo se puede deshacer.")]


# ======================================================================
C += [h1("7. Calidad y publicación")]
C += [p(
    "Antes de publicar el proyecto en GitHub dediqué una tanda de trabajo a "
    "la calidad, siempre con las pruebas como red de seguridad:")]
C += [lista([
    "<b>Estructura.</b> La ventana principal tenía más de 2.100 líneas en una "
    "sola clase. Ahora es una carcasa de ~200 líneas y cada pestaña es un "
    "componente con su propio estado, en su módulo "
    "(<font face='Courier'>pestana_*.py</font>). Lo hice pestaña a pestaña, "
    "comprobando cada vez que las 16 capturas de la interfaz (tema claro y "
    "oscuro) seguían siendo idénticas píxel a píxel. También repartí "
    "<font face='Courier'>escanear()</font> en una función por pasada.",
    "<b>Herramientas.</b> pytest (con cobertura del núcleo y de la interfaz), "
    "ruff para el estilo y mypy para los tipos del núcleo, que está "
    "completamente anotado. Todo se ejecuta en cada <i>push</i> con GitHub "
    "Actions, y Dependabot avisa de actualizaciones.",
    "<b>Contraste.</b> Las pruebas miden con la fórmula de WCAG cada pareja de "
    "texto y fondo en el tema claro y en el oscuro (nivel AA, 4,5:1). Con "
    "ellas sustituí los azules y grises por defecto de CustomTkinter, que con "
    "texto blanco no llegaban, por colores propios (5,7:1).",
    "<b>Registro de errores.</b> Sin consola, los errores del .exe "
    "desaparecían. Ahora se anotan en un archivo y la app avisa de dónde "
    "está.",
    "<b>Rendimiento.</b> <font face='Courier'>pruebas/benchmark.py</font> "
    "compara el escaneo en 3 pasadas con hashear todo: lee un 66 % menos de "
    "bytes y encuentra exactamente los mismos grupos.",
    "<b>Dos formatos de descarga.</b> Con Avast instalado, el .exe de un solo "
    "archivo se me quedó congelado en el primer arranque (se descomprime en una "
    "carpeta temporal cada vez). Por eso cada versión incluye también un ZIP "
    "con carpeta, que no extrae nada al arrancar. Al probarlo vi que, sin "
    "consola, una simple advertencia de CustomTkinter (ruta de más de 260 "
    "caracteres) hacía caer la app; ahora se descartan las salidas que no "
    "existen.",
    "<b>Privacidad en capturas.</b> Las capturas y el GIF se hacen sobre una "
    "carpeta de ejemplo con ruta neutra, para que no aparezca el nombre de "
    "usuario de Windows.",
])]
C += [p(
    "<b>Cómo lo hice.</b> Lo desarrollé con Claude (Anthropic) como copiloto "
    "de programación: yo decidía qué construir y revisaba el resultado, y "
    "Claude escribía y probaba el código en sesiones de trabajo conjunto. Los "
    "commits llevan la línea «Co-Authored-By» para dejarlo claro.")]


# ======================================================================
C += [h1("8. Qué he aprendido")]
C += [lista([
    "<b>Lo que más me costó:</b> cómo dividir el código para que no quedaran "
    "archivos demasiado largos. Se nota en la estructura actual: la lógica "
    "(<font face='Courier'>core/</font>) separada de la interfaz "
    "(<font face='Courier'>ui/</font>) y un componente por pestaña.",
    "<b>Lo que más he aprendido:</b> la versatilidad de Python para ejecutar "
    "scripts directamente sobre los archivos: con muy pocas líneas se puede "
    "recorrer un disco, comparar contenidos y mover archivos.",
])]
C += [p(
    "No hay una hoja de ruta cerrada: iré mejorando la aplicación sobre la "
    "marcha, según vea con la práctica qué funciones le faltan. Si alguien "
    "tiene ideas para funcionalidades futuras, me encantará conocerlas.")]


construir(
    SALIDA,
    titulo="Buscador de duplicados",
    subtitulo="Documentación del proceso de creación y sus fases",
    titulo_corto="Proceso de creación",
    resumen_portada=(
        "Cómo pasé de un script de 150 líneas a una aplicación de "
        "escritorio para Windows con tres funciones (duplicados exactos, fotos parecidas y "
        "reunir imágenes), interfaz en dos niveles y un historial para "
        "deshacer cualquier operación."),
    cuerpo_flowables=C)
