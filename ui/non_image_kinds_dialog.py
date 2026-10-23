"""Dialog: what to do with the files that are not images.

For each kind (extension) found, the user chooses:
  · Leave     -> it is not moved, it stays in the source.
  · Move      -> it goes to the destination with its same subpath (like the images).
  · Group     -> it goes to  destination/<folder named by the user>/<subpath>.
"""

import customtkinter as ctk

from core.filters import NO_EXTENSION
from core.gather import NonImageRules, LEAVE, GROUP
from core.file_moves import MOVE
from . import styles
from .widgets import KeyedSegmentedButton
from core.i18n import tr

# Default names of the folders where each kind is grouped (names inside the user's folders
# are fixed English; the user can edit them in the dialog).
_FOLDER_NAME = {
    "pdf": "Documents", "doc": "Documents", "docx": "Documents",
    "xls": "Documents", "xlsx": "Documents", "txt": "Documents",
    "mp3": "Music", "wav": "Music", "flac": "Music",
    "mp4": "Videos", "mkv": "Videos", "avi": "Videos",
    "zip": "Archives", "rar": "Archives", "7z": "Archives",
}


class NonImageKindsWindow(ctk.CTkToplevel):
    def __init__(self, master, kinds):
        """kinds: dict  ext -> list of paths."""
        super().__init__(master)
        self.title(tr("kinds.title"))
        self.geometry("620x460")
        self.configure(fg_color=styles.COLOR_BACKGROUND)
        self.transient(master)
        self.grab_set()

        self.rules = None          # filled in when "Apply" is pressed
        self._rows = {}            # ext -> (segmented, entry)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self, text=tr("kinds.intro"),
            font=styles.base_font(12), wraplength=580, justify="left",
            anchor="w").grid(row=0, column=0, padx=16, pady=(14, 8), sticky="w")

        items = ctk.CTkScrollableFrame(self, fg_color=styles.COLOR_TABLE_BACKGROUND)
        items.grid(row=1, column=0, sticky="nsew", padx=12, pady=6)
        items.grid_columnconfigure(0, weight=1)

        for i, (ext, paths) in enumerate(kinds.items()):
            self._row(items, i, ext, len(paths))

        caption = ctk.CTkFrame(self, fg_color="transparent")
        caption.grid(row=2, column=0, sticky="ew", padx=12, pady=(4, 12))
        ctk.CTkButton(caption, text=tr("common.cancel"), width=100, fg_color="transparent",
                      border_width=1, text_color=styles.COLOR_TEXT,
                      command=self._cancel).pack(side="right", padx=4)
        ctk.CTkButton(caption, text=tr("kinds.apply"), width=110,
                      command=self._apply).pack(side="right", padx=4)

        self.after(150, self.lift)
        self.protocol("WM_DELETE_WINDOW", self._cancel)

    def _row(self, parent, i, ext, how_many):
        frame = ctk.CTkFrame(parent, fg_color=styles.COLOR_CARD)
        frame.grid(row=i, column=0, sticky="ew", pady=(0, 6))
        frame.grid_columnconfigure(1, weight=1)

        label = f".{ext}" if ext != NO_EXTENSION else tr("common.no_extension")
        ctk.CTkLabel(frame, text=f"{label}   ({how_many})",
                     font=styles.base_font(12, "bold"), width=110,
                     anchor="w").grid(row=0, column=0, padx=(12, 8), pady=10,
                                      sticky="w")

        seg = KeyedSegmentedButton(
            frame, {LEAVE: tr("kinds.leave"), MOVE: tr("kinds.move"), GROUP: tr("kinds.group")},
            command=lambda _v, e=ext: self._toggle_entry(e))
        seg.set_key(LEAVE)
        seg.grid(row=0, column=1, padx=4, pady=10, sticky="w")

        entry = ctk.CTkEntry(frame, width=150, placeholder_text=tr("kinds.folder_name_placeholder"))
        entry.insert(0, _FOLDER_NAME.get(ext, ext.capitalize() or "Other"))
        entry.configure(state="disabled")
        entry.grid(row=0, column=2, padx=(4, 12), pady=10)

        self._rows[ext] = (seg, entry)

    def _toggle_entry(self, ext):
        seg, entry = self._rows[ext]
        entry.configure(state="normal" if seg.get_key() == GROUP else "disabled")

    def _apply(self):
        actions, folders = {}, {}
        for ext, (seg, entry) in self._rows.items():
            chosen = seg.get_key()
            if chosen == MOVE:
                actions[ext] = MOVE
            elif chosen == GROUP:
                actions[ext] = GROUP
                folders[ext] = entry.get().strip() or ext
            else:
                actions[ext] = LEAVE
        self.rules = NonImageRules(action_by_ext=actions,
                                     folder_by_ext=folders)
        self.grab_release()
        self.destroy()

    def _cancel(self):
        self.rules = None
        self.grab_release()
        self.destroy()
