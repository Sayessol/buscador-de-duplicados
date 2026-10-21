"""Tabla de resultados del escaneo de duplicados exactos.

Cada grupo es un nodo padre desplegable; cada archivo del grupo es un
hijo con su miniatura (imagen real o un recuadro con la extensión).

Interacción con una fila de archivo:
  * un clic normal        -> la selecciona (la ventana muestra la vista grande)
  * clic en "Decisión"    -> alterna conservar / mover de ese archivo
  * doble clic            -> deja ese archivo como la única copia a conservar

La tabla no decide nada por su cuenta: lee y escribe sobre una
`SeleccionDuplicados` que le pasa la ventana principal.
"""

import queue
import threading
import tkinter as tk
from tkinter import ttk

import customtkinter as ctk
from PIL import ImageTk

from core.hashing import formatear_tamano
from core.registro import log
from core.seleccion import (
    SeleccionDuplicados, CONSERVAR,
    GRUPO_OK, GRUPO_SIN_CONSERVAR, GRUPO_MULTIPLE,
)
from . import styles
from .thumbnails import miniatura_o_placeholder

_ETIQUETA_ESTADO = {
    GRUPO_OK: "listo",
    GRUPO_SIN_CONSERVAR: "elige cuál conservar",
    GRUPO_MULTIPLE: "elige cuál conservar",
}

_ALTO_FILA = 48
_LADO_MINI = 40


