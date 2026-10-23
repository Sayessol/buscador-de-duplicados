"""Generates 'guia-del-codigo.pdf'.

A document for whoever wants to understand HOW the code is built and
learn from it.
"""

from pathlib import Path

from reportlab.platypus import PageBreak

from _pdf_common import build, h1, h2, h3, p, note, bullet_list, table, pre

OUTPUT = (Path(__file__).resolve().parent / "guia-del-codigo.pdf")

C = []

# ======================================================================
C += [h1("1. Cómo leer este proyecto")]
C += [p(
    "En esta guía te explico cómo está hecho el código, para que puedas "
    "entenderlo y aprender de él, igual que yo he ido aprendiendo. Está en la "
    "raíz del repositorio y lo dividí en tres partes bien separadas:")]
C += [table([
    ["Carpeta", "Qué contiene", "Regla"],
    ["core/", "Toda la lógica: escanear, comparar, mover, deshacer.",
     "No importa NADA de la interfaz. Se prueba entero por consola."],
    ["ui/", "La ventana y todos sus widgets (CustomTkinter).",
     "Solo pinta y reacciona a clics; delega la lógica en core/."],
    ["tests/", "15 suites + pruebas unitarias; se ejecutan con pytest.",
     "Crean archivos de verdad y comprueban el resultado en disco."],
], widths_cm=[2.4, 6.8, 6.4])]
C += [p(
    "<b>Por dónde te recomiendo empezar a leer:</b> "
    "<font face='Courier'>core/scanner.py</font> (el algoritmo central), "
    "luego <font face='Courier'>app.py</font> y "
    "<font face='Courier'>ui/main_window.py</font> (la carcasa de la ventana; "
    "cada pestaña es un componente en su <font face='Courier'>pestana_*.py</font>). "
    "El resto son piezas que se entienden solas con su docstring.")]

C += [h2("1.1. Mapa de módulos")]
C += [table([
    ["core/", ""],
    ["hashing.py", "hash BLAKE2b (parcial y completo); formatear bytes a KB/MB."],
    ["scanner.py", "escanear(): las 3 pasadas. Devuelve ScanResult."],
    ["filters.py", "ScanFilter: qué incluir/excluir. CATEGORY_EXTENSIONS."],
    ["selection.py", "DuplicateSelection: estado conservar/mover por grupo."],
    ["quarantine.py", "move_to_quarantine(): mover preservando estructura + CSV."],
    ["perceptual.py", "fotos parecidas: dHash, distancia de Hamming, BK-tree."],
    ["file_moves.py", "primitivas mover/copiar lotes (las usa gather.py)."],
    ["gather.py", "listar imágenes + estrategias por archivos / carpeta entera."],
    ["history.py", "registro de operaciones en JSON + deshacer."],
    ["config.py", "JSON persistente: recuerda el modo (Sencilla/Avanzada) y el tema."],
], widths_cm=[2.8, 12.8])]
C += [table([
    ["ui/", ""],
    ["main_window.py", "MainWindow: cabecera, tema y modo. Crea los 3 componentes."],
    ["exact_duplicates_tab.py", "ExactDuplicatesTab: pestaña Duplicados exactos."],
    ["similar_photos_tab.py", "SimilarPhotosTab: pestaña Fotos parecidas."],
    ["gather_images_tab.py", "GatherImagesTab: pestaña Reunir imágenes."],
    ["extension_breakdown_dialog.py", "ExtensionBreakdownWindow: duplicados por extensión."],
    ["results_table.py", "ResultsTable: la tabla de duplicados exactos."],
    ["image_viewer.py", "ImageViewer: ver una foto a pantalla completa con zoom."],
    ["history_window.py", "HistoryWindow: lista de operaciones + Deshacer."],
    ["non_image_kinds_dialog.py", "diálogo 'qué hacer con los no-imagen'."],
    ["thumbnails.py", "generar miniaturas (imagen real o placeholder con la ext.)."],
    ["widgets.py, styles.py, icons.py", "piezas visuales, paleta clara/oscura y glifos."],
], widths_cm=[5.2, 10.4])]

