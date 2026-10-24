"""Generates docs/img/social-preview.png (1280x640): the image shown when sharing the repo.

    python docs/gen_cover.py        # English (the one the repository uses): social-preview.png
    python docs/gen_cover.py es     # Spanish: social-preview.es.png

It needs the screenshot of the simple mode (python docs/capture.py dark en|es). It is uploaded by
hand on GitHub: Settings -> General -> Social preview.
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

IMG = Path(__file__).resolve().parent / "img"
LANGUAGE = sys.argv[1] if len(sys.argv) > 1 else "en"
assert LANGUAGE in ("es", "en"), "usage: gen_cover.py [es|en]"
TEXTS = {
    "es": (
        "Buscador de\nduplicados",
        "Encuentra duplicados y fotos parecidas.",
        "Nunca borra tus originales. Todo se puede deshacer.",
        "Hecho con Claude como copiloto",
    ),
    "en": (
        "Duplicate\nFinder",
        "Finds duplicates and similar photos.",
        "Your originals are never deleted. Undo anything.",
        "Built with Claude as a copilot",
    ),
}[LANGUAGE]
FONTS = Path("C:/Windows/Fonts")


def font(name, size):
    try:
        return ImageFont.truetype(str(FONTS / name), size)
    except OSError:
        return ImageFont.load_default()


BACKGROUND, TEXT, MUTED, ACCENT = (30, 33, 38), (240, 243, 247), (169, 176, 186), (74, 163, 223)

canvas = Image.new("RGB", (1280, 640), BACKGROUND)
d = ImageDraw.Draw(canvas)
d.rectangle([0, 0, 12, 640], fill=ACCENT)  # colour band on the left

d.text((70, 110), TEXTS[0], font=font("segoeuib.ttf", 64), fill=TEXT, spacing=4)
d.text((72, 290), TEXTS[1], font=font("segoeui.ttf", 28), fill=MUTED)
d.text((72, 330), TEXTS[2], font=font("segoeui.ttf", 28), fill=MUTED)

x = 72
for text in ("Python", "CustomTkinter", "Windows", "MIT"):
    f = font("segoeuib.ttf", 24)
    width = int(d.textlength(text, font=f)) + 36
    d.rounded_rectangle([x, 410, x + width, 458], radius=24, outline=ACCENT, width=2)
    d.text((x + 18, 418), text, font=f, fill=ACCENT)
    x += width + 14

d.text((72, 560), TEXTS[3], font=font("segoeui.ttf", 26), fill=MUTED)

# Screenshot of the app, tilted to the right and with a shadow.
capture = Image.open(IMG / LANGUAGE / "01_simple.png").convert("RGB")
capture = capture.resize((560, round(capture.height * 560 / capture.width)), Image.LANCZOS)
shadow = Image.new("RGBA", (capture.width + 80, capture.height + 80), (0, 0, 0, 0))
ImageDraw.Draw(shadow).rectangle(
    [40, 50, 40 + capture.width, 50 + capture.height], fill=(0, 0, 0, 170)
)
shadow = shadow.filter(ImageFilter.GaussianBlur(18))
canvas.paste(shadow, (690, 110), shadow)
canvas.paste(capture, (730, 140))

output = IMG / ("social-preview.png" if LANGUAGE == "en" else f"social-preview.{LANGUAGE}.png")
canvas.save(output, optimize=True)
print(output.name, canvas.size)
