"""Detection of SIMILAR photos (not identical).

It catches: the same photo recompressed, resized, with a colour/brightness
filter or a watermark in a corner.

It does NOT catch: crops or strong rotations (that would need feature matching
like OpenCV, which would multiply the size of the app).

How it works
------------
For each image a cheap "fingerprint" is computed:

* **dHash (64 bits)** · measures the STRUCTURE (horizontal gradients of a
  9×8 grayscale thumbnail). It is very stable against recompression, resizing
  and colour filters, because those do not move the edges.
* **Colour signature (4×4 cells, mean RGB)** · a secondary signal so that two
  different photos that happen to have similar gradients (a sky and a plain
  wall, for example) are not put together.

Two images are "similar" if the Hamming distance of their dHashes is
small AND their colour does not diverge. The threshold is decided by the caller
(in the app, a sensitivity slider).

Grouping
--------
* A **BK-tree** over the dHashes finds neighbours by Hamming distance
  without comparing every image against every other.
* **Union-Find** joins chains of similar images: if A~B and B~C, the group is
  {A, B, C} even if A and C do not look alike directly.

Requires Pillow. Only this module (and the thumbnails one) depend on it.
"""

import os
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import cast

from PIL import Image, ImageOps

from .filters import ScanFilter
from .app_logging import log
from .scanner import DuplicateFile
from .callbacks import CancelledCallback, ProgressCallback
from .i18n import tr

# Colour signature: a tuple of (r, g, b) colours, one per cell of the 4×4 grid.
Color = tuple[tuple[int, int, int], ...]

# Extensions that Pillow opens without extra plugins.
IMAGE_EXTENSIONS = {
    "jpg", "jpeg", "jpe", "png", "gif", "bmp", "webp",
    "tif", "tiff", "ppm", "pgm",
}
# HEIC/HEIF are left out: Pillow does not open them without pillow-heif.

_DHASH_SIDE = 8            # -> hash of 8*8 = 64 bits
_COLOR_SIDE = 4            # -> signature of 4*4 RGB cells

# Lossless formats: at equal resolution they are preferred as the
# "best copy" (they are usually the original file, not a re-save).
_LOSSLESS_EXT = {"png", "tif", "tiff", "bmp", "ppm", "pgm"}


def _is_lossless(path: str) -> bool:
    return os.path.splitext(path)[1].lower().lstrip(".") in _LOSSLESS_EXT


class ComparisonCancelled(Exception):
    """The caller asked to abort halfway through."""


@dataclass
class ImageFingerprint:
    path: str
    size: int
    width: int
    height: int
    dhash: int
    color: Color  # length _COLOR_SIDE**2

    @property
    def megapixels(self) -> float:
        return (self.width * self.height) / 1_000_000


@dataclass
class SimilarGroup:
    """Set of 2+ visually similar images.

    `files` are DuplicateFile (path + size) so that the keep/move selection
    and the move to quarantine can be reused as they are.
    `fingerprints` carries the extra data (resolution, similarity) for the
    interface. Both lists are in the same order; the first one is the
    "best" copy (most resolution, and on a tie, the largest file).
    """

    fingerprints: list[ImageFingerprint]
    files: list[DuplicateFile]      # same order as fingerprints
    similarity: list[float]          # 0..1 of each photo relative to the best one

    @property
    def count(self) -> int:
        return len(self.files)

    @property
    def size(self) -> int:
        # For compatibility with DuplicateGroup. Not all copies
        # weigh the same, so we give the size of the best one.
        return self.files[0].size

    @property
    def reclaimable_space(self) -> int:
        return sum(a.size for a in self.files[1:])


@dataclass
class SimilarResult:
    groups: list[SimilarGroup]
    total_images: int
    errors: list[tuple[str, str]] = field(default_factory=list)   # (path, message)
    total_excluded: int = 0

    @property
    def total_groups(self) -> int:
        return len(self.groups)

    @property
    def total_photos_in_groups(self) -> int:
        return sum(g.count for g in self.groups)

    @property
    def extra_copies(self) -> int:
        return sum(g.count - 1 for g in self.groups)

    @property
    def total_reclaimable_space(self) -> int:
        return sum(g.reclaimable_space for g in self.groups)