# ======================================================================
C += [PageBreak(), h1("2. El núcleo, explicado")]

C += [h2("2.1. Detectar duplicados exactos: tres pasadas")]
C += [p(
    "Comparar el contenido de cada archivo con el de todos los demás sería "
    "lentísimo. En vez de eso filtro de lo barato a lo caro "
    "(<font face='Courier'>core/scanner.py</font>). Cada pasada es una función "
    "(<font face='Courier'>_pasada_tamanos</font>, "
    "<font face='Courier'>_pasada_hash_parcial</font> y "
    "<font face='Courier'>_pasada_hash_completo</font>) y "
    "<font face='Courier'>escanear()</font> solo las encadena:")]
C += [bullet_list([
    "<b>Pasada 1 — tamaños.</b> Recorro la carpeta con "
    "<font face='Courier'>os.walk</font> y agrupo los archivos por su "
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
    "por_parcial[(tamano, hp)].append(ruta)\n"
    "...\n"
    "finalistas = {c: r for c, r in por_parcial.items() if len(r) > 1}")]
C += [note(
    "Optimización sutil: si un archivo pesa menos de 64 KB, su hash parcial "
    "ya cubre todo el contenido, así que me salto la Pasada 3 para él.")]

C += [h3("Podar carpetas con os.walk")]
C += [p(
    "<font face='Courier'>os.walk</font> entrega tres cosas por carpeta: "
    "(ruta, subcarpetas, archivos). Si modificas la lista de subcarpetas "
    "<i>en el sitio</i>, os.walk no entra en las que quites — así se "
    "excluyen <font face='Courier'>node_modules</font>, "
    "<font face='Courier'>$RECYCLE.BIN</font>, etc. sin recorrerlas:")]
C += [pre("subdirs[:] = [d for d in subdirs if not filtro.excluye_carpeta(d)]")]

C += [h2("2.2. El hash: BLAKE2b y lectura en bloques")]
C += [p(
    "Uso BLAKE2b (viene con Python, más rápido que SHA-256). El archivo "
    "completo lo leo de 64 KB en 64 KB para no cargarlo entero en memoria:")]
C += [pre(
    "h = hashlib.blake2b()\n"
    "with open(ruta, 'rb') as f:\n"
    "    while True:\n"
    "        bloque = f.read(65536)     # 64 KB\n"
    "        if not bloque:              # b'' = fin del archivo\n"
    "            break\n"
    "        h.update(bloque)            # acumula\n"
    "return h.hexdigest()")]

C += [h2("2.3. El filtro: lista blanca y lista negra")]
C += [p(
    "<font face='Courier'>ScanFilter</font> tiene dos mecanismos. Una "
    "<b>lista blanca</b> (<font face='Courier'>extensiones_incluidas</font>): "
    "si no está vacía, solo pasan esas extensiones ('buscar solo "
    "imágenes'). Y varias <b>listas negras</b> (extensiones, carpetas y "
    "nombres a ignorar, más un tamaño mínimo). El escáner llama a "
    "<font face='Courier'>filtro.excluye_nombre(...)</font> y "
    "<font face='Courier'>filtro.excluye_carpeta(...)</font> y no cuenta ni "
    "lee lo que se excluye.")]

C += [PageBreak(), h2("2.4. La decisión: qué copia se conserva")]
C += [p(
    "<font face='Courier'>DuplicateSelection</font> es un diccionario "
    "<font face='Courier'>(indice_grupo, ruta) -&gt; 'conservar' | 'mover'</font>. "
    "Empieza todo en 'conservar' (no se movería nada). La regla que impone "
    "la app: para poder mover, cada grupo debe tener <b>exactamente una</b> "
    "copia en 'conservar'.")]
C += [p(
    "En modo Sencilla, <font face='Courier'>preselect_primary()</font> "
    "elige sola la copia principal de cada grupo con esta puntuación (gana "
    "la tupla más pequeña):")]
C += [pre(
    "(parece_copia,   # 0 si el nombre no tiene 'copia', '(1)'...  1 si sí\n"
    " profundidad,    # nº de carpetas: cuanto menos anidada, mejor\n"
    " mtime,          # fecha: la más antigua suele ser el original\n"
    " len(ruta))      # a igualdad de todo, la ruta más corta")]

C += [h2("2.5. Fotos parecidas: dHash + BK-tree + Union-Find")]
C += [p(
    "Aquí no puedo comparar contenido (dos fotos parecidas tienen bytes "
    "distintos). Por cada imagen calculo una <b>huella</b> "
    "(<font face='Courier'>core/perceptual.py</font>):")]
C += [h3("dHash de 64 bits")]
C += [p(
    "Reduzco la imagen a una miniatura de 9×8 en gris. Por cada fila, "
    "comparo cada píxel con el de su derecha: bit 1 si sube el brillo, 0 si "
    "baja. 8×8 = 64 bits. Mide la <i>forma</i>, no el color, por eso "
    "aguanta la recompresión y los filtros:")]
C += [pre(
    "bits = 0\n"
    "for fila in range(8):\n"
    "    for col in range(8):\n"
    "        sube = gris[base+col] < gris[base+col+1]\n"
    "        bits = (bits << 1) | (1 if sube else 0)")]
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
    "<font face='Courier'>grupos()</font> agrupa por representante.")]

