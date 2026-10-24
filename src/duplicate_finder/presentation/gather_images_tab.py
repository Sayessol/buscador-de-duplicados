""" "Gather images" tab: collects into one folder the photos spread across another.

It is a component with its OWN state (the list of images, the queues, the thread...):
the main window only creates it and notifies it of the Simple / Advanced mode.
"""

import logging
import os
import queue
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from duplicate_finder.application.file_transfers import InvalidDestination, validate_destination
from duplicate_finder.application.gather import non_image_kinds
from duplicate_finder.application.services import Services
from duplicate_finder.domain.transfers import COPY, LEAVE, MOVE, NonImageRules
from duplicate_finder.i18n import tr

from . import icons, styles
from .background_job import BackgroundJob
from .dialogs import offer_to_open_folder, proceed_despite
from .image_viewer import open_viewer
from .non_image_kinds_dialog import NonImageKindsWindow
from .thumbnails import (
    clear_cache,
    thumbnail_or_placeholder,
)
from .widgets import EmptyState, KeyedSegmentedButton, SectionHeader, StatTile, make_card

log = logging.getLogger(__name__)

# Keys of the options of the selectors (the labels the user sees come from the catalog).
SCOPE_ALL, SCOPE_FIRST = "all", "first"
STRATEGY_FILES, STRATEGY_FOLDER = "files", "folder"


