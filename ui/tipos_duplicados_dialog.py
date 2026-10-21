"""Ventana con el desglose de duplicados por extensión."""

import customtkinter as ctk

from core.hashing import formatear_tamano
from . import styles
from . import icons


class VentanaTipos(ctk.CTkToplevel):
    """Desglose de los duplicados por extensión, con opción de excluir."""

    def __init__(self, master, resultado, al_excluir):
        super().__init__(master)
        self.title("Tipos de archivo entre los duplicados")
        self.geometry("560x480")
        self.transient(master)
        self._al_excluir = al_excluir

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self, text=f"{icons.GRAFICO}  Ordenado por espacio ocupado. "
                       f"«Excluir» añade la extensión al filtro; después hay que "
                       f"volver a escanear.",
            font=styles.fuente_base(11), text_color=styles.COLOR_TEXTO_TENUE,
            wraplength=520, justify="left",
        ).grid(row=0, column=0, padx=16, pady=(14, 6), sticky="w")

        lista = ctk.CTkScrollableFrame(self)
        lista.grid(row=1, column=0, sticky="nsew", padx=12, pady=6)
        lista.grid_columnconfigure(0, weight=1)

        for fila, (ext, cantidad, bytes_) in enumerate(
                resultado.resumen_por_extension()):
            marco = ctk.CTkFrame(lista)
            marco.grid(row=fila, column=0, sticky="ew", pady=3)
            marco.grid_columnconfigure(0, weight=1)
            etiqueta = f".{ext}" if ext != "(sin extensión)" else ext
            ctk.CTkLabel(
                marco,
                text=f"{etiqueta}      {cantidad} archivos   ·   "
                     f"{formatear_tamano(bytes_)}",
                font=styles.fuente_base(12), anchor="w",
            ).grid(row=0, column=0, padx=12, pady=8, sticky="w")
            if ext != "(sin extensión)":
                ctk.CTkButton(marco, text="Excluir", width=80,
                              fg_color="transparent", border_width=1,
                              text_color=styles.COLOR_TEXTO,
                              command=lambda e=ext: self._excluir(e)).grid(
                    row=0, column=1, padx=8, pady=5)

        ctk.CTkButton(self, text="Cerrar", command=self.destroy).grid(
            row=2, column=0, pady=(6, 14))
        self.after(120, self.lift)

    def _excluir(self, ext):
        self._al_excluir(ext)
        self.title(f"Tipos de archivo  ·  .{ext} añadido al filtro")
