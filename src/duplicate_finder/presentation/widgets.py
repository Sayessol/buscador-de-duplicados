"""Reusable visual pieces for the main window."""

import customtkinter as ctk

from . import styles


class SectionHeader(ctk.CTkFrame):
    """Title row of a section: number in a circle + text."""

    def __init__(self, master, number, text, icon="", **kw):
        super().__init__(master, fg_color="transparent", **kw)
        badge = ctk.CTkLabel(
            self,
            text=str(number),
            width=22,
            height=22,
            corner_radius=11,
            fg_color=styles.COLOR_SELECTION,
            text_color="#ffffff",
            font=styles.base_font(11, "bold"),
        )
        badge.pack(side="left", padx=(0, 8))
        label = f"{icon}  {text}" if icon else text
        ctk.CTkLabel(self, text=label, font=styles.title_font(14)).pack(side="left")


class StatTile(ctk.CTkFrame):
    """Box with a big number and a label underneath."""

    def __init__(self, master, label, **kw):
        super().__init__(master, fg_color=styles.COLOR_TILE, corner_radius=8, **kw)
        self._value = ctk.CTkLabel(
            self, text="—", font=styles.number_font(19), text_color=styles.COLOR_TEXT
        )
        self._value.pack(padx=14, pady=(8, 0), anchor="w")
        ctk.CTkLabel(
            self, text=label, font=styles.base_font(11), text_color=styles.COLOR_MUTED_TEXT
        ).pack(padx=14, pady=(0, 8), anchor="w")

    def set(self, text, color=None):
        self._value.configure(text=str(text), text_color=color or styles.COLOR_TEXT)


class EmptyState(ctk.CTkFrame):
    """Centred message for when the table has no results."""

    def __init__(self, master, icon, title, detail, **kw):
        super().__init__(master, fg_color=styles.COLOR_TABLE_BACKGROUND, corner_radius=8, **kw)
        center = ctk.CTkFrame(self, fg_color="transparent")
        center.place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(center, text=icon, font=styles.base_font(46)).pack(pady=(0, 10))
        self._title = ctk.CTkLabel(center, text=title, font=styles.title_font(15))
        self._title.pack()
        self._detail = ctk.CTkLabel(
            center,
            text=detail,
            font=styles.base_font(12),
            text_color=styles.COLOR_MUTED_TEXT,
            wraplength=420,
            justify="center",
        )
        self._detail.pack(pady=(4, 0))

    def configure(self, title=None, detail=None):
        if title is not None:
            self._title.configure(text=title)
        if detail is not None:
            self._detail.configure(text=detail)


class KeyedSegmentedButton(ctk.CTkSegmentedButton):
    """Segmented button whose options have a stable key and a translated label.

    The code works with the keys (`get_key()`, `set_key()`); only the labels depend on the
    language, so comparing against text the user sees is never needed.
    """

    def __init__(self, master, options, **kw):
        """`options` maps each key to its label, in the order they are shown."""
        super().__init__(master, values=list(options.values()), **kw)
        self._labels = dict(options)

    def set_key(self, key):
        self.set(self._labels[key])

    def get_key(self):
        label = self.get()
        return next(key for key, text in self._labels.items() if text == label)


class KeyedOptionMenu(ctk.CTkOptionMenu):
    """Drop-down list with the same key / label split as KeyedSegmentedButton."""

    def __init__(self, master, options, **kw):
        super().__init__(master, values=list(options.values()), **kw)
        self._labels = dict(options)

    def set_key(self, key):
        self.set(self._labels[key])

    def key_of(self, label):
        """The key of a label (what the `command` callback receives)."""
        return next(key for key, text in self._labels.items() if text == label)


def make_card(parent, row):
    """Section card: a frame with a card background that takes up a row of the parent."""
    t = ctk.CTkFrame(parent, fg_color=styles.COLOR_CARD)
    t.grid(row=row, column=0, sticky="ew", padx=6, pady=(8, 0))
    t.grid_columnconfigure(0, weight=1)
    return t
