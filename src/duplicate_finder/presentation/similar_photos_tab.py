""""Similar photos" tab: groups the same photo saved at different quality.

It is a component with its OWN state (result, selection, queues, thread, thumbnails...):
the main window only creates it and notifies it of the Simple / Advanced mode.
"""

import logging
import os
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from duplicate_finder.domain.formatting import format_size
from duplicate_finder.domain.selection import KEEP as _KEEP
from duplicate_finder.application.services import Services
from duplicate_finder.domain.similarity import ComparisonCancelled
from .background_job import BackgroundJob
from .dialogs import choose_quarantine_folder, offer_to_open_folder
from . import styles
from . import icons
from .image_viewer import open_viewer
from .widgets import SectionHeader, StatTile, EmptyState, make_card
from .thumbnails import (
    load_thumbnail, clear_cache,
)
from duplicate_finder.i18n import tr

log = logging.getLogger(__name__)


# Windows does not draw windows taller than 32,767 px: past that point the
# gallery gets cut off and the scrollbar disappears. That is why the groups
# are split into pages whose estimated height never gets close to that limit.
COLUMNS = 5                  # photos per row inside a group
HEADER_HEIGHT = 70            # px taken by the title of a group and its margins
ROW_HEIGHT = 400               # px of a row of photos (an upper bound)
PAGE_MAX_HEIGHT = 20000       # estimated px per page (real limit: 32,767)
MAX_GROUPS_PER_PAGE = 40        # and never more than 40 groups: the page is drawn quickly


