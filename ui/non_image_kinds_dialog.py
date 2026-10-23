"""Diálogo: qué hacer con los archivos que no son imágenes.

Por cada tipo (extensión) encontrado, el usuario elige:
  · Dejar     -> no se mueve, se queda en el origen.
  · Mover     -> va al destino con su misma subruta (como las imágenes).
  · Agrupar   -> va a  destino/<carpeta que nombra el usuario>/<subruta>.
"""

import customtkinter as ctk

from core.gather import NonImageRules, LEAVE, GROUP
from core.file_moves import MOVE
from . import styles

_FOLDER_NAME = {
    "pdf": "Documentos", "doc": "Documentos", "docx": "Documentos",
    "xls": "Documentos", "xlsx": "Documentos", "txt": "Documentos",
    "mp3": "Música", "wav": "Música", "flac": "Música",
    "mp4": "Vídeos", "mkv": "Vídeos", "avi": "Vídeos",
    "zip": "Comprimidos", "rar": "Comprimidos", "7z": "Comprimidos",
}


class NonImageKindsWindow(ctk.CTkToplevel):
    def __init__(self, master, kinds):
        """tipos: dict  ext -> lista de rutas."""
        super().__init__(master)
        self.title("Archivos que no son imágenes")
        self.geometry("620x460")
        self.configure(fg_color=styles.COLOR_BACKGROUND)
        self.transient(master)
        self.grab_set()

        self.rules = None          # se rellena al pulsar "Aplicar"
        self._rows = {}            # ext -> (segmented, entry)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self, text="En esas carpetas también hay archivos que no son "
                       "imágenes. Elige qué hacer con cada tipo:",
            font=styles.base_font(12), wraplength=580, justify="left",
            anchor="w").grid(row=0, column=0, padx=16, pady=(14, 8), sticky="w")

        items = ctk.CTkScrollableFrame(self, fg_color=styles.COLOR_TABLE_BACKGROUND)
        items.grid(row=1, column=0, sticky="nsew", padx=12, pady=6)
        items.grid_columnconfigure(0, weight=1)

        for i, (ext, paths) in enumerate(kinds.items()):
            self._row(items, i, ext, len(paths))

        caption = ctk.CTkFrame(self, fg_color="transparent")
        caption.grid(row=2, column=0, sticky="ew", padx=12, pady=(4, 12))
        ctk.CTkButton(caption, text="Cancelar", width=100, fg_color="transparent",
                      border_width=1, text_color=styles.COLOR_TEXT,
                      command=self._cancel).pack(side="right", padx=4)
        ctk.CTkButton(caption, text="Aplicar", width=110,
                      command=self._apply).pack(side="right", padx=4)

        self.after(150, self.lift)
        self.protocol("WM_DELETE_WINDOW", self._cancel)

    def _row(self, parent, i, ext, how_many):
        frame = ctk.CTkFrame(parent, fg_color=styles.COLOR_CARD)
        frame.grid(row=i, column=0, sticky="ew", pady=(0, 6))
        frame.grid_columnconfigure(1, weight=1)

        label = f".{ext}" if ext != "(sin extensión)" else ext
        ctk.CTkLabel(frame, text=f"{label}   ({how_many})",
                     font=styles.base_font(12, "bold"), width=110,
                     anchor="w").grid(row=0, column=0, padx=(12, 8), pady=10,
                                      sticky="w")

        seg = ctk.CTkSegmentedButton(
            frame, values=["Dejar", "Mover", "Agrupar"],
            command=lambda _v, e=ext: self._toggle_entry(e))
        seg.set("Dejar")
        seg.grid(row=0, column=1, padx=4, pady=10, sticky="w")

        entry = ctk.CTkEntry(frame, width=150, placeholder_text="nombre carpeta")
        entry.insert(0, _FOLDER_NAME.get(ext, ext.capitalize() or "Otros"))
        entry.configure(state="disabled")
        entry.grid(row=0, column=2, padx=(4, 12), pady=10)

        self._rows[ext] = (seg, entry)

    def _toggle_entry(self, ext):
        seg, entry = self._rows[ext]
        entry.configure(state="normal" if seg.get() == "Agrupar" else "disabled")

    def _apply(self):
        actions, folders = {}, {}
        for ext, (seg, entry) in self._rows.items():
            chosen = seg.get()
            if chosen == "Mover":
                actions[ext] = MOVE
            elif chosen == "Agrupar":
                actions[ext] = GROUP
                folders[ext] = entry.get().strip() or ext
            else:
                actions[ext] = LEAVE
        self.rules = NonImageRules(action_by_ext=actions,
                                     folder_by_ext=folders)
        self.grab_release()
        self.destroy()

    def _cancel(self):
        self.rules = None
        self.grab_release()
        self.destroy()
