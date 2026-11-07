"""Export a played Minecraft world back to an .aoe2scenario (epic #4198, first part).

Usage:
    python3 game/export.py WORLD OUT.aoe2scenario    # WORLD: a converted world, or a save folder of game/run.py

The start map comes from aoe2mc.json of the world: the size, the terrain and elevation of each tile, the players and
their civilizations, and the objects. A save folder (savegame.py: `world/` and `savegame.json`) gives the state at the
end of the game: the units that still live (the "soldiers" and "villagers" of each player), the buildings of the
construction sites that are done, the fallen start buildings ("ruins") and the mines with no resource left. The
entities of the world give the last position of each unit (its UUID). The tiles and the terrain turn back to the
orientation of the source scenario (the turn of --orientation, #5674). The resources and the starting age of each
player: the end of the game with a save, else those of aoe2mc.json. A tile whose ground a player changed (most of
its T x T block columns have a new top block) gets the AoE2 terrain of the new top block (`ground()`); the
elevation stays the one of aoe2mc.json (a dug hole does not change the AoE2 elevation).
"""
import argparse
import contextlib
import io
import json
import math
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402
import savegame  # noqa: E402
import scenarios  # noqa: E402
from AoE2ScenarioParser.datasets.object_support import Civilization, StartingAge  # noqa: E402

import aoe2mc  # noqa: E402
import units as unitlib  # noqa: E402

RESOURCES = ("food", "wood", "gold", "stone")
AGES = (StartingAge.DARK_AGE, StartingAge.FEUDAL_AGE, StartingAge.CASTLE_AGE, StartingAge.IMPERIAL_AGE)


def folders(path):
    """(world folder, saved state or None) of a world or of a save folder."""
    if os.path.exists(os.path.join(path, savegame.FILE)):
        return os.path.join(path, "world"), savegame.read(path)
    return path, None


def positions(world):
    """UUID -> (x, z) in blocks of each entity of the world."""
    import world_reader
    out = {}
    for e in world_reader.World(world).entities():
        if "UUID" in e and "Pos" in e:
            out[unitlib.uuid_str(e["UUID"])] = (float(e["Pos"][0]), float(e["Pos"][2]))
    return out


def alive(state):
    """UUID -> player of the units of the players that live at the end of the game (train.py drops the dead ones)."""
    out = {}
    for p, x in state["players"].items():
        for u in [*x.get("soldiers", {}), *x.get("villagers", {})]:
            out[u] = int(p)
    return out


