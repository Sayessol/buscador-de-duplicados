"""The panel with the large preview of the selected file, its details and a click to enlarge."""

import datetime
import logging
import os

import customtkinter as ctk

from duplicate_finder.domain.formatting import format_size
from duplicate_finder.i18n import tr

from . import icons, styles
from .image_viewer import can_be_displayed, open_viewer
from .thumbnails import IMAGE_EXT, large_preview

log = logging.getLogger(__name__)


class PreviewPanel(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=styles.COLOR_CARD, width=290, **kwargs)
        self.grid_propagate(False)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.path = None
        self._ctk_image = None
        self.image_label = ctk.CTkLabel(
            self,
            text=tr("exact.preview_hint"),
            font=styles.base_font(12),
            text_color=styles.COLOR_MUTED_TEXT,
        )
        self.image_label.grid(row=0, column=0, padx=12, pady=12)
        self.image_label.bind("<Button-1>", lambda _e: self._open_viewer())
        self.name_label = ctk.CTkLabel(
            self,
            text="",
            font=styles.base_font(12, "bold"),
            wraplength=262,
            justify="left",
            anchor="w",
        )
        self.name_label.grid(row=1, column=0, padx=12, pady=(0, 2), sticky="w")
        self.meta_label = ctk.CTkLabel(
            self,
            text="",
            font=styles.base_font(11),
            text_color=styles.COLOR_MUTED_TEXT,
            wraplength=262,
            justify="left",
            anchor="w",
        )
        self.meta_label.grid(row=2, column=0, padx=12, pady=(0, 4), sticky="w")
        self.enlarge_label = ctk.CTkLabel(
            self, text="", font=styles.base_font(11), text_color=styles.COLOR_ACCENT, anchor="w"
        )
        self.enlarge_label.grid(row=3, column=0, padx=12, pady=(0, 12), sticky="w")
        self.enlarge_label.bind("<Button-1>", lambda _e: self._open_viewer())

    def _open_viewer(self):
        open_viewer(self.winfo_toplevel(), self.path)

    def _clear_image(self):
        """Clears the image of the panel.

        CTkLabel.configure(image=None) does NOT remove the image that was already being
        shown (a known CustomTkinter 5.2.2 bug), so the tkinter
        Label inside is cleared instead.
        """
        self.image_label.configure(image=None)
        self.image_label._label.configure(image="")
        self._ctk_image = None

    def show(self, path):
        """Shows the large preview of `path` (None empties the panel)."""
        self.path = path
        if not path:
            self._clear_image()
            self.image_label.configure(text=tr("exact.preview_hint"))
            self.name_label.configure(text="")
            self.meta_label.configure(text="")
            self.enlarge_label.configure(text="")
            return

        try:
            pil = large_preview(path)
        except Exception:  # no preview; it is logged so it can be investigated
            log.warning("Could not show the preview of %s", path, exc_info=True)
            pil = None
        if pil is not None:
            img = ctk.CTkImage(light_image=pil, dark_image=pil, size=(pil.width, pil.height))
            self._ctk_image = img  # keep the reference
            self.image_label.configure(image=img, text="")
        else:
            self._clear_image()
            self.image_label.configure(text=tr("exact.no_preview"))

        self.name_label.configure(text=os.path.basename(path))
        parts = [os.path.dirname(path)]
        data = []
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        if ext in IMAGE_EXT:
            try:
                from PIL import Image

                with Image.open(path) as im:
                    data.append(f"{im.width}×{im.height}")
            except (OSError, ValueError):  # if it cannot be read, the resolution is omitted
                pass
        try:
            st = os.stat(path)
            data.append(format_size(st.st_size))
            data.append(
                datetime.datetime.fromtimestamp(st.st_mtime).strftime(tr("common.date_format"))
            )
        except OSError:
            pass
        if data:
            parts.append("   ·   ".join(data))
        self.meta_label.configure(text="\n".join(parts))
        self.enlarge_label.configure(
            text=f"{icons.SEARCH}  {tr('exact.click_to_enlarge')}" if can_be_displayed(path) else ""
        )
