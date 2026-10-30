#!/usr/bin/env python3
"""
Writes the column "Used today in" of the feature table in docs/DESIGN.md (section 2) from the designs (#234).

Usage:
    python3 tools/feature_table.py [DESIGN.md]      # default: docs/DESIGN.md

The column "Minecraft block" is the pattern of a row: each name in backticks is a block name (`*` is a wildcard,
`[...]` is ignored). "`brick` stairs" also matches `brick_stairs`. Names that are not blocks (`Canvas.flag`) match
nothing. The tool draws each design in all architecture sets and lists the design functions that place blocks of the
row. A design that uses fewer than half of the names that the best design uses is not listed (the cobblestone of
each foundation is not a "mined stone"). Design PRs add rows, but do not edit the column: the workflow
`coverage.yml` writes it on main.
"""
import os
import re
import sys
from collections import Counter, defaultdict
from fnmatch import fnmatchcase

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import buildings  # noqa: E402

HEADER = "| AoE2 feature | Minecraft block | Used today in |"
SHOW = 4                # names in the column; more functions give "+N more"


def designer(frame):
    """Name of the innermost module-level function of buildings.py in the call stack (not a Canvas method)."""
    while frame:
        code = frame.f_code
        f = vars(buildings).get(code.co_name)
        if getattr(f, "__code__", None) is code and code.co_name != "place_building":
            return code.co_name
        frame = frame.f_back
    return None


def usage(only=None):
    """{function name: Counter(block name: blocks written)} of all designs (or the names in `only`) in all architecture
    sets. The blocks
    count for the innermost function of buildings.py that draws them: `granary` (not `mill`), `decorate`, `log_pile`."""
    import render
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo
    from AoE2ScenarioParser.datasets.other import OtherInfo

    import aoe2mc
    names = {}
    for e in [*BuildingInfo, *(e for e in OtherInfo if e.name.startswith(aoe2mc.MONUMENTS))]:
        if e.name != "RUINS" and (only is None or e.name in only):
            fn, kw = buildings.select(e.name)
            names.setdefault((fn.__name__, tuple(sorted(kw.items()))), e.name)
    out = defaultdict(Counter)
    canvas = buildings.Canvas
    box, fill = canvas.box, canvas._fill_mask

    def record(self, b, n):
        i = self.id(b)
        if i >= 0 and n > 0:
            out[designer(sys._getframe(2))][aoe2mc.B.states[i].split(":")[-1].split("[")[0]] += n

    def counted_box(self, x0, x1, y0, y1, z0, z1, b):
        record(self, b, max(0, x1 - x0) * max(0, y1 - y0) * max(0, z1 - z0))
        box(self, x0, x1, y0, y1, z0, z1, b)

    def counted_fill(self, mask, y0, y1, b):
        record(self, b, int(mask.sum()) * max(0, y1 - y0))
        fill(self, mask, y0, y1, b)
    canvas.box, canvas._fill_mask = counted_box, counted_fill
    try:
        for _, name in sorted(names.items()):
            for arch in sorted(buildings.ARCH):
                render.building_blocks(name, arch)
    finally:
        canvas.box, canvas._fill_mask = box, fill
    out.pop(None, None)
    return out


def patterns(cell):
    """Block name patterns of a "Minecraft block" cell: [[pattern, ...] per name in backticks]."""
    out = []
    for name, stairs in re.findall(r"`([^`]+)`(\s+stairs)?", cell):
        name = name.split("[")[0]
        if re.fullmatch(r"[a-z_*]+", name):
            out.append([name, name + "_stairs"] if stairs else [name])
    return out


def column(cell, use):
    """The text of "Used today in" for a row with the "Minecraft block" cell, from usage()."""
    pats = patterns(cell)
    found = {}
    for fn, blocks in use.items():
        hits = [sum(n for b, n in blocks.items() if any(fnmatchcase(b, p) for p in alt)) for alt in pats]
        if any(hits):
            found[fn] = (sum(h > 0 for h in hits), sum(hits) / sum(blocks.values()))
    if not found:
        return "no design"
    best = max(k for k, _ in found.values())
    keep = sorted((f for f, (k, _) in found.items() if 2 * k >= best), key=lambda f: (-found[f][0], -found[f][1], f))
    text = ", ".join(f"`{f}`" for f in keep[:SHOW])
    return text + (f" +{len(keep) - SHOW} more" if len(keep) > SHOW else "")


def rewrite(text, use):
    """docs/DESIGN.md text with a new "Used today in" column in the feature table."""
    lines = text.split("\n")
    i = lines.index(HEADER) + 2
    while i < len(lines) and lines[i].startswith("|"):
        cells = [c.strip() for c in lines[i].strip()[1:-1].split("|")]      # a new row can leave the column out
        if len(cells) >= 2:
            lines[i] = f"| {cells[0]} | {cells[1]} | {column(cells[1], use)} |"
        i += 1
    return "\n".join(lines)


def main(argv):
    path = argv[1] if len(argv) > 1 else os.path.join(ROOT, "docs", "DESIGN.md")
    with open(path) as f:
        text = f.read()
    new = rewrite(text, usage())
    with open(path, "w") as f:
        f.write(new)
    print(f"wrote {path}" + ("" if new != text else " (no change)"))


if __name__ == "__main__":
    main(sys.argv)
