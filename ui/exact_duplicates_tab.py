""""Exact duplicates" tab: scans a folder and decides which copy to keep.

It is a component with its OWN state (scan result, selection, queues, threads...):
the main window only creates it, notifies it of the Simple / Advanced mode and that it is closing.
"""

import datetime
import os
import queue
import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk

from core.scanner import scan, ScanCancelled
from core.report import export_csv
from core.hashing import format_size
from core.app_logging import log
from core.filters import (
    ScanFilter, parse_extensions, parse_names, set_to_text,
    JUNK_EXTENSIONS, JUNK_NAMES, JUNK_FOLDERS, CATEGORY_EXTENSIONS,
)
from core.selection import DuplicateSelection
from core.quarantine import (
    move_to_quarantine, validate_quarantine_folder, InvalidQuarantine,
)
from core import history
from core.file_moves import MOVE as MOVE_ACTION
from . import styles
from . import icons
from .widgets import SectionHeader, StatTile, EmptyState, make_card
from .results_table import ResultsTable
from .thumbnails import (
    large_preview, clear_cache, IMAGE_EXT,
)
from .image_viewer import open_viewer, can_be_displayed
from .extension_breakdown_dialog import ExtensionBreakdownWindow


class ExactDuplicatesTab(ctk.CTkFrame):
    def __init__(self, container, advanced):
        """`container` is the CTkTabview tab where this component is placed;
        `advanced` is the mode the window starts with."""
        super().__init__(container, fg_color="transparent")
        container.grid_columnconfigure(0, weight=1)    # the component fills the whole tab
        container.grid_rowconfigure(0, weight=1)
        self.grid(row=0, column=0, sticky="nsew")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(6, weight=1)

        self._advanced = advanced
        self._queue = queue.Queue()            # messages from the thread that scans
        self._thread = None
        self._cancel_event = threading.Event()
        self._result = None
        self._selection = None
        self._scanned_folder = None
        self._quarantine_queue = queue.Queue()       # messages from the quarantine thread
        self._excl_text = ""

        self._build_scan_card()
        self._build_scan_options()
        self._build_progress_area()
        self._build_decision_card()
        self._build_stats()
        self._build_table()
        self._build_bottom_bar()
        self._set_initial_state()

    # ------------------------------------------------------------------
    # What the main window asks of it
    # ------------------------------------------------------------------
    def apply_mode(self, advanced):
        """Shows or hides the "advanced" controls (without deleting widgets, so the
        state is kept when toggling)."""
        self._advanced = advanced
        # In Simple mode these are hidden: the options panel, the "preferred
        # folder" row, "View kinds" and "Export CSV".
        for w in (self._options_container, self.decision_card_header,
                  self.decision_card_row, self.btn_kinds, self.btn_export):
            (w.grid if advanced else w.grid_remove)()
        if not advanced and self._options_open.get():
            self._toggle_options()       # collapse the panel if it was open

    def on_switch_to_simple(self):
        """If there are already results and the user goes back to Simple,
        the app decides by itself again."""
        if self._selection is not None:
            self._selection.preselect_primary()
            self.table.refresh_all()
            self._on_selection_change()

    def cancel_jobs(self):
        """Called by the window when it closes: if a scan is running, it is cancelled."""
        if self._thread and self._thread.is_alive():
            self._cancel_event.set()

    def _build_scan_card(self):
        card = make_card(self, 1)
        SectionHeader(card, 1, "Elige la carpeta que quieres revisar",
                        icons.FOLDER).grid(
            row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 16))
        row.grid_columnconfigure(0, weight=1)

        self.entry_folder = ctk.CTkEntry(
            row, height=36, placeholder_text=r"Ej.  D:\Fotos")
        self.entry_folder.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.btn_choose = ctk.CTkButton(
            row, text=f"{icons.FOLDER}  Elegir", width=110, height=36,
            command=self._choose_folder)
        self.btn_choose.grid(row=0, column=1, padx=4)
        self.btn_scan = ctk.CTkButton(
            row, text=f"{icons.SEARCH}  Escanear", width=130, height=36,
            font=styles.base_font(13, "bold"), command=self._start_scan)
        self.btn_scan.grid(row=0, column=2, padx=(4, 0))

    def _build_scan_options(self):
        cont = ctk.CTkFrame(self, fg_color="transparent")
        cont.grid(row=2, column=0, sticky="ew", padx=6, pady=(6, 0))
        cont.grid_columnconfigure(0, weight=1)
        self._options_container = cont

        self._options_open = ctk.BooleanVar(value=False)
        self.btn_toggle_options = ctk.CTkButton(
            cont, text=f"{icons.TRI_RIGHT}  {icons.GEAR}  Opciones de escaneo "
                       f"(filtrar por tipo de archivo)",
            anchor="w", fg_color="transparent", hover=False,
            text_color=styles.COLOR_MUTED_TEXT, command=self._toggle_options)
        self.btn_toggle_options.grid(row=0, column=0, sticky="ew")

        self.options_panel = ctk.CTkFrame(cont, fg_color=styles.COLOR_CARD)
        self.options_panel.grid(row=1, column=0, sticky="ew", pady=(2, 0))
        self.options_panel.grid_columnconfigure(1, weight=1)
        self.options_panel.grid_remove()
        p = self.options_panel

        # --- Search only these kinds (whitelist) ------------------
        ctk.CTkLabel(p, text="Buscar solo estos tipos de archivo:",
                     font=styles.base_font(12, "bold")).grid(
            row=0, column=0, columnspan=3, padx=16, pady=(12, 4), sticky="w")

        chips = ctk.CTkFrame(p, fg_color="transparent")
        chips.grid(row=1, column=0, columnspan=3, padx=14, pady=(0, 4), sticky="w")
        self.chk_categories = {}
        for name in CATEGORY_EXTENSIONS:
            chk = ctk.CTkCheckBox(
                chips, text=f"{icons.CATEGORY_ICON[name]}  {name}",
                font=styles.base_font(12),
                command=lambda n=name: self._toggle_category(n))
            chk.pack(side="left", padx=(2, 12), pady=4)
            self.chk_categories[name] = chk

        ctk.CTkLabel(p, text="Extensiones:", font=styles.base_font(12)).grid(
            row=2, column=0, padx=(16, 8), pady=4, sticky="w")
        self.entry_include = ctk.CTkEntry(
            p, height=32, placeholder_text="vacío = se buscan todos los tipos")
        self.entry_include.grid(row=2, column=1, columnspan=2, padx=(4, 16),
                                pady=4, sticky="ew")
        self.entry_include.bind("<KeyRelease>", self._sync_categories)

        ctk.CTkLabel(
            p, text="Marca una categoría o escribe extensiones a mano. "
                    "Si lo dejas vacío se buscan duplicados de cualquier tipo.",
            font=styles.base_font(11), text_color=styles.COLOR_MUTED_TEXT,
        ).grid(row=3, column=0, columnspan=3, padx=16, pady=(0, 10), sticky="w")

        ctk.CTkFrame(p, height=1, fg_color=styles.COLOR_ALTERNATE_ROW).grid(
            row=4, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 8))

        # --- Ignore (blacklist) ------------------------------------
        ctk.CTkLabel(p, text="Ignorar además:",
                     font=styles.base_font(12, "bold")).grid(
            row=5, column=0, columnspan=3, padx=16, pady=(0, 4), sticky="w")

        def field(row, label):
            ctk.CTkLabel(p, text=label, font=styles.base_font(12)).grid(
                row=row, column=0, padx=(16, 8), pady=4, sticky="w")
            e = ctk.CTkEntry(p, height=32)
            e.grid(row=row, column=1, columnspan=2, padx=(4, 16), pady=4,
                   sticky="ew")
            return e

        self.entry_ext = field(6, "Extensiones:")
        self.entry_folders = field(7, "Carpetas:")
        self.entry_names = field(8, "Nombres:")

        self.chk_empty = ctk.CTkCheckBox(
            p, text="Ignorar archivos de 0 bytes", font=styles.base_font(12))
        self.chk_empty.grid(row=9, column=0, columnspan=2, padx=16,
                             pady=(6, 4), sticky="w")

        buttons = ctk.CTkFrame(p, fg_color="transparent")
        buttons.grid(row=9, column=2, padx=12, pady=(6, 4), sticky="e")
        ctk.CTkButton(buttons, text="Valores por defecto", width=140,
                      fg_color="transparent", border_width=1,
                      text_color=styles.COLOR_TEXT,
                      command=self._default_filters).pack(side="left", padx=4)
        ctk.CTkButton(buttons, text="Quitar todo", width=90,
                      fg_color="transparent", border_width=1,
                      text_color=styles.COLOR_TEXT,
                      command=self._empty_filters).pack(side="left", padx=4)

        ctk.CTkLabel(
            p, text="Separa los valores con espacios o comas.",
            font=styles.base_font(11), text_color=styles.COLOR_MUTED_TEXT,
        ).grid(row=10, column=0, columnspan=3, padx=16, pady=(0, 12), sticky="w")

        self._default_filters()

    def _build_progress_area(self):
        self.progress_area = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_area.grid(row=3, column=0, sticky="ew", padx=16, pady=(8, 0))
        self.progress_area.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(self.progress_area, height=10)
        self.progress_bar.grid(row=0, column=0, sticky="ew", pady=(4, 2))
        self.progress_bar.set(0)
        self.lbl_state = ctk.CTkLabel(
            self.progress_area, text="", font=styles.base_font(12),
            text_color=styles.COLOR_MUTED_TEXT, anchor="w")
        self.lbl_state.grid(row=1, column=0, sticky="ew")

    def _build_decision_card(self):
        card = make_card(self, 4)
        self.decision_card = card
        self.decision_card_header = SectionHeader(
            card, 2, "Decide qué copia conservar en cada grupo", icons.STAR)
        self.decision_card_header.grid(row=0, column=0, sticky="w",
                                       padx=16, pady=(14, 8))

        row = ctk.CTkFrame(card, fg_color="transparent")
        self.decision_card_row = row
        row.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 6))
        row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(row, text="Carpeta preferida:",
                     font=styles.base_font(12)).grid(
            row=0, column=0, padx=(0, 8), pady=6, sticky="w")
        self.entry_preferred_folder = ctk.CTkEntry(
            row, height=34,
            placeholder_text=r"Las copias dentro de esta carpeta se conservan.  "
                             r"Ej.  D:\Fotos\Organizado")
        self.entry_preferred_folder.grid(row=0, column=1, padx=4, pady=6, sticky="ew")
        self.btn_choose_preferred = ctk.CTkButton(
            row, text=f"{icons.FOLDER}  Elegir", width=100, height=34,
            command=self._choose_preferred_folder)
        self.btn_choose_preferred.grid(row=0, column=2, padx=4, pady=6)
        self.btn_rule = ctk.CTkButton(
            row, text=f"{icons.AUTO}  Regla por carpeta", width=170,
            height=34, command=self._apply_rule)
        self.btn_rule.grid(row=0, column=3, padx=4, pady=6)
        self.btn_primary = ctk.CTkButton(
            row, text=f"{icons.OK}  Elegir la principal", width=170,
            height=34, fg_color="transparent", border_width=1,
            command=self._choose_primary)
        self.btn_primary.grid(row=0, column=4, padx=(4, 0), pady=6)

        self.lbl_validation = ctk.CTkLabel(
            card, text="", font=styles.base_font(12), anchor="w",
            justify="left", wraplength=1000)
        self.lbl_validation.grid(row=2, column=0, sticky="w",
                                 padx=16, pady=(2, 14))

    def _build_stats(self):
        self.stats_row = ctk.CTkFrame(self, fg_color="transparent")
        self.stats_row.grid(row=5, column=0, sticky="ew", padx=6, pady=(8, 0))
        for i in range(4):
            self.stats_row.grid_columnconfigure(i, weight=1)

        self.stat_groups = StatTile(self.stats_row, "Grupos de duplicados")
        self.stat_duplicates = StatTile(self.stats_row, "Archivos duplicados")
        self.stat_move = StatTile(self.stats_row, "Archivos a mover")
        self.stat_space = StatTile(self.stats_row, "Espacio recuperable")
        for i, b in enumerate((self.stat_groups, self.stat_duplicates,
                               self.stat_move, self.stat_space)):
            b.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 6, 0))

    def _build_table(self):
        self.table_wrap = ctk.CTkFrame(self, fg_color="transparent")
        self.table_wrap.grid(row=6, column=0, sticky="nsew", padx=6, pady=(8, 0))
        self.table_wrap.grid_rowconfigure(0, weight=1)
        self.table_wrap.grid_columnconfigure(0, weight=1)

        # Left container: table + empty state (same spot).
        self.table_area = ctk.CTkFrame(self.table_wrap, fg_color="transparent")
        self.table_area.grid(row=0, column=0, sticky="nsew")
        self.table_area.grid_rowconfigure(0, weight=1)
        self.table_area.grid_columnconfigure(0, weight=1)

        self.table = ResultsTable(
            self.table_area, on_change=self._on_selection_change,
            on_selection=self._preview_file)
        self.table.grid(row=0, column=0, sticky="nsew")

        self.empty_state = EmptyState(
            self.table_area, icons.SEARCH,
            "Todavía no hay resultados",
            "Elige una carpeta arriba y pulsa «Escanear». "
            "Los grupos de archivos duplicados aparecerán aquí.")
        self.empty_state.grid(row=0, column=0, sticky="nsew")

        # Preview panel on the right.
        self.panel_preview = ctk.CTkFrame(
            self.table_wrap, fg_color=styles.COLOR_CARD, width=290)
        self.panel_preview.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self.panel_preview.grid_propagate(False)
        self.panel_preview.grid_columnconfigure(0, weight=1)
        self.panel_preview.grid_rowconfigure(0, weight=1)

        self._preview_path = None
        self.preview_img = ctk.CTkLabel(
            self.panel_preview,
            text="Selecciona un archivo\npara ver la vista previa",
            font=styles.base_font(12), text_color=styles.COLOR_MUTED_TEXT)
        self.preview_img.grid(row=0, column=0, padx=12, pady=12)
        self.preview_img.bind("<Button-1>", lambda _e: self._open_viewer())
        self.preview_name = ctk.CTkLabel(
            self.panel_preview, text="", font=styles.base_font(12, "bold"),
            wraplength=262, justify="left", anchor="w")
        self.preview_name.grid(row=1, column=0, padx=12, pady=(0, 2), sticky="w")
        self.preview_meta = ctk.CTkLabel(
            self.panel_preview, text="", font=styles.base_font(11),
            text_color=styles.COLOR_MUTED_TEXT, wraplength=262,
            justify="left", anchor="w")
        self.preview_meta.grid(row=2, column=0, padx=12, pady=(0, 4), sticky="w")
        self.preview_zoom_in = ctk.CTkLabel(
            self.panel_preview, text="", font=styles.base_font(11),
            text_color=styles.COLOR_ACCENT, anchor="w")
        self.preview_zoom_in.grid(row=3, column=0, padx=12, pady=(0, 12), sticky="w")
        self.preview_zoom_in.bind("<Button-1>", lambda _e: self._open_viewer())

    def _build_bottom_bar(self):
        bar = ctk.CTkFrame(self, fg_color=styles.COLOR_CARD)
        bar.grid(row=7, column=0, sticky="ew", padx=6, pady=(12, 6))
        bar.grid_columnconfigure(0, weight=1)

        self.lbl_totals = ctk.CTkLabel(
            bar, text="Sin escanear todavía.", font=styles.base_font(12),
            text_color=styles.COLOR_MUTED_TEXT, anchor="w")
        self.lbl_totals.grid(row=0, column=0, padx=16, pady=12, sticky="w")

        self.btn_kinds = ctk.CTkButton(
            bar, text=f"{icons.CHART}  Ver tipos de archivo", width=180,
            height=36, fg_color="transparent", border_width=1,
            text_color=styles.COLOR_TEXT,
            command=self._show_kinds)
        self.btn_kinds.grid(row=0, column=1, padx=4, pady=12)
        self.btn_export = ctk.CTkButton(
            bar, text=f"{icons.SAVE}  Exportar CSV", width=150, height=36,
            fg_color="transparent", border_width=1, text_color=styles.COLOR_TEXT,
            command=self._export_csv)
        self.btn_export.grid(row=0, column=2, padx=4, pady=12)
        self.btn_quarantine = ctk.CTkButton(
            bar, text=f"{icons.SHIELD}  Mover a cuarentena", width=200,
            height=36, font=styles.base_font(13, "bold"),
            fg_color=styles.COLOR_OK_BUTTON, hover_color="#26734d",
            command=self._move_to_quarantine)
        self.btn_quarantine.grid(row=0, column=3, padx=(4, 16), pady=12)

    def _toggle_options(self):
        open = not self._options_open.get()
        self._options_open.set(open)
        tri = icons.TRI_DOWN if open else icons.TRI_RIGHT
        self.btn_toggle_options.configure(
            text=f"{tri}  {icons.GEAR}  Opciones de escaneo "
                 f"(filtrar por tipo de archivo)")
        if open:
            self.options_panel.grid()
        else:
            self.options_panel.grid_remove()

    def _toggle_category(self, name):
        """Ticks/unticks the extensions of a category in the field."""
        current_set = parse_extensions(self.entry_include.get())
        exts = CATEGORY_EXTENSIONS[name]
        if self.chk_categories[name].get():
            current_set |= exts
        else:
            current_set -= exts
        self.entry_include.delete(0, "end")
        self.entry_include.insert(0, set_to_text(current_set))

    def _sync_categories(self, _event=None):
        """After editing the field by hand, leaves ticked only the categories
        whose extensions are all present."""
        present = parse_extensions(self.entry_include.get())
        for name, chk in self.chk_categories.items():
            complete = CATEGORY_EXTENSIONS[name] <= present
            if complete and not chk.get():
                chk.select()
            elif not complete and chk.get():
                chk.deselect()

    def _default_filters(self):
        for entry, values in (
            (self.entry_ext, JUNK_EXTENSIONS),
            (self.entry_folders, JUNK_FOLDERS),
            (self.entry_names, JUNK_NAMES),
        ):
            entry.delete(0, "end")
            entry.insert(0, "  ".join(values))
        self.chk_empty.select()
        self.entry_include.delete(0, "end")
        for chk in self.chk_categories.values():
            chk.deselect()

    def _empty_filters(self):
        for entry in (self.entry_include, self.entry_ext,
                      self.entry_folders, self.entry_names):
            entry.delete(0, "end")
        self.chk_empty.deselect()
        for chk in self.chk_categories.values():
            chk.deselect()

    def _current_filter(self):
        return ScanFilter(
            included_extensions=parse_extensions(self.entry_include.get()),
            excluded_extensions=parse_extensions(self.entry_ext.get()),
            excluded_names=parse_names(self.entry_names.get()),
            excluded_folders=parse_names(self.entry_folders.get()),
            min_size=1 if self.chk_empty.get() else 0,
        )

    def _add_extension_to_filter(self, ext):
        current_set = parse_extensions(self.entry_ext.get())
        current_set.add(ext.lower().lstrip("."))
        self.entry_ext.delete(0, "end")
        self.entry_ext.insert(0, set_to_text(current_set))
        if not self._options_open.get():
            self._toggle_options()

    def _set_initial_state(self):
        self.progress_bar.set(0)
        self.lbl_state.configure(text="")
        self.progress_area.grid_remove()
        self.stats_row.grid_remove()
        self._enable_actions(False)
        self._enable_decision(False)
        self.lbl_validation.configure(text="")
        self.empty_state.tkraise()

    def _enable_actions(self, active):
        # "View kinds" and "Export CSV" are "secondary" buttons (with a border).
        for btn in (self.btn_kinds, self.btn_export):
            styles.activate_button(btn, active, fg="transparent",
                                 hover=styles.COLOR_TILE)

    def _enable_decision(self, active):
        state = "normal" if active else "disabled"
        self.entry_preferred_folder.configure(state=state)
        styles.activate_button(self.btn_choose_preferred, active)   # primary button (blue)
        styles.activate_button(self.btn_rule, active)          # primary button (blue)
        styles.activate_button(self.btn_primary, active,      # secondary button (border)
                             fg="transparent", hover=styles.COLOR_TILE)
        styles.action_button(self.btn_quarantine, active)

    def _choose_primary(self):
        if self._selection is None:
            return
        self._selection.preselect_primary()
        self.table.refresh_all()
        self._on_selection_change()

    def _set_scanning(self, scanning):
        # While scanning: "Choose" and the folder field are switched off,
        # and "Scan" turns into "Cancel" (red).
        styles.activate_button(self.btn_choose, not scanning)
        self.entry_folder.configure(state="disabled" if scanning else "normal")
        if scanning:
            self.btn_scan.configure(
                text=f"{icons.CROSS}  Cancelar", command=self._cancel_scan,
                state="normal",
                fg_color=styles.COLOR_DANGER_BUTTON,
                hover_color=("#9c2f24", "#8f2b22"),
                text_color="#ffffff")
        else:
            styles.activate_button(self.btn_scan, True)
            self.btn_scan.configure(
                text=f"{icons.SEARCH}  Escanear", command=self._start_scan)

    def _choose_folder(self):
        folder = filedialog.askdirectory(title="Elige la carpeta a escanear")
        if folder:
            self.entry_folder.delete(0, "end")
            self.entry_folder.insert(0, os.path.normpath(folder))

    def _choose_preferred_folder(self):
        folder = filedialog.askdirectory(title="Elige la carpeta preferida")
        if folder:
            self.entry_preferred_folder.delete(0, "end")
            self.entry_preferred_folder.insert(0, os.path.normpath(folder))

    def _start_scan(self):
        folder = self.entry_folder.get().strip()
        if not folder:
            messagebox.showwarning("Falta la carpeta",
                                   "Elige primero una carpeta para escanear.")
            return
        if not os.path.isdir(folder):
            messagebox.showerror(
                "Carpeta no válida",
                f"La ruta no existe o no es una carpeta:\n\n{folder}")
            return

        filter = self._current_filter()

        self.table.clear()
        self._result = None
        self._selection = None
        self._scanned_folder = folder
        self._cancel_event.clear()
        clear_cache()
        self.progress_area.grid()
        self.progress_bar.set(0)
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start()
        self.lbl_state.configure(text="Preparando el escaneo…")
        self.lbl_totals.configure(text="Escaneando…")
        self.lbl_validation.configure(text="")
        self.stats_row.grid_remove()
        self.empty_state.configure(
            title="Escaneando…", detail="Buscando archivos duplicados.")
        self.empty_state.tkraise()
        self._enable_actions(False)
        self._enable_decision(False)
        self._set_scanning(True)

        # --- thread + queue + after() PATTERN (repeated throughout the app) ---
        # Tkinter is not thread-safe: only the main thread can touch
        # widgets. So:
        # · the heavy work (scanning) runs in a separate thread,
        # · that thread does NOT touch the interface: it only puts messages in a queue,
        # · the interface calls _poll_queue() every 100 ms, takes out the
        # messages and updates the widgets from the main thread.
        # This way the window does not freeze and the scan can be cancelled halfway.
        self._thread = threading.Thread(target=self._scan_job,
                                      args=(folder, filter), daemon=True)
        self._thread.start()
        self.after(100, self._poll_queue)

    def _cancel_scan(self):
        # The thread checks this event between one file and the next.
        self._cancel_event.set()
        self.lbl_state.configure(text="Cancelando…")
        self.btn_scan.configure(state="disabled")

    def _scan_job(self, folder, filter):
        """Runs in the SECONDARY THREAD. It does not touch a single widget: everything goes through
        the queue as tuples (kind, data)."""
        try:
            result = scan(
                folder,
                progress=lambda p: self._queue.put(("progress", p)),
                cancelled=self._cancel_event.is_set,
                filter=filter,
            )
            self._queue.put(("done", result))
        except ScanCancelled:
            self._queue.put(("cancelled", None))
        except Exception as e:  # any failure is logged and shown
            log.exception("Falló el escaneo de %s", folder)
            self._queue.put(("error", e))

    def _poll_queue(self):
        """Runs in the MAIN THREAD. Empties the queue and acts according to the type
        of message. It reschedules itself until "done",
        "cancelled" or "error" arrives."""
        try:
            while True:
                kind, datum = self._queue.get_nowait()   # raises queue.Empty if there is none
                if kind == "progress":
                    self._apply_progress(datum)
                elif kind == "done":
                    self._finish_scan(datum)
                    return
                elif kind == "cancelled":
                    self._scan_cancelled()
                    return
                elif kind == "error":
                    self._scan_failed(datum)
                    return
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)          # keep polling

    def _apply_progress(self, p):
        self.lbl_state.configure(text=p.message)
        if p.total > 0:
            if self.progress_bar.cget("mode") != "determinate":
                self.progress_bar.stop()
                self.progress_bar.configure(mode="determinate")
            self.progress_bar.set(min(p.current / p.total, 1.0))

    def _finish_scan(self, result):
        self._result = result
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(1.0)
        self._set_scanning(False)
        self.btn_scan.configure(state="normal")

        self._excl_text = (
            f"  ·  {result.total_excluded} ignorados por filtro"
            if result.total_excluded else "")

        if result.total_groups == 0:
            self.stats_row.grid_remove()
            self.lbl_state.configure(text="No se han encontrado duplicados.")
            self.lbl_totals.configure(
                text=f"{result.total_files} archivos revisados"
                     f"{self._excl_text} · 0 duplicados.")
            self._enable_actions(False)
            self._enable_decision(False)
            self.lbl_validation.configure(text="")
            self.empty_state.configure(
                title="No se han encontrado duplicados",
                detail=f"Se han revisado {result.total_files} archivos y "
                        f"todos son únicos.")
            self.empty_state.tkraise()
            return

        self._selection = DuplicateSelection(result)
        if not self._advanced:
            self._selection.preselect_primary()
        self.table.load(self._selection)
        self.table.tkraise()
        self.stats_row.grid()
        self.stat_groups.set(result.total_groups)
        self.stat_duplicates.set(result.total_files_duplicates)
        self.lbl_state.configure(
            text="Escaneo terminado."
            + (f"  {len(result.errors)} archivo(s) no se pudieron leer."
               if result.errors else ""))
        self._enable_actions(True)
        self._enable_decision(True)
        self._on_selection_change()

    def _scan_cancelled(self):
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(0)
        self.lbl_state.configure(text="Escaneo cancelado.")
        self.lbl_totals.configure(text="Escaneo cancelado.")
        self._set_scanning(False)
        self.btn_scan.configure(state="normal")
        self.empty_state.configure(
            title="Escaneo cancelado",
            detail="Pulsa «Escanear» para intentarlo de nuevo.")
        self.empty_state.tkraise()

    def _scan_failed(self, e):
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(0)
        self.lbl_state.configure(text="El escaneo ha fallado.")
        self.lbl_totals.configure(text="El escaneo ha fallado.")
        self._set_scanning(False)
        self.btn_scan.configure(state="normal")
        messagebox.showerror("Error durante el escaneo",
                             f"Ha ocurrido un problema:\n\n{type(e).__name__}: {e}")

    def _apply_rule(self):
        if self._selection is None:
            return
        preferred_folder = self.entry_preferred_folder.get().strip()
        if not preferred_folder:
            messagebox.showinfo(
                "Falta la carpeta preferida",
                "Escribe o elige antes una carpeta preferida.")
            return
        if not os.path.isdir(preferred_folder):
            if not messagebox.askyesno(
                "La carpeta no existe",
                f"La carpeta preferida no existe ahora mismo:\n\n{preferred_folder}\n\n"
                "¿Quieres aplicar la regla igualmente? (los grupos sin coincidencia "
                "quedarán sin decidir)"):
                return

        resolved, no_match = self._selection.apply_folder_rule(
            preferred_folder)
        self.table.refresh_all()
        self._on_selection_change()

        msg = f"Regla aplicada: {resolved} grupo(s) resueltos automáticamente."
        if no_match:
            msg += (f"\n{no_match} grupo(s) no tienen ninguna copia dentro "
                    "de la carpeta preferida: han quedado resaltados para que elijas "
                    "manualmente (un clic sobre la copia que quieres conservar, o "
                    "doble clic para conservar solo esa).")
            self.table.go_to_pending()
        messagebox.showinfo("Regla automática", msg)

    def _on_selection_change(self):
        if self._selection is None:
            return
        r = self._result
        pending = self._selection.pending_groups()
        to_move = self._selection.count_to_move()
        free = self._selection.space_to_free()

        self.stat_move.set(to_move)
        self.stat_space.set(format_size(free),
                              color=styles.COLOR_OK if free else None)
        self.lbl_totals.configure(
            text=f"{r.total_groups} grupos · {r.total_files_duplicates} "
                 f"archivos duplicados{self._excl_text}")

        if not pending:
            if not self._advanced:
                text = (f"{icons.OK}  La app conservará la copia principal de "
                         f"cada grupo. Doble clic en una fila para conservar "
                         f"otra. Cuando quieras, pulsa «Mover a cuarentena».")
            else:
                text = (f"{icons.OK}  Todos los grupos tienen una sola copia "
                         f"marcada para conservar. Ya puedes mover a cuarentena.")
            self.lbl_validation.configure(text=text, text_color=styles.COLOR_OK)
            styles.action_button(self.btn_quarantine, True)
        else:
            self.lbl_validation.configure(
                text=f"{icons.WARNING}  {len(pending)} grupo(s) sin resolver "
                     f"(resaltados en la tabla). Marca una sola copia para "
                     f"conservar en cada uno. El botón «Mover a cuarentena» "
                     f"está bloqueado.",
                text_color=styles.COLOR_WARNING)
            styles.action_button(self.btn_quarantine, False)

    def _move_to_quarantine(self):
        if self._selection is None or not self._selection.all_ready():
            return

        root = self._scanned_folder
        quarantine_folder = filedialog.askdirectory(
            title="Elige (o crea) la carpeta de cuarentena", mustexist=False)
        if not quarantine_folder:
            return
        quarantine_folder = os.path.normpath(quarantine_folder)

        try:
            warning = validate_quarantine_folder(quarantine_folder, root)
        except InvalidQuarantine as e:
            messagebox.showerror("Carpeta de cuarentena no válida", str(e))
            return
        if warning and not messagebox.askyesno("Atención", warning + "\n\n¿Continuar?"):
            return

        n = self._selection.count_to_move()
        frees = format_size(self._selection.space_to_free())
        if not messagebox.askyesno(
            "Confirmar movimiento a cuarentena",
            f"Se van a MOVER {n} archivo(s) ({frees}) a:\n\n{quarantine_folder}\n\n"
            "Los originales que has marcado para conservar NO se tocan. No se "
            "borra nada: todo queda en la cuarentena para que lo revises y lo "
            "borres tú manualmente cuando quieras.\n\n¿Mover ahora?"):
            return

        self._set_quarantine_busy(True)
        self.lbl_state.configure(text="Moviendo a cuarentena…")
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(0)

        thread = threading.Thread(
            target=self._quarantine_job,
            args=(self._selection, root, quarantine_folder), daemon=True)
        thread.start()
        self.after(100, self._poll_quarantine_queue)

    def _set_quarantine_busy(self, busy):
        active = not busy
        for btn in (self.btn_scan, self.btn_rule, self.btn_choose,
                    self.btn_choose_preferred):
            styles.activate_button(btn, active)
        for btn in (self.btn_export, self.btn_kinds):
            styles.activate_button(btn, active, fg="transparent",
                                 hover=styles.COLOR_TILE)
        styles.action_button(self.btn_quarantine, active)

    def _quarantine_job(self, selection, root, quarantine_folder):
        try:
            res = move_to_quarantine(
                selection, root, quarantine_folder,
                progress=lambda a, t, m: self._quarantine_queue.put(("progress", (a, t, m))))
            self._quarantine_queue.put(("done", (res, quarantine_folder)))
        except Exception as e:  # it is logged and shown to the user
            log.exception("Falló el movimiento a cuarentena (origen %s, destino %s)",
                          root, quarantine_folder)
            self._quarantine_queue.put(("error", e))

    def _poll_quarantine_queue(self):
        try:
            while True:
                kind, datum = self._quarantine_queue.get_nowait()
                if kind == "progress":
                    current, total, msg = datum
                    self.lbl_state.configure(text=msg)
                    if total:
                        self.progress_bar.set(min(current / total, 1.0))
                elif kind == "done":
                    self._quarantine_finished(*datum)
                    return
                elif kind == "error":
                    self._set_quarantine_busy(False)
                    self.lbl_state.configure(text="El movimiento ha fallado.")
                    messagebox.showerror(
                        "Error al mover", f"{type(datum).__name__}: {datum}")
                    return
        except queue.Empty:
            pass
        self.after(100, self._poll_quarantine_queue)

    def _quarantine_finished(self, res, quarantine_folder):
        self._set_quarantine_busy(False)
        self.progress_bar.set(1.0)
        self.lbl_state.configure(text="Movimiento a cuarentena terminado.")

        if res.moved:
            history.record(
                history.KIND_QUARANTINE, MOVE_ACTION, self._scanned_folder,
                quarantine_folder, [(m.source, m.destination) for m in res.moved],
                f"{len(res.moved)} duplicados exactos")

        moved = len(res.moved)
        failed = len(res.failed)
        detail = (f"Se han movido {moved} archivo(s) "
                   f"({format_size(res.bytes_moved)}).")
        if failed:
            detail += (f"\n{failed} no se han podido mover "
                        f"(consulta el CSV de registro).")
        if res.log_path:
            detail += f"\n\nRegistro: {res.log_path}"

        self.table.clear()
        self._selection = None
        self._result = None
        self._enable_decision(False)
        self._enable_actions(False)
        self.lbl_validation.configure(text="")
        self.stats_row.grid_remove()
        self.lbl_totals.configure(
            text=f"{moved} archivo(s) movidos a cuarentena. "
                 f"Vuelve a escanear si quieres continuar.")
        self.empty_state.configure(
            title="Archivos movidos a cuarentena",
            detail=detail.split("\n\n")[0] + " Vuelve a escanear para continuar.")
        self.empty_state.tkraise()

        if messagebox.askyesno(
            "Hecho", detail + "\n\n¿Quieres abrir la carpeta de cuarentena?"):
            try:
                os.startfile(quarantine_folder)  # noqa: S606 (Windows)
            except OSError:
                pass

    def _open_viewer(self, path=None):
        open_viewer(self.winfo_toplevel(), path or self._preview_path)

    def _clear_preview_image(self):
        """Clears the image of the preview panel.

        CTkLabel.configure(image=None) does NOT remove the image that was already being
        shown (a known CustomTkinter 5.2.2 bug), so the tkinter
        Label inside is cleared instead.
        """
        self.preview_img.configure(image=None)
        self.preview_img._label.configure(image="")
        self._preview_ctkimg = None

    def _preview_file(self, path):
        """Shows the large preview of the file selected in the table."""
        self._preview_path = path
        if not path:
            self._clear_preview_image()
            self.preview_img.configure(
                text="Selecciona un archivo\npara ver la vista previa")
            self.preview_name.configure(text="")
            self.preview_meta.configure(text="")
            self.preview_zoom_in.configure(text="")
            return

        try:
            pil = large_preview(path)
        except Exception:  # no preview; it is logged so it can be investigated
            log.warning("No se pudo mostrar la vista previa de %s", path, exc_info=True)
            pil = None
        if pil is not None:
            img = ctk.CTkImage(light_image=pil, dark_image=pil,
                               size=(pil.width, pil.height))
            self._preview_ctkimg = img  # keep the reference
            self.preview_img.configure(image=img, text="")
        else:
            self._clear_preview_image()
            self.preview_img.configure(text="(sin vista previa)")

        self.preview_name.configure(text=os.path.basename(path))
        parts = [os.path.dirname(path)]
        data = []
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        if ext in IMAGE_EXT:
            try:
                from PIL import Image
                with Image.open(path) as im:
                    data.append(f"{im.width}×{im.height}")
            except (OSError, ValueError):  # if it cannot be read, the resolution is omitted
                pass
        try:
            st = os.stat(path)
            data.append(format_size(st.st_size))
            data.append(datetime.datetime.fromtimestamp(
                st.st_mtime).strftime("%d/%m/%Y %H:%M"))
        except OSError:
            pass
        if data:
            parts.append("   ·   ".join(data))
        self.preview_meta.configure(text="\n".join(parts))
        self.preview_zoom_in.configure(
            text=f"{icons.SEARCH}  Clic para ver la imagen en grande"
            if can_be_displayed(path) else "")

    def _show_kinds(self):
        if not self._result or self._result.total_groups == 0:
            return
        ExtensionBreakdownWindow(self.winfo_toplevel(), self._result, self._add_extension_to_filter)

    def _export_csv(self):
        if not self._result or self._result.total_groups == 0:
            return
        path = filedialog.asksaveasfilename(
            title="Guardar informe CSV", defaultextension=".csv",
            initialfile="duplicates_report.csv",
            filetypes=[("CSV", "*.csv"), ("Todos los archivos", "*.*")])
        if not path:
            return
        try:
            n = export_csv(self._result, path)
        except OSError as e:
            messagebox.showerror("No se pudo guardar",
                                 f"No se pudo escribir el archivo:\n\n{e}")
            return
        messagebox.showinfo("Informe guardado",
                            f"Se han guardado {n} grupos de duplicados en:\n\n{path}")
