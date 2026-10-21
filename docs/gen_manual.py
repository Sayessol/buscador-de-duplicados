"""Genera 'manual-de-usuario.pdf'."""

from pathlib import Path

from reportlab.platypus import PageBreak

from _pdf_comun import (
    construir, h1, h2, h3, p, nota, lista, imagen, tabla,
)

SALIDA = Path(__file__).resolve().parent / "manual-de-usuario.pdf"

C = []

# ======================================================================
C += [h1("1. Qué hace esta aplicación")]
C += [p(
    "En este manual te explico cómo usar <b>Buscador de duplicados</b>, la "
    "aplicación que creé para poner orden entre mis archivos, sobre todo mis "
    "fotos, y que ahora puede ayudarte a ti. Tiene tres funciones, una por "
    "pestaña:")]
C += [tabla([
    ["Pestaña", "Para qué sirve"],
    ["Duplicados exactos",
     "Encuentra archivos idénticos byte a byte (la misma foto o documento "
     "guardado varias veces) y te deja quedarte con una copia."],
    ["Fotos parecidas",
     "Encuentra la misma foto guardada varias veces aunque no sea idéntica: "
     "recomprimida, en menor resolución o con un filtro de color."],
    ["Reunir imágenes",
     "Junta en una sola carpeta todas las fotos que tengas repartidas por "
     "una carpeta y sus subcarpetas."],
], anchos_cm=[3.6, 12.0])]
C += [nota(
    "La regla de oro que me marqué: <b>la aplicación nunca borra ni modifica tus archivos "
    "originales</b>. Solo los lee y, cuando tú lo confirmas, los <i>mueve</i> "
    "a otra carpeta. Además, cualquier operación se puede deshacer desde el "
    "«Historial».")]

# ======================================================================
C += [h1("2. Instalación y primer arranque")]
C += [lista([
    "No hay que instalar nada. Descarga <font face='Courier'>Buscador-de-duplicados.exe</font> "
    "(un solo archivo: cópialo donde quieras y haz doble clic) o, si tu antivirus "
    "lo bloquea o tarda, <font face='Courier'>Buscador-de-duplicados-portable.zip</font>: "
    "descomprímelo en una carpeta con ruta corta (por ejemplo "
    r"<font face='Courier'>C:\Apps</font>) y abre el .exe de dentro.",
    "No necesita conexión a internet ni permisos de administrador.",
    "La primera vez arranca en <b>modo Sencilla</b>. Tu elección de modo se "
    "recuerda para la próxima vez.",
])]
C += [p(
    "Windows puede mostrar un aviso de «editor desconocido» la primera vez "
    "(porque el ejecutable no está firmado). Es normal en programas "
    "pequeños; pulsa «Más información» y «Ejecutar de todas formas».")]

# ======================================================================
C += [h1("3. La pantalla principal")]
C += imagen("01_sencilla.png", pie=(
    "Modo Sencilla, pestaña «Duplicados exactos», después de un escaneo."))
C += [p(
    "Arriba a la derecha hay dos ajustes:")]
C += [lista([
    "<b>Tema</b>: <i>Automático</i> (sigue al tema de Windows), <i>Claro</i> "
    "u <i>Oscuro</i>. Se aplica al momento y se recuerda para la próxima vez.",
    "<b>Vista — Sencilla / Avanzada</b>:",
])]
C += [lista([
    "<b>Sencilla</b>: lo mínimo — elegir carpeta, escanear y mover. La "
    "aplicación decide sola qué copia conservar en cada grupo.",
    "<b>Avanzada</b>: aparece todo — filtros de escaneo, carpeta preferida, "
    "exportar a CSV, el deslizador de sensibilidad, y el botón «Historial».",
])]
C += [p(
    "Justo debajo están las tres pestañas. Cambiar de pestaña no pierde lo "
    "que tengas en las otras.")]
C += [nota(
    "Los botones deshabilitados se ven en gris apagado (no en rojo ni "
    "verde): quiere decir que esa acción todavía no está disponible, no "
    "que haya un error.")]

# ======================================================================
C += [PageBreak(), h1("4. Pestaña «Duplicados exactos»")]

