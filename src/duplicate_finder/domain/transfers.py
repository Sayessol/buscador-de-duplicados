"""Data of the operations that move or copy files: one transfer, the result of a
batch, the quarantine moves and the rules for files that are not images."""

from dataclasses import dataclass, field

MOVE = "move"
COPY = "copy"


@dataclass
class Transfer:
    source: str
    destination: str
    size: int = 0
    ok: bool = False
    error: str = ""


@dataclass
class TransferResult:
    transfers: list[Transfer] = field(default_factory=list)
    action: str = MOVE
    log_path: str = ""

    @property
    def done(self) -> list[Transfer]:
        return [t for t in self.transfers if t.ok]

    @property
    def failed(self) -> list[Transfer]:
        return [t for t in self.transfers if not t.ok]

    @property
    def bytes_done(self) -> int:
        return sum(t.size for t in self.done)


@dataclass
class Move:
    group: int
    source: str
    destination: str
    size: int
    ok: bool = False
    error: str = ""


@dataclass
class QuarantineResult:
    moves: list[Move] = field(default_factory=list)
    log_path: str = ""

    @property
    def moved(self) -> list[Move]:
        return [m for m in self.moves if m.ok]

    @property
    def failed(self) -> list[Move]:
        return [m for m in self.moves if not m.ok]

    @property
    def bytes_moved(self) -> int:
        return sum(m.size for m in self.moved)


LEAVE = "leave"


# (for non-images: LEAVE | MOVE | GROUP)
GROUP = "group"


@dataclass
class NonImageRules:
    """What to do with each kind of file that is not an image.

    action_by_ext: ext -> "leave" | "move" | "group"
    folder_by_ext: ext -> folder name (only if "group")
    """

    action_by_ext: dict[str, str] = field(default_factory=dict)
    folder_by_ext: dict[str, str] = field(default_factory=dict)

    def action(self, ext: str) -> str:
        return self.action_by_ext.get(ext, LEAVE)

    def folder(self, ext: str) -> str:
        return (self.folder_by_ext.get(ext) or ext).strip() or ext
