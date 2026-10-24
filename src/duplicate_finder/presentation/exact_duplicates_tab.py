""""Exact duplicates" tab: scans a folder and decides which copy to keep.

It is a component with its OWN state (scan result, selection, queues, threads...):
the main window only creates it, notifies it of the Simple / Advanced mode and that it is closing.
"""

import logging
import os
import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk

from duplicate_finder.application.scan_duplicates import ScanCancelled
from duplicate_finder.application.services import Services
from duplicate_finder.domain.formatting import format_size
from .dialogs import choose_quarantine_folder, offer_to_open_folder
from . import styles
from . import icons
from .widgets import SectionHeader, StatTile, EmptyState, make_card
from .background_job import BackgroundJob
from .preview_panel import PreviewPanel
from .results_table import ResultsTable
from .scan_options_panel import ScanOptionsPanel
from .thumbnails import clear_cache
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
        self._cancel_event = threading.Event()
        self._result = None
        self._selection = None
        self._scanned_folder = None
        self._quarantine_folder = None
        self._excl_text = ""

        self._scan_job = BackgroundJob(
            self.after, self._apply_progress, self._finish_scan, self._scan_failed,
            self._scan_cancelled, cancelled_exceptions=(ScanCancelled,))
        self._quarantine_job = BackgroundJob(
            self.after, self._apply_quarantine_progress, self._quarantine_finished,
            self._quarantine_failed)

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
        for w in (self.options, self.decision_card_header,
                  self.decision_card_row, self.btn_kinds, self.btn_export):
            (w.grid if advanced else w.grid_remove)()
        if not advanced:
            self.options.collapse()      # collapse the panel if it was open

    def on_switch_to_simple(self):
        """If there are already results and the user goes back to Simple,
        the app decides by itself again."""
        if self._selection is not None:
            self._selection.preselect_primary()
            self.table.refresh_all()
            self._on_selection_change()

    def cancel_jobs(self):
        """Called by the window when it closes: if a scan is running, it is cancelled."""
        if self._scan_job.running:
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
        self.options = ScanOptionsPanel(self)
        self.options.grid(row=2, column=0, sticky="ew", padx=6, pady=(6, 0))

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
            on_selection=lambda path: self.preview.show(path))
        self.table.grid(row=0, column=0, sticky="nsew")

        self.empty_state = EmptyState(
            self.table_area, icons.SEARCH,
            tr("exact.empty_title"),
            tr("exact.empty_detail"))
        self.empty_state.grid(row=0, column=0, sticky="nsew")

        # Preview panel on the right.
        self.preview = PreviewPanel(self.table_wrap)
        self.preview.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

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

        filter = self.options.current_filter()

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

        self._launch_scan(folder, filter)

    def _launch_scan(self, folder, filter):
        """Starts the scan in the background (see BackgroundJob): the window stays alive and the
        scan can be cancelled halfway."""
        self._scan_job.start(
            lambda report: self._services.scan_duplicates(
                folder, progress=report, cancelled=self._cancel_event.is_set, filter=filter),
            what=f"Scan of {folder}")

    def _cancel_scan(self):
        # The thread checks this event between one file and the next.
        self._cancel_event.set()
        self.lbl_state.configure(text=tr("common.cancelling"))
        self.btn_scan.configure(state="disabled")

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
        quarantine_folder = choose_quarantine_folder(root)
        if not quarantine_folder:
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

        self._quarantine_folder = quarantine_folder
        selection = self._selection
        self._quarantine_job.start(
            lambda report: self._services.move_to_quarantine(
                selection, root, quarantine_folder,
                progress=lambda current, total, message: report((current, total, message))),
            what=f"Move to quarantine from {root} to {quarantine_folder}")

    def _set_quarantine_busy(self, busy):
        active = not busy
        for btn in (self.btn_scan, self.btn_rule, self.btn_choose,
                    self.btn_choose_preferred):
            styles.activate_button(btn, active)
        for btn in (self.btn_export, self.btn_kinds):
            styles.activate_button(btn, active, fg="transparent",
                                 hover=styles.COLOR_TILE)
        styles.action_button(self.btn_quarantine, active)

    def _apply_quarantine_progress(self, progress):
        current, total, message = progress
        self.lbl_state.configure(text=message)
        if total:
            self.progress_bar.set(min(current / total, 1.0))

    def _quarantine_failed(self, e):
        self._set_quarantine_busy(False)
        self.lbl_state.configure(text=tr("exact.move_failed"))
        messagebox.showerror(
            tr("common.move_error_title"),
            tr("common.error_detail", name=type(e).__name__, datum=e))

    def _quarantine_finished(self, res):
        quarantine_folder = self._quarantine_folder
        self._set_quarantine_busy(False)
        self.progress_bar.set(1.0)
        self.lbl_state.configure(text=tr("exact.move_done"))

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

        offer_to_open_folder(detail + tr("exact.open_quarantine_question"), quarantine_folder)

    def _show_kinds(self):
        if not self._result or self._result.total_groups == 0:
            return
        ExtensionBreakdownWindow(
            self.winfo_toplevel(), self._result, self.options.exclude_extension)

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
