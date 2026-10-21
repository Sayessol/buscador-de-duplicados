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

from core.hashing import formatear_tamano
from core.registro import log
from core.seleccion import SeleccionDuplicados, CONSERVAR as _CONSERVAR
from core.quarantine import (
    mover_a_cuarentena, validar_carpeta_cuarentena, CuarentenaInvalida,
)
from core.perceptual import analizar_carpeta, ComparacionCancelada
from core import historial
from . import styles
from . import icons
from .image_viewer import abrir_visor
from .widgets import CabeceraSeccion, Baldosa, EstadoVacio, tarjeta
from .thumbnails import (
    cargar_miniatura, limpiar_cache,
)


# Windows no dibuja ventanas de más de 32.767 px de alto: pasado ese punto la
# galería se corta y la barra de desplazamiento desaparece. Por eso los grupos
# se reparten en páginas cuya altura estimada nunca se acerca a ese límite.
COLUMNAS = 5                  # fotos por fila dentro de un grupo
ALTO_CABECERA = 70            # px que ocupa el título de un grupo y sus márgenes
ALTO_FILA = 400               # px de una fila de fotos (cota por arriba)
ALTO_MAX_PAGINA = 20000       # px estimados por página (límite real: 32.767)
GRUPOS_MAX_PAGINA = 40        # y nunca más de 40 grupos: la página se dibuja rápido


