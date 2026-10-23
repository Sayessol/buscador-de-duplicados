"""Tabla de resultados del escaneo de duplicados exactos.

Cada grupo es un nodo padre desplegable; cada archivo del grupo es un
hijo con su miniatura (imagen real o un recuadro con la extensión).

Interacción con una fila de archivo:
  * un clic normal        -> la selecciona (la ventana muestra la vista grande)
  * clic en "Decisión"    -> alterna conservar / mover de ese archivo
  * doble clic            -> deja ese archivo como la única copia a conservar

La tabla no decide nada por su cuenta: lee y escribe sobre una
`DuplicateSelection` que le pasa la ventana principal.
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

        self._img_refs = {}          # iid -> ImageTk.PhotoImage (hay que guardarlas)
        self._thumbs_queue = queue.Queue()
        self._gen = 0                # generación: descarta miniaturas de escaneos viejos

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._configure_ttk_style()

        self.tree = ttk.Treeview(
            self, columns=("decision", "tamano", "info"),
            selectmode="browse", style="Duplicados.Treeview")
        self.tree.heading("#0", text="Grupo / Archivo", anchor="w")
        self.tree.heading("decision", text="Decisión", anchor="w")
        self.tree.heading("tamano", text="Tamaño", anchor="e")
        self.tree.heading("info", text="", anchor="w")

        self.tree.column("#0", width=520, minwidth=260, stretch=True, anchor="w")
        self.tree.column("decision", width=140, minwidth=110, stretch=False,
                         anchor="w")
        self.tree.column("tamano", width=100, minwidth=80, stretch=False,
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

    # -- estilo ttk: se re-aplica cuando cambia el tema claro/oscuro ----
    def _configure_ttk_style(self):
        # ttk.Treeview NO cambia solo con el tema de CustomTkinter, así que
        # aquí se resuelve cada color con styles.col(...) para el tema activo.
        c = styles.col
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Duplicados.Treeview",
            background=c(styles.COLOR_TABLE_BACKGROUND),
            fieldbackground=c(styles.COLOR_TABLE_BACKGROUND),
            foreground=c(styles.COLOR_TEXT),
            rowheight=_ROW_HEIGHT, font=styles.table_font(), borderwidth=0)
        style.configure(
            "Duplicados.Treeview.Heading",
            background=c(styles.COLOR_HEADER), foreground=c(styles.COLOR_TEXT),
            font=styles.table_heading_font(), relief="flat")
        style.map("Duplicados.Treeview.Heading",
                   background=[("active", c(styles.COLOR_HEADER))])
        style.map("Duplicados.Treeview",
                   background=[("selected", c(styles.COLOR_SELECTION))],
                   foreground=[("selected", "#ffffff")])

    def _configure_tags(self):
        c = styles.col
        self.tree.tag_configure("grupo", background=c(styles.COLOR_TABLE_BACKGROUND),
                                foreground=c(styles.COLOR_TEXT),
                                font=styles.table_heading_font())
        self.tree.tag_configure("grupo_pendiente",
                                background=c(styles.COLOR_PENDING_GROUP),
                                foreground=c(styles.COLOR_TEXT),
                                font=styles.table_heading_font())
        self.tree.tag_configure("conservar", foreground=c(styles.COLOR_OK))
        self.tree.tag_configure("mover", foreground=c(styles.COLOR_WARNING))

    def _set_appearance_mode(self, mode_string):
        super()._set_appearance_mode(mode_string)
        # el tema ha cambiado: re-pintar lo que ttk no actualiza solo
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
            self._meta[group_id] = ("grupo", gi)
            self._group_iid[gi] = group_id

            for file in group.files:
                iid = self.tree.insert(
                    group_id, "end", text="  " + file.path,
                    values=("", format_size(file.size), ""))
                self._meta[iid] = ("archivo", gi, file.path)
                self._file_iids[(gi, file.path)] = iid
                pending_thumb.append((iid, file.path))

            self._refresh_group(gi)

        self._load_thumbnails(pending_thumb)

    # -- miniaturas en un hilo aparte ------------------------------
    # Decodificar imágenes es lento, así que se hace en un hilo. El hilo
    # solo produce objetos PIL; convertirlos a ImageTk.PhotoImage y
    # pegarlos en las filas se hace en el hilo principal (Tkinter).
    # `self._gen` sube en cada limpiar(): si el usuario reescanea, las
    # miniaturas a medio hacer del escaneo viejo se descartan.
    def _load_thumbnails(self, items):
        gen = self._gen

        def job():
            for iid, path in items:
                if gen != self._gen:        # llegó otro escaneo: abandonar
                    return
                try:
                    pil = thumbnail_or_placeholder(path, _MINI_SIDE)
                except Exception as e:  # un archivo roto no debe parar las miniaturas
                    log.info("No se pudo crear la miniatura de %s: %s", path, e)
                    pil = None
                self._thumbs_queue.put((gen, iid, pil))

        threading.Thread(target=job, daemon=True).start()
        self.after(80, self._process_thumbs_queue)

    def _process_thumbs_queue(self):
        processed = 0
        try:
            while processed < 40:          # como mucho 40 por tick, para no atascar
                gen, iid, pil = self._thumbs_queue.get_nowait()
                processed += 1
                if gen != self._gen or pil is None:
                    continue
                if not self.tree.exists(iid):   # la fila ya no existe
                    continue
                photo = ImageTk.PhotoImage(pil)
                self._img_refs[iid] = photo      # ¡hay que guardar la referencia!
                self.tree.item(iid, image=photo)  # si no, Python la recolecta y desaparece
        except queue.Empty:
            return
        self.after(60, self._process_thumbs_queue)

    # ------------------------------------------------------------------
    def _refresh_group(self, gi):
        if self.selection is None:
            return
        state = self.selection.group_state(gi)
        group_id = self._group_iid[gi]
        tag_group = "grupo" if state == GROUP_OK else "grupo_pendiente"
        mark = "OK" if state == GROUP_OK else "!"
        vals = list(self.tree.item(group_id, "values"))
        vals[0] = f"{mark}  {_STATE_LABEL[state]}"
        self.tree.item(group_id, values=vals, tags=(tag_group,))

        for file in self.selection.result.groups[gi].files:
            iid = self._file_iids[(gi, file.path)]
            decision = self.selection.decision(gi, file.path)
            vals = list(self.tree.item(iid, "values"))
            if decision == KEEP:
                vals[0], tag = "✔ conservar", "conservar"
            else:
                vals[0], tag = "→ mover", "mover"
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
    # Gestión de clics. En la tabla (ttk.Treeview) hay que preguntarle a
    # Tk QUÉ hay bajo el ratón: identify_row (qué fila), identify_column
    # (qué columna: "#1" es "Decisión"), identify_region ("heading",
    # "cell"...). Con eso decidimos qué hacer.
    def _file_row(self, event):
        """(indice_grupo, ruta) si el ratón está sobre una fila de
        archivo; None si está sobre una cabecera de grupo o fuera."""
        iid = self.tree.identify_row(event.y)
        if not iid:
            return None
        meta = self._meta.get(iid)
        if not meta or meta[0] != "archivo":
            return None
        return meta[1], meta[2]

    def _on_click(self, event):
        if self.tree.identify_region(event.x, event.y) == "heading":
            return
        target = self._file_row(event)
        if target is None:
            return
        # Un clic normal solo SELECCIONA (para la vista previa). Únicamente
        # si cae en la columna "Decisión" alterna conservar/mover.
        if self.tree.identify_column(event.x) == "#1":
            gi, path = target
            self.selection.toggle(gi, path)
            self._refresh_group(gi)
            if self.on_change:
                self.on_change()

    def _on_double_click(self, event):
        # Doble clic = "quiero conservar ESTA copia" (y mover el resto).
        target = self._file_row(event)
        if target is None:
            return None
        gi, path = target
        self.selection.keep_only(gi, path)
        self._refresh_group(gi)
        if self.on_change:
            self.on_change()
        return "break"       # evita que Tk además expanda/colapse el nodo

    def _on_selection(self, _event):
        if not self.on_selection:
            return
        sel = self.tree.selection()
        if not sel:
            self.on_selection(None)
            return
        meta = self._meta.get(sel[0])
        self.on_selection(meta[2] if meta and meta[0] == "archivo" else None)

    def expand_all(self, open=True):
        for iid in self._group_iid.values():
            self.tree.item(iid, open=open)
