"""Ventana de historial de operaciones, con "Deshacer".

Lista las operaciones registradas (mover a cuarentena, reunir imágenes)
y permite revertir cada una:
- "mover"  -> devuelve los archivos a su sitio,
- "copiar" -> borra las copias del destino (con confirmación clara).
"""

import os
from tkinter import messagebox

import customtkinter as ctk

from core import historial
from core.hashing import formatear_tamano  # noqa: F401  (por si hace falta)
from . import styles, icons

_ETIQUETA_TIPO = {
    historial.TIPO_CUARENTENA: "Mover a cuarentena",
    historial.TIPO_REUNIR: "Reunir imágenes",
    historial.TIPO_REUNIR_CARPETA: "Reunir (carpeta entera)",
}


class VentanaHistorial(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Historial de operaciones")
        self.geometry("720x560")
        self.configure(fg_color=styles.COLOR_FONDO)
        self.transient(master)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self, text="Cada operación se puede deshacer. «Mover» devuelve los "
                       "archivos a su sitio; «copiar» borra las copias del destino.",
            font=styles.fuente_base(11), text_color=styles.COLOR_TEXTO_TENUE,
            wraplength=680, justify="left").grid(
            row=0, column=0, padx=16, pady=(14, 6), sticky="w")

        self.lista = ctk.CTkScrollableFrame(self, fg_color=styles.COLOR_FONDO_TABLA)
        self.lista.grid(row=1, column=0, sticky="nsew", padx=12, pady=6)
        self.lista.grid_columnconfigure(0, weight=1)

        pie = ctk.CTkFrame(self, fg_color="transparent")
        pie.grid(row=2, column=0, sticky="ew", padx=12, pady=(4, 12))
        ctk.CTkButton(pie, text="Actualizar", width=110, fg_color="transparent",
                      border_width=1, text_color=styles.COLOR_TEXTO,
                      command=self._pintar).pack(side="left")
        ctk.CTkButton(pie, text="Cerrar", width=100,
                      command=self.destroy).pack(side="right")

        self._pintar()
        self.after(150, self.lift)

    # ------------------------------------------------------------------
    def _pintar(self):
        for hijo in self.lista.winfo_children():
            hijo.destroy()

        ops = historial.listar()
        if not ops:
            ctk.CTkLabel(
                self.lista, text="Todavía no hay operaciones registradas.",
                font=styles.fuente_base(12),
                text_color=styles.COLOR_TEXTO_TENUE).grid(
                row=0, column=0, padx=16, pady=20)
            return

        for fila, op in enumerate(ops):
            self._tarjeta_op(fila, op)

    def _tarjeta_op(self, fila, op):
        card = ctk.CTkFrame(self.lista, fg_color=styles.COLOR_TARJETA)
        card.grid(row=fila, column=0, sticky="ew", pady=(0, 8))
        card.grid_columnconfigure(0, weight=1)

        tipo = _ETIQUETA_TIPO.get(op["tipo"], op["tipo"])
        verbo = "copiados" if op["accion"] == "copiar" else "movidos"
        n = len(op["movimientos"])
        fecha = op["fecha"].replace("T", "  ")
        titulo = f"{tipo}  ·  {n} archivo(s) {verbo}"
        ctk.CTkLabel(card, text=titulo, font=styles.fuente_base(12, "bold"),
                     anchor="w").grid(row=0, column=0, padx=12, pady=(10, 2),
                                      sticky="w")
        sub = f"{fecha}   →   {op['destino']}"
        ctk.CTkLabel(card, text=sub, font=styles.fuente_base(11),
                     text_color=styles.COLOR_TEXTO_TENUE, anchor="w",
                     wraplength=520, justify="left").grid(
            row=1, column=0, padx=12, pady=(0, 10), sticky="w")

        if op.get("deshecha"):
            ctk.CTkLabel(card, text=f"{icons.OK} deshecha",
                         font=styles.fuente_base(11),
                         text_color=styles.COLOR_OK).grid(
                row=0, column=1, rowspan=2, padx=12)
        else:
            ctk.CTkButton(
                card, text=f"{icons.RECARGA}  Deshacer", width=120,
                command=lambda o=op: self._deshacer(o)).grid(
                row=0, column=1, rowspan=2, padx=12, pady=8)

    def _deshacer(self, op):
        n = len(op["movimientos"])
        if op["accion"] == "copiar":
            aviso = (f"Se van a BORRAR {n} archivo(s) copiados en:\n\n"
                     f"{op['destino']}\n\n"
                     "Son las copias que hizo la app. Los originales no se "
                     "tocan. Esta acción no se puede deshacer.\n\n¿Continuar?")
        else:
            aviso = (f"Se van a devolver {n} archivo(s) a su ubicación "
                     f"original (desde {op['destino']}).\n\n¿Continuar?")
        if not messagebox.askyesno("Deshacer operación", aviso, parent=self):
            return

        res = historial.deshacer(op["id"])
        self._pintar()

        if res["fallos"]:
            detalle = "\n".join(f"· {os.path.basename(r) or r}: {m}"
                                for r, m in res["fallos"][:12])
            messagebox.showwarning(
                "Deshacer con avisos",
                f"Revertidos: {res['ok']}.\nNo se pudieron revertir "
                f"{len(res['fallos'])}:\n\n{detalle}", parent=self)
        else:
            messagebox.showinfo(
                "Hecho", f"Operación deshecha: {res['ok']} archivo(s).",
                parent=self)
