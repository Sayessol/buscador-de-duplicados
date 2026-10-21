"""Piezas visuales reutilizables para la ventana principal."""

import customtkinter as ctk

from . import styles


class CabeceraSeccion(ctk.CTkFrame):
    """Fila de título de una sección: número en un círculo + texto."""

    def __init__(self, master, numero, texto, icono="", **kw):
        super().__init__(master, fg_color="transparent", **kw)
        insignia = ctk.CTkLabel(
            self, text=str(numero), width=22, height=22,
            corner_radius=11, fg_color=styles.COLOR_SELECCION,
            text_color="#ffffff", font=styles.fuente_base(11, "bold"))
        insignia.pack(side="left", padx=(0, 8))
        etiqueta = f"{icono}  {texto}" if icono else texto
        ctk.CTkLabel(self, text=etiqueta,
                     font=styles.fuente_titulo(14)).pack(side="left")


class Baldosa(ctk.CTkFrame):
    """Recuadro con un número grande y una etiqueta debajo."""

    def __init__(self, master, etiqueta, **kw):
        super().__init__(master, fg_color=styles.COLOR_BALDOSA,
                         corner_radius=8, **kw)
        self._valor = ctk.CTkLabel(self, text="—", font=styles.fuente_numero(19),
                                   text_color=styles.COLOR_TEXTO)
        self._valor.pack(padx=14, pady=(8, 0), anchor="w")
        ctk.CTkLabel(self, text=etiqueta, font=styles.fuente_base(11),
                     text_color=styles.COLOR_TEXTO_TENUE).pack(
            padx=14, pady=(0, 8), anchor="w")

    def set(self, texto, color=None):
        self._valor.configure(text=str(texto),
                              text_color=color or styles.COLOR_TEXTO)


class EstadoVacio(ctk.CTkFrame):
    """Mensaje centrado para cuando la tabla no tiene resultados."""

    def __init__(self, master, icono, titulo, detalle, **kw):
        super().__init__(master, fg_color=styles.COLOR_FONDO_TABLA,
                         corner_radius=8, **kw)
        centro = ctk.CTkFrame(self, fg_color="transparent")
        centro.place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(centro, text=icono,
                     font=styles.fuente_base(46)).pack(pady=(0, 10))
        self._titulo = ctk.CTkLabel(centro, text=titulo,
                                    font=styles.fuente_titulo(15))
        self._titulo.pack()
        self._detalle = ctk.CTkLabel(
            centro, text=detalle, font=styles.fuente_base(12),
            text_color=styles.COLOR_TEXTO_TENUE, wraplength=420,
            justify="center")
        self._detalle.pack(pady=(4, 0))

    def configurar(self, titulo=None, detalle=None):
        if titulo is not None:
            self._titulo.configure(text=titulo)
        if detalle is not None:
            self._detalle.configure(text=detalle)


def tarjeta(parent, row):
    """Tarjeta de sección: un marco con fondo de tarjeta que ocupa una fila del padre."""
    t = ctk.CTkFrame(parent, fg_color=styles.COLOR_TARJETA)
    t.grid(row=row, column=0, sticky="ew", padx=6, pady=(8, 0))
    t.grid_columnconfigure(0, weight=1)
    return t
