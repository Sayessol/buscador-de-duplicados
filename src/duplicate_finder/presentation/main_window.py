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

Interface in English or Spanish (texts in i18n/locales), light/dark theme, icons made of
Unicode glyphs.
"""

import logging
from pathlib import Path
from tkinter import TclError, messagebox

import customtkinter as ctk

from duplicate_finder import __version__, i18n
from duplicate_finder.application.services import Services
from duplicate_finder.i18n import tr

from . import icons, styles
from .exact_duplicates_tab import ExactDuplicatesTab
from .gather_images_tab import GatherImagesTab
from .history_window import HistoryWindow
from .similar_photos_tab import SimilarPhotosTab
from .widgets import KeyedOptionMenu, KeyedSegmentedButton

log = logging.getLogger(__name__)


class MainWindow(ctk.CTk):
    def __init__(self, services: Services):
        super().__init__()

        self.title(tr("main.window_title", version=__version__))
        self.geometry("1240x900")
        self.minsize(920, 640)
        self._set_window_icon()

        self.services = services
        self._mode = services.settings.get_mode()  # "simple" | "advanced"
        self._error_warned = False  # the unexpected-error warning appears only once

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()

        self.tabs = ctk.CTkTabview(self, fg_color="transparent")
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=10, pady=(2, 0))
        self._tab_titles = {
            "exact": f"{icons.SEARCH}  {tr('main.tab_exact')}",
            "similar": f"{icons.CAT_IMAGES}  {tr('main.tab_similar')}",
            "gather": f"{icons.GATHER}  {tr('main.tab_gather')}",
        }
        self.tab_exact = self.tabs.add(self._tab_titles["exact"])
        self.tab_similar = self.tabs.add(self._tab_titles["similar"])
        self.tab_gather = self.tabs.add(self._tab_titles["gather"])

        self.exact = ExactDuplicatesTab(self.tab_exact, self._mode == "advanced", services)
        self.similar = SimilarPhotosTab(self.tab_similar, services)
        self.gather = GatherImagesTab(self.tab_gather, services)

        self._apply_mode()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def report_callback_exception(self, exc, val, tb):
        """Tkinter calls this when a button or timer callback fails.

        By default the error only went to the console, which does not exist in the .exe.
        It is logged and the user is warned once, so as not to fill the screen
        with windows if the same failure repeats.
        """
        log.error("Unexpected error in the interface", exc_info=(exc, val, tb))
        if self._error_warned:
            return
        self._error_warned = True
        path = self.services.log_file_path()
        where = tr("main.log_saved", path=path) if path else tr("main.log_failed")
        messagebox.showerror(
            tr("main.error_title"), tr("main.error_msg", name=exc.__name__, val=val, where=where)
        )

    def _set_window_icon(self):
        """Icon of the title bar / taskbar.

        CustomTkinter sets its own icon 200 ms after creating the
        window, unless iconbitmap() has already been called — that is
        why iconbitmap() is used with an .ico (not iconphoto with a
        PhotoImage), so that its internal check detects it and does not
        overwrite it. icon.ico is generated with `python gen_icon.py`; if it does not
        exist (for example, in a clean checkout where it has not been generated yet)
        the window keeps working with the default icon.
        """
        ico_path = Path(__file__).resolve().parent.parent / "icon.ico"
        try:
            if ico_path.exists():
                self.iconbitmap(str(ico_path))
        except TclError:  # the icon is optional
            log.info("Could not set the window icon", exc_info=True)

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=styles.COLOR_HEADER, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(header, text=icons.SEARCH, font=styles.base_font(24)).grid(
            row=0, column=0, rowspan=2, padx=(18, 12), pady=12
        )
        title = ctk.CTkFrame(header, fg_color="transparent")
        title.grid(row=0, column=1, sticky="sw", pady=(12, 0))
        ctk.CTkLabel(title, text=tr("common.app_name"), font=styles.title_font(17)).pack(
            side="left"
        )
        ctk.CTkLabel(
            title,
            text=f"v{__version__}",
            font=styles.base_font(11),
            text_color=styles.COLOR_MUTED_TEXT,
        ).pack(side="left", padx=(8, 0), pady=(4, 0))
        ctk.CTkLabel(
            header,
            text=tr("main.tagline"),
            font=styles.base_font(11),
            text_color=styles.COLOR_MUTED_TEXT,
        ).grid(row=1, column=1, sticky="nw", pady=(0, 12))

        self.btn_history = ctk.CTkButton(
            header,
            text=f"{icons.HISTORY}  {tr('main.history')}",
            width=115,
            fg_color="transparent",
            border_width=1,
            border_color=styles.COLOR_BORDER,
            text_color=styles.COLOR_TEXT,
            hover_color=styles.COLOR_TILE,
            command=self._open_history,
        )
        self.btn_history.grid(row=0, column=2, rowspan=2, padx=(8, 12), pady=12)

        # Right panel: theme selector (top) and view selector (bottom).
        right = ctk.CTkFrame(header, fg_color="transparent")
        right.grid(row=0, column=3, rowspan=2, padx=(0, 16), pady=10)

        ctk.CTkLabel(
            right,
            text=tr("main.theme_label"),
            font=styles.base_font(11),
            text_color=styles.COLOR_MUTED_TEXT,
        ).grid(row=0, column=0, padx=(0, 6), pady=(0, 4), sticky="e")
        self.theme_selector = KeyedOptionMenu(
            right,
            {
                "auto": tr("main.theme_auto"),
                "light": tr("main.theme_light"),
                "dark": tr("main.theme_dark"),
            },
            width=118,
            command=self._change_theme,
        )
        self.theme_selector.set_key(self.services.settings.get_theme())
        self.theme_selector.grid(row=0, column=1, pady=(0, 4), sticky="w")

        ctk.CTkLabel(
            right,
            text=tr("main.view_label"),
            font=styles.base_font(11),
            text_color=styles.COLOR_MUTED_TEXT,
        ).grid(row=1, column=0, padx=(0, 6), sticky="e")
        self.mode_selector = KeyedSegmentedButton(
            right,
            {"simple": tr("main.mode_simple"), "advanced": tr("main.mode_advanced")},
            command=self._change_mode,
        )
        self.mode_selector.set_key(self._mode)
        self.mode_selector.grid(row=1, column=1, columnspan=3, sticky="w")

        ctk.CTkLabel(
            right,
            text=tr("main.language_label"),
            font=styles.base_font(11),
            text_color=styles.COLOR_MUTED_TEXT,
        ).grid(row=0, column=2, padx=(16, 6), pady=(0, 4), sticky="e")
        self.language_selector = ctk.CTkOptionMenu(
            right,
            values=list(i18n.LANGUAGE_NAMES.values()),
            width=110,
            command=self._change_language,
        )
        self.language_selector.set(i18n.LANGUAGE_NAMES[i18n.get_language()])
        self.language_selector.grid(row=0, column=3, pady=(0, 4), sticky="w")

    def show_tab(self, name):
        """Shows one of the tabs: "exact", "similar" or "gather"."""
        self.tabs.set(self._tab_titles[name])

    def _open_history(self):
        HistoryWindow(self, self.services.history)

    def _change_theme(self, label):
        theme = self.theme_selector.key_of(label)
        self.services.settings.set_theme(theme)
        styles.change_theme(theme)  # CustomTkinter repaints; ttk does it in _set_appearance_mode

    def _change_language(self, name):
        """Saves the language; the texts are drawn once, so it applies the next time."""
        code = next(code for code, label in i18n.LANGUAGE_NAMES.items() if label == name)
        if code == i18n.get_language():
            return
        self.services.settings.set_language(code)
        messagebox.showinfo(tr("main.language_changed_title"), tr("main.language_changed_msg"))

    def _change_mode(self, value):
        """Called by the switch in the header."""
        self._mode = self.mode_selector.get_key()
        self.services.settings.set_mode(self._mode)  # remembered for next time
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


def launch(services: Services):
    # The language is chosen before any text is created: the saved one, or the system's.
    i18n.set_language(i18n.resolve_language(services.settings.get_language()))
    # Applies the saved theme (auto/light/dark) BEFORE creating the window.
    styles.apply_theme(services.settings.get_theme())
    app = MainWindow(services)
    app.mainloop()
