"""Window with the breakdown of duplicates by extension."""

import customtkinter as ctk

from core.hashing import format_size
from . import styles
from . import icons


class ExtensionBreakdownWindow(ctk.CTkToplevel):
    """Breakdown of the duplicates by extension, with an option to exclude."""

    def __init__(self, master, result, on_exclude):
        super().__init__(master)
        self.title("Tipos de archivo entre los duplicados")
        self.geometry("560x480")
        self.transient(master)
        self._on_exclude = on_exclude

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self, text=f"{icons.CHART}  Ordenado por espacio ocupado. "
                       f"«Excluir» añade la extensión al filtro; después hay que "
                       f"volver a escanear.",
            font=styles.base_font(11), text_color=styles.COLOR_MUTED_TEXT,
            wraplength=520, justify="left",
        ).grid(row=0, column=0, padx=16, pady=(14, 6), sticky="w")

        items = ctk.CTkScrollableFrame(self)
        items.grid(row=1, column=0, sticky="nsew", padx=12, pady=6)
        items.grid_columnconfigure(0, weight=1)

        for row, (ext, count, bytes_) in enumerate(
                result.summary_by_extension()):
            frame = ctk.CTkFrame(items)
            frame.grid(row=row, column=0, sticky="ew", pady=3)
            frame.grid_columnconfigure(0, weight=1)
            label = f".{ext}" if ext != "(sin extensión)" else ext
            ctk.CTkLabel(
                frame,
                text=f"{label}      {count} archivos   ·   "
                     f"{format_size(bytes_)}",
                font=styles.base_font(12), anchor="w",
            ).grid(row=0, column=0, padx=12, pady=8, sticky="w")
            if ext != "(sin extensión)":
                ctk.CTkButton(frame, text="Excluir", width=80,
                              fg_color="transparent", border_width=1,
                              text_color=styles.COLOR_TEXT,
                              command=lambda e=ext: self._exclude(e)).grid(
                    row=0, column=1, padx=8, pady=5)

        ctk.CTkButton(self, text="Cerrar", command=self.destroy).grid(
            row=2, column=0, pady=(6, 14))
        self.after(120, self.lift)

    def _exclude(self, ext):
        self._on_exclude(ext)
        self.title(f"Tipos de archivo  ·  .{ext} añadido al filtro")
