"""
Data files of the game program: one JSON object per line (#1702, #1912). A new entry is one new line, so parallel
tickets do not conflict (`merge=union` in .gitattributes). Two lines of one name (both sides of a merge changed it)
stop the import.
"""
import json
import os

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def load(path):
    """The rows of the file `path` (a name in `DIR`, or a path), in file order."""
    path = os.path.join(DIR, path)
    rows = [json.loads(s) for s in open(path, encoding="utf-8") if s.strip()]
    names = [r["name"] for r in rows]
    twice = sorted({n for n in names if names.count(n) > 1})
    if twice:
        raise ValueError(f"{path}: more than one line for {', '.join(twice)}")
    return rows
