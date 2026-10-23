""""Exact duplicates" tab: scans a folder and decides which copy to keep.

It is a component with its OWN state (scan result, selection, queues, threads...):
the main window only creates it, notifies it of the Simple / Advanced mode and that it is closing.
"""

import logging
import datetime
import os
import queue
import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk

from duplicate_finder.application.scan_duplicates import ScanCancelled
from duplicate_finder.application.services import Services
from duplicate_finder.domain.formatting import format_size
from duplicate_finder.domain.filters import (
    ScanFilter,
    parse_extensions,
    parse_names,
    set_to_text,
    JUNK_EXTENSIONS,
    JUNK_NAMES,
    JUNK_FOLDERS,
    CATEGORY_EXTENSIONS,
)
from duplicate_finder.application.quarantine import (
    validate_quarantine_folder,
    InvalidQuarantine,
)
from duplicate_finder.domain.operations import KIND_QUARANTINE
from duplicate_finder.domain.transfers import MOVE as MOVE_ACTION
from . import styles
from . import icons
from .widgets import SectionHeader, StatTile, EmptyState, make_card
from .results_table import ResultsTable
from .thumbnails import (
    large_preview, clear_cache, IMAGE_EXT,
)
from .image_viewer import open_viewer, can_be_displayed
from .extension_breakdown_dialog import ExtensionBreakdownWindow
from duplicate_finder.i18n import tr

log = logging.getLogger(__name__)


