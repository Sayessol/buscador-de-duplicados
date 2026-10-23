"""Iconos de la interfaz.

Son glifos Unicode monocromo que dibuja la fuente del sistema (Segoe UI
Symbol / Segoe UI Emoji en Windows). No hay archivos de imagen ni
dependencias: se usan como prefijo del texto de botones y títulos.

`window_icon()` dibuja una lupa por código en un PhotoImage para
`app.iconphoto()` (barra de tareas y título de la ventana).
"""

import math
import tkinter as tk

# --- glifos --------------------------------------------------------------
SEARCH = "\U0001F50D"      # 🔍  escanear / app
FOLDER = "\U0001F4C1"     # 📁  elegir carpeta
GEAR = "⚙"       # ⚙   opciones
STAR = "⭐"        # ⭐  carpeta preferida
AUTO = "✨"            # ✨  aplicar regla automática
CHART = "\U0001F4CA"     # 📊  ver tipos de archivo
SAVE = "\U0001F4BE"     # 💾  exportar CSV
SHIELD = "\U0001F6E1"      # 🛡   mover a cuarentena (zona segura, no se borra)
OK = "✔"              # ✔   validación correcta
WARNING = "⚠"           # ⚠   validación pendiente
CROSS = "✕"            # ✕   cancelar
TRI_RIGHT = "▸"         # ▸   sección colapsada
TRI_DOWN = "▾"       # ▾   sección abierta
ARROW = "→"          # →   "mover"
RELOAD = "↻"         # ↻   reescanear / deshacer
GATHER = "\U0001F4E5"      # 📥  reunir imágenes
HISTORY = "\U0001F553"   # 🕓  historial de operaciones

# --- categorías de tipos de archivo -----------------------------------
CAT_IMAGES = "\U0001F4F7"     # 📷
CAT_AUDIO = "\U0001F3B5"        # 🎵
CAT_VIDEO = "\U0001F3AC"        # 🎬
CAT_DOCUMENTS = "\U0001F4C4"   # 📄
CAT_ARCHIVES = "\U0001F4E6"  # 📦

CATEGORY_ICON = {
    "Imágenes": CAT_IMAGES,
    "Audio": CAT_AUDIO,
    "Vídeo": CAT_VIDEO,
    "Documentos": CAT_DOCUMENTS,
    "Comprimidos": CAT_ARCHIVES,
}


def window_icon(size=64, color="#5aa9e6"):
    """PhotoImage con una lupa dibujada, para app.iconphoto(True, img).

    Los píxeles no pintados quedan transparentes.
    """
    img = tk.PhotoImage(width=size, height=size)

    cx, cy = size * 0.42, size * 0.42
    r = size * 0.27
    thickness = max(2.0, size / 12)

    def point(x, y):
        xi, yi = int(round(x)), int(round(y))
        if 0 <= xi < size and 0 <= yi < size:
            img.put(color, to=(xi, yi))

    # Anillo de la lupa.
    steps = max(120, int(size * 6))
    for i in range(steps):
        ang = 2 * math.pi * i / steps
        for t in range(int(thickness)):
            rr = r - thickness / 2 + t
            point(cx + rr * math.cos(ang), cy + rr * math.sin(ang))

    # Mango.
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