def repartir_en_paginas(cantidades):
    """Reparte los grupos en páginas: devuelve una lista de (primero, último + 1).

    `cantidades` es el número de fotos de cada grupo. Todo grupo cabe en alguna
    página (si uno solo supera el presupuesto, ocupa una página para él)."""
    paginas = []
    inicio = 0
    alto = 0
    for i, n in enumerate(cantidades):
        h = ALTO_CABECERA + ALTO_FILA * -(-n // COLUMNAS)       # filas = n / 5 redondeado arriba
        if i > inicio and (alto + h > ALTO_MAX_PAGINA or i - inicio >= GRUPOS_MAX_PAGINA):
            paginas.append((inicio, i))
            inicio, alto = i, 0
        alto += h
    if cantidades:
        paginas.append((inicio, len(cantidades)))
    return paginas


class PestanaParecidas(ctk.CTkFrame):
    def __init__(self, contenedor):
        """`contenedor` es la pestaña del CTkTabview donde se coloca este componente."""
        super().__init__(contenedor, fg_color="transparent")
        contenedor.grid_columnconfigure(0, weight=1)    # el componente llena toda la pestaña
        contenedor.grid_rowconfigure(0, weight=1)
        self.grid(row=0, column=0, sticky="nsew")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        self._cola = queue.Queue()
        self._hilo = None
        self._cancelar = threading.Event()
        self._resultado = None
        self._seleccion = None
        self._carpeta = None
        self._thumbs = {}
        self._img_cache = []  # referencias a CTkImage (si no, se recolectan)
        self._tiles = {}
        self._botones = {}
        self._paginas = []    # [(primer grupo, último + 1)] de cada página de la galería
        self._pagina = 0

        self._construir()
        self._estado_inicial()

    def aplicar_modo(self, avanzado):
        """Lo llama la ventana al cambiar entre Sencilla y Avanzada."""
        (self._sens_row.grid if avanzado else self._sens_row.grid_remove)()
        if not avanzado:
            self.slider_sensibilidad.set(10)
            self._sensibilidad_cambiada(10)

    def cancelar_trabajos(self):
        """Lo llama la ventana al cerrarse: si hay un análisis en marcha, se cancela."""
        if self._hilo and self._hilo.is_alive():
            self._cancelar.set()

    def _construir(self):
        t = self

        card = tarjeta(t, 0)
        CabeceraSeccion(
            card, 1, "Busca fotos parecidas (no idénticas)",
            icons.CAT_IMAGENES).grid(row=0, column=0, sticky="w",
                                     padx=16, pady=(14, 4))
        ctk.CTkLabel(
            card, text="Encuentra la misma foto guardada varias veces: "
                       "recomprimida, en menor resolución o con un filtro de "
                       "color. No detecta recortes ni rotaciones.",
            font=styles.fuente_base(11), text_color=styles.COLOR_TEXTO_TENUE,
            wraplength=980, justify="left", anchor="w").grid(
            row=1, column=0, sticky="w", padx=16, pady=(0, 8))

        fila = ctk.CTkFrame(card, fg_color="transparent")
        fila.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 8))
        fila.grid_columnconfigure(0, weight=1)
        self.entry_carpeta = ctk.CTkEntry(
            fila, height=36, placeholder_text=r"Carpeta con fotos.  Ej.  D:\Fotos")
        self.entry_carpeta.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.btn_elegir = ctk.CTkButton(
            fila, text=f"{icons.CARPETA}  Elegir", width=110, height=36,
            command=self._elegir_carpeta)
        self.btn_elegir.grid(row=0, column=1, padx=4)
        self.btn_analizar = ctk.CTkButton(
            fila, text=f"{icons.CAT_IMAGENES}  Analizar", width=130, height=36,
            font=styles.fuente_base(13, "bold"), command=self._iniciar)
        self.btn_analizar.grid(row=0, column=2, padx=(4, 0))

        sens = ctk.CTkFrame(card, fg_color="transparent")
        self._sens_row = sens
        sens.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 14))
        ctk.CTkLabel(sens, text="Sensibilidad:",
                     font=styles.fuente_base(12)).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(sens, text="estricta", font=styles.fuente_base(11),
                     text_color=styles.COLOR_TEXTO_TENUE).pack(side="left")
        self.slider_sensibilidad = ctk.CTkSlider(
            sens, from_=4, to=18, number_of_steps=14, width=220,
            command=self._sensibilidad_cambiada)
        self.slider_sensibilidad.set(10)
        self.slider_sensibilidad.pack(side="left", padx=8)
        ctk.CTkLabel(sens, text="tolerante", font=styles.fuente_base(11),
                     text_color=styles.COLOR_TEXTO_TENUE).pack(side="left")
        self.lbl_sensibilidad = ctk.CTkLabel(
            sens, text="  (normal)", font=styles.fuente_base(11),
            text_color=styles.COLOR_TEXTO_TENUE)
        self.lbl_sensibilidad.pack(side="left", padx=(6, 0))

        # Progreso
        self.zona_progreso = ctk.CTkFrame(t, fg_color="transparent")
        self.zona_progreso.grid(row=1, column=0, sticky="ew",
                                    padx=16, pady=(8, 0))
        self.zona_progreso.grid_columnconfigure(0, weight=1)
        self.barra_progreso = ctk.CTkProgressBar(
            self.zona_progreso, height=10)
        self.barra_progreso.grid(row=0, column=0, sticky="ew", pady=(4, 2))
        self.barra_progreso.set(0)
        self.lbl_estado = ctk.CTkLabel(
            self.zona_progreso, text="", font=styles.fuente_base(12),
            text_color=styles.COLOR_TEXTO_TENUE, anchor="w")
        self.lbl_estado.grid(row=1, column=0, sticky="ew")

        # Estadísticas
        self.fila_stats = ctk.CTkFrame(t, fg_color="transparent")
        self.fila_stats.grid(row=2, column=0, sticky="ew", padx=6, pady=(8, 0))
        for i in range(4):
            self.fila_stats.grid_columnconfigure(i, weight=1)
        self.stat_grupos = Baldosa(self.fila_stats, "Grupos de parecidas")
        self.stat_fotos = Baldosa(self.fila_stats, "Fotos en grupos")
        self.stat_mover = Baldosa(self.fila_stats, "Fotos a mover")
        self.stat_espacio = Baldosa(self.fila_stats, "Espacio recuperable")
        for i, b in enumerate((self.stat_grupos, self.stat_fotos,
                               self.stat_mover, self.stat_espacio)):
            b.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 6, 0))

        # Galería de resultados
        self.galeria = ctk.CTkScrollableFrame(t, fg_color=styles.COLOR_FONDO_TABLA)
        self.galeria.grid(row=4, column=0, sticky="nsew", padx=6, pady=(8, 0))
        self.galeria.grid_columnconfigure(0, weight=1)

        self.estado_vacio = EstadoVacio(
            t, icons.CAT_IMAGENES, "Sin analizar todavía",
            "Elige una carpeta con fotos y pulsa «Analizar». Los grupos de "
            "fotos parecidas aparecerán aquí, con miniatura de cada una.")
        self.estado_vacio.grid(row=4, column=0, sticky="nsew", padx=6,
                                   pady=(10, 0))

        # Paginador (solo se ve si los grupos no caben en una página)
        self.pager = ctk.CTkFrame(t, fg_color="transparent")
        self.pager.grid(row=5, column=0, sticky="ew", padx=6, pady=(8, 0))
        self.pager.grid_columnconfigure(1, weight=1)
        self.btn_pag_ant = ctk.CTkButton(
            self.pager, text="‹  Anterior", width=110, fg_color="transparent",
            border_width=1, text_color=styles.COLOR_TEXTO,
            command=lambda: self._cambiar_pagina(-1))
        self.btn_pag_ant.grid(row=0, column=0)
        self.lbl_pagina = ctk.CTkLabel(
            self.pager, text="", font=styles.fuente_base(12),
            text_color=styles.COLOR_TEXTO_TENUE)
        self.lbl_pagina.grid(row=0, column=1, padx=10)
        self.btn_pag_sig = ctk.CTkButton(
            self.pager, text="Siguiente  ›", width=110, fg_color="transparent",
            border_width=1, text_color=styles.COLOR_TEXTO,
            command=lambda: self._cambiar_pagina(1))
        self.btn_pag_sig.grid(row=0, column=2)
        self.pager.grid_remove()

        # Barra inferior
        barra = ctk.CTkFrame(t, fg_color=styles.COLOR_TARJETA)
        barra.grid(row=6, column=0, sticky="ew", padx=6, pady=(10, 6))
        barra.grid_columnconfigure(0, weight=1)
        self.lbl_totales = ctk.CTkLabel(
            barra, text="Sin analizar todavía.", font=styles.fuente_base(12),
            text_color=styles.COLOR_TEXTO_TENUE, anchor="w")
        self.lbl_totales.grid(row=0, column=0, padx=16, pady=12, sticky="w")
        self.btn_cuarentena = ctk.CTkButton(
            barra, text=f"{icons.ESCUDO}  Mover a cuarentena", width=200,
            height=36, font=styles.fuente_base(13, "bold"),
            fg_color=styles.COLOR_OK_BOTON, hover_color="#26734d",
            command=self._mover_a_cuarentena)
        self.btn_cuarentena.grid(row=0, column=1, padx=(4, 16), pady=12)

    # -- estado -------------------------------------------------------
    def _estado_inicial(self):
        self.barra_progreso.set(0)
        self.lbl_estado.configure(text="")
        self.zona_progreso.grid_remove()
        self.fila_stats.grid_remove()
        styles.boton_accion(self.btn_cuarentena, False)
        self._ver_galeria(False)

    def _sensibilidad_cambiada(self, valor):
        v = int(round(valor))
        etiqueta = ("muy estricta" if v <= 5 else "estricta" if v <= 8
                    else "normal" if v <= 11 else "tolerante" if v <= 15
                    else "muy tolerante")
        self.lbl_sensibilidad.configure(text=f"  ({etiqueta})")

    def _set_analizando(self, activo):
        styles.activar_boton(self.btn_elegir, not activo)
        self.entry_carpeta.configure(state="disabled" if activo else "normal")
        if activo:
            self.btn_analizar.configure(
                text=f"{icons.CRUZ}  Cancelar", command=self._cancelar_analisis,
                state="normal", fg_color=styles.COLOR_PELIGRO_BOTON,
                hover_color=("#9c2f24", "#8f2b22"), text_color="#ffffff")
        else:
            styles.activar_boton(self.btn_analizar, True)
            self.btn_analizar.configure(
                text=f"{icons.CAT_IMAGENES}  Analizar",
                command=self._iniciar)

    # -- acciones ---------------------------------------------------
    def _elegir_carpeta(self):
        carpeta = filedialog.askdirectory(title="Elige la carpeta con fotos")
        if carpeta:
            self.entry_carpeta.delete(0, "end")
            self.entry_carpeta.insert(0, os.path.normpath(carpeta))

    def _iniciar(self):
        carpeta = self.entry_carpeta.get().strip()
        if not carpeta or not os.path.isdir(carpeta):
            messagebox.showwarning(
                "Carpeta no válida",
                "Elige una carpeta con fotos para analizar.")
            return

        umbral = int(round(self.slider_sensibilidad.get()))
        self._carpeta = carpeta
        self._resultado = None
        self._seleccion = None
        self._thumbs = {}
        self._cancelar.clear()
        limpiar_cache()
        self._vaciar_galeria()

        self.zona_progreso.grid()
        self.barra_progreso.configure(mode="indeterminate")
        self.barra_progreso.start()
        self.lbl_estado.configure(text="Buscando imágenes…")
        self.lbl_totales.configure(text="Analizando…")
        self.fila_stats.grid_remove()
        styles.boton_accion(self.btn_cuarentena, False)
        self.estado_vacio.configurar(
            titulo="Analizando…", detalle="Comparando las fotos entre sí.")
        self._ver_galeria(False)
        self._set_analizando(True)

        self._hilo = threading.Thread(
            target=self._trabajo, args=(carpeta, umbral), daemon=True)
        self._hilo.start()
        self.after(100, self._revisar_cola)

    def _cancelar_analisis(self):
        self._cancelar.set()
        self.lbl_estado.configure(text="Cancelando…")
        self.btn_analizar.configure(state="disabled")

    def _trabajo(self, carpeta, umbral):
        try:
            res = analizar_carpeta(
                carpeta, umbral_hamming=umbral,
                progreso=lambda a, t, m: self._cola.put(("progreso", (a, t, m))),
                cancelado=self._cancelar.is_set)

            thumbs = {}
            total = res.total_fotos_en_grupos
            hechas = 0
            for g in res.grupos:
                for h in g.huellas:
                    if self._cancelar.is_set():
                        raise ComparacionCancelada()
                    hechas += 1
                    if hechas % 4 == 0 or hechas == total:
                        self._cola.put(("progreso", (
                            hechas, total,
                            f"Cargando miniaturas… ({hechas}/{total})")))
                    try:
                        thumbs[h.ruta] = cargar_miniatura(h.ruta)
                    except Exception as e:  # un archivo roto no debe parar la galería
                        log.info("No se pudo crear la miniatura de %s: %s", h.ruta, e)
                        thumbs[h.ruta] = None
            self._cola.put(("hecho", (res, thumbs)))
        except ComparacionCancelada:
            self._cola.put(("cancelado", None))
        except Exception as e:  # se anota en el registro y se muestra al usuario
            log.exception("Falló el análisis de fotos parecidas de %s", carpeta)
            self._cola.put(("error", e))

    def _revisar_cola(self):
        try:
            while True:
                tipo, dato = self._cola.get_nowait()
                if tipo == "progreso":
                    a, t, m = dato
                    self.lbl_estado.configure(text=m)
                    if t:
                        if self.barra_progreso.cget("mode") != "determinate":
                            self.barra_progreso.stop()
                            self.barra_progreso.configure(mode="determinate")
                        self.barra_progreso.set(min(a / t, 1.0))
                elif tipo == "hecho":
                    self._terminado(*dato)
                    return
                elif tipo == "cancelado":
                    self._cancelado()
                    return
                elif tipo == "error":
                    self._error(dato)
                    return
        except queue.Empty:
            pass
        self.after(100, self._revisar_cola)

    def _terminado(self, res, thumbs):
        self._resultado = res
        self._thumbs = thumbs
        self.barra_progreso.stop()
        self.barra_progreso.configure(mode="determinate")
        self.barra_progreso.set(1.0)
        self._set_analizando(False)
        self.btn_analizar.configure(state="normal")

        extra = (f"  ·  {len(res.errores)} imagen(es) ilegibles"
                 if res.errores else "")

        if res.total_grupos == 0:
            self.fila_stats.grid_remove()
            self.lbl_estado.configure(text="No se han encontrado fotos parecidas.")
            self.lbl_totales.configure(
                text=f"{res.total_imagenes} imágenes analizadas{extra} · "
                     f"0 grupos.")
            self.estado_vacio.configurar(
                titulo="No se han encontrado fotos parecidas",
                detalle=f"Se han comparado {res.total_imagenes} imágenes. "
                        f"Prueba a subir la sensibilidad si esperabas más.")
            self._ver_galeria(False)
            return

        # Preselección: en cada grupo se conserva la "mejor" copia (la
        # primera, que perceptual ordena por resolución). El usuario lo
        # cambia con un clic si no está de acuerdo.
        self._seleccion = SeleccionDuplicados(res)
        for gi, g in enumerate(res.grupos):
            self._seleccion.conservar_solo(gi, g.archivos[0].ruta)

        self.fila_stats.grid()
        self.stat_grupos.set(res.total_grupos)
        self.stat_fotos.set(res.total_fotos_en_grupos)
        self.lbl_estado.configure(
            text=f"Análisis terminado.{extra}")
        self._construir_galeria()
        self._ver_galeria(True)
        self._al_cambiar_seleccion()

    def _cancelado(self):
        self.barra_progreso.stop()
        self.barra_progreso.configure(mode="determinate")
        self.barra_progreso.set(0)
        self.lbl_estado.configure(text="Análisis cancelado.")
        self.lbl_totales.configure(text="Análisis cancelado.")
        self._set_analizando(False)
        self.btn_analizar.configure(state="normal")
        self.estado_vacio.configurar(
            titulo="Análisis cancelado",
            detalle="Pulsa «Analizar» para intentarlo de nuevo.")
        self._ver_galeria(False)

    def _error(self, e):
        self.barra_progreso.stop()
        self.barra_progreso.configure(mode="determinate")
        self.barra_progreso.set(0)
        self.lbl_estado.configure(text="El análisis ha fallado.")
        self.lbl_totales.configure(text="El análisis ha fallado.")
        self._set_analizando(False)
        self.btn_analizar.configure(state="normal")
        messagebox.showerror("Error durante el análisis",
                             f"{type(e).__name__}: {e}")

    # -- galería ---------------------------------------------------
    def _ver_galeria(self, mostrar):
        """Alterna galería / mensaje de estado vacío (mismo hueco)."""
        if mostrar:
            self.estado_vacio.grid_remove()
            self.galeria.grid()
        else:
            self.galeria.grid_remove()
            self.estado_vacio.grid()

    def _vaciar_galeria(self):
        for hijo in self.galeria.winfo_children():
            hijo.destroy()
        self._img_cache.clear()
        self._tiles = {}   # (gi, ruta) -> frame del tile
        self._botones = {}      # (gi, ruta) -> botón conservar/mover
        self._paginas = []
        self._pagina = 0
        self.pager.grid_remove()

    def _construir_galeria(self):
        self._vaciar_galeria()
        self._paginas = repartir_en_paginas(
            [g.cantidad for g in self._resultado.grupos])
        self._mostrar_pagina(0)

    def _cambiar_pagina(self, paso):
        nueva = self._pagina + paso
        if 0 <= nueva < len(self._paginas):
            self._mostrar_pagina(nueva)

    def _mostrar_pagina(self, pagina):
        """Dibuja los grupos de una página (los de las demás no existen como widgets)."""
        for hijo in self.galeria.winfo_children():
            hijo.destroy()
        self._img_cache.clear()
        self._tiles = {}
        self._botones = {}
        self._pagina = pagina
        primero, fin = self._paginas[pagina]

        for gi in range(primero, fin):
            g = self._resultado.grupos[gi]
            card = ctk.CTkFrame(self.galeria, fg_color=styles.COLOR_TARJETA)
            card.grid(row=gi - primero, column=0, sticky="ew", pady=(0, 10))
            card.grid_columnconfigure(0, weight=1)

            cab = ctk.CTkLabel(
                card, anchor="w", font=styles.fuente_base(12, "bold"),
                text=f"Grupo {gi + 1}   ·   {g.cantidad} fotos parecidas   ·   "
                     f"liberas {formatear_tamano(g.espacio_recuperable)}")
            cab.grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))

            tiras = ctk.CTkFrame(card, fg_color="transparent")
            tiras.grid(row=1, column=0, sticky="w", padx=8, pady=(0, 10))

            for j, (h, sim) in enumerate(zip(g.huellas, g.similitud)):
                self._tile_foto(tiras, gi, j, h, sim)
            self._refrescar_grupo(gi)

        self.galeria._parent_canvas.yview_moveto(0)
        if len(self._paginas) > 1:
            total = len(self._resultado.grupos)
            self.lbl_pagina.configure(
                text=f"Página {pagina + 1} de {len(self._paginas)}  ·  "
                     f"grupos {primero + 1}–{fin} de {total}")
            styles.activar_boton(self.btn_pag_ant, pagina > 0, fg="transparent")
            styles.activar_boton(self.btn_pag_sig, pagina < len(self._paginas) - 1,
                                 fg="transparent")
            self.pager.grid()
        else:
            self.pager.grid_remove()

    def _tile_foto(self, parent, gi, j, huella, sim):
        tile = ctk.CTkFrame(parent, fg_color=styles.COLOR_BALDOSA, corner_radius=8,
                            border_width=2)
        tile.grid(row=j // COLUMNAS, column=j % COLUMNAS, padx=6, pady=4, sticky="n")
        self._tiles[(gi, huella.ruta)] = tile

        pil = self._thumbs.get(huella.ruta)
        if pil is not None:
            img = ctk.CTkImage(light_image=pil, dark_image=pil,
                               size=(pil.width, pil.height))
            self._img_cache.append(img)
            lbl_img = ctk.CTkLabel(tile, image=img, text="")
        else:
            lbl_img = ctk.CTkLabel(tile, text="(sin\nvista previa)",
                                   width=150, height=150,
                                   text_color=styles.COLOR_TEXTO_TENUE)
        lbl_img.grid(row=0, column=0, padx=6, pady=(6, 4))
        lbl_img.configure(cursor="hand2")
        lbl_img.bind("<Button-1>", lambda _e, r=huella.ruta: abrir_visor(self.winfo_toplevel(), r))

        ctk.CTkLabel(tile, text=Path(huella.ruta).name, font=styles.fuente_base(10),
                     wraplength=150, justify="left", anchor="w").grid(
            row=1, column=0, padx=6, sticky="w")
        ctk.CTkLabel(
            tile, text=f"{huella.ancho}×{huella.alto}  ·  "
                       f"{formatear_tamano(huella.tamano)}",
            font=styles.fuente_base(10), text_color=styles.COLOR_TEXTO_TENUE).grid(
            row=2, column=0, padx=6, sticky="w")
        etiqueta_sim = "mejor calidad" if j == 0 else f"{sim * 100:.0f}% parecida"
        ctk.CTkLabel(tile, text=etiqueta_sim, font=styles.fuente_base(10),
                     text_color=styles.COLOR_TEXTO_TENUE).grid(
            row=3, column=0, padx=6, sticky="w")

        boton = ctk.CTkButton(
            tile, width=120, height=26, font=styles.fuente_base(11),
            command=lambda g=gi, r=huella.ruta: self._elegir_conservar(g, r))
        boton.grid(row=4, column=0, padx=6, pady=(4, 8))
        self._botones[(gi, huella.ruta)] = boton

    def _pintar_tile(self, gi, ruta):
        dec = self._seleccion.decision(gi, ruta)
        tile = self._tiles.get((gi, ruta))
        boton = self._botones.get((gi, ruta))
        if tile is None or boton is None:
            return
        if dec == _CONSERVAR:
            # Es la que se conserva: botón en verde y sin acción (ya lo es).
            tile.configure(border_color=styles.COLOR_OK)
            boton.configure(text=f"{icons.OK}  Se conserva", state="disabled",
                            fg_color=styles.COLOR_OK_BOTON,
                            text_color_disabled="#ffffff")  # legible, no "roto"
        else:
            tile.configure(border_color=styles.COLOR_ADVERTENCIA)
            boton.configure(text="Conservar esta", state="normal",
                            fg_color="transparent", border_width=1,
                            text_color=styles.COLOR_TEXTO,
                            hover_color=styles.COLOR_BALDOSA)

    def _refrescar_grupo(self, gi):
        for h in self._resultado.grupos[gi].huellas:
            self._pintar_tile(gi, h.ruta)

    def _elegir_conservar(self, gi, ruta):
        self._seleccion.conservar_solo(gi, ruta)
        self._refrescar_grupo(gi)
        self._al_cambiar_seleccion()

    def _al_cambiar_seleccion(self):
        if self._seleccion is None:
            return
        # repintar los grupos de la página que se está viendo
        if self._paginas:
            for gi in range(*self._paginas[self._pagina]):
                self._refrescar_grupo(gi)

        pendientes = self._seleccion.grupos_pendientes()
        a_mover = self._seleccion.cantidad_a_mover()
        liberar = self._seleccion.espacio_a_liberar()
        self.stat_mover.set(a_mover)
        self.stat_espacio.set(formatear_tamano(liberar),
                                  color=styles.COLOR_OK if liberar else None)

        if pendientes:
            self.lbl_totales.configure(
                text=f"{icons.AVISO}  {len(pendientes)} grupo(s) con más de una "
                     f"foto marcada para conservar. Deja solo una en cada grupo.")
            styles.boton_accion(self.btn_cuarentena, False)
        else:
            self.lbl_totales.configure(
                text=f"{icons.OK}  Listo: se moverán {a_mover} fotos "
                     f"({formatear_tamano(liberar)}).")
            styles.boton_accion(self.btn_cuarentena, bool(a_mover))

    def _mover_a_cuarentena(self):
        if self._seleccion is None or not self._seleccion.todo_listo():
            return
        if self._seleccion.cantidad_a_mover() == 0:
            return
        raiz = self._carpeta
        destino = filedialog.askdirectory(
            title="Elige (o crea) la carpeta de cuarentena", mustexist=False)
        if not destino:
            return
        destino = os.path.normpath(destino)
        try:
            aviso = validar_carpeta_cuarentena(destino, raiz)
        except CuarentenaInvalida as e:
            messagebox.showerror("Carpeta de cuarentena no válida", str(e))
            return
        if aviso and not messagebox.askyesno("Atención", aviso + "\n\n¿Continuar?"):
            return

        n = self._seleccion.cantidad_a_mover()
        libera = formatear_tamano(self._seleccion.espacio_a_liberar())
        if not messagebox.askyesno(
            "Confirmar movimiento a cuarentena",
            f"Se van a MOVER {n} foto(s) ({libera}) a:\n\n{destino}\n\n"
            "Las fotos marcadas para conservar NO se tocan. No se borra nada.\n\n"
            "¿Mover ahora?"):
            return

        try:
            res = mover_a_cuarentena(self._seleccion, raiz, destino)
        except Exception as e:  # se anota en el registro y se muestra al usuario
            log.exception("Falló el movimiento a cuarentena de fotos parecidas")
            messagebox.showerror("Error al mover", f"{type(e).__name__}: {e}")
            return

        if res.movidos:
            historial.registrar(
                historial.TIPO_CUARENTENA, "mover", raiz, destino,
                [(m.origen, m.destino) for m in res.movidos],
                f"{len(res.movidos)} fotos parecidas")

        self._resultado = None
        self._seleccion = None
        self._vaciar_galeria()
        self.fila_stats.grid_remove()
        styles.boton_accion(self.btn_cuarentena, False)
        self.lbl_totales.configure(
            text=f"{len(res.movidos)} foto(s) movidas a cuarentena. "
                 f"Vuelve a analizar si quieres continuar.")
        self.estado_vacio.configurar(
            titulo="Fotos movidas a cuarentena",
            detalle=f"Se han movido {len(res.movidos)} fotos. "
                    f"Vuelve a analizar para continuar.")
        self._ver_galeria(False)
        detalle = f"Se han movido {len(res.movidos)} fotos."
        if res.ruta_log:
            detalle += f"\n\nRegistro: {res.ruta_log}"
        if messagebox.askyesno("Hecho",
                               detalle + "\n\n¿Abrir la carpeta de cuarentena?"):
            try:
                os.startfile(destino)  # noqa: S606
            except OSError:
                pass
