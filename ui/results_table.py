"""Results table of the exact-duplicates scan.

Each group is an expandable parent node; each file of the group is a
child with its thumbnail (a real image or a box with the extension).

Interaction with a file row:
  * a normal click        -> selects it (the window shows the large preview)
  * click on "Decision"   -> toggles keep / move for that file
  * double click          -> leaves that file as the only copy to keep

The table decides nothing by itself: it reads and writes on a
`DuplicateSelection` handed to it by the main window.
"""

import queue
import threading
import tkinter as tk
from tkinter import ttk

import customtkinter as ctk
from PIL import ImageTk

from core.hashing import format_size
from core.app_logging import log
from core.selection import (
    DuplicateSelection, KEEP,
    GROUP_OK, GROUP_NOTHING_KEPT, GROUP_MULTIPLE,
)
from . import styles
from .thumbnails import thumbnail_or_placeholder

_STATE_LABEL = {
    GROUP_OK: "listo",
    GROUP_NOTHING_KEPT: "elige cuál conservar",
    GROUP_MULTIPLE: "elige cuál conservar",
}

_ROW_HEIGHT = 48
_MINI_SIDE = 40


class ResultsTable(ctk.CTkFrame):
    def __init__(self, master, on_change=None, on_selection=None, **kwargs):
        super().__init__(master, **kwargs)
        self.on_change = on_change
        self.on_selection = on_selection
        self.selection = None

        self._meta = {}
        self._group_iid = {}
        self._file_iids = {}

        self._img_refs = {}          # iid -> ImageTk.PhotoImage (they must be kept)
        self._thumbs_queue = queue.Queue()
        self._gen = 0                # generation: discards thumbnails from old scans

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._configure_ttk_style()

        self.tree = ttk.Treeview(
            self, columns=("decision", "size", "info"),
            selectmode="browse", style="Duplicates.Treeview")
        self.tree.heading("#0", text="Grupo / Archivo", anchor="w")
        self.tree.heading("decision", text="Decisión", anchor="w")
        self.tree.heading("size", text="Tamaño", anchor="e")
        self.tree.heading("info", text="", anchor="w")

        self.tree.column("#0", width=520, minwidth=260, stretch=True, anchor="w")
        self.tree.column("decision", width=140, minwidth=110, stretch=False,
                         anchor="w")
        self.tree.column("size", width=100, minwidth=80, stretch=False,
                         anchor="e")
        self.tree.column("info", width=150, minwidth=100, stretch=False,
                         anchor="w")

        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self._configure_tags()

        self.tree.bind("<Button-1>", self._on_click)
        self.tree.bind("<Double-Button-1>", self._on_double_click)
        self.tree.bind("<<TreeviewSelect>>", self._on_selection)

    # -- ttk style: re-applied when the light/dark theme changes ----
    def _configure_ttk_style(self):
        # ttk.Treeview does NOT change by itself with the CustomTkinter theme, so
        # here each colour is resolved with styles.col(...) for the active theme.
        c = styles.col
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Duplicates.Treeview",
            background=c(styles.COLOR_TABLE_BACKGROUND),
            fieldbackground=c(styles.COLOR_TABLE_BACKGROUND),
            foreground=c(styles.COLOR_TEXT),
            rowheight=_ROW_HEIGHT, font=styles.table_font(), borderwidth=0)
        style.configure(
            "Duplicates.Treeview.Heading",
            background=c(styles.COLOR_HEADER), foreground=c(styles.COLOR_TEXT),
            font=styles.table_heading_font(), relief="flat")
        style.map("Duplicates.Treeview.Heading",
                   background=[("active", c(styles.COLOR_HEADER))])
        style.map("Duplicates.Treeview",
                   background=[("selected", c(styles.COLOR_SELECTION))],
                   foreground=[("selected", "#ffffff")])

    def _configure_tags(self):
        c = styles.col
        self.tree.tag_configure("group", background=c(styles.COLOR_TABLE_BACKGROUND),
                                foreground=c(styles.COLOR_TEXT),
                                font=styles.table_heading_font())
        self.tree.tag_configure("group_pending",
                                background=c(styles.COLOR_PENDING_GROUP),
                                foreground=c(styles.COLOR_TEXT),
                                font=styles.table_heading_font())
        self.tree.tag_configure("keep", foreground=c(styles.COLOR_OK))
        self.tree.tag_configure("move", foreground=c(styles.COLOR_WARNING))

    def _set_appearance_mode(self, mode_string):
        super()._set_appearance_mode(mode_string)
        # the theme has changed: repaint what ttk does not update by itself
        try:
            self._configure_ttk_style()
            self._configure_tags()
        except tk.TclError:
            pass

    # ------------------------------------------------------------------
    def clear(self):
        self._gen += 1
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self._meta.clear()
        self._group_iid.clear()
        self._file_iids.clear()
        self._img_refs.clear()
        self.selection = None
        if self.on_selection:
            self.on_selection(None)

    def load(self, selection: DuplicateSelection):
        self.clear()
        self.selection = selection
        result = selection.result

        pending_thumb = []
        for gi, group in enumerate(result.groups):
            group_id = self.tree.insert(
                "", "end",
                text=f"Grupo {gi + 1}  ·  {group.count} copias",
                values=("", format_size(group.size),
                        f"libera {format_size(group.reclaimable_space)}"),
                open=True)
            self._meta[group_id] = ("group", gi)
            self._group_iid[gi] = group_id

            for file in group.files:
                iid = self.tree.insert(
                    group_id, "end", text="  " + file.path,
                    values=("", format_size(file.size), ""))
                self._meta[iid] = ("file", gi, file.path)
                self._file_iids[(gi, file.path)] = iid
                pending_thumb.append((iid, file.path))

            self._refresh_group(gi)

        self._load_thumbnails(pending_thumb)

    # -- thumbnails in a separate thread ------------------------------
    # Decoding images is slow, so it is done in a thread. The thread
    # only produces PIL objects; converting them to ImageTk.PhotoImage and
    # pasting them into the rows is done in the main thread (Tkinter).
    # `self._gen` goes up on every clear(): if the user rescans, the
    # half-done thumbnails of the old scan are discarded.
    def _load_thumbnails(self, items):
        gen = self._gen

        def job():
            for iid, path in items:
                if gen != self._gen:        # another scan arrived: give up
                    return
                try:
                    pil = thumbnail_or_placeholder(path, _MINI_SIDE)
                except Exception as e:  # a broken file must not stop the thumbnails
                    log.info("No se pudo crear la miniatura de %s: %s", path, e)
                    pil = None
                self._thumbs_queue.put((gen, iid, pil))

        threading.Thread(target=job, daemon=True).start()
        self.after(80, self._process_thumbs_queue)

    def _process_thumbs_queue(self):
        processed = 0
        try:
            while processed < 40:          # at most 40 per tick, so as not to clog things up
                gen, iid, pil = self._thumbs_queue.get_nowait()
                processed += 1
                if gen != self._gen or pil is None:
                    continue
                if not self.tree.exists(iid):   # the row no longer exists
                    continue
                photo = ImageTk.PhotoImage(pil)
                self._img_refs[iid] = photo      # the reference must be kept!
                self.tree.item(iid, image=photo)  # otherwise Python collects it and it disappears
        except queue.Empty:
            return
        self.after(60, self._process_thumbs_queue)

    # ------------------------------------------------------------------
    def _refresh_group(self, gi):
        if self.selection is None:
            return
        state = self.selection.group_state(gi)
        group_id = self._group_iid[gi]
        tag_group = "group" if state == GROUP_OK else "group_pending"
        mark = "OK" if state == GROUP_OK else "!"
        vals = list(self.tree.item(group_id, "values"))
        vals[0] = f"{mark}  {_STATE_LABEL[state]}"
        self.tree.item(group_id, values=vals, tags=(tag_group,))

        for file in self.selection.result.groups[gi].files:
            iid = self._file_iids[(gi, file.path)]
            decision = self.selection.decision(gi, file.path)
            vals = list(self.tree.item(iid, "values"))
            if decision == KEEP:
                vals[0], tag = "✔ conservar", "keep"
            else:
                vals[0], tag = "→ mover", "move"
            self.tree.item(iid, values=vals, tags=(tag,))

    def refresh_all(self):
        if self.selection is None:
            return
        for gi in range(len(self.selection.result.groups)):
            self._refresh_group(gi)

    def go_to_pending(self):
        if self.selection is None:
            return
        pending = self.selection.pending_groups()
        if not pending:
            return
        iid = self._group_iid[pending[0]]
        self.tree.see(iid)
        self.tree.selection_set(iid)

    # ------------------------------------------------------------------
    # Click handling. In the table (ttk.Treeview) we have to ask
    # Tk WHAT is under the mouse: identify_row (which row), identify_column
    # (which column: "#1" is "Decision"), identify_region ("heading",
    # "cell"...). With that we decide what to do.
    def _file_row(self, event):
        """(group_index, path) if the mouse is over a file row;
        None if it is over a group header or outside."""
        iid = self.tree.identify_row(event.y)
        if not iid:
            return None
        meta = self._meta.get(iid)
        if not meta or meta[0] != "file":
            return None
        return meta[1], meta[2]

    def _on_click(self, event):
        if self.tree.identify_region(event.x, event.y) == "heading":
            return
        target = self._file_row(event)
        if target is None:
            return
        # A normal click only SELECTS (for the preview). Only
        # if it falls on the "Decision" column does it toggle keep/move.
        if self.tree.identify_column(event.x) == "#1":
            gi, path = target
            self.selection.toggle(gi, path)
            self._refresh_group(gi)
            if self.on_change:
                self.on_change()

    def _on_double_click(self, event):
        # Double click = "I want to keep THIS copy" (and move the rest).
        target = self._file_row(event)
        if target is None:
            return None
        gi, path = target
        self.selection.keep_only(gi, path)
        self._refresh_group(gi)
        if self.on_change:
            self.on_change()
        return "break"       # prevents Tk from also expanding/collapsing the node

    def _on_selection(self, _event):
        if not self.on_selection:
            return
        sel = self.tree.selection()
        if not sel:
            self.on_selection(None)
            return
        meta = self._meta.get(sel[0])
        self.on_selection(meta[2] if meta and meta[0] == "file" else None)

    def expand_all(self, open=True):
        for iid in self._group_iid.values():
            self.tree.item(iid, open=open)
