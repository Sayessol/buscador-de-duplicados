"""Main window of the app.

Only the "shell" stays here: header (theme, view, history), the
tab selector and the Simple / Advanced mode. Each tab is a
COMPONENT with its own state, in its own module:

  exact_duplicates_tab.py   ExactDuplicatesTab   "Exact duplicates"  -> self.exact
  similar_photos_tab.py     SimilarPhotosTab      "Similar photos"    -> self.similar
  gather_images_tab.py      GatherImagesTab       "Gather images"     -> self.gather

The window only creates the three components and notifies them of two things:
`apply_mode(advanced)` when switching between Simple and Advanced, and
`cancel_jobs()` when closing. None of them touches the state of the others.

Every long task (scan, analyze, move) uses the same pattern:
thread + queue + after(); it is explained in
exact_duplicates_tab.py:_scan_job.

Interface in European Spanish, light/dark theme, icons made of Unicode glyphs.
"""
from pathlib import Path
from tkinter import TclError, messagebox

import customtkinter as ctk

from core import __version__, config, app_logging
from core.app_logging import log
from . import styles
from . import icons
from .history_window import HistoryWindow
from .exact_duplicates_tab import ExactDuplicatesTab
from .gather_images_tab import GatherImagesTab
from .similar_photos_tab import SimilarPhotosTab


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"Buscador de duplicados {__version__}")
        self.geometry("1240x900")
        self.minsize(920, 640)
        self._set_window_icon()

        self._mode = config.get_mode()  # "simple" | "advanced"
        self._error_warned = False     # the unexpected-error warning appears only once

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()

        self.tabs = ctk.CTkTabview(self, fg_color="transparent")
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=10, pady=(2, 0))
        self.tab_exact = self.tabs.add(f"{icons.SEARCH}  Duplicados exactos")
        self.tab_similar = self.tabs.add(f"{icons.CAT_IMAGES}  Fotos parecidas")
        self.tab_gather = self.tabs.add(f"{icons.GATHER}  Reunir imágenes")

        self.exact = ExactDuplicatesTab(self.tab_exact, self._mode == "advanced")
        self.similar = SimilarPhotosTab(self.tab_similar)
        self.gather = GatherImagesTab(self.tab_gather)

        self._apply_mode()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def report_callback_exception(self, exc, val, tb):
        """Tkinter calls this when a button or timer callback fails.

        By default the error only went to the console, which does not exist in the .exe.
        It is logged and the user is warned once, so as not to fill the screen
        with windows if the same failure repeats.
        """
        log.error("Error inesperado en la interfaz", exc_info=(exc, val, tb))
        if self._error_warned:
            return
        self._error_warned = True
        path = app_logging.file_path()
        where = (f"Se ha anotado en el registro:\n{path}" if path
                 else "No se ha podido guardar el registro.")
        messagebox.showerror(
            "Error inesperado",
            f"Ha ocurrido un error inesperado ({exc.__name__}: {val}).\n\n{where}\n\n"
            "Puedes seguir usando la aplicación; si el fallo se repite, cierra y "
            "vuelve a abrirla. Tus archivos no se han tocado.")

    def _set_window_icon(self):
        """Icon of the title bar / taskbar.

        CustomTkinter sets its own icon 200 ms after creating the
        window, unless iconbitmap() has already been called — that is
        why iconbitmap() is used with an .ico (not iconphoto with a
        PhotoImage), so that its internal check detects it and does not
        overwrite it. icono.ico is generated with `python gen_icon.py`; if it does not
        exist (for example, in a clean checkout where it has not been generated yet)
        the window keeps working with the default icon.
        """
        ico_path = Path(__file__).resolve().parent.parent / "icono.ico"
        try:
            if ico_path.exists():
                self.iconbitmap(str(ico_path))
        except TclError:  # the icon is optional
            log.info("No se pudo poner el icono de la ventana", exc_info=True)

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=styles.COLOR_HEADER, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(header, text=icons.SEARCH, font=styles.base_font(24)).grid(
            row=0, column=0, rowspan=2, padx=(18, 12), pady=12)
        title = ctk.CTkFrame(header, fg_color="transparent")
        title.grid(row=0, column=1, sticky="sw", pady=(12, 0))
        ctk.CTkLabel(title, text="Buscador de duplicados",
                     font=styles.title_font(17)).pack(side="left")
        ctk.CTkLabel(title, text=f"v{__version__}", font=styles.base_font(11),
                     text_color=styles.COLOR_MUTED_TEXT).pack(
            side="left", padx=(8, 0), pady=(4, 0))
        ctk.CTkLabel(
            header, text="Encuentra archivos repetidos y muévelos a cuarentena. "
                      "Nunca se borran tus originales.",
            font=styles.base_font(11), text_color=styles.COLOR_MUTED_TEXT).grid(
            row=1, column=1, sticky="nw", pady=(0, 12))

        self.btn_history = ctk.CTkButton(
            header, text=f"{icons.HISTORY}  Historial", width=115,
            fg_color="transparent", border_width=1,
            border_color=styles.COLOR_BORDER, text_color=styles.COLOR_TEXT,
            hover_color=styles.COLOR_TILE, command=self._open_history)
        self.btn_history.grid(row=0, column=2, rowspan=2, padx=(8, 12), pady=12)

        # Right panel: theme selector (top) and view selector (bottom).
        right = ctk.CTkFrame(header, fg_color="transparent")
        right.grid(row=0, column=3, rowspan=2, padx=(0, 16), pady=10)

        ctk.CTkLabel(right, text="Tema:", font=styles.base_font(11),
                     text_color=styles.COLOR_MUTED_TEXT).grid(
            row=0, column=0, padx=(0, 6), pady=(0, 4), sticky="e")
        self.theme_selector = ctk.CTkOptionMenu(
            right, values=["Automático", "Claro", "Oscuro"], width=118,
            command=self._change_theme)
        self.theme_selector.set({"auto": "Automático", "light": "Claro",
                                "dark": "Oscuro"}[config.get_theme()])
        self.theme_selector.grid(row=0, column=1, pady=(0, 4), sticky="w")

        ctk.CTkLabel(right, text="Vista:", font=styles.base_font(11),
                     text_color=styles.COLOR_MUTED_TEXT).grid(
            row=1, column=0, padx=(0, 6), sticky="e")
        self.mode_selector = ctk.CTkSegmentedButton(
            right, values=["Sencilla", "Avanzada"], command=self._change_mode)
        self.mode_selector.set("Sencilla" if self._mode == "simple"
                               else "Avanzada")
        self.mode_selector.grid(row=1, column=1, sticky="w")

    def _open_history(self):
        HistoryWindow(self)

    def _change_theme(self, label):
        theme = {"Automático": "auto", "Claro": "light", "Oscuro": "dark"}[label]
        config.set_theme(theme)
        styles.change_theme(theme)     # CustomTkinter repaints; ttk does it in _set_appearance_mode

    def _change_mode(self, value):
        """Called by the switch in the header."""
        self._mode = "simple" if value == "Sencilla" else "advanced"
        config.set_mode(self._mode)          # remembered for next time
        self._apply_mode()
        if self._mode == "simple":
            self.exact.on_switch_to_simple()

    def _apply_mode(self):
        """Shows or hides the "advanced" controls. It does not delete widgets:
        it only removes/puts them back in the grid with grid_remove()/grid(), so the
        state is kept when toggling."""
        advanced = self._mode == "advanced"

        # "Exact duplicates" tab: in Simple mode the options panel,
        # the preferred folder, "View kinds" and "Export CSV" are hidden.
        self.exact.apply_mode(advanced)

        # "Similar photos" tab: the sensitivity slider only in Advanced.
        self.similar.apply_mode(advanced)

        # "History" only in Advanced.
        (self.btn_history.grid if advanced else self.btn_history.grid_remove)()

        # "Gather images": "Whole folder" and Move/Copy only in Advanced.
        self.gather.apply_mode(advanced)

    def _on_close(self):
        self.exact.cancel_jobs()
        self.similar.cancel_jobs()
        self.gather.cancel_jobs()
        self.destroy()


def launch():
    # Applies the saved theme (auto/light/dark) BEFORE creating the window.
    styles.apply_theme(config.get_theme())
    app = MainWindow()
    app.mainloop()
