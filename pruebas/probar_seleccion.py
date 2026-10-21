"""Pruebas de SeleccionDuplicados: regla de carpeta preferida, ajuste
manual y validación de "una sola copia por grupo".

    python pruebas/probar_seleccion.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.scanner import ArchivoDup, GrupoDuplicado, ResultadoEscaneo  # noqa: E402
from core.seleccion import (  # noqa: E402
    SeleccionDuplicados, CONSERVAR, MOVER,
    GRUPO_OK, GRUPO_MULTIPLE,
)

fallos = []


def check(cond, msg):
    print(f"  [{'OK  ' if cond else 'FALLA'}] {msg}")
    if not cond:
        fallos.append(msg)


def resultado_de_prueba():
    g1 = GrupoDuplicado(hash="h1", tamano=100, archivos=[
        ArchivoDup(r"D:\Fotos\Organizado\viaje\a.jpg", 100),
        ArchivoDup(r"D:\Descargas\a.jpg", 100),
        ArchivoDup(r"E:\Respaldo\a.jpg", 100),
    ])
    g2 = GrupoDuplicado(hash="h2", tamano=50, archivos=[
        ArchivoDup(r"D:\Descargas\b.txt", 50),
        ArchivoDup(r"D:\Escritorio\b.txt", 50),
    ])
    g3 = GrupoDuplicado(hash="h3", tamano=200, archivos=[
        ArchivoDup(r"D:\Fotos\Organizado\c.png", 200),
        ArchivoDup(r"D:\Fotos\Organizado\copia\c.png", 200),
    ])
    return ResultadoEscaneo(grupos=[g1, g2, g3], total_archivos=7)


def main():
    r = resultado_de_prueba()
    sel = SeleccionDuplicados(r)

    print("\n--- Estado inicial ---")
    check(all(sel.decision(gi, a.ruta) == CONSERVAR
              for gi, g in enumerate(r.grupos) for a in g.archivos),
          "todo arranca en CONSERVAR")
    check(sel.estado_grupo(0) == GRUPO_MULTIPLE, "grupo con 3 conservadas -> MULTIPLE")
    check(not sel.todo_listo(), "nada listo al inicio")
    check(sel.cantidad_a_mover() == 0, "no se movería nada al inicio")

    print("\n--- Regla de carpeta preferida: D:\\Fotos\\Organizado ---")
    resueltos, sin_coincidencia = sel.aplicar_regla_carpeta(r"D:\Fotos\Organizado")
    print(f"    resueltos={resueltos}  sin_coincidencia={sin_coincidencia}")
    check(resueltos == 2, "g1 y g3 tienen copia en la carpeta preferida")
    check(sin_coincidencia == 1, "g2 no tiene copia en la carpeta preferida")

    # g1: conserva la de Organizado, mueve las otras dos
    check(sel.decision(0, r"D:\Fotos\Organizado\viaje\a.jpg") == CONSERVAR,
          "g1 conserva la copia dentro de la carpeta preferida")
    check(sel.decision(0, r"D:\Descargas\a.jpg") == MOVER, "g1 mueve la de Descargas")
    check(sel.estado_grupo(0) == GRUPO_OK, "g1 queda OK")

    # g3: dos copias dentro de la carpeta preferida -> conserva la de ruta más corta
    check(sel.decision(2, r"D:\Fotos\Organizado\c.png") == CONSERVAR,
          "g3 conserva la copia de ruta más corta dentro de la carpeta")
    check(sel.decision(2, r"D:\Fotos\Organizado\copia\c.png") == MOVER,
          "g3 mueve la copia anidada")
    check(sel.estado_grupo(2) == GRUPO_OK, "g3 queda OK")

    # g2: sin coincidencia -> sigue todo en CONSERVAR -> pendiente
    check(sel.estado_grupo(1) == GRUPO_MULTIPLE, "g2 sigue pendiente")
    check(sel.grupos_pendientes() == [1], "solo g2 queda pendiente")
    check(not sel.todo_listo(), "todavía no está todo listo (falta g2)")

    print("\n--- Ajuste manual de g2 ---")
    sel.conservar_solo(1, r"D:\Escritorio\b.txt")
    check(sel.estado_grupo(1) == GRUPO_OK, "g2 resuelto a mano")
    check(sel.todo_listo(), "ahora sí, todo listo")

    print("\n--- Resumen de movimientos ---")
    check(sel.cantidad_a_mover() == 4, "se moverían 4 archivos (2 de g1, 1 de g2, 1 de g3)")
    check(sel.espacio_a_liberar() == 100 + 100 + 50 + 200, "espacio a liberar correcto")

    print("\n--- alternar() ---")
    sel.marcar(1, r"D:\Descargas\b.txt", CONSERVAR)  # ahora g2 tiene 2 conservadas
    check(sel.estado_grupo(1) == GRUPO_MULTIPLE, "marcar dos conservadas rompe g2")
    nueva = sel.alternar(1, r"D:\Descargas\b.txt")
    check(nueva == MOVER and sel.estado_grupo(1) == GRUPO_OK, "alternar lo vuelve a arreglar")

    print("\n--- carpeta preferida vacía o inexistente ---")
    sel2 = SeleccionDuplicados(resultado_de_prueba())
    res, sinc = sel2.aplicar_regla_carpeta("")
    check(res == 0 and sinc == 3, "carpeta vacía: ningún grupo se resuelve")

    print("\n--- preseleccionar_principales() (modo Sencilla) ---")
    import tempfile
    from core.scanner import escanear
    with tempfile.TemporaryDirectory() as tmp:
        raiz = Path(tmp)
        datos = b"contenido identico\n" * 40
        (raiz / "Fotos").mkdir()
        (raiz / "Fotos" / "Backup").mkdir()
        (raiz / "Fotos" / "vacaciones.jpg").write_bytes(datos)          # principal
        (raiz / "Fotos" / "vacaciones (1).jpg").write_bytes(datos)      # parece copia
        (raiz / "Fotos" / "Backup" / "vacaciones.jpg").write_bytes(datos)  # más anidada
        r = escanear(str(raiz))
        s = SeleccionDuplicados(r)
        s.preseleccionar_principales()
        check(s.todo_listo(), "tras preseleccionar, todos los grupos quedan OK")
        conservada = [a for a in r.grupos[0].archivos
                      if s.decision(0, a.ruta) == CONSERVAR][0]
        check(Path(conservada.ruta).name == "vacaciones.jpg"
              and "Backup" not in conservada.ruta,
              "conserva 'vacaciones.jpg' de la carpeta menos anidada, "
              "no la '(1)' ni la de Backup")
        check(s.cantidad_a_mover() == 2, "marca las otras 2 copias para mover")

    print()
    if fallos:
        print(f"FALLARON {len(fallos)} comprobaciones.")
        sys.exit(1)
    print("TODA LA SELECCION OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