def split_into_pages(counts):
    """Splits the groups into pages: returns a list of (first, last + 1).

    `counts` is the number of photos in each group. Every group fits in some
    page (if a single one exceeds the budget, it gets a page of its own)."""
    pages = []
    start = 0
    height = 0
    for i, n in enumerate(counts):
        h = HEADER_HEIGHT + ROW_HEIGHT * -(-n // COLUMNS)       # rows = n / 5 rounded up
        if i > start and (height + h > PAGE_MAX_HEIGHT or i - start >= MAX_GROUPS_PER_PAGE):
            pages.append((start, i))
            start, height = i, 0
        height += h
    if counts:
        pages.append((start, len(counts)))
    return pages


class SimilarPhotosTab(ctk.CTkFrame):
    def __init__(self, container, services: Services):
        """`container` is the CTkTabview tab where this component is placed."""
        super().__init__(container, fg_color="transparent")
        self._services = services
        container.grid_columnconfigure(0, weight=1)    # the component fills the whole tab
        container.grid_rowconfigure(0, weight=1)
        self.grid(row=0, column=0, sticky="nsew")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        self._cancel = threading.Event()
        self._job = BackgroundJob(
            self.after, self._apply_progress, lambda result: self._finished(*result),
            self._error, self._cancelled, cancelled_exceptions=(ComparisonCancelled,))
        self._result = None
        self._selection = None
        self._folder = None
        self._thumbs = {}
        self._img_cache = []  # references to CTkImage (otherwise they are garbage collected)
        self._tiles = {}
        self._buttons = {}
        self._pages = []    # [(first group, last + 1)] of each page of the gallery
        self._page = 0

        self._build()
        self._initial_state()

    def apply_mode(self, advanced):
        """Called by the window when switching between Simple and Advanced."""
        (self._sensitivity_row.grid if advanced else self._sensitivity_row.grid_remove)()
        if not advanced:
            self.sensitivity_slider.set(10)
            self._sensitivity_changed(10)

    def cancel_jobs(self):
        """Called by the window when it closes: if an analysis is running, it is cancelled."""
        if self._job.running:
            self._cancel.set()

    def _build(self):
        t = self

        card = make_card(t, 0)
        SectionHeader(
            card, 1, tr("similar.header"),
            icons.CAT_IMAGES).grid(row=0, column=0, sticky="w",
                                     padx=16, pady=(14, 4))
        ctk.CTkLabel(
            card, text=tr("similar.intro"),
            font=styles.base_font(11), text_color=styles.COLOR_MUTED_TEXT,
            wraplength=980, justify="left", anchor="w").grid(
            row=1, column=0, sticky="w", padx=16, pady=(0, 8))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 8))
        row.grid_columnconfigure(0, weight=1)
        self.entry_folder = ctk.CTkEntry(
            row, height=36, placeholder_text=tr("similar.folder_placeholder"))
        self.entry_folder.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.btn_choose = ctk.CTkButton(
            row, text=f"{icons.FOLDER}  {tr("common.choose")}", width=110, height=36,
            command=self._choose_folder)
        self.btn_choose.grid(row=0, column=1, padx=4)
        self.btn_analyze = ctk.CTkButton(
            row, text=f"{icons.CAT_IMAGES}  {tr("similar.analyze")}", width=130, height=36,
            font=styles.base_font(13, "bold"), command=self._start)
        self.btn_analyze.grid(row=0, column=2, padx=(4, 0))

        sensitivity = ctk.CTkFrame(card, fg_color="transparent")
        self._sensitivity_row = sensitivity
        sensitivity.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 14))
        ctk.CTkLabel(sensitivity, text=tr("similar.sensitivity"),
                     font=styles.base_font(12)).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(sensitivity, text=tr("similar.strict"), font=styles.base_font(11),
                     text_color=styles.COLOR_MUTED_TEXT).pack(side="left")
        self.sensitivity_slider = ctk.CTkSlider(
            sensitivity, from_=4, to=18, number_of_steps=14, width=220,
            command=self._sensitivity_changed)
        self.sensitivity_slider.set(10)
        self.sensitivity_slider.pack(side="left", padx=8)
        ctk.CTkLabel(sensitivity, text=tr("similar.tolerant"), font=styles.base_font(11),
                     text_color=styles.COLOR_MUTED_TEXT).pack(side="left")
        self.lbl_sensitivity = ctk.CTkLabel(
            sensitivity, text=tr("similar.sensitivity_label", label=tr("similar.normal")),
            font=styles.base_font(11),
            text_color=styles.COLOR_MUTED_TEXT)
        self.lbl_sensitivity.pack(side="left", padx=(6, 0))

        # Progress
        self.progress_area = ctk.CTkFrame(t, fg_color="transparent")
        self.progress_area.grid(row=1, column=0, sticky="ew",
                                    padx=16, pady=(8, 0))
        self.progress_area.grid_columnconfigure(0, weight=1)
        self.progress_bar = ctk.CTkProgressBar(
            self.progress_area, height=10)
        self.progress_bar.grid(row=0, column=0, sticky="ew", pady=(4, 2))
        self.progress_bar.set(0)
        self.lbl_state = ctk.CTkLabel(
            self.progress_area, text="", font=styles.base_font(12),
            text_color=styles.COLOR_MUTED_TEXT, anchor="w")
        self.lbl_state.grid(row=1, column=0, sticky="ew")

        # Statistics
        self.stats_row = ctk.CTkFrame(t, fg_color="transparent")
        self.stats_row.grid(row=2, column=0, sticky="ew", padx=6, pady=(8, 0))
        for i in range(4):
            self.stats_row.grid_columnconfigure(i, weight=1)
        self.stat_groups = StatTile(self.stats_row, tr("similar.tile_groups"))
        self.stat_photos = StatTile(self.stats_row, tr("similar.tile_photos"))
        self.stat_move = StatTile(self.stats_row, tr("similar.tile_to_move"))
        self.stat_space = StatTile(self.stats_row, tr("common.tile_recoverable"))
        for i, b in enumerate((self.stat_groups, self.stat_photos,
                               self.stat_move, self.stat_space)):
            b.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 6, 0))

        # Results gallery
        self.gallery = ctk.CTkScrollableFrame(t, fg_color=styles.COLOR_TABLE_BACKGROUND)
        self.gallery.grid(row=4, column=0, sticky="nsew", padx=6, pady=(8, 0))
        self.gallery.grid_columnconfigure(0, weight=1)

        self.empty_state = EmptyState(
            t, icons.CAT_IMAGES, tr("similar.not_analyzed_title"),
            tr("similar.empty_detail"))
        self.empty_state.grid(row=4, column=0, sticky="nsew", padx=6,
                                   pady=(10, 0))

        # Pager (only visible if the groups do not fit in one page)
        self.pager = ctk.CTkFrame(t, fg_color="transparent")
        self.pager.grid(row=5, column=0, sticky="ew", padx=6, pady=(8, 0))
        self.pager.grid_columnconfigure(1, weight=1)
        self.btn_page_prev = ctk.CTkButton(
            self.pager, text=tr("similar.previous"), width=110, fg_color="transparent",
            border_width=1, text_color=styles.COLOR_TEXT,
            command=lambda: self._change_page(-1))
        self.btn_page_prev.grid(row=0, column=0)
        self.lbl_page = ctk.CTkLabel(
            self.pager, text="", font=styles.base_font(12),
            text_color=styles.COLOR_MUTED_TEXT)
        self.lbl_page.grid(row=0, column=1, padx=10)
        self.btn_page_next = ctk.CTkButton(
            self.pager, text=tr("similar.next"), width=110, fg_color="transparent",
            border_width=1, text_color=styles.COLOR_TEXT,
            command=lambda: self._change_page(1))
        self.btn_page_next.grid(row=0, column=2)
        self.pager.grid_remove()

        # Bottom bar
        bar = ctk.CTkFrame(t, fg_color=styles.COLOR_CARD)
        bar.grid(row=6, column=0, sticky="ew", padx=6, pady=(10, 6))
        bar.grid_columnconfigure(0, weight=1)
        self.lbl_totals = ctk.CTkLabel(
            bar, text=tr("similar.not_analyzed"), font=styles.base_font(12),
            text_color=styles.COLOR_MUTED_TEXT, anchor="w")
        self.lbl_totals.grid(row=0, column=0, padx=16, pady=12, sticky="w")
        self.btn_quarantine = ctk.CTkButton(
            bar, text=f"{icons.SHIELD}  {tr("common.move_quarantine")}", width=200,
            height=36, font=styles.base_font(13, "bold"),
            fg_color=styles.COLOR_OK_BUTTON, hover_color="#26734d",
            command=self._move_to_quarantine)
        self.btn_quarantine.grid(row=0, column=1, padx=(4, 16), pady=12)

    # -- state --------------------------------------------------------
    def _initial_state(self):
        self.progress_bar.set(0)
        self.lbl_state.configure(text="")
        self.progress_area.grid_remove()
        self.stats_row.grid_remove()
        styles.action_button(self.btn_quarantine, False)
        self._show_gallery(False)

    def _sensitivity_changed(self, value):
        v = int(round(value))
        label = tr("similar.very_strict" if v <= 5 else "similar.strict" if v <= 8
                   else "similar.normal" if v <= 11 else "similar.tolerant" if v <= 15
                   else "similar.very_tolerant")
        self.lbl_sensitivity.configure(text=tr("similar.sensitivity_label", label=label))

    def _set_analyzing(self, active):
        styles.activate_button(self.btn_choose, not active)
        self.entry_folder.configure(state="disabled" if active else "normal")
        if active:
            self.btn_analyze.configure(
                text=f"{icons.CROSS}  {tr("common.cancel")}", command=self._cancel_analysis,
                state="normal", fg_color=styles.COLOR_DANGER_BUTTON,
                hover_color=("#9c2f24", "#8f2b22"), text_color="#ffffff")
        else:
            styles.activate_button(self.btn_analyze, True)
            self.btn_analyze.configure(
                text=f"{icons.CAT_IMAGES}  {tr("similar.analyze")}",
                command=self._start)

    # -- actions ---------------------------------------------------
    def _choose_folder(self):
        folder = filedialog.askdirectory(title=tr("similar.pick_folder"))
        if folder:
            self.entry_folder.delete(0, "end")
            self.entry_folder.insert(0, os.path.normpath(folder))

    def _start(self):
        folder = self.entry_folder.get().strip()
        if not folder or not os.path.isdir(folder):
            messagebox.showwarning(
                tr("common.invalid_folder_title"),
                tr("similar.invalid_folder_msg"))
            return

        threshold = int(round(self.sensitivity_slider.get()))
        self._folder = folder
        self._result = None
        self._selection = None
        self._thumbs = {}
        self._cancel.clear()
        clear_cache()
        self._clear_gallery()

        self.progress_area.grid()
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start()
        self.lbl_state.configure(text=tr("similar.finding_images"))
        self.lbl_totals.configure(text=tr("similar.analyzing"))
        self.stats_row.grid_remove()
        styles.action_button(self.btn_quarantine, False)
        self.empty_state.configure(
            title=tr("similar.analyzing"), detail=tr("similar.comparing_detail"))
        self._show_gallery(False)
        self._set_analyzing(True)

        self._job.start(
            lambda report: self._analyze(folder, threshold, report),
            what=f"Similar-photo analysis of {folder}")

    def _cancel_analysis(self):
        self._cancel.set()
        self.lbl_state.configure(text=tr("common.cancelling"))
        self.btn_analyze.configure(state="disabled")

    def _analyze(self, folder, threshold, report):
        """Runs in the background: finds the similar photos and makes their thumbnails."""
        res = self._services.find_similar_photos(
            folder, hamming_threshold=threshold,
            progress=lambda a, t, m: report((a, t, m)),
            cancelled=self._cancel.is_set)

        thumbs = {}
        total = res.total_photos_in_groups
        processed_count = 0
        for g in res.groups:
            for h in g.fingerprints:
                if self._cancel.is_set():
                    raise ComparisonCancelled()
                processed_count += 1
                if processed_count % 4 == 0 or processed_count == total:
                    report((processed_count, total,
                            tr("similar.loading_thumbnails", processed_count=processed_count,
                               total=total)))
                try:
                    thumbs[h.path] = load_thumbnail(h.path)
                except Exception as e:  # a broken file must not stop the gallery
                    log.info("Could not create the thumbnail of %s: %s", h.path, e)
                    thumbs[h.path] = None
        return res, thumbs

    def _apply_progress(self, progress):
        current, total, message = progress
        self.lbl_state.configure(text=message)
        if total:
            if self.progress_bar.cget("mode") != "determinate":
                self.progress_bar.stop()
                self.progress_bar.configure(mode="determinate")
            self.progress_bar.set(min(current / total, 1.0))

    def _finished(self, res, thumbs):
        self._result = res
        self._thumbs = thumbs
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(1.0)
        self._set_analyzing(False)
        self.btn_analyze.configure(state="normal")

        extra = (tr("similar.unreadable_suffix", count=len(res.errors))
                 if res.errors else "")

        if res.total_groups == 0:
            self.stats_row.grid_remove()
            self.lbl_state.configure(text=tr("similar.none_found"))
            self.lbl_totals.configure(
                text=tr("similar.totals_none", total_images=res.total_images, extra=extra))
            self.empty_state.configure(
                title=tr("similar.none_found_title"),
                detail=tr("similar.none_found_detail", total_images=res.total_images))
            self._show_gallery(False)
            return

        # Preselection: in each group the "best" copy is kept (the
        # first one, which perceptual sorts by resolution). The user
        # changes it with one click if they disagree.
        self._selection = self._services.start_selection(res)
        for gi, g in enumerate(res.groups):
            self._selection.keep_only(gi, g.files[0].path)

        self.stats_row.grid()
        self.stat_groups.set(res.total_groups)
        self.stat_photos.set(res.total_photos_in_groups)
        self.lbl_state.configure(
            text=tr("similar.finished", extra=extra))
        self._build_gallery()
        self._show_gallery(True)
        self._on_selection_change()

    def _cancelled(self):
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(0)
        self.lbl_state.configure(text=tr("similar.cancelled"))
        self.lbl_totals.configure(text=tr("similar.cancelled"))
        self._set_analyzing(False)
        self.btn_analyze.configure(state="normal")
        self.empty_state.configure(
            title=tr("similar.cancelled_title"),
            detail=tr("similar.cancelled_detail"))
        self._show_gallery(False)

    def _error(self, e):
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(0)
        self.lbl_state.configure(text=tr("similar.failed"))
        self.lbl_totals.configure(text=tr("similar.failed"))
        self._set_analyzing(False)
        self.btn_analyze.configure(state="normal")
        messagebox.showerror(tr("similar.error_title"),
                             tr("similar.error_detail", name=type(e).__name__, e=e))

    # -- gallery ---------------------------------------------------
    def _show_gallery(self, show):
        """Toggles gallery / empty-state message (same spot)."""
        if show:
            self.empty_state.grid_remove()
            self.gallery.grid()
        else:
            self.gallery.grid_remove()
            self.empty_state.grid()

    def _clear_gallery(self):
        for child in self.gallery.winfo_children():
            child.destroy()
        self._img_cache.clear()
        self._tiles = {}   # (gi, path) -> frame of the tile
        self._buttons = {}      # (gi, path) -> keep/move button
        self._pages = []
        self._page = 0
        self.pager.grid_remove()

    def _build_gallery(self):
        self._clear_gallery()
        self._pages = split_into_pages(
            [g.count for g in self._result.groups])
        self._show_page(0)

    def _change_page(self, step):
        new = self._page + step
        if 0 <= new < len(self._pages):
            self._show_page(new)

    def _show_page(self, page):
        """Draws the groups of one page (those of the other pages do not exist as widgets)."""
        for child in self.gallery.winfo_children():
            child.destroy()
        self._img_cache.clear()
        self._tiles = {}
        self._buttons = {}
        self._page = page
        first, end = self._pages[page]

        for gi in range(first, end):
            g = self._result.groups[gi]
            card = ctk.CTkFrame(self.gallery, fg_color=styles.COLOR_CARD)
            card.grid(row=gi - first, column=0, sticky="ew", pady=(0, 10))
            card.grid_columnconfigure(0, weight=1)

            header = ctk.CTkLabel(
                card, anchor="w", font=styles.base_font(12, "bold"),
                text=tr("similar.group_title", number=gi + 1, count=g.count,
                        size=format_size(g.reclaimable_space)))
            header.grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))

            strips = ctk.CTkFrame(card, fg_color="transparent")
            strips.grid(row=1, column=0, sticky="w", padx=8, pady=(0, 10))

            for j, (h, sim) in enumerate(zip(g.fingerprints, g.similarity)):
                self._photo_tile(strips, gi, j, h, sim)
            self._refresh_group(gi)

        self.gallery._parent_canvas.yview_moveto(0)
        if len(self._pages) > 1:
            total = len(self._result.groups)
            self.lbl_page.configure(
                text=tr("similar.page_label", page=page + 1, pages=len(self._pages),
                        first=first + 1, end=end, total=total))
            styles.activate_button(self.btn_page_prev, page > 0, fg="transparent")
            styles.activate_button(self.btn_page_next, page < len(self._pages) - 1,
                                 fg="transparent")
            self.pager.grid()
        else:
            self.pager.grid_remove()

    def _photo_tile(self, parent, gi, j, fingerprint, sim):
        tile = ctk.CTkFrame(parent, fg_color=styles.COLOR_TILE, corner_radius=8,
                            border_width=2)
        tile.grid(row=j // COLUMNS, column=j % COLUMNS, padx=6, pady=4, sticky="n")
        self._tiles[(gi, fingerprint.path)] = tile

        pil = self._thumbs.get(fingerprint.path)
        if pil is not None:
            img = ctk.CTkImage(light_image=pil, dark_image=pil,
                               size=(pil.width, pil.height))
            self._img_cache.append(img)
            lbl_img = ctk.CTkLabel(tile, image=img, text="")
        else:
            lbl_img = ctk.CTkLabel(tile, text=tr("similar.no_preview"),
                                   width=150, height=150,
                                   text_color=styles.COLOR_MUTED_TEXT)
        lbl_img.grid(row=0, column=0, padx=6, pady=(6, 4))
        lbl_img.configure(cursor="hand2")
        lbl_img.bind("<Button-1>", lambda _e, r=fingerprint.path:
                     open_viewer(self.winfo_toplevel(), r))

        ctk.CTkLabel(tile, text=Path(fingerprint.path).name, font=styles.base_font(10),
                     wraplength=150, justify="left", anchor="w").grid(
            row=1, column=0, padx=6, sticky="w")
        ctk.CTkLabel(
            tile, text=f"{fingerprint.width}×{fingerprint.height}  ·  "
                       f"{format_size(fingerprint.size)}",
            font=styles.base_font(10), text_color=styles.COLOR_MUTED_TEXT).grid(
            row=2, column=0, padx=6, sticky="w")
        similarity_label = tr("similar.best_quality") if j == 0 else tr("similar.similarity",
                                                                        percent=sim * 100)
        ctk.CTkLabel(tile, text=similarity_label, font=styles.base_font(10),
                     text_color=styles.COLOR_MUTED_TEXT).grid(
            row=3, column=0, padx=6, sticky="w")

        button = ctk.CTkButton(
            tile, width=120, height=26, font=styles.base_font(11),
            command=lambda g=gi, r=fingerprint.path: self._choose_keep(g, r))
        button.grid(row=4, column=0, padx=6, pady=(4, 8))
        self._buttons[(gi, fingerprint.path)] = button

    def _paint_tile(self, gi, path):
        dec = self._selection.decision(gi, path)
        tile = self._tiles.get((gi, path))
        button = self._buttons.get((gi, path))
        if tile is None or button is None:
            return
        if dec == _KEEP:
            # It is the one being kept: green button and no action (it already is).
            tile.configure(border_color=styles.COLOR_OK)
            button.configure(text=f"{icons.OK}  {tr("similar.kept")}", state="disabled",
                            fg_color=styles.COLOR_OK_BUTTON,
                            text_color_disabled="#ffffff")  # readable, not "broken"
        else:
            tile.configure(border_color=styles.COLOR_WARNING)
            button.configure(text=tr("similar.keep_this"), state="normal",
                            fg_color="transparent", border_width=1,
                            text_color=styles.COLOR_TEXT,
                            hover_color=styles.COLOR_TILE)

    def _refresh_group(self, gi):
        for h in self._result.groups[gi].fingerprints:
            self._paint_tile(gi, h.path)

    def _choose_keep(self, gi, path):
        self._selection.keep_only(gi, path)
        self._refresh_group(gi)
        self._on_selection_change()

    def _on_selection_change(self):
        if self._selection is None:
            return
        # repaint the groups of the page being viewed
        if self._pages:
            for gi in range(*self._pages[self._page]):
                self._refresh_group(gi)

        pending = self._selection.pending_groups()
        to_move = self._selection.count_to_move()
        free = self._selection.space_to_free()
        self.stat_move.set(to_move)
        self.stat_space.set(format_size(free),
                                  color=styles.COLOR_OK if free else None)

        if pending:
            self.lbl_totals.configure(
                text=f"{icons.WARNING}  {tr("similar.too_many_kept", count=len(pending))}")
            styles.action_button(self.btn_quarantine, False)
        else:
            self.lbl_totals.configure(
                text=f"{icons.OK}  {tr("similar.ready", to_move=to_move, size=format_size(free))}")
            styles.action_button(self.btn_quarantine, bool(to_move))

    def _move_to_quarantine(self):
        if self._selection is None or not self._selection.all_ready():
            return
        if self._selection.count_to_move() == 0:
            return
        root = self._folder
        destination = choose_quarantine_folder(root)
        if not destination:
            return

        n = self._selection.count_to_move()
        frees = format_size(self._selection.space_to_free())
        if not messagebox.askyesno(
            tr("common.confirm_title"),
            tr("similar.confirm_msg", n=n, frees=frees, destination=destination)):
            return

        try:
            res = self._services.move_to_quarantine(
                self._selection, root, destination,
                description_key="history.description_similar")
        except Exception as e:  # it is logged and shown to the user
            log.exception("Move of similar photos to quarantine failed")
            messagebox.showerror(tr("common.move_error_title"), tr("similar.error_detail",
                                                                   name=type(e).__name__, e=e))
            return

        self._result = None
        self._selection = None
        self._clear_gallery()
        self.stats_row.grid_remove()
        styles.action_button(self.btn_quarantine, False)
        self.lbl_totals.configure(
            text=tr("similar.moved_totals", count=len(res.moved)))
        self.empty_state.configure(
            title=tr("similar.moved_title"),
            detail=tr("similar.moved_detail", count=len(res.moved)))
        self._show_gallery(False)
        detail = tr("similar.moved_summary", count=len(res.moved))
        if res.log_path:
            detail += tr("common.log_note", log_path=res.log_path)
        offer_to_open_folder(detail + tr("similar.open_quarantine_question"), destination)
