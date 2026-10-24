"""Contents of 'guia-del-codigo.pdf' (Spanish).

A document for whoever wants to understand HOW the code is built and learn from it.
"""

from reportlab.platypus import PageBreak

from _pdf_common import bullet_list, h1, h2, h3, note, p, pre, table

TITLE = "Buscador de duplicados"
SUBTITLE = "Guía del código — cómo funciona por dentro"
SHORT_TITLE = "Guía del código"
COVER_SUMMARY = (
    "Recorrido por el código para quien quiera entenderlo o aprender a partir de él: la "
    "arquitectura por capas con puertos y adaptadores, los algoritmos (las 3 pasadas del "
    "escaneo, dHash, BK-tree, Union-Find), el patrón de hilos de la interfaz, los "
    "idiomas, el empaquetado y cómo se prueba todo.")


def body():
    C = []

    # ======================================================================
    C += [h1("1. Cómo leer este proyecto")]
    C += [p(
        "En esta guía te explico cómo está hecho el código, para que puedas "
        "entenderlo y aprender de él, igual que yo he ido aprendiendo. Está en el "
        "paquete <font face='Courier'>src/duplicate_finder/</font>, dividido en capas, y "
        "al lado hay una carpeta de pruebas:")]
    C += [table([
        ["Carpeta", "Qué contiene", "Regla"],
        ["domain/", "Reglas y datos: filtros, grupos de duplicados, selección, "
                    "similitud.",
         "No importa nada del resto. Sin entrada ni salida (ni disco, ni ventana)."],
        ["application/", "Los casos de uso (escanear, mover, reunir, historial...) y los "
                         "puertos que necesitan.",
         "Solo importa domain/ e i18n/. El disco, solo a través de puertos."],
        ["infrastructure/", "Los adaptadores: disco, hashes, Pillow, JSON, registro.",
         "Implementa los puertos. Nunca importa la interfaz."],
        ["presentation/", "La ventana y todos sus widgets (CustomTkinter).",
         "Solo pinta y reacciona a clics; delega en los casos de uso."],
        ["i18n/", "Los textos en inglés y español.", "No importa nada."],
        ["tests/", "Pruebas con pytest, de varios niveles.",
         "Crean archivos de verdad o usan dobles en memoria de los puertos."],
    ], widths_cm=[2.8, 6.6, 6.2])]
    C += [p(
        "<b>Por dónde te recomiendo empezar a leer:</b> "
        "<font face='Courier'>application/scan_duplicates.py</font> (el algoritmo "
        "central), luego <font face='Courier'>bootstrap.py</font> (cómo se conecta "
        "todo) y <font face='Courier'>presentation/main_window.py</font> (la carcasa de "
        "la ventana; cada pestaña es un componente en su <font face='Courier'>*_tab.py</font>). "
        "El resto son piezas que se entienden solas con su docstring.")]

    C += [h2("1.1. Mapa de módulos")]
    C += [table([
        ["domain/", ""],
        ["duplicates.py", "DuplicateFile, DuplicateGroup, ScanResult: el resultado de un "
                          "escaneo."],
        ["filters.py", "ScanFilter: qué incluir/excluir. CATEGORY_EXTENSIONS."],
        ["selection.py", "DuplicateSelection: estado conservar/mover por grupo."],
        ["similarity.py", "fotos parecidas: distancia de Hamming, BK-tree, Union-Find."],
        ["transfers.py", "reglas de mover/copiar y qué hacer con lo que no son imágenes."],
        ["formatting.py, operations.py", "tamaños legibles (KB/MB) y tipos de operación."],
    ], widths_cm=[4.4, 11.2])]
    C += [table([
        ["application/", ""],
        ["ports.py", "las interfaces (Protocol): FileSystem, FileHasher, "
                     "FingerprintReader, HistoryStore, SettingsStore."],
        ["scan_duplicates.py", "ScanDuplicates: las 3 pasadas. Devuelve ScanResult."],
        ["find_similar_photos.py", "FindSimilarPhotos: huellas + agrupar."],
        ["quarantine.py", "MoveToQuarantine: validar, mover preservando estructura, CSV, "
                          "historial."],
        ["gather.py, file_transfers.py", "GatherImages y las primitivas mover/copiar "
                                         "por lotes."],
        ["history.py", "OperationHistory: registro de operaciones + deshacer."],
        ["report.py, settings.py, start_selection.py", "exportar CSV, ajustes, "
                                                        "preselección."],
        ["services.py", "Services: todos los casos de uso juntos, para la interfaz."],
    ], widths_cm=[4.4, 11.2])]
    C += [table([
        ["infrastructure/", ""],
        ["local_file_system.py", "LocalFileSystem: os y shutil (con reintentos al borrar)."],
        ["hashing.py", "Blake2Hasher: hash BLAKE2b parcial y completo."],
        ["image_fingerprints.py", "PillowFingerprintReader: dHash y firma de color."],
        ["history_store.py, settings.py", "JsonHistoryStore y JsonSettingsStore (y la "
                                          "migración de los datos de la 1.0)."],
        ["app_logging.py, data_folder.py", "registro de errores y carpeta de datos."],
    ], widths_cm=[4.4, 11.2])]
    C += [table([
        ["presentation/", ""],
        ["main_window.py", "MainWindow: cabecera, tema, idioma y modo. Crea las 3 pestañas."],
        ["exact_duplicates_tab.py", "ExactDuplicatesTab: pestaña Duplicados exactos."],
        ["similar_photos_tab.py", "SimilarPhotosTab: pestaña Fotos parecidas."],
        ["gather_images_tab.py", "GatherImagesTab: pestaña Reunir imágenes."],
        ["scan_options_panel.py, preview_panel.py", "los dos paneles de la primera pestaña."],
        ["background_job.py", "BackgroundJob: hilo + cola + sondeo, para toda tarea larga."],
        ["results_table.py", "ResultsTable: la tabla de duplicados exactos."],
        ["dialogs.py", "las preguntas que comparten las tres pestañas al mover."],
        ["image_viewer.py, history_window.py, ...", "visor con zoom, historial + Deshacer, "
                                                    "diálogos."],
        ["thumbnails.py, widgets.py, styles.py, icons.py",
         "miniaturas, piezas visuales, paleta clara/oscura y glifos."],
    ], widths_cm=[5.2, 10.4])]

    # ======================================================================
    C += [PageBreak(), h1("2. La lógica, explicada")]

    C += [h2("2.1. Detectar duplicados exactos: tres pasadas")]
    C += [p(
        "Comparar el contenido de cada archivo con el de todos los demás sería "
        "lentísimo. En vez de eso filtro de lo barato a lo caro "
        "(<font face='Courier'>application/scan_duplicates.py</font>). Cada pasada es "
        "un método (<font face='Courier'>_size_pass</font>, "
        "<font face='Courier'>_partial_hash_pass</font> y "
        "<font face='Courier'>_full_hash_pass</font>) y "
        "<font face='Courier'>ScanDuplicates.__call__()</font> solo las encadena:")]
    C += [bullet_list([
        "<b>Pasada 1 — tamaños.</b> Recorro la carpeta con el puerto "
        "<font face='Courier'>FileSystem.walk</font> (por debajo, "
        "<font face='Courier'>os.walk</font>) y agrupo los archivos por su "
        "tamaño en bytes. Un tamaño único no puede tener duplicados, así que lo "
        "descarto sin abrir el archivo.",
        "<b>Pasada 2 — hash parcial.</b> Para los que comparten tamaño, "
        "calculo el hash BLAKE2b de solo los primeros 64 KB. Rápido, y descarta "
        "casi todos los que no son iguales.",
        "<b>Pasada 3 — hash completo.</b> Solo para los que además comparten "
        "hash parcial, hasheo el archivo entero. Los que coinciden aquí son "
        "idénticos byte a byte.",
    ])]
    C += [pre(
        "# clave = (tamaño, hash_parcial): dos archivos con el mismo hash\n"
        "# parcial pero distinto tamaño nunca son el mismo archivo.\n"
        "by_partial[(size, hp)].append(path)\n"
        "...\n"
        "finalists = {key: paths for key, paths in by_partial.items() if len(paths) > 1}")]
    C += [note(
        "Optimización sutil: si un archivo pesa menos de 64 KB, su hash parcial "
        "ya cubre todo el contenido, así que me salto la Pasada 3 para él.")]

    C += [h3("Podar carpetas al recorrer")]
    C += [p(
        "El recorrido entrega tres cosas por carpeta: "
        "(ruta, subcarpetas, archivos). Si modificas la lista de subcarpetas "
        "<i>en el sitio</i>, no entra en las que quites — así se "
        "excluyen <font face='Courier'>node_modules</font>, "
        "<font face='Courier'>$RECYCLE.BIN</font>, etc. sin recorrerlas:")]
    C += [pre("subdirs[:] = [d for d in subdirs if not filter.excludes_folder(d)]")]

    C += [h2("2.2. El hash: BLAKE2b y lectura en bloques")]
    C += [p(
        "Uso BLAKE2b (viene con Python, más rápido que SHA-256). Está en "
        "<font face='Courier'>infrastructure/hashing.py</font>, y el caso de uso lo "
        "recibe como puerto (<font face='Courier'>FileHasher</font>). El archivo "
        "completo lo leo de 64 KB en 64 KB para no cargarlo entero en memoria:")]
    C += [pre(
        "h = hashlib.blake2b()\n"
        "with open(file_path, 'rb') as f:\n"
        "    while True:\n"
        "        block = f.read(65536)      # 64 KB\n"
        "        if not block:              # b'' = fin del archivo\n"
        "            break\n"
        "        h.update(block)            # acumula\n"
        "return h.hexdigest()")]

    C += [h2("2.3. El filtro: lista blanca y lista negra")]
    C += [p(
        "<font face='Courier'>ScanFilter</font> (en <font face='Courier'>domain/filters.py</font>) "
        "tiene dos mecanismos. Una <b>lista blanca</b> "
        "(<font face='Courier'>included_extensions</font>): si no está vacía, solo pasan "
        "esas extensiones ('buscar solo imágenes'). Y varias <b>listas negras</b> "
        "(extensiones, carpetas y nombres a ignorar, más un tamaño mínimo). El escaneo "
        "llama a <font face='Courier'>filter.excludes_name(...)</font> y "
        "<font face='Courier'>filter.excludes_folder(...)</font> y no cuenta ni "
        "lee lo que se excluye.")]

    C += [PageBreak(), h2("2.4. La decisión: qué copia se conserva")]
    C += [p(
        "<font face='Courier'>DuplicateSelection</font> (en "
        "<font face='Courier'>domain/selection.py</font>) es un diccionario "
        "<font face='Courier'>(índice_de_grupo, ruta) -&gt; 'keep' | 'move'</font>. "
        "Empieza todo en 'keep' (no se movería nada). La regla que impone "
        "la app: para poder mover, cada grupo debe tener <b>exactamente una</b> "
        "copia en 'keep'.")]
    C += [p(
        "En modo Sencilla, <font face='Courier'>preselect_primary()</font> "
        "elige sola la copia principal de cada grupo con esta puntuación (gana "
        "la tupla más pequeña):")]
    C += [pre(
        "(looks_like_copy,  # 0 si el nombre no tiene 'copia', '(1)'...  1 si sí\n"
        " depth,            # nº de carpetas: cuanto menos anidada, mejor\n"
        " mtime,            # fecha: la más antigua suele ser el original\n"
        " len(path))        # a igualdad de todo, la ruta más corta")]

    C += [h2("2.5. Fotos parecidas: dHash + BK-tree + Union-Find")]
    C += [p(
        "Aquí no puedo comparar contenido (dos fotos parecidas tienen bytes "
        "distintos). Por cada imagen calculo una <b>huella</b> "
        "(<font face='Courier'>infrastructure/image_fingerprints.py</font>, con Pillow); "
        "la comparación de huellas es lógica pura "
        "(<font face='Courier'>domain/similarity.py</font>):")]
    C += [h3("dHash de 64 bits")]
    C += [p(
        "Reduzco la imagen a una miniatura de 9×8 en gris. Por cada fila, "
        "comparo cada píxel con el de su derecha: bit 1 si sube el brillo, 0 si "
        "baja. 8×8 = 64 bits. Mide la <i>forma</i>, no el color, por eso "
        "aguanta la recompresión y los filtros:")]
    C += [pre(
        "bits = 0\n"
        "for row in range(8):\n"
        "    for col in range(8):\n"
        "        goes_up = gray[base+col] < gray[base+col+1]\n"
        "        bits = (bits << 1) | (1 if goes_up else 0)")]
    C += [h3("Distancia de Hamming")]
    C += [p(
        "Cómo de distintas son dos huellas = cuántos bits difieren. "
        "<font face='Courier'>bin(a ^ b).count('1')</font>. 0 = iguales, "
        "64 = opuestas. El deslizador de sensibilidad fija el umbral (~10).")]
    C += [h3("BK-tree")]
    C += [p(
        "Para no comparar todas las fotos contra todas, meto los dHash en "
        "un BK-tree: un árbol donde cada hijo va etiquetado por su distancia "
        "exacta al padre. Al buscar 'los que están a &le; N', la desigualdad "
        "triangular permite <b>podar</b> ramas enteras: solo hay que mirar los "
        "hijos cuya etiqueta esté en <font face='Courier'>[d-N, d+N]</font>.")]
    C += [h3("Union-Find")]
    C += [p(
        "Si A se parece a B y B a C, deben acabar en el mismo grupo aunque A y "
        "C no se parezcan directamente. Union-Find (conjuntos disjuntos) une "
        "esas cadenas: cada elemento apunta a 'otro de su grupo' y siguiendo la "
        "cadena se llega al representante. "
        "<font face='Courier'>groups()</font> agrupa por representante.")]

    C += [PageBreak(), h2("2.6. Mover archivos con seguridad")]
    C += [p(
        "Los casos de uso que mueven o copian "
        "(<font face='Courier'>quarantine.py</font>, "
        "<font face='Courier'>file_transfers.py</font>, "
        "<font face='Courier'>gather.py</font>) comparten las mismas reglas:")]
    C += [bullet_list([
        "<b>Nunca pisar.</b> Antes de mover, si el destino ya existe pruebo "
        "<font face='Courier'>nombre (1).ext</font>, "
        "<font face='Courier'>nombre (2).ext</font>... "
        "(<font face='Courier'>collision_free_path</font>).",
        "<b>Preservar estructura.</b> El destino de cada archivo es "
        "<font face='Courier'>carpeta_destino / relpath(origen, raíz)</font>, "
        "así se recrea la jerarquía de subcarpetas.",
        "<b>Mover, no copiar-y-borrar.</b> <font face='Courier'>shutil.move</font> "
        "(dentro del adaptador <font face='Courier'>LocalFileSystem</font>) "
        "hace un <font face='Courier'>rename</font> atómico si es el mismo disco; "
        "solo copia+borra si es otro disco (y ahí el original desaparece cuando "
        "la copia ya está a salvo).",
        "<b>Destino fuera del origen.</b> <font face='Courier'>validate_destination</font> "
        "y <font face='Courier'>validate_quarantine_folder</font> lo comprueban (si no, "
        "el próximo escaneo reencontraría lo movido).",
        "<b>Todo queda anotado.</b> El propio caso de uso escribe el CSV de registro y "
        "la entrada del historial; la interfaz no tiene que acordarse de hacerlo.",
    ])]

    C += [h2("2.7. Historial y deshacer")]
    C += [p(
        "Cada operación de mover/copiar se apunta (a través del puerto "
        "<font face='Courier'>HistoryStore</font>, en "
        "<font face='Courier'>%APPDATA%\\BuscadorDuplicados\\history.json</font>) "
        "con la lista de pares (origen, destino). "
        "<font face='Courier'>OperationHistory.undo(id)</font>:")]
    C += [bullet_list([
        "si fue <b>mover</b>: devuelve cada archivo al origen — pero si ya hay "
        "algo en el origen, lo avisa y no pisa.",
        "si fue <b>copiar</b>: borra las copias del destino. Es el único punto "
        "de todo el código donde se borra algo, y solo archivos que la app creó. El "
        "borrado reintenta un momento si Windows aún tiene el archivo en uso.",
    ])]

    # ======================================================================
    C += [PageBreak(), h1("3. La arquitectura: puertos, adaptadores y raíz de composición")]
    C += [p(
        "El truco que mantiene ordenado todo lo anterior es que los casos de uso no "
        "saben <i>cómo</i> se lee el disco, se calcula un hash o se guarda un JSON: "
        "piden esas cosas a través de <b>puertos</b>, que son interfaces "
        "(<font face='Courier'>typing.Protocol</font>) en "
        "<font face='Courier'>application/ports.py</font>:")]
    C += [pre(
        "class FileHasher(Protocol):\n"
        "    partial_size: int\n"
        "    def partial_hash(self, path: str) -> str: ...\n"
        "    def full_hash(self, path: str) -> str: ...")]
    C += [p(
        "Un caso de uso recibe sus puertos en el constructor y nunca crea nada por su "
        "cuenta:")]
    C += [pre(
        "class ScanDuplicates:\n"
        "    def __init__(self, fs: FileSystem, hasher: FileHasher) -> None:\n"
        "        self._fs = fs\n"
        "        self._hasher = hasher")]
    C += [p(
        "Los <b>adaptadores</b> de <font face='Courier'>infrastructure/</font> "
        "implementan esos puertos con el mundo real (<font face='Courier'>Blake2Hasher</font>, "
        "<font face='Courier'>LocalFileSystem</font>...). Y "
        "<font face='Courier'>bootstrap.py</font> es la <b>raíz de composición</b>: el único "
        "módulo que conoce todas las capas. Construye los adaptadores, los inyecta y le "
        "da a la ventana un objeto <font face='Courier'>Services</font> con todos los "
        "casos de uso:")]
    C += [pre(
        "def build_services() -> Services:\n"
        "    fs = LocalFileSystem()\n"
        "    history = OperationHistory(JsonHistoryStore(), fs)\n"
        "    return Services(\n"
        "        scan_duplicates=ScanDuplicates(fs, Blake2Hasher()),\n"
        "        find_similar_photos=FindSimilarPhotos(fs, PillowFingerprintReader()),\n"
        "        move_to_quarantine=MoveToQuarantine(fs, history),\n"
        "        ...)")]
    C += [h3("Qué se gana")]
    C += [bullet_list([
        "<b>Se prueba sin disco.</b> Las pruebas de los casos de uso les pasan dobles en "
        "memoria (<font face='Courier'>tests/fakes.py</font>): un sistema de archivos que es un "
        "diccionario, un hasher que usa el contenido. Son rápidas y deterministas.",
        "<b>La interfaz se podría cambiar</b> sin tocar la lógica, porque solo ve "
        "<font face='Courier'>Services</font>.",
        "<b>Cada cosa está en su sitio.</b> Si necesitas saber cómo se mueve un archivo, "
        "miras un adaptador; si necesitas saber cuándo, miras un caso de uso.",
    ])]
    C += [note(
        "No todo tiene puerto: solo lo que toca el mundo exterior (disco, hashes, "
        "imágenes, historial, ajustes). Los cálculos puros (filtros, similitud, selección) "
        "son funciones normales en <font face='Courier'>domain/</font>; una interfaz "
        "ahí no aportaría nada.")]
    C += [h3("Las reglas, comprobadas por una prueba")]
    C += [p(
        "<font face='Courier'>tests/test_architecture.py</font> lee cada módulo con "
        "<font face='Courier'>ast</font> y falla si una capa importa algo que no debe (por "
        "ejemplo, <font face='Courier'>domain</font> importando "
        "<font face='Courier'>tkinter</font>, o <font face='Courier'>presentation</font> "
        "importando <font face='Courier'>infrastructure</font>), si el dominio o los "
        "casos de uso llaman a funciones que tocan el disco, o si algo fuera de "
        "<font face='Courier'>bootstrap.py</font> construye un adaptador. La propia "
        "prueba se comprueba con fragmentos de código que rompen cada regla.")]

    # ======================================================================
    C += [PageBreak(), h1("4. La interfaz, explicada")]

    C += [h2("4.1. CustomTkinter y el arranque")]
    C += [p(
        "CustomTkinter es Tkinter con widgets repintados. "
        "<font face='Courier'>MainWindow</font> hereda de "
        "<font face='Courier'>ctk.CTk</font> y recibe el objeto "
        "<font face='Courier'>Services</font>. "
        "<font face='Courier'>app.py</font> (o "
        "<font face='Courier'>python -m duplicate_finder</font>) llama a "
        "<font face='Courier'>bootstrap.main()</font>: arranca el registro de errores, "
        "construye los servicios y abre la ventana.")]

    C += [h2("4.2. El patrón hilo + cola + after() (el más importante)")]
    C += [p(
        "Tkinter no es 'thread-safe': solo el hilo principal puede tocar "
        "widgets. Pero escanear tarda. La solución está en una sola clase, "
        "<font face='Courier'>presentation/background_job.py</font>, que usan todas las "
        "tareas largas (escanear, analizar, mover, reunir):")]
    C += [pre(
        "# hilo principal: lanzar. BackgroundJob programa el sondeo con after().\n"
        "self._scan_job.start(\n"
        "    lambda report: self._services.scan_duplicates(folder, progress=report, ...),\n"
        "    what=f'Scan of {folder}')\n\n"
        "# dentro de BackgroundJob, hilo secundario: NO toca widgets, solo la cola\n"
        "result = work(lambda value: messages.put(('progress', value)))\n"
        "messages.put(('done', result))\n\n"
        "# hilo principal, cada 100 ms: vaciar la cola y avisar a la pestaña\n"
        "kind, datum = self._messages.get_nowait()\n"
        "if kind == 'progress': self._on_progress(datum)\n"
        "elif kind == 'done':   self._on_done(datum)")]
    C += [p(
        "Así la ventana no se congela, se ve el progreso y se puede cancelar "
        "(el hilo comprueba un <font face='Courier'>threading.Event</font> entre "
        "archivo y archivo). Si la tarea falla, <font face='Courier'>BackgroundJob</font> "
        "anota el error con su traza y avisa a la pestaña. Se prueba sin ventana "
        "(<font face='Courier'>tests/test_background_job.py</font>) sustituyendo "
        "<font face='Courier'>after</font> por un planificador que maneja la prueba.")]

    C += [h2("4.3. Las tres pestañas")]
    C += [p(
        "Un <font face='Courier'>ctk.CTkTabview</font> con tres pestañas. Cada "
        "una es un <b>componente</b>: una clase que hereda de "
        "<font face='Courier'>ctk.CTkFrame</font> y guarda su PROPIO estado "
        "(el resultado, las tareas en segundo plano...) en lugar de compartirlo con la "
        "ventana. La ventana solo las crea "
        "(<font face='Courier'>self.exact</font>, "
        "<font face='Courier'>self.similar</font> y "
        "<font face='Courier'>self.gather</font>) y les avisa con "
        "<font face='Courier'>apply_mode(advanced)</font> y "
        "<font face='Courier'>cancel_jobs()</font>. Cada pestaña repite el "
        "patrón: tarjeta de arriba con la carpeta, zona de progreso, panel de "
        "estadísticas, galería/tabla y barra inferior con el botón de acción. Las "
        "partes grandes son componentes aparte (<font face='Courier'>ScanOptionsPanel</font>, "
        "<font face='Courier'>PreviewPanel</font>), y las preguntas de mover "
        "(elegir la cuarentena, avisos) están en <font face='Courier'>dialogs.py</font>.")]

    C += [h2("4.4. Textos e idiomas")]
    C += [p(
        "Ningún texto de la interfaz está escrito en el código: cada uno se pide con "
        "<font face='Courier'>tr('clave', ...)</font>, y los textos viven en un catálogo por "
        "idioma (<font face='Courier'>i18n/locales/en.py</font> y "
        "<font face='Courier'>es.py</font>), un diccionario de claves a frases con "
        "marcadores:")]
    C += [pre(
        "\"exact.moved_summary\": \"{moved} file(s) moved ({size}).\"      # en.py\n"
        "\"exact.moved_summary\": \"Se han movido {moved} archivo(s) ({size}).\"  # es.py\n\n"
        "label.configure(text=tr('exact.moved_summary', moved=3, size='1.2 MB'))")]
    C += [p(
        "El idioma se elige al arrancar (el guardado, o el de Windows, o inglés), antes "
        "de crear ningún widget; por eso el selector de la cabecera se aplica la próxima "
        "vez. <font face='Courier'>tests/test_i18n.py</font> comprueba que los dos "
        "catálogos tienen las mismas claves y marcadores, y que todo texto que pide el "
        "código existe. Los selectores (modo, tema, estrategia...) trabajan con claves "
        "estables y no con el texto visible, para que cambiar de idioma no rompa nada.")]

    C += [h2("4.5. Tema claro / oscuro")]
    C += [p(
        "En <font face='Courier'>presentation/styles.py</font> cada color es una tupla "
        "<font face='Courier'>(claro, oscuro)</font>. Los widgets de "
        "CustomTkinter aceptan esa tupla y cambian solos. Para lo que NO es "
        "CustomTkinter (la tabla <font face='Courier'>ttk.Treeview</font> y el "
        "<font face='Courier'>tk.Canvas</font> del visor) se usa "
        "<font face='Courier'>styles.col(tupla)</font>, que devuelve el color "
        "del tema activo, y se re-pinta a mano sobreescribiendo "
        "<font face='Courier'>_set_appearance_mode</font>:")]
    C += [pre(
        "def _set_appearance_mode(self, mode_string):\n"
        "    super()._set_appearance_mode(mode_string)\n"
        "    self._configure_ttk_style()    # ttk no cambia solo\n"
        "    self._configure_tags()")]
    C += [p(
        "Los botones deshabilitados pasan a gris (relleno y texto) con "
        "<font face='Courier'>styles.activate_button(btn, active)</font>, para "
        "que 'deshabilitado' no se confunda con un color de acción o de error. "
        "El tema elegido se guarda con el resto de los ajustes "
        "(<font face='Courier'>AppSettings</font>).")]

    C += [h2("4.6. Modo Sencilla / Avanzada")]
    C += [p(
        "<font face='Courier'>_apply_mode()</font> no crea ni destruye "
        "widgets: los quita y pone del grid con "
        "<font face='Courier'>grid_remove()</font> / "
        "<font face='Courier'>grid()</font>. Así el estado (lo que hubiera "
        "escrito el usuario) se conserva al alternar. La elección se guarda en los "
        "ajustes.")]

    C += [h2("4.7. La tabla (ttk.Treeview)")]
    C += [p(
        "Para los duplicados exactos se usa un "
        "<font face='Courier'>ttk.Treeview</font> (aguanta miles de filas). Al "
        "hacer clic hay que preguntarle a Tk qué hay debajo del ratón:")]
    C += [pre(
        "self.tree.identify_row(event.y)      # id de la fila\n"
        "self.tree.identify_column(event.x)   # '#1' = columna 'Decisión'\n"
        "self.tree.identify_region(x, y)      # 'heading', 'cell'...")]
    C += [p(
        "Con eso: clic normal = seleccionar (y mostrar la vista previa); clic en "
        "'Decisión' = alternar conservar/mover; doble clic = 'conservar solo "
        "esta'.")]

    C += [h2("4.8. Miniaturas e imágenes en Tkinter")]
    C += [bullet_list([
        "Decodificar la imagen (Pillow) se hace en un hilo; produce un objeto "
        "PIL.",
        "Convertir a <font face='Courier'>ImageTk.PhotoImage</font> y pegarlo en "
        "la fila se hace en el hilo principal.",
        "<b>Hay que guardar una referencia</b> a cada PhotoImage "
        "(<font face='Courier'>self._img_refs[iid] = photo</font>). Si no, Python "
        "la recolecta y la imagen desaparece de la pantalla.",
    ])]

    # ======================================================================
    C += [PageBreak(), h1("5. Empaquetado")]
    C += [p(
        "<font face='Courier'>build.spec</font> configura PyInstaller: un solo "
        "archivo, sin consola, con los datos de CustomTkinter incluidos y "
        "<font face='Courier'>icon.ico</font> como icono (el código está en "
        "<font face='Courier'>src/</font>, que se añade a la ruta de búsqueda). "
        "<font face='Courier'>build_exe.py</font> lo ejecuta y comprueba el "
        "resultado.")]
    C += [p(
        "El icono es una lupa <b>dibujada por código</b> "
        "(<font face='Courier'>presentation/icons.py:window_icon</font>) sobre un "
        "<font face='Courier'>tk.PhotoImage</font>, y "
        "<font face='Courier'>gen_icon.py</font> arma el "
        "<font face='Courier'>.ico</font> multi-tamaño a mano con "
        "<font face='Courier'>struct</font>. Nada de imágenes externas.")]

    # ======================================================================
    C += [h1("6. Cómo se prueba")]
    C += [p(
        "Hay varios niveles. Las pruebas de comportamiento sobre archivos no usan "
        "<i>mocks</i>: cada una crea archivos reales en una carpeta temporal "
        "(<font face='Courier'>tempfile.TemporaryDirectory</font>), ejecuta la función "
        "de verdad y comprueba el estado en disco. Las de los casos de uso "
        "(<font face='Courier'>tests/test_use_cases.py</font>) usan los dobles en memoria "
        "de <font face='Courier'>tests/fakes.py</font>. Las de interfaz montan la "
        "ventana entera, simulan los diálogos "
        "(<font face='Courier'>filedialog</font> y "
        "<font face='Courier'>messagebox</font> se sustituyen por funciones que "
        "devuelven un valor fijo) y pulsan los métodos de los botones. Además hay "
        "pruebas de la arquitectura, de los catálogos de idioma y de la migración de "
        "los datos de la versión 1.0.")]
    C += [pre(
        "pytest                    # todo\n"
        "pytest -m \"not gui\"       # solo lógica, sin abrir ventanas\n"
        "pytest --cov              # con cobertura (el CI exige 90 % lógica, 70 % interfaz)\n"
        "python tests/check_perceptual.py \"D:\\Fotos\" 10   # con datos reales")]

    C += [h1("7. Añadir una función nueva: receta")]
    C += [bullet_list([
        "<b>1.</b> Escribe la regla pura en <font face='Courier'>domain/</font> y el "
        "caso de uso en <font face='Courier'>application/</font> (una clase, con los "
        "puertos que necesite en el constructor). Si necesita algo del mundo exterior "
        "que no existe aún, añade un puerto y su adaptador en "
        "<font face='Courier'>infrastructure/</font>.",
        "<b>2.</b> Conéctalo en <font face='Courier'>bootstrap.py</font> y añádelo a "
        "<font face='Courier'>Services</font>.",
        "<b>3.</b> Añade pruebas: del caso de uso con dobles en memoria y, si toca "
        "archivos de verdad, con carpetas temporales.",
        "<b>4.</b> En <font face='Courier'>presentation/</font>, añade los widgets y un "
        "handler que llame al caso de uso. Si la tarea es larga, lánzala con "
        "<font face='Courier'>BackgroundJob</font>. Cada texto nuevo va a los dos "
        "catálogos con <font face='Courier'>tr()</font>.",
        "<b>5.</b> Si mueve o copia archivos, hazlo pasar por "
        "<font face='Courier'>FileTransfers</font> y regístralo en el historial para que "
        "se pueda deshacer.",
        "<b>6.</b> Ejecuta <font face='Courier'>pytest</font>, "
        "<font face='Courier'>ruff check .</font> y "
        "<font face='Courier'>python -m mypy</font>. "
        "Todo en verde antes de dar por hecho nada: incluida la prueba de arquitectura, que "
        "te avisa si has puesto algo en la capa equivocada.",
    ])]

    return C