C += [h2("4.1. Uso básico (modo Sencilla)")]
C += [lista([
    "<b>1.</b> Pulsa «Elegir» y selecciona la carpeta que quieres revisar "
    "(por ejemplo tu carpeta de fotos o un disco entero).",
    "<b>2.</b> Pulsa «Escanear». La barra de progreso muestra dos etapas: "
    "primero revisa tamaños, luego calcula huellas.",
    "<b>3.</b> Al terminar ves los grupos de duplicados. La aplicación ya ha "
    "marcado en cada grupo la <b>copia principal</b> (la de nombre menos "
    "«de copia», en la carpeta menos anidada y más antigua) para conservar, "
    "y el resto para mover.",
    "<b>4.</b> Revisa. Si quieres conservar otra copia en un grupo, haz "
    "<b>doble clic</b> sobre su fila.",
    "<b>5.</b> Pulsa «Mover a cuarentena», elige una carpeta (debe estar "
    "<b>fuera</b> de la que escaneaste) y confirma.",
])]
C += [p(
    "El panel de estadísticas muestra cuántos grupos hay, cuántos archivos "
    "duplicados, cuántos se moverían y cuánto espacio recuperarías.")]

C += [h2("4.2. Vista previa y ver en grande")]
C += [p(
    "Al seleccionar un archivo de la lista, a la derecha aparece su vista "
    "previa (la imagen, o un recuadro con la extensión si no es una imagen) "
    "con su nombre, ruta, tamaño, fecha y resolución. <b>Pulsa la vista "
    "previa</b> para abrir la imagen a pantalla casi completa, con zoom "
    "(rueda del ratón o botones) y desplazamiento arrastrando.")]
C += imagen("08_visor.png", ancho_cm=13.5, pie=(
    "El visor de imagen: rueda para el zoom, arrastrar para moverse, "
    "«Ajustar» para encajarla en la ventana."))

C += [PageBreak(), h2("4.3. Opciones de escaneo (modo Avanzada)")]
C += imagen("03_opciones.png", pie=(
    "El panel «Opciones de escaneo» desplegado, con «Imágenes» marcado."))
C += [h3("Buscar solo estos tipos de archivo")]
C += [p(
    "Marca una o varias categorías (Imágenes, Audio, Vídeo, Documentos, "
    "Comprimidos) y el campo de extensiones se rellena solo. También puedes "
    "escribir extensiones a mano. Si lo dejas vacío se buscan duplicados de "
    "cualquier tipo.")]
C += [h3("Ignorar además")]
C += [p(
    "Descarta basura antes de escanear: extensiones "
    "(<font face='Courier'>tmp</font>, <font face='Courier'>log</font>...), "
    "carpetas (<font face='Courier'>node_modules</font>, "
    "<font face='Courier'>$RECYCLE.BIN</font>...), nombres "
    "(<font face='Courier'>Thumbs.db</font>...) y archivos de 0 bytes. Viene "
    "con valores razonables. Lo que se ignora ni se lee, así que el escaneo "
    "va más rápido.")]

C += [h2("4.4. Elegir qué conservar (modo Avanzada)")]
C += imagen("02_avanzada.png", pie=(
    "Modo Avanzada: reaparecen «Carpeta preferida», «Regla por carpeta», "
    "«Elegir la principal», «Ver tipos de archivo» y «Exportar CSV»."))
C += [lista([
    "<b>Carpeta preferida + «Regla por carpeta»</b>: indica una carpeta "
    "(por ejemplo <font face='Courier'>D:\\Fotos\\Organizado</font>) y pulsa "
    "el botón. En cada grupo, si hay una copia dentro de esa carpeta se "
    "conserva esa. Los grupos sin ninguna copia ahí quedan resaltados para "
    "que decidas a mano.",
    "<b>«Elegir la principal»</b>: aplica la misma preselección automática "
    "del modo Sencilla.",
    "<b>Interacción con la tabla</b>: un clic selecciona (y muestra la vista "
    "previa); un clic en la columna «Decisión» alterna conservar/mover de "
    "ese archivo; un doble clic deja esa copia como la única a conservar.",
    "<b>«Ver tipos de archivo»</b>: muestra los duplicados agrupados por "
    "extensión con su peso, para decidir qué añadir al filtro.",
    "<b>«Exportar CSV»</b>: guarda el informe completo en un archivo.",
])]

