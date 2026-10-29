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
# The rule set of the process (docs/research/antiquity.md, 2.3, #3666): "aoe2", or the name of a folder in DIR whose
# files replace the AoE2 file of the same name (the item lists) or add to it (the files of ADD: lookups by name).
RULES = os.environ.get("AOE2MC_RULES", "aoe2")
ADD = {
    "buildings.jsonl",
    "gather.jsonl",
    "monk.jsonl",
    "sounds.jsonl",
    "units.jsonl",
}
LOADED = []                                                        # the names of the files that load() read


def use(rules):
    """Make `rules` the rule set of the process. Stop when a file of a rule set folder is loaded already: a module
    keeps its rows. The shared files (setup.jsonl: the lobby) have no copy, so they can load before."""
    global RULES
    ruled = sorted({p for p in LOADED for r in (RULES, rules) if os.path.exists(os.path.join(DIR, r, p))})
    if rules != RULES and ruled:
        raise RuntimeError(f"rule set {rules}: the rule files {', '.join(ruled)} are loaded already")
    RULES = os.environ["AOE2MC_RULES"] = rules                         # a child process (the bots) uses the same set


def read(path):
    """The rows of one file, in file order. Two lines of one name stop."""
    rows = [json.loads(s) for s in open(path, encoding="utf-8") if s.strip()]
    names = [r["name"] for r in rows]
    twice = sorted({n for n in names if names.count(n) > 1})
    if twice:
        raise ValueError(f"{path}: more than one line for {', '.join(twice)}")
    return rows


def load(path, rules=None):
    """The rows of the file `path` (a name in `DIR`, or a path), in file order, of the rule set `rules` (default
    RULES): its file in DIR/rules replaces the file, or adds to it (ADD; a line of the same name replaces the line)."""
    rules = RULES if rules is None else rules
    own = os.path.join(DIR, rules, path)
    if os.path.dirname(path) or rules == "aoe2" or not os.path.exists(own):
        rows = read(os.path.join(DIR, path))
    elif path in ADD:
        extra = read(own)
        names = {r["name"] for r in extra}
        rows = [r for r in read(os.path.join(DIR, path)) if r["name"] not in names] + extra
    else:
        rows = read(own)
    LOADED.append(path)
    return rows
