"""Pestaña "Reunir imágenes": junta en una carpeta las fotos repartidas por otra.

Es un componente con su PROPIO estado (la lista de imágenes, las colas, el hilo...):
la ventana principal solo la crea y le avisa del modo Sencilla / Avanzada.
"""

import os
import queue
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from core import reunir, historial
from core.registro import log
from core.mover import MOVER, COPIAR, DestinoInvalido, validar_destino
from . import styles
from . import icons
from .image_viewer import abrir_visor
from .widgets import CabeceraSeccion, Baldosa, EstadoVacio, tarjeta
from .thumbnails import (
    limpiar_cache, miniatura_o_placeholder,
)
from .tipos_dialog import VentanaTiposNoImagen


class PestanaReunir(ctk.CTkFrame):
    def __init__(self, contenedor):
        """`contenedor` es la pestaña del CTkTabview donde se coloca este componente."""
        super().__init__(contenedor, fg_color="transparent")
        contenedor.grid_columnconfigure(0, weight=1)    # el componente llena toda la pestaña
        contenedor.grid_rowconfigure(0, weight=1)
        self.grid(row=0, column=0, sticky="nsew")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        self._cola = queue.Queue()            # mensajes del hilo que mueve/copia
        self._cola_thumbs = queue.Queue()     # mensajes del hilo que crea miniaturas
        self._hilo = None
        self._cancelar = threading.Event()
        self._imagenes = []
        self._otros = []
        self._carpeta = None
        self._incluidas = set()   # rutas de imagen marcadas
        self._thumbs = {}
        self._img_cache = []      # referencias a CTkImage (si no, se recolectan)
        self._tiles = {}

        self._construir()
        self._estado_inicial()

    def aplicar_modo(self, avanzado):
        """Lo llama la ventana al cambiar entre Sencilla y Avanzada."""
        (self._avanzado.grid if avanzado else self._avanzado.grid_remove)()
        if not avanzado:
            self.seg_accion.set("Mover")
            self.seg_estrategia.set("Por archivos")

    def cancelar_trabajos(self):
        """Lo llama la ventana al cerrarse: si hay una operación en marcha, se cancela."""
        if self._hilo and self._hilo.is_alive():
            self._cancelar.set()

    def _construir(self):
        t = self

        card = tarjeta(t, 0)
        CabeceraSeccion(card, 1, "Reúne todas las imágenes en una carpeta",
                        icons.REUNIR).grid(row=0, column=0, sticky="w",
                                           padx=16, pady=(14, 4))
        ctk.CTkLabel(
            card, text="Junta en un solo sitio las fotos que tengas repartidas "
                       "por una carpeta y sus subcarpetas.",
            font=styles.fuente_base(11), text_color=styles.COLOR_TEXTO_TENUE,
            anchor="w").grid(row=1, column=0, sticky="w", padx=16, pady=(0, 8))

        fila = ctk.CTkFrame(card, fg_color="transparent")
        fila.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 6))
        fila.grid_columnconfigure(0, weight=1)
        self.entry_carpeta = ctk.CTkEntry(
            fila, height=36, placeholder_text=r"Carpeta a revisar.  Ej.  D:\Fotos")
        self.entry_carpeta.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.btn_elegir = ctk.CTkButton(
            fila, text=f"{icons.CARPETA}  Elegir", width=110, height=36,
            command=self._elegir_carpeta)
        self.btn_elegir.grid(row=0, column=1, padx=4)
        self.btn_buscar = ctk.CTkButton(
            fila, text=f"{icons.BUSCAR}  Buscar imágenes", width=150, height=36,
            font=styles.fuente_base(13, "bold"), command=self._buscar)
        self.btn_buscar.grid(row=0, column=2, padx=(4, 0))

        self.seg_alcance = ctk.CTkSegmentedButton(
            card, values=["Todas las subcarpetas", "Solo el primer nivel"])
        self.seg_alcance.set("Todas las subcarpetas")
        self.seg_alcance.grid(row=3, column=0, sticky="w",
                                     padx=16, pady=(0, 14))

        # --- opciones de destino / acción (fila) --------------------
        opc = ctk.CTkFrame(card, fg_color="transparent")
        opc.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 12))
        opc.grid_columnconfigure(0, weight=1)
        self.entry_destino = ctk.CTkEntry(
            opc, height=34, placeholder_text=r"Carpeta común de destino")
        self.entry_destino.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(opc, text=f"{icons.CARPETA}  Elegir", width=100, height=34,
                      command=self._elegir_destino).grid(row=0, column=1,
                                                                padx=4)

        self._avanzado = ctk.CTkFrame(card, fg_color="transparent")
        self._avanzado.grid(row=5, column=0, sticky="w", padx=16,
                                   pady=(0, 12))
        ctk.CTkLabel(self._avanzado, text="Acción:",
                     font=styles.fuente_base(12)).pack(side="left", padx=(0, 6))
        self.seg_accion = ctk.CTkSegmentedButton(
            self._avanzado, values=["Mover", "Copiar"])
        self.seg_accion.set("Mover")
        self.seg_accion.pack(side="left", padx=(0, 16))
        ctk.CTkLabel(self._avanzado, text="Estrategia:",
                     font=styles.fuente_base(12)).pack(side="left", padx=(0, 6))
        self.seg_estrategia = ctk.CTkSegmentedButton(
            self._avanzado,
            values=["Por archivos", "Carpeta entera"])
        self.seg_estrategia.set("Por archivos")
        self.seg_estrategia.pack(side="left")

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
        self.fila_stats.grid(row=2, column=0, sticky="ew", padx=6,
                                    pady=(10, 0))
        for i in range(3):
            self.fila_stats.grid_columnconfigure(i, weight=1)
        self.stat_img = Baldosa(self.fila_stats, "Imágenes encontradas")
        self.stat_sel = Baldosa(self.fila_stats, "Marcadas para reunir")
        self.stat_otros = Baldosa(self.fila_stats, "Otros archivos")
        for i, b in enumerate((self.stat_img, self.stat_sel,
                               self.stat_otros)):
            b.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 6, 0))

        # Galería
        self.galeria = ctk.CTkScrollableFrame(
            t, fg_color=styles.COLOR_FONDO_TABLA)
        self.galeria.grid(row=4, column=0, sticky="nsew", padx=6,
                                 pady=(10, 0))
        for c in range(6):
            self.galeria.grid_columnconfigure(c, weight=1, uniform="tile")
        self.estado_vacio = EstadoVacio(
            t, icons.REUNIR, "Sin buscar todavía",
            "Elige una carpeta y pulsa «Buscar imágenes». Aparecerán aquí para "
            "que elijas cuáles reunir.")
        self.estado_vacio.grid(row=4, column=0, sticky="nsew", padx=6,
                                      pady=(10, 0))

        # Barra inferior
        barra = ctk.CTkFrame(t, fg_color=styles.COLOR_TARJETA)
        barra.grid(row=5, column=0, sticky="ew", padx=6, pady=(10, 6))
        barra.grid_columnconfigure(0, weight=1)
        self.lbl_totales = ctk.CTkLabel(
            barra, text="", font=styles.fuente_base(12),
            text_color=styles.COLOR_TEXTO_TENUE, anchor="w")
        self.lbl_totales.grid(row=0, column=0, padx=16, pady=12, sticky="w")
        self.btn_reunir = ctk.CTkButton(
            barra, text=f"{icons.REUNIR}  Reunir aquí", width=170, height=36,
            font=styles.fuente_base(13, "bold"),
            fg_color=styles.COLOR_OK_BOTON, hover_color="#26734d",
            command=self._ejecutar)
        self.btn_reunir.grid(row=0, column=1, padx=(4, 16), pady=12)

    def _estado_inicial(self):
        self.barra_progreso.set(0)
        self.lbl_estado.configure(text="")
        self.zona_progreso.grid_remove()
        self.fila_stats.grid_remove()
        styles.boton_accion(self.btn_reunir, False)
        self.lbl_totales.configure(text="")
        self._ver_galeria(False)

    def _ver_galeria(self, mostrar):
        if mostrar:
            self.estado_vacio.grid_remove()
            self.galeria.grid()
        else:
            self.galeria.grid_remove()
            self.estado_vacio.grid()

    # -- buscar imágenes -----------------------------------------
    def _elegir_carpeta(self):
        carpeta = filedialog.askdirectory(title="Elige la carpeta a revisar")
        if carpeta:
            self.entry_carpeta.delete(0, "end")
            self.entry_carpeta.insert(0, os.path.normpath(carpeta))

    def _elegir_destino(self):
        carpeta = filedialog.askdirectory(
            title="Elige (o crea) la carpeta de destino", mustexist=False)
        if carpeta:
            self.entry_destino.delete(0, "end")
            self.entry_destino.insert(0, os.path.normpath(carpeta))

    def _buscar(self):
        carpeta = self.entry_carpeta.get().strip()
        if not carpeta or not os.path.isdir(carpeta):
            messagebox.showwarning("Carpeta no válida",
                                   "Elige una carpeta para revisar.")
            return
        recursivo = self.seg_alcance.get() == "Todas las subcarpetas"
        self._carpeta = carpeta
        limpiar_cache()
        try:
            imagenes, otros = reunir.listar(carpeta, recursivo=recursivo)
        except OSError as e:
            messagebox.showerror("Error al leer la carpeta", str(e))
            return
        self._imagenes = imagenes
        self._otros = otros
        self._incluidas = set(imagenes)
        self._thumbs = {}

        if not imagenes:
            self._estado_inicial()
            self.estado_vacio.configurar(
                titulo="No se han encontrado imágenes",
                detalle="En esa carpeta no hay archivos de imagen"
                        + ("" if recursivo else " en el primer nivel") + ".")
            self._ver_galeria(False)
            return

        self.fila_stats.grid()
        self.stat_img.set(len(imagenes))
        self.stat_otros.set(len(otros))
        self._construir_galeria()
        self._ver_galeria(True)
        styles.boton_accion(self.btn_reunir, True)
        self._actualizar_totales()
        # miniaturas en un hilo
        threading.Thread(target=self._cargar_thumbs,
                         args=(list(imagenes),), daemon=True).start()
        self.after(80, self._procesar_thumbs)

    def _cargar_thumbs(self, rutas):
        for r in rutas:
            try:
                self._thumbs[r] = miniatura_o_placeholder(r, 96)
            except Exception as e:  # un archivo roto no debe parar la galería
                log.info("No se pudo crear la miniatura de %s: %s", r, e)
                self._thumbs[r] = None
            self._cola_thumbs.put(r)

    def _procesar_thumbs(self):
        hechas = 0
        try:
            while hechas < 30:
                ruta = self._cola_thumbs.get_nowait()
                hechas += 1
                self._pintar_thumb(ruta)
        except queue.Empty:
            pass
        self.after(70, self._procesar_thumbs)

    def _construir_galeria(self):
        for h in self.galeria.winfo_children():
            h.destroy()
        self._img_cache.clear()
        self._tiles.clear()

        cols = 6
        LIMITE = 300
        for i, ruta in enumerate(self._imagenes[:LIMITE]):
            tile = ctk.CTkFrame(self.galeria, fg_color=styles.COLOR_BALDOSA,
                                corner_radius=6)
            tile.grid(row=i // cols, column=i % cols, padx=4, pady=4, sticky="new")
            marca = ctk.CTkCheckBox(
                tile, text="", width=20,
                command=lambda r=ruta: self._alternar(r))
            marca.select()
            marca.grid(row=0, column=0, padx=(6, 0), pady=(4, 0), sticky="w")
            lbl = ctk.CTkLabel(tile, text="…", width=96, height=96,
                               text_color=styles.COLOR_TEXTO_TENUE)
            lbl.grid(row=1, column=0, padx=6, pady=(0, 2))
            lbl.configure(cursor="hand2")
            lbl.bind("<Button-1>", lambda _e, r=ruta: abrir_visor(self.winfo_toplevel(), r))
            ctk.CTkLabel(tile, text=Path(ruta).name, font=styles.fuente_base(9),
                         wraplength=96, justify="left").grid(
                row=2, column=0, padx=6, pady=(0, 6), sticky="w")
            self._tiles[ruta] = (tile, marca, lbl)

        if len(self._imagenes) > LIMITE:
            ctk.CTkLabel(
                self.galeria,
                text=f"… y {len(self._imagenes) - LIMITE} más "
                     f"(se reunirán todas las marcadas igualmente).",
                font=styles.fuente_base(11),
                text_color=styles.COLOR_TEXTO_TENUE).grid(
                row=LIMITE, column=0, columnspan=cols, pady=8)

    def _pintar_thumb(self, ruta):
        entrada = self._tiles.get(ruta)
        pil = self._thumbs.get(ruta)
        if not entrada or pil is None:
            return
        _tile, _marca, lbl = entrada
        img = ctk.CTkImage(light_image=pil, dark_image=pil,
                           size=(pil.width, pil.height))
        self._img_cache.append(img)
        lbl.configure(image=img, text="")

    def _alternar(self, ruta):
        entrada = self._tiles.get(ruta)
        if not entrada:
            return
        _tile, marca, _lbl = entrada
        if marca.get():
            self._incluidas.add(ruta)
        else:
            self._incluidas.discard(ruta)
        self._actualizar_totales()

    def _actualizar_totales(self):
        n = len(self._incluidas)
        self.stat_sel.set(n)
        styles.boton_accion(self.btn_reunir, bool(n))
        self.lbl_totales.configure(
            text=f"{n} imagen(es) marcadas · {len(self._otros)} archivos "
                 f"que no son imágenes")

    # -- ejecutar ------------------------------------------------
    def _ejecutar(self):
        """Botón "Reunir aquí". Pasos: validar destino -> según la
        estrategia, confirmar y lanzar la operación en un hilo."""
        origen = self._carpeta
        if not origen:
            return
        destino = self.entry_destino.get().strip()
        if not destino:
            messagebox.showwarning("Falta el destino",
                                   "Elige la carpeta común de destino.")
            return
        destino = os.path.normpath(destino)
        try:
            # rechaza que el destino esté dentro del origen
            aviso = validar_destino(destino, origen)
        except DestinoInvalido as e:
            messagebox.showerror("Destino no válido", str(e))
            return
        if aviso and not messagebox.askyesno("Atención", aviso + "\n\n¿Continuar?"):
            return

        accion = COPIAR if self.seg_accion.get() == "Copiar" else MOVER
        estrategia = self.seg_estrategia.get()
        verbo = "copiar" if accion == COPIAR else "mover"

        if estrategia == "Carpeta entera":
            nombre = os.path.basename(os.path.normpath(origen))
            if not messagebox.askyesno(
                "Confirmar",
                f"Se va a {verbo.upper()} la carpeta «{nombre}» ENTERA "
                f"(con todo lo que hay dentro) a:\n\n{destino}\\{nombre}\\\n\n"
                f"¿Continuar?"):
                return
            self._lanzar(
                lambda p, c: reunir.reunir_carpeta_entera(
                    origen, destino, accion=accion, progreso=p),
                accion, destino, historial.TIPO_REUNIR_CARPETA,
                f"carpeta «{nombre}» entera")
            return

        # --- Por archivos ---
        imagenes = [r for r in self._imagenes
                    if r in self._incluidas]     # solo las casillas marcadas
        if not imagenes:
            return
        otros = self._otros
        reglas = reunir.ReglasNoImagen()               # por defecto: dejar todo lo no-imagen
        if otros:
            # Diálogo MODAL: wait_window() bloquea aquí hasta que se cierre;
            # después leemos dlg.reglas (o None si canceló).
            dlg = VentanaTiposNoImagen(self.winfo_toplevel(), reunir.tipos_no_imagen(otros))
            self.wait_window(dlg)
            if dlg.reglas is None:
                return
            reglas = dlg.reglas

        n_otros = sum(1 for r in otros
                      if reglas.accion(os.path.splitext(r)[1].lower().lstrip("."))
                      != reunir.DEJAR)
        if not messagebox.askyesno(
            "Confirmar",
            f"Se van a {verbo.upper()} {len(imagenes)} imagen(es)"
            + (f" y {n_otros} archivo(s) más" if n_otros else "")
            + f" a:\n\n{destino}\n\n"
            "Se mantienen las subcarpetas. ¿Continuar?"):
            return

        self._lanzar(
            lambda p, c: reunir.reunir_por_archivos(
                imagenes, otros, origen, destino, accion=accion,
                reglas=reglas, progreso=p, cancelado=c),
            accion, destino, historial.TIPO_REUNIR,
            f"{len(imagenes)} imágenes")

    def _lanzar(self, fn, accion, destino, tipo, descripcion):
        self._cancelar.clear()
        self.zona_progreso.grid()
        self.barra_progreso.set(0)
        self.lbl_estado.configure(text="Empezando…")
        styles.boton_accion(self.btn_reunir, False)
        styles.activar_boton(self.btn_buscar, False)
        styles.activar_boton(self.btn_elegir, False)

        def trabajo():
            try:
                res = fn(
                    lambda a, t, m: self._cola.put(("prog", (a, t, m))),
                    self._cancelar.is_set)
                self._cola.put(
                    ("hecho", (res, accion, destino, tipo, descripcion, self._carpeta)))
            except Exception as e:  # se anota en el registro y se muestra al usuario
                log.exception("Falló la operación «%s» (%s)", tipo, descripcion)
                self._cola.put(("error", e))

        self._hilo = threading.Thread(target=trabajo, daemon=True)
        self._hilo.start()
        self.after(100, self._revisar_cola)

    def _revisar_cola(self):
        try:
            while True:
                tipo, dato = self._cola.get_nowait()
                if tipo == "prog":
                    a, t, m = dato
                    self.lbl_estado.configure(text=m)
                    if t:
                        self.barra_progreso.set(min(a / t, 1.0))
                elif tipo == "hecho":
                    self._terminado(*dato)
                    return
                elif tipo == "error":
                    self._error(dato)
                    return
        except queue.Empty:
            pass
        self.after(100, self._revisar_cola)

    def _terminado(self, res, accion, destino, tipo, descripcion, origen):
        styles.activar_boton(self.btn_buscar, True)
        styles.activar_boton(self.btn_elegir, True)
        self.barra_progreso.set(1.0)

        hechos = res.hechos
        if hechos:
            historial.registrar(
                tipo, accion, origen, destino,
                [(t.origen, t.destino) for t in hechos], descripcion)

        verbo = "copiado" if accion == COPIAR else "movido"
        self.lbl_estado.configure(
            text=f"Listo: {len(hechos)} archivo(s) {verbo}(s)."
            + (f"  {len(res.fallidos)} con error." if res.fallidos else ""))
        self.lbl_totales.configure(
            text=f"{len(hechos)} archivo(s) {verbo}(s) a {destino}.")

        # limpiar la lista (lo movido ya no está)
        self._imagenes = []
        self._incluidas = set()
        self.fila_stats.grid_remove()
        styles.boton_accion(self.btn_reunir, False)
        for h in self.galeria.winfo_children():
            h.destroy()
        self.estado_vacio.configurar(
            titulo=f"{len(hechos)} archivo(s) {verbo}(s)",
            detalle="Puedes deshacerlo desde «Historial» (arriba, en modo "
                    "Avanzada). Vuelve a buscar si quieres continuar.")
        self._ver_galeria(False)

        detalle = f"{len(hechos)} archivo(s) {verbo}(s) a:\n\n{destino}"
        if res.ruta_log:
            detalle += f"\n\nRegistro: {res.ruta_log}"
        if messagebox.askyesno("Hecho",
                               detalle + "\n\n¿Abrir la carpeta de destino?"):
            try:
                os.startfile(destino)  # noqa: S606
            except OSError:
                pass

    def _error(self, e):
        styles.boton_accion(self.btn_reunir, True)
        styles.activar_boton(self.btn_buscar, True)
        styles.activar_boton(self.btn_elegir, True)
        self.barra_progreso.set(0)
        self.lbl_estado.configure(text="La operación ha fallado.")
        messagebox.showerror("Error al reunir", f"{type(e).__name__}: {e}")
