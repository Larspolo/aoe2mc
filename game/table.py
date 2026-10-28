"""
Data files of the game program: one JSON object per line (#1702, #1912). A new entry is one new line, so parallel
tickets do not conflict (`merge=union` in .gitattributes). Two lines of one name (both sides of a merge changed it)
stop the import.
"""
import json
import os
import sys

FROZEN = "game_data"   # the folder in an app bundle: the converter data of units.py is in "data" there, with files of
# the same names (train.jsonl, units.jsonl), and the modules of game/ are next to it (packaging/aoe2mc.spec, #2839)


def folder(frozen=None):
    """The folder of the data files: game/data in a source checkout, FROZEN next to the modules in an app bundle."""
    frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), FROZEN if frozen else "data")


DIR = folder()


def load(path):
    """The rows of the file `path` (a name in `DIR`, or a path), in file order."""
    path = os.path.join(DIR, path)
    rows = [json.loads(s) for s in open(path, encoding="utf-8") if s.strip()]
    names = [r["name"] for r in rows]
    twice = sorted({n for n in names if names.count(n) > 1})
    if twice:
        raise ValueError(f"{path}: more than one line for {', '.join(twice)}")
    return rows
