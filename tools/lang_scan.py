#!/usr/bin/env python3
"""List the plain texts of the game program (#5379): the functions of game/*.py that send a "text" component that is
not a lang.text (epic #5343). A dict with the key "text" (not "") or a JSON text '"text":"..."' in a string or f-string
is a plain text. game/data/lang_plain.jsonl has the exceptions (names, record texts, owner tools); tests/test_lang_scan.py
fails on a function that is in neither.

Usage: python3 tools/lang_scan.py [--all]   (default: only the functions that are not in lang_plain.jsonl)
Exit 0: none, 1: plain texts found.
"""
import ast
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = re.compile(r'"text"\s*:\s*"[^"]')                 # JSON in a string; a value of an f-string counts as "x"


def allowed():
    """The names of game/data/lang_plain.jsonl."""
    with open(os.path.join(ROOT, "game", "data", "lang_plain.jsonl"), encoding="utf-8") as f:
        return {json.loads(s)["name"] for s in f if s.strip()}


def plain(node):
    """True when node sends a plain text: a dict with a "text" that is not "", or a JSON text in a string."""
    if isinstance(node, ast.Dict):
        return any(isinstance(k, ast.Constant) and k.value == "text" and not (isinstance(v, ast.Constant) and v.value == "")
                   for k, v in zip(node.keys, node.values))
    if isinstance(node, ast.JoinedStr):
        return bool(RAW.search("".join(v.value if isinstance(v, ast.Constant) else "x" for v in node.values)))
    return isinstance(node, ast.Constant) and isinstance(node.value, str) and bool(RAW.search(node.value))


def scan(source, module):
    """The functions (module.Class.function) of source with a plain text."""
    found = set()

    def walk(node, where):
        for c in ast.iter_child_nodes(node):
            w = f"{where}.{c.name}" if isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) else where
            if plain(c):
                found.add(w)
            walk(c, w)
    walk(ast.parse(source), module)
    return found


def found():
    out = set()
    for f in sorted(glob.glob(os.path.join(ROOT, "game", "*.py"))):
        module = os.path.basename(f)[:-3]
        if module != "lang":
            out |= scan(open(f, encoding="utf-8").read(), module)
    return out




def main(argv=None):
    every = "--all" in (sys.argv[1:] if argv is None else argv)
    names = sorted(found() if every else found() - allowed())
    for n in names:
        print(n)
    return 1 if names else 0


if __name__ == "__main__":
    sys.exit(main())