def objects(data, state, pos):
    """The objects at the end of the game: dicts with "id", "player", "tile" (x, y) and "rotation". A save of the
    editor has only "placed": the objects that the person placed (editor.State, #6012), no game state."""
    T, out = data["tile_size"], []
    placed = (state or {}).get("placed", [])
    removed = set((state or {}).get("removed", []))                    # start objects removed in the editor (#6002)
    state = state if state and "players" in state else None
    live = alive(state) if state else None
    ruins, empty, done = set(), set(), []
    seen, left = set(), set()                                          # trees, bushes and fish (#5672)
    for x in (state or {}).get("players", {}).values():
        ruins |= {tuple(r) for r in savegame.unpack(x.get("ruins", {"set": []}))}
        for tiles in savegame.unpack(x.get("map", {}).get("mines", {})).values():
            empty |= {tuple(t) for t, amount in tiles.items() if amount <= 0}
        for key in ("bushes", "fish", "trees"):
            if key in x.get("map", {}):
                tiles = savegame.unpack(x["map"][key])
                seen |= {tuple(t) for t in tiles}
                left |= {tuple(t) for t, amount in tiles.items() if amount > 0}
        done += [s for s in savegame.unpack(x.get("sites", [])) if s.get("progress", 0) >= 1]
    empty |= seen - left                                               # a cut tree, an empty bush or fish
    for i, o in enumerate(data["objects"]):
        if i in removed:
            continue
        tile = tuple(o["tile"])
        if o["kind"] == "unit" and live is not None and o.get("uuid") and o["player"] and o["uuid"] not in live \
                and (str(o["player"]) in state["players"] or o["uuid"] not in pos):
            continue                                                   # killed in the game; no loop: no entity (#5752)
        if o["kind"] == "unit" and state is not None and o.get("uuid") and not o["player"] and o["uuid"] not in pos:
            continue                                                   # a hunted animal: no entity left (#5672)
        if o["kind"] == "building" and "footprint" in o:
            x0, z0, x1, z1 = o["footprint"]
            if (x0, x1, z0, z1) in ruins:
                continue
        if o["kind"] == "other" and (int(tile[0]), int(tile[1])) in empty:
            continue                                                   # a mined mine, a cut tree or an empty food source
        if o.get("uuid") in pos:
            tile = tuple(v / T for v in pos[o["uuid"]])
        player = live.get(o.get("uuid"), o["player"]) if live else o["player"]   # a converted unit (monk)
        out.append({"id": o["id"], "player": player, "tile": tile, "rotation": o.get("rotation", 0.0)})
    start = {o.get("uuid") for o in data["objects"]}
    names = {}
    for x in (state or {}).get("players", {}).values():
        names.update(x.get("soldiers", {}))
        names.update(dict.fromkeys(x.get("villagers", {}), "VILLAGER_MALE"))
    for u, p in sorted((live or {}).items()):                          # the trained units
        if u not in start and u in pos and (i := unit_id(names.get(u))) is not None:
            out.append({"id": i, "player": p, "tile": tuple(v / T for v in pos[u]), "rotation": 0.0})
    for s in done:                                                     # the new buildings
        x0, x1, z0, z1 = s["footprint"]
        if (i := unit_id(s["name"])) is not None and not any(tuple(o.get("footprint", ())) == (x0, z0, x1, z1)
                                                             for o in data["objects"]):
            out.append({"id": i, "player": s["player"], "tile": ((x0 + x1) / 2 / T, (z0 + z1) / 2 / T), "rotation": 0.0})
    out += [{"id": int(o["id"]), "player": int(o["player"]), "tile": tuple(o["tile"]), "rotation": 0.0} for o in placed]
    import aoe2mc  # the tiles of the world are turned (#5674)
    back, turn = (4 - data.get("turn", 0)) % 4, data.get("turn", 0)
    for o in out:
        o["tile"] = aoe2mc.turn_tile(*o["tile"], data["map_size"], back)
        o["rotation"] = o["rotation"] - turn * math.pi / 2
    return out


def base(state):
    """The block name of a block state, with no "minecraft:" and no properties."""
    return state.split("[")[0].removeprefix("minecraft:")


# Blocks on the ground that are not the ground: plants, snow, water, trees (with the deco of terrain_style)
LOOSE = ("air", "water", "lava", "barrier", "light", "snow", "ice", "grass", "fern", "bush", "flower", "leaves", "log",
         "kelp", "wheat", "carrot", "potato", "sapling", "vine", "lily", "mushroom", "tulip", "poppy", "dandelion",
         "orchid", "allium", "bluet", "daisy", "cornflower", "lilac", "rose", "peony", "sugar_cane", "bamboo", "torch",
         "carpet", "petals", "button", "pressure_plate", "rail", "sign", "banner")


# The ground blocks that Columns.ground_detail mixes into the top of a terrain (noise patches, worn roads and verges):
# a change inside one family is the detail of the converter, not a player (also not grass to dirt by a player).
FAMILIES = (("grass_block", "coarse_dirt", "moss_block", "podzol", "rooted_dirt", "dirt", "dirt_path", "mycelium"),
            ("cobblestone", "mossy_cobblestone", "andesite", "stone", "gravel", "tuff", "cracked_stone_bricks",
             "polished_andesite", "coarse_dirt", "dirt_path"))


def same(a, b):
    """True when the top block a can be the converter's detail of the top block b."""
    return a == b or any(a in f and b in f for f in FAMILIES)


def terrain_tops():
    """({top block: AoE2 terrain ID}, {terrain ID: top block}, loose block names). A block of several terrains gets
    the lowest ID."""
    from AoE2ScenarioParser.datasets.terrains import TerrainId
    tops, of, loose = {}, {}, set()
    for t in sorted(TerrainId, key=lambda t: t.value):
        style = aoe2mc.terrain_style(t.name)
        of[t.value] = b = base(style["top"])
        tops.setdefault(b, t.value)
        loose |= {base(d) for d, _ in style["deco"]}
    return tops, of, loose - set(tops)


