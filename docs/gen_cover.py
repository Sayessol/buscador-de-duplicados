"""Genera docs/img/social-preview.png (1280x640): la imagen que se ve al compartir el repo.

    python docs/gen_cover.py

Se sube a mano en GitHub: Settings -> General -> Social preview.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

IMG = Path(__file__).resolve().parent / "img"
FONTS = Path("C:/Windows/Fonts")


def font(name, size):
    try:
        return ImageFont.truetype(str(FONTS / name), size)
    except OSError:
        return ImageFont.load_default()


BACKGROUND, TEXT, MUTED, ACCENT = (30, 33, 38), (240, 243, 247), (169, 176, 186), (74, 163, 223)

canvas = Image.new("RGB", (1280, 640), BACKGROUND)
d = ImageDraw.Draw(canvas)
d.rectangle([0, 0, 12, 640], fill=ACCENT)             # franja de color a la izquierda

d.text((70, 110), "Buscador de\nduplicados", font=font("segoeuib.ttf", 64), fill=TEXT,
       spacing=4)
d.text((72, 290), "Encuentra duplicados y fotos parecidas.",
       font=font("segoeui.ttf", 28), fill=MUTED)
d.text((72, 330), "Nunca borra tus originales. Todo se puede deshacer.",
       font=font("segoeui.ttf", 28), fill=MUTED)

x = 72
for text in ("Python", "CustomTkinter", "Windows", "MIT"):
    f = font("segoeuib.ttf", 24)
    width = int(d.textlength(text, font=f)) + 36
    d.rounded_rectangle([x, 410, x + width, 458], radius=24, outline=ACCENT, width=2)
    d.text((x + 18, 418), text, font=f, fill=ACCENT)
    x += width + 14

d.text((72, 560), "Hecho con Claude como copiloto", font=font("segoeui.ttf", 26), fill=MUTED)

# Captura de la app, inclinada hacia la derecha y con sombra.
capture = Image.open(IMG / "01_sencilla.png").convert("RGB")
capture = capture.resize((560, round(capture.height * 560 / capture.width)), Image.LANCZOS)
shadow = Image.new("RGBA", (capture.width + 80, capture.height + 80), (0, 0, 0, 0))
ImageDraw.Draw(shadow).rectangle([40, 50, 40 + capture.width, 50 + capture.height],
                                 fill=(0, 0, 0, 170))
shadow = shadow.filter(ImageFilter.GaussianBlur(18))
canvas.paste(shadow, (690, 110), shadow)
canvas.paste(capture, (730, 140))

canvas.save(IMG / "social-preview.png", optimize=True)
print("social-preview.png", canvas.size)
