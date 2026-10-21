"""Diálogo: qué hacer con los archivos que no son imágenes.

Por cada tipo (extensión) encontrado, el usuario elige:
  · Dejar     -> no se mueve, se queda en el origen.
  · Mover     -> va al destino con su misma subruta (como las imágenes).
  · Agrupar   -> va a  destino/<carpeta que nombra el usuario>/<subruta>.
"""

import customtkinter as ctk

from core.reunir import ReglasNoImagen, DEJAR, AGRUPAR
from core.mover import MOVER
from . import styles

_NOMBRE_CARPETA = {
    "pdf": "Documentos", "doc": "Documentos", "docx": "Documentos",
    "xls": "Documentos", "xlsx": "Documentos", "txt": "Documentos",
    "mp3": "Música", "wav": "Música", "flac": "Música",
    "mp4": "Vídeos", "mkv": "Vídeos", "avi": "Vídeos",
    "zip": "Comprimidos", "rar": "Comprimidos", "7z": "Comprimidos",
}


class VentanaTiposNoImagen(ctk.CTkToplevel):
    def __init__(self, master, tipos):
        """tipos: dict  ext -> lista de rutas."""
        super().__init__(master)
        self.title("Archivos que no son imágenes")
        self.geometry("620x460")
        self.configure(fg_color=styles.COLOR_FONDO)
        self.transient(master)
        self.grab_set()

        self.reglas = None          # se rellena al pulsar "Aplicar"
        self._filas = {}            # ext -> (segmented, entry)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self, text="En esas carpetas también hay archivos que no son "
                       "imágenes. Elige qué hacer con cada tipo:",
            font=styles.fuente_base(12), wraplength=580, justify="left",
            anchor="w").grid(row=0, column=0, padx=16, pady=(14, 8), sticky="w")

        lista = ctk.CTkScrollableFrame(self, fg_color=styles.COLOR_FONDO_TABLA)
        lista.grid(row=1, column=0, sticky="nsew", padx=12, pady=6)
        lista.grid_columnconfigure(0, weight=1)

        for i, (ext, rutas) in enumerate(tipos.items()):
            self._fila(lista, i, ext, len(rutas))

        pie = ctk.CTkFrame(self, fg_color="transparent")
        pie.grid(row=2, column=0, sticky="ew", padx=12, pady=(4, 12))
        ctk.CTkButton(pie, text="Cancelar", width=100, fg_color="transparent",
                      border_width=1, text_color=styles.COLOR_TEXTO,
                      command=self._cancelar).pack(side="right", padx=4)
        ctk.CTkButton(pie, text="Aplicar", width=110,
                      command=self._aplicar).pack(side="right", padx=4)

        self.after(150, self.lift)
        self.protocol("WM_DELETE_WINDOW", self._cancelar)

    def _fila(self, parent, i, ext, cuantos):
        marco = ctk.CTkFrame(parent, fg_color=styles.COLOR_TARJETA)
        marco.grid(row=i, column=0, sticky="ew", pady=(0, 6))
        marco.grid_columnconfigure(1, weight=1)

        etiqueta = f".{ext}" if ext != "(sin extensión)" else ext
        ctk.CTkLabel(marco, text=f"{etiqueta}   ({cuantos})",
                     font=styles.fuente_base(12, "bold"), width=110,
                     anchor="w").grid(row=0, column=0, padx=(12, 8), pady=10,
                                      sticky="w")

        seg = ctk.CTkSegmentedButton(
            marco, values=["Dejar", "Mover", "Agrupar"],
            command=lambda _v, e=ext: self._toggle_entry(e))
        seg.set("Dejar")
        seg.grid(row=0, column=1, padx=4, pady=10, sticky="w")

        entry = ctk.CTkEntry(marco, width=150, placeholder_text="nombre carpeta")
        entry.insert(0, _NOMBRE_CARPETA.get(ext, ext.capitalize() or "Otros"))
        entry.configure(state="disabled")
        entry.grid(row=0, column=2, padx=(4, 12), pady=10)

        self._filas[ext] = (seg, entry)

    def _toggle_entry(self, ext):
        seg, entry = self._filas[ext]
        entry.configure(state="normal" if seg.get() == "Agrupar" else "disabled")

    def _aplicar(self):
        acciones, carpetas = {}, {}
        for ext, (seg, entry) in self._filas.items():
            elegido = seg.get()
            if elegido == "Mover":
                acciones[ext] = MOVER
            elif elegido == "Agrupar":
                acciones[ext] = AGRUPAR
                carpetas[ext] = entry.get().strip() or ext
            else:
                acciones[ext] = DEJAR
        self.reglas = ReglasNoImagen(accion_por_ext=acciones,
                                     carpeta_por_ext=carpetas)
        self.grab_release()
        self.destroy()

    def _cancelar(self):
        self.reglas = None
        self.grab_release()
        self.destroy()
