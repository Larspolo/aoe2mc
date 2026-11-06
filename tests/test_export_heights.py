"""game/export.py: with heights=True a raised or dug tile gets its new AoE2 elevation (#6000)."""
import contextlib
import io
import json
import os
import shutil
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import export  # noqa: E402
import world_reader  # noqa: E402
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario  # noqa: E402
from test_export_terrain import set_blocks, surface  # noqa: E402


def raised_world(tiny_world, tmp_path):
    """A copy of tiny_world with 3 stone blocks on 3 of 4 rows of the columns of a free tile. Returns (world, data,
    (x, y) of the tile in the turned grid)."""
    world = str(tmp_path / "w")
    shutil.copytree(tiny_world[0], world)
    with open(os.path.join(world, "aoe2mc.json")) as f:
        data = json.load(f)
    T, n = data["tile_size"], data["map_size"]
    elev = np.array([[int(v) for v in r.split()] for r in data["elevation"]])
    skip = export.covered(data)
    tx, ty = next((x, y) for y in range(1, n) for x in range(1, n) if (x, y) not in skip and elev[y, x] == 0
                  and data["terrain"][y].split()[x] == data["terrain"][0].split()[0])
    w, cells = world_reader.World(world), {}
    for dx in range(T):
        for dz in range(T - 1):                                     # most columns, not all
            X, Z = tx * T + dx, ty * T + dz
            s = surface(w, X, Z)
            cells.update({(X, s + k, Z): "stone" for k in (1, 2, 3)})
    set_blocks(world, cells)
    return world, data, (tx, ty)


def elevations(world, tmp_path, heights):
    with contextlib.redirect_stdout(io.StringIO()):
        scn = AoE2DEScenario.from_file(export.export(world, str(tmp_path / f"{heights}.aoe2scenario"), heights=heights))
    return {(t.x, t.y): t.elevation for t in scn.map_manager.terrain}


def turned(data, grid):
    """{(x, y): level} of a [y][x] grid of the turned world, in the orientation of the scenario (as export)."""
    a = np.rot90(np.array(grid).T, (4 - data.get("turn", 0)) % 4)
    return {(x, y): int(a[x, y]) for x in range(a.shape[0]) for y in range(a.shape[1])}


def test_raised_tile_gets_one_level_more_only_with_heights(tiny_world, tmp_path):
    world, data, (tx, ty) = raised_world(tiny_world, tmp_path)
    old = np.array([[int(v) for v in r.split()] for r in data["elevation"]])
    new = old.copy()
    new[ty, tx] += 1
    assert elevations(world, tmp_path, True) == turned(data, new)
    assert elevations(world, tmp_path, False) == turned(data, old)


def test_unchanged_world_keeps_its_elevation(tiny_world, tmp_path):
    with open(os.path.join(tiny_world[0], "aoe2mc.json")) as f:
        data = json.load(f)
    old = [[int(v) for v in r.split()] for r in data["elevation"]]
    assert elevations(tiny_world[0], tmp_path, True) == turned(data, old)