# ======================================================================
C += [PageBreak(), h1("5. Pestaña «Fotos parecidas»")]
C += imagen("04_parecidas.png", pie=(
    "Cada grupo muestra las fotos parecidas con su miniatura, resolución, "
    "peso y porcentaje de parecido."))
C += [lista([
    "<b>1.</b> Elige la carpeta y pulsa «Analizar».",
    "<b>2.</b> El deslizador de <b>Sensibilidad</b> (modo Avanzada) controla "
    "cuánto se parecen dos fotos para considerarlas del mismo grupo: "
    "«estricta» junta menos, «tolerante» junta más.",
    "<b>3.</b> En cada grupo, la primera foto es la <b>mejor calidad</b> "
    "(más resolución) y aparece marcada para conservar. Si prefieres otra, "
    "pulsa «Conservar esta» debajo de ella.",
    "<b>4.</b> Pulsa una miniatura para ver la foto en grande y comparar.",
    "<b>5.</b> «Mover a cuarentena» mueve las fotos no marcadas.",
])]
C += [h2("5.1. Qué encuentra y qué no")]
C += [tabla([
    ["Sí encuentra", "No encuentra"],
    ["La misma foto recomprimida o en menor calidad", "Fotos recortadas"],
    ["La misma foto redimensionada (más pequeña)", "Fotos rotadas o volteadas"],
    ["La misma foto con un filtro de color o brillo", "Un trozo de un collage"],
    ["La misma foto con una marca de agua en una esquina", ""],
], anchos_cm=[8.0, 7.6])]

# ======================================================================
C += [PageBreak(), h1("6. Pestaña «Reunir imágenes»")]
C += imagen("05_reunir.png", pie=(
    "Lista de imágenes encontradas, con casilla para excluir alguna."))
C += [lista([
    "<b>1.</b> Elige la carpeta a revisar. El selector "
    "<b>«Todas las subcarpetas» / «Solo el primer nivel»</b> decide si busca "
    "en profundidad o solo lo que está suelto en la carpeta.",
    "<b>2.</b> Pulsa «Buscar imágenes». Aparecen con su miniatura; desmarca "
    "las que no quieras llevarte.",
    "<b>3.</b> Elige la <b>carpeta común de destino</b>.",
    "<b>4.</b> (modo Avanzada) Elige <b>Mover</b> (las quita del origen) o "
    "<b>Copiar</b> (deja los originales), y la estrategia:",
])]
C += [tabla([
    ["Estrategia", "Qué hace"],
    ["Por archivos",
     "Cada imagen va a destino/<i>misma subcarpeta</i>. Por ejemplo "
     "«vacaciones/playa.jpg» acaba en «destino/vacaciones/playa.jpg»."],
    ["Carpeta entera",
     "Mueve o copia la carpeta que estás revisando completa (con todo lo "
     "que hay dentro) a «destino/NombreDeLaCarpeta/»."],
], anchos_cm=[3.4, 12.2])]

C += [h2("6.1. Archivos que no son imágenes")]
C += [p(
    "Si en esas carpetas hay también documentos, música, etc., y usas la "
    "estrategia «Por archivos», aparece este diálogo:")]
C += imagen("06_tipos.png", ancho_cm=12.5, pie=(
    "Para cada tipo de archivo eliges qué hacer."))
C += [lista([
    "<b>Dejar</b>: no se mueve, se queda donde está.",
    "<b>Mover</b>: va al destino con su misma subcarpeta, igual que las "
    "imágenes.",
    "<b>Agrupar</b>: todos los archivos de ese tipo van a una carpeta con "
    "el nombre que tú escribas (por ejemplo «Documentos»), manteniendo las "
    "subcarpetas dentro.",
])]

