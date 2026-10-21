"""Ventana principal de la app.

Aquí queda solo la "carcasa": cabecera (tema, vista, historial), el
selector de pestañas y el modo Sencilla / Avanzada. Cada pestaña es un
COMPONENTE con su propio estado, en su propio módulo:

  pestana_exactos.py     PestanaExactos     "Duplicados exactos"  -> self.exactos
  pestana_parecidas.py   PestanaParecidas   "Fotos parecidas"     -> self.parecidas
  pestana_reunir.py      PestanaReunir      "Reunir imágenes"     -> self.reunir

La ventana solo crea los tres componentes y les avisa de dos cosas:
`aplicar_modo(avanzado)` al cambiar entre Sencilla y Avanzada y
`cancelar_trabajos()` al cerrar. Ninguno toca el estado de los otros.

Toda tarea larga (escanear, analizar, mover) usa el mismo patrón
hilo + cola + after(); está explicado en
pestana_exactos.py:_trabajo_escaneo.

Interfaz en español de España, tema claro/oscuro, iconos con glifos Unicode.
"""
from pathlib import Path
from tkinter import TclError, messagebox

import customtkinter as ctk

from core import __version__, config, registro
from core.registro import log
from . import styles
from . import icons
from .history_window import VentanaHistorial
from .pestana_exactos import PestanaExactos
from .pestana_reunir import PestanaReunir
from .pestana_parecidas import PestanaParecidas


