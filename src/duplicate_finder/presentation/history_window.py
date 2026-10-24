"""Operation history window, with "Undo".

Lists the recorded operations (move to quarantine, gather images)
and lets you revert each one:
- "move" -> puts the files back in their place,
- "copy" -> deletes the copies in the destination (with a clear confirmation).
"""

import os
from tkinter import messagebox

import customtkinter as ctk

from duplicate_finder.application.history import OperationHistory
from duplicate_finder.domain.formatting import format_size  # noqa: F401  (in case it is needed)
from duplicate_finder.domain.operations import KIND_GATHER, KIND_GATHER_FOLDER, KIND_QUARANTINE
from duplicate_finder.domain.transfers import COPY
from duplicate_finder.i18n import tr

from . import icons, styles

# Catalog key of the label of each kind of operation (translated when the window is drawn).
_KIND_LABEL = {
    KIND_QUARANTINE: "common.move_quarantine",
    KIND_GATHER: "history_ui.kind_gather",
    KIND_GATHER_FOLDER: "history_ui.kind_gather_folder",
}


class HistoryWindow(ctk.CTkToplevel):
    def __init__(self, master, history: OperationHistory):
        super().__init__(master)
        self._history = history
        self.title(tr("history_ui.title"))
        self.geometry("720x560")
        self.configure(fg_color=styles.COLOR_BACKGROUND)
        self.transient(master)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self,
            text=tr("history_ui.intro"),
            font=styles.base_font(11),
            text_color=styles.COLOR_MUTED_TEXT,
            wraplength=680,
            justify="left",
        ).grid(row=0, column=0, padx=16, pady=(14, 6), sticky="w")

        self.items = ctk.CTkScrollableFrame(self, fg_color=styles.COLOR_TABLE_BACKGROUND)
        self.items.grid(row=1, column=0, sticky="nsew", padx=12, pady=6)
        self.items.grid_columnconfigure(0, weight=1)

        caption = ctk.CTkFrame(self, fg_color="transparent")
        caption.grid(row=2, column=0, sticky="ew", padx=12, pady=(4, 12))
        ctk.CTkButton(
            caption,
            text=tr("history_ui.refresh"),
            width=110,
            fg_color="transparent",
            border_width=1,
            text_color=styles.COLOR_TEXT,
            command=self._paint,
        ).pack(side="left")
        ctk.CTkButton(caption, text=tr("common.close"), width=100, command=self.destroy).pack(
            side="right"
        )

        self._paint()
        self.after(150, self.lift)

    # ------------------------------------------------------------------
    def _paint(self):
        for child in self.items.winfo_children():
            child.destroy()

        ops = self._history.list_all()
        if not ops:
            ctk.CTkLabel(
                self.items,
                text=tr("history_ui.empty"),
                font=styles.base_font(12),
                text_color=styles.COLOR_MUTED_TEXT,
            ).grid(row=0, column=0, padx=16, pady=20)
            return

        for row, op in enumerate(ops):
            self._op_card(row, op)

    def _op_card(self, row, op):
        card = ctk.CTkFrame(self.items, fg_color=styles.COLOR_CARD)
        card.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        card.grid_columnconfigure(0, weight=1)

        kind = tr(_KIND_LABEL[op["kind"]]) if op["kind"] in _KIND_LABEL else op["kind"]
        verb = tr("history_ui.verb_copied" if op["action"] == COPY else "history_ui.verb_moved")
        n = len(op["moves"])
        date = op["date"].replace("T", "  ")
        title = f"{kind}  {tr('history_ui.item_title', n=n, verb=verb)}"
        ctk.CTkLabel(card, text=title, font=styles.base_font(12, "bold"), anchor="w").grid(
            row=0, column=0, padx=12, pady=(10, 2), sticky="w"
        )
        sub = f"{date}   →   {op['destination']}"
        ctk.CTkLabel(
            card,
            text=sub,
            font=styles.base_font(11),
            text_color=styles.COLOR_MUTED_TEXT,
            anchor="w",
            wraplength=520,
            justify="left",
        ).grid(row=1, column=0, padx=12, pady=(0, 10), sticky="w")

        if op.get("undone"):
            ctk.CTkLabel(
                card,
                text=tr("history_ui.undone", OK=icons.OK),
                font=styles.base_font(11),
                text_color=styles.COLOR_OK,
            ).grid(row=0, column=1, rowspan=2, padx=12)
        else:
            ctk.CTkButton(
                card,
                text=f"{icons.RELOAD}  {tr('history_ui.undo')}",
                width=120,
                command=lambda o=op: self._undo(o),
            ).grid(row=0, column=1, rowspan=2, padx=12, pady=8)

    def _undo(self, op):
        n = len(op["moves"])
        if op["action"] == COPY:
            warning = tr("history_ui.confirm_delete_copies", n=n, destination=op["destination"])
        else:
            warning = tr("history_ui.confirm_return", n=n, destination=op["destination"])
        if not messagebox.askyesno(tr("history_ui.undo_title"), warning, parent=self):
            return

        res = self._history.undo(op["id"])
        self._paint()

        if res["failures"]:
            detail = "\n".join(
                tr("history_ui.failure_line", name=os.path.basename(r) or r, m=m)
                for r, m in res["failures"][:12]
            )
            messagebox.showwarning(
                tr("history_ui.undo_warnings_title"),
                tr(
                    "history_ui.undo_warnings_msg",
                    reverted=res["reverted"],
                    count=len(res["failures"]),
                    detail=detail,
                ),
                parent=self,
            )
        else:
            messagebox.showinfo(
                tr("common.done_title"),
                tr("history_ui.undo_done", reverted=res["reverted"]),
                parent=self,
            )
