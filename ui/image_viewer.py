"""Visor de imagen a (casi) pantalla completa, con zoom y desplazamiento.

Se abre al pulsar una previsualización. Permite ver los detalles:
- rueda del ratón (o botones +/−) para acercar/alejar,
- arrastrar con el ratón para desplazarse,
- "Ajustar" para encajar la imagen en la ventana, "100%" para verla a
  tamaño real.
"""

import os
import tkinter as tk

import customtkinter as ctk
from PIL import Image, ImageOps, ImageTk

from core.registro import log

from . import styles
from .thumbnails import EXT_IMAGEN

# Límite al cargar (px, lado mayor): evita reventar la memoria con fotos
# enormes; el zoom sigue funcionando dentro de ese límite.
_MAX_LADO = 6000


def puede_visualizarse(ruta):
    ext = os.path.splitext(ruta)[1].lower().lstrip(".")
    return ext in EXT_IMAGEN


class VisorImagen(ctk.CTkToplevel):
    def __init__(self, master, ruta):
        super().__init__(master)
        self.title(os.path.basename(ruta))
        self.configure(fg_color=styles.COLOR_FONDO)

        self._orig = None
        try:
            with Image.open(ruta) as im:
                im = ImageOps.exif_transpose(im).convert("RGB")
                if max(im.size) > _MAX_LADO:
                    im.thumbnail((_MAX_LADO, _MAX_LADO), Image.LANCZOS)
                self._orig = im.copy()
        except Exception:  # el visor enseña «no se puede abrir» en vez de romperse
            log.warning("No se pudo abrir la imagen %s en el visor", ruta, exc_info=True)
            self._orig = None

        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = int(sw * 0.85), int(sh * 0.85)
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        barra = ctk.CTkFrame(self)
        barra.pack(fill="x", padx=8, pady=8)
        ctk.CTkButton(barra, text="−", width=40,
                      command=lambda: self._zoom(1 / 1.25)).pack(side="left", padx=2)
        ctk.CTkButton(barra, text="Ajustar", width=90,
                      command=self._ajustar).pack(side="left", padx=2)
        ctk.CTkButton(barra, text="100 %", width=60,
                      command=lambda: self._set_escala(1.0)).pack(side="left", padx=2)
        ctk.CTkButton(barra, text="+", width=40,
                      command=lambda: self._zoom(1.25)).pack(side="left", padx=2)
        self._lbl_info = ctk.CTkLabel(
            barra, text="", font=styles.fuente_base(12),
            text_color=styles.COLOR_TEXTO_TENUE)
        self._lbl_info.pack(side="left", padx=14)
        ctk.CTkButton(barra, text="Cerrar", width=80,
                      command=self.destroy).pack(side="right", padx=2)

        ctk.CTkLabel(self, text=ruta, font=styles.fuente_base(11),
                     text_color=styles.COLOR_TEXTO_TENUE, anchor="w").pack(
            fill="x", padx=14, pady=(0, 4))

        cont = ctk.CTkFrame(self, fg_color=styles.COLOR_FONDO_TABLA)
        cont.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        # tk.Canvas no es de CustomTkinter: su color se resuelve a mano.
        self.canvas = tk.Canvas(cont, bg=styles.col(styles.COLOR_FONDO_TABLA),
                                highlightthickness=0)
        vsb = ctk.CTkScrollbar(cont, command=self.canvas.yview)
        hsb = ctk.CTkScrollbar(cont, orientation="horizontal",
                               command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)

        self._escala = 1.0
        self._tkimg = None

        self.canvas.bind("<ButtonPress-1>",
                         lambda e: self.canvas.scan_mark(e.x, e.y))
        self.canvas.bind("<B1-Motion>",
                         lambda e: self.canvas.scan_dragto(e.x, e.y, gain=1))
        self.canvas.bind("<MouseWheel>", self._rueda)
        self.bind("<Escape>", lambda _e: self.destroy())

        self.transient(master)
        self.after(60, self._ajustar)
        self.after(150, self.lift)
        self.after(160, self.focus)

    # ------------------------------------------------------------------
    def _set_appearance_mode(self, mode_string):
        super()._set_appearance_mode(mode_string)
        try:
            self.canvas.configure(bg=styles.col(styles.COLOR_FONDO_TABLA))
            self._redibujar()
        except tk.TclError:
            pass

    def _redibujar(self):
        self.canvas.delete("all")
        if self._orig is None:
            self.canvas.create_text(
                20, 20, anchor="nw", fill=styles.col(styles.COLOR_TEXTO),
                text="No se puede mostrar esta imagen.")
            self._lbl_info.configure(text="")
            return
        w = max(1, int(self._orig.width * self._escala))
        h = max(1, int(self._orig.height * self._escala))
        remuestreo = Image.LANCZOS if self._escala < 1 else Image.NEAREST
        self._tkimg = ImageTk.PhotoImage(self._orig.resize((w, h), remuestreo))
        self.canvas.create_image(0, 0, anchor="nw", image=self._tkimg)
        self.canvas.configure(scrollregion=(0, 0, w, h))
        self._lbl_info.configure(
            text=f"{self._orig.width}×{self._orig.height} px   ·   "
                 f"{int(self._escala * 100)} %")

    def _set_escala(self, escala):
        self._escala = max(0.05, min(escala, 8.0))
        self._redibujar()

    def _zoom(self, factor):
        self._set_escala(self._escala * factor)

    def _ajustar(self):
        if self._orig is None:
            self._redibujar()
            return
        self.canvas.update_idletasks()
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        if cw < 10 or ch < 10:
            self.after(80, self._ajustar)
            return
        self._set_escala(min(cw / self._orig.width, ch / self._orig.height, 1.0))

    def _rueda(self, evento):
        self._zoom(1.1 if evento.delta > 0 else 1 / 1.1)


def abrir_visor(master, ruta):
    """Abre el visor a pantalla casi completa si `ruta` es una imagen que se puede mostrar."""
    if ruta and puede_visualizarse(ruta) and os.path.isfile(ruta):
        VisorImagen(master, ruta)
