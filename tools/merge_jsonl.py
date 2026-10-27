#!/usr/bin/env python3
"""Git merge driver for the data tables `game/data/*.jsonl`: merge the lines by their key "name" (#2004).

`merge=union` keeps the old and the new version of a line that one side changed, and `table.load()` then stops
("more than one line for X", #1890, #1934). This driver takes, for each name, the side that changed it. A name
that both sides changed to different lines is a conflict: the file gets conflict markers and the exit code is 1.

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