def is_loose(name, loose):
    return name in loose or (name not in ("snow_block", "packed_ice", "grass_block")
                             and any(k in name for k in LOOSE))


def top_blocks(world, n, T, tops, loose, ys=False):
    """(n*T, n*T) array of the highest ground block of each column: a terrain top, or "" for a block of no terrain.
    Loose blocks on the ground (plants, snow, leaves, water) do not count. ys: also the (n*T, n*T) Y of that block
    (of any ground block, -1 for none)."""
    import numpy as np
    import world_reader
    w, size = world_reader.World(world), n * T
    out = np.full((size, size), "", dtype=object)
    height = np.full((size, size), -1, dtype=np.int32)
    for (cx, cz), c in w.chunks().items():
        x0, z0 = cx * 16, cz * 16
        if x0 >= size or z0 >= size or x0 < 0 or z0 < 0:
            continue
        found = np.full((16, 16), "", dtype=object)                    # [z, x]
        fy = np.full((16, 16), -1, dtype=np.int32)
        for sec in sorted(c.get("sections", []), key=lambda s: -int(s["Y"])):
            if "block_states" not in sec:
                continue
            names = [base(world_reader.state_name(e)) for e in sec["block_states"]["palette"]]
            good = np.array([not is_loose(v, loose) for v in names])
            if not good.any():
                continue
            bs = sec["block_states"]
            if "data" in bs:
                bits = max(4, (len(names) - 1).bit_length())
                per = 64 // bits
                longs = np.array([int(v) & 0xFFFFFFFFFFFFFFFF for v in bs["data"]], dtype=np.uint64)
                idx = ((longs[:, None] >> (np.arange(per, dtype=np.uint64) * np.uint64(bits)))
                       & np.uint64((1 << bits) - 1)).ravel()[:4096].astype(np.int64).reshape(16, 16, 16)   # [y, z, x]
            else:
                idx = np.zeros((16, 16, 16), dtype=np.int64)
            hit = good[idx]
            for y in range(15, -1, -1):
                new = hit[y] & (found == "")
                if new.any():
                    found[new] = np.array(names, dtype=object)[idx[y][new]]
                    fy[new] = int(sec["Y"]) * 16 + y
            if (found != "").all():
                break
        found[~np.isin(found, list(tops))] = ""
        height[z0:z0 + 16, x0:x0 + 16] = fy[:size - z0, :size - x0]
        out[z0:z0 + 16, x0:x0 + 16] = found[:size - z0, :size - x0]
    return (out, height) if ys else out