# ----------------------------------------------------------------------
# Fingerprint of an image
# ----------------------------------------------------------------------
def _load_thumbnails(
    path: str,
) -> tuple[list[int], list[tuple[int, int, int]], tuple[int, int]]:
    """Opens the image once and returns (gray_9x8, rgb_4x4, (w, h))."""
    with Image.open(path) as im:
        width, height = im.size          # real size, before touching anything
        # draft speeds up the decoding of large JPEGs a lot (but changes
        # im.size, which is why it is read beforehand).
        try:
            im.draft("L", (64, 64))
        except (ValueError, OSError):  # draft is optional: if unavailable, decode in full
            pass
        upright = ImageOps.exif_transpose(im)     # respects the EXIF orientation
        gray = upright.convert("L").resize(
            (_DHASH_SIDE + 1, _DHASH_SIDE), Image.Resampling.BOX)
        rgb = upright.convert("RGB").resize(
            (_COLOR_SIDE, _COLOR_SIDE), Image.Resampling.BOX)
    # Pillow returns a wide type (depending on the image mode); here we know
    # that "L" gives integers and "RGB" gives (r, g, b) tuples.
    gray_data = cast(tuple[int, ...], gray.get_flattened_data())
    rgb_data = cast(tuple[tuple[int, int, int], ...], rgb.get_flattened_data())
    return list(gray_data), list(rgb_data), (width, height)


def compute_fingerprint(path: str) -> ImageFingerprint:
    """ImageFingerprint of `path`. Raises OSError/Image errors if it cannot be opened."""
    gray, rgb, (width, height) = _load_thumbnails(path)

    # dHash: on a 9x8 grayscale thumbnail, for each row we compare
    # every pixel with the one to its right. It gives 1 if the brightness "goes up", 0 if it
    # "goes down". 8 comparisons per row x 8 rows = 64 bits. What it measures
    # is the shape of the image, not the colours, which is why it withstands
    # recompression and filters well.
    width_g = _DHASH_SIDE + 1        # the thumbnail has 1 extra column
    bits = 0
    for row in range(_DHASH_SIDE):
        base = row * width_g       # first pixel of this row in the flat list
        for col in range(_DHASH_SIDE):
            left = gray[base + col]
            right = gray[base + col + 1]
            # shifts the hash one position and appends the new bit at the end
            bits = (bits << 1) | (1 if left < right else 0)

    try:
        size = os.path.getsize(path)
    except OSError:
        size = 0

    return ImageFingerprint(
        path=path, size=size, width=width, height=height,
        dhash=bits, color=tuple(rgb),
    )


def hamming_distance(a: int, b: int) -> int:
    # XOR sets to 1 the bits where a and b differ; we count those ones.
    # 0 = identical hash; 64 = completely opposite.
    return bin(a ^ b).count("1")


def color_distance(c1: Sequence[Sequence[int]], c2: Sequence[Sequence[int]]) -> float:
    """Mean per-channel difference between two colour signatures (0..255)."""
    total = 0
    for (r1, g1, b1), (r2, g2, b2) in zip(c1, c2):
        total += abs(r1 - r2) + abs(g1 - g2) + abs(b1 - b2)
    return total / (len(c1) * 3)


# ----------------------------------------------------------------------
# BK-tree: a tree to look for "the ones within N distance"
# without comparing everything against everything. Each node stores a key (a dHash)
# and its children are labelled with the exact distance to that node.
# ----------------------------------------------------------------------
type _Node = tuple[int, int, dict[int, _Node]]      # (key, index, {distance: subnode})


class _BKTree:
    def __init__(self) -> None:
        self._root: _Node | None = None

    def add(self, key: int, index: int) -> None:
        if self._root is None:
            self._root = (key, index, {})
            return
        node = self._root
        while True:
            d = hamming_distance(key, node[0])
            child = node[2].get(d)
            if child is None:
                # there is no child at that exact distance: the new one goes here
                node[2][d] = (key, index, {})
                return
            node = child          # there was already one: we keep going down through it

    def neighbors(self, key: int, radius: int) -> list[int]:
        """Indices whose keys are within <= `radius` of `key`."""
        if self._root is None:
            return []
        output: list[int] = []
        stack: list[_Node] = [self._root]
        while stack:
            node = stack.pop()
            d = hamming_distance(key, node[0])
            if d <= radius:
                output.append(node[1])
            # BK-tree trick: there can only be neighbours in the children
            # whose distance label is in [d - radius, d + radius]
            # (triangle inequality). The rest is pruned.
            for child_dist, child in node[2].items():
                if d - radius <= child_dist <= d + radius:
                    stack.append(child)
        return output


