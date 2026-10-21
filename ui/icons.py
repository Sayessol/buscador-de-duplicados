"""Iconos de la interfaz.

Son glifos Unicode monocromo que dibuja la fuente del sistema (Segoe UI
Symbol / Segoe UI Emoji en Windows). No hay archivos de imagen ni
dependencias: se usan como prefijo del texto de botones y títulos.

`icono_ventana()` dibuja una lupa por código en un PhotoImage para
`app.iconphoto()` (barra de tareas y título de la ventana).
"""

import math
import tkinter as tk

# --- glifos --------------------------------------------------------------
BUSCAR = "\U0001F50D"      # 🔍  escanear / app
CARPETA = "\U0001F4C1"     # 📁  elegir carpeta
ENGRANAJE = "⚙"       # ⚙   opciones
ESTRELLA = "⭐"        # ⭐  carpeta preferida
AUTO = "✨"            # ✨  aplicar regla automática
GRAFICO = "\U0001F4CA"     # 📊  ver tipos de archivo
GUARDAR = "\U0001F4BE"     # 💾  exportar CSV
ESCUDO = "\U0001F6E1"      # 🛡   mover a cuarentena (zona segura, no se borra)
OK = "✔"              # ✔   validación correcta
AVISO = "⚠"           # ⚠   validación pendiente
CRUZ = "✕"            # ✕   cancelar
TRI_DER = "▸"         # ▸   sección colapsada
TRI_ABAJO = "▾"       # ▾   sección abierta
FLECHA = "→"          # →   "mover"
RECARGA = "↻"         # ↻   reescanear / deshacer
REUNIR = "\U0001F4E5"      # 📥  reunir imágenes
HISTORIAL = "\U0001F553"   # 🕓  historial de operaciones

# --- categorías de tipos de archivo -----------------------------------
CAT_IMAGENES = "\U0001F4F7"     # 📷
CAT_AUDIO = "\U0001F3B5"        # 🎵
CAT_VIDEO = "\U0001F3AC"        # 🎬
CAT_DOCUMENTOS = "\U0001F4C4"   # 📄
CAT_COMPRIMIDOS = "\U0001F4E6"  # 📦

ICONO_CATEGORIA = {
    "Imágenes": CAT_IMAGENES,
    "Audio": CAT_AUDIO,
    "Vídeo": CAT_VIDEO,
    "Documentos": CAT_DOCUMENTOS,
    "Comprimidos": CAT_COMPRIMIDOS,
}


def icono_ventana(size=64, color="#5aa9e6"):
    """PhotoImage con una lupa dibujada, para app.iconphoto(True, img).

    Los píxeles no pintados quedan transparentes.
    """
    img = tk.PhotoImage(width=size, height=size)

    cx, cy = size * 0.42, size * 0.42
    r = size * 0.27
    grosor = max(2.0, size / 12)

    def punto(x, y):
        xi, yi = int(round(x)), int(round(y))
        if 0 <= xi < size and 0 <= yi < size:
            img.put(color, to=(xi, yi))

    # Anillo de la lupa.
    pasos = max(120, int(size * 6))
    for i in range(pasos):
        ang = 2 * math.pi * i / pasos
        for t in range(int(grosor)):
            rr = r - grosor / 2 + t
            punto(cx + rr * math.cos(ang), cy + rr * math.sin(ang))

    # Mango.
    hx, hy = cx + r * 0.7, cy + r * 0.7
    ex, ey = size * 0.9, size * 0.9
    largo = max(60, int(size * 3))
    rad = int(grosor / 2) + 1
    for i in range(largo):
        f = i / largo
        x = hx + (ex - hx) * f
        y = hy + (ey - hy) * f
        for dx in range(-rad, rad + 1):
            for dy in range(-rad, rad + 1):
                if dx * dx + dy * dy <= rad * rad:
                    punto(x + dx, y + dy)

    return img
