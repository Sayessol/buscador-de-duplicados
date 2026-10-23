"""Pestaña "Fotos parecidas": agrupa la misma foto guardada con distinta calidad.

Es un componente con su PROPIO estado (resultado, selección, colas, hilo, miniaturas...):
la ventana principal solo la crea y le avisa del modo Sencilla / Avanzada.
"""

import os
import queue
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from core.hashing import format_size
from core.app_logging import log
from core.selection import DuplicateSelection, KEEP as _KEEP
from core.quarantine import (
    move_to_quarantine, validate_quarantine_folder, InvalidQuarantine,
)
from core.perceptual import analyze_folder, ComparisonCancelled
from core import history
from . import styles
from . import icons
from .image_viewer import open_viewer
from .widgets import SectionHeader, StatTile, EmptyState, make_card
from .thumbnails import (
    load_thumbnail, clear_cache,
)


# Windows no dibuja ventanas de más de 32.767 px de alto: pasado ese punto la
# galería se corta y la barra de desplazamiento desaparece. Por eso los grupos
# se reparten en páginas cuya altura estimada nunca se acerca a ese límite.
COLUMNS = 5                  # fotos por fila dentro de un grupo
HEADER_HEIGHT = 70            # px que ocupa el título de un grupo y sus márgenes
ROW_HEIGHT = 400               # px de una fila de fotos (cota por arriba)
PAGE_MAX_HEIGHT = 20000       # px estimados por página (límite real: 32.767)
MAX_GROUPS_PER_PAGE = 40        # y nunca más de 40 grupos: la página se dibuja rápido


