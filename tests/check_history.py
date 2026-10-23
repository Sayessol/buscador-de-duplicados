"""Tests of the operation history and of "undo" (core/history.py).

  * record and list (most recent first),
  * undo a MOVE -> the files go back to their place,
  * undo a COPY -> the copies in the destination are deleted,
  * conflicting undo (something already in the source) -> reports the failure,
  * an operation that was already undone is not undone twice.

It does not touch the real history: it redirects %APPDATA% to a temporary folder.

    python tests/check_history.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

failures = []


def check(cond, msg):
    print(f"  [{'OK  ' if cond else 'FAIL'}] {msg}")
    if not cond:
        failures.append(msg)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        import os
        os.environ["APPDATA"] = str(tmp / "appdata")

        # import AFTER setting APPDATA
        from core import history
        from core.file_moves import execute, Transfer, MOVE, COPY

        # --- set up a case: move 2 files to a destination ----------
        source = tmp / "source" / "sub"
        source.mkdir(parents=True)
        destination = tmp / "destination"
        (source / "a.txt").write_text("aaa")
        (source / "b.txt").write_text("bbb")

        plan = [Transfer(str(source / "a.txt"), str(destination / "sub" / "a.txt")),
                Transfer(str(source / "b.txt"), str(destination / "sub" / "b.txt"))]
        res = execute(plan, action=MOVE)
        op_id = history.record(
            history.KIND_GATHER, "move", str(tmp / "source"), str(destination),
            [(t.source, t.destination) for t in res.done], "2 test files")

        ops = history.list_all()
        check(len(ops) == 1 and ops[0]["id"] == op_id, "the operation is recorded")
        check(ops[0]["undone"] is False, "it starts as not undone")
        check(not (source / "a.txt").exists()
              and (destination / "sub" / "a.txt").exists(),
              "after the move: the files are in the destination")

        # --- undo the MOVE ------------------------------------
        r = history.undo(op_id)
        check(r["reverted"] == 2 and not r["failures"], "undo move: 2 reverted")
        check((source / "a.txt").exists() and (source / "b.txt").exists()
              and not (destination / "sub" / "a.txt").exists(),
              "the files are back in their original folder")
        check(history.list_all()[0]["undone"] is True,
              "the operation is marked as undone")

        r2 = history.undo(op_id)
        check(r2["reverted"] == 0 and r2["failures"], "it cannot be undone twice")

        # --- COPY and undo (deletes the copies) ----------------
        plan_c = [Transfer(str(source / "a.txt"), str(destination / "c" / "a.txt"))]
        rc = execute(plan_c, action=COPY)
        op_c = history.record(
            history.KIND_GATHER, "copy", str(tmp / "source"), str(destination),
            [(t.source, t.destination) for t in rc.done])
        check((destination / "c" / "a.txt").exists() and (source / "a.txt").exists(),
              "copy: original and copy both exist")
        rd = history.undo(op_c)
        check(rd["reverted"] == 1 and not (destination / "c" / "a.txt").exists()
              and (source / "a.txt").exists(),
              "undo copy: the copy is deleted, the original stays")

        # --- undo with a conflict -----------------------------
        (source / "x.txt").write_text("x")
        plan_x = [Transfer(str(source / "x.txt"), str(destination / "x.txt"))]
        rx = execute(plan_x, action=MOVE)
        op_x = history.record(
            history.KIND_GATHER, "move", str(tmp / "source"), str(destination),
            [(t.source, t.destination) for t in rx.done])
        (source / "x.txt").write_text("something else")  # we occupy the original path
        rr = history.undo(op_x)
        check(rr["reverted"] == 0 and rr["failures"],
              "undo with the original path taken -> reports a failure, does not overwrite")
        check((source / "x.txt").read_text() == "something else",
              "the file that occupied the original path was not touched")

    print()
    if failures:
        print(f"{len(failures)} CHECKS FAILED.")
        sys.exit(1)
    print("HISTORY OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
