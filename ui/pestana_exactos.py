"""Pestaña "Duplicados exactos": escanea una carpeta y decide qué copia conservar.

Es un componente con su PROPIO estado (resultado del escaneo, selección, colas, hilos...):
la ventana principal solo lo crea, le avisa del modo Sencilla / Avanzada y de que se cierra.
"""

import datetime
import os
import queue
import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk

from core.scanner import escanear, EscaneoCancelado
from core.reporte import exportar_csv
from core.hashing import formatear_tamano
from core.registro import log
from core.filtros import (
    FiltroEscaneo, parsear_extensiones, parsear_nombres, texto_de,
    EXTENSIONES_BASURA, NOMBRES_BASURA, CARPETAS_BASURA, CATEGORIAS_EXTENSIONES,
)
from core.seleccion import SeleccionDuplicados
from core.quarantine import (
    mover_a_cuarentena, validar_carpeta_cuarentena, CuarentenaInvalida,
)
from core import historial
from . import styles
from . import icons
from .widgets import CabeceraSeccion, Baldosa, EstadoVacio, tarjeta
from .results_table import TablaResultados
from .thumbnails import (
    vista_grande, limpiar_cache, EXT_IMAGEN,
)
from .image_viewer import abrir_visor, puede_visualizarse
from .tipos_duplicados_dialog import VentanaTipos