def covered(data):
    """The (x, y) tiles of the turned grid under an object: footprints, mines and tree heaps."""
    T, skip = data["tile_size"], set()
    for o in data["objects"]:
        if "footprint" in o:
            x0, z0, x1, z1 = o["footprint"]
            skip |= {(x, y) for x in range(x0 // T, -(-x1 // T)) for y in range(z0 // T, -(-z1 // T))}
        elif o["kind"] == "other":                                     # a mine or tree heap covers its tile
            skip.add((int(o["tile"][0]), int(o["tile"][1])))
    return skip


def ground(world, data, terrain):
    """The terrain rows with the tiles whose ground a player changed: a tile changes when the most common top block
    of its columns is a terrain top and not the top of its start terrain (or of its detail, FAMILIES). Footprint tiles
    of objects and the tiles of mines and trees stay."""
    from collections import Counter
    n, T = data["map_size"], data["tile_size"]
    tops, of, loose = terrain_tops()
    top = top_blocks(world, n, T, tops, loose)
    skip = covered(data)
    out = [list(r) for r in terrain]
    for y in range(n):
        for x in range(n):
            if (x, y) in skip:
                continue
            cells = top[y * T:(y + 1) * T, x * T:(x + 1) * T].ravel()
            b = Counter(cells).most_common(1)[0][0]
            if b and not same(b, of.get(terrain[y][x])):
                out[y][x] = tops[b]
    return out


def heights(world, data, T, H):
    """(n, n) AoE2 elevation of each tile of the turned grid, [y][x]: the median Y of the top ground block of its
    T x T columns, round((Y - WATER_Y - 1) / H), clipped to the levels 0 to 7 (the land of aoe2mc.convert)."""
    tops, _, loose = terrain_tops()
    n = data["map_size"]
    _, y = top_blocks(world, n, T, tops, loose, ys=True)
    med = np.median(y.reshape(n, T, n, T), axis=(1, 3))
    return np.clip(np.rint((med - aoe2mc.WATER_Y - 1) / H), 0, 7).astype(int)


def raised(world, data, elevation):
    """The elevation [y][x] with the new level of each tile whose height differs from the land of its level.
    Footprint tiles of objects and the tiles of mines and trees keep their level."""
    T = data["tile_size"]
    new = heights(world, data, T, data.get("level_height", 3))
    out, skip = elevation.copy(), covered(data)
    for x, y in zip(*np.nonzero(new != elevation)[::-1]):
        if (int(x), int(y)) not in skip:
            out[y, x] = new[y, x]
    return out


def unit_id(name):
    """The AoE2 ID of a unit, building or other object name of AoE2ScenarioParser, or None."""
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo
    from AoE2ScenarioParser.datasets.other import OtherInfo
    from AoE2ScenarioParser.datasets.units import UnitInfo
    for info in (UnitInfo, BuildingInfo, OtherInfo):
        if name in info.__members__:
            return info[name].ID
    return None


def export(path, out, heights=False):
    """Write the scenario of the world or save folder path to out. Returns out. heights: a tile whose ground height
    the person changed gets the new elevation (the editor, #6000)."""
    world, state = folders(path)
    with open(os.path.join(world, "aoe2mc.json")) as f:
        data = json.load(f)
    n = data["map_size"]
    scn = scenarios.new_scenario(n)
    back = (4 - data.get("turn", 0)) % 4                # the turn of --orientation, undone (#5674)
    terrain = ground(world, data, [[int(v) for v in row.split()] for row in data["terrain"]])  # in the turned grid
    terrain = np.rot90(np.array(terrain).T, back)
    elevation = np.array([[int(v) for v in row.split()] for row in data["elevation"]])     # [y][x], turned grid
    if heights:
        elevation = raised(world, data, elevation)
    elevation = np.rot90(elevation.T, back)
    for t in scn.map_manager.terrain:
        t.terrain_id, t.elevation = int(terrain[t.x, t.y]), int(elevation[t.x, t.y])
    players = [int(p) for p in data["players"] if int(p)]
    scn.player_manager.active_players = max(players, default=1)
    for p in players:
        civ = data["players"][str(p)].get("civ")
        if civ in Civilization.__members__:
            scn.player_manager.players[p].civilization = Civilization[civ]
        pl, info = scn.player_manager.players[p], data["players"][str(p)]
        if state and str(p) in state.get("players", {}):           # the end of the game (#5673)
            s = state["players"][str(p)]
            for r in RESOURCES:
                setattr(pl, r, int(s.get("stock", {}).get(r, 0)))
            reached = sum(t in s.get("techs", ()) for t in build.AGE_TECHS)
            pl.starting_age = AGES[min(reached, len(AGES) - 1)]
        else:
            for r, v in info.get("resources", {}).items():
                setattr(pl, r, int(v))
            if "age" in info:                               # "feudal" in aoe2mc.json, as the setup of the world
                pl.starting_age = StartingAge[info["age"].upper().replace("-", "_") + "_AGE"]
    from AoE2ScenarioParser.datasets.players import PlayerId
    with contextlib.redirect_stdout(io.StringIO()):
        for o in objects(data, state, positions(world)):
            x, y = (min(max(v, 0), n - 0.01) for v in o["tile"])
            scn.unit_manager.add_unit(PlayerId(o["player"]), o["id"], x=x, y=y, rotation=o["rotation"])
    return scenarios.save(scn, out)


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("world", help="a converted world, or a save folder of game/run.py (saves/...)")
    a.add_argument("out", help="the .aoe2scenario file to write")
    args = a.parse_args(argv)
    print(export(args.world, args.out))


if __name__ == "__main__":
    main()