class VentanaPrincipal(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"Buscador de duplicados {__version__}")
        self.geometry("1240x900")
        self.minsize(920, 640)
        self._poner_icono_ventana()

        self._modo = config.get_modo()  # "sencillo" | "avanzado"
        self._error_avisado = False     # el aviso de error inesperado sale una sola vez

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._construir_cabecera()

        self.tabs = ctk.CTkTabview(self, fg_color="transparent")
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=10, pady=(2, 0))
        self.tab_exactos = self.tabs.add(f"{icons.BUSCAR}  Duplicados exactos")
        self.tab_parecidas = self.tabs.add(f"{icons.CAT_IMAGENES}  Fotos parecidas")
        self.tab_reunir = self.tabs.add(f"{icons.REUNIR}  Reunir imágenes")

        self.exactos = PestanaExactos(self.tab_exactos, self._modo == "avanzado")
        self.parecidas = PestanaParecidas(self.tab_parecidas)
        self.reunir = PestanaReunir(self.tab_reunir)

        self._aplicar_modo()
        self.protocol("WM_DELETE_WINDOW", self._al_cerrar)

    def report_callback_exception(self, exc, val, tb):
        """Tkinter llama aquí cuando falla una función de un botón o un temporizador.

        Por defecto el error solo salía por la consola, que en el .exe no existe.
        Se anota en el registro y se avisa una vez, para no llenar la pantalla
        de ventanas si el mismo fallo se repite.
        """
        log.error("Error inesperado en la interfaz", exc_info=(exc, val, tb))
        if self._error_avisado:
            return
        self._error_avisado = True
        ruta = registro.ruta_archivo()
        donde = (f"Se ha anotado en el registro:\n{ruta}" if ruta
                 else "No se ha podido guardar el registro.")
        messagebox.showerror(
            "Error inesperado",
            f"Ha ocurrido un error inesperado ({exc.__name__}: {val}).\n\n{donde}\n\n"
            "Puedes seguir usando la aplicación; si el fallo se repite, cierra y "
            "vuelve a abrirla. Tus archivos no se han tocado.")

    def _poner_icono_ventana(self):
        """Icono de la barra de título / barra de tareas.

        CustomTkinter pone su propio icono 200 ms después de crear la
        ventana, salvo que ya se haya llamado a iconbitmap() antes — por
        eso se usa iconbitmap() con un .ico (no iconphoto con un
        PhotoImage), para que la comprobación interna lo detecte y no lo
        pise. icono.ico se genera con `python generar_icono.py`; si no
        existe (por ejemplo, en un checkout limpio sin generarlo todavía)
        la ventana sigue funcionando con el icono por defecto.
        """
        ruta_ico = Path(__file__).resolve().parent.parent / "icono.ico"
        try:
            if ruta_ico.exists():
                self.iconbitmap(str(ruta_ico))
        except TclError:  # el icono es opcional
            log.info("No se pudo poner el icono de la ventana", exc_info=True)

    def _construir_cabecera(self):
        cab = ctk.CTkFrame(self, fg_color=styles.COLOR_CABECERA, corner_radius=0)
        cab.grid(row=0, column=0, sticky="ew")
        cab.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(cab, text=icons.BUSCAR, font=styles.fuente_base(24)).grid(
            row=0, column=0, rowspan=2, padx=(18, 12), pady=12)
        titulo = ctk.CTkFrame(cab, fg_color="transparent")
        titulo.grid(row=0, column=1, sticky="sw", pady=(12, 0))
        ctk.CTkLabel(titulo, text="Buscador de duplicados",
                     font=styles.fuente_titulo(17)).pack(side="left")
        ctk.CTkLabel(titulo, text=f"v{__version__}", font=styles.fuente_base(11),
                     text_color=styles.COLOR_TEXTO_TENUE).pack(
            side="left", padx=(8, 0), pady=(4, 0))
        ctk.CTkLabel(
            cab, text="Encuentra archivos repetidos y muévelos a cuarentena. "
                      "Nunca se borran tus originales.",
            font=styles.fuente_base(11), text_color=styles.COLOR_TEXTO_TENUE).grid(
            row=1, column=1, sticky="nw", pady=(0, 12))

        self.btn_historial = ctk.CTkButton(
            cab, text=f"{icons.HISTORIAL}  Historial", width=115,
            fg_color="transparent", border_width=1,
            border_color=styles.COLOR_BORDE, text_color=styles.COLOR_TEXTO,
            hover_color=styles.COLOR_BALDOSA, command=self._abrir_historial)
        self.btn_historial.grid(row=0, column=2, rowspan=2, padx=(8, 12), pady=12)

        # Panel derecho: selector de tema (arriba) y de vista (abajo).
        der = ctk.CTkFrame(cab, fg_color="transparent")
        der.grid(row=0, column=3, rowspan=2, padx=(0, 16), pady=10)

        ctk.CTkLabel(der, text="Tema:", font=styles.fuente_base(11),
                     text_color=styles.COLOR_TEXTO_TENUE).grid(
            row=0, column=0, padx=(0, 6), pady=(0, 4), sticky="e")
        self.selector_tema = ctk.CTkOptionMenu(
            der, values=["Automático", "Claro", "Oscuro"], width=118,
            command=self._cambiar_tema)
        self.selector_tema.set({"auto": "Automático", "claro": "Claro",
                                "oscuro": "Oscuro"}[config.get_tema()])
        self.selector_tema.grid(row=0, column=1, pady=(0, 4), sticky="w")

        ctk.CTkLabel(der, text="Vista:", font=styles.fuente_base(11),
                     text_color=styles.COLOR_TEXTO_TENUE).grid(
            row=1, column=0, padx=(0, 6), sticky="e")
        self.selector_modo = ctk.CTkSegmentedButton(
            der, values=["Sencilla", "Avanzada"], command=self._cambiar_modo)
        self.selector_modo.set("Sencilla" if self._modo == "sencillo"
                               else "Avanzada")
        self.selector_modo.grid(row=1, column=1, sticky="w")

    def _abrir_historial(self):
        VentanaHistorial(self)

    def _cambiar_tema(self, etiqueta):
        tema = {"Automático": "auto", "Claro": "claro", "Oscuro": "oscuro"}[etiqueta]
        config.set_tema(tema)
        styles.cambiar_tema(tema)     # CustomTkinter re-pinta; ttk lo hace en _set_appearance_mode

    def _cambiar_modo(self, valor):
        """Lo llama el interruptor de la cabecera."""
        self._modo = "sencillo" if valor == "Sencilla" else "avanzado"
        config.set_modo(self._modo)          # se recuerda para la próxima vez
        self._aplicar_modo()
        if self._modo == "sencillo":
            self.exactos.al_pasar_a_sencilla()

    def _aplicar_modo(self):
        """Muestra u oculta los controles "avanzados". No borra widgets:
        solo los quita/pone en el grid con grid_remove()/grid(), así el
        estado se conserva al alternar."""
        avanzado = self._modo == "avanzado"

        # Pestaña "Duplicados exactos": en Sencilla se ocultan el panel de opciones,
        # la carpeta preferida, "Ver tipos" y "Exportar CSV".
        self.exactos.aplicar_modo(avanzado)

        # Pestaña "Fotos parecidas": el deslizador de sensibilidad solo en Avanzada.
        self.parecidas.aplicar_modo(avanzado)

        # "Historial" solo en Avanzada.
        (self.btn_historial.grid if avanzado else self.btn_historial.grid_remove)()

        # "Reunir imágenes": «Carpeta entera» y Mover/Copiar solo en Avanzada.
        self.reunir.aplicar_modo(avanzado)

    def _al_cerrar(self):
        self.exactos.cancelar_trabajos()
        self.parecidas.cancelar_trabajos()
        self.reunir.cancelar_trabajos()
        self.destroy()


def lanzar():
    # Aplica el tema guardado (auto/claro/oscuro) ANTES de crear la ventana.
    styles.aplicar_tema(config.get_tema())
    app = VentanaPrincipal()
    app.mainloop()