class PestanaExactos(ctk.CTkFrame):
    def __init__(self, contenedor, avanzado):
        """`contenedor` es la pestaña del CTkTabview donde se coloca este componente;
        `avanzado` es el modo con el que arranca la ventana."""
        super().__init__(contenedor, fg_color="transparent")
        contenedor.grid_columnconfigure(0, weight=1)    # el componente llena toda la pestaña
        contenedor.grid_rowconfigure(0, weight=1)
        self.grid(row=0, column=0, sticky="nsew")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(6, weight=1)

        self._avanzado = avanzado
        self._cola = queue.Queue()            # mensajes del hilo que escanea
        self._hilo = None
        self._cancelar_evento = threading.Event()
        self._resultado = None
        self._seleccion = None
        self._carpeta_escaneada = None
        self._cola_cuar = queue.Queue()       # mensajes del hilo que mueve a cuarentena
        self._excl_texto = ""

        self._construir_tarjeta_escaneo()
        self._construir_opciones_escaneo()
        self._construir_zona_progreso()
        self._construir_tarjeta_decision()
        self._construir_estadisticas()
        self._construir_tabla()
        self._construir_barra_inferior()
        self._set_estado_inicial()

    # ------------------------------------------------------------------
    # Lo que la ventana principal le pide
    # ------------------------------------------------------------------
    def aplicar_modo(self, avanzado):
        """Muestra u oculta los controles «avanzados» (sin borrar widgets: así el
        estado se conserva al alternar)."""
        self._avanzado = avanzado
        # En Sencilla se ocultan: panel de opciones, la fila de "carpeta
        # preferida", "Ver tipos" y "Exportar CSV".
        for w in (self._opciones_cont, self.tarjeta_decision_cab,
                  self.tarjeta_decision_fila, self.btn_tipos, self.btn_exportar):
            (w.grid if avanzado else w.grid_remove)()
        if not avanzado and self._opciones_abiertas.get():
            self._alternar_opciones()       # colapsar el panel si estaba abierto

    def al_pasar_a_sencilla(self):
        """Si ya hay resultados y se vuelve a Sencilla, la app decide sola otra vez."""
        if self._seleccion is not None:
            self._seleccion.preseleccionar_principales()
            self.tabla.refrescar_todo()
            self._al_cambiar_seleccion()

    def cancelar_trabajos(self):
        """Lo llama la ventana al cerrarse: si hay un escaneo en marcha, se cancela."""
        if self._hilo and self._hilo.is_alive():
            self._cancelar_evento.set()

    def _construir_tarjeta_escaneo(self):
        card = tarjeta(self, 1)
        CabeceraSeccion(card, 1, "Elige la carpeta que quieres revisar",
                        icons.CARPETA).grid(
            row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        fila = ctk.CTkFrame(card, fg_color="transparent")
        fila.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 16))
        fila.grid_columnconfigure(0, weight=1)

        self.entry_carpeta = ctk.CTkEntry(
            fila, height=36, placeholder_text=r"Ej.  D:\Fotos")
        self.entry_carpeta.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.btn_elegir = ctk.CTkButton(
            fila, text=f"{icons.CARPETA}  Elegir", width=110, height=36,
            command=self._elegir_carpeta)
        self.btn_elegir.grid(row=0, column=1, padx=4)
        self.btn_escanear = ctk.CTkButton(
            fila, text=f"{icons.BUSCAR}  Escanear", width=130, height=36,
            font=styles.fuente_base(13, "bold"), command=self._iniciar_escaneo)
        self.btn_escanear.grid(row=0, column=2, padx=(4, 0))

    def _construir_opciones_escaneo(self):
        cont = ctk.CTkFrame(self, fg_color="transparent")
        cont.grid(row=2, column=0, sticky="ew", padx=6, pady=(6, 0))
        cont.grid_columnconfigure(0, weight=1)
        self._opciones_cont = cont

        self._opciones_abiertas = ctk.BooleanVar(value=False)
        self.btn_toggle_opciones = ctk.CTkButton(
            cont, text=f"{icons.TRI_DER}  {icons.ENGRANAJE}  Opciones de escaneo "
                       f"(filtrar por tipo de archivo)",
            anchor="w", fg_color="transparent", hover=False,
            text_color=styles.COLOR_TEXTO_TENUE, command=self._alternar_opciones)
        self.btn_toggle_opciones.grid(row=0, column=0, sticky="ew")

        self.panel_opciones = ctk.CTkFrame(cont, fg_color=styles.COLOR_TARJETA)
        self.panel_opciones.grid(row=1, column=0, sticky="ew", pady=(2, 0))
        self.panel_opciones.grid_columnconfigure(1, weight=1)
        self.panel_opciones.grid_remove()
        p = self.panel_opciones

        # --- Buscar solo estos tipos (lista blanca) ------------------
        ctk.CTkLabel(p, text="Buscar solo estos tipos de archivo:",
                     font=styles.fuente_base(12, "bold")).grid(
            row=0, column=0, columnspan=3, padx=16, pady=(12, 4), sticky="w")

        chips = ctk.CTkFrame(p, fg_color="transparent")
        chips.grid(row=1, column=0, columnspan=3, padx=14, pady=(0, 4), sticky="w")
        self.chk_categorias = {}
        for nombre in CATEGORIAS_EXTENSIONES:
            chk = ctk.CTkCheckBox(
                chips, text=f"{icons.ICONO_CATEGORIA[nombre]}  {nombre}",
                font=styles.fuente_base(12),
                command=lambda n=nombre: self._alternar_categoria(n))
            chk.pack(side="left", padx=(2, 12), pady=4)
            self.chk_categorias[nombre] = chk

        ctk.CTkLabel(p, text="Extensiones:", font=styles.fuente_base(12)).grid(
            row=2, column=0, padx=(16, 8), pady=4, sticky="w")
        self.entry_incluir = ctk.CTkEntry(
            p, height=32, placeholder_text="vacío = se buscan todos los tipos")
        self.entry_incluir.grid(row=2, column=1, columnspan=2, padx=(4, 16),
                                pady=4, sticky="ew")
        self.entry_incluir.bind("<KeyRelease>", self._sincronizar_categorias)

        ctk.CTkLabel(
            p, text="Marca una categoría o escribe extensiones a mano. "
                    "Si lo dejas vacío se buscan duplicados de cualquier tipo.",
            font=styles.fuente_base(11), text_color=styles.COLOR_TEXTO_TENUE,
        ).grid(row=3, column=0, columnspan=3, padx=16, pady=(0, 10), sticky="w")

        ctk.CTkFrame(p, height=1, fg_color=styles.COLOR_FILA_ALTERNA).grid(
            row=4, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 8))

        # --- Ignorar (lista negra) ----------------------------------
        ctk.CTkLabel(p, text="Ignorar además:",
                     font=styles.fuente_base(12, "bold")).grid(
            row=5, column=0, columnspan=3, padx=16, pady=(0, 4), sticky="w")

        def campo(fila, etiqueta):
            ctk.CTkLabel(p, text=etiqueta, font=styles.fuente_base(12)).grid(
                row=fila, column=0, padx=(16, 8), pady=4, sticky="w")
            e = ctk.CTkEntry(p, height=32)
            e.grid(row=fila, column=1, columnspan=2, padx=(4, 16), pady=4,
                   sticky="ew")
            return e

        self.entry_ext = campo(6, "Extensiones:")
        self.entry_carpetas = campo(7, "Carpetas:")
        self.entry_nombres = campo(8, "Nombres:")

        self.chk_vacios = ctk.CTkCheckBox(
            p, text="Ignorar archivos de 0 bytes", font=styles.fuente_base(12))
        self.chk_vacios.grid(row=9, column=0, columnspan=2, padx=16,
                             pady=(6, 4), sticky="w")

        botones = ctk.CTkFrame(p, fg_color="transparent")
        botones.grid(row=9, column=2, padx=12, pady=(6, 4), sticky="e")
        ctk.CTkButton(botones, text="Valores por defecto", width=140,
                      fg_color="transparent", border_width=1,
                      text_color=styles.COLOR_TEXTO,
                      command=self._filtros_por_defecto).pack(side="left", padx=4)
        ctk.CTkButton(botones, text="Quitar todo", width=90,
                      fg_color="transparent", border_width=1,
                      text_color=styles.COLOR_TEXTO,
                      command=self._filtros_vacios).pack(side="left", padx=4)

        ctk.CTkLabel(
            p, text="Separa los valores con espacios o comas.",
            font=styles.fuente_base(11), text_color=styles.COLOR_TEXTO_TENUE,
        ).grid(row=10, column=0, columnspan=3, padx=16, pady=(0, 12), sticky="w")

        self._filtros_por_defecto()

    def _construir_zona_progreso(self):
        self.zona_progreso = ctk.CTkFrame(self, fg_color="transparent")
        self.zona_progreso.grid(row=3, column=0, sticky="ew", padx=16, pady=(8, 0))
        self.zona_progreso.grid_columnconfigure(0, weight=1)

        self.barra_progreso = ctk.CTkProgressBar(self.zona_progreso, height=10)
        self.barra_progreso.grid(row=0, column=0, sticky="ew", pady=(4, 2))
        self.barra_progreso.set(0)
        self.lbl_estado = ctk.CTkLabel(
            self.zona_progreso, text="", font=styles.fuente_base(12),
            text_color=styles.COLOR_TEXTO_TENUE, anchor="w")
        self.lbl_estado.grid(row=1, column=0, sticky="ew")

    def _construir_tarjeta_decision(self):
        card = tarjeta(self, 4)
        self.tarjeta_decision = card
        self.tarjeta_decision_cab = CabeceraSeccion(
            card, 2, "Decide qué copia conservar en cada grupo", icons.ESTRELLA)
        self.tarjeta_decision_cab.grid(row=0, column=0, sticky="w",
                                       padx=16, pady=(14, 8))

        fila = ctk.CTkFrame(card, fg_color="transparent")
        self.tarjeta_decision_fila = fila
        fila.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 6))
        fila.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(fila, text="Carpeta preferida:",
                     font=styles.fuente_base(12)).grid(
            row=0, column=0, padx=(0, 8), pady=6, sticky="w")
        self.entry_carpeta_buena = ctk.CTkEntry(
            fila, height=34,
            placeholder_text=r"Las copias dentro de esta carpeta se conservan.  "
                             r"Ej.  D:\Fotos\Organizado")
        self.entry_carpeta_buena.grid(row=0, column=1, padx=4, pady=6, sticky="ew")
        self.btn_elegir_buena = ctk.CTkButton(
            fila, text=f"{icons.CARPETA}  Elegir", width=100, height=34,
            command=self._elegir_carpeta_buena)
        self.btn_elegir_buena.grid(row=0, column=2, padx=4, pady=6)
        self.btn_regla = ctk.CTkButton(
            fila, text=f"{icons.AUTO}  Regla por carpeta", width=170,
            height=34, command=self._aplicar_regla)
        self.btn_regla.grid(row=0, column=3, padx=4, pady=6)
        self.btn_principal = ctk.CTkButton(
            fila, text=f"{icons.OK}  Elegir la principal", width=170,
            height=34, fg_color="transparent", border_width=1,
            command=self._elegir_principales)
        self.btn_principal.grid(row=0, column=4, padx=(4, 0), pady=6)

        self.lbl_validacion = ctk.CTkLabel(
            card, text="", font=styles.fuente_base(12), anchor="w",
            justify="left", wraplength=1000)
        self.lbl_validacion.grid(row=2, column=0, sticky="w",
                                 padx=16, pady=(2, 14))

    def _construir_estadisticas(self):
        self.fila_stats = ctk.CTkFrame(self, fg_color="transparent")
        self.fila_stats.grid(row=5, column=0, sticky="ew", padx=6, pady=(8, 0))
        for i in range(4):
            self.fila_stats.grid_columnconfigure(i, weight=1)

        self.stat_grupos = Baldosa(self.fila_stats, "Grupos de duplicados")
        self.stat_dupes = Baldosa(self.fila_stats, "Archivos duplicados")
        self.stat_mover = Baldosa(self.fila_stats, "Archivos a mover")
        self.stat_espacio = Baldosa(self.fila_stats, "Espacio recuperable")
        for i, b in enumerate((self.stat_grupos, self.stat_dupes,
                               self.stat_mover, self.stat_espacio)):
            b.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 6, 0))

    def _construir_tabla(self):
        self.tabla_wrap = ctk.CTkFrame(self, fg_color="transparent")
        self.tabla_wrap.grid(row=6, column=0, sticky="nsew", padx=6, pady=(8, 0))
        self.tabla_wrap.grid_rowconfigure(0, weight=1)
        self.tabla_wrap.grid_columnconfigure(0, weight=1)

        # Contenedor izquierdo: tabla + estado vacío (mismo hueco).
        self.zona_tabla = ctk.CTkFrame(self.tabla_wrap, fg_color="transparent")
        self.zona_tabla.grid(row=0, column=0, sticky="nsew")
        self.zona_tabla.grid_rowconfigure(0, weight=1)
        self.zona_tabla.grid_columnconfigure(0, weight=1)

        self.tabla = TablaResultados(
            self.zona_tabla, on_cambio=self._al_cambiar_seleccion,
            on_seleccion=self._preview_archivo)
        self.tabla.grid(row=0, column=0, sticky="nsew")

        self.estado_vacio = EstadoVacio(
            self.zona_tabla, icons.BUSCAR,
            "Todavía no hay resultados",
            "Elige una carpeta arriba y pulsa «Escanear». "
            "Los grupos de archivos duplicados aparecerán aquí.")
        self.estado_vacio.grid(row=0, column=0, sticky="nsew")

        # Panel de vista previa a la derecha.
        self.panel_preview = ctk.CTkFrame(
            self.tabla_wrap, fg_color=styles.COLOR_TARJETA, width=290)
        self.panel_preview.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self.panel_preview.grid_propagate(False)
        self.panel_preview.grid_columnconfigure(0, weight=1)
        self.panel_preview.grid_rowconfigure(0, weight=1)

        self._preview_ruta = None
        self.preview_img = ctk.CTkLabel(
            self.panel_preview,
            text="Selecciona un archivo\npara ver la vista previa",
            font=styles.fuente_base(12), text_color=styles.COLOR_TEXTO_TENUE)
        self.preview_img.grid(row=0, column=0, padx=12, pady=12)
        self.preview_img.bind("<Button-1>", lambda _e: self._abrir_visor())
        self.preview_nombre = ctk.CTkLabel(
            self.panel_preview, text="", font=styles.fuente_base(12, "bold"),
            wraplength=262, justify="left", anchor="w")
        self.preview_nombre.grid(row=1, column=0, padx=12, pady=(0, 2), sticky="w")
        self.preview_meta = ctk.CTkLabel(
            self.panel_preview, text="", font=styles.fuente_base(11),
            text_color=styles.COLOR_TEXTO_TENUE, wraplength=262,
            justify="left", anchor="w")
        self.preview_meta.grid(row=2, column=0, padx=12, pady=(0, 4), sticky="w")
        self.preview_ampliar = ctk.CTkLabel(
            self.panel_preview, text="", font=styles.fuente_base(11),
            text_color=styles.COLOR_ACENTO, anchor="w")
        self.preview_ampliar.grid(row=3, column=0, padx=12, pady=(0, 12), sticky="w")
        self.preview_ampliar.bind("<Button-1>", lambda _e: self._abrir_visor())

    def _construir_barra_inferior(self):
        barra = ctk.CTkFrame(self, fg_color=styles.COLOR_TARJETA)
        barra.grid(row=7, column=0, sticky="ew", padx=6, pady=(12, 6))
        barra.grid_columnconfigure(0, weight=1)

        self.lbl_totales = ctk.CTkLabel(
            barra, text="Sin escanear todavía.", font=styles.fuente_base(12),
            text_color=styles.COLOR_TEXTO_TENUE, anchor="w")
        self.lbl_totales.grid(row=0, column=0, padx=16, pady=12, sticky="w")

        self.btn_tipos = ctk.CTkButton(
            barra, text=f"{icons.GRAFICO}  Ver tipos de archivo", width=180,
            height=36, fg_color="transparent", border_width=1,
            text_color=styles.COLOR_TEXTO,
            command=self._ver_tipos)
        self.btn_tipos.grid(row=0, column=1, padx=4, pady=12)
        self.btn_exportar = ctk.CTkButton(
            barra, text=f"{icons.GUARDAR}  Exportar CSV", width=150, height=36,
            fg_color="transparent", border_width=1, text_color=styles.COLOR_TEXTO,
            command=self._exportar_csv)
        self.btn_exportar.grid(row=0, column=2, padx=4, pady=12)
        self.btn_cuarentena = ctk.CTkButton(
            barra, text=f"{icons.ESCUDO}  Mover a cuarentena", width=200,
            height=36, font=styles.fuente_base(13, "bold"),
            fg_color=styles.COLOR_OK_BOTON, hover_color="#26734d",
            command=self._mover_a_cuarentena)
        self.btn_cuarentena.grid(row=0, column=3, padx=(4, 16), pady=12)

    def _alternar_opciones(self):
        abierto = not self._opciones_abiertas.get()
        self._opciones_abiertas.set(abierto)
        tri = icons.TRI_ABAJO if abierto else icons.TRI_DER
        self.btn_toggle_opciones.configure(
            text=f"{tri}  {icons.ENGRANAJE}  Opciones de escaneo "
                 f"(filtrar por tipo de archivo)")
        if abierto:
            self.panel_opciones.grid()
        else:
            self.panel_opciones.grid_remove()

    def _alternar_categoria(self, nombre):
        """Marca/desmarca las extensiones de una categoría en el campo."""
        actuales = parsear_extensiones(self.entry_incluir.get())
        exts = CATEGORIAS_EXTENSIONES[nombre]
        if self.chk_categorias[nombre].get():
            actuales |= exts
        else:
            actuales -= exts
        self.entry_incluir.delete(0, "end")
        self.entry_incluir.insert(0, texto_de(actuales))

    def _sincronizar_categorias(self, _evento=None):
        """Tras editar el campo a mano, deja marcadas solo las categorías
        cuyas extensiones estén todas presentes."""
        presentes = parsear_extensiones(self.entry_incluir.get())
        for nombre, chk in self.chk_categorias.items():
            completa = CATEGORIAS_EXTENSIONES[nombre] <= presentes
            if completa and not chk.get():
                chk.select()
            elif not completa and chk.get():
                chk.deselect()

    def _filtros_por_defecto(self):
        for entry, valores in (
            (self.entry_ext, EXTENSIONES_BASURA),
            (self.entry_carpetas, CARPETAS_BASURA),
            (self.entry_nombres, NOMBRES_BASURA),
        ):
            entry.delete(0, "end")
            entry.insert(0, "  ".join(valores))
        self.chk_vacios.select()
        self.entry_incluir.delete(0, "end")
        for chk in self.chk_categorias.values():
            chk.deselect()

    def _filtros_vacios(self):
        for entry in (self.entry_incluir, self.entry_ext,
                      self.entry_carpetas, self.entry_nombres):
            entry.delete(0, "end")
        self.chk_vacios.deselect()
        for chk in self.chk_categorias.values():
            chk.deselect()

    def _filtro_actual(self):
        return FiltroEscaneo(
            extensiones_incluidas=parsear_extensiones(self.entry_incluir.get()),
            extensiones_excluidas=parsear_extensiones(self.entry_ext.get()),
            nombres_excluidos=parsear_nombres(self.entry_nombres.get()),
            carpetas_excluidas=parsear_nombres(self.entry_carpetas.get()),
            tamano_minimo=1 if self.chk_vacios.get() else 0,
        )

    def _agregar_extension_al_filtro(self, ext):
        actuales = parsear_extensiones(self.entry_ext.get())
        actuales.add(ext.lower().lstrip("."))
        self.entry_ext.delete(0, "end")
        self.entry_ext.insert(0, texto_de(actuales))
        if not self._opciones_abiertas.get():
            self._alternar_opciones()

    def _set_estado_inicial(self):
        self.barra_progreso.set(0)
        self.lbl_estado.configure(text="")
        self.zona_progreso.grid_remove()
        self.fila_stats.grid_remove()
        self._habilitar_acciones(False)
        self._habilitar_decision(False)
        self.lbl_validacion.configure(text="")
        self.estado_vacio.tkraise()

    def _habilitar_acciones(self, activo):
        # "Ver tipos" y "Exportar CSV" son botones "secundarios" (borde).
        for btn in (self.btn_tipos, self.btn_exportar):
            styles.activar_boton(btn, activo, fg="transparent",
                                 hover=styles.COLOR_BALDOSA)

    def _habilitar_decision(self, activo):
        estado = "normal" if activo else "disabled"
        self.entry_carpeta_buena.configure(state=estado)
        styles.activar_boton(self.btn_elegir_buena, activo)   # botón primario (azul)
        styles.activar_boton(self.btn_regla, activo)          # botón primario (azul)
        styles.activar_boton(self.btn_principal, activo,      # botón secundario (borde)
                             fg="transparent", hover=styles.COLOR_BALDOSA)
        styles.boton_accion(self.btn_cuarentena, activo)

    def _elegir_principales(self):
        if self._seleccion is None:
            return
        self._seleccion.preseleccionar_principales()
        self.tabla.refrescar_todo()
        self._al_cambiar_seleccion()

    def _set_escaneando(self, escaneando):
        # Mientras se escanea: "Elegir" y el campo de carpeta se apagan,
        # y "Escanear" se convierte en "Cancelar" (rojo).
        styles.activar_boton(self.btn_elegir, not escaneando)
        self.entry_carpeta.configure(state="disabled" if escaneando else "normal")
        if escaneando:
            self.btn_escanear.configure(
                text=f"{icons.CRUZ}  Cancelar", command=self._cancelar_escaneo,
                state="normal",
                fg_color=styles.COLOR_PELIGRO_BOTON,
                hover_color=("#9c2f24", "#8f2b22"),
                text_color="#ffffff")
        else:
            styles.activar_boton(self.btn_escanear, True)
            self.btn_escanear.configure(
                text=f"{icons.BUSCAR}  Escanear", command=self._iniciar_escaneo)

    def _elegir_carpeta(self):
        carpeta = filedialog.askdirectory(title="Elige la carpeta a escanear")
        if carpeta:
            self.entry_carpeta.delete(0, "end")
            self.entry_carpeta.insert(0, os.path.normpath(carpeta))

    def _elegir_carpeta_buena(self):
        carpeta = filedialog.askdirectory(title="Elige la carpeta preferida")
        if carpeta:
            self.entry_carpeta_buena.delete(0, "end")
            self.entry_carpeta_buena.insert(0, os.path.normpath(carpeta))

    def _iniciar_escaneo(self):
        carpeta = self.entry_carpeta.get().strip()
        if not carpeta:
            messagebox.showwarning("Falta la carpeta",
                                   "Elige primero una carpeta para escanear.")
            return
        if not os.path.isdir(carpeta):
            messagebox.showerror(
                "Carpeta no válida",
                f"La ruta no existe o no es una carpeta:\n\n{carpeta}")
            return

        filtro = self._filtro_actual()

        self.tabla.limpiar()
        self._resultado = None
        self._seleccion = None
        self._carpeta_escaneada = carpeta
        self._cancelar_evento.clear()
        limpiar_cache()
        self.zona_progreso.grid()
        self.barra_progreso.set(0)
        self.barra_progreso.configure(mode="indeterminate")
        self.barra_progreso.start()
        self.lbl_estado.configure(text="Preparando el escaneo…")
        self.lbl_totales.configure(text="Escaneando…")
        self.lbl_validacion.configure(text="")
        self.fila_stats.grid_remove()
        self.estado_vacio.configurar(
            titulo="Escaneando…", detalle="Buscando archivos duplicados.")
        self.estado_vacio.tkraise()
        self._habilitar_acciones(False)
        self._habilitar_decision(False)
        self._set_escaneando(True)

        # --- PATRÓN hilo + cola + after() (se repite en toda la app) ---
        # Tkinter no es "thread-safe": solo el hilo principal puede tocar
        # widgets. Entonces:
        #   · el trabajo pesado (escanear) corre en un hilo aparte,
        #   · ese hilo NO toca la interfaz: solo mete mensajes en una cola,
        #   · la interfaz llama a _revisar_cola() cada 100 ms, saca los
        #     mensajes y actualiza los widgets desde el hilo principal.
        # Así la ventana no se congela y se puede cancelar a mitad.
        self._hilo = threading.Thread(target=self._trabajo_escaneo,
                                      args=(carpeta, filtro), daemon=True)
        self._hilo.start()
        self.after(100, self._revisar_cola)

    def _cancelar_escaneo(self):
        # El hilo comprueba este evento entre archivo y archivo.
        self._cancelar_evento.set()
        self.lbl_estado.configure(text="Cancelando…")
        self.btn_escanear.configure(state="disabled")

    def _trabajo_escaneo(self, carpeta, filtro):
        """Corre en el HILO SECUNDARIO. No toca ni un widget: todo va por
        la cola como tuplas (tipo, dato)."""
        try:
            resultado = escanear(
                carpeta,
                progreso=lambda p: self._cola.put(("progreso", p)),
                cancelado=self._cancelar_evento.is_set,
                filtro=filtro,
            )
            self._cola.put(("hecho", resultado))
        except EscaneoCancelado:
            self._cola.put(("cancelado", None))
        except Exception as e:  # cualquier fallo se anota en el registro y se muestra
            log.exception("Falló el escaneo de %s", carpeta)
            self._cola.put(("error", e))

    def _revisar_cola(self):
        """Corre en el HILO PRINCIPAL. Vacía la cola y actúa según el tipo
        de mensaje. Se vuelve a programar sola hasta que llega "hecho",
        "cancelado" o "error"."""
        try:
            while True:
                tipo, dato = self._cola.get_nowait()   # lanza queue.Empty si no hay
                if tipo == "progreso":
                    self._aplicar_progreso(dato)
                elif tipo == "hecho":
                    self._finalizar_escaneo(dato)
                    return
                elif tipo == "cancelado":
                    self._escaneo_cancelado()
                    return
                elif tipo == "error":
                    self._escaneo_con_error(dato)
                    return
        except queue.Empty:
            pass
        self.after(100, self._revisar_cola)          # seguir mirando

    def _aplicar_progreso(self, p):
        self.lbl_estado.configure(text=p.mensaje)
        if p.total > 0:
            if self.barra_progreso.cget("mode") != "determinate":
                self.barra_progreso.stop()
                self.barra_progreso.configure(mode="determinate")
            self.barra_progreso.set(min(p.actual / p.total, 1.0))

    def _finalizar_escaneo(self, resultado):
        self._resultado = resultado
        self.barra_progreso.stop()
        self.barra_progreso.configure(mode="determinate")
        self.barra_progreso.set(1.0)
        self._set_escaneando(False)
        self.btn_escanear.configure(state="normal")

        self._excl_texto = (
            f"  ·  {resultado.total_excluidos} ignorados por filtro"
            if resultado.total_excluidos else "")

        if resultado.total_grupos == 0:
            self.fila_stats.grid_remove()
            self.lbl_estado.configure(text="No se han encontrado duplicados.")
            self.lbl_totales.configure(
                text=f"{resultado.total_archivos} archivos revisados"
                     f"{self._excl_texto} · 0 duplicados.")
            self._habilitar_acciones(False)
            self._habilitar_decision(False)
            self.lbl_validacion.configure(text="")
            self.estado_vacio.configurar(
                titulo="No se han encontrado duplicados",
                detalle=f"Se han revisado {resultado.total_archivos} archivos y "
                        f"todos son únicos.")
            self.estado_vacio.tkraise()
            return

        self._seleccion = SeleccionDuplicados(resultado)
        if not self._avanzado:
            self._seleccion.preseleccionar_principales()
        self.tabla.cargar(self._seleccion)
        self.tabla.tkraise()
        self.fila_stats.grid()
        self.stat_grupos.set(resultado.total_grupos)
        self.stat_dupes.set(resultado.total_archivos_duplicados)
        self.lbl_estado.configure(
            text="Escaneo terminado."
            + (f"  {len(resultado.errores)} archivo(s) no se pudieron leer."
               if resultado.errores else ""))
        self._habilitar_acciones(True)
        self._habilitar_decision(True)
        self._al_cambiar_seleccion()

    def _escaneo_cancelado(self):
        self.barra_progreso.stop()
        self.barra_progreso.configure(mode="determinate")
        self.barra_progreso.set(0)
        self.lbl_estado.configure(text="Escaneo cancelado.")
        self.lbl_totales.configure(text="Escaneo cancelado.")
        self._set_escaneando(False)
        self.btn_escanear.configure(state="normal")
        self.estado_vacio.configurar(
            titulo="Escaneo cancelado",
            detalle="Pulsa «Escanear» para intentarlo de nuevo.")
        self.estado_vacio.tkraise()

    def _escaneo_con_error(self, e):
        self.barra_progreso.stop()
        self.barra_progreso.configure(mode="determinate")
        self.barra_progreso.set(0)
        self.lbl_estado.configure(text="El escaneo ha fallado.")
        self.lbl_totales.configure(text="El escaneo ha fallado.")
        self._set_escaneando(False)
        self.btn_escanear.configure(state="normal")
        messagebox.showerror("Error durante el escaneo",
                             f"Ha ocurrido un problema:\n\n{type(e).__name__}: {e}")

    def _aplicar_regla(self):
        if self._seleccion is None:
            return
        carpeta_buena = self.entry_carpeta_buena.get().strip()
        if not carpeta_buena:
            messagebox.showinfo(
                "Falta la carpeta preferida",
                "Escribe o elige antes una carpeta preferida.")
            return
        if not os.path.isdir(carpeta_buena):
            if not messagebox.askyesno(
                "La carpeta no existe",
                f"La carpeta preferida no existe ahora mismo:\n\n{carpeta_buena}\n\n"
                "¿Quieres aplicar la regla igualmente? (los grupos sin coincidencia "
                "quedarán sin decidir)"):
                return

        resueltos, sin_coincidencia = self._seleccion.aplicar_regla_carpeta(
            carpeta_buena)
        self.tabla.refrescar_todo()
        self._al_cambiar_seleccion()

        msg = f"Regla aplicada: {resueltos} grupo(s) resueltos automáticamente."
        if sin_coincidencia:
            msg += (f"\n{sin_coincidencia} grupo(s) no tienen ninguna copia dentro "
                    "de la carpeta preferida: han quedado resaltados para que elijas "
                    "manualmente (un clic sobre la copia que quieres conservar, o "
                    "doble clic para conservar solo esa).")
            self.tabla.ir_a_pendiente()
        messagebox.showinfo("Regla automática", msg)

    def _al_cambiar_seleccion(self):
        if self._seleccion is None:
            return
        r = self._resultado
        pendientes = self._seleccion.grupos_pendientes()
        a_mover = self._seleccion.cantidad_a_mover()
        liberar = self._seleccion.espacio_a_liberar()

        self.stat_mover.set(a_mover)
        self.stat_espacio.set(formatear_tamano(liberar),
                              color=styles.COLOR_OK if liberar else None)
        self.lbl_totales.configure(
            text=f"{r.total_grupos} grupos · {r.total_archivos_duplicados} "
                 f"archivos duplicados{self._excl_texto}")

        if not pendientes:
            if not self._avanzado:
                texto = (f"{icons.OK}  La app conservará la copia principal de "
                         f"cada grupo. Doble clic en una fila para conservar "
                         f"otra. Cuando quieras, pulsa «Mover a cuarentena».")
            else:
                texto = (f"{icons.OK}  Todos los grupos tienen una sola copia "
                         f"marcada para conservar. Ya puedes mover a cuarentena.")
            self.lbl_validacion.configure(text=texto, text_color=styles.COLOR_OK)
            styles.boton_accion(self.btn_cuarentena, True)
        else:
            self.lbl_validacion.configure(
                text=f"{icons.AVISO}  {len(pendientes)} grupo(s) sin resolver "
                     f"(resaltados en la tabla). Marca una sola copia para "
                     f"conservar en cada uno. El botón «Mover a cuarentena» "
                     f"está bloqueado.",
                text_color=styles.COLOR_ADVERTENCIA)
            styles.boton_accion(self.btn_cuarentena, False)

    def _mover_a_cuarentena(self):
        if self._seleccion is None or not self._seleccion.todo_listo():
            return

        raiz = self._carpeta_escaneada
        carpeta_cuarentena = filedialog.askdirectory(
            title="Elige (o crea) la carpeta de cuarentena", mustexist=False)
        if not carpeta_cuarentena:
            return
        carpeta_cuarentena = os.path.normpath(carpeta_cuarentena)

        try:
            aviso = validar_carpeta_cuarentena(carpeta_cuarentena, raiz)
        except CuarentenaInvalida as e:
            messagebox.showerror("Carpeta de cuarentena no válida", str(e))
            return
        if aviso and not messagebox.askyesno("Atención", aviso + "\n\n¿Continuar?"):
            return

        n = self._seleccion.cantidad_a_mover()
        libera = formatear_tamano(self._seleccion.espacio_a_liberar())
        if not messagebox.askyesno(
            "Confirmar movimiento a cuarentena",
            f"Se van a MOVER {n} archivo(s) ({libera}) a:\n\n{carpeta_cuarentena}\n\n"
            "Los originales que has marcado para conservar NO se tocan. No se "
            "borra nada: todo queda en la cuarentena para que lo revises y lo "
            "borres tú manualmente cuando quieras.\n\n¿Mover ahora?"):
            return

        self._set_ocupado_cuarentena(True)
        self.lbl_estado.configure(text="Moviendo a cuarentena…")
        self.barra_progreso.configure(mode="determinate")
        self.barra_progreso.set(0)

        hilo = threading.Thread(
            target=self._trabajo_cuarentena,
            args=(self._seleccion, raiz, carpeta_cuarentena), daemon=True)
        hilo.start()
        self.after(100, self._revisar_cola_cuarentena)

    def _set_ocupado_cuarentena(self, ocupado):
        activo = not ocupado
        for btn in (self.btn_escanear, self.btn_regla, self.btn_elegir,
                    self.btn_elegir_buena):
            styles.activar_boton(btn, activo)
        for btn in (self.btn_exportar, self.btn_tipos):
            styles.activar_boton(btn, activo, fg="transparent",
                                 hover=styles.COLOR_BALDOSA)
        styles.boton_accion(self.btn_cuarentena, activo)

    def _trabajo_cuarentena(self, seleccion, raiz, carpeta_cuarentena):
        try:
            res = mover_a_cuarentena(
                seleccion, raiz, carpeta_cuarentena,
                progreso=lambda a, t, m: self._cola_cuar.put(("progreso", (a, t, m))))
            self._cola_cuar.put(("hecho", (res, carpeta_cuarentena)))
        except Exception as e:  # se anota en el registro y se muestra al usuario
            log.exception("Falló el movimiento a cuarentena (origen %s, destino %s)",
                          raiz, carpeta_cuarentena)
            self._cola_cuar.put(("error", e))

    def _revisar_cola_cuarentena(self):
        try:
            while True:
                tipo, dato = self._cola_cuar.get_nowait()
                if tipo == "progreso":
                    actual, total, msg = dato
                    self.lbl_estado.configure(text=msg)
                    if total:
                        self.barra_progreso.set(min(actual / total, 1.0))
                elif tipo == "hecho":
                    self._cuarentena_terminada(*dato)
                    return
                elif tipo == "error":
                    self._set_ocupado_cuarentena(False)
                    self.lbl_estado.configure(text="El movimiento ha fallado.")
                    messagebox.showerror(
                        "Error al mover", f"{type(dato).__name__}: {dato}")
                    return
        except queue.Empty:
            pass
        self.after(100, self._revisar_cola_cuarentena)

    def _cuarentena_terminada(self, res, carpeta_cuarentena):
        self._set_ocupado_cuarentena(False)
        self.barra_progreso.set(1.0)
        self.lbl_estado.configure(text="Movimiento a cuarentena terminado.")

        if res.movidos:
            historial.registrar(
                historial.TIPO_CUARENTENA, "mover", self._carpeta_escaneada,
                carpeta_cuarentena, [(m.origen, m.destino) for m in res.movidos],
                f"{len(res.movidos)} duplicados exactos")

        movidos = len(res.movidos)
        fallidos = len(res.fallidos)
        detalle = (f"Se han movido {movidos} archivo(s) "
                   f"({formatear_tamano(res.bytes_movidos)}).")
        if fallidos:
            detalle += (f"\n{fallidos} no se han podido mover "
                        f"(consulta el CSV de registro).")
        if res.ruta_log:
            detalle += f"\n\nRegistro: {res.ruta_log}"

        self.tabla.limpiar()
        self._seleccion = None
        self._resultado = None
        self._habilitar_decision(False)
        self._habilitar_acciones(False)
        self.lbl_validacion.configure(text="")
        self.fila_stats.grid_remove()
        self.lbl_totales.configure(
            text=f"{movidos} archivo(s) movidos a cuarentena. "
                 f"Vuelve a escanear si quieres continuar.")
        self.estado_vacio.configurar(
            titulo="Archivos movidos a cuarentena",
            detalle=detalle.split("\n\n")[0] + " Vuelve a escanear para continuar.")
        self.estado_vacio.tkraise()

        if messagebox.askyesno(
            "Hecho", detalle + "\n\n¿Quieres abrir la carpeta de cuarentena?"):
            try:
                os.startfile(carpeta_cuarentena)  # noqa: S606 (Windows)
            except OSError:
                pass

    def _abrir_visor(self, ruta=None):
        abrir_visor(self.winfo_toplevel(), ruta or self._preview_ruta)

    def _quitar_imagen_preview(self):
        """Borra la imagen del panel de vista previa.

        CTkLabel.configure(image=None) NO quita la imagen que ya se estaba
        mostrando (fallo conocido de CustomTkinter 5.2.2), así que se limpia el
        Label de tkinter que hay por dentro.
        """
        self.preview_img.configure(image=None)
        self.preview_img._label.configure(image="")
        self._preview_ctkimg = None

    def _preview_archivo(self, ruta):
        """Muestra la vista grande del archivo seleccionado en la tabla."""
        self._preview_ruta = ruta
        if not ruta:
            self._quitar_imagen_preview()
            self.preview_img.configure(
                text="Selecciona un archivo\npara ver la vista previa")
            self.preview_nombre.configure(text="")
            self.preview_meta.configure(text="")
            self.preview_ampliar.configure(text="")
            return

        try:
            pil = vista_grande(ruta)
        except Exception:  # sin vista previa; se anota para poder investigarlo
            log.warning("No se pudo mostrar la vista previa de %s", ruta, exc_info=True)
            pil = None
        if pil is not None:
            img = ctk.CTkImage(light_image=pil, dark_image=pil,
                               size=(pil.width, pil.height))
            self._preview_ctkimg = img  # guardar referencia
            self.preview_img.configure(image=img, text="")
        else:
            self._quitar_imagen_preview()
            self.preview_img.configure(text="(sin vista previa)")

        self.preview_nombre.configure(text=os.path.basename(ruta))
        partes = [os.path.dirname(ruta)]
        datos = []
        ext = os.path.splitext(ruta)[1].lower().lstrip(".")
        if ext in EXT_IMAGEN:
            try:
                from PIL import Image
                with Image.open(ruta) as im:
                    datos.append(f"{im.width}×{im.height}")
            except (OSError, ValueError):  # si no se puede leer, se omite la resolución
                pass
        try:
            st = os.stat(ruta)
            datos.append(formatear_tamano(st.st_size))
            datos.append(datetime.datetime.fromtimestamp(
                st.st_mtime).strftime("%d/%m/%Y %H:%M"))
        except OSError:
            pass
        if datos:
            partes.append("   ·   ".join(datos))
        self.preview_meta.configure(text="\n".join(partes))
        self.preview_ampliar.configure(
            text=f"{icons.BUSCAR}  Clic para ver la imagen en grande"
            if puede_visualizarse(ruta) else "")

    def _ver_tipos(self):
        if not self._resultado or self._resultado.total_grupos == 0:
            return
        VentanaTipos(self.winfo_toplevel(), self._resultado, self._agregar_extension_al_filtro)

    def _exportar_csv(self):
        if not self._resultado or self._resultado.total_grupos == 0:
            return
        ruta = filedialog.asksaveasfilename(
            title="Guardar informe CSV", defaultextension=".csv",
            initialfile="duplicados_informe.csv",
            filetypes=[("CSV", "*.csv"), ("Todos los archivos", "*.*")])
        if not ruta:
            return
        try:
            n = exportar_csv(self._resultado, ruta)
        except OSError as e:
            messagebox.showerror("No se pudo guardar",
                                 f"No se pudo escribir el archivo:\n\n{e}")
            return
        messagebox.showinfo("Informe guardado",
                            f"Se han guardado {n} grupos de duplicados en:\n\n{ruta}")
