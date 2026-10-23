"""Image viewer at (almost) full screen, with zoom and panning.

It opens when a preview is clicked. It lets you see details:
- mouse wheel (or +/− buttons) to zoom in/out,
- drag with the mouse to pan,
- "Fit" to fit the image to the window, "100%" to see it at
  real size.
"""

import os
import tkinter as tk

import customtkinter as ctk
from PIL import Image, ImageOps, ImageTk

from core.app_logging import log

from . import styles
from .thumbnails import IMAGE_EXT

# Limit when loading (px, longer side): avoids exhausting memory with huge
# photos; zoom keeps working within that limit.
_MAX_SIDE = 6000


def can_be_displayed(path):
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    return ext in IMAGE_EXT


class ImageViewer(ctk.CTkToplevel):
    def __init__(self, master, path):
        super().__init__(master)
        self.title(os.path.basename(path))
        self.configure(fg_color=styles.COLOR_BACKGROUND)

        self._orig = None
        try:
            with Image.open(path) as im:
                im = ImageOps.exif_transpose(im).convert("RGB")
                if max(im.size) > _MAX_SIDE:
                    im.thumbnail((_MAX_SIDE, _MAX_SIDE), Image.LANCZOS)
                self._orig = im.copy()
        except Exception:  # the viewer shows "cannot be opened" instead of breaking
            log.warning("No se pudo abrir la imagen %s en el visor", path, exc_info=True)
            self._orig = None

        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = int(sw * 0.85), int(sh * 0.85)
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        bar = ctk.CTkFrame(self)
        bar.pack(fill="x", padx=8, pady=8)
        ctk.CTkButton(bar, text="−", width=40,
                      command=lambda: self._zoom(1 / 1.25)).pack(side="left", padx=2)
        ctk.CTkButton(bar, text="Ajustar", width=90,
                      command=self._fit).pack(side="left", padx=2)
        ctk.CTkButton(bar, text="100 %", width=60,
                      command=lambda: self._set_scale(1.0)).pack(side="left", padx=2)
        ctk.CTkButton(bar, text="+", width=40,
                      command=lambda: self._zoom(1.25)).pack(side="left", padx=2)
        self._lbl_info = ctk.CTkLabel(
            bar, text="", font=styles.base_font(12),
            text_color=styles.COLOR_MUTED_TEXT)
        self._lbl_info.pack(side="left", padx=14)
        ctk.CTkButton(bar, text="Cerrar", width=80,
                      command=self.destroy).pack(side="right", padx=2)

        ctk.CTkLabel(self, text=path, font=styles.base_font(11),
                     text_color=styles.COLOR_MUTED_TEXT, anchor="w").pack(
            fill="x", padx=14, pady=(0, 4))

        cont = ctk.CTkFrame(self, fg_color=styles.COLOR_TABLE_BACKGROUND)
        cont.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        # tk.Canvas is not a CustomTkinter widget: its colour is resolved by hand.
        self.canvas = tk.Canvas(cont, bg=styles.col(styles.COLOR_TABLE_BACKGROUND),
                                highlightthickness=0)
        vsb = ctk.CTkScrollbar(cont, command=self.canvas.yview)
        hsb = ctk.CTkScrollbar(cont, orientation="horizontal",
                               command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)

        self._scale = 1.0
        self._tkimg = None

        self.canvas.bind("<ButtonPress-1>",
                         lambda e: self.canvas.scan_mark(e.x, e.y))
        self.canvas.bind("<B1-Motion>",
                         lambda e: self.canvas.scan_dragto(e.x, e.y, gain=1))
        self.canvas.bind("<MouseWheel>", self._wheel)
        self.bind("<Escape>", lambda _e: self.destroy())

        self.transient(master)
        self.after(60, self._fit)
        self.after(150, self.lift)
        self.after(160, self.focus)

    # ------------------------------------------------------------------
    def _set_appearance_mode(self, mode_string):
        super()._set_appearance_mode(mode_string)
        try:
            self.canvas.configure(bg=styles.col(styles.COLOR_TABLE_BACKGROUND))
            self._redraw()
        except tk.TclError:
            pass

    def _redraw(self):
        self.canvas.delete("all")
        if self._orig is None:
            self.canvas.create_text(
                20, 20, anchor="nw", fill=styles.col(styles.COLOR_TEXT),
                text="No se puede mostrar esta imagen.")
            self._lbl_info.configure(text="")
            return
        w = max(1, int(self._orig.width * self._scale))
        h = max(1, int(self._orig.height * self._scale))
        resampling = Image.LANCZOS if self._scale < 1 else Image.NEAREST
        self._tkimg = ImageTk.PhotoImage(self._orig.resize((w, h), resampling))
        self.canvas.create_image(0, 0, anchor="nw", image=self._tkimg)
        self.canvas.configure(scrollregion=(0, 0, w, h))
        self._lbl_info.configure(
            text=f"{self._orig.width}×{self._orig.height} px   ·   "
                 f"{int(self._scale * 100)} %")

    def _set_scale(self, scale):
        self._scale = max(0.05, min(scale, 8.0))
        self._redraw()

    def _zoom(self, factor):
        self._set_scale(self._scale * factor)

    def _fit(self):
        if self._orig is None:
            self._redraw()
            return
        self.canvas.update_idletasks()
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        if cw < 10 or ch < 10:
            self.after(80, self._fit)
            return
        self._set_scale(min(cw / self._orig.width, ch / self._orig.height, 1.0))

    def _wheel(self, event):
        self._zoom(1.1 if event.delta > 0 else 1 / 1.1)


def open_viewer(master, path):
    """Opens the viewer at almost full screen if `path` is an image that can be shown."""
    if path and can_be_displayed(path) and os.path.isfile(path):
        ImageViewer(master, path)
