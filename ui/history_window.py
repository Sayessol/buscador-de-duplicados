"""Operation history window, with "Undo".

Lists the recorded operations (move to quarantine, gather images)
and lets you revert each one:
- "mover"  -> puts the files back in their place,
- "copiar" -> deletes the copies in the destination (with a clear confirmation).
"""

import os
from tkinter import messagebox

import customtkinter as ctk

from core import history
from core.hashing import format_size  # noqa: F401  (in case it is needed)
from . import styles, icons

_KIND_LABEL = {
    history.KIND_QUARANTINE: "Mover a cuarentena",
    history.KIND_GATHER: "Reunir imágenes",
    history.KIND_GATHER_FOLDER: "Reunir (carpeta entera)",
}


class HistoryWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Historial de operaciones")
        self.geometry("720x560")
        self.configure(fg_color=styles.COLOR_BACKGROUND)
        self.transient(master)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self, text="Cada operación se puede deshacer. «Mover» devuelve los "
                       "archivos a su sitio; «copiar» borra las copias del destino.",
            font=styles.base_font(11), text_color=styles.COLOR_MUTED_TEXT,
            wraplength=680, justify="left").grid(
            row=0, column=0, padx=16, pady=(14, 6), sticky="w")

        self.items = ctk.CTkScrollableFrame(self, fg_color=styles.COLOR_TABLE_BACKGROUND)
        self.items.grid(row=1, column=0, sticky="nsew", padx=12, pady=6)
        self.items.grid_columnconfigure(0, weight=1)

        caption = ctk.CTkFrame(self, fg_color="transparent")
        caption.grid(row=2, column=0, sticky="ew", padx=12, pady=(4, 12))
        ctk.CTkButton(caption, text="Actualizar", width=110, fg_color="transparent",
                      border_width=1, text_color=styles.COLOR_TEXT,
                      command=self._paint).pack(side="left")
        ctk.CTkButton(caption, text="Cerrar", width=100,
                      command=self.destroy).pack(side="right")

        self._paint()
        self.after(150, self.lift)

    # ------------------------------------------------------------------
    def _paint(self):
        for child in self.items.winfo_children():
            child.destroy()

        ops = history.list_all()
        if not ops:
            ctk.CTkLabel(
                self.items, text="Todavía no hay operaciones registradas.",
                font=styles.base_font(12),
                text_color=styles.COLOR_MUTED_TEXT).grid(
                row=0, column=0, padx=16, pady=20)
            return

        for row, op in enumerate(ops):
            self._op_card(row, op)

    def _op_card(self, row, op):
        card = ctk.CTkFrame(self.items, fg_color=styles.COLOR_CARD)
        card.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        card.grid_columnconfigure(0, weight=1)

        kind = _KIND_LABEL.get(op["tipo"], op["tipo"])
        verb = "copiados" if op["accion"] == "copiar" else "movidos"
        n = len(op["movimientos"])
        date = op["fecha"].replace("T", "  ")
        title = f"{kind}  ·  {n} archivo(s) {verb}"
        ctk.CTkLabel(card, text=title, font=styles.base_font(12, "bold"),
                     anchor="w").grid(row=0, column=0, padx=12, pady=(10, 2),
                                      sticky="w")
        sub = f"{date}   →   {op['destino']}"
        ctk.CTkLabel(card, text=sub, font=styles.base_font(11),
                     text_color=styles.COLOR_MUTED_TEXT, anchor="w",
                     wraplength=520, justify="left").grid(
            row=1, column=0, padx=12, pady=(0, 10), sticky="w")

        if op.get("deshecha"):
            ctk.CTkLabel(card, text=f"{icons.OK} deshecha",
                         font=styles.base_font(11),
                         text_color=styles.COLOR_OK).grid(
                row=0, column=1, rowspan=2, padx=12)
        else:
            ctk.CTkButton(
                card, text=f"{icons.RELOAD}  Deshacer", width=120,
                command=lambda o=op: self._undo(o)).grid(
                row=0, column=1, rowspan=2, padx=12, pady=8)

    def _undo(self, op):
        n = len(op["movimientos"])
        if op["accion"] == "copiar":
            warning = (f"Se van a BORRAR {n} archivo(s) copiados en:\n\n"
                     f"{op['destino']}\n\n"
                     "Son las copias que hizo la app. Los originales no se "
                     "tocan. Esta acción no se puede deshacer.\n\n¿Continuar?")
        else:
            warning = (f"Se van a devolver {n} archivo(s) a su ubicación "
                     f"original (desde {op['destino']}).\n\n¿Continuar?")
        if not messagebox.askyesno("Deshacer operación", warning, parent=self):
            return

        res = history.undo(op["id"])
        self._paint()

        if res["fallos"]:
            detail = "\n".join(f"· {os.path.basename(r) or r}: {m}"
                                for r, m in res["fallos"][:12])
            messagebox.showwarning(
                "Deshacer con avisos",
                f"Revertidos: {res['ok']}.\nNo se pudieron revertir "
                f"{len(res['fallos'])}:\n\n{detail}", parent=self)
        else:
            messagebox.showinfo(
                "Hecho", f"Operación deshecha: {res['ok']} archivo(s).",
                parent=self)
