"""The vertical section of tools/world_reader.py (#474)."""
import os
import subprocess
import sys

import world_reader


def test_section_matches_blocks(tiny_world):
    w = world_reader.World(tiny_world[0])
    x, z0, z1, y0, y1 = 40, 30, 50, 55, 75
    rows, legend = w.section("x", x, z0, z1, y0, y1)
    assert len(rows) == y1 - y0 + 1 and all(len(r) == z1 - z0 + 1 for r in rows)
    assert len(set(legend)) == len(legend) and " " not in legend and "." not in legend
    names = {v: k for k, v in legend.items()}
    for i, y in enumerate(range(y1, y0 - 1, -1)):
        for j, z in enumerate(range(z0, z1 + 1)):
            name = w.block(x, y, z).removeprefix("minecraft:").split("[")[0]
            assert rows[i][j] == (" " if name in world_reader.AIR else names[name])
    assert any(r.strip() for r in rows) and any(" " in r for r in rows)     # ground and air in the section


def test_section_along_x_and_outside(tiny_world):
    w = world_reader.World(tiny_world[0])
    rows, legend = w.section("z", 40, 30, 50, 63, 63)                   # z = 40: one row along x
    names = {v: k for k, v in legend.items()}
    assert rows[0] == "".join(names.get(w.block(x, 63, 40).removeprefix("minecraft:").split("[")[0], " ")
                              for x in range(30, 51))
    assert w.section("z", 10 ** 5, 0, 3, 60, 60)[0] == ["...."]          # no chunk there


def test_section_cli(tiny_world):
    tool = os.path.join(os.path.dirname(__file__), "..", "tools", "world_reader.py")
    out = subprocess.run([sys.executable, tool, tiny_world[0], "--section", "x", "40", "30", "35",
                          "60", "62"], capture_output=True, text=True, check=True).stdout
    lines = out.splitlines()
    assert lines[0].startswith("section x = 40") and lines[1].startswith("   62 |") and lines[3].startswith("   60 |")