class ExactDuplicatesTab(ctk.CTkFrame):
    def __init__(self, container, advanced, services: Services):
        """`container` is the CTkTabview tab where this component is placed;
        `advanced` is the mode the window starts with."""
        super().__init__(container, fg_color="transparent")
        self._services = services
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
        SectionHeader(card, 1, tr("exact.choose_folder_header"),
                        icons.FOLDER).grid(
            row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 16))
        row.grid_columnconfigure(0, weight=1)

        self.entry_folder = ctk.CTkEntry(
            row, height=36, placeholder_text=tr("common.folder_placeholder"))
        self.entry_folder.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.btn_choose = ctk.CTkButton(
            row, text=f"{icons.FOLDER}  {tr("common.choose")}", width=110, height=36,
            command=self._choose_folder)
        self.btn_choose.grid(row=0, column=1, padx=4)
        self.btn_scan = ctk.CTkButton(
            row, text=f"{icons.SEARCH}  {tr("common.scan")}", width=130, height=36,
            font=styles.base_font(13, "bold"), command=self._start_scan)
        self.btn_scan.grid(row=0, column=2, padx=(4, 0))

    def _build_scan_options(self):
        cont = ctk.CTkFrame(self, fg_color="transparent")
        cont.grid(row=2, column=0, sticky="ew", padx=6, pady=(6, 0))
        cont.grid_columnconfigure(0, weight=1)
        self._options_container = cont

        self._options_open = ctk.BooleanVar(value=False)
        self.btn_toggle_options = ctk.CTkButton(
            cont, text=f"{icons.TRI_RIGHT}  {icons.GEAR}  {tr("exact.options_toggle")}",
            anchor="w", fg_color="transparent", hover=False,
            text_color=styles.COLOR_MUTED_TEXT, command=self._toggle_options)
        self.btn_toggle_options.grid(row=0, column=0, sticky="ew")

        self.options_panel = ctk.CTkFrame(cont, fg_color=styles.COLOR_CARD)
        self.options_panel.grid(row=1, column=0, sticky="ew", pady=(2, 0))
        self.options_panel.grid_columnconfigure(1, weight=1)
        self.options_panel.grid_remove()
        p = self.options_panel

        # --- Search only these kinds (whitelist) ------------------
        ctk.CTkLabel(p, text=tr("exact.only_kinds"),
                     font=styles.base_font(12, "bold")).grid(
            row=0, column=0, columnspan=3, padx=16, pady=(12, 4), sticky="w")

        chips = ctk.CTkFrame(p, fg_color="transparent")
        chips.grid(row=1, column=0, columnspan=3, padx=14, pady=(0, 4), sticky="w")
        self.chk_categories = {}
        for name in CATEGORY_EXTENSIONS:
            chk = ctk.CTkCheckBox(
                chips, text=f"{icons.CATEGORY_ICON[name]}  {tr(f"category.{name}")}",
                font=styles.base_font(12),
                command=lambda n=name: self._toggle_category(n))
            chk.pack(side="left", padx=(2, 12), pady=4)
            self.chk_categories[name] = chk

        ctk.CTkLabel(p, text=tr("exact.extensions"), font=styles.base_font(12)).grid(
            row=2, column=0, padx=(16, 8), pady=4, sticky="w")
        self.entry_include = ctk.CTkEntry(
            p, height=32, placeholder_text=tr("exact.all_kinds_placeholder"))
        self.entry_include.grid(row=2, column=1, columnspan=2, padx=(4, 16),
                                pady=4, sticky="ew")
        self.entry_include.bind("<KeyRelease>", self._sync_categories)

        ctk.CTkLabel(
            p, text=tr("exact.categories_hint"),
            font=styles.base_font(11), text_color=styles.COLOR_MUTED_TEXT,
        ).grid(row=3, column=0, columnspan=3, padx=16, pady=(0, 10), sticky="w")

        ctk.CTkFrame(p, height=1, fg_color=styles.COLOR_ALTERNATE_ROW).grid(
            row=4, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 8))

        # --- Ignore (blacklist) ------------------------------------
        ctk.CTkLabel(p, text=tr("exact.ignore_also"),
                     font=styles.base_font(12, "bold")).grid(
            row=5, column=0, columnspan=3, padx=16, pady=(0, 4), sticky="w")

        def field(row, label):
            ctk.CTkLabel(p, text=label, font=styles.base_font(12)).grid(
                row=row, column=0, padx=(16, 8), pady=4, sticky="w")
            e = ctk.CTkEntry(p, height=32)
            e.grid(row=row, column=1, columnspan=2, padx=(4, 16), pady=4,
                   sticky="ew")
            return e

        self.entry_ext = field(6, tr("exact.extensions"))
        self.entry_folders = field(7, tr("exact.folders"))
        self.entry_names = field(8, tr("exact.names"))

        self.chk_empty = ctk.CTkCheckBox(
            p, text=tr("exact.ignore_empty"), font=styles.base_font(12))
        self.chk_empty.grid(row=9, column=0, columnspan=2, padx=16,
                             pady=(6, 4), sticky="w")

        buttons = ctk.CTkFrame(p, fg_color="transparent")
        buttons.grid(row=9, column=2, padx=12, pady=(6, 4), sticky="e")
        ctk.CTkButton(buttons, text=tr("exact.defaults"), width=140,
                      fg_color="transparent", border_width=1,
                      text_color=styles.COLOR_TEXT,
                      command=self._default_filters).pack(side="left", padx=4)
        ctk.CTkButton(buttons, text=tr("exact.clear_all"), width=90,
                      fg_color="transparent", border_width=1,
                      text_color=styles.COLOR_TEXT,
                      command=self._empty_filters).pack(side="left", padx=4)

        ctk.CTkLabel(
            p, text=tr("exact.separate_hint"),
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
            card, 2, tr("exact.keep_header"), icons.STAR)
        self.decision_card_header.grid(row=0, column=0, sticky="w",
                                       padx=16, pady=(14, 8))

        row = ctk.CTkFrame(card, fg_color="transparent")
        self.decision_card_row = row
        row.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 6))
        row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(row, text=tr("exact.preferred_folder"),
                     font=styles.base_font(12)).grid(
            row=0, column=0, padx=(0, 8), pady=6, sticky="w")
        self.entry_preferred_folder = ctk.CTkEntry(
            row, height=34,
            placeholder_text=tr("exact.preferred_placeholder"))
        self.entry_preferred_folder.grid(row=0, column=1, padx=4, pady=6, sticky="ew")
        self.btn_choose_preferred = ctk.CTkButton(
            row, text=f"{icons.FOLDER}  {tr("common.choose")}", width=100, height=34,
            command=self._choose_preferred_folder)
        self.btn_choose_preferred.grid(row=0, column=2, padx=4, pady=6)
        self.btn_rule = ctk.CTkButton(
            row, text=f"{icons.AUTO}  {tr("exact.rule_by_folder")}", width=170,
            height=34, command=self._apply_rule)
        self.btn_rule.grid(row=0, column=3, padx=4, pady=6)
        self.btn_primary = ctk.CTkButton(
            row, text=f"{icons.OK}  {tr("exact.choose_main")}", width=170,
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

        self.stat_groups = StatTile(self.stats_row, tr("exact.tile_groups"))
        self.stat_duplicates = StatTile(self.stats_row, tr("exact.tile_files"))
        self.stat_move = StatTile(self.stats_row, tr("exact.tile_to_move"))
        self.stat_space = StatTile(self.stats_row, tr("common.tile_recoverable"))
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
            tr("exact.empty_title"),
            tr("exact.empty_detail"))
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
            text=tr("exact.preview_hint"),
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
            bar, text=tr("exact.not_scanned"), font=styles.base_font(12),
            text_color=styles.COLOR_MUTED_TEXT, anchor="w")
        self.lbl_totals.grid(row=0, column=0, padx=16, pady=12, sticky="w")

        self.btn_kinds = ctk.CTkButton(
            bar, text=f"{icons.CHART}  {tr("exact.view_kinds")}", width=180,
            height=36, fg_color="transparent", border_width=1,
            text_color=styles.COLOR_TEXT,
            command=self._show_kinds)
        self.btn_kinds.grid(row=0, column=1, padx=4, pady=12)
        self.btn_export = ctk.CTkButton(
            bar, text=f"{icons.SAVE}  {tr("exact.export_csv")}", width=150, height=36,
            fg_color="transparent", border_width=1, text_color=styles.COLOR_TEXT,
            command=self._export_csv)
        self.btn_export.grid(row=0, column=2, padx=4, pady=12)
        self.btn_quarantine = ctk.CTkButton(
            bar, text=f"{icons.SHIELD}  {tr("common.move_quarantine")}", width=200,
            height=36, font=styles.base_font(13, "bold"),
            fg_color=styles.COLOR_OK_BUTTON, hover_color="#26734d",
            command=self._move_to_quarantine)
        self.btn_quarantine.grid(row=0, column=3, padx=(4, 16), pady=12)

    def _toggle_options(self):
        open = not self._options_open.get()
        self._options_open.set(open)
        tri = icons.TRI_DOWN if open else icons.TRI_RIGHT
        self.btn_toggle_options.configure(
            text=f"{tri}  {icons.GEAR}  {tr("exact.options_toggle")}")
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
                text=f"{icons.CROSS}  {tr("common.cancel")}", command=self._cancel_scan,
                state="normal",
                fg_color=styles.COLOR_DANGER_BUTTON,
                hover_color=("#9c2f24", "#8f2b22"),
                text_color="#ffffff")
        else:
            styles.activate_button(self.btn_scan, True)
            self.btn_scan.configure(
                text=f"{icons.SEARCH}  {tr("common.scan")}", command=self._start_scan)

    def _choose_folder(self):
        folder = filedialog.askdirectory(title=tr("exact.pick_scan_folder"))
        if folder:
            self.entry_folder.delete(0, "end")
            self.entry_folder.insert(0, os.path.normpath(folder))

    def _choose_preferred_folder(self):
        folder = filedialog.askdirectory(title=tr("exact.pick_preferred_folder"))
        if folder:
            self.entry_preferred_folder.delete(0, "end")
            self.entry_preferred_folder.insert(0, os.path.normpath(folder))

    def _start_scan(self):
        folder = self.entry_folder.get().strip()
        if not folder:
            messagebox.showwarning(tr("exact.missing_folder_title"),
                                   tr("exact.missing_folder_msg"))
            return
        if not os.path.isdir(folder):
            messagebox.showerror(
                tr("common.invalid_folder_title"),
                tr("exact.invalid_folder_msg", folder=folder))
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
        self.lbl_state.configure(text=tr("exact.preparing"))
        self.lbl_totals.configure(text=tr("exact.scanning"))
        self.lbl_validation.configure(text="")
        self.stats_row.grid_remove()
        self.empty_state.configure(
            title=tr("exact.scanning"), detail=tr("exact.searching_detail"))
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
        self.lbl_state.configure(text=tr("common.cancelling"))
        self.btn_scan.configure(state="disabled")

    def _scan_job(self, folder, filter):
        """Runs in the SECONDARY THREAD. It does not touch a single widget: everything goes through
        the queue as tuples (kind, data)."""
        try:
            result = self._services.scan_duplicates(
                folder,
                progress=lambda p: self._queue.put(("progress", p)),
                cancelled=self._cancel_event.is_set,
                filter=filter,
            )
            self._queue.put(("done", result))
        except ScanCancelled:
            self._queue.put(("cancelled", None))
        except Exception as e:  # any failure is logged and shown
            log.exception("Scan of %s failed", folder)
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
            tr("exact.excluded_suffix", total_excluded=result.total_excluded)
            if result.total_excluded else "")

        if result.total_groups == 0:
            self.stats_row.grid_remove()
            self.lbl_state.configure(text=tr("exact.none_found"))
            self.lbl_totals.configure(
                text=tr("exact.totals_none", total_files=result.total_files,
                        excl_text=self._excl_text))
            self._enable_actions(False)
            self._enable_decision(False)
            self.lbl_validation.configure(text="")
            self.empty_state.configure(
                title=tr("exact.none_found_title"),
                detail=tr("exact.none_found_detail", total_files=result.total_files))
            self.empty_state.tkraise()
            return

        self._selection = self._services.start_selection(result)
        if not self._advanced:
            self._selection.preselect_primary()
        self.table.load(self._selection)
        self.table.tkraise()
        self.stats_row.grid()
        self.stat_groups.set(result.total_groups)
        self.stat_duplicates.set(result.total_files_duplicates)
        self.lbl_state.configure(
            text=tr("scan.finished")
            + (tr("exact.unreadable", count=len(result.errors))
               if result.errors else ""))
        self._enable_actions(True)
        self._enable_decision(True)
        self._on_selection_change()

    def _scan_cancelled(self):
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(0)
        self.lbl_state.configure(text=tr("exact.cancelled"))
        self.lbl_totals.configure(text=tr("exact.cancelled"))
        self._set_scanning(False)
        self.btn_scan.configure(state="normal")
        self.empty_state.configure(
            title=tr("exact.cancelled_title"),
            detail=tr("exact.cancelled_detail"))
        self.empty_state.tkraise()

    def _scan_failed(self, e):
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(0)
        self.lbl_state.configure(text=tr("exact.failed"))
        self.lbl_totals.configure(text=tr("exact.failed"))
        self._set_scanning(False)
        self.btn_scan.configure(state="normal")
        messagebox.showerror(tr("exact.error_title"),
                             tr("exact.error_msg", name=type(e).__name__, e=e))

    def _apply_rule(self):
        if self._selection is None:
            return
        preferred_folder = self.entry_preferred_folder.get().strip()
        if not preferred_folder:
            messagebox.showinfo(
                tr("exact.need_preferred_title"),
                tr("exact.need_preferred_msg"))
            return
        if not os.path.isdir(preferred_folder):
            if not messagebox.askyesno(
                tr("exact.no_such_folder_title"),
                tr("exact.no_such_folder_msg", preferred_folder=preferred_folder)):
                return

        resolved, no_match = self._selection.apply_folder_rule(
            preferred_folder)
        self.table.refresh_all()
        self._on_selection_change()

        msg = tr("exact.rule_applied", resolved=resolved)
        if no_match:
            msg += tr("exact.rule_no_match", no_match=no_match)
            self.table.go_to_pending()
        messagebox.showinfo(tr("exact.rule_title"), msg)

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
            text=tr("exact.totals", total_groups=r.total_groups,
                    total_files_duplicates=r.total_files_duplicates, excl_text=self._excl_text))

        if not pending:
            if not self._advanced:
                text = f"{icons.OK}  {tr("exact.hint_main_kept")}"
            else:
                text = f"{icons.OK}  {tr("exact.hint_all_resolved")}"
            self.lbl_validation.configure(text=text, text_color=styles.COLOR_OK)
            styles.action_button(self.btn_quarantine, True)
        else:
            self.lbl_validation.configure(
                text=f"{icons.WARNING}  {tr("exact.hint_unresolved", count=len(pending))}",
                text_color=styles.COLOR_WARNING)
            styles.action_button(self.btn_quarantine, False)

    def _move_to_quarantine(self):
        if self._selection is None or not self._selection.all_ready():
            return

        root = self._scanned_folder
        quarantine_folder = filedialog.askdirectory(
            title=tr("common.pick_quarantine"), mustexist=False)
        if not quarantine_folder:
            return
        quarantine_folder = os.path.normpath(quarantine_folder)

        try:
            warning = validate_quarantine_folder(quarantine_folder, root)
        except InvalidQuarantine as e:
            messagebox.showerror(tr("common.invalid_quarantine_title"), str(e))
            return
        if warning and not messagebox.askyesno(
                tr("common.warning"), warning + tr("common.continue_question")):
            return

        n = self._selection.count_to_move()
        frees = format_size(self._selection.space_to_free())
        if not messagebox.askyesno(
            tr("common.confirm_title"),
            tr("exact.confirm_msg", n=n, frees=frees, quarantine_folder=quarantine_folder)):
            return

        self._set_quarantine_busy(True)
        self.lbl_state.configure(text=tr("exact.moving"))
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
            res = self._services.move_to_quarantine(
                selection, root, quarantine_folder,
                progress=lambda a, t, m: self._quarantine_queue.put(("progress", (a, t, m))))
            self._quarantine_queue.put(("done", (res, quarantine_folder)))
        except Exception as e:  # it is logged and shown to the user
            log.exception("Move to quarantine failed (source %s, destination %s)",
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
                    self.lbl_state.configure(text=tr("exact.move_failed"))
                    messagebox.showerror(
                        tr("common.move_error_title"), tr("common.error_detail",
                                                          name=type(datum).__name__, datum=datum))
                    return
        except queue.Empty:
            pass
        self.after(100, self._poll_quarantine_queue)

    def _quarantine_finished(self, res, quarantine_folder):
        self._set_quarantine_busy(False)
        self.progress_bar.set(1.0)
        self.lbl_state.configure(text=tr("exact.move_done"))

        if res.moved:
            self._services.history.record(
                KIND_QUARANTINE, MOVE_ACTION, self._scanned_folder,
                quarantine_folder, [(m.source, m.destination) for m in res.moved],
                tr("exact.history_description", count=len(res.moved)))

        moved = len(res.moved)
        failed = len(res.failed)
        detail = tr("exact.moved_summary", moved=moved, size=format_size(res.bytes_moved))
        if failed:
            detail += tr("exact.failed_note", failed=failed)
        if res.log_path:
            detail += tr("common.log_note", log_path=res.log_path)

        self.table.clear()
        self._selection = None
        self._result = None
        self._enable_decision(False)
        self._enable_actions(False)
        self.lbl_validation.configure(text="")
        self.stats_row.grid_remove()
        self.lbl_totals.configure(
            text=tr("exact.moved_totals", moved=moved))
        self.empty_state.configure(
            title=tr("exact.moved_title"),
            detail=detail.split("\n\n")[0] + tr("exact.scan_again"))
        self.empty_state.tkraise()

        if messagebox.askyesno(
            tr("common.done_title"), detail + tr("exact.open_quarantine_question")):
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
                text=tr("exact.preview_hint"))
            self.preview_name.configure(text="")
            self.preview_meta.configure(text="")
            self.preview_zoom_in.configure(text="")
            return

        try:
            pil = large_preview(path)
        except Exception:  # no preview; it is logged so it can be investigated
            log.warning("Could not show the preview of %s", path, exc_info=True)
            pil = None
        if pil is not None:
            img = ctk.CTkImage(light_image=pil, dark_image=pil,
                               size=(pil.width, pil.height))
            self._preview_ctkimg = img  # keep the reference
            self.preview_img.configure(image=img, text="")
        else:
            self._clear_preview_image()
            self.preview_img.configure(text=tr("exact.no_preview"))

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
                st.st_mtime).strftime(tr("common.date_format")))
        except OSError:
            pass
        if data:
            parts.append("   ·   ".join(data))
        self.preview_meta.configure(text="\n".join(parts))
        self.preview_zoom_in.configure(
            text=f"{icons.SEARCH}  {tr("exact.click_to_enlarge")}"
            if can_be_displayed(path) else "")

    def _show_kinds(self):
        if not self._result or self._result.total_groups == 0:
            return
        ExtensionBreakdownWindow(self.winfo_toplevel(), self._result, self._add_extension_to_filter)

    def _export_csv(self):
        if not self._result or self._result.total_groups == 0:
            return
        path = filedialog.asksaveasfilename(
            title=tr("exact.save_report_title"), defaultextension=".csv",
            initialfile="duplicates_report.csv",
            filetypes=[("CSV", "*.csv"), (tr("common.all_files"), "*.*")])
        if not path:
            return
        try:
            n = self._services.export_report(self._result, path)
        except OSError as e:
            messagebox.showerror(tr("exact.save_failed_title"),
                                 tr("exact.save_failed_msg", e=e))
            return
        messagebox.showinfo(tr("exact.report_saved_title"),
                            tr("exact.report_saved_msg", n=n, path=path))