C += [PageBreak(), h2("2.6. Mover archivos con seguridad")]
C += [p(
    "Tres módulos comparten las mismas reglas "
    "(<font face='Courier'>quarantine.py</font>, "
    "<font face='Courier'>file_moves.py</font>, "
    "<font face='Courier'>gather.py</font>):")]
C += [bullet_list([
    "<b>Nunca pisar.</b> Antes de mover, si el destino ya existe pruebo "
    "<font face='Courier'>nombre (1).ext</font>, "
    "<font face='Courier'>nombre (2).ext</font>...",
    "<b>Preservar estructura.</b> El destino de cada archivo es "
    "<font face='Courier'>carpeta_destino / os.path.relpath(origen, raiz)</font>, "
    "así se recrea la jerarquía de subcarpetas.",
    "<b>Mover, no copiar-y-borrar.</b> <font face='Courier'>shutil.move</font> "
    "hace un <font face='Courier'>rename</font> atómico si es el mismo disco; "
    "solo copia+borra si es otro disco (y ahí el original desaparece cuando "
    "la copia ya está a salvo).",
    "<b>Destino fuera del origen.</b> <font face='Courier'>validar_destino</font> "
    "lo comprueba (si no, el próximo escaneo reencontraría lo movido).",
])]

C += [h2("2.7. Historial y deshacer")]
C += [p(
    "Cada operación de mover/copiar se apunta en "
    "<font face='Courier'>%APPDATA%\\BuscadorDuplicados\\historial.json</font> "
    "con la lista de pares (origen, destino). "
    "<font face='Courier'>deshacer(id)</font>:")]
C += [bullet_list([
    "si fue <b>mover</b>: <font face='Courier'>shutil.move(destino, origen)</font> "
    "de vuelta — pero si ya hay algo en el origen, lo avisa y no pisa.",
    "si fue <b>copiar</b>: borra las copias del destino. Es el único punto "
    "de todo el código donde se borra algo, y solo archivos que la app creó.",
])]

# ======================================================================
C += [PageBreak(), h1("3. La interfaz, explicada")]

