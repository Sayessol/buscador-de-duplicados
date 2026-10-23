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

    python tests/check_perceptual.py
    python tests/check_perceptual.py "D:\\Fotos" 10
"""

import random
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image, ImageDraw, ImageEnhance   # noqa: E402

from core.perceptual import analyze_folder  # noqa: E402
from core.hashing import format_size                       # noqa: E402

failures = []


def check(cond, msg):
    print(f"  [{'OK  ' if cond else 'FALLA'}] {msg}")
    if not cond:
        failures.append(msg)


def photo_base(seed, size=(900, 600)):
    """Imagen con formas de colores: suficiente estructura para el dHash."""
    rnd = random.Random(seed)
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


def build(base: Path):
    base.mkdir(parents=True, exist_ok=True)
    original = photo_base(1)

    # --- versiones de la MISMA foto (deben acabar en un grupo) --------
    original.save(base / "playa_original.png")
    original.save(base / "playa_calidad_baja.jpg", quality=25)
    original.resize((450, 300)).save(base / "playa_pequena.jpg", quality=80)

    filtered = ImageEnhance.Color(original).enhance(1.8)
    filtered = ImageEnhance.Brightness(filtered).enhance(1.15)
    filtered.save(base / "playa_con_filtro.jpg", quality=85)

    mark = original.copy()
    d = ImageDraw.Draw(mark)
    d.rectangle([740, 550, 890, 590], fill=(255, 255, 255))
    d.text((748, 560), "©2024", fill=(0, 0, 0))
    mark.save(base / "playa_marca_agua.jpg", quality=85)

    # --- otra foto distinta, también con un par de versiones ----------
    other = photo_base(99)
    other.save(base / "montana_original.png")
    other.save(base / "montana_recomprimida.jpg", quality=30)

    # --- fotos sueltas sin relación ---------------------------------
    for s in (7, 21, 42):
        photo_base(s).save(base / f"suelta_{s}.jpg", quality=80)

    # una imagen corrupta (debe ir a 'errores', no romper nada)
    (base / "rota.jpg").write_bytes(b"esto no es una imagen")


def names(group):
    return sorted(Path(a.path).name for a in group.files)


def main():
    with tempfile.TemporaryDirectory(prefix="dup_perc_") as tmp:
        base = Path(tmp) / "fotos"
        build(base)

        r = analyze_folder(str(base), hamming_threshold=12)
        print(f"\n  {r.total_images} imágenes analizadas, "
              f"{r.total_groups} grupos, {len(r.errors)} ilegibles\n")
        for i, g in enumerate(r.groups, 1):
            print(f"  Grupo {i}  (mejor: {Path(g.files[0].path).name}, "
                  f"{g.fingerprints[0].width}x{g.fingerprints[0].height}):")
            for a, s in zip(g.files, g.similarity):
                print(f"      {s * 100:5.1f}%  {Path(a.path).name}")

        groups_by_name = {tuple(names(g)) for g in r.groups}

        beach = {"playa_original.png", "playa_calidad_baja.jpg",
                 "playa_pequena.jpg", "playa_con_filtro.jpg",
                 "playa_marca_agua.jpg"}
        mountain = {"montana_original.png", "montana_recomprimida.jpg"}

        beach_group = next((g for g in groups_by_name if "playa_original.png" in g), None)
        mountain_group = next((g for g in groups_by_name if "montana_original.png" in g), None)

        check(beach_group is not None and beach.issubset(set(beach_group)),
              "las 5 versiones de la foto 'playa' caen en el mismo grupo")
        check(mountain_group is not None and set(mountain_group) == mountain,
              "las 2 versiones de 'montana' forman su propio grupo")
        check(all(not any(n.startswith("suelta_") for n in g)
                  for g in groups_by_name),
              "ninguna foto suelta se coló en un grupo")
        check(len(r.errors) == 1 and "rota.jpg" in r.errors[0][0],
              "la imagen corrupta se reporta como error, no rompe el análisis")

        if beach_group:
            g = next(g for g in r.groups if "playa_original.png" in names(g))
            check(Path(g.files[0].path).name == "playa_original.png",
                  "la 'mejor' copia de playa es el PNG original (más resolución)")
            check(g.reclaimable_space > 0, "el grupo reporta espacio recuperable")

    # --- carpeta real opcional -------------------------------------
    if len(sys.argv) > 1 and Path(sys.argv[1]).is_dir():
        threshold = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        print(f"\n=== Carpeta real: {sys.argv[1]}  (umbral {threshold}) ===")
        rr = analyze_folder(sys.argv[1], hamming_threshold=threshold,
                              progress=lambda a, t, m: print(f"  {m}", end="\r"))
        print(f"\n  {rr.total_images} imágenes, {rr.total_groups} grupos de parecidas, "
              f"recuperable {format_size(rr.total_reclaimable_space)}")
        for i, g in enumerate(rr.groups[:15], 1):
            print(f"\n  Grupo {i} ({g.count} fotos):")
            for a, s in zip(g.files, g.similarity):
                print(f"      {s * 100:5.1f}%  {a.path}")

    print()
    if failures:
        print(f"FALLARON {len(failures)} comprobaciones.")
        sys.exit(1)
    print("NÚCLEO PERCEPTUAL OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
