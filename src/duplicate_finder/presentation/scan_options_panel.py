"""The collapsible panel of scan options: search only some kinds of file, and what to ignore."""

import customtkinter as ctk

from duplicate_finder.domain.filters import (
    CATEGORY_EXTENSIONS,
    JUNK_EXTENSIONS,
    JUNK_FOLDERS,
    JUNK_NAMES,
    ScanFilter,
    parse_extensions,
    parse_names,
    set_to_text,
)
from duplicate_finder.i18n import tr

from . import icons, styles


class ScanOptionsPanel(ctk.CTkFrame):
    """A toggle button and, under it, the filters. It owns the state of every field."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)

        self._open = ctk.BooleanVar(value=False)
        self.btn_toggle = ctk.CTkButton(
            self,
            text=f"{icons.TRI_RIGHT}  {icons.GEAR}  {tr('exact.options_toggle')}",
            anchor="w",
            fg_color="transparent",
            hover=False,
            text_color=styles.COLOR_MUTED_TEXT,
            command=self.toggle,
        )
        self.btn_toggle.grid(row=0, column=0, sticky="ew")

        self.panel = ctk.CTkFrame(self, fg_color=styles.COLOR_CARD)
        self.panel.grid(row=1, column=0, sticky="ew", pady=(2, 0))
        self.panel.grid_columnconfigure(1, weight=1)
        self.panel.grid_remove()
        p = self.panel

        # --- Search only these kinds (whitelist) ------------------
        ctk.CTkLabel(p, text=tr("exact.only_kinds"), font=styles.base_font(12, "bold")).grid(
            row=0, column=0, columnspan=3, padx=16, pady=(12, 4), sticky="w"
        )

        chips = ctk.CTkFrame(p, fg_color="transparent")
        chips.grid(row=1, column=0, columnspan=3, padx=14, pady=(0, 4), sticky="w")
        self.chk_categories = {}
        for name in CATEGORY_EXTENSIONS:
            chk = ctk.CTkCheckBox(
                chips,
                text=f"{icons.CATEGORY_ICON[name]}  {tr(f'category.{name}')}",
                font=styles.base_font(12),
                command=lambda n=name: self.toggle_category(n),
            )
            chk.pack(side="left", padx=(2, 12), pady=4)
            self.chk_categories[name] = chk

        ctk.CTkLabel(p, text=tr("exact.extensions"), font=styles.base_font(12)).grid(
            row=2, column=0, padx=(16, 8), pady=4, sticky="w"
        )
        self.entry_include = ctk.CTkEntry(
            p, height=32, placeholder_text=tr("exact.all_kinds_placeholder")
        )
        self.entry_include.grid(row=2, column=1, columnspan=2, padx=(4, 16), pady=4, sticky="ew")
        self.entry_include.bind("<KeyRelease>", self._sync_categories)

        ctk.CTkLabel(
            p,
            text=tr("exact.categories_hint"),
            font=styles.base_font(11),
            text_color=styles.COLOR_MUTED_TEXT,
        ).grid(row=3, column=0, columnspan=3, padx=16, pady=(0, 10), sticky="w")

        ctk.CTkFrame(p, height=1, fg_color=styles.COLOR_ALTERNATE_ROW).grid(
            row=4, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 8)
        )

        # --- Ignore (blacklist) ------------------------------------
        ctk.CTkLabel(p, text=tr("exact.ignore_also"), font=styles.base_font(12, "bold")).grid(
            row=5, column=0, columnspan=3, padx=16, pady=(0, 4), sticky="w"
        )

        def field(row, label):
            ctk.CTkLabel(p, text=label, font=styles.base_font(12)).grid(
                row=row, column=0, padx=(16, 8), pady=4, sticky="w"
            )
            e = ctk.CTkEntry(p, height=32)
            e.grid(row=row, column=1, columnspan=2, padx=(4, 16), pady=4, sticky="ew")
            return e

        self.entry_ext = field(6, tr("exact.extensions"))
        self.entry_folders = field(7, tr("exact.folders"))
        self.entry_names = field(8, tr("exact.names"))

        self.chk_empty = ctk.CTkCheckBox(
            p, text=tr("exact.ignore_empty"), font=styles.base_font(12)
        )
        self.chk_empty.grid(row=9, column=0, columnspan=2, padx=16, pady=(6, 4), sticky="w")

        buttons = ctk.CTkFrame(p, fg_color="transparent")
        buttons.grid(row=9, column=2, padx=12, pady=(6, 4), sticky="e")
        ctk.CTkButton(
            buttons,
            text=tr("exact.defaults"),
            width=140,
            fg_color="transparent",
            border_width=1,
            text_color=styles.COLOR_TEXT,
            command=self.reset_to_defaults,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            buttons,
            text=tr("exact.clear_all"),
            width=90,
            fg_color="transparent",
            border_width=1,
            text_color=styles.COLOR_TEXT,
            command=self.clear,
        ).pack(side="left", padx=4)

        ctk.CTkLabel(
            p,
            text=tr("exact.separate_hint"),
            font=styles.base_font(11),
            text_color=styles.COLOR_MUTED_TEXT,
        ).grid(row=10, column=0, columnspan=3, padx=16, pady=(0, 12), sticky="w")

        self.reset_to_defaults()

    # ------------------------------------------------------------------
    @property
    def is_open(self) -> bool:
        return bool(self._open.get())

    def toggle(self) -> None:
        opening = not self.is_open
        self._open.set(opening)
        tri = icons.TRI_DOWN if opening else icons.TRI_RIGHT
        self.btn_toggle.configure(text=f"{tri}  {icons.GEAR}  {tr('exact.options_toggle')}")
        if opening:
            self.panel.grid()
        else:
            self.panel.grid_remove()

    def collapse(self) -> None:
        if self.is_open:
            self.toggle()

    def toggle_category(self, name) -> None:
        """Ticks/unticks the extensions of a category in the field."""
        current_set = parse_extensions(self.entry_include.get())
        exts = CATEGORY_EXTENSIONS[name]
        if self.chk_categories[name].get():
            current_set |= exts
        else:
            current_set -= exts
        self.entry_include.delete(0, "end")
        self.entry_include.insert(0, set_to_text(current_set))

    def _sync_categories(self, _event=None) -> None:
        """After editing the field by hand, leaves ticked only the categories
        whose extensions are all present."""
        present = parse_extensions(self.entry_include.get())
        for name, chk in self.chk_categories.items():
            complete = CATEGORY_EXTENSIONS[name] <= present
            if complete and not chk.get():
                chk.select()
            elif not complete and chk.get():
                chk.deselect()

    def reset_to_defaults(self) -> None:
        for entry, values in (
            (self.entry_ext, JUNK_EXTENSIONS),
            (self.entry_folders, JUNK_FOLDERS),
            (self.entry_names, JUNK_NAMES),
        ):
            entry.delete(0, "end")
            entry.insert(0, "  ".join(values))
        self.chk_empty.select()
        self.entry_include.delete(0, "end")
        for chk in self.chk_categories.values():
            chk.deselect()

    def clear(self) -> None:
        for entry in (self.entry_include, self.entry_ext, self.entry_folders, self.entry_names):
            entry.delete(0, "end")
        self.chk_empty.deselect()
        for chk in self.chk_categories.values():
            chk.deselect()

    def current_filter(self) -> ScanFilter:
        return ScanFilter(
            included_extensions=parse_extensions(self.entry_include.get()),
            excluded_extensions=parse_extensions(self.entry_ext.get()),
            excluded_names=parse_names(self.entry_names.get()),
            excluded_folders=parse_names(self.entry_folders.get()),
            min_size=1 if self.chk_empty.get() else 0,
        )

    def exclude_extension(self, ext) -> None:
        """Adds an extension to the ignored ones (and opens the panel so the user sees it)."""
        current_set = parse_extensions(self.entry_ext.get())
        current_set.add(ext.lower().lstrip("."))
        self.entry_ext.delete(0, "end")
        self.entry_ext.insert(0, set_to_text(current_set))
        if not self.is_open:
            self.toggle()
