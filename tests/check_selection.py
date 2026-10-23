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
    print(f"  [{'OK  ' if cond else 'FAIL'}] {msg}")
    if not cond:
        failures.append(msg)


def test_result():
    g1 = DuplicateGroup(hash="h1", size=100, files=[
        DuplicateFile(r"D:\Photos\Organized\trip\a.jpg", 100),
        DuplicateFile(r"D:\Downloads\a.jpg", 100),
        DuplicateFile(r"E:\Backup\a.jpg", 100),
    ])
    g2 = DuplicateGroup(hash="h2", size=50, files=[
        DuplicateFile(r"D:\Downloads\b.txt", 50),
        DuplicateFile(r"D:\Desktop\b.txt", 50),
    ])
    g3 = DuplicateGroup(hash="h3", size=200, files=[
        DuplicateFile(r"D:\Photos\Organized\c.png", 200),
        DuplicateFile(r"D:\Photos\Organized\copy\c.png", 200),
    ])
    return ScanResult(groups=[g1, g2, g3], total_files=7)


def main():
    r = test_result()
    sel = DuplicateSelection(r)

    print("\n--- Initial state ---")
    check(all(sel.decision(gi, a.path) == KEEP
              for gi, g in enumerate(r.groups) for a in g.files),
          "everything starts as KEEP")
    check(sel.group_state(0) == GROUP_MULTIPLE, "group with 3 kept -> MULTIPLE")
    check(not sel.all_ready(), "nothing ready at the start")
    check(sel.count_to_move() == 0, "nothing would be moved at the start")

    print("\n--- Preferred folder rule: D:\\Photos\\Organized ---")
    resolved, no_match = sel.apply_folder_rule(r"D:\Photos\Organized")
    print(f"    resolved={resolved}  no_match={no_match}")
    check(resolved == 2, "g1 and g3 have a copy in the preferred folder")
    check(no_match == 1, "g2 has no copy in the preferred folder")

    # g1: keeps the one in Organizado, moves the other two
    check(sel.decision(0, r"D:\Photos\Organized\trip\a.jpg") == KEEP,
          "g1 keeps the copy inside the preferred folder")
    check(sel.decision(0, r"D:\Downloads\a.jpg") == MOVE, "g1 moves the one from Downloads")
    check(sel.group_state(0) == GROUP_OK, "g1 ends up OK")

    # g3: two copies inside the preferred folder -> keeps the one with the shortest path
    check(sel.decision(2, r"D:\Photos\Organized\c.png") == KEEP,
          "g3 keeps the shortest-path copy inside the folder")
    check(sel.decision(2, r"D:\Photos\Organized\copy\c.png") == MOVE,
          "g3 moves the nested copy")
    check(sel.group_state(2) == GROUP_OK, "g3 ends up OK")

    # g2: no match -> everything stays on KEEP -> pending
    check(sel.group_state(1) == GROUP_MULTIPLE, "g2 is still pending")
    check(sel.pending_groups() == [1], "only g2 is left pending")
    check(not sel.all_ready(), "not everything is ready yet (g2 missing)")

    print("\n--- Manual adjustment of g2 ---")
    sel.keep_only(1, r"D:\Desktop\b.txt")
    check(sel.group_state(1) == GROUP_OK, "g2 resolved by hand")
    check(sel.all_ready(), "now everything is ready")

    print("\n--- Summary of moves ---")
    check(sel.count_to_move() == 4, "4 files would be moved (2 from g1, 1 from g2, 1 from g3)")
    check(sel.space_to_free() == 100 + 100 + 50 + 200, "the space to free is correct")

    print("\n--- toggle() ---")
    sel.mark(1, r"D:\Downloads\b.txt", KEEP)  # now g2 has 2 kept
    check(sel.group_state(1) == GROUP_MULTIPLE, "marking two as kept breaks g2")
    new = sel.toggle(1, r"D:\Downloads\b.txt")
    check(new == MOVE and sel.group_state(1) == GROUP_OK, "toggling fixes it again")

    print("\n--- preferred folder empty or non-existent ---")
    sel2 = DuplicateSelection(test_result())
    res, sync = sel2.apply_folder_rule("")
    check(res == 0 and sync == 3, "empty folder: no group is resolved")

    print("\n--- preselect_primary() (Simple view) ---")
    import tempfile
    from core.scanner import scan
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        data = b"content identico\n" * 40
        (root / "Photos").mkdir()
        (root / "Photos" / "Backup").mkdir()
        (root / "Photos" / "holidays.jpg").write_bytes(data)          # primary
        (root / "Photos" / "holidays (1).jpg").write_bytes(data)      # looks like a copy
        (root / "Photos" / "Backup" / "holidays.jpg").write_bytes(data)  # more nested
        r = scan(str(root))
        s = DuplicateSelection(r)
        s.preselect_primary()
        check(s.all_ready(), "after preselecting, every group is OK")
        kept = [a for a in r.groups[0].files
                      if s.decision(0, a.path) == KEEP][0]
        check(Path(kept.path).name == "holidays.jpg"
              and "Backup" not in kept.path,
              "keeps 'holidays.jpg' from the least nested folder, "
              "not the '(1)' one nor the Backup one")
        check(s.count_to_move() == 2, "marks the other 2 copies to move")

    print()
    if failures:
        print(f"{len(failures)} CHECKS FAILED.")
        sys.exit(1)
    print("THE WHOLE SELECTION OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
