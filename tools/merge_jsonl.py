#!/usr/bin/env python3
"""Git merge driver for the data tables `game/data/*.jsonl`: merge the lines by their key "name" (#2004).

`merge=union` keeps the old and the new version of a line that one side changed, and `table.load()` then stops
("more than one line for X", #1890, #1934). This driver takes, for each name, the side that changed it. A name
that both sides changed to different lines gets a merge of its keys: a list takes the items that each side added
and removed (the "missing" list of each civilization line in `civs.jsonl`: two new unique units change all lines,
owner request 2026-10-27), another key takes the side that changed it. A key that both sides changed in another way is
a conflict: the file gets conflict markers and the exit code is 1.

    python3 tools/merge_jsonl.py BASE OURS THEIRS     # git: merge.jsonl.driver "python3 tools/merge_jsonl.py %O %A %B"

The result goes into OURS. A line without a JSON object with "name" is keyed by its text (a union without copies).
A file that does not parse falls back to the text merge of `git merge-file`.
"""
import json
import subprocess
import sys


def rows(path):
    """{key: line} of the file `path`, in file order."""
    with open(path, encoding="utf-8") as f:
        return rows_of(f)


def rows_of(lines):
    """{key: line} of the text lines `lines`, in their order."""
    out = {}
    for s in lines:
        if not s.strip():
            continue
        s = s.rstrip("\n") + "\n"
        o = json.loads(s)
        out[o["name"] if isinstance(o, dict) and "name" in o else s] = s
    return out


def merge_list(o, a, b):
    """The list `a` with the items that `b` added to `o` and without the items that `b` removed, or None when an item
    is not hashable. Sorted when all three lists are sorted (the "missing" lists are)."""
    try:
        add, gone = [x for x in b if x not in set(o)], set(o) - set(b)
    except TypeError:
        return None
    out = [x for x in a if x not in gone] + [x for x in add if x not in set(a)]
    return sorted(out) if all(v == sorted(v) for v in (o, a, b)) else out


def merge_line(o, a, b):
    """The 3-way merge of one line that both sides changed, or None (a conflict)."""
    try:
        o, a, b = json.loads(o), json.loads(a), json.loads(b)
    except (TypeError, ValueError):
        return None
    if not all(isinstance(v, dict) for v in (o, a, b)):
        return None
    out = {}
    for k in list(a) + [k for k in b if k not in a]:
        x, y, z = o.get(k), a.get(k), b.get(k)
        if y == z or z == x:
            v = y
        elif y == x:
            v = z
        elif all(isinstance(v, list) for v in (x, y, z)) and (v := merge_list(x, y, z)) is not None:
            pass
        else:
            return None
        if v is not None or (k in a and k in b):
            out[k] = v
    return json.dumps(out, ensure_ascii=False) + "\n"


def merge(base, ours, theirs):
    """(lines, conflicts): the merged lines in the order of `ours`, the new lines of `theirs` after their
    neighbour above in `theirs` and after the new lines of `ours` there (as `merge=union`)."""
    order = list(ours)
    for i, k in enumerate(theirs):                       # place the new names of theirs
        if k in ours:
            continue
        above = [j for j in list(theirs)[:i] if j in order]
        at = order.index(above[-1]) + 1 if above else 0
        while at < len(order) and order[at] not in theirs:
            at += 1
        order.insert(at, k)
    lines, conflicts = [], 0
    for k in order:
        o, a, b = base.get(k), ours.get(k), theirs.get(k)
        if a == b or b == o:
            pick = a
        elif a == o:
            pick = b                                     # changed (or deleted) only on their side
        elif (pick := merge_line(o, a, b)) is not None:
            pass
        else:
            conflicts += 1
            lines += ["<<<<<<< ours\n", a or "", "=======\n", b or "", ">>>>>>> theirs\n"]
            continue
        if pick is not None:
            lines.append(pick)
    return lines, conflicts


def main(argv):
    base, ours, theirs = argv[1:4]
    try:
        lines, conflicts = merge(rows(base), rows(ours), rows(theirs))
    except (ValueError, KeyError, TypeError):            # not one JSON object per line: the plain text merge
        r = subprocess.run(["git", "merge-file", "-L", "ours", "-L", "base", "-L", "theirs", ours, base, theirs])
        return 1 if r.returncode else 0
    with open(ours, "w", encoding="utf-8") as f:
        f.writelines(lines)
    if conflicts:
        print(f"{ours}: {conflicts} name(s) changed on both sides", file=sys.stderr)
    return 1 if conflicts else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
