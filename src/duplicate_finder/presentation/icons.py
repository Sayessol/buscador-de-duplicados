"""Interface icons.

They are monochrome Unicode glyphs drawn by the system font (Segoe UI
Symbol / Segoe UI Emoji on Windows). There are no image files or
dependencies: they are used as a prefix of the text of buttons and titles.

`window_icon()` draws a magnifying glass in code on a PhotoImage for
`app.iconphoto()` (taskbar and window title).
"""

import math
import tkinter as tk

# --- glyphs ---------------------------------------------------------------
SEARCH = "\U0001f50d"  # 🔍  scan / app
FOLDER = "\U0001f4c1"  # 📁  choose folder
GEAR = "⚙"  # ⚙   options
STAR = "⭐"  # ⭐  preferred folder
AUTO = "✨"  # ✨  apply automatic rule
CHART = "\U0001f4ca"  # 📊  view file kinds
SAVE = "\U0001f4be"  # 💾  export CSV
SHIELD = "\U0001f6e1"  # 🛡   move to quarantine (safe zone, nothing is deleted)
OK = "✔"  # ✔   validation passed
WARNING = "⚠"  # ⚠   validation pending
CROSS = "✕"  # ✕   cancel
TRI_RIGHT = "▸"  # ▸   collapsed section
TRI_DOWN = "▾"  # ▾   open section
ARROW = "→"  # →   "move"
RELOAD = "↻"  # ↻   rescan / undo
GATHER = "\U0001f4e5"  # 📥  gather images
HISTORY = "\U0001f553"  # 🕓  history of operations

# --- file kind categories -----------------------------------
CAT_IMAGES = "\U0001f4f7"  # 📷
CAT_AUDIO = "\U0001f3b5"  # 🎵
CAT_VIDEO = "\U0001f3ac"  # 🎬
CAT_DOCUMENTS = "\U0001f4c4"  # 📄
CAT_ARCHIVES = "\U0001f4e6"  # 📦

CATEGORY_ICON = {
    "images": CAT_IMAGES,
    "audio": CAT_AUDIO,
    "video": CAT_VIDEO,
    "documents": CAT_DOCUMENTS,
    "archives": CAT_ARCHIVES,
}


def window_icon(size=64, color="#5aa9e6"):
    """PhotoImage with a magnifying glass drawn on it, for app.iconphoto(True, img).

    Unpainted pixels stay transparent.
    """
    img = tk.PhotoImage(width=size, height=size)

    cx, cy = size * 0.42, size * 0.42
    r = size * 0.27
    thickness = max(2.0, size / 12)

    def point(x, y):
        xi, yi = int(round(x)), int(round(y))
        if 0 <= xi < size and 0 <= yi < size:
            img.put(color, to=(xi, yi))

    # Ring of the magnifying glass.
    steps = max(120, int(size * 6))
    for i in range(steps):
        ang = 2 * math.pi * i / steps
        for t in range(int(thickness)):
            rr = r - thickness / 2 + t
            point(cx + rr * math.cos(ang), cy + rr * math.sin(ang))

    # Handle.
    hx, hy = cx + r * 0.7, cy + r * 0.7
    ex, ey = size * 0.9, size * 0.9
    long = max(60, int(size * 3))
    rad = int(thickness / 2) + 1
    for i in range(long):
        f = i / long
        x = hx + (ex - hx) * f
        y = hy + (ey - hy) * f
        for dx in range(-rad, rad + 1):
            for dy in range(-rad, rad + 1):
                if dx * dx + dy * dy <= rad * rad:
                    point(x + dx, y + dy)

    return img