C += [h2("3.1. CustomTkinter y el arranque")]
C += [p(
    "CustomTkinter es Tkinter con widgets repintados. "
    "<font face='Courier'>MainWindow</font> hereda de "
    "<font face='Courier'>ctk.CTk</font>. "
    "<font face='Courier'>app.py</font> es de tres líneas: aplica el tema, "
    "crea la ventana y llama a <font face='Courier'>mainloop()</font>.")]

C += [h2("3.2. El patrón hilo + cola + after() (el más importante)")]
C += [p(
    "Tkinter no es 'thread-safe': solo el hilo principal puede tocar "
    "widgets. Pero escanear tarda. La solución, que repito en toda la app:")]
C += [pre(
    "# hilo principal: lanzar y programar el sondeo\n"
    "threading.Thread(target=self._trabajo, daemon=True).start()\n"
    "self.after(100, self._revisar_cola)\n\n"
    "# hilo secundario: NO toca widgets, solo la cola\n"
    "def _trabajo(self):\n"
    "    res = escanear(..., progreso=lambda p: self._cola.put(('prog', p)))\n"
    "    self._cola.put(('hecho', res))\n\n"
    "# hilo principal, cada 100 ms: vaciar la cola y pintar\n"
    "def _revisar_cola(self):\n"
    "    try:\n"
    "        while True:\n"
    "            tipo, dato = self._cola.get_nowait()\n"
    "            ...   # actualizar widgets según 'tipo'\n"
    "    except queue.Empty:\n"
    "        pass\n"
    "    self.after(100, self._revisar_cola)")]
C += [p(
    "Así la ventana no se congela, se ve el progreso y se puede cancelar "
    "(el hilo comprueba un <font face='Courier'>threading.Event</font> entre "
    "archivo y archivo).")]

C += [PageBreak(), h2("3.3. Las tres pestañas")]
C += [p(
    "Un <font face='Courier'>ctk.CTkTabview</font> con tres pestañas. Cada "
    "una es un <b>componente</b>: una clase que hereda de "
    "<font face='Courier'>ctk.CTkFrame</font> y guarda su PROPIO estado "
    "(las colas, el hilo, el resultado...) en lugar de compartirlo con la "
    "ventana. La ventana solo las crea "
    "(<font face='Courier'>self.exactos</font>, "
    "<font face='Courier'>self.parecidas</font> y "
    "<font face='Courier'>self.reunir</font>) y les avisa con "
    "<font face='Courier'>aplicar_modo(avanzado)</font> y "
    "<font face='Courier'>cancel_jobs()</font>. Cada pestaña repite el "
    "patrón: tarjeta de arriba con la carpeta, zona de progreso, panel de "
    "estadísticas, galería/tabla y barra inferior con el botón de acción.")]

C += [h2("3.4. Tema claro / oscuro")]
C += [p(
    "En <font face='Courier'>ui/styles.py</font> cada color es una tupla "
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
    "    self._configurar_estilo_ttk()   # ttk no cambia solo\n"
    "    self._configurar_tags()")]
C += [p(
    "Los botones deshabilitados pasan a gris (relleno y texto) con "
    "<font face='Courier'>styles.activar_boton(btn, activo)</font>, para "
    "que 'deshabilitado' no se confunda con un color de acción o de error. "
    "El tema elegido se guarda en <font face='Courier'>config.py</font> "
    "(auto/claro/oscuro).")]

C += [h2("3.5. Modo Sencilla / Avanzada")]
C += [p(
    "<font face='Courier'>_aplicar_modo()</font> no crea ni destruye "
    "widgets: los quita y pone del grid con "
    "<font face='Courier'>grid_remove()</font> / "
    "<font face='Courier'>grid()</font>. Así el estado (lo que hubiera "
    "escrito el usuario) se conserva al alternar. La elección se guarda en "
    "<font face='Courier'>config.py</font>.")]

C += [h2("3.6. La tabla (ttk.Treeview)")]
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

