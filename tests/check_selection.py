"""Tests of DuplicateSelection: preferred-folder rule, manual
adjustment and validation of "a single copy per group".

    python tests/check_selection.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.scanner import DuplicateFile, DuplicateGroup, ScanResult  # noqa: E402
from core.selection import (  # noqa: E402
    DuplicateSelection, KEEP, MOVE,
    GROUP_OK, GROUP_MULTIPLE,
)

failures = []


def check(cond, msg):
    print(f"  [{'OK  ' if cond else 'FALLA'}] {msg}")
    if not cond:
        failures.append(msg)


def test_result():
    g1 = DuplicateGroup(hash="h1", size=100, files=[
        DuplicateFile(r"D:\Fotos\Organizado\viaje\a.jpg", 100),
        DuplicateFile(r"D:\Descargas\a.jpg", 100),
        DuplicateFile(r"E:\Respaldo\a.jpg", 100),
    ])
    g2 = DuplicateGroup(hash="h2", size=50, files=[
        DuplicateFile(r"D:\Descargas\b.txt", 50),
        DuplicateFile(r"D:\Escritorio\b.txt", 50),
    ])
    g3 = DuplicateGroup(hash="h3", size=200, files=[
        DuplicateFile(r"D:\Fotos\Organizado\c.png", 200),
        DuplicateFile(r"D:\Fotos\Organizado\copia\c.png", 200),
    ])
    return ScanResult(groups=[g1, g2, g3], total_files=7)


def main():
    r = test_result()
    sel = DuplicateSelection(r)

    print("\n--- Estado inicial ---")
    check(all(sel.decision(gi, a.path) == KEEP
              for gi, g in enumerate(r.groups) for a in g.files),
          "todo arranca en CONSERVAR")
    check(sel.group_state(0) == GROUP_MULTIPLE, "grupo con 3 conservadas -> MULTIPLE")
    check(not sel.all_ready(), "nada listo al inicio")
    check(sel.count_to_move() == 0, "no se movería nada al inicio")

    print("\n--- Regla de carpeta preferida: D:\\Fotos\\Organizado ---")
    resolved, no_match = sel.apply_folder_rule(r"D:\Fotos\Organizado")
    print(f"    resueltos={resolved}  sin_coincidencia={no_match}")
    check(resolved == 2, "g1 y g3 tienen copia en la carpeta preferida")
    check(no_match == 1, "g2 no tiene copia en la carpeta preferida")

    # g1: keeps the one in Organizado, moves the other two
    check(sel.decision(0, r"D:\Fotos\Organizado\viaje\a.jpg") == KEEP,
          "g1 conserva la copia dentro de la carpeta preferida")
    check(sel.decision(0, r"D:\Descargas\a.jpg") == MOVE, "g1 mueve la de Descargas")
    check(sel.group_state(0) == GROUP_OK, "g1 queda OK")

    # g3: two copies inside the preferred folder -> keeps the one with the shortest path
    check(sel.decision(2, r"D:\Fotos\Organizado\c.png") == KEEP,
          "g3 conserva la copia de ruta más corta dentro de la carpeta")
    check(sel.decision(2, r"D:\Fotos\Organizado\copia\c.png") == MOVE,
          "g3 mueve la copia anidada")
    check(sel.group_state(2) == GROUP_OK, "g3 queda OK")

    # g2: no match -> everything stays on KEEP -> pending
    check(sel.group_state(1) == GROUP_MULTIPLE, "g2 sigue pendiente")
    check(sel.pending_groups() == [1], "solo g2 queda pendiente")
    check(not sel.all_ready(), "todavía no está todo listo (falta g2)")

    print("\n--- Ajuste manual de g2 ---")
    sel.keep_only(1, r"D:\Escritorio\b.txt")
    check(sel.group_state(1) == GROUP_OK, "g2 resuelto a mano")
    check(sel.all_ready(), "ahora sí, todo listo")

    print("\n--- Resumen de movimientos ---")
    check(sel.count_to_move() == 4, "se moverían 4 archivos (2 de g1, 1 de g2, 1 de g3)")
    check(sel.space_to_free() == 100 + 100 + 50 + 200, "espacio a liberar correcto")

    print("\n--- alternar() ---")
    sel.mark(1, r"D:\Descargas\b.txt", KEEP)  # now g2 has 2 kept
    check(sel.group_state(1) == GROUP_MULTIPLE, "marcar dos conservadas rompe g2")
    new = sel.toggle(1, r"D:\Descargas\b.txt")
    check(new == MOVE and sel.group_state(1) == GROUP_OK, "alternar lo vuelve a arreglar")

    print("\n--- carpeta preferida vacía o inexistente ---")
    sel2 = DuplicateSelection(test_result())
    res, sync = sel2.apply_folder_rule("")
    check(res == 0 and sync == 3, "carpeta vacía: ningún grupo se resuelve")

    print("\n--- preselect_primary() (modo Sencilla) ---")
    import tempfile
    from core.scanner import scan
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        data = b"contenido identico\n" * 40
        (root / "Fotos").mkdir()
        (root / "Fotos" / "Backup").mkdir()
        (root / "Fotos" / "vacaciones.jpg").write_bytes(data)          # primary
        (root / "Fotos" / "vacaciones (1).jpg").write_bytes(data)      # looks like a copy
        (root / "Fotos" / "Backup" / "vacaciones.jpg").write_bytes(data)  # more nested
        r = scan(str(root))
        s = DuplicateSelection(r)
        s.preselect_primary()
        check(s.all_ready(), "tras preseleccionar, todos los grupos quedan OK")
        kept = [a for a in r.groups[0].files
                      if s.decision(0, a.path) == KEEP][0]
        check(Path(kept.path).name == "vacaciones.jpg"
              and "Backup" not in kept.path,
              "conserva 'vacaciones.jpg' de la carpeta menos anidada, "
              "no la '(1)' ni la de Backup")
        check(s.count_to_move() == 2, "marca las otras 2 copias para mover")

    print()
    if failures:
        print(f"FALLARON {len(failures)} comprobaciones.")
        sys.exit(1)
    print("TODA LA SELECCION OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
