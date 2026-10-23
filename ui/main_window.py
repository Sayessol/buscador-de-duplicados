"""Ventana principal de la app.

Aquí queda solo la "carcasa": cabecera (tema, vista, historial), el
selector de pestañas y el modo Sencilla / Avanzada. Cada pestaña es un
COMPONENTE con su propio estado, en su propio módulo:

  exact_duplicates_tab.py     ExactDuplicatesTab     "Duplicados exactos"  -> self.exactos
  similar_photos_tab.py   SimilarPhotosTab   "Fotos parecidas"     -> self.parecidas
  gather_images_tab.py      GatherImagesTab      "Reunir imágenes"     -> self.reunir

La ventana solo crea los tres componentes y les avisa de dos cosas:
`aplicar_modo(avanzado)` al cambiar entre Sencilla y Avanzada y
`cancel_jobs()` al cerrar. Ninguno toca el estado de los otros.

Toda tarea larga (escanear, analizar, mover) usa el mismo patrón
hilo + cola + after(); está explicado en
exact_duplicates_tab.py:_trabajo_escaneo.

Interfaz en español de España, tema claro/oscuro, iconos con glifos Unicode.
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

        self._mode = config.get_mode()  # "sencillo" | "avanzado"
        self._error_warned = False     # el aviso de error inesperado sale una sola vez

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()

        self.tabs = ctk.CTkTabview(self, fg_color="transparent")
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=10, pady=(2, 0))
        self.tab_exact = self.tabs.add(f"{icons.SEARCH}  Duplicados exactos")
        self.tab_similar = self.tabs.add(f"{icons.CAT_IMAGES}  Fotos parecidas")
        self.tab_gather = self.tabs.add(f"{icons.GATHER}  Reunir imágenes")

        self.exact = ExactDuplicatesTab(self.tab_exact, self._mode == "avanzado")
        self.similar = SimilarPhotosTab(self.tab_similar)
        self.gather = GatherImagesTab(self.tab_gather)

        self._apply_mode()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def report_callback_exception(self, exc, val, tb):
        """Tkinter llama aquí cuando falla una función de un botón o un temporizador.

        Por defecto el error solo salía por la consola, que en el .exe no existe.
        Se anota en el registro y se avisa una vez, para no llenar la pantalla
        de ventanas si el mismo fallo se repite.
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
        """Icono de la barra de título / barra de tareas.

        CustomTkinter pone su propio icono 200 ms después de crear la
        ventana, salvo que ya se haya llamado a iconbitmap() antes — por
        eso se usa iconbitmap() con un .ico (no iconphoto con un
        PhotoImage), para que la comprobación interna lo detecte y no lo
        pise. icono.ico se genera con `python gen_icon.py`; si no
        existe (por ejemplo, en un checkout limpio sin generarlo todavía)
        la ventana sigue funcionando con el icono por defecto.
        """
        ico_path = Path(__file__).resolve().parent.parent / "icono.ico"
        try:
            if ico_path.exists():
                self.iconbitmap(str(ico_path))
        except TclError:  # el icono es opcional
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

        # Panel derecho: selector de tema (arriba) y de vista (abajo).
        right = ctk.CTkFrame(header, fg_color="transparent")
        right.grid(row=0, column=3, rowspan=2, padx=(0, 16), pady=10)

        ctk.CTkLabel(right, text="Tema:", font=styles.base_font(11),
                     text_color=styles.COLOR_MUTED_TEXT).grid(
            row=0, column=0, padx=(0, 6), pady=(0, 4), sticky="e")
        self.theme_selector = ctk.CTkOptionMenu(
            right, values=["Automático", "Claro", "Oscuro"], width=118,
            command=self._change_theme)
        self.theme_selector.set({"auto": "Automático", "claro": "Claro",
                                "oscuro": "Oscuro"}[config.get_theme()])
        self.theme_selector.grid(row=0, column=1, pady=(0, 4), sticky="w")

        ctk.CTkLabel(right, text="Vista:", font=styles.base_font(11),
                     text_color=styles.COLOR_MUTED_TEXT).grid(
            row=1, column=0, padx=(0, 6), sticky="e")
        self.mode_selector = ctk.CTkSegmentedButton(
            right, values=["Sencilla", "Avanzada"], command=self._change_mode)
        self.mode_selector.set("Sencilla" if self._mode == "sencillo"
                               else "Avanzada")
        self.mode_selector.grid(row=1, column=1, sticky="w")

    def _open_history(self):
        HistoryWindow(self)

    def _change_theme(self, label):
        theme = {"Automático": "auto", "Claro": "claro", "Oscuro": "oscuro"}[label]
        config.set_theme(theme)
        styles.change_theme(theme)     # CustomTkinter re-pinta; ttk lo hace en _set_appearance_mode

    def _change_mode(self, value):
        """Lo llama el interruptor de la cabecera."""
        self._mode = "sencillo" if value == "Sencilla" else "avanzado"
        config.set_mode(self._mode)          # se recuerda para la próxima vez
        self._apply_mode()
        if self._mode == "sencillo":
            self.exact.on_switch_to_simple()

    def _apply_mode(self):
        """Muestra u oculta los controles "avanzados". No borra widgets:
        solo los quita/pone en el grid con grid_remove()/grid(), así el
        estado se conserva al alternar."""
        advanced = self._mode == "avanzado"

        # Pestaña "Duplicados exactos": en Sencilla se ocultan el panel de opciones,
        # la carpeta preferida, "Ver tipos" y "Exportar CSV".
        self.exact.apply_mode(advanced)

        # Pestaña "Fotos parecidas": el deslizador de sensibilidad solo en Avanzada.
        self.similar.apply_mode(advanced)

        # "Historial" solo en Avanzada.
        (self.btn_history.grid if advanced else self.btn_history.grid_remove)()

        # "Reunir imágenes": «Carpeta entera» y Mover/Copiar solo en Avanzada.
        self.gather.apply_mode(advanced)

    def _on_close(self):
        self.exact.cancel_jobs()
        self.similar.cancel_jobs()
        self.gather.cancel_jobs()
        self.destroy()


def launch():
    # Aplica el tema guardado (auto/claro/oscuro) ANTES de crear la ventana.
    styles.apply_theme(config.get_theme())
    app = MainWindow()
    app.mainloop()
