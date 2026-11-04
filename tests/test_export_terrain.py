"""game/export.py: a tile whose top blocks a player changed gets the terrain of the new top block (#5675)."""
import contextlib
import io
import json
import os
import shutil
import sys

import nbtlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import export  # noqa: E402
import world_reader  # noqa: E402
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario  # noqa: E402

import aoe2mc  # noqa: E402


def set_blocks(world, cells):
    """Set the block of each (x, y, z) in cells to its state name (a block of the palette of its section)."""
    w = world_reader.World(world)
    by = {}
    for (x, y, z), name in cells.items():
        by.setdefault((x >> 9, z >> 9), {}).setdefault((x >> 4 & 31, z >> 4 & 31), []).append((x, y, z, name))
    for (rx, rz), chunks in by.items():
        path = os.path.join(w.path, "region", f"r.{rx}.{rz}.mca")
        region = world_reader.read_region(path)
        for key, edits in chunks.items():
            c = region[key]
            for x, y, z, name in edits:
                sec = next(s for s in c["sections"] if int(s["Y"]) == y >> 4)
                names, idx = w.section_states(sec)
                if "minecraft:" + name not in names:
                    sec["block_states"]["palette"].append(nbtlib.Compound({"Name": nbtlib.String("minecraft:" + name)}))
                    names.append("minecraft:" + name)
                idx[(y & 15) * 256 + (z & 15) * 16 + (x & 15)] = names.index("minecraft:" + name)
                bits = max(4, (len(names) - 1).bit_length())
                per, longs = 64 // bits, []
                for i in range(0, 4096, per):
                    v = sum(k << (j * bits) for j, k in enumerate(idx[i:i + per]))
                    longs.append(v - (1 << 64) if v >= 1 << 63 else v)
                sec["block_states"]["data"] = nbtlib.LongArray(longs)
        out = {}
        for key, c in region.items():
            b = io.BytesIO()
            c.write(b)
            out[key] = b.getvalue()
        aoe2mc.write_region(path, out)


def surface(w, x, z):
    """y of the highest block that is not loose ground."""
    tops, of, loose = export.terrain_tops()
    for y in range(319, -64, -1):
        b = w.block(x, y, z)
        if b and not export.is_loose(export.base(b), loose):
            return y


def test_changed_tile_gets_the_terrain_of_its_new_top(tiny_world, tmp_path):
    world = str(tmp_path / "w")
    shutil.copytree(tiny_world[0], world)
    with open(os.path.join(world, "aoe2mc.json")) as f:
        data = json.load(f)
    T, n = data["tile_size"], data["map_size"]
    terrain = [[int(v) for v in r.split()] for r in data["terrain"]]
    tops, of, loose = export.terrain_tops()
    feet = {(x, y) for o in data["objects"] if "footprint" in o
            for x in range(o["footprint"][0] // T, -(-o["footprint"][2] // T))
            for y in range(o["footprint"][1] // T, -(-o["footprint"][3] // T))}
    w = world_reader.World(world)
    land = [(x, y) for y in range(n) for x in range(n) if (x, y) not in feet and of[terrain[y][x]] == "grass_block"]
    (tx, ty), (bx, by) = land[len(land) // 2], land[len(land) // 3]
    building = next(iter(feet))
    new = next(b for b in tops if b not in (of[terrain[ty][tx]], "farmland") and b != "grass_block")
    cells = {}
    for x, y, name in ((tx, ty, new), (bx, by, "oak_planks"), (*building, new)):
        for dx in range(T):
            for dz in range(T):
                X, Z = x * T + dx, y * T + dz
                cells[(X, surface(w, X, Z), Z)] = name
    set_blocks(world, cells)
    with contextlib.redirect_stdout(io.StringIO()):
        scn = AoE2DEScenario.from_file(export.export(world, str(tmp_path / "back.aoe2scenario")))
    got = {(t.x, t.y): t.terrain_id for t in scn.map_manager.terrain}
    assert got[(tx, ty)] == tops[new]
    assert all(v == terrain[y][x] for (x, y), v in got.items() if (x, y) != (tx, ty))
