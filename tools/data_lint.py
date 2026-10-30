"""Game data in the code (#1909): the literals of the product code that name two or more AoE2 things.

Game data (the units, buildings, technologies, objects, terrains and civilizations of AoE2, and their values) goes in
a data file (`game/data/*.jsonl`, `data/*.jsonl`, one JSON object per line, `merge=union`), not in the code. A
literal (tuple, list, set or dict) with two or more AoE2 names is game data, whatever its size: a set of 3 unit names
in a function is data too. `tests/test_game_names_in_code.py` fails on such a literal when the list
`tests/data/game_names_in_code.txt` does not have it, and on a line of the list with more literals than the code.
So the list only gets shorter: the epic #1909 moves its places to data files until it is empty.

    python3 tools/data_lint.py            # each place: the line and the first names of each literal
    python3 tools/data_lint.py --shrink   # lower the counts of the list to the code (it never adds or raises one)
"""
import argparse
import ast
import contextlib
import glob
import io
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "framework", "tools"))
from agent_config import CONFIG  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIST = os.path.join(ROOT, CONFIG["lint"]["data"])     # tests/data/game_names_in_code.txt
FILES = ("*.py", "game/*.py")             # the product code: the tests and tools may name AoE2 things
HEAD = """\
# Game data in the code (#1909, tools/data_lint.py): a place (file:scope) and its count of literals with two or more
# AoE2 names. Only delete lines or lower counts here (python3 tools/data_lint.py --shrink): new game data goes in a
# data file (game/data/*.jsonl, data/*.jsonl). tests/test_game_names_in_code.py checks this list against the code.
"""


def names():
    """The AoE2 names: the enums of AoE2ScenarioParser and the civilizations of `game/data/civs.jsonl`."""
    with contextlib.redirect_stdout(io.StringIO()):                     # the parser prints much text
        from AoE2ScenarioParser.datasets.buildings import BuildingInfo
        from AoE2ScenarioParser.datasets.heroes import HeroInfo
        from AoE2ScenarioParser.datasets.other import OtherInfo
        from AoE2ScenarioParser.datasets.techs import TechInfo
        from AoE2ScenarioParser.datasets.terrains import TerrainId
        from AoE2ScenarioParser.datasets.units import UnitInfo
    out = {m.name for e in (BuildingInfo, HeroInfo, OtherInfo, TechInfo, TerrainId, UnitInfo) for m in e}
    with open(os.path.join(ROOT, "game", "data", "civs.jsonl"), encoding="utf-8") as f:
        return out | {json.loads(s)["name"] for s in f if s.strip()}


def literals(tree, known):
    """{scope: [(line, names)]} of one module: the outermost literals with two or more names of `known`. The scope
    is the name of a module-level assignment, or the dotted name of the function or class around the literal."""
    out = {}

    def visit(node, scope):
        if isinstance(node, (ast.Tuple, ast.List, ast.Set, ast.Dict)):
            found = sorted({x.value for x in ast.walk(node) if isinstance(x, ast.Constant) and x.value in known})
            if len(found) >= 2:
                out.setdefault(scope, []).append((node.lineno, found))
                return                                # one count for a table, not one for each row
        for child in ast.iter_child_nodes(node):
            inner = isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            visit(child, f"{scope}.{child.name}" if inner else scope)

    for stmt in tree.body:
        target = stmt.targets[0] if isinstance(stmt, ast.Assign) else \
            stmt.target if isinstance(stmt, (ast.AnnAssign, ast.AugAssign)) else None
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            visit(stmt, stmt.name)
        else:
            visit(stmt, target.id if isinstance(target, ast.Name) else "<module>")
    return out


def scan(root=ROOT, known=None):
    """{"file:scope": [(line, names)]} of the product code."""
    known = names() if known is None else known
    out = {}
    for pattern in FILES:
        for path in sorted(glob.glob(os.path.join(root, pattern))):
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            with open(path, encoding="utf-8") as f:
                out.update({f"{rel}:{s}": v for s, v in literals(ast.parse(f.read()), known).items()})
    return out


def read(path=LIST):
    """The (place, count) pairs of the list, in file order (`framework/tools/health.py` reads it the same way)."""
    with open(path, encoding="utf-8") as f:
        return [(p, int(n)) for p, n in (s.split() for s in f if s.strip() and not s.startswith("#"))]


def problems(found, rows):
    """The errors of the list `rows` against the counts `found` ({place: count}): two lines of one place (a union
    merge kept both sides), a place with more literals than the list, a line with more literals than the code."""
    listed, places = dict(rows), [p for p, _ in rows]
    out = [f"{p}: two lines in the list (a merge kept both sides): keep one, then --shrink"
           for p in sorted({p for p in places if places.count(p) > 1})]
    out += [f"{p}: {n} literal(s) with AoE2 names, the list allows {listed.get(p, 0)}: put the names in a data file "
            "(game/data/*.jsonl, data/*.jsonl), not in the code" for p, n in sorted(found.items()) if n > listed.get(p, 0)]
    out += [f"{p}: the list says {n}, the code has {found.get(p, 0)}: run python3 tools/data_lint.py --shrink"
            for p, n in rows if n > found.get(p, 0)]
    return out


def shrink(found, rows):
    """The lines of the list with each count lowered to the code: a place leaves when the code has none. It never adds
    a place or raises a count."""
    low = {}
    for p, n in rows:
        low[p] = min(n, low.get(p, n), found.get(p, 0))
    return [f"{p} {n}" for p, n in sorted(low.items()) if n > 0]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--shrink", action="store_true", help="lower the counts of the list to the code")
    a = ap.parse_args(argv)
    found = scan()
    counts = {p: len(v) for p, v in found.items()}
    if a.shrink:
        rows = read(LIST)                           # before the open: mode "w" empties the file (#3066)
        with open(LIST, "w", encoding="utf-8") as f:
            f.write(HEAD + "".join(line + "\n" for line in shrink(counts, rows)))
    for p, v in sorted(found.items()):
        for line, ns in v:
            print(f"{p.split(':')[0]}:{line} {p.split(':')[1]}: {', '.join(ns[:4])}{' ...' if len(ns) > 4 else ''}")
    errors = problems(counts, read(LIST))
    print(f"{sum(counts.values())} literals with AoE2 names in {len(counts)} places", file=sys.stderr)
    print("\n".join(errors), file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