C += [h2("3.7. Miniaturas e imágenes en Tkinter")]
C += [bullet_list([
    "Decodificar la imagen (Pillow) se hace en un hilo; produce un objeto "
    "PIL.",
    "Convertir a <font face='Courier'>ImageTk.PhotoImage</font> y pegarlo en "
    "la fila se hace en el hilo principal.",
    "<b>Hay que guardar una referencia</b> a cada PhotoImage "
    "(<font face='Courier'>self._img_refs[iid] = foto</font>). Si no, Python "
    "la recolecta y la imagen desaparece de la pantalla.",
])]

# ======================================================================
C += [PageBreak(), h1("4. Empaquetado")]
C += [p(
    "<font face='Courier'>build.spec</font> configura PyInstaller: un solo "
    "archivo, sin consola, con los datos de CustomTkinter incluidos y "
    "<font face='Courier'>icono.ico</font> como icono. "
    "<font face='Courier'>build_exe.py</font> lo ejecuta y comprueba el "
    "resultado.")]
C += [p(
    "El icono es una lupa <b>dibujada por código</b> "
    "(<font face='Courier'>ui/icons.py:icono_ventana</font>) sobre un "
    "<font face='Courier'>tk.PhotoImage</font>, y "
    "<font face='Courier'>gen_icon.py</font> arma el "
    "<font face='Courier'>.ico</font> multi-tamaño a mano con "
    "<font face='Courier'>struct</font>. Nada de imágenes externas.")]

# ======================================================================
C += [h1("5. Cómo se prueba")]
C += [p(
    "Mis pruebas no usan <i>mocks</i>: cada una crea archivos reales en una "
    "carpeta temporal (<font face='Courier'>tempfile.TemporaryDirectory</font>), "
    "ejecuta la función de verdad y comprueba el estado en disco. Las de "
    "interfaz montan la ventana entera, simulan los diálogos "
    "(<font face='Courier'>filedialog</font> y "
    "<font face='Courier'>messagebox</font> se sustituyen por funciones que "
    "devuelven un valor fijo) y pulsan los métodos de los botones.")]
C += [pre(
    "pytest   # 134 pruebas;  pytest --cov = cobertura (núcleo 93 %, interfaz 79 %)\n"
    "python tests/check_perceptual.py \"D:\\Fotos\" 10   # con datos reales")]

C += [h1("6. Añadir una función nueva: receta")]
C += [bullet_list([
    "<b>1.</b> Escribe la lógica en un módulo de "
    "<font face='Courier'>core/</font>, sin tocar la interfaz. Que reciba "
    "rutas y devuelva datos.",
    "<b>2.</b> Añade una prueba en <font face='Courier'>tests/</font> que "
    "cree archivos temporales y compruebe el resultado. Súmala a "
    "<font face='Courier'>LOGICA</font> en <font face='Courier'>test_suites.py</font>.",
    "<b>3.</b> En <font face='Courier'>ui/</font>, añade los widgets y un "
    "handler. Si la tarea es larga, usa el patrón hilo + cola + after().",
    "<b>4.</b> Si mueve o copia archivos, hazlo pasar por "
    "<font face='Courier'>core/file_moves.py</font> y regístralo en "
    "<font face='Courier'>history.py</font> para que se pueda deshacer.",
    "<b>5.</b> Ejecuta <font face='Courier'>pytest</font>, "
    "<font face='Courier'>ruff check .</font> y "
    "<font face='Courier'>python -m mypy</font>. "
    "Todo en verde antes de dar por hecho nada.",
])]


build(
    OUTPUT,
    title="Buscador de duplicados",
    subtitle="Guía del código — cómo funciona por dentro",
    short_title="Guía del código",
    cover_summary=(
        "Recorrido por el código para quien quiera entenderlo o aprender a "
        "partir de él: la arquitectura, los algoritmos (las 3 pasadas del "
        "escaneo, dHash, BK-tree, Union-Find), el patrón de hilos de la "
        "interfaz, el empaquetado y cómo se prueba todo."),
    body_flowables=C)