# ----------------------------------------------------------------------
# Union-Find (disjoint sets): to join chains of similar images.
# _parent[i] points to "another one in the same group"; following the chain
# leads to the representative of the group.
# ----------------------------------------------------------------------
class _UnionFind:
    def __init__(self, n: int) -> None:
        self._parent = list(range(n))   # at the start each one is its own group

    def root(self, x: int) -> int:
        # goes up to the representative; along the way it "flattens" the chain so that
        # next time it is shorter (path compression).
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]
            x = self._parent[x]
        return x

    def join(self, a: int, b: int) -> None:
        ra, rb = self.root(a), self.root(b)
        if ra != rb:
            self._parent[ra] = rb       # hangs one group from the other

    def groups(self) -> list[list[int]]:
        # groups the indices by their representative
        by_root: dict[int, list[int]] = {}
        for i in range(len(self._parent)):
            by_root.setdefault(self.root(i), []).append(i)
        return list(by_root.values())


# ----------------------------------------------------------------------
# Main API
# ----------------------------------------------------------------------
def list_images(root_folder: str, filter: ScanFilter | None = None) -> list[str]:
    """Paths of image files under `root_folder` (recursive).

    `filter` is an optional ScanFilter (its excluded folders and
    names are respected; the extensions are always limited to images).
    """
    paths: list[str] = []
    for current_dir, subdirs, names in os.walk(root_folder):
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

    # 1) Compute the fingerprint (dHash + colour) of each image. The ones that
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
            fingerprints.append(compute_fingerprint(path))
        except Exception as e:  # a broken or odd file must not stop the whole analysis
            log.info("Could not analyze image %s: %s", path, e)
            errors.append((path, str(e)))

    # 2) Put all the dHashes in a BK-tree to find neighbours quickly.
    tree = _BKTree()
    for idx, h in enumerate(fingerprints):
        tree.add(h.dhash, idx)

    # 3) For each image, look for its neighbours by structure (Hamming) and,
    # if the colour fits too, join them into the same group.
    uf = _UnionFind(len(fingerprints))
    for idx, h in enumerate(fingerprints):
        if cancelled():
            raise ComparisonCancelled()
        for neighbor in tree.neighbors(h.dhash, hamming_threshold):
            if neighbor == idx:
                continue
            if color_distance(h.color, fingerprints[neighbor].color) <= color_threshold:
                uf.join(idx, neighbor)

    # 4) Build the final groups (only those with 2+ photos).
    groups: list[SimilarGroup] = []
    for indices in uf.groups():
        if len(indices) < 2:
            continue
        members = [fingerprints[i] for i in indices]
        # The "best" copy: most megapixels; on a tie, a lossless format
        # before JPEG; and on a tie, the largest file.
        members.sort(
            key=lambda h: (h.width * h.height, _is_lossless(h.path), h.size),
            reverse=True)
        best = members[0]
        similarity = [
            1.0 - hamming_distance(m.dhash, best.dhash) / 64.0
            for m in members
        ]
        groups.append(SimilarGroup(
            fingerprints=members,
            files=[DuplicateFile(m.path, m.size) for m in members],
            similarity=similarity,
        ))

    # The groups that free the most space, first.
    groups.sort(key=lambda g: -g.reclaimable_space)

    progress(total, total, tr("perceptual.finished"))
    return SimilarResult(
        groups=groups,
        total_images=len(fingerprints),
        errors=errors,
    )


def analyze_folder(
    root_folder: str,
    hamming_threshold: int = 10,
    color_threshold: float = 32,
    filter: ScanFilter | None = None,
    progress: ProgressCallback | None = None,
    cancelled: CancelledCallback | None = None,
) -> SimilarResult:
    """Shortcut: list the images of a folder and group them by similarity."""
    if not os.path.isdir(root_folder):
        raise NotADirectoryError(tr("common.not_a_folder", root_folder=root_folder))
    paths = list_images(root_folder, filter=filter)
    return group_similar(
        paths, hamming_threshold=hamming_threshold, color_threshold=color_threshold,
        progress=progress, cancelled=cancelled)