class GatherImagesTab(ctk.CTkFrame):
    def __init__(self, container, services: Services):
        """`container` is the CTkTabview tab where this component is placed."""
        super().__init__(container, fg_color="transparent")
        self._services = services
        container.grid_columnconfigure(0, weight=1)  # the component fills the whole tab
        container.grid_rowconfigure(0, weight=1)
        self.grid(row=0, column=0, sticky="nsew")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        self._thumbs_queue: queue.Queue[tuple] = (
            queue.Queue()
        )  # messages from the thread that creates thumbnails
        self._cancel = threading.Event()
        self._job = BackgroundJob(self.after, self._apply_progress, self._finished, self._error)
        self._pending = None  # (action, destination) of the running operation
        self._images: list = []
        self._others: list = []
        self._folder = None
        self._included: set[str] = set()  # ticked image paths
        self._thumbs: dict = {}
        self._img_cache: list = []  # references to CTkImage (otherwise they are garbage collected)
        self._tiles: dict = {}

        self._build()
        self._initial_state()

    def apply_mode(self, advanced):
        """Called by the window when switching between Simple and Advanced."""
        (self._advanced.grid if advanced else self._advanced.grid_remove)()
        if not advanced:
            self.seg_action.set_key(MOVE)
            self.seg_strategy.set_key(STRATEGY_FILES)

    def cancel_jobs(self):
        """Called by the window when it closes: if an operation is running, it is cancelled."""
        if self._job.running:
            self._cancel.set()

    def _build(self):
        t = self

        card = make_card(t, 0)
        SectionHeader(card, 1, tr("gather.header"), icons.GATHER).grid(
            row=0, column=0, sticky="w", padx=16, pady=(14, 4)
        )
        ctk.CTkLabel(
            card,
            text=tr("gather.intro"),
            font=styles.base_font(11),
            text_color=styles.COLOR_MUTED_TEXT,
            anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 8))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 6))
        row.grid_columnconfigure(0, weight=1)
        self.entry_folder = ctk.CTkEntry(
            row, height=36, placeholder_text=tr("gather.folder_placeholder")
        )
        self.entry_folder.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.btn_choose = ctk.CTkButton(
            row,
            text=f"{icons.FOLDER}  {tr('common.choose')}",
            width=110,
            height=36,
            command=self._choose_folder,
        )
        self.btn_choose.grid(row=0, column=1, padx=4)
        self.btn_search = ctk.CTkButton(
            row,
            text=f"{icons.SEARCH}  {tr('gather.find_images')}",
            width=150,
            height=36,
            font=styles.base_font(13, "bold"),
            command=self._search,
        )
        self.btn_search.grid(row=0, column=2, padx=(4, 0))

        self.seg_scope = KeyedSegmentedButton(
            card, {SCOPE_ALL: tr("gather.scope_all"), SCOPE_FIRST: tr("gather.scope_first")}
        )
        self.seg_scope.set_key(SCOPE_ALL)
        self.seg_scope.grid(row=3, column=0, sticky="w", padx=16, pady=(0, 14))

        # --- destination / action options (row) --------------------
        option = ctk.CTkFrame(card, fg_color="transparent")
        option.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 12))
        option.grid_columnconfigure(0, weight=1)
        self.entry_destination = ctk.CTkEntry(
            option, height=34, placeholder_text=tr("gather.destination_placeholder")
        )
        self.entry_destination.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(
            option,
            text=f"{icons.FOLDER}  {tr('common.choose')}",
            width=100,
            height=34,
            command=self._choose_destination,
        ).grid(row=0, column=1, padx=4)

        self._advanced = ctk.CTkFrame(card, fg_color="transparent")
        self._advanced.grid(row=5, column=0, sticky="w", padx=16, pady=(0, 12))
        ctk.CTkLabel(
            self._advanced, text=tr("gather.action_label"), font=styles.base_font(12)
        ).pack(side="left", padx=(0, 6))
        self.seg_action = KeyedSegmentedButton(
            self._advanced, {MOVE: tr("gather.action_move"), COPY: tr("gather.action_copy")}
        )
        self.seg_action.set_key(MOVE)
        self.seg_action.pack(side="left", padx=(0, 16))
        ctk.CTkLabel(
            self._advanced, text=tr("gather.strategy_label"), font=styles.base_font(12)
        ).pack(side="left", padx=(0, 6))
        self.seg_strategy = KeyedSegmentedButton(
            self._advanced,
            {
                STRATEGY_FILES: tr("gather.strategy_files"),
                STRATEGY_FOLDER: tr("gather.strategy_folder"),
            },
        )
        self.seg_strategy.set_key(STRATEGY_FILES)
        self.seg_strategy.pack(side="left")

        # Progress
        self.progress_area = ctk.CTkFrame(t, fg_color="transparent")
        self.progress_area.grid(row=1, column=0, sticky="ew", padx=16, pady=(8, 0))
        self.progress_area.grid_columnconfigure(0, weight=1)
        self.progress_bar = ctk.CTkProgressBar(self.progress_area, height=10)
        self.progress_bar.grid(row=0, column=0, sticky="ew", pady=(4, 2))
        self.progress_bar.set(0)
        self.lbl_state = ctk.CTkLabel(
            self.progress_area,
            text="",
            font=styles.base_font(12),
            text_color=styles.COLOR_MUTED_TEXT,
            anchor="w",
        )
        self.lbl_state.grid(row=1, column=0, sticky="ew")

        # Statistics
        self.stats_row = ctk.CTkFrame(t, fg_color="transparent")
        self.stats_row.grid(row=2, column=0, sticky="ew", padx=6, pady=(10, 0))
        for i in range(3):
            self.stats_row.grid_columnconfigure(i, weight=1)
        self.stat_img = StatTile(self.stats_row, tr("gather.tile_found"))
        self.stat_sel = StatTile(self.stats_row, tr("gather.tile_marked"))
        self.stat_others = StatTile(self.stats_row, tr("gather.tile_others"))
        for i, b in enumerate((self.stat_img, self.stat_sel, self.stat_others)):
            b.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 6, 0))

        # Gallery
        self.gallery = ctk.CTkScrollableFrame(t, fg_color=styles.COLOR_TABLE_BACKGROUND)
        self.gallery.grid(row=4, column=0, sticky="nsew", padx=6, pady=(10, 0))
        for c in range(6):
            self.gallery.grid_columnconfigure(c, weight=1, uniform="tile")
        self.empty_state = EmptyState(
            t, icons.GATHER, tr("gather.not_searched_title"), tr("gather.empty_detail")
        )
        self.empty_state.grid(row=4, column=0, sticky="nsew", padx=6, pady=(10, 0))

        # Bottom bar
        bar = ctk.CTkFrame(t, fg_color=styles.COLOR_CARD)
        bar.grid(row=5, column=0, sticky="ew", padx=6, pady=(10, 6))
        bar.grid_columnconfigure(0, weight=1)
        self.lbl_totals = ctk.CTkLabel(
            bar, text="", font=styles.base_font(12), text_color=styles.COLOR_MUTED_TEXT, anchor="w"
        )
        self.lbl_totals.grid(row=0, column=0, padx=16, pady=12, sticky="w")
        self.btn_gather = ctk.CTkButton(
            bar,
            text=f"{icons.GATHER}  {tr('gather.gather_here')}",
            width=170,
            height=36,
            font=styles.base_font(13, "bold"),
            fg_color=styles.COLOR_OK_BUTTON,
            hover_color="#26734d",
            command=self._run,
        )
        self.btn_gather.grid(row=0, column=1, padx=(4, 16), pady=12)

    def _initial_state(self):
        self.progress_bar.set(0)
        self.lbl_state.configure(text="")
        self.progress_area.grid_remove()
        self.stats_row.grid_remove()
        styles.action_button(self.btn_gather, False)
        self.lbl_totals.configure(text="")
        self._show_gallery(False)

    def _show_gallery(self, show):
        if show:
            self.empty_state.grid_remove()
            self.gallery.grid()
        else:
            self.gallery.grid_remove()
            self.empty_state.grid()

    # -- search images -----------------------------------------
    def _choose_folder(self):
        folder = filedialog.askdirectory(title=tr("gather.pick_folder"))
        if folder:
            self.entry_folder.delete(0, "end")
            self.entry_folder.insert(0, os.path.normpath(folder))

    def _choose_destination(self):
        folder = filedialog.askdirectory(title=tr("gather.pick_destination"), mustexist=False)
        if folder:
            self.entry_destination.delete(0, "end")
            self.entry_destination.insert(0, os.path.normpath(folder))

    def _search(self):
        folder = self.entry_folder.get().strip()
        if not folder or not os.path.isdir(folder):
            messagebox.showwarning(
                tr("common.invalid_folder_title"), tr("gather.invalid_folder_msg")
            )
            return
        recursive = self.seg_scope.get_key() == SCOPE_ALL
        self._folder = folder
        clear_cache()
        try:
            images, others = self._services.gather.list_all(folder, recursive=recursive)
        except OSError as e:
            messagebox.showerror(tr("gather.read_error_title"), str(e))
            return
        self._images = images
        self._others = others
        self._included = set(images)
        self._thumbs = {}

        if not images:
            self._initial_state()
            self.empty_state.configure(
                title=tr("gather.no_images_title"),
                detail=tr("gather.no_images_detail")
                + ("" if recursive else tr("gather.first_level_suffix"))
                + ".",
            )
            self._show_gallery(False)
            return

        self.stats_row.grid()
        self.stat_img.set(len(images))
        self.stat_others.set(len(others))
        self._build_gallery()
        self._show_gallery(True)
        styles.action_button(self.btn_gather, True)
        self._update_totals()
        # thumbnails in a thread
        threading.Thread(target=self._load_thumbs, args=(list(images),), daemon=True).start()
        self.after(80, self._process_thumbs)

    def _load_thumbs(self, paths):
        for r in paths:
            try:
                self._thumbs[r] = thumbnail_or_placeholder(r, 96)
            except Exception as e:  # a broken file must not stop the gallery
                log.info("Could not create the thumbnail of %s: %s", r, e)
                self._thumbs[r] = None
            self._thumbs_queue.put(r)

    def _process_thumbs(self):
        processed_count = 0
        try:
            while processed_count < 30:
                path = self._thumbs_queue.get_nowait()
                processed_count += 1
                self._paint_thumb(path)
        except queue.Empty:
            pass
        self.after(70, self._process_thumbs)

    def _build_gallery(self):
        for h in self.gallery.winfo_children():
            h.destroy()
        self._img_cache.clear()
        self._tiles.clear()

        cols = 6
        LIMIT = 300
        for i, path in enumerate(self._images[:LIMIT]):
            tile = ctk.CTkFrame(self.gallery, fg_color=styles.COLOR_TILE, corner_radius=6)
            tile.grid(row=i // cols, column=i % cols, padx=4, pady=4, sticky="new")
            mark = ctk.CTkCheckBox(tile, text="", width=20, command=lambda r=path: self._toggle(r))
            mark.select()
            mark.grid(row=0, column=0, padx=(6, 0), pady=(4, 0), sticky="w")
            lbl = ctk.CTkLabel(
                tile, text="…", width=96, height=96, text_color=styles.COLOR_MUTED_TEXT
            )
            lbl.grid(row=1, column=0, padx=6, pady=(0, 2))
            lbl.configure(cursor="hand2")
            lbl.bind("<Button-1>", lambda _e, r=path: open_viewer(self.winfo_toplevel(), r))
            ctk.CTkLabel(
                tile, text=Path(path).name, font=styles.base_font(9), wraplength=96, justify="left"
            ).grid(row=2, column=0, padx=6, pady=(0, 6), sticky="w")
            self._tiles[path] = (tile, mark, lbl)

        if len(self._images) > LIMIT:
            ctk.CTkLabel(
                self.gallery,
                text=tr("gather.and_more", hidden=len(self._images) - LIMIT),
                font=styles.base_font(11),
                text_color=styles.COLOR_MUTED_TEXT,
            ).grid(row=LIMIT, column=0, columnspan=cols, pady=8)

    def _paint_thumb(self, path):
        input = self._tiles.get(path)
        pil = self._thumbs.get(path)
        if not input or pil is None:
            return
        _tile, _mark, lbl = input
        img = ctk.CTkImage(light_image=pil, dark_image=pil, size=(pil.width, pil.height))
        self._img_cache.append(img)
        lbl.configure(image=img, text="")

    def _toggle(self, path):
        input = self._tiles.get(path)
        if not input:
            return
        _tile, mark, _lbl = input
        if mark.get():
            self._included.add(path)
        else:
            self._included.discard(path)
        self._update_totals()

    def _update_totals(self):
        n = len(self._included)
        self.stat_sel.set(n)
        styles.action_button(self.btn_gather, bool(n))
        self.lbl_totals.configure(text=tr("gather.totals", n=n, others=len(self._others)))

    # -- run ----------------------------------------------------
    def _run(self):
        """ "Gather here" button. Steps: validate the destination -> depending on the
        strategy, confirm and launch the operation in a thread."""
        source = self._folder
        if not source:
            return
        destination = self.entry_destination.get().strip()
        if not destination:
            messagebox.showwarning(
                tr("gather.missing_destination_title"), tr("gather.missing_destination_msg")
            )
            return
        destination = os.path.normpath(destination)
        try:
            # reject a destination that is inside the source
            warning = validate_destination(destination, source)
        except InvalidDestination as e:
            messagebox.showerror(tr("gather.invalid_destination_title"), str(e))
            return
        if not proceed_despite(warning):
            return

        action = self.seg_action.get_key()
        strategy = self.seg_strategy.get_key()
        verb = tr("gather.infinitive_copy" if action == COPY else "gather.infinitive_move")

        if strategy == STRATEGY_FOLDER:
            name = os.path.basename(os.path.normpath(source))
            if not messagebox.askyesno(
                tr("common.confirm"),
                tr(
                    "gather.confirm_whole_folder",
                    upper=verb.upper(),
                    name=name,
                    destination=destination,
                ),
            ):
                return
            self._launch(
                lambda p, c: self._services.gather.gather_whole_folder(
                    source,
                    destination,
                    action=action,
                    progress=p,
                    description=tr("gather.description_folder", name=name),
                ),
                action,
                destination,
            )
            return

        # --- By files ---
        images = [r for r in self._images if r in self._included]  # only the ticked boxes
        if not images:
            return
        others = self._others
        rules = NonImageRules()  # default: leave all non-images
        if others:
            # MODAL dialog: wait_window() blocks here until it is closed;
            # afterwards we read dlg.rules (or None if the user cancelled).
            dlg = NonImageKindsWindow(self.winfo_toplevel(), non_image_kinds(others))
            self.wait_window(dlg)
            if dlg.rules is None:
                return
            rules = dlg.rules

        n_others = sum(
            1 for r in others if rules.action(os.path.splitext(r)[1].lower().lstrip(".")) != LEAVE
        )
        if not messagebox.askyesno(
            tr("common.confirm"),
            tr("gather.confirm_files", upper=verb.upper(), count=len(images))
            + (tr("gather.confirm_and_others", n_others=n_others) if n_others else "")
            + tr("gather.confirm_tail", destination=destination),
        ):
            return

        self._launch(
            lambda p, c: self._services.gather.gather_by_files(
                images,
                others,
                source,
                destination,
                action=action,
                rules=rules,
                progress=p,
                cancelled=c,
                description=tr("gather.description_files", count=len(images)),
            ),
            action,
            destination,
        )

    def _launch(self, fn, action, destination):
        self._cancel.clear()
        self.progress_area.grid()
        self.progress_bar.set(0)
        self.lbl_state.configure(text=tr("gather.starting"))
        styles.action_button(self.btn_gather, False)
        styles.activate_button(self.btn_search, False)
        styles.activate_button(self.btn_choose, False)

        self._pending = (action, destination)
        self._job.start(
            lambda report: fn(lambda a, t, m: report((a, t, m)), self._cancel.is_set),
            what=f"Gather ({action}) from {self._folder} to {destination}",
        )

    def _apply_progress(self, progress):
        current, total, message = progress
        self.lbl_state.configure(text=message)
        if total:
            self.progress_bar.set(min(current / total, 1.0))

    def _finished(self, res):
        action, destination = self._pending
        styles.activate_button(self.btn_search, True)
        styles.activate_button(self.btn_choose, True)
        self.progress_bar.set(1.0)

        done = res.done
        verb = tr("gather.past_copy" if action == COPY else "gather.past_move")
        self.lbl_state.configure(
            text=tr("gather.done_summary", count=len(done), verb=verb)
            + (tr("gather.failed_suffix", count=len(res.failed)) if res.failed else "")
        )
        self.lbl_totals.configure(
            text=tr("gather.totals_done", count=len(done), verb=verb, destination=destination)
        )

        # clear the list (what was moved is no longer there)
        self._images = []
        self._included = set()
        self.stats_row.grid_remove()
        styles.action_button(self.btn_gather, False)
        for h in self.gallery.winfo_children():
            h.destroy()
        self.empty_state.configure(
            title=tr("gather.result_title", count=len(done), verb=verb),
            detail=tr("gather.undo_hint"),
        )
        self._show_gallery(False)

        detail = tr("gather.result_detail", count=len(done), verb=verb, destination=destination)
        if res.log_path:
            detail += tr("common.log_note", log_path=res.log_path)
        offer_to_open_folder(detail + tr("gather.open_destination_question"), destination)

    def _error(self, e):
        styles.action_button(self.btn_gather, True)
        styles.activate_button(self.btn_search, True)
        styles.activate_button(self.btn_choose, True)
        self.progress_bar.set(0)
        self.lbl_state.configure(text=tr("gather.failed"))
        messagebox.showerror(
            tr("gather.error_title"), tr("gather.error_detail", name=type(e).__name__, e=e)
        )