def split_into_pages(counts):
    """Reparte los grupos en páginas: devuelve una lista de (primero, último + 1).

    `cantidades` es el número de fotos de cada grupo. Todo grupo cabe en alguna
    página (si uno solo supera el presupuesto, ocupa una página para él)."""
    pages = []
    start = 0
    height = 0
    for i, n in enumerate(counts):
        h = HEADER_HEIGHT + ROW_HEIGHT * -(-n // COLUMNS)       # filas = n / 5 redondeado arriba
        if i > start and (height + h > PAGE_MAX_HEIGHT or i - start >= MAX_GROUPS_PER_PAGE):
            pages.append((start, i))
            start, height = i, 0
        height += h
    if counts:
        pages.append((start, len(counts)))
    return pages


class SimilarPhotosTab(ctk.CTkFrame):
    def __init__(self, container):
        """`contenedor` es la pestaña del CTkTabview donde se coloca este componente."""
        super().__init__(container, fg_color="transparent")
        container.grid_columnconfigure(0, weight=1)    # el componente llena toda la pestaña
        container.grid_rowconfigure(0, weight=1)
        self.grid(row=0, column=0, sticky="nsew")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        self._queue = queue.Queue()
        self._thread = None
        self._cancel = threading.Event()
        self._result = None
        self._selection = None
        self._folder = None
        self._thumbs = {}
        self._img_cache = []  # referencias a CTkImage (si no, se recolectan)
        self._tiles = {}
        self._buttons = {}
        self._pages = []    # [(primer grupo, último + 1)] de cada página de la galería
        self._page = 0

        self._build()
        self._initial_state()

    def apply_mode(self, advanced):
        """Lo llama la ventana al cambiar entre Sencilla y Avanzada."""
        (self._sensitivity_row.grid if advanced else self._sensitivity_row.grid_remove)()
        if not advanced:
            self.sensitivity_slider.set(10)
            self._sensitivity_changed(10)

    def cancel_jobs(self):
        """Lo llama la ventana al cerrarse: si hay un análisis en marcha, se cancela."""
        if self._thread and self._thread.is_alive():
            self._cancel.set()

    def _build(self):
        t = self

        card = make_card(t, 0)
        SectionHeader(
            card, 1, "Busca fotos parecidas (no idénticas)",
            icons.CAT_IMAGES).grid(row=0, column=0, sticky="w",
                                     padx=16, pady=(14, 4))
        ctk.CTkLabel(
            card, text="Encuentra la misma foto guardada varias veces: "
                       "recomprimida, en menor resolución o con un filtro de "
                       "color. No detecta recortes ni rotaciones.",
            font=styles.base_font(11), text_color=styles.COLOR_MUTED_TEXT,
            wraplength=980, justify="left", anchor="w").grid(
            row=1, column=0, sticky="w", padx=16, pady=(0, 8))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 8))
        row.grid_columnconfigure(0, weight=1)
        self.entry_folder = ctk.CTkEntry(
            row, height=36, placeholder_text=r"Carpeta con fotos.  Ej.  D:\Fotos")
        self.entry_folder.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.btn_choose = ctk.CTkButton(
            row, text=f"{icons.FOLDER}  Elegir", width=110, height=36,
            command=self._choose_folder)
        self.btn_choose.grid(row=0, column=1, padx=4)
        self.btn_analyze = ctk.CTkButton(
            row, text=f"{icons.CAT_IMAGES}  Analizar", width=130, height=36,
            font=styles.base_font(13, "bold"), command=self._start)
        self.btn_analyze.grid(row=0, column=2, padx=(4, 0))

        sensitivity = ctk.CTkFrame(card, fg_color="transparent")
        self._sensitivity_row = sensitivity
        sensitivity.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 14))
        ctk.CTkLabel(sensitivity, text="Sensibilidad:",
                     font=styles.base_font(12)).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(sensitivity, text="estricta", font=styles.base_font(11),
                     text_color=styles.COLOR_MUTED_TEXT).pack(side="left")
        self.sensitivity_slider = ctk.CTkSlider(
            sensitivity, from_=4, to=18, number_of_steps=14, width=220,
            command=self._sensitivity_changed)
        self.sensitivity_slider.set(10)
        self.sensitivity_slider.pack(side="left", padx=8)
        ctk.CTkLabel(sensitivity, text="tolerante", font=styles.base_font(11),
                     text_color=styles.COLOR_MUTED_TEXT).pack(side="left")
        self.lbl_sensitivity = ctk.CTkLabel(
            sensitivity, text="  (normal)", font=styles.base_font(11),
            text_color=styles.COLOR_MUTED_TEXT)
        self.lbl_sensitivity.pack(side="left", padx=(6, 0))

        # Progreso
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

        # Estadísticas
        self.stats_row = ctk.CTkFrame(t, fg_color="transparent")
        self.stats_row.grid(row=2, column=0, sticky="ew", padx=6, pady=(8, 0))
        for i in range(4):
            self.stats_row.grid_columnconfigure(i, weight=1)
        self.stat_groups = StatTile(self.stats_row, "Grupos de parecidas")
        self.stat_photos = StatTile(self.stats_row, "Fotos en grupos")
        self.stat_move = StatTile(self.stats_row, "Fotos a mover")
        self.stat_space = StatTile(self.stats_row, "Espacio recuperable")
        for i, b in enumerate((self.stat_groups, self.stat_photos,
                               self.stat_move, self.stat_space)):
            b.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 6, 0))

        # Galería de resultados
        self.gallery = ctk.CTkScrollableFrame(t, fg_color=styles.COLOR_TABLE_BACKGROUND)
        self.gallery.grid(row=4, column=0, sticky="nsew", padx=6, pady=(8, 0))
        self.gallery.grid_columnconfigure(0, weight=1)

        self.empty_state = EmptyState(
            t, icons.CAT_IMAGES, "Sin analizar todavía",
            "Elige una carpeta con fotos y pulsa «Analizar». Los grupos de "
            "fotos parecidas aparecerán aquí, con miniatura de cada una.")
        self.empty_state.grid(row=4, column=0, sticky="nsew", padx=6,
                                   pady=(10, 0))

        # Paginador (solo se ve si los grupos no caben en una página)
        self.pager = ctk.CTkFrame(t, fg_color="transparent")
        self.pager.grid(row=5, column=0, sticky="ew", padx=6, pady=(8, 0))
        self.pager.grid_columnconfigure(1, weight=1)
        self.btn_page_prev = ctk.CTkButton(
            self.pager, text="‹  Anterior", width=110, fg_color="transparent",
            border_width=1, text_color=styles.COLOR_TEXT,
            command=lambda: self._change_page(-1))
        self.btn_page_prev.grid(row=0, column=0)
        self.lbl_page = ctk.CTkLabel(
            self.pager, text="", font=styles.base_font(12),
            text_color=styles.COLOR_MUTED_TEXT)
        self.lbl_page.grid(row=0, column=1, padx=10)
        self.btn_page_next = ctk.CTkButton(
            self.pager, text="Siguiente  ›", width=110, fg_color="transparent",
            border_width=1, text_color=styles.COLOR_TEXT,
            command=lambda: self._change_page(1))
        self.btn_page_next.grid(row=0, column=2)
        self.pager.grid_remove()

        # Barra inferior
        bar = ctk.CTkFrame(t, fg_color=styles.COLOR_CARD)
        bar.grid(row=6, column=0, sticky="ew", padx=6, pady=(10, 6))
        bar.grid_columnconfigure(0, weight=1)
        self.lbl_totals = ctk.CTkLabel(
            bar, text="Sin analizar todavía.", font=styles.base_font(12),
            text_color=styles.COLOR_MUTED_TEXT, anchor="w")
        self.lbl_totals.grid(row=0, column=0, padx=16, pady=12, sticky="w")
        self.btn_quarantine = ctk.CTkButton(
            bar, text=f"{icons.SHIELD}  Mover a cuarentena", width=200,
            height=36, font=styles.base_font(13, "bold"),
            fg_color=styles.COLOR_OK_BUTTON, hover_color="#26734d",
            command=self._move_to_quarantine)
        self.btn_quarantine.grid(row=0, column=1, padx=(4, 16), pady=12)

    # -- estado -------------------------------------------------------
    def _initial_state(self):
        self.progress_bar.set(0)
        self.lbl_state.configure(text="")
        self.progress_area.grid_remove()
        self.stats_row.grid_remove()
        styles.action_button(self.btn_quarantine, False)
        self._show_gallery(False)

    def _sensitivity_changed(self, value):
        v = int(round(value))
        label = ("muy estricta" if v <= 5 else "estricta" if v <= 8
                    else "normal" if v <= 11 else "tolerante" if v <= 15
                    else "muy tolerante")
        self.lbl_sensitivity.configure(text=f"  ({label})")

    def _set_analyzing(self, active):
        styles.activate_button(self.btn_choose, not active)
        self.entry_folder.configure(state="disabled" if active else "normal")
        if active:
            self.btn_analyze.configure(
                text=f"{icons.CROSS}  Cancelar", command=self._cancel_analysis,
                state="normal", fg_color=styles.COLOR_DANGER_BUTTON,
                hover_color=("#9c2f24", "#8f2b22"), text_color="#ffffff")
        else:
            styles.activate_button(self.btn_analyze, True)
            self.btn_analyze.configure(
                text=f"{icons.CAT_IMAGES}  Analizar",
                command=self._start)

    # -- acciones ---------------------------------------------------
    def _choose_folder(self):
        folder = filedialog.askdirectory(title="Elige la carpeta con fotos")
        if folder:
            self.entry_folder.delete(0, "end")
            self.entry_folder.insert(0, os.path.normpath(folder))

    def _start(self):
        folder = self.entry_folder.get().strip()
        if not folder or not os.path.isdir(folder):
            messagebox.showwarning(
                "Carpeta no válida",
                "Elige una carpeta con fotos para analizar.")
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
        self.lbl_state.configure(text="Buscando imágenes…")
        self.lbl_totals.configure(text="Analizando…")
        self.stats_row.grid_remove()
        styles.action_button(self.btn_quarantine, False)
        self.empty_state.configure(
            title="Analizando…", detail="Comparando las fotos entre sí.")
        self._show_gallery(False)
        self._set_analyzing(True)

        self._thread = threading.Thread(
            target=self._job, args=(folder, threshold), daemon=True)
        self._thread.start()
        self.after(100, self._poll_queue)

    def _cancel_analysis(self):
        self._cancel.set()
        self.lbl_state.configure(text="Cancelando…")
        self.btn_analyze.configure(state="disabled")

    def _job(self, folder, threshold):
        try:
            res = analyze_folder(
                folder, hamming_threshold=threshold,
                progress=lambda a, t, m: self._queue.put(("progreso", (a, t, m))),
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
                        self._queue.put(("progreso", (
                            processed_count, total,
                            f"Cargando miniaturas… ({processed_count}/{total})")))
                    try:
                        thumbs[h.path] = load_thumbnail(h.path)
                    except Exception as e:  # un archivo roto no debe parar la galería
                        log.info("No se pudo crear la miniatura de %s: %s", h.path, e)
                        thumbs[h.path] = None
            self._queue.put(("hecho", (res, thumbs)))
        except ComparisonCancelled:
            self._queue.put(("cancelado", None))
        except Exception as e:  # se anota en el registro y se muestra al usuario
            log.exception("Falló el análisis de fotos parecidas de %s", folder)
            self._queue.put(("error", e))

    def _poll_queue(self):
        try:
            while True:
                kind, datum = self._queue.get_nowait()
                if kind == "progreso":
                    a, t, m = datum
                    self.lbl_state.configure(text=m)
                    if t:
                        if self.progress_bar.cget("mode") != "determinate":
                            self.progress_bar.stop()
                            self.progress_bar.configure(mode="determinate")
                        self.progress_bar.set(min(a / t, 1.0))
                elif kind == "hecho":
                    self._finished(*datum)
                    return
                elif kind == "cancelado":
                    self._cancelled()
                    return
                elif kind == "error":
                    self._error(datum)
                    return
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _finished(self, res, thumbs):
        self._result = res
        self._thumbs = thumbs
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(1.0)
        self._set_analyzing(False)
        self.btn_analyze.configure(state="normal")

        extra = (f"  ·  {len(res.errors)} imagen(es) ilegibles"
                 if res.errors else "")

        if res.total_groups == 0:
            self.stats_row.grid_remove()
            self.lbl_state.configure(text="No se han encontrado fotos parecidas.")
            self.lbl_totals.configure(
                text=f"{res.total_images} imágenes analizadas{extra} · "
                     f"0 grupos.")
            self.empty_state.configure(
                title="No se han encontrado fotos parecidas",
                detail=f"Se han comparado {res.total_images} imágenes. "
                        f"Prueba a subir la sensibilidad si esperabas más.")
            self._show_gallery(False)
            return

        # Preselección: en cada grupo se conserva la "mejor" copia (la
        # primera, que perceptual ordena por resolución). El usuario lo
        # cambia con un clic si no está de acuerdo.
        self._selection = DuplicateSelection(res)
        for gi, g in enumerate(res.groups):
            self._selection.keep_only(gi, g.files[0].path)

        self.stats_row.grid()
        self.stat_groups.set(res.total_groups)
        self.stat_photos.set(res.total_photos_in_groups)
        self.lbl_state.configure(
            text=f"Análisis terminado.{extra}")
        self._build_gallery()
        self._show_gallery(True)
        self._on_selection_change()

    def _cancelled(self):
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(0)
        self.lbl_state.configure(text="Análisis cancelado.")
        self.lbl_totals.configure(text="Análisis cancelado.")
        self._set_analyzing(False)
        self.btn_analyze.configure(state="normal")
        self.empty_state.configure(
            title="Análisis cancelado",
            detail="Pulsa «Analizar» para intentarlo de nuevo.")
        self._show_gallery(False)

    def _error(self, e):
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(0)
        self.lbl_state.configure(text="El análisis ha fallado.")
        self.lbl_totals.configure(text="El análisis ha fallado.")
        self._set_analyzing(False)
        self.btn_analyze.configure(state="normal")
        messagebox.showerror("Error durante el análisis",
                             f"{type(e).__name__}: {e}")

    # -- galería ---------------------------------------------------
    def _show_gallery(self, show):
        """Alterna galería / mensaje de estado vacío (mismo hueco)."""
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
        self._tiles = {}   # (gi, ruta) -> frame del tile
        self._buttons = {}      # (gi, ruta) -> botón conservar/mover
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
        """Dibuja los grupos de una página (los de las demás no existen como widgets)."""
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
                text=f"Grupo {gi + 1}   ·   {g.count} fotos parecidas   ·   "
                     f"liberas {format_size(g.reclaimable_space)}")
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
                text=f"Página {page + 1} de {len(self._pages)}  ·  "
                     f"grupos {first + 1}–{end} de {total}")
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
            lbl_img = ctk.CTkLabel(tile, text="(sin\nvista previa)",
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
        similarity_label = "mejor calidad" if j == 0 else f"{sim * 100:.0f}% parecida"
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
            # Es la que se conserva: botón en verde y sin acción (ya lo es).
            tile.configure(border_color=styles.COLOR_OK)
            button.configure(text=f"{icons.OK}  Se conserva", state="disabled",
                            fg_color=styles.COLOR_OK_BUTTON,
                            text_color_disabled="#ffffff")  # legible, no "roto"
        else:
            tile.configure(border_color=styles.COLOR_WARNING)
            button.configure(text="Conservar esta", state="normal",
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
        # repintar los grupos de la página que se está viendo
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
                text=f"{icons.WARNING}  {len(pending)} grupo(s) con más de una "
                     f"foto marcada para conservar. Deja solo una en cada grupo.")
            styles.action_button(self.btn_quarantine, False)
        else:
            self.lbl_totals.configure(
                text=f"{icons.OK}  Listo: se moverán {to_move} fotos "
                     f"({format_size(free)}).")
            styles.action_button(self.btn_quarantine, bool(to_move))

    def _move_to_quarantine(self):
        if self._selection is None or not self._selection.all_ready():
            return
        if self._selection.count_to_move() == 0:
            return
        root = self._folder
        destination = filedialog.askdirectory(
            title="Elige (o crea) la carpeta de cuarentena", mustexist=False)
        if not destination:
            return
        destination = os.path.normpath(destination)
        try:
            warning = validate_quarantine_folder(destination, root)
        except InvalidQuarantine as e:
            messagebox.showerror("Carpeta de cuarentena no válida", str(e))
            return
        if warning and not messagebox.askyesno("Atención", warning + "\n\n¿Continuar?"):
            return

        n = self._selection.count_to_move()
        frees = format_size(self._selection.space_to_free())
        if not messagebox.askyesno(
            "Confirmar movimiento a cuarentena",
            f"Se van a MOVER {n} foto(s) ({frees}) a:\n\n{destination}\n\n"
            "Las fotos marcadas para conservar NO se tocan. No se borra nada.\n\n"
            "¿Mover ahora?"):
            return

        try:
            res = move_to_quarantine(self._selection, root, destination)
        except Exception as e:  # se anota en el registro y se muestra al usuario
            log.exception("Falló el movimiento a cuarentena de fotos parecidas")
            messagebox.showerror("Error al mover", f"{type(e).__name__}: {e}")
            return

        if res.moved:
            history.record(
                history.KIND_QUARANTINE, "mover", root, destination,
                [(m.source, m.destination) for m in res.moved],
                f"{len(res.moved)} fotos parecidas")

        self._result = None
        self._selection = None
        self._clear_gallery()
        self.stats_row.grid_remove()
        styles.action_button(self.btn_quarantine, False)
        self.lbl_totals.configure(
            text=f"{len(res.moved)} foto(s) movidas a cuarentena. "
                 f"Vuelve a analizar si quieres continuar.")
        self.empty_state.configure(
            title="Fotos movidas a cuarentena",
            detail=f"Se han movido {len(res.moved)} fotos. "
                    f"Vuelve a analizar para continuar.")
        self._show_gallery(False)
        detail = f"Se han movido {len(res.moved)} fotos."
        if res.log_path:
            detail += f"\n\nRegistro: {res.log_path}"
        if messagebox.askyesno("Hecho",
                               detail + "\n\n¿Abrir la carpeta de cuarentena?"):
            try:
                os.startfile(destination)  # noqa: S606
            except OSError:
                pass
