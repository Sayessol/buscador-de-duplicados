"""Use case: gather all the images of a folder into a common folder.

Two strategies:

* **by files** (`gather_by_files`): moves/copies each image to `destination/<same subpath>`.
  Files that are not images are handled according to `NonImageRules`
  (leave them, move them anyway, or group them by kind in a folder with the
  name the user chooses).

* **whole folder** (`gather_whole_folder`): moves/copies the whole folder to analyze (with
  everything inside it) to `destination/<folder name>/`.
"""

import os

from duplicate_finder.application.callbacks import CancelledCallback, ProgressCallback
from duplicate_finder.application.file_transfers import (
    FileTransfers,
    collision_free_path,
    validate_destination,
)
from duplicate_finder.application.ports import FileSystem
from duplicate_finder.domain.filters import CATEGORY_EXTENSIONS, NO_EXTENSION
from duplicate_finder.domain.transfers import (
    COPY,
    GROUP,
    LEAVE,
    MOVE,
    NonImageRules,
    Transfer,
    TransferResult,
)
from duplicate_finder.i18n import tr

# Extensions considered "image" (broader than what Pillow
# can preview: it includes raw, heic, etc.).
IMAGE_EXT = {e.lower() for e in CATEGORY_EXTENSIONS["images"]}


def _ext(path: str) -> str:
    return os.path.splitext(path)[1].lower().lstrip(".")


def non_image_kinds(others: list[str]) -> dict[str, list[str]]:
    """dict: extension -> list of paths, for the per-kind dialog."""
    d: dict[str, list[str]] = {}
    for path in others:
        d.setdefault(_ext(path) or NO_EXTENSION, []).append(path)
    return dict(sorted(d.items()))


class GatherImages:
    def __init__(self, fs: FileSystem, transfers: FileTransfers) -> None:
        self._fs = fs
        self._transfers = transfers

    def list_all(self, root_folder: str, recursive: bool = True) -> tuple[list[str], list[str]]:
        """Returns (images, non_images): two lists of absolute paths."""
        images: list[str] = []
        others: list[str] = []
        if recursive:
            for current_dir, _sub, names in self._fs.walk(root_folder):
                for n in names:
                    path = os.path.join(current_dir, n)
                    (images if _ext(n) in IMAGE_EXT else others).append(path)
        else:
            for n in sorted(self._fs.list_dir(root_folder)):
                path = os.path.join(root_folder, n)
                if self._fs.is_file(path):
                    (images if _ext(n) in IMAGE_EXT else others).append(path)
        return sorted(images), sorted(others)

    def plan_by_files(
        self,
        images: list[str],
        others: list[str],
        root_folder: str,
        destination: str,
        rules: NonImageRules | None = None,
    ) -> list[Transfer]:
        """List of Transfer (not executed)."""
        rules = rules or NonImageRules()
        plan: list[Transfer] = []

        # Images: always to destination/<same subpath they had in the source>.
        for path in images:
            rel = os.path.relpath(path, root_folder)   # e.g. "holidays/beach.jpg"
            plan.append(Transfer(path, os.path.join(destination, rel),
                                 self._transfers.size(path)))

        # Non-images: according to what the user chose for each kind.
        for path in others:
            ext = _ext(path) or NO_EXTENSION
            acc = rules.action(ext)
            if acc == LEAVE:
                continue                                # left alone
            rel = os.path.relpath(path, root_folder)
            if acc == GROUP:
                # destination/<folder named by the user>/<subpath>
                final_destination = os.path.join(destination, rules.folder(ext), rel)
            else:  # "move": same as the images
                final_destination = os.path.join(destination, rel)
            plan.append(Transfer(path, final_destination, self._transfers.size(path)))

        return plan

    def gather_by_files(
        self,
        images: list[str],
        others: list[str],
        root_folder: str,
        destination: str,
        action: str = MOVE,
        rules: NonImageRules | None = None,
        progress: ProgressCallback | None = None,
        cancelled: CancelledCallback | None = None,
    ) -> TransferResult:
        validate_destination(destination, root_folder)
        self._fs.make_dirs(destination)
        plan = self.plan_by_files(images, others, root_folder, destination, rules)
        res = self._transfers.execute(plan, action=action, progress=progress, cancelled=cancelled)
        res.log_path = self._transfers.write_log(plan, destination, "gather", root_folder, action)
        return res

    def gather_whole_folder(
        self, root_folder: str, destination: str, action: str = MOVE,
        progress: ProgressCallback | None = None,
    ) -> TransferResult:
        """Moves/copies the whole folder to analyze into the destination."""
        validate_destination(destination, root_folder)
        self._fs.make_dirs(destination)
        progress = progress or (lambda *_: None)

        name = os.path.basename(os.path.normpath(root_folder)) or "folder"
        final = collision_free_path(self._fs, os.path.join(destination, name))
        verb = tr("common.copying") if action == COPY else tr("common.moving")
        progress(0, 1, tr("gather.folder_progress", verb=verb, name=name))

        t = Transfer(root_folder, final, 0)
        try:
            if action == COPY:
                self._fs.copy_tree(root_folder, final)
            else:
                self._fs.move(root_folder, final)
            t.ok = True
        except OSError as e:
            t.ok, t.error = False, str(e)

        progress(1, 1, tr("common.done"))
        res = TransferResult(transfers=[t], action=action)
        res.log_path = self._transfers.write_log([t], destination, "gather_folder", root_folder,
                                                 action)
        return res
