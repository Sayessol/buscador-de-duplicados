"""Use case: find similar (not identical) photos in a folder."""

import logging
import os

from duplicate_finder.application.callbacks import CancelledCallback, ProgressCallback
from duplicate_finder.application.ports import FileSystem, FingerprintReader
from duplicate_finder.domain.filters import ScanFilter
from duplicate_finder.domain.similarity import (
    ComparisonCancelled,
    ImageFingerprint,
    SimilarResult,
    group_fingerprints,
)
from duplicate_finder.i18n import tr

log = logging.getLogger(__name__)

# Extensions that Pillow opens without extra plugins.
IMAGE_EXTENSIONS = {
    "jpg",
    "jpeg",
    "jpe",
    "png",
    "gif",
    "bmp",
    "webp",
    "tif",
    "tiff",
    "ppm",
    "pgm",
}


class FindSimilarPhotos:
    def __init__(self, fs: FileSystem, fingerprints: FingerprintReader) -> None:
        self._fs = fs
        self._fingerprints = fingerprints

    def list_images(self, root_folder: str, filter: ScanFilter | None = None) -> list[str]:
        """Paths of image files under `root_folder` (recursive).

        `filter` is an optional ScanFilter (its excluded folders
        and names are respected; the extensions are always limited to images).
        """
        paths: list[str] = []
        for current_dir, subdirs, names in self._fs.walk(root_folder):
            if filter is not None:
                subdirs[:] = [d for d in subdirs if not filter.excludes_folder(d)]
            for name in names:
                ext = os.path.splitext(name)[1].lower().lstrip(".")
                if ext not in IMAGE_EXTENSIONS:
                    continue
                if filter is not None and name.lower() in filter.excluded_names:
                    continue
                paths.append(os.path.join(current_dir, name))
        return paths

    def group_similar(
        self,
        paths: list[str],
        hamming_threshold: int = 10,
        color_threshold: float = 32,
        progress: ProgressCallback | None = None,
        cancelled: CancelledCallback | None = None,
    ) -> SimilarResult:
        """Groups the images in `paths` by visual similarity.

        hamming_threshold : 0..64. Higher = more tolerant (joins more).
                            ~6 strict, ~10 normal, ~16 very tolerant.
        color_threshold   : 0..255. Mean colour difference allowed.
        progress          : optional callable(current, total, message).
        cancelled         : optional callable() -> bool.
        """
        progress = progress or (lambda *_: None)
        cancelled = cancelled or (lambda: False)

        # Compute the fingerprint (dHash + colour) of each image. The ones that
        # cannot be opened go to `errors` and do not break the analysis.
        fingerprints: list[ImageFingerprint] = []
        errors: list[tuple[str, str]] = []
        total = len(paths)
        for i, path in enumerate(paths, 1):
            if cancelled():
                raise ComparisonCancelled()
            if i % 25 == 0 or i == total:
                progress(i, total, tr("perceptual.analyzing", i=i, total=total))
            try:
                fingerprints.append(self._fingerprints.read(path))
            except Exception as e:  # a broken or odd file must not stop the whole analysis
                log.info("Could not analyze image %s: %s", path, e)
                errors.append((path, str(e)))

        groups = group_fingerprints(fingerprints, hamming_threshold, color_threshold, cancelled)

        progress(total, total, tr("perceptual.finished"))
        return SimilarResult(
            groups=groups,
            total_images=len(fingerprints),
            errors=errors,
        )

    def __call__(
        self,
        root_folder: str,
        hamming_threshold: int = 10,
        color_threshold: float = 32,
        filter: ScanFilter | None = None,
        progress: ProgressCallback | None = None,
        cancelled: CancelledCallback | None = None,
    ) -> SimilarResult:
        """List the images of a folder and group them by similarity."""
        if not self._fs.is_dir(root_folder):
            raise NotADirectoryError(tr("common.not_a_folder", root_folder=root_folder))
        paths = self.list_images(root_folder, filter=filter)
        return self.group_similar(
            paths,
            hamming_threshold=hamming_threshold,
            color_threshold=color_threshold,
            progress=progress,
            cancelled=cancelled,
        )
