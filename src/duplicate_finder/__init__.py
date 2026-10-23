"""Duplicate Finder: finds repeated files and similar photos and moves them to quarantine.

The code is split in layers; each one only depends on the ones below it:

  presentation    the Tkinter / CustomTkinter interface
  application     the use cases (scan, move to quarantine, gather, undo, ...)
  infrastructure  the disk, the history file, the configuration, the logs, Pillow
  domain          the data and the rules, with no input or output at all

`i18n` (the texts the user sees) is shared by the layers above the domain.

The golden rule holds everywhere: **never delete, never modify the original, only read
and (when the user confirms) move.**
"""

# Single source of the version: the window and the release name use it.
# When publishing a new version, change it here and add its section to CHANGELOG.md
# (a test checks that the two match).
__version__ = "1.0.0"
