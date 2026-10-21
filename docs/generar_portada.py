"""Genera docs/img/social-preview.png (1280x640): la imagen que se ve al compartir el repo.

    python docs/generar_portada.py

Se sube a mano en GitHub: Settings -> General -> Social preview.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

IMG = Path(__file__).resolve().parent / "img"
FUENTES = Path("C:/Windows/Fonts")


def fuente(nombre, tam):
    try:
        return ImageFont.truetype(str(FUENTES / nombre), tam)
    except OSError:
        return ImageFont.load_default()


FONDO, TEXTO, TENUE, ACENTO = (30, 33, 38), (240, 243, 247), (169, 176, 186), (74, 163, 223)

lienzo = Image.new("RGB", (1280, 640), FONDO)
d = ImageDraw.Draw(lienzo)
d.rectangle([0, 0, 12, 640], fill=ACENTO)             # franja de color a la izquierda

d.text((70, 110), "Buscador de\nduplicados", font=fuente("segoeuib.ttf", 64), fill=TEXTO,
       spacing=4)
d.text((72, 290), "Encuentra duplicados y fotos parecidas.",
       font=fuente("segoeui.ttf", 28), fill=TENUE)
d.text((72, 330), "Nunca borra tus originales. Todo se puede deshacer.",
       font=fuente("segoeui.ttf", 28), fill=TENUE)

x = 72
for texto in ("Python", "CustomTkinter", "Windows", "MIT"):
    f = fuente("segoeuib.ttf", 24)
    ancho = int(d.textlength(texto, font=f)) + 36
    d.rounded_rectangle([x, 410, x + ancho, 458], radius=24, outline=ACENTO, width=2)
    d.text((x + 18, 418), texto, font=f, fill=ACENTO)
    x += ancho + 14

d.text((72, 560), "Hecho con Claude como copiloto", font=fuente("segoeui.ttf", 26), fill=TENUE)

# Captura de la app, inclinada hacia la derecha y con sombra.
captura = Image.open(IMG / "01_sencilla.png").convert("RGB")
captura = captura.resize((560, round(captura.height * 560 / captura.width)), Image.LANCZOS)
sombra = Image.new("RGBA", (captura.width + 80, captura.height + 80), (0, 0, 0, 0))
ImageDraw.Draw(sombra).rectangle([40, 50, 40 + captura.width, 50 + captura.height],
                                 fill=(0, 0, 0, 170))
sombra = sombra.filter(ImageFilter.GaussianBlur(18))
lienzo.paste(sombra, (690, 110), sombra)
lienzo.paste(captura, (730, 140))

lienzo.save(IMG / "social-preview.png", optimize=True)
print("social-preview.png", lienzo.size)