class TablaResultados(ctk.CTkFrame):
    def __init__(self, master, on_cambio=None, on_seleccion=None, **kwargs):
        super().__init__(master, **kwargs)
        self.on_cambio = on_cambio
        self.on_seleccion = on_seleccion
        self.seleccion = None

        self._meta = {}
        self._iid_grupo = {}
        self._iids_archivo = {}

        self._img_refs = {}          # iid -> ImageTk.PhotoImage (hay que guardarlas)
        self._cola_thumbs = queue.Queue()
        self._gen = 0                # generación: descarta miniaturas de escaneos viejos

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._configurar_estilo_ttk()

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

        self._configurar_tags()

        self.tree.bind("<Button-1>", self._on_click)
        self.tree.bind("<Double-Button-1>", self._on_doble_click)
        self.tree.bind("<<TreeviewSelect>>", self._on_seleccion)

    # -- estilo ttk: se re-aplica cuando cambia el tema claro/oscuro ----
    def _configurar_estilo_ttk(self):
        # ttk.Treeview NO cambia solo con el tema de CustomTkinter, así que
        # aquí se resuelve cada color con styles.col(...) para el tema activo.
        c = styles.col
        estilo = ttk.Style()
        try:
            estilo.theme_use("clam")
        except tk.TclError:
            pass
        estilo.configure(
            "Duplicados.Treeview",
            background=c(styles.COLOR_FONDO_TABLA),
            fieldbackground=c(styles.COLOR_FONDO_TABLA),
            foreground=c(styles.COLOR_TEXTO),
            rowheight=_ALTO_FILA, font=styles.fuente_tabla(), borderwidth=0)
        estilo.configure(
            "Duplicados.Treeview.Heading",
            background=c(styles.COLOR_CABECERA), foreground=c(styles.COLOR_TEXTO),
            font=styles.fuente_tabla_encabezado(), relief="flat")
        estilo.map("Duplicados.Treeview.Heading",
                   background=[("active", c(styles.COLOR_CABECERA))])
        estilo.map("Duplicados.Treeview",
                   background=[("selected", c(styles.COLOR_SELECCION))],
                   foreground=[("selected", "#ffffff")])

    def _configurar_tags(self):
        c = styles.col
        self.tree.tag_configure("grupo", background=c(styles.COLOR_FONDO_TABLA),
                                foreground=c(styles.COLOR_TEXTO),
                                font=styles.fuente_tabla_encabezado())
        self.tree.tag_configure("grupo_pendiente",
                                background=c(styles.COLOR_GRUPO_PENDIENTE),
                                foreground=c(styles.COLOR_TEXTO),
                                font=styles.fuente_tabla_encabezado())
        self.tree.tag_configure("conservar", foreground=c(styles.COLOR_OK))
        self.tree.tag_configure("mover", foreground=c(styles.COLOR_ADVERTENCIA))

    def _set_appearance_mode(self, mode_string):
        super()._set_appearance_mode(mode_string)
        # el tema ha cambiado: re-pintar lo que ttk no actualiza solo
        try:
            self._configurar_estilo_ttk()
            self._configurar_tags()
        except tk.TclError:
            pass

    # ------------------------------------------------------------------
    def limpiar(self):
        self._gen += 1
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self._meta.clear()
        self._iid_grupo.clear()
        self._iids_archivo.clear()
        self._img_refs.clear()
        self.seleccion = None
        if self.on_seleccion:
            self.on_seleccion(None)

    def cargar(self, seleccion: SeleccionDuplicados):
        self.limpiar()
        self.seleccion = seleccion
        resultado = seleccion.resultado

        pendientes_thumb = []
        for gi, grupo in enumerate(resultado.grupos):
            id_grupo = self.tree.insert(
                "", "end",
                text=f"Grupo {gi + 1}  ·  {grupo.cantidad} copias",
                values=("", formatear_tamano(grupo.tamano),
                        f"libera {formatear_tamano(grupo.espacio_recuperable)}"),
                open=True)
            self._meta[id_grupo] = ("grupo", gi)
            self._iid_grupo[gi] = id_grupo

            for archivo in grupo.archivos:
                iid = self.tree.insert(
                    id_grupo, "end", text="  " + archivo.ruta,
                    values=("", formatear_tamano(archivo.tamano), ""))
                self._meta[iid] = ("archivo", gi, archivo.ruta)
                self._iids_archivo[(gi, archivo.ruta)] = iid
                pendientes_thumb.append((iid, archivo.ruta))

            self._refrescar_grupo(gi)

        self._cargar_miniaturas(pendientes_thumb)

    # -- miniaturas en un hilo aparte ------------------------------
    # Decodificar imágenes es lento, así que se hace en un hilo. El hilo
    # solo produce objetos PIL; convertirlos a ImageTk.PhotoImage y
    # pegarlos en las filas se hace en el hilo principal (Tkinter).
    # `self._gen` sube en cada limpiar(): si el usuario reescanea, las
    # miniaturas a medio hacer del escaneo viejo se descartan.
    def _cargar_miniaturas(self, items):
        gen = self._gen

        def trabajo():
            for iid, ruta in items:
                if gen != self._gen:        # llegó otro escaneo: abandonar
                    return
                try:
                    pil = miniatura_o_placeholder(ruta, _LADO_MINI)
                except Exception as e:  # un archivo roto no debe parar las miniaturas
                    log.info("No se pudo crear la miniatura de %s: %s", ruta, e)
                    pil = None
                self._cola_thumbs.put((gen, iid, pil))

        threading.Thread(target=trabajo, daemon=True).start()
        self.after(80, self._procesar_cola_thumbs)

    def _procesar_cola_thumbs(self):
        procesadas = 0
        try:
            while procesadas < 40:          # como mucho 40 por tick, para no atascar
                gen, iid, pil = self._cola_thumbs.get_nowait()
                procesadas += 1
                if gen != self._gen or pil is None:
                    continue
                if not self.tree.exists(iid):   # la fila ya no existe
                    continue
                foto = ImageTk.PhotoImage(pil)
                self._img_refs[iid] = foto      # ¡hay que guardar la referencia!
                self.tree.item(iid, image=foto)  # si no, Python la recolecta y desaparece
        except queue.Empty:
            return
        self.after(60, self._procesar_cola_thumbs)

    # ------------------------------------------------------------------
    def _refrescar_grupo(self, gi):
        if self.seleccion is None:
            return
        estado = self.seleccion.estado_grupo(gi)
        id_grupo = self._iid_grupo[gi]
        tag_grupo = "grupo" if estado == GRUPO_OK else "grupo_pendiente"
        marca = "OK" if estado == GRUPO_OK else "!"
        vals = list(self.tree.item(id_grupo, "values"))
        vals[0] = f"{marca}  {_ETIQUETA_ESTADO[estado]}"
        self.tree.item(id_grupo, values=vals, tags=(tag_grupo,))

        for archivo in self.seleccion.resultado.grupos[gi].archivos:
            iid = self._iids_archivo[(gi, archivo.ruta)]
            decision = self.seleccion.decision(gi, archivo.ruta)
            vals = list(self.tree.item(iid, "values"))
            if decision == CONSERVAR:
                vals[0], tag = "✔ conservar", "conservar"
            else:
                vals[0], tag = "→ mover", "mover"
            self.tree.item(iid, values=vals, tags=(tag,))

    def refrescar_todo(self):
        if self.seleccion is None:
            return
        for gi in range(len(self.seleccion.resultado.grupos)):
            self._refrescar_grupo(gi)

    def ir_a_pendiente(self):
        if self.seleccion is None:
            return
        pend = self.seleccion.grupos_pendientes()
        if not pend:
            return
        iid = self._iid_grupo[pend[0]]
        self.tree.see(iid)
        self.tree.selection_set(iid)

    # ------------------------------------------------------------------
    # Gestión de clics. En la tabla (ttk.Treeview) hay que preguntarle a
    # Tk QUÉ hay bajo el ratón: identify_row (qué fila), identify_column
    # (qué columna: "#1" es "Decisión"), identify_region ("heading",
    # "cell"...). Con eso decidimos qué hacer.
    def _fila_archivo(self, event):
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
        objetivo = self._fila_archivo(event)
        if objetivo is None:
            return
        # Un clic normal solo SELECCIONA (para la vista previa). Únicamente
        # si cae en la columna "Decisión" alterna conservar/mover.
        if self.tree.identify_column(event.x) == "#1":
            gi, ruta = objetivo
            self.seleccion.alternar(gi, ruta)
            self._refrescar_grupo(gi)
            if self.on_cambio:
                self.on_cambio()

    def _on_doble_click(self, event):
        # Doble clic = "quiero conservar ESTA copia" (y mover el resto).
        objetivo = self._fila_archivo(event)
        if objetivo is None:
            return None
        gi, ruta = objetivo
        self.seleccion.conservar_solo(gi, ruta)
        self._refrescar_grupo(gi)
        if self.on_cambio:
            self.on_cambio()
        return "break"       # evita que Tk además expanda/colapse el nodo

    def _on_seleccion(self, _event):
        if not self.on_seleccion:
            return
        sel = self.tree.selection()
        if not sel:
            self.on_seleccion(None)
            return
        meta = self._meta.get(sel[0])
        self.on_seleccion(meta[2] if meta and meta[0] == "archivo" else None)

    def expandir_todo(self, abierto=True):
        for iid in self._iid_grupo.values():
            self.tree.item(iid, open=abierto)
