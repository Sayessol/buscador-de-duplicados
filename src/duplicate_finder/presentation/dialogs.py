"""Dialogs the tabs share: choosing a quarantine folder and the questions around a move.

The three operations that move files (exact duplicates, similar photos, gather images) ask the
user the same things in the same order; the questions live here so each tab only says what
is specific to it.
"""

import os
from tkinter import filedialog, messagebox

from duplicate_finder.application.quarantine import InvalidQuarantine, validate_quarantine_folder
from duplicate_finder.i18n import tr


def proceed_despite(warning: str | None) -> bool:
    """False if there is a warning and the user does not want to continue."""
    if not warning:
        return True
    return messagebox.askyesno(tr("common.warning"), warning + tr("common.continue_question"))


def choose_quarantine_folder(scanned_folder: str) -> str | None:
    """Asks for the quarantine folder and checks it against the scanned one.

    Returns the folder, or None if the user gave up, the folder is not valid (the user is told)
    or the warning about it was not accepted.
    """
    folder = filedialog.askdirectory(title=tr("common.pick_quarantine"), mustexist=False)
    if not folder:
        return None
    folder = os.path.normpath(folder)
    try:
        warning = validate_quarantine_folder(folder, scanned_folder)
    except InvalidQuarantine as e:
        messagebox.showerror(tr("common.invalid_quarantine_title"), str(e))
        return None
    return folder if proceed_despite(warning) else None


def offer_to_open_folder(message: str, folder: str) -> None:
    """Says the operation is done and offers to open the folder where the files went."""
    if messagebox.askyesno(tr("common.done_title"), message):
        try:
            os.startfile(folder)  # noqa: S606 (Windows)
        except OSError:
            pass
