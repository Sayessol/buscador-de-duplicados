"""Prueba del núcleo de fotos parecidas.

Genera un juego de imágenes sintéticas (una foto "original" y varias
versiones alteradas: recomprimida, redimensionada, con filtro de color,
con marca de agua) más imágenes sin relación, y comprueba que la
agrupación:

  * junta todas las versiones de la misma foto en un grupo,
  * NO junta las imágenes que no tienen nada que ver,
  * elige como "mejor" la de más resolución.

Con una ruta como argumento, además analiza esa carpeta real y lista
los grupos encontrados (útil para calibrar el umbral con fotos propias):

    python pruebas/probar_perceptual.py
    python pruebas/probar_perceptual.py "D:\\Fotos" 10
"""

import random
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image, ImageDraw, ImageEnhance   # noqa: E402

from core.perceptual import analizar_carpeta  # noqa: E402
from core.hashing import formatear_tamano                       # noqa: E402

fallos = []


def check(cond, msg):
    print(f"  [{'OK  ' if cond else 'FALLA'}] {msg}")
    if not cond:
        fallos.append(msg)


def foto_base(semilla, size=(900, 600)):
    """Imagen con formas de colores: suficiente estructura para el dHash."""
    rnd = random.Random(semilla)
    im = Image.new("RGB", size, (rnd.randint(0, 60),) * 3)
    d = ImageDraw.Draw(im)
    for _ in range(18):
        x0, y0 = rnd.randint(0, size[0]), rnd.randint(0, size[1])
        x1, y1 = x0 + rnd.randint(40, 300), y0 + rnd.randint(40, 300)
        col = (rnd.randint(0, 255), rnd.randint(0, 255), rnd.randint(0, 255))
        if rnd.random() < 0.5:
            d.rectangle([x0, y0, x1, y1], fill=col)
        else:
            d.ellipse([x0, y0, x1, y1], fill=col)
    return im


def construir(base: Path):
    base.mkdir(parents=True, exist_ok=True)
    original = foto_base(1)

    # --- versiones de la MISMA foto (deben acabar en un grupo) --------
    original.save(base / "playa_original.png")
    original.save(base / "playa_calidad_baja.jpg", quality=25)
    original.resize((450, 300)).save(base / "playa_pequena.jpg", quality=80)

    filtrada = ImageEnhance.Color(original).enhance(1.8)
    filtrada = ImageEnhance.Brightness(filtrada).enhance(1.15)
    filtrada.save(base / "playa_con_filtro.jpg", quality=85)

    marca = original.copy()
    d = ImageDraw.Draw(marca)
    d.rectangle([740, 550, 890, 590], fill=(255, 255, 255))
    d.text((748, 560), "©2024", fill=(0, 0, 0))
    marca.save(base / "playa_marca_agua.jpg", quality=85)

    # --- otra foto distinta, también con un par de versiones ----------
    otra = foto_base(99)
    otra.save(base / "montana_original.png")
    otra.save(base / "montana_recomprimida.jpg", quality=30)

    # --- fotos sueltas sin relación ---------------------------------
    for s in (7, 21, 42):
        foto_base(s).save(base / f"suelta_{s}.jpg", quality=80)

    # una imagen corrupta (debe ir a 'errores', no romper nada)
    (base / "rota.jpg").write_bytes(b"esto no es una imagen")


def nombres(grupo):
    return sorted(Path(a.ruta).name for a in grupo.archivos)


def main():
    with tempfile.TemporaryDirectory(prefix="dup_perc_") as tmp:
        base = Path(tmp) / "fotos"
        construir(base)

        r = analizar_carpeta(str(base), umbral_hamming=12)
        print(f"\n  {r.total_imagenes} imágenes analizadas, "
              f"{r.total_grupos} grupos, {len(r.errores)} ilegibles\n")
        for i, g in enumerate(r.grupos, 1):
            print(f"  Grupo {i}  (mejor: {Path(g.archivos[0].ruta).name}, "
                  f"{g.huellas[0].ancho}x{g.huellas[0].alto}):")
            for a, s in zip(g.archivos, g.similitud):
                print(f"      {s * 100:5.1f}%  {Path(a.ruta).name}")

        grupos_por_nombre = {tuple(nombres(g)) for g in r.grupos}

        playa = {"playa_original.png", "playa_calidad_baja.jpg",
                 "playa_pequena.jpg", "playa_con_filtro.jpg",
                 "playa_marca_agua.jpg"}
        montana = {"montana_original.png", "montana_recomprimida.jpg"}

        grupo_playa = next((g for g in grupos_por_nombre if "playa_original.png" in g), None)
        grupo_mont = next((g for g in grupos_por_nombre if "montana_original.png" in g), None)

        check(grupo_playa is not None and playa.issubset(set(grupo_playa)),
              "las 5 versiones de la foto 'playa' caen en el mismo grupo")
        check(grupo_mont is not None and set(grupo_mont) == montana,
              "las 2 versiones de 'montana' forman su propio grupo")
        check(all(not any(n.startswith("suelta_") for n in g)
                  for g in grupos_por_nombre),
              "ninguna foto suelta se coló en un grupo")
        check(len(r.errores) == 1 and "rota.jpg" in r.errores[0][0],
              "la imagen corrupta se reporta como error, no rompe el análisis")

        if grupo_playa:
            g = next(g for g in r.grupos if "playa_original.png" in nombres(g))
            check(Path(g.archivos[0].ruta).name == "playa_original.png",
                  "la 'mejor' copia de playa es el PNG original (más resolución)")
            check(g.espacio_recuperable > 0, "el grupo reporta espacio recuperable")

    # --- carpeta real opcional -------------------------------------
    if len(sys.argv) > 1 and Path(sys.argv[1]).is_dir():
        umbral = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        print(f"\n=== Carpeta real: {sys.argv[1]}  (umbral {umbral}) ===")
        rr = analizar_carpeta(sys.argv[1], umbral_hamming=umbral,
                              progreso=lambda a, t, m: print(f"  {m}", end="\r"))
        print(f"\n  {rr.total_imagenes} imágenes, {rr.total_grupos} grupos de parecidas, "
              f"recuperable {formatear_tamano(rr.espacio_recuperable_total)}")
        for i, g in enumerate(rr.grupos[:15], 1):
            print(f"\n  Grupo {i} ({g.cantidad} fotos):")
            for a, s in zip(g.archivos, g.similitud):
                print(f"      {s * 100:5.1f}%  {a.ruta}")

    print()
    if fallos:
        print(f"FALLARON {len(fallos)} comprobaciones.")
        sys.exit(1)
    print("NÚCLEO PERCEPTUAL OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
