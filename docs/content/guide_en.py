"""Contents of 'code-guide.pdf' (English).

A document for whoever wants to understand HOW the code is built and learn from it.
"""

from reportlab.platypus import PageBreak

from _pdf_common import bullet_list, h1, h2, h3, note, p, pre, table

TITLE = "Duplicate Finder"
SUBTITLE = "Code guide — how it works inside"
SHORT_TITLE = "Code guide"
COVER_SUMMARY = (
    "A tour of the code for anyone who wants to understand it or learn from it: the "
    "layered architecture with ports and adapters, the algorithms (the 3 passes of the "
    "scan, dHash, BK-tree, Union-Find), the interface's threading pattern, the "
    "languages, the packaging and how everything is tested.")


def body():
    C = []

    # ======================================================================
    C += [h1("1. How to read this project")]
    C += [p(
        "This guide explains how the code is built, so that you can understand it and "
        "learn from it, just as I have been learning. It lives in the "
        "<font face='Courier'>src/duplicate_finder/</font> package, split into layers, "
        "with a test folder next to it:")]
    C += [table([
        ["Folder", "What it contains", "Rule"],
        ["domain/", "Rules and data: filters, duplicate groups, selection, similarity.",
         "Imports nothing from the rest. No input or output (no disk, no window)."],
        ["application/", "The use cases (scan, move, gather, history...) and the ports "
                         "they need.",
         "Imports only domain/ and i18n/. The disk only through ports."],
        ["infrastructure/", "The adapters: disk, hashes, Pillow, JSON, logging.",
         "Implements the ports. Never imports the interface."],
        ["presentation/", "The window and all its widgets (CustomTkinter).",
         "Only draws and reacts to clicks; delegates to the use cases."],
        ["i18n/", "The English and Spanish texts.", "Imports nothing."],
        ["tests/", "pytest tests, at several levels.",
         "They create real files or use in-memory fakes of the ports."],
    ], widths_cm=[2.8, 6.6, 6.2])]
    C += [p(
        "<b>Where I recommend you start reading:</b> "
        "<font face='Courier'>application/scan_duplicates.py</font> (the central "
        "algorithm), then <font face='Courier'>bootstrap.py</font> (how everything is "
        "wired) and <font face='Courier'>presentation/main_window.py</font> (the window "
        "shell; each tab is a component in its own <font face='Courier'>*_tab.py</font>). "
        "The rest are pieces that explain themselves with their docstring.")]

    C += [h2("1.1. Module map")]
    C += [table([
        ["domain/", ""],
        ["duplicates.py", "DuplicateFile, DuplicateGroup, ScanResult: the result of a "
                          "scan."],
        ["filters.py", "ScanFilter: what to include/exclude. CATEGORY_EXTENSIONS."],
        ["selection.py", "DuplicateSelection: keep/move state per group."],
        ["similarity.py", "similar photos: Hamming distance, BK-tree, Union-Find."],
        ["transfers.py", "move/copy rules and what to do with the non-image files."],
        ["formatting.py, operations.py", "readable sizes (KB/MB) and operation kinds."],
    ], widths_cm=[4.4, 11.2])]
    C += [table([
        ["application/", ""],
        ["ports.py", "the interfaces (Protocol): FileSystem, FileHasher, "
                     "FingerprintReader, HistoryStore, SettingsStore."],
        ["scan_duplicates.py", "ScanDuplicates: the 3 passes. Returns a ScanResult."],
        ["find_similar_photos.py", "FindSimilarPhotos: fingerprints + grouping."],
        ["quarantine.py", "MoveToQuarantine: validate, move preserving structure, CSV, "
                          "history."],
        ["gather.py, file_transfers.py", "GatherImages and the batch move/copy "
                                         "primitives."],
        ["history.py", "OperationHistory: log of operations + undo."],
        ["report.py, settings.py, start_selection.py", "CSV export, settings, "
                                                        "preselection."],
        ["services.py", "Services: all the use cases together, for the interface."],
    ], widths_cm=[4.4, 11.2])]
    C += [table([
        ["infrastructure/", ""],
        ["local_file_system.py", "LocalFileSystem: os and shutil (with retries on delete)."],
        ["hashing.py", "Blake2Hasher: partial and full BLAKE2b hash."],
        ["image_fingerprints.py", "PillowFingerprintReader: dHash and colour signature."],
        ["history_store.py, settings.py", "JsonHistoryStore and JsonSettingsStore (and the "
                                          "migration of the 1.0 data)."],
        ["app_logging.py, data_folder.py", "error log and data folder."],
    ], widths_cm=[4.4, 11.2])]
    C += [table([
        ["presentation/", ""],
        ["main_window.py", "MainWindow: header, theme, language and view. Creates the 3 tabs."],
        ["exact_duplicates_tab.py", "ExactDuplicatesTab: the Exact duplicates tab."],
        ["similar_photos_tab.py", "SimilarPhotosTab: the Similar photos tab."],
        ["gather_images_tab.py", "GatherImagesTab: the Gather images tab."],
        ["scan_options_panel.py, preview_panel.py", "the two panels of the first tab."],
        ["background_job.py", "BackgroundJob: thread + queue + polling, for every long task."],
        ["results_table.py", "ResultsTable: the table of exact duplicates."],
        ["dialogs.py", "the questions the three tabs share when moving."],
        ["image_viewer.py, history_window.py, ...", "viewer with zoom, history + Undo, "
                                                    "dialogs."],
        ["thumbnails.py, widgets.py, styles.py, icons.py",
         "thumbnails, visual pieces, light/dark palette and glyphs."],
    ], widths_cm=[5.2, 10.4])]

    # ======================================================================
    C += [PageBreak(), h1("2. The logic, explained")]

    C += [h2("2.1. Detecting exact duplicates: three passes")]
    C += [p(
        "Comparing the content of every file with that of every other would be "
        "painfully slow. Instead I filter from cheap to expensive "
        "(<font face='Courier'>application/scan_duplicates.py</font>). Each pass is a "
        "method (<font face='Courier'>_size_pass</font>, "
        "<font face='Courier'>_partial_hash_pass</font> and "
        "<font face='Courier'>_full_hash_pass</font>) and "
        "<font face='Courier'>ScanDuplicates.__call__()</font> only chains them:")]
    C += [bullet_list([
        "<b>Pass 1 — sizes.</b> I walk the folder with the "
        "<font face='Courier'>FileSystem.walk</font> port (underneath, "
        "<font face='Courier'>os.walk</font>) and group the files by size in bytes. A "
        "unique size cannot have duplicates, so I discard it without opening the file.",
        "<b>Pass 2 — partial hash.</b> For those that share a size, I compute the "
        "BLAKE2b hash of only the first 64 KB. Fast, and it discards almost all of "
        "those that are not equal.",
        "<b>Pass 3 — full hash.</b> Only for those that also share a partial hash, I "
        "hash the whole file. Those that match here are identical byte for byte.",
    ])]
    C += [pre(
        "# key = (size, partial_hash): two files with the same partial hash\n"
        "# but a different size are never the same file.\n"
        "by_partial[(size, hp)].append(path)\n"
        "...\n"
        "finalists = {key: paths for key, paths in by_partial.items() if len(paths) > 1}")]
    C += [note(
        "A subtle optimisation: if a file weighs less than 64 KB, its partial hash "
        "already covers the whole content, so I skip Pass 3 for it.")]

    C += [h3("Pruning folders while walking")]
    C += [p(
        "The walk hands you three things per folder: (path, subfolders, files). If you "
        "modify the list of subfolders <i>in place</i>, it does not enter the ones you "
        "remove — that is how <font face='Courier'>node_modules</font>, "
        "<font face='Courier'>$RECYCLE.BIN</font>, etc. are excluded without walking "
        "them:")]
    C += [pre("subdirs[:] = [d for d in subdirs if not filter.excludes_folder(d)]")]

    C += [h2("2.2. The hash: BLAKE2b and block reading")]
    C += [p(
        "I use BLAKE2b (it ships with Python, faster than SHA-256). It lives in "
        "<font face='Courier'>infrastructure/hashing.py</font>, and the use case receives "
        "it as a port (<font face='Courier'>FileHasher</font>). I read the whole file "
        "64 KB at a time so it is never loaded into memory in full:")]
    C += [pre(
        "h = hashlib.blake2b()\n"
        "with open(file_path, 'rb') as f:\n"
        "    while True:\n"
        "        block = f.read(65536)      # 64 KB\n"
        "        if not block:              # b'' = end of file\n"
        "            break\n"
        "        h.update(block)            # accumulates\n"
        "return h.hexdigest()")]

    C += [h2("2.3. The filter: whitelist and blacklist")]
    C += [p(
        "<font face='Courier'>ScanFilter</font> (in <font face='Courier'>domain/filters.py</font>) "
        "has two mechanisms. A <b>whitelist</b> "
        "(<font face='Courier'>included_extensions</font>): if it is not empty, only "
        "those extensions pass ('search only images'). And several <b>blacklists</b> "
        "(extensions, folders and names to ignore, plus a minimum size). The scan calls "
        "<font face='Courier'>filter.excludes_name(...)</font> and "
        "<font face='Courier'>filter.excludes_folder(...)</font> and neither counts nor "
        "reads what is excluded.")]

    C += [PageBreak(), h2("2.4. The decision: which copy is kept")]
    C += [p(
        "<font face='Courier'>DuplicateSelection</font> (in "
        "<font face='Courier'>domain/selection.py</font>) is a dictionary "
        "<font face='Courier'>(group_index, path) -&gt; 'keep' | 'move'</font>. "
        "Everything starts as 'keep' (nothing would be moved). The rule the app "
        "enforces: to be able to move, every group must have <b>exactly one</b> copy "
        "set to 'keep'.")]
    C += [p(
        "In Simple view, <font face='Courier'>preselect_primary()</font> picks the "
        "main copy of each group by itself with this score (the smallest tuple wins):")]
    C += [pre(
        "(looks_like_copy,  # 0 if the name has no 'copy', '(1)'...  1 if it does\n"
        " depth,            # number of folders: the less nested, the better\n"
        " mtime,            # date: the oldest is usually the original\n"
        " len(path))        # if all else is equal, the shortest path")]

    C += [h2("2.5. Similar photos: dHash + BK-tree + Union-Find")]
    C += [p(
        "Here I cannot compare content (two similar photos have different bytes). For "
        "each image I compute a <b>fingerprint</b> "
        "(<font face='Courier'>infrastructure/image_fingerprints.py</font>, with Pillow); "
        "comparing fingerprints is pure logic "
        "(<font face='Courier'>domain/similarity.py</font>):")]
    C += [h3("64-bit dHash")]
    C += [p(
        "I shrink the image to a 9×8 grayscale thumbnail. For each row, I compare each "
        "pixel with the one to its right: bit 1 if the brightness goes up, 0 if it goes "
        "down. 8×8 = 64 bits. It measures the <i>shape</i>, not the colour, which is why "
        "it withstands recompression and filters:")]
    C += [pre(
        "bits = 0\n"
        "for row in range(8):\n"
        "    for col in range(8):\n"
        "        goes_up = gray[base+col] < gray[base+col+1]\n"
        "        bits = (bits << 1) | (1 if goes_up else 0)")]
    C += [h3("Hamming distance")]
    C += [p(
        "How different two fingerprints are = how many bits differ. "
        "<font face='Courier'>bin(a ^ b).count('1')</font>. 0 = identical, 64 = "
        "opposite. The sensitivity slider sets the threshold (~10).")]
    C += [h3("BK-tree")]
    C += [p(
        "To avoid comparing every photo with every other, I put the dHashes in a "
        "BK-tree: a tree where each child is labelled with its exact distance to its "
        "parent. When searching for 'those within &le; N', the triangle inequality lets "
        "me <b>prune</b> whole branches: I only have to look at the children whose "
        "label is in <font face='Courier'>[d-N, d+N]</font>.")]
    C += [h3("Union-Find")]
    C += [p(
        "If A looks like B and B like C, they must end up in the same group even if A "
        "and C do not look alike directly. Union-Find (disjoint sets) joins those "
        "chains: each element points to 'another one of its group' and following the "
        "chain leads to the representative. "
        "<font face='Courier'>groups()</font> groups by representative.")]

    C += [PageBreak(), h2("2.6. Moving files safely")]
    C += [p(
        "The use cases that move or copy "
        "(<font face='Courier'>quarantine.py</font>, "
        "<font face='Courier'>file_transfers.py</font>, "
        "<font face='Courier'>gather.py</font>) share the same rules:")]
    C += [bullet_list([
        "<b>Never overwrite.</b> Before moving, if the destination already exists I try "
        "<font face='Courier'>name (1).ext</font>, "
        "<font face='Courier'>name (2).ext</font>... "
        "(<font face='Courier'>collision_free_path</font>).",
        "<b>Preserve structure.</b> The destination of each file is "
        "<font face='Courier'>destination_folder / relpath(source, root)</font>, so the "
        "subfolder hierarchy is recreated.",
        "<b>Move, not copy-and-delete.</b> <font face='Courier'>shutil.move</font> "
        "(inside the <font face='Courier'>LocalFileSystem</font> adapter) does an atomic "
        "<font face='Courier'>rename</font> on the same drive; it only copies+deletes "
        "across drives (and there the original disappears only once the copy is safe).",
        "<b>Destination outside the source.</b> "
        "<font face='Courier'>validate_destination</font> and "
        "<font face='Courier'>validate_quarantine_folder</font> check it (otherwise the "
        "next scan would find again what was moved).",
        "<b>Everything is recorded.</b> The use case itself writes the CSV log and the "
        "history entry; the interface does not have to remember to do it.",
    ])]

    C += [h2("2.7. History and undo")]
    C += [p(
        "Every move/copy operation is recorded (through the "
        "<font face='Courier'>HistoryStore</font> port, in "
        "<font face='Courier'>%APPDATA%\\BuscadorDuplicados\\history.json</font>) with "
        "the list of (source, destination) pairs. "
        "<font face='Courier'>OperationHistory.undo(id)</font>:")]
    C += [bullet_list([
        "if it was a <b>move</b>: it returns each file to its source — but if something "
        "already exists at the source, it warns and overwrites nothing.",
        "if it was a <b>copy</b>: it deletes the copies in the destination. It is the "
        "only point in the whole code where anything is deleted, and only files the app "
        "created. The deletion retries for a moment if Windows still has the file in "
        "use.",
    ])]

    # ======================================================================
    C += [PageBreak(), h1("3. The architecture: ports, adapters and composition root")]
    C += [p(
        "The trick that keeps all of the above tidy is that the use cases do not know "
        "<i>how</i> the disk is read, a hash is computed or a JSON is saved: they ask "
        "for those things through <b>ports</b>, which are interfaces "
        "(<font face='Courier'>typing.Protocol</font>) in "
        "<font face='Courier'>application/ports.py</font>:")]
    C += [pre(
        "class FileHasher(Protocol):\n"
        "    partial_size: int\n"
        "    def partial_hash(self, path: str) -> str: ...\n"
        "    def full_hash(self, path: str) -> str: ...")]
    C += [p(
        "A use case receives its ports in the constructor and never creates anything on "
        "its own:")]
    C += [pre(
        "class ScanDuplicates:\n"
        "    def __init__(self, fs: FileSystem, hasher: FileHasher) -> None:\n"
        "        self._fs = fs\n"
        "        self._hasher = hasher")]
    C += [p(
        "The <b>adapters</b> in <font face='Courier'>infrastructure/</font> implement "
        "those ports with the real world (<font face='Courier'>Blake2Hasher</font>, "
        "<font face='Courier'>LocalFileSystem</font>...). And "
        "<font face='Courier'>bootstrap.py</font> is the <b>composition root</b>: the "
        "only module that knows every layer. It builds the adapters, injects them and "
        "gives the window a <font face='Courier'>Services</font> object with all the "
        "use cases:")]
    C += [pre(
        "def build_services() -> Services:\n"
        "    fs = LocalFileSystem()\n"
        "    history = OperationHistory(JsonHistoryStore(), fs)\n"
        "    return Services(\n"
        "        scan_duplicates=ScanDuplicates(fs, Blake2Hasher()),\n"
        "        find_similar_photos=FindSimilarPhotos(fs, PillowFingerprintReader()),\n"
        "        move_to_quarantine=MoveToQuarantine(fs, history),\n"
        "        ...)")]
    C += [h3("What it buys")]
    C += [bullet_list([
        "<b>It is tested without a disk.</b> The use-case tests pass them in-memory "
        "fakes (<font face='Courier'>tests/fakes.py</font>): a file system that is a "
        "dictionary, a hasher that uses the content. They are fast and deterministic.",
        "<b>The interface could be replaced</b> without touching the logic, because it "
        "only sees <font face='Courier'>Services</font>.",
        "<b>Everything is in its place.</b> If you need to know how a file is moved, "
        "you look at an adapter; if you need to know when, you look at a use case.",
    ])]
    C += [note(
        "Not everything has a port: only what touches the outside world (disk, hashes, "
        "images, history, settings). Pure computations (filters, similarity, selection) "
        "are plain functions in <font face='Courier'>domain/</font>; an interface there "
        "would add nothing.")]
    C += [h3("The rules, checked by a test")]
    C += [p(
        "<font face='Courier'>tests/test_architecture.py</font> reads every module with "
        "<font face='Courier'>ast</font> and fails if a layer imports something it "
        "should not (for example <font face='Courier'>domain</font> importing "
        "<font face='Courier'>tkinter</font>, or <font face='Courier'>presentation</font> "
        "importing <font face='Courier'>infrastructure</font>), if the domain or the use "
        "cases call functions that touch the disk, or if anything outside "
        "<font face='Courier'>bootstrap.py</font> builds an adapter. The test itself is "
        "checked with code snippets that break each rule.")]

    # ======================================================================
    C += [PageBreak(), h1("4. The interface, explained")]

    C += [h2("4.1. CustomTkinter and startup")]
    C += [p(
        "CustomTkinter is Tkinter with repainted widgets. "
        "<font face='Courier'>MainWindow</font> inherits from "
        "<font face='Courier'>ctk.CTk</font> and receives the "
        "<font face='Courier'>Services</font> object. "
        "<font face='Courier'>app.py</font> (or "
        "<font face='Courier'>python -m duplicate_finder</font>) calls "
        "<font face='Courier'>bootstrap.main()</font>: it starts the error log, builds "
        "the services and opens the window.")]

    C += [h2("4.2. The thread + queue + after() pattern (the most important one)")]
    C += [p(
        "Tkinter is not 'thread-safe': only the main thread can touch widgets. But "
        "scanning takes time. The solution lives in a single class, "
        "<font face='Courier'>presentation/background_job.py</font>, which every long "
        "task uses (scan, analyze, move, gather):")]
    C += [pre(
        "# main thread: launch. BackgroundJob schedules the polling with after().\n"
        "self._scan_job.start(\n"
        "    lambda report: self._services.scan_duplicates(folder, progress=report, ...),\n"
        "    what=f'Scan of {folder}')\n\n"
        "# inside BackgroundJob, worker thread: does NOT touch widgets, only the queue\n"
        "result = work(lambda value: messages.put(('progress', value)))\n"
        "messages.put(('done', result))\n\n"
        "# main thread, every 100 ms: empty the queue and notify the tab\n"
        "kind, datum = self._messages.get_nowait()\n"
        "if kind == 'progress': self._on_progress(datum)\n"
        "elif kind == 'done':   self._on_done(datum)")]
    C += [p(
        "That way the window does not freeze, progress is visible and the task can be "
        "cancelled (the thread checks a <font face='Courier'>threading.Event</font> "
        "between files). If the task fails, <font face='Courier'>BackgroundJob</font> "
        "logs the error with its traceback and notifies the tab. It is tested without a "
        "window (<font face='Courier'>tests/test_background_job.py</font>) by replacing "
        "<font face='Courier'>after</font> with a scheduler the test drives.")]

    C += [h2("4.3. The three tabs")]
    C += [p(
        "A <font face='Courier'>ctk.CTkTabview</font> with three tabs. Each one is a "
        "<b>component</b>: a class that inherits from "
        "<font face='Courier'>ctk.CTkFrame</font> and keeps its OWN state (the result, "
        "the background tasks...) instead of sharing it with the window. The window only "
        "creates them (<font face='Courier'>self.exact</font>, "
        "<font face='Courier'>self.similar</font> and "
        "<font face='Courier'>self.gather</font>) and notifies them with "
        "<font face='Courier'>apply_mode(advanced)</font> and "
        "<font face='Courier'>cancel_jobs()</font>. Every tab repeats the pattern: a top "
        "card with the folder, a progress area, a statistics panel, a gallery/table and "
        "a bottom bar with the action button. The big parts are separate components "
        "(<font face='Courier'>ScanOptionsPanel</font>, "
        "<font face='Courier'>PreviewPanel</font>), and the move questions (choosing the "
        "quarantine, warnings) are in <font face='Courier'>dialogs.py</font>.")]

    C += [h2("4.4. Texts and languages")]
    C += [p(
        "No interface text is written in the code: each one is requested with "
        "<font face='Courier'>tr('key', ...)</font>, and the texts live in one catalog "
        "per language (<font face='Courier'>i18n/locales/en.py</font> and "
        "<font face='Courier'>es.py</font>), a dictionary from keys to sentences with "
        "placeholders:")]
    C += [pre(
        "\"exact.moved_summary\": \"{moved} file(s) moved ({size}).\"            # en.py\n"
        "\"exact.moved_summary\": \"Se han movido {moved} archivo(s) ({size}).\"  # es.py\n\n"
        "label.configure(text=tr('exact.moved_summary', moved=3, size='1.2 MB'))")]
    C += [p(
        "The language is chosen at startup (the saved one, or Windows', or English), "
        "before any widget is created; that is why the header selector applies the next "
        "time. <font face='Courier'>tests/test_i18n.py</font> checks that both catalogs "
        "have the same keys and placeholders, and that every text the code asks for "
        "exists. The selectors (view, theme, strategy...) work with stable keys rather "
        "than the visible text, so changing language breaks nothing.")]

    C += [h2("4.5. Light / dark theme")]
    C += [p(
        "In <font face='Courier'>presentation/styles.py</font> each colour is a "
        "<font face='Courier'>(light, dark)</font> tuple. CustomTkinter widgets accept "
        "that tuple and change by themselves. For what is NOT CustomTkinter (the "
        "<font face='Courier'>ttk.Treeview</font> table and the viewer's "
        "<font face='Courier'>tk.Canvas</font>) I use "
        "<font face='Courier'>styles.col(tuple)</font>, which returns the colour of the "
        "active theme, and I repaint by hand by overriding "
        "<font face='Courier'>_set_appearance_mode</font>:")]
    C += [pre(
        "def _set_appearance_mode(self, mode_string):\n"
        "    super()._set_appearance_mode(mode_string)\n"
        "    self._configure_ttk_style()    # ttk does not change by itself\n"
        "    self._configure_tags()")]
    C += [p(
        "Disabled buttons turn grey (fill and text) with "
        "<font face='Courier'>styles.activate_button(btn, active)</font>, so that "
        "'disabled' is not confused with an action or error colour. The chosen theme is "
        "saved with the rest of the settings (<font face='Courier'>AppSettings</font>).")]

    C += [h2("4.6. Simple / Advanced view")]
    C += [p(
        "<font face='Courier'>_apply_mode()</font> neither creates nor destroys "
        "widgets: it removes them from and puts them back in the grid with "
        "<font face='Courier'>grid_remove()</font> / "
        "<font face='Courier'>grid()</font>. That way the state (whatever the user had "
        "typed) is kept when toggling. The choice is saved in the settings.")]

    C += [h2("4.7. The table (ttk.Treeview)")]
    C += [p(
        "For exact duplicates a <font face='Courier'>ttk.Treeview</font> is used (it "
        "copes with thousands of rows). On a click you have to ask Tk what is under the "
        "mouse:")]
    C += [pre(
        "self.tree.identify_row(event.y)      # row id\n"
        "self.tree.identify_column(event.x)   # '#1' = the 'Decision' column\n"
        "self.tree.identify_region(x, y)      # 'heading', 'cell'...")]
    C += [p(
        "With that: a normal click = select (and show the preview); a click on "
        "'Decision' = toggle keep/move; a double-click = 'keep only this one'.")]

    C += [h2("4.8. Thumbnails and images in Tkinter")]
    C += [bullet_list([
        "Decoding the image (Pillow) is done in a thread; it produces a PIL object.",
        "Converting to <font face='Courier'>ImageTk.PhotoImage</font> and putting it on "
        "the row is done in the main thread.",
        "<b>You must keep a reference</b> to each PhotoImage "
        "(<font face='Courier'>self._img_refs[iid] = photo</font>). Otherwise Python "
        "collects it and the image vanishes from the screen.",
    ])]

    # ======================================================================
    C += [PageBreak(), h1("5. Packaging")]
    C += [p(
        "<font face='Courier'>build.spec</font> configures PyInstaller: a single file, "
        "no console, with the CustomTkinter data included and "
        "<font face='Courier'>icon.ico</font> as the icon (the code lives in "
        "<font face='Courier'>src/</font>, which is added to the search path). "
        "<font face='Courier'>build_exe.py</font> runs it and checks the result.")]
    C += [p(
        "The icon is a magnifying glass <b>drawn by code</b> "
        "(<font face='Courier'>presentation/icons.py:window_icon</font>) on a "
        "<font face='Courier'>tk.PhotoImage</font>, and "
        "<font face='Courier'>gen_icon.py</font> assembles the multi-size "
        "<font face='Courier'>.ico</font> by hand with "
        "<font face='Courier'>struct</font>. No external images.")]

    # ======================================================================
    C += [h1("6. How it is tested")]
    C += [p(
        "There are several levels. The behaviour tests on files use no <i>mocks</i>: "
        "each one creates real files in a temporary folder "
        "(<font face='Courier'>tempfile.TemporaryDirectory</font>), runs the function for "
        "real and checks the state on disk. The use-case tests "
        "(<font face='Courier'>tests/test_use_cases.py</font>) use the in-memory fakes of "
        "<font face='Courier'>tests/fakes.py</font>. The interface tests build the whole "
        "window, simulate the dialogs (<font face='Courier'>filedialog</font> and "
        "<font face='Courier'>messagebox</font> are replaced by functions that return a "
        "fixed value) and press the buttons' methods. There are also tests for the "
        "architecture, for the language catalogs and for the migration of the data of "
        "version 1.0.")]
    C += [pre(
        "pytest                    # everything\n"
        "pytest -m \"not gui\"       # logic only, no windows\n"
        "pytest --cov              # with coverage (CI requires 90 % logic, 70 % interface)\n"
        "python tests/check_perceptual.py \"D:\\Photos\" 10   # with real data")]

    C += [h1("7. Adding a new feature: a recipe")]
    C += [bullet_list([
        "<b>1.</b> Write the pure rule in <font face='Courier'>domain/</font> and the use "
        "case in <font face='Courier'>application/</font> (one class, with the ports it "
        "needs in the constructor). If it needs something from the outside world that "
        "does not exist yet, add a port and its adapter in "
        "<font face='Courier'>infrastructure/</font>.",
        "<b>2.</b> Wire it in <font face='Courier'>bootstrap.py</font> and add it to "
        "<font face='Courier'>Services</font>.",
        "<b>3.</b> Add tests: of the use case with in-memory fakes and, if it touches "
        "real files, with temporary folders.",
        "<b>4.</b> In <font face='Courier'>presentation/</font>, add the widgets and a "
        "handler that calls the use case. If the task is long, launch it with "
        "<font face='Courier'>BackgroundJob</font>. Every new text goes into both "
        "catalogs with <font face='Courier'>tr()</font>.",
        "<b>5.</b> If it moves or copies files, make it go through "
        "<font face='Courier'>FileTransfers</font> and record it in the history so it "
        "can be undone.",
        "<b>6.</b> Run <font face='Courier'>pytest</font>, "
        "<font face='Courier'>ruff check .</font> and "
        "<font face='Courier'>python -m mypy</font>. All green before considering "
        "anything done: including the architecture test, which warns you if you put "
        "something in the wrong layer.",
    ])]

    return C