# ======================================================================
C += [PageBreak(), h1("7. Historial y deshacer")]
C += [p(
    "En <b>modo Avanzada</b>, el botón <b>«Historial»</b> de la cabecera "
    "abre esta ventana desde cualquier pestaña:")]
C += imagen("07_historial.png", ancho_cm=13.5, pie=(
    "Cada operación de mover o copiar queda registrada, con su botón "
    "«Deshacer»."))
C += [lista([
    "Si la operación fue <b>mover</b>, «Deshacer» devuelve cada archivo a "
    "su ubicación original. Si en esa ruta ya hay algo, lo avisa y no pisa "
    "nada.",
    "Si la operación fue <b>copiar</b>, «Deshacer» borra las copias del "
    "destino (con una confirmación clara). Es el único caso en que la "
    "aplicación borra algo, y solo archivos que ella misma creó.",
])]
C += [p(
    "El historial se guarda en "
    "<font face='Courier'>%APPDATA%\\BuscadorDuplicados\\historial.json</font> "
    "y conserva las últimas operaciones.")]

# ======================================================================
C += [h1("8. La carpeta de cuarentena y los registros")]
C += [lista([
    "La carpeta de cuarentena (o de destino, en «Reunir imágenes») la "
    "eliges tú cada vez. No hay una fija.",
    "Dentro se recrea la estructura de subcarpetas del origen, para que "
    "sepas de dónde salió cada archivo.",
    "Se escribe un CSV "
    "(<font face='Courier'>_log_cuarentena_FECHA.csv</font> o "
    "<font face='Courier'>_log_reunir_FECHA.csv</font>) con origen y destino "
    "de cada archivo, por si prefieres revisar o deshacer a mano.",
    "Nada se borra: revisa esa carpeta con calma y elimina tú lo que ya no "
    "necesites.",
])]

# ======================================================================
C += [h1("9. Consejos y preguntas frecuentes")]
C += [tabla([
    ["Pregunta", "Respuesta"],
    ["¿Puede borrarme fotos sin querer?",
     "No tus originales. Solo mueve archivos, y siempre tras una confirmación. "
     "Todo se puede deshacer desde el Historial. La única vez que borra algo es "
     "al deshacer una copia: elimina las copias que ella misma creó, y antes te "
     "pide confirmación."],
    ["Me ha salido un aviso de «error inesperado». ¿Qué hago?",
     r"La aplicación anota lo ocurrido en un archivo de texto: "
     r"<font face='Courier'>%APPDATA%\BuscadorDuplicados\registro\buscador.log</font> "
     "(pega esa ruta en el Explorador y ábrelo con el Bloc de notas). Puedes "
     "seguir usando la aplicación, y tus archivos no se han tocado. Si el fallo "
     "se repite, cierra y vuelve a abrirla; si quieres informar del problema, "
     "adjunta ese archivo."],
    ["He movido cosas y veo carpetas vacías en el origen.",
     "Es normal: se movieron los archivos de dentro, no las carpetas. La "
     "carpeta vacía se queda; puedes borrarla tú si quieres."],
    ["El escaneo tarda mucho.",
     "Usa el filtro «Buscar solo imágenes» o reduce la carpeta. La primera "
     "pasada (tamaños) es rápida; el tiempo se va en calcular huellas de "
     "archivos grandes."],
    ["¿Qué diferencia hay entre las dos primeras pestañas?",
     "«Duplicados exactos» busca archivos idénticos; «Fotos parecidas» "
     "busca la misma foto aunque se haya reguardado con otra calidad o "
     "filtro."],
    ["¿Se puede usar en un disco externo o de red?",
     "Sí. Ten en cuenta que mover entre discos distintos es más lento "
     "(copia y luego borra el original)."],
], anchos_cm=[5.4, 10.2])]


construir(
    SALIDA,
    titulo="Buscador de duplicados",
    subtitulo="Manual de usuario",
    titulo_corto="Manual de usuario",
    resumen_portada=(
        "Guía para encontrar archivos duplicados, agrupar fotos parecidas y "
        "reunir imágenes dispersas — sin riesgo de perder nada, porque la "
        "aplicación nunca borra tus originales y todo se puede deshacer."),
    cuerpo_flowables=C)
