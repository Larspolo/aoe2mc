#!/usr/bin/env python3
"""
aoe2mc - Convert an Age of Empires II: DE scenario (.aoe2scenario) or the start state of a recorded game
(.aoe2record) or an old scenario (.scx, format 1.21) to a Minecraft Java world. A campaign (.aoe2campaign) gives one world per scenario; an old campaign
(.cpx, .cpn) gives its old scenario files and the steps to save them in the DE editor.

Usage:
    python aoe2mc.py MAP.aoe2scenario OUTPUT_WORLD_FOLDER [options]

Options:
    --tile-size N      Minecraft blocks per AoE2 tile, in each direction (default 4)
    --level-height N   Minecraft blocks per AoE2 elevation level (default 3)
    --name TEXT        World name in the Minecraft menu (default: file name)
    --seed N           Seed for the random details (tree heights, flowers) (default 1)
    --preview          Also write preview.png (top view) into the world folder
    --mc-version V     Minecraft Java version of the output: 26.3 (default) or 1.21.1
    --orientation C    Minecraft corner (ne, se, sw, nw) of the top corner of the AoE2 screen (default ne)
    --no-units         Do not convert units (mobs, boats, minecarts)
    --no-birds         Do not convert birds
    --no-barriers      Do not fill building footprints with invisible barrier blocks
    --verbose          Print the time of each phase (read, columns, objects, units, chunks, write)
    --scenario N       Campaign: convert only scenario N (1 = the first)
    --architecture X   Use one architecture set for all players (western, central, mediterranean,
                       middle_eastern, south_asian, african, east_asian, southeast_asian, mesoamerican)

Requirements:
    pip install AoE2ScenarioParser nbtlib numpy pillow

Coordinates: AoE2 tile (x, y) becomes Minecraft block x = x * tile-size, z = y * tile-size.
The world is saved with Minecraft data version 1.21.1. Newer Minecraft versions upgrade it on load.
"""
import argparse
import contextlib
import io
import json
import math
import os
import re
import textwrap
import time
import zlib
from collections import Counter

import numpy as np
from nbtlib import File
from nbtlib.tag import Byte, Compound, Double, Float, Int, IntArray, List, Long, LongArray, String

import buildings
import units

# Blocks with the 'waterlogged' property. A block of this list under the water surface gets waterlogged=true (#19).
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools", "mcdata", "1.21.1.json")) as _f:
    BLOCK_PROPS = {"minecraft:" + k: v for k, v in json.load(_f)["blocks"].items()}
WATERLOGGABLE = {k for k, v in BLOCK_PROPS.items() if "waterlogged" in v}

# Output format per Minecraft Java version (docs/minecraft-versions.md). Entities: units.to_version().
VERSIONS = {
    "1.21.1": dict(name="1.21.1", data_version=3955, pack_format=48, renames={}),
    "26.3": dict(name="26.3", data_version=5023, pack_format=121, renames={"minecraft:chain": "minecraft:iron_chain"}),
}
VERSION_NAME = "26.3"        # the default output version. The code uses the 1.21.1 names (no renames).
DATA_VERSION = VERSIONS[VERSION_NAME]["data_version"]
MC = VERSIONS[VERSION_NAME]  # the version of the running conversion; convert() sets it
V26_1, V26_3 = 4786, 5023    # data versions of format changes (more in units.to_version)
MIN_Y, MAX_Y = -64, 320      # world height range (MAX_Y exclusive)
HEIGHT = MAX_Y - MIN_Y
WATER_Y = 62                 # Y of the highest water block (sea level)
NONE = -10000                # marker for "no column here" (outside the map)
# AoE2 tile x goes to the top corner of the screen, tile y to the bottom corner. With x → +X and y → +Z the
# top corner is in the north-east: the map is the in-game view turned 45° clockwise, not mirrored.
# The player looks north-east at the spawn, like the AoE2 camera (yaw 0 = south, 90 = west, 180 = north).
SPAWN_YAW = -135.0
# --orientation: the Minecraft corner that gets the top corner of the AoE2 screen. Value: clockwise quarter turns
# of the tile grid (seen from above) and the spawn yaw (the player looks at that corner). "ne" is no turn.
ORIENTATIONS = {"ne": (0, SPAWN_YAW), "se": (1, -45.0), "sw": (2, 45.0), "nw": (3, 135.0)}


# --------------------------------------------------------------------------------------------
# Block registry: one integer per block state, so that the world can be numpy arrays.
# --------------------------------------------------------------------------------------------
class Blocks:
    def __init__(self):
        self.states = ["minecraft:air"]
        self.index = {"minecraft:air": 0}
        self.wets = {}

    def __call__(self, state):
        if not state.startswith("minecraft:"):
            state = "minecraft:" + state
        i = self.index.get(state)
        if i is None:
            i = len(self.states)
            self.states.append(state)
            self.index[state] = i
        return i

    def wet(self, i):
        """Block id i with waterlogged=true, or i if the block has no 'waterlogged' property."""
        if i not in self.wets:
            name, _, props = self.states[i].partition("[")
            p = [kv for kv in props[:-1].split(",") if kv and not kv.startswith("waterlogged=")]
            self.wets[i] = self(f"{name}[{','.join(p + ['waterlogged=true'])}]") if name in WATERLOGGABLE else i
        return self.wets[i]

    def nbt(self, i):
        """Palette entry for block id i: {Name, Properties}, with the block names of the output version."""
        name, _, props = self.states[i].partition("[")
        name = MC["renames"].get(name, name)
        key, pkey = ("id", "properties") if MC["data_version"] >= V26_3 else ("Name", "Properties")
        if not props:
            return Compound({key: String(name)})
        p = dict(kv.split("=") for kv in props[:-1].split(","))
        return Compound({key: String(name), pkey: Compound({k: String(v) for k, v in p.items()})})


B = Blocks()
AIR = 0
STONE, DEEPSLATE, BEDROCK = B("stone"), B("deepslate"), B("bedrock")
WATER, ICE = B("water[level=0]"), B("ice")

PLAYER_COLORS = ["light_gray", "blue", "red", "green", "yellow", "cyan", "purple", "gray", "orange"]


# --------------------------------------------------------------------------------------------
# Terrain: AoE2 terrain name -> Minecraft surface.
# depth > 0 means water. deco is a list of (block, chance) put on top of the column.
# --------------------------------------------------------------------------------------------
FLOWERS = [("poppy", .06), ("dandelion", .06), ("cornflower", .04), ("oxeye_daisy", .04),
           ("short_grass", .2)]


def terrain_style(name):
    n = name.upper()

    def S(top, sub="dirt", depth=0, bottom="sand", biome="plains", deco=(), ice=False):
        return dict(top=top, sub=sub, depth=depth, bottom=bottom, biome=biome,
                    deco=list(deco), ice=ice)

    # --- water ---
    if "ICE_NAVIGABLE" in n:
        return S("gravel", "gravel", 2, "gravel", "frozen_ocean", ice=True)
    if "SWAMP_SHALLOWS" in n:
        return S("mud", "mud", 1, "mud", "swamp", [("seagrass", .3)])
    if "MANGROVE" in n:
        return S("mud", "mud", 1, "mud", "mangrove_swamp")
    if "DEEP" in n and "WATER" in n:
        return S("gravel", "gravel", 7, "gravel", "deep_ocean")
    if "SHALLOW" in n:
        return S("sand", "sand", 1, "sand", "river", [("seagrass", .1)])
    if "WATER" in n:
        if "BROWN" in n or "GREEN" in n:
            return S("mud", "mud", 4, "mud", "swamp", [("seagrass", .2)])
        if "AZURE" in n:
            return S("sand", "sand", 4, "sand", "warm_ocean")
        return S("sand", "sand", 4, "sand", "ocean", [("seagrass", .2 if "WEEDS" in n else .05)])
    # --- land ---
    if "ICE" in n:
        return S("packed_ice", "packed_ice", biome="snowy_plains")
    if "SNOW" in n:
        return S("snow_block", "dirt", biome="snowy_taiga" if "FOREST" in n else "snowy_plains")
    if "BEACH" in n:
        top = "gravel" if "GRAVEL" in n else "stone" if "ROCK" in n else "sand"
        return S(top, "sand", biome="beach",
                 deco=[("short_grass", .15)] if "VEGETATION" in n else [])
    if "DESERT" in n and "GRAVEL" not in n:
        return S("sandstone" if "CRACKED" in n else "sand", "sandstone", biome="desert",
                 deco=[("dead_bush", .01)])
    if "GRAVEL" in n and "ROAD" not in n:
        return S("gravel", "gravel", biome="desert" if "DESERT" in n else "plains")
    if "FARM" in n:
        if "DEAD" in n:
            return S("farmland[moisture=7]")
        age = "0" if n.endswith("_0") else "3" if n.endswith("_33") else "5" if n.endswith("_67") else "7"
        return S("farmland[moisture=7]", deco=[(f"wheat[age={age}]", 1.0)])
    if "PASTURE" in n:
        return S("grass_block", deco=[("short_grass", .3)])
    if "ROAD" in n:
        top = ("gravel" if "GRAVEL" in n else "mycelium" if "FUNGUS" in n
               else "mossy_cobblestone" if "BROKEN" in n else "cobblestone")
        return S(top, "cobblestone")
    if "ROCK" in n:
        return S("stone", "stone")
    if "BLACK" in n:
        return S("blackstone", "blackstone")
    if "CORRUPTION" in n:
        return S("crimson_nylium", "netherrack")
    if "BOG" in n or "MUD" in n:
        return S("mud", "mud", biome="swamp")
    if "SAVANNAH" in n:
        return S("coarse_dirt", biome="savanna")
    if "DIRT" in n:
        return S("coarse_dirt", biome="savanna")
    if "DRY" in n and "GRASS" in n:
        return S("grass_block", biome="savanna", deco=[("short_grass", .1)])
    if any(k in n for k in ("ACACIA", "BAOBAB", "DRAGON")):
        return S("grass_block", biome="savanna")
    if "PALM_DESERT" in n:
        return S("sand", "sandstone", biome="desert")
    if "BAMBOO" in n:
        return S("grass_block", biome="bamboo_jungle")
    if any(k in n for k in ("JUNGLE", "RAINFOREST", "PALM", "SOUTH_AMERICAN")):
        return S("grass_block", biome="jungle", deco=[("fern", .1)])
    if "PINE" in n or "SPRUCE" in n:
        return S("podzol", biome="taiga")
    if "BIRCH" in n:
        return S("grass_block", biome="birch_forest")
    if "DEAD" in n:
        return S("coarse_dirt")
    if "UNDERBRUSH" in n:
        return S("podzol" if "LEAVES" in n else "grass_block", biome="forest",
                 deco=[("fern", .25), ("short_grass", .2)])
    if "FOREST" in n:
        return S("grass_block", biome="forest")
    if "FLOWERS" in n:
        return S("grass_block", biome="meadow", deco=FLOWERS)
    return S("grass_block", deco=[("short_grass", .05)])


# --------------------------------------------------------------------------------------------
# Read the AoE2 scenario.
# --------------------------------------------------------------------------------------------
def object_kinds():
    """Object ID -> (kind prefix, name). Scenarios and recorded games use the same IDs."""
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo
    from AoE2ScenarioParser.datasets.heroes import HeroInfo
    from AoE2ScenarioParser.datasets.other import OtherInfo
    from AoE2ScenarioParser.datasets.units import UnitInfo
    kinds = {}
    for prefix, enum in (("H", HeroInfo), ("U", UnitInfo), ("O", OtherInfo), ("B", BuildingInfo)):
        for e in enum:          # later enums win: Building > Other > Unit > Hero
            kinds[e.ID] = (prefix, e.name)
    return kinds


def read_map(path):
    """read_record for .aoe2record files, read_scx for old .scx scenarios, else read_scenario."""
    p = path.lower()
    return (read_record if p.endswith(".aoe2record") else read_scx if p.endswith(".scx") else read_scenario)(path)


def read_scx(path):
    """An old scenario (.scx format 1.21, #312), as read_scenario returns it. The old terrain and object IDs are the
    DE IDs. A map that is not square gets the edge tiles repeated to a square. Old scenarios give no texts here."""
    import scx
    from AoE2ScenarioParser.datasets.terrains import TerrainId
    try:
        s = scx.read(path)
    except scx.ScxError as e:
        raise OptionError(str(e)) from None
    w, h = s["width"], s["height"]
    size = max(w, h)
    terrain, elevation = (np.pad(a, ((0, size - w), (0, size - h)), mode="edge") for a in (s["terrain"], s["elevation"]))
    kinds = object_kinds()
    players = {}
    for pid, p in s["players"].items():
        color = buildings.COLOR_NAMES[p["color"]] if pid and p["color"] is not None and 0 <= p["color"] < 8 else "light_gray"
        players[pid] = {"color": color, "arch": buildings.CIV_TO_ARCH.get(p["civ"], "western"), "civ": p["civ"],
                        "view": p["view"]}
    objects = []
    for o in s["objects"]:
        prefix, name = kinds.get(o["type"], ("?", f"UNKNOWN_{o['type']}"))
        holder = o["garrisoned_in"]
        objects.append(dict(kind="U" if prefix == "H" else prefix, hero=prefix == "H", name=name, id=o["type"],
                            player=o["player"], x=o["x"], y=o["y"], rotation=float(o["angle"]),
                            garrisoned=holder is not None, ref=o["id"], holder=holder))
    texts = {k: "" for k in CHAPTERS}
    return size, terrain, elevation, {t.value: t.name for t in TerrainId}, texts, objects, players


def read_scenario(path):
    from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
    from AoE2ScenarioParser.datasets.terrains import TerrainId

    with contextlib.redirect_stdout(io.StringIO()):   # the parser prints a lot of status text
        scn = AoE2DEScenario.from_file(path)

    mm = scn.map_manager
    size = mm.map_size
    terrain = np.zeros((size, size), np.int16)
    elevation = np.zeros((size, size), np.float32)
    for t in mm.terrain:
        terrain[t.x, t.y] = t.terrain_id
        elevation[t.x, t.y] = t.elevation

    terrain_names = {t.value: t.name for t in TerrainId}

    kinds = object_kinds()

    players = {}
    for p in scn.player_manager.players:
        civ = p.civilization          # the architecture set field is not reliable in older scenario versions
        try:
            if getattr(civ, "name", "RANDOM") in ("RANDOM", "GAIA") and p.architecture_set.name not in ("RANDOM", "GAIA"):
                civ = p.architecture_set
        except Exception:
            pass
        color = buildings.COLOR_NAMES[p.color] if 0 <= p.color < 8 else "light_gray"
        arch = buildings.CIV_TO_ARCH.get(getattr(civ, "name", ""), "western")
        view = (getattr(p, "initial_player_view_x", -1), getattr(p, "initial_player_view_y", -1))
        players[p.player_id] = {"color": color if p.player_id else "light_gray", "arch": arch,
                                "civ": getattr(civ, "name", "?"),
                                "view": view if view[0] is not None and min(view) >= 0 else None}

    msg = scn.message_manager
    texts = {k: getattr(msg, k, "") or "" for k in CHAPTERS}

    objects = []
    for player, player_units in enumerate(scn.unit_manager.units):
        for u in player_units:
            prefix, name = kinds.get(u.unit_const, ("?", f"UNKNOWN_{u.unit_const}"))
            garrisoned = u.garrisoned_in_id not in (None, -1)
            objects.append(dict(kind="U" if prefix == "H" else prefix, hero=prefix == "H", name=name, id=u.unit_const,
                                player=player, x=u.x, y=u.y, rotation=float(u.rotation or 0), garrisoned=garrisoned,
                                ref=u.reference_id, holder=u.garrisoned_in_id if garrisoned else None))
    return size, terrain, elevation, terrain_names, texts, objects, players


ANNEXES = {618, 619, 620}       # the three annex parts of a town center: the TC design draws them


def read_record(path):
    """The start state of a recorded game (the header snapshot), as read_scenario returns it. The mgz model
    has no rotation (0) and no texts; the start view of a player is its start position."""
    try:
        from mgz.model import parse_match
    except ImportError:
        raise SystemExit("A .aoe2record file needs the mgz package: python3 -m pip install mgz") from None
    from AoE2ScenarioParser.datasets.terrains import TerrainId
    with open(path, "rb") as f:
        match = parse_match(f)
    size = match.map.dimension
    terrain = np.zeros((size, size), np.int16)
    elevation = np.zeros((size, size), np.float32)
    for t in match.map.tiles:
        terrain[t.position.x, t.position.y] = t.terrain
        elevation[t.position.x, t.position.y] = t.elevation
    terrain_names = {t.value: t.name for t in TerrainId}

    players = {0: {"color": "light_gray", "arch": "western", "civ": "GAIA", "view": None}}
    for p in match.players:
        civ = (p.civilization or "?").upper()
        players[p.number] = {"color": buildings.COLOR_NAMES[p.color_id] if 0 <= p.color_id < 8 else "light_gray",
                             "arch": buildings.CIV_TO_ARCH.get(civ, "western"), "civ": civ,
                             "view": (p.position.x, p.position.y) if p.position else None}

    kinds, objects = object_kinds(), []
    for player, objs in [(0, match.gaia)] + [(p.number, p.objects) for p in match.players]:
        for o in objs:
            if o.object_id in ANNEXES:
                continue
            prefix, name = kinds.get(o.object_id, ("?", f"UNKNOWN_{o.object_id}"))
            objects.append(dict(kind="U" if prefix == "H" else prefix, hero=prefix == "H", name=name, player=player,
                                x=o.position.x, y=o.position.y, rotation=0.0, garrisoned=False,
                                ref=o.instance_id, holder=None))
    return size, terrain, elevation, terrain_names, {k: "" for k in CHAPTERS}, objects, players


def turn_tile(x, y, size, k):
    """Tile position (x, y) after k clockwise quarter turns of a size × size grid (size 0: turn a vector)."""
    for _ in range(k % 4):
        x, y = size - y, x
    return x, y


def turn_map(k, size, terrain, elevation, objects, players):
    """Turn the tile grid by k clockwise quarter turns (--orientation). It is a turn, not a mirror, so buildings
    keep their hand. Unit rotation (direction cos r, sin r in tiles) and the start views turn with the map."""
    for o in objects:
        o["x"], o["y"] = turn_tile(o["x"], o["y"], size, k)
        o["rotation"] = o.get("rotation", 0.0) + k * math.pi / 2
    for p in players.values():
        if p.get("view"):
            p["view"] = turn_tile(*p["view"], size, k)
    return np.rot90(terrain, k).copy(), np.rot90(elevation, k).copy()


# --------------------------------------------------------------------------------------------
# Columns: the terrain of each Minecraft (x, z) column, as numpy arrays.
# --------------------------------------------------------------------------------------------
def upsample(grid, T):
    """Bilinear interpolation of a tile grid to a block grid (smooth slopes)."""
    n = grid.shape[0]
    u = (np.arange(n * T) + 0.5) / T - 0.5
    u = np.clip(u, 0, n - 1)
    i0 = np.floor(u).astype(int)
    i1 = np.minimum(i0 + 1, n - 1)
    f = (u - i0).astype(np.float32)
    a = grid[i0][:, i0] * (1 - f)[None, :] + grid[i0][:, i1] * f[None, :]
    b = grid[i1][:, i0] * (1 - f)[None, :] + grid[i1][:, i1] * f[None, :]
    return a * (1 - f)[:, None] + b * f[:, None]


def water_bodies(wet, elevation):
    """Label the 4-connected bodies of water tiles. Returns (label per tile, lowest elevation per label);
    label 0 is land (elevation 0)."""
    from collections import deque
    n = wet.shape[0]
    body = np.zeros(wet.shape, np.int32)
    levels = [0.0]
    for i, j in zip(*np.nonzero(wet)):
        if body[i, j]:
            continue
        k = len(levels)
        body[i, j] = k
        low, q = float(elevation[i, j]), deque([(i, j)])
        while q:
            a, b = q.popleft()
            low = min(low, float(elevation[a, b]))
            for x, y in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
                if 0 <= x < n and 0 <= y < n and wet[x, y] and not body[x, y]:
                    body[x, y] = k
                    q.append((x, y))
        levels.append(low)
    return body, np.array(levels, np.float32)


class Columns:
    def __init__(self, size, terrain, elevation, terrain_names, T, H, rng):
        styles, style_of_id = [], {}
        for tid in np.unique(terrain):
            style_of_id[int(tid)] = len(styles)
            styles.append(terrain_style(terrain_names.get(int(tid), "GRASS_1")))
        sid_tiles = np.vectorize(style_of_id.get)(terrain).astype(np.int16)

        n = size * T
        self.T, self.n = T, n
        self.water_y = WATER_Y
        self.width = -(-n // 16) * 16                  # round up to whole chunks
        W = self.width
        sid = np.repeat(np.repeat(sid_tiles, T, 0), T, 1)

        depth_tiles = np.array([s["depth"] for s in styles], np.float32)[sid_tiles]
        land = WATER_Y + 1 + np.rint(upsample(elevation, T) * H).astype(np.int16)
        depth = upsample(depth_tiles, T)
        is_water = np.repeat(np.repeat(depth_tiles > 0, T, 0), T, 1)
        # One level per connected body of water (#165): AoE2 has no water level, and Minecraft water must be level.
        # The lowest elevation of the body cannot spill over its own tiles (docs/research/water.md).
        body, levels = water_bodies(depth_tiles > 0, elevation)
        surface_tiles = WATER_Y + np.rint(levels[body] * H).astype(np.int16)
        surface = np.repeat(np.repeat(surface_tiles, T, 0), T, 1)
        water_bottom = (surface - np.maximum(1, np.rint(depth))).astype(np.int16)
        # Shores (#166): land within 2 tiles of the water slopes down to it, 1 block per block in the first tile (a
        # beach that units can walk), 2 in the second (AoE2 draws a slope of the height map there, never a wall).
        # ws = the highest water surface near the column.
        ws = np.where(is_water, surface, NONE).astype(np.int16)
        cap = np.full((n, n), 32767, np.int16)
        for d in range(1, 2 * T + 1):
            p = np.full((n + 2, n + 2), NONE, np.int16)
            p[1:-1, 1:-1] = ws
            ws = np.maximum.reduce([p[a:a + n, b:b + n] for a in range(3) for b in range(3)])
            cap = np.where((ws > NONE) & (cap == 32767), ws + d + max(0, d - T), cap)
        land = np.minimum(land, cap)
        # Land next to the water is at least as high as the surface, else the water flows out.
        rim = np.full((n + 2, n + 2), NONE, np.int16)
        rim[1:-1, 1:-1] = np.where(is_water, surface, NONE)
        rim = np.maximum.reduce([rim[:-2, 1:-1], rim[2:, 1:-1], rim[1:-1, :-2], rim[1:-1, 2:]])
        land = np.where(~is_water, np.maximum(land, rim), land)

        def full(fill, dtype):
            a = np.full((W, W), fill, dtype)
            return a

        self.top = full(NONE, np.int16)
        self.wtop = full(NONE, np.int16)
        self.top[:n, :n] = np.where(is_water, water_bottom, land)
        self.wtop[:n, :n] = np.where(is_water, surface, self.top[:n, :n])

        lut = lambda key: np.array([B(s[key]) for s in styles], np.uint16)
        sub_lut = np.array([B(s["bottom"] if s["depth"] else s["sub"]) for s in styles], np.uint16)
        self.top_id = full(AIR, np.uint16)
        self.sub_id = full(AIR, np.uint16)
        # Blocks of `sub` under the top: at least 3, and down to the lowest neighbour, so that steep banks and
        # steps show dirt or sand on their faces, not stone.
        t = np.pad(self.top[:n, :n], 1, mode="edge")
        low = np.minimum.reduce([t[:-2, 1:-1], t[2:, 1:-1], t[1:-1, :-2], t[1:-1, 2:]])
        self.sub_depth = full(3, np.int16)
        self.sub_depth[:n, :n] = np.clip(self.top[:n, :n] - low, 3, 64)
        self.ice = full(False, bool)
        self.top_id[:n, :n] = lut("top")[sid]
        self.sub_id[:n, :n] = sub_lut[sid]
        self.ice[:n, :n] = np.array([s["ice"] for s in styles])[sid] & is_water

        biomes = sorted({s["biome"] for s in styles})
        self.biome_names = ["minecraft:" + b for b in biomes]
        self.biome = full(0, np.uint8)
        self.biome[:n, :n] = np.array([biomes.index(s["biome"]) for s in styles], np.uint8)[sid]

        # Decoration (flowers, grass, wheat, seagrass) on top of the column.
        self.deco = full(AIR, np.uint16)
        r = rng.random((n, n))
        deco = np.zeros((n, n), np.uint16)
        for i, s in enumerate(styles):
            m = sid == i
            acc = 0.0
            for block, chance in s["deco"]:
                hit = m & (r >= acc) & (r < acc + chance)
                deco[hit] = B(block)
                acc += chance
        self.deco[:n, :n] = deco
        self.deco2 = full(AIR, np.uint16)             # upper half of tall plants
        self.blocked = np.zeros((n, n), bool)         # columns inside a building or obstacle footprint
        self.floor = MIN_Y                            # air under this Y (--border diorama)
        self.ground_detail(styles, sid, depth_tiles, rng)

    def ground_detail(self, styles, sid, depth_tiles, rng):
        """Patches of other ground blocks and plants, so large grass and dirt areas are not plain.
        Everything is decoration that cannot be used (no crops, no berries)."""
        n = self.n

        def noise(scale):
            g = rng.random((n // scale + 2, n // scale + 2)).astype(np.float32)
            return upsample(g, scale)[:n, :n]

        def group(s):
            if s["depth"] or "farmland" in s["top"]:
                return 0
            if s["top"] == "grass_block":
                return 2 if s["biome"] in ("forest", "birch_forest", "jungle", "bamboo_jungle", "taiga") else 1
            if s["top"] == "gravel" and s["sub"] == "cobblestone":
                return 6                                # gravel road (other gravel is terrain or sea floor)
            return {"podzol": 2, "coarse_dirt": 3, "dirt": 3, "mud": 3, "sand": 4,
                    "cobblestone": 5, "mossy_cobblestone": 5}.get(s["top"], 0)

        g = np.array([group(s) for s in styles], np.int8)[sid]
        n1, n2, n3, n4 = noise(24), noise(7), noise(11), noise(16)
        r, r2 = rng.random((n, n)), rng.random((n, n))
        top, deco, deco2 = self.top_id[:n, :n], self.deco[:n, :n], self.deco2[:n, :n]
        free = deco == AIR

        grass, forest, dirt, sand = g == 1, g == 2, g == 3, g == 4
        # ground blocks: worn and lush patches
        top[(grass | forest) & (n1 > 0.78) & (n2 > 0.55)] = B("coarse_dirt")
        top[grass & (n1 < 0.2) & (n2 < 0.45)] = B("moss_block")
        top[forest & (n2 > 0.7)] = B("podzol")
        top[dirt & (n2 > 0.72)] = B("rooted_dirt")
        top[dirt & (n2 < 0.2)] = B("dirt")
        # grass: denser in some places, tall grass in lush places, flower fields
        dens = 0.03 + 0.45 * np.clip((n2 - 0.35) / 0.5, 0, 1)
        tufts = grass & free & (r < dens)
        deco[tufts] = B("short_grass")
        tall = tufts & (n1 < 0.4) & (r2 < 0.3)
        deco[tall], deco2[tall] = B("tall_grass[half=lower]"), B("tall_grass[half=upper]")
        flowers = ["poppy", "dandelion", "cornflower", "oxeye_daisy", "azure_bluet", "allium", "red_tulip",
                   "white_tulip", "orange_tulip", "pink_tulip", "lily_of_the_valley"]
        kind = (n4 * len(flowers) * 3).astype(int) % len(flowers)          # one kind of flower per patch
        field = grass & free & (n3 > 0.8) & (r < 0.35)
        ids = np.array([B(f) for f in flowers], np.uint16)
        deco[field] = ids[kind[field]]
        petals = grass & free & (n3 < 0.1) & (r < 0.5)
        deco[petals] = B("pink_petals[facing=north,flower_amount=3]")
        # forest floor: ferns, moss, mushrooms
        floor = forest & free
        deco[floor & (r < 0.18)] = B("fern")
        big = floor & (r >= 0.18) & (r < 0.22)
        deco[big], deco2[big] = B("large_fern[half=lower]"), B("large_fern[half=upper]")
        deco[floor & (r >= 0.22) & (r < 0.24)] = B("brown_mushroom")
        deco[floor & (r >= 0.24) & (r < 0.25)] = B("red_mushroom")
        deco[floor & (r >= 0.25) & (r < 0.45) & (n2 > 0.6)] = B("moss_carpet")
        deco[floor & (r >= 0.45) & (r < 0.6)] = B("short_grass")
        def near(mask):                                 # 4 neighbors, no wrap-around at the map edge
            m = np.zeros_like(mask)
            m[1:] |= mask[:-1]; m[:-1] |= mask[1:]; m[:, 1:] |= mask[:, :-1]; m[:, :-1] |= mask[:, 1:]
            return m

        # roads: a mix of stones with worn patches, rough edges and worn verges next to the road
        road = g == 5
        if road.any():
            edge = road & near(~road)
            verge = ~road & near(road) & ((g == 1) | (g == 2) | (g == 3))
            stones = [("cobblestone", .34), ("andesite", .14), ("stone", .10), ("mossy_cobblestone", .10),
                      ("gravel", .08), ("tuff", .06), ("cracked_stone_bricks", .06), ("polished_andesite", .05),
                      ("coarse_dirt", .04), ("dirt_path", .03)]
            acc = 0.0
            for block, share in stones:
                top[road & (r >= acc) & (r < acc + share)] = B(block)
                acc += share
            worn = road & (n2 > 0.7)                                   # worn patches in the middle
            top[worn & (r2 < 0.35)] = B("gravel")
            top[worn & (r2 >= 0.35) & (r2 < 0.55)] = B("dirt_path")
            top[edge & (r2 < 0.30)] = B("dirt_path")                    # rough edges
            top[edge & (r2 >= 0.30) & (r2 < 0.45)] = B("coarse_dirt")
            top[verge & (r2 < 0.30)] = B("dirt_path")                   # worn verges beside the road
            top[verge & (r2 >= 0.30) & (r2 < 0.42)] = B("coarse_dirt")
            deco[edge & free & (r < 0.12)] = B("short_grass")
            deco[road & ~edge & free & (r2 > 0.97)] = B("short_grass")  # grass between the stones
            deco[verge & (top == B("dirt_path"))] = AIR                 # no plants on worn ground

        # gravel roads: some dirt and stones, and worn edges and verges
        road = g == 6
        top[road & (r < 0.15)] = B("coarse_dirt")
        top[road & (r >= 0.15) & (r < 0.22)] = B("cobblestone")
        top[road & (r >= 0.22) & (r < 0.3)] = B("dirt_path")
        land = (g > 0) & ~road
        edge = road & near(land)
        top[edge & (r2 < 0.35)] = B("dirt_path")
        top[edge & (r2 >= 0.35) & (r2 < 0.5)] = B("coarse_dirt")
        worn = land & near(road)
        top[worn & (r2 < 0.3)] = B("coarse_dirt")
        top[worn & (r2 >= 0.3) & (r2 < 0.45)] = B("dirt_path")
        deco[worn & (r2 < 0.45)] = AIR
        deco2[worn & (r2 < 0.45)] = AIR

        # dry ground (steppe): patches of dry grass, tufts, dead bushes
        steppe_grass = dirt & (top == B("coarse_dirt")) & (n1 < 0.3)
        top[steppe_grass] = B("grass_block")
        top[dirt & ~steppe_grass & (n3 > 0.75)] = B("dirt")
        deco[steppe_grass & free & (r < 0.30)] = B("short_grass")
        tall = steppe_grass & free & (r >= 0.30) & (r < 0.34)
        deco[tall], deco2[tall] = B("tall_grass[half=lower]"), B("tall_grass[half=upper]")
        deco[dirt & ~steppe_grass & free & (r < 0.02)] = B("dead_bush")
        deco[dirt & ~steppe_grass & free & (r >= 0.02) & (r < 0.10)] = B("short_grass")
        deco[sand & free & (r < 0.012)] = B("dead_bush")

    def outside(self):
        """Columns of one chunk outside the map (--border): no ground, the most common biome of the map."""
        c = object.__new__(Columns)
        c.n, c.width, c.floor = 0, 16, MIN_Y
        for k, v, dt in (("top", NONE, np.int16), ("wtop", NONE, np.int16), ("top_id", AIR, np.uint16),
                         ("sub_id", AIR, np.uint16), ("sub_depth", 3, np.int16), ("ice", False, bool),
                         ("deco", AIR, np.uint16), ("deco2", AIR, np.uint16), ("biome", 0, np.uint8)):
            setattr(c, k, np.full((16, 16), v, dt))
        c.biome_names = [self.biome_names[np.bincount(self.biome[:self.n, :self.n].ravel()).argmax()]]
        return c

    def inside(self, x, z):
        return 0 <= x < self.n and 0 <= z < self.n

    def surface(self, x, z):
        """Y of the first free block above the ground or the water."""
        x, z = min(max(x, 0), self.n - 1), min(max(z, 0), self.n - 1)
        return int(self.wtop[x, z]) + 1


# --------------------------------------------------------------------------------------------
# Edits: blocks for trees, mines and buildings, stored as numpy arrays.
# "soft" edits (leaves) go only into air. "hard" edits replace what is there.
# --------------------------------------------------------------------------------------------
# Connections of panes, iron bars, fences and walls (#189). Minecraft computes them only when a neighbour changes,
# so the converter writes them. The rules follow IronBarsBlock, FenceBlock and WallBlock.
SIDES = (("north", 0, -1), ("east", 1, 0), ("south", 0, 1), ("west", -1, 0))
NOT_STURDY = ("slab", "stairs", "fence", "_wall", "pane", "bars", "door", "banner", "torch", "lantern", "sign", "button",
              "lever", "plate", "carpet", "rail", "ladder", "vine", "chain", "rod", "campfire", "bell", "anvil",
              "cauldron", "flower", "short_grass", "tall_grass", "fern", "bush", "sapling", "leaves", "air", "water",
              "lava", "fire", "mushroom", "poppy", "dandelion", "orchid", "allium", "tulip", "daisy", "cornflower",
              "lily", "rose", "peony", "lilac", "sunflower", "kelp", "seagrass", "coral", "pickle", "candle", "head",
              "skull", "pot", "cake", "_bed", "chest", "lectern", "grindstone", "stonecutter", "enchanting", "dripstone",
              "cluster", "_bud", "cobweb", "sugar_cane", "bamboo", "cactus", "egg", "conduit", "hopper", "brewing",
              "farmland", "dirt_path", "scaffolding", "wheat", "carrots", "potatoes", "beetroots", "stem", "berry",
              "cocoa", "wart", "frogspawn", "roots", "sprouts", "hanging", "spore", "dripleaf", "azalea", "lichen",
              "vein", "tripwire", "redstone_wire", "repeater", "comparator", "daylight", "piston_head", "moving",
              "structure_void", "barrier", "pumpkin", "melon", "shulker", "composter", "heavy_core",
              "propagule", "petals", "snow", "turtle_egg", "end_portal", "nether_portal", "frame", "bubble", "fungus",
              "chorus_plant", "bluet", "glow_berries", "spawner", "end_gateway")
STURDY_PROPS = {"axis", "facing", "lit", "open", "snowy", "power", "triggered", "instrument", "note", "powered",
                "has_record", "honey_level", "up", "down", "north", "east", "south", "west", "charges", "orientation",
                "crafting", "extended", "bloom"}


def connect_kind(state):
    """'pane', 'fence', 'nether_fence', 'wall', 'gate_x' / 'gate_z' (axis of the gate), 'solid' or ''."""
    name = state.partition("[")[0]
    p = BLOCK_PROPS.get(name, {})
    if name.endswith("_fence_gate"):
        facing = re.search(r"facing=(\w+)", state)
        return "gate_z" if facing and facing.group(1) in ("north", "south") else "gate_x"
    if name.endswith("_pane") or name == "minecraft:iron_bars":
        return "pane"
    if name.endswith("_fence"):
        return "nether_fence" if name == "minecraft:nether_brick_fence" else "fence"
    if p.get("north") == ["none", "low", "tall"]:
        return "wall"
    short = name[10:]
    if any(k in short for k in ("torch", "banner", "sign")):
        return "post"                                                 # WALL_POST_OVERRIDE: a wall raises its post
    if short == "light" or any(k in short for k in NOT_STURDY) and not short.endswith(
            ("_block", "stone_bricks", "sea_lantern", "planks", "mosaic", "mushroom_stem")):
        return ""
    return "solid" if set(p) <= STURDY_PROPS else ""


def connected_state(state, me, sides, above):
    """State of a pane, fence or wall with the neighbour kinds of SIDES (north, east, south, west) and above."""
    name, _, props = state.partition("[")
    wet = "waterlogged=true" in props
    c = []
    for (d, _, _), k in zip(SIDES, sides):
        gate = k == ("gate_x" if d in ("north", "south") else "gate_z")    # a gate connects across its own axis
        if me == "pane":
            c.append(k in ("solid", "pane", "wall"))
        elif me in ("fence", "nether_fence"):
            c.append(k in ("solid", me) or gate)
        else:
            c.append(k in ("solid", "wall", "pane") or gate)
    w = ["true" if wet else "false"]
    if me != "wall":
        p = {d: "true" if v else "false" for (d, _, _), v in zip(SIDES, c)}
    else:
        tall = above in ("solid", "wall")
        p = {d: ("tall" if tall else "low") if v else "none" for (d, _, _), v in zip(SIDES, c)}
        n, e, s, wst = (p[d] for d in ("north", "east", "south", "west"))
        straight = (n == s) and (e == wst) and not (n == e == "none")
        up = above == "wall" or not straight or (not (n == s == "tall" or e == wst == "tall") and above in ("solid", "post"))
        p["up"] = "true" if up else "false"
    p["waterlogged"] = w[0]
    return f"{name}[{','.join(f'{k}={v}' for k, v in sorted(p.items()))}]"


class Edits:
    """Blocks of trees, mines, cliffs and buildings.

    footprint = (x0, x1, z0, z1): while it is set, a block outside this area is only kept when it is at
    least HEAD blocks above the ground of its column. Thus each object keeps the space next to it free for units.
    """
    HEAD = 3

    def __init__(self, cols=None):
        self.parts = []
        self.cols = cols
        self.footprint = None
        self.blocked = None      # block columns of buildings; natural objects place nothing there
        self.natural = False

    def add(self, xs, ys, zs, block, hard=True):
        xs, ys, zs = (np.asarray(a, np.int32).ravel() for a in (xs, ys, zs))
        ids = np.broadcast_to(np.asarray(block, np.uint16), xs.shape).copy() \
            if not isinstance(block, str) else np.full(xs.shape, B(block), np.uint16)
        if self.natural and self.blocked is not None and len(xs):
            n = self.blocked.shape[0]
            inside = (xs >= 0) & (zs >= 0) & (xs < n) & (zs < n)
            keep = ~inside.copy()
            keep[inside] = ~self.blocked[xs[inside], zs[inside]]
            xs, ys, zs, ids = xs[keep], ys[keep], zs[keep], ids[keep]
        if self.footprint is not None and self.cols is not None and len(xs):
            x0, x1, z0, z1 = self.footprint
            outside = (xs < x0) | (xs >= x1) | (zs < z0) | (zs >= z1)
            if outside.any():
                n = self.cols.n
                cx, cz = np.clip(xs, 0, n - 1), np.clip(zs, 0, n - 1)
                ground = self.cols.wtop[cx, cz].astype(np.int32)
                keep = ~outside | (ys >= ground + self.HEAD)
                xs, ys, zs, ids = xs[keep], ys[keep], zs[keep], ids[keep]
        self.parts.append((xs, ys, zs, ids, np.full(xs.shape, hard, bool)))

    def box(self, x0, x1, y0, y1, z0, z1, block, hard=True):
        """Fill the box x0..x1-1, y0..y1-1, z0..z1-1."""
        if x1 <= x0 or y1 <= y0 or z1 <= z0:
            return
        X, Y, Z = np.meshgrid(np.arange(x0, x1), np.arange(y0, y1), np.arange(z0, z1), indexing="ij")
        self.add(X, Y, Z, block, hard)

    def connect(self):
        """Set the connection states of panes, bars, fences and walls from their final neighbours (#189).
        Call it after all objects are placed. A position keeps its last hard block, else its first soft block;
        a neighbour without an edit is solid when it is in the ground of its column."""
        if not self.parts:
            return
        x, y, z, ids, hard = (np.concatenate(p) for p in zip(*self.parts))
        key = ((x.astype(np.int64) + 4096) << 40) | ((y.astype(np.int64) + 1024) << 20) | (z.astype(np.int64) + 4096)
        rank = np.where(hard, np.arange(len(key)) + len(key), len(key) - np.arange(len(key)))   # last hard, first soft
        order = np.lexsort((rank, key))
        last = np.r_[key[order][1:] != key[order][:-1], True]
        keys, fid, fhard = key[order][last], ids[order][last], hard[order][last]
        kinds = {}
        kind = lambda i: kinds.setdefault(int(i), connect_kind(B.states[int(i)]))
        uniq = np.unique(fid)
        conn = [int(i) for i in uniq if kind(i) in ("pane", "fence", "nether_fence", "wall")]
        if not conn:
            return
        sel = np.flatnonzero(np.isin(fid, conn))
        X, Y, Z = (keys[sel] >> 40) - 4096, ((keys[sel] >> 20) & 0xFFFFF) - 1024, (keys[sel] & 0xFFFFF) - 4096
        top = self.cols.top if self.cols is not None else None

        def at(dx, dy, dz):
            """Kind of the final block next to each selected block, with the direction for fence gates."""
            k = ((X + dx + 4096) << 40) | ((Y + dy + 1024) << 20) | (Z + dz + 4096)
            j = np.clip(np.searchsorted(keys, k), 0, len(keys) - 1)
            found = keys[j] == k
            out = np.full(len(k), "", object)
            for i in np.unique(fid[j[found]]):
                out[np.flatnonzero(found)[fid[j[found]] == i]] = kind(i)
            if top is not None:
                n = top.shape[0]
                nx, nz = np.clip(X + dx, 0, n - 1), np.clip(Z + dz, 0, n - 1)
                ground = ~found & (Y + dy <= top[nx, nz])
                out[ground] = "solid"
            return out

        side = {d: at(dx, 0, dz) for d, dx, dz in SIDES}
        above = at(0, 1, 0)
        new = np.empty(len(sel), np.uint16)
        cache = {}
        for n, i in enumerate(fid[sel]):
            me = kind(i)
            ks = tuple(side[d][n] for d, _, _ in SIDES)
            ck = (int(i), ks, above[n])
            if ck not in cache:
                cache[ck] = B(connected_state(B.states[int(i)], me, ks, above[n]))
            new[n] = cache[ck]
        self.parts.append((X.astype(np.int32), Y.astype(np.int32), Z.astype(np.int32), new, fhard[sel]))

    def by_chunk(self, width, lo=0):
        """Return {(cx, cz): (x, y, z, id, hard)} with local x/z, in the order of addition. x and z: lo..width-1."""
        if not self.parts:
            return {}
        x, y, z, ids, hard = (np.concatenate(p) for p in zip(*self.parts))
        ok = (x >= lo) & (z >= lo) & (x < width) & (z < width) & (y >= MIN_Y) & (y < MAX_Y)
        x, y, z, ids, hard = x[ok], y[ok], z[ok], ids[ok], hard[ok]
        key = ((x >> 4) + 1000) * 100000 + (z >> 4) + 1000
        order = np.argsort(key, kind="stable")
        x, y, z, ids, hard, key = x[order], y[order], z[order], ids[order], hard[order], key[order]
        keys, starts = np.unique(key, return_index=True)
        ends = list(starts[1:]) + [len(key)]
        out = {}
        for k, s, e in zip(keys, starts, ends):
            out[(int(k // 100000) - 1000, int(k % 100000) - 1000)] = (x[s:e] & 15, y[s:e], z[s:e] & 15, ids[s:e], hard[s:e])
        return out


# --------------------------------------------------------------------------------------------
# Trees
# --------------------------------------------------------------------------------------------
def tree_kind(n):
    if "BAMBOO" in n: return "bamboo"
    if "PINE" in n or "SPRUCE" in n or "CYPRESS" in n: return "spruce"
    if "BIRCH" in n: return "birch"
    if "PALM" in n: return "palm"
    if "ACACIA" in n or "BAOBAB" in n or "DRAGON" in n: return "acacia"
    if "MANGROVE" in n: return "mangrove"
    if "JUNGLE" in n or "RAINFOREST" in n: return "jungle"
    if "DEAD" in n or "STUMP" in n: return "dead"
    return "oak"


def leaves(wood):
    return f"{wood}_leaves[persistent=true]"


def make_tree(E, kind, x, y, z, rng):
    """Put one tree with its trunk base at (x, y, z)."""
    h = int(rng.integers(4, 7))
    if kind == "bamboo":
        for _ in range(3):
            dx, dz = rng.integers(-1, 2, 2)
            E.box(x + dx, x + dx + 1, y, y + int(rng.integers(6, 11)), z + dz, z + dz + 1,
                  "bamboo[leaves=large]")
        return
    if kind == "dead":
        E.box(x, x + 1, y, y + h - 1, z, z + 1, "oak_log")
        E.add([x + 1, x - 1], [y + h - 2, y + h - 3], [z, z], "oak_log[axis=x]")
        return
    wood = {"palm": "jungle", "jungle": "jungle", "acacia": "acacia", "spruce": "spruce",
            "birch": "birch", "mangrove": "mangrove"}.get(kind, "oak")
    log, leaf = f"{wood}_log", leaves(wood)
    if kind == "spruce":
        h += 2
        for i, dy in enumerate(range(2, h + 1)):
            r = 0 if dy == h else (2 if (h - dy) % 2 == 0 and dy < h - 2 else 1)
            disc(E, x, y + dy, z, r, leaf)
        E.box(x, x + 1, y, y + h, z, z + 1, log)
    elif kind == "acacia":
        disc(E, x, y + h, z, 2, leaf)
        disc(E, x, y + h + 1, z, 1, leaf)
        E.box(x, x + 1, y, y + h, z, z + 1, log)
    elif kind == "palm":
        h += 2
        E.box(x, x + 1, y, y + h, z, z + 1, log)
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            E.add([x + dx, x + 2 * dx, x + 3 * dx], [y + h, y + h, y + h - 1],
                  [z + dz, z + 2 * dz, z + 3 * dz], leaf, hard=False)
        E.add([x], [y + h], [z], leaf, hard=False)
    else:  # round trees: oak, birch, jungle, mangrove
        if kind == "jungle":
            h += 3
        for dy, r in ((h - 2, 2), (h - 1, 2), (h, 1), (h + 1, 1)):
            disc(E, x, y + dy, z, r, leaf)
        E.box(x, x + 1, y, y + h, z, z + 1, log)


def disc(E, x, y, z, r, block):
    """Leaves in a flat square of radius r without the corners."""
    if r == 0:
        E.add([x], [y], [z], block, hard=False)
        return
    d = np.arange(-r, r + 1)
    DX, DZ = np.meshgrid(d, d, indexing="ij")
    keep = ~((np.abs(DX) == r) & (np.abs(DZ) == r))
    E.add(x + DX[keep], np.full(keep.sum(), y), z + DZ[keep], block, hard=False)


# --------------------------------------------------------------------------------------------
# Mines, rocks, cliffs, bushes, flags, relics
# --------------------------------------------------------------------------------------------
def mound(E, cols, cx, cz, radius, height, blocks, rng):
    """A round heap of mixed blocks on the ground."""
    r = int(np.ceil(radius))
    for dx in range(-r, r + 1):
        for dz in range(-r, r + 1):
            d = (dx * dx + dz * dz) ** 0.5 / max(radius, 0.5)
            if d > 1 or not cols.inside(cx + dx, cz + dz):
                continue
            h = max(1, int(round(height * (1 - d * d) + rng.random() * 0.8)))
            y0 = cols.surface(cx + dx, cz + dz)
            for dy in range(h):
                E.add([cx + dx], [y0 + dy], [cz + dz], blocks[int(rng.integers(len(blocks)))])


def tile_heap(E, cols, rect, height, blocks, rng):
    """A heap of mixed blocks that covers its whole footprint, highest in the middle."""
    x0, x1, z0, z1 = rect
    cx, cz, hx, hz = (x0 + x1 - 1) / 2, (z0 + z1 - 1) / 2, max((x1 - x0) / 2, 1), max((z1 - z0) / 2, 1)
    for x in range(max(0, x0), min(cols.n, x1)):
        for z in range(max(0, z0), min(cols.n, z1)):
            d = max(abs(x - cx) / hx, abs(z - cz) / hz)
            h = max(1, int(round(1 + (height - 1) * (1 - d * d) + rng.random() * 0.7)))
            y0 = cols.surface(x, z)
            for dy in range(h):
                E.add([x], [y0 + dy], [z], blocks[int(rng.integers(len(blocks)))])


def decor(E, cols, name, rect, rng):
    """Small decorative AoE2 objects (statues, stalls, wells, hay, barrels ...). Returns False if unknown."""
    x0, x1, z0, z1 = rect
    cx, cz = (x0 + x1) // 2, (z0 + z1) // 2
    y = cols.surface(cx, cz)
    put = lambda dx, dy, dz, b: E.add([cx + dx], [y + dy], [cz + dz], b)
    pick = lambda opts: opts[int(rng.integers(len(opts)))]
    n = name
    if n.startswith(("STATUE", "TROPAION", "STELAE", "HERO_SHRINE")):
        E.box(cx - 1, cx + 1, y, y + 1, cz - 1, cz + 1, "polished_andesite")
        h = 5 if "COLUMN" in n else 3
        for dy in range(1, h):
            put(0, dy, 0, "quartz_pillar" if "COLUMN" in n else "chiseled_quartz_block" if dy == 1 else "smooth_quartz")
        put(0, h, 0, pick(["end_rod", "lightning_rod", "smooth_quartz_slab[type=bottom]"]))
    elif "THOLOS" in n or "SHRINE" in n:
        for dx, dz in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            for dy in range(1, 4):
                put(dx, dy, dz, "quartz_pillar")
        E.box(cx - 1, cx + 2, y + 4, y + 5, cz - 1, cz + 2, "smooth_quartz_slab[type=bottom]")
        put(0, 1, 0, "chiseled_quartz_block")
    elif "MARKET_STALL" in n or "GOODS" in n:
        for dx, dz in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            put(dx, 1, dz, "oak_fence"); put(dx, 2, dz, "oak_fence")
        wool = pick(["red", "yellow", "blue", "green", "orange", "white"])
        E.box(cx - 1, cx + 2, y + 3, y + 4, cz - 1, cz + 2, f"{wool}_wool")
        put(0, 1, 0, pick(["barrel[facing=up]", "melon", "pumpkin", "hay_block", "chest[facing=south]"]))
        put(1, 1, 0, pick(["barrel[facing=up]", "composter", "decorated_pot[facing=south,cracked=false]"]))
    elif n == "WELL":
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                if dx or dz:
                    put(dx, 0, dz, "cobblestone"); put(dx, 1, dz, "cobblestone_wall")
        put(0, 0, 0, "water[level=0]")
        put(-1, 2, 0, "oak_fence"); put(1, 2, 0, "oak_fence")
        E.box(cx - 1, cx + 2, y + 3, y + 4, cz, cz + 1, "spruce_slab[type=bottom]")
    elif "HAY_STACK" in n:
        E.box(cx - 1, cx + 1, y, y + 2, cz - 1, cz + 1, "hay_block"); put(0, 2, 0, "hay_block")
    elif "LUMBER" in n or "SIEGE" in n:
        E.box(cx - 1, cx + 2, y, y + 1, cz, cz + 1, "oak_log[axis=x]"); put(0, 1, 0, "oak_log[axis=x]")
        if "SIEGE" in n:
            put(-1, 0, 1, "barrel[facing=up]"); put(1, 0, -1, "chain")
    elif "BARREL" in n:
        for dx, dz in ((0, 0), (1, 0), (0, 1)):
            put(dx, 0, dz, "barrel[facing=up]")
        put(0, 1, 0, "barrel[facing=up]")
    elif "WEAPON" in n:
        put(0, 0, 0, "grindstone[face=floor,facing=north]"); put(1, 0, 0, "anvil[facing=east]")
        put(-1, 0, 0, "oak_fence"); put(-1, 1, 0, "lightning_rod")
    elif "TARGET" in n:
        put(0, 0, 0, "hay_block"); put(0, 1, 0, "target")
    elif "RUG" in n:
        E.box(cx - 1, cx + 1, y, y + 1, cz - 1, cz + 1, f"{pick(['red', 'orange', 'purple', 'cyan'])}_carpet")
    elif "VASE" in n:
        put(0, 0, 0, "decorated_pot[facing=south,cracked=false]"); put(1, 0, 0, "flower_pot")
    elif "FLOWER" in n:
        for dx in range(-1, 2):
            for dz in range(-1, 2):
                if rng.random() < 0.8:
                    E.add([cx + dx], [cols.surface(cx + dx, cz + dz)], [cz + dz],
                          pick(["poppy", "dandelion", "allium", "azure_bluet", "red_tulip", "oxeye_daisy"]), hard=False)
    elif "FERN" in n:
        for dx in range(-1, 2):
            for dz in range(-1, 2):
                if rng.random() < 0.7:
                    E.add([cx + dx], [cols.surface(cx + dx, cz + dz)], [cz + dz], "fern", hard=False)
    elif "HEDGE" in n or "GRAPEVINE" in n:
        for x in range(x0, x1):
            for z in range(z0, z1):
                yy = cols.surface(x, z)
                if "HEDGE" in n:
                    E.add([x, x], [yy, yy + 1], [z, z], "oak_leaves[persistent=true]")
                elif (x + z) % 2 == 0:
                    E.add([x, x], [yy, yy + 1], [z, z], [B("oak_fence"), B("azalea_leaves[persistent=true]")])
    elif "BROKEN_CART" in n:
        put(0, 0, 0, "spruce_slab[type=bottom]"); put(1, 0, 0, "spruce_slab[type=bottom]")
        put(-1, 0, 0, "spruce_trapdoor[facing=east,half=bottom,open=true]"); put(0, 1, 0, "barrel[facing=east]")
    elif "BONFIRE" in n or n.startswith(("FLAME", "FLARE")):     # a flare is a signal: tall smoke
        put(0, 0, 0, f"campfire[lit=true,signal_fire={str(n.startswith('FLARE')).lower()}]")
    elif "STUMP" in n:
        put(0, 0, 0, "stripped_bamboo_block[axis=y]" if "BAMBOO" in n else "spruce_log[axis=y]")
    elif n.startswith(("PATH_", "BLACK_TILE")):        # flat: a path in the ground, black carpet on it
        for x in range(x0, x1):
            for z in range(z0, z1):
                yy = cols.surface(x, z)
                if n == "BLACK_TILE":
                    E.add([x], [yy], [z], "black_carpet", hard=False)
                elif rng.random() < 0.8 and yy - 1 == cols.top[min(max(x, 0), cols.n - 1), min(max(z, 0), cols.n - 1)]:
                    E.add([x], [yy - 1], [z], "dirt_path")
    elif n in ("HEAD", "IMPALED_CORPSE"):
        h = 2 if n == "IMPALED_CORPSE" else 0
        for dy in range(h):
            put(0, dy, 0, "spruce_fence")
        put(0, h, 0, "skeleton_skull[rotation=8]")
        if h:
            put(1, 0, 0, "bone_block[axis=x]")
    elif n in ("TREASURE_CHEST", "LOOT"):
        put(0, 0, 0, "chest[facing=south]" if n == "TREASURE_CHEST" else "barrel[facing=up]")
        put(1, 0, 0, "gold_block" if n == "TREASURE_CHEST" else "raw_gold_block")
    elif n == "LEATHERWORKING_EQUIPMENT":
        put(0, 0, 0, "loom[facing=south]"); put(1, 0, 0, "spruce_fence"); put(1, 1, 0, "brown_carpet")
    elif n in ("ARCHAIC_FENCE", "STAKE_BARRICADE"):
        for x in range(x0, x1):
            yy = cols.surface(x, cz)
            if n == "ARCHAIC_FENCE":
                E.add([x], [yy], [cz], f"oak_fence[east={str(x < x1 - 1).lower()},west={str(x > x0).lower()}]")
            else:                                      # single sharp stakes of two heights
                E.box(x, x + 1, yy, yy + 1 + (x % 2), cz, cz + 1, "spruce_fence")
    elif n == "PIECE_OF_THE_TRUE_CROSS":
        put(0, 0, 0, "dark_oak_fence"); put(0, 2, 0, "dark_oak_fence")
        put(0, 1, 0, "dark_oak_fence[east=true,west=true]")
        put(-1, 1, 0, "dark_oak_fence[east=true]"); put(1, 1, 0, "dark_oak_fence[west=true]")
    elif n == "ICE_NAVIGABLE":
        for x in range(x0, x1):
            for z in range(z0, z1):
                E.add([x], [cols.surface(x, z) - 1], [z], "ice")
    elif n == "SIGN":
        put(0, 0, 0, "oak_sign[rotation=8]")
    elif "GALLOW" in n:
        put(-1, 0, 0, "dark_oak_fence"); put(-1, 1, 0, "dark_oak_fence"); put(-1, 2, 0, "dark_oak_fence")
        E.box(cx - 1, cx + 2, y + 3, y + 4, cz, cz + 1, "dark_oak_log[axis=x]"); put(1, 2, 0, "chain")
    elif "OYSTER" in n:
        x, z = min(max(cx, 0), cols.n - 1), min(max(cz, 0), cols.n - 1)
        if cols.wtop[x, z] > cols.top[x, z]:
            E.add([x], [int(cols.top[x, z]) + 1], [z], "sea_pickle[pickles=3]")
    elif n.startswith(("DRIFTWOOD", "FLOTSAM")):      # in water: at the water level, so that it floats half under
        x, z = min(max(cx, 0), cols.n - 1), min(max(cz, 0), cols.n - 1)
        wet = cols.wtop[x, z] > cols.top[x, z]
        yy = int(cols.wtop[x, z]) if wet else y
        if n == "FLOTSAM":
            E.add([cx, cx + 1, cx - 1], [yy] * 3, [cz, cz, cz - 1],
                  [B("spruce_slab[type=top]"), B("barrel[facing=up]" if wet else "spruce_slab[type=bottom]"),
                   B("spruce_trapdoor[facing=north,half=top,open=false]")])
        else:
            E.add([cx - 1, cx, cx + 1], [yy] * 3, [cz] * 3, "stripped_oak_log[axis=x]")
            put(0, yy - y, 1, "stripped_birch_log[axis=z]")
    elif n == "KELP_SEAWEEDS" or n == "WATER_LILY":
        for x in range(max(0, x0), min(cols.n, x1)):
            for z in range(max(0, z0), min(cols.n, z1)):
                floor, top = int(cols.top[x, z]), int(cols.wtop[x, z])
                if top <= floor or rng.random() > 0.6:
                    continue
                if n == "WATER_LILY":
                    E.add([x], [top + 1], [z], "lily_pad", hard=False)
                elif top - floor < 2:
                    E.add([x], [floor + 1], [z], "seagrass", hard=False)
                else:                                  # a kelp column of random height, at most up to the surface
                    h = int(rng.integers(1, top - floor + 1))
                    E.add([x] * h, list(range(floor + 1, floor + h + 1)), [z] * h,
                          [B("kelp_plant")] * (h - 1) + [B("kelp[age=25]")], hard=False)
    elif n == "BEACHED_WHALE":                        # a skeleton: spine, ribs and skull of bone blocks
        for dx in range(-2, 2):
            put(dx, 1, 0, "bone_block[axis=x]")
            if dx > -2:
                for dz in (-1, 1):
                    put(dx, 0, dz, "bone_block[axis=y]")
        put(-2, 0, 0, "bone_block[axis=x]")
    elif n == "SMALL_WATERFALL":                      # a water source on a rock step falls down its east side
        for dx, dz, h in ((0, 0, 2), (-1, 0, 3), (0, -1, 3), (-1, -1, 3), (1, -1, 2), (-1, 1, 2), (0, 1, 1)):
            E.box(cx + dx, cx + dx + 1, y, y + h, cz + dz, cz + dz + 1,
                  "mossy_cobblestone" if (dx + dz) % 2 else "stone")
        put(0, 2, 0, "water[level=0]"); put(1, 2, 0, "water[level=1]")
        put(1, 1, 0, "water[level=8]"); put(1, 0, 0, "water[level=8]")
    elif n.startswith("FALLEN_LEAVES"):               # flat ground cover on land
        leaves = (["pink_petals[facing=north,flower_amount=4]", "pink_petals[facing=east,flower_amount=2]",
                   "pink_petals[facing=south,flower_amount=3]"] if "PEACH" in n else
                  ["orange_carpet", "red_carpet", "yellow_carpet", "brown_carpet"] if "AUTUMN" in n else
                  ["moss_carpet", "moss_carpet", "lime_carpet"])
        for x in range(max(0, x0), min(cols.n, x1)):
            for z in range(max(0, z0), min(cols.n, z1)):
                if cols.wtop[x, z] == cols.top[x, z] and rng.random() < 0.6:
                    E.add([x], [cols.surface(x, z)], [z], pick(leaves), hard=False)
    elif chinese_garden(E, n, rect, y, put):
        pass
    else:
        return False
    return True


def chinese_garden(E, n, rect, y, put):
    """Chinese garden objects (#294): red wood, white stone and dark tile roofs. Returns False if unknown."""
    x0, x1, z0, z1 = rect
    W, cz = x1 - x0, (z0 + z1) // 2
    i = 1 if W >= 6 else 0                              # inset of posts in a large footprint

    def roof(a0, a1, b0, b1, yy):                      # stepped tile roof that ends in a ridge
        for k in range(max(1, (min(a1 - a0, b1 - b0) + 1) // 2)):
            E.box(a0 + k, a1 - k, yy + k, yy + k + 1, b0 + k, b1 - k, "deepslate_tile_slab[type=bottom]")
        return yy + k + 1

    if n == "PAPER_LANTERN":                            # a glowing paper lantern hangs from a post
        for dy in range(3):
            put(0, dy, 0, "dark_oak_fence")
        put(1, 2, 0, "dark_oak_fence"); put(1, 1, 0, "shroomlight")
    elif n == "ASIAN_LANTERNS":                         # a row of stone lanterns (toro)
        for x in range(x0 + (W > 2), max(x0 + 1, x1 - (W > 2)), 2):
            E.add([x] * 3, [y, y + 1, y + 2], [cz] * 3,
                  [B("stone_brick_wall"), B("lantern[hanging=false]"), B("stone_brick_slab[type=bottom]")])
    elif n == "HUABIAO_TOTEM":                          # white marble column with a cloud board near the top
        E.box(x0 + (W > 2), x1 - (W > 2), y, y + 1, z0 + (W > 2), z1 - (W > 2), "polished_diorite")
        for dy in range(1, 6):
            put(0, dy, 0, "chiseled_quartz_block" if dy == 5 else "quartz_pillar")
        put(-1, 4, 0, "smooth_quartz_slab[type=top]"); put(1, 4, 0, "smooth_quartz_slab[type=top]")
        put(0, 6, 0, "smooth_quartz_slab[type=bottom]")
    elif n.startswith("PAIFANG_GATE"):                  # red posts, beams and tile roofs along x
        large = n.endswith("LARGE")
        a, b, H = x0 + (W >= 4), x1 - 1 - (W >= 4), 5 if large else 4
        k = (b - a) // 3 if large else 0
        for x in sorted({a, b, a + k, b - k}):
            E.add([x], [y], [cz], "polished_blackstone")
            E.box(x, x + 1, y + 1, y + H, cz, cz + 1, "red_concrete")
        E.box(a, b + 1, y + H - 1, y + H, cz, cz + 1, "red_concrete")
        for r0, r1, yy in ((a, b, y + H), (a + k, b - k, y + H + 1)) if large else ((a, b, y + H),):
            E.box(r0, r1 + 1, yy, yy + 1, cz - 1, cz, "deepslate_tile_stairs[facing=south,half=bottom,shape=straight]")
            E.box(r0, r1 + 1, yy, yy + 1, cz + 1, cz + 2, "deepslate_tile_stairs[facing=north,half=bottom,shape=straight]")
            E.box(r0, r1 + 1, yy, yy + 1, cz, cz + 1, "deepslate_tile_slab[type=double]")
        if large:
            E.box(a + k + 1, b - k, y + H - 2, y + H - 1, cz, cz + 1, "gold_block")    # name board
    elif n == "GARDEN_PAVILION":                        # open pavilion: four red posts, a floor and a tile roof
        E.box(x0 + i, x1 - i, y, y + 1, z0 + i, z1 - i, "smooth_stone_slab[type=bottom]")
        for x, z in ((x0 + i, z0 + i), (x1 - 1 - i, z0 + i), (x0 + i, z1 - 1 - i), (x1 - 1 - i, z1 - 1 - i)):
            E.box(x, x + 1, y, y + 3, z, z + 1, "stripped_mangrove_log[axis=y]")
        top = roof(x0, x1, z0, z1, y + 3)
        put(0, top - y, 0, "lightning_rod"); put(0, 2, 0, "lantern[hanging=true]")
    elif n == "QUE_TOWER":                              # tall brick tower with a small pavilion on top
        H = max(4, W)
        E.box(x0 + i, x1 - i, y, y + H, z0 + i, z1 - i, "stone_bricks")
        E.box(x0 + i, x1 - i, y + H - 1, y + H, z0 + i, z1 - i, "polished_andesite")
        j = i + (W >= 4)
        for x, z in ((x0 + j, z0 + j), (x1 - 1 - j, z0 + j), (x0 + j, z1 - 1 - j), (x1 - 1 - j, z1 - 1 - j)):
            E.box(x, x + 1, y + H, y + H + 2, z, z + 1, "stripped_mangrove_log[axis=y]")
        roof(x0, x1, z0, z1, y + H + 2)
    elif n == "GARDEN_BRIDGE":                          # red arched bridge along x: deck of half steps, rails
        for x in range(x0, x1):
            h = min(x - x0, x1 - 1 - x, 3)
            yy = y + h // 2
            E.box(x, x + 1, yy, yy + 1, z0 + i, z1 - i, f"spruce_slab[type={'top' if h % 2 else 'bottom'}]")
            for z in {z0 + i, z1 - 1 - i}:              # on a top slab, else in place of the low slab
                E.add([x], [yy + h % 2], [z], "mangrove_fence")
    else:
        return False
    return True


def cliff_ridges(E, cols, rects, rng):
    """All cliffs together form continuous rock ridges: high in the middle, sloped at the open sides."""
    if not rects:
        return
    n, T = cols.n, cols.T
    mask = np.zeros((n, n), bool)
    for x0, x1, z0, z1 in rects:
        mask[max(0, x0):max(0, min(n, x1)), max(0, z0):max(0, min(n, z1))] = True
    dist = np.zeros((n, n), np.int16)
    cur = mask.copy()
    for k in range(1, T + 2):                          # distance to the edge of the ridge
        dist[cur] = k
        inner = cur.copy()
        inner[1:] &= cur[:-1]; inner[:-1] &= cur[1:]; inner[:, 1:] &= cur[:, :-1]; inner[:, :-1] &= cur[:, 1:]
        cur = inner
    height = np.minimum(2 * T, 2 * dist - 1 + (rng.random((n, n)) < 0.5)) * mask
    xs, zs = np.nonzero(height)
    hs = height[xs, zs]
    base = cols.wtop[xs, zs].astype(np.int32) + 1
    X, Z = np.repeat(xs, hs), np.repeat(zs, hs)
    Y = np.repeat(base, hs) + (np.arange(hs.sum()) - np.repeat(np.cumsum(hs) - hs, hs))
    rocks = np.array([B(b) for b in ("stone", "stone", "andesite", "andesite", "tuff", "cobblestone", "stone", "mossy_cobblestone")], np.uint16)
    E.add(X, Y, Z, rocks[rng.integers(len(rocks), size=len(X))])
    snowy = cols.top_id[xs, zs] == B("snow_block")         # snow on top of ridges in snow areas
    if snowy.any():
        E.add(xs[snowy], (base + hs)[snowy], zs[snowy], "snow[layers=2]")


def obstacle(E, cols, rect, height=3):
    """Barrier blocks over the footprint of a tree, mine, bush or cliff: like in AoE2, units cannot walk through."""
    x0, x1, z0, z1 = rect
    cols.blocked[max(0, x0):max(0, x1), max(0, z0):max(0, z1)] = True
    if not buildings.BARRIERS:
        return
    for x in range(max(0, x0), min(cols.n, x1)):
        for z in range(max(0, z0), min(cols.n, z1)):
            y = cols.surface(x, z)
            E.add([x] * height, list(range(y, y + height)), [z] * height, "barrier", hard=False)


def player_color(p, players=None):
    if players and p in players:
        return players[p]["color"]
    return PLAYER_COLORS[p] if 0 <= p < len(PLAYER_COLORS) else "white"


# --------------------------------------------------------------------------------------------
# Place all objects of the scenario.
# --------------------------------------------------------------------------------------------
MOUNTAINS = ("MOUNTAIN", "SNOW_MOUNTAIN")
MONUMENTS = ("BUDDHA_STATUE", "INDIAN_STATUES", "OLD_STONE_HEAD", "NINE_BANDS", "PAGODA_", "TORII_GATE", "STUPA",
             "TROWULAN_GATE", "REKHA_DEUL_TEMPLE", "SVAN_TOWER", "MEDITERRANEAN_COURTYARD_WALLS",
             "MESOPOTAMIAN_PILLAR", "MESOPOTAMIAN_GARDEN", "MESOPOTAMIAN_TOMB", "BURNED_BUILDING")    # buildings.py designs
PASSABLE_OBJECTS = ("FLOWER", "FERN", "RUG", "GRASS", "PLANT", "OYSTER", "FISH", "RELIC", "GRAVE", "BONFIRE",
                    "PATH_", "BLACK_TILE", "ICE_NAVIGABLE", "DOLPHIN", "BOX_TURTLES", "KELP", "WATER_LILY",
                    "FALLEN_LEAVES")


def object_footprint(o, T):
    """Block area (x0, x1, z0, z1) of a non-building object. An object at x.0 has an even size, at x.5 an odd size."""
    n = o["name"]
    big = 4 if n.startswith(MOUNTAINS) else 3 if n.startswith("CLIFF") or "QUARRY" in n or "TEMPLE" in n else 0

    def axis(v):
        even = abs(v % 1) < 0.25
        size = (big - (1 if big and not even and big % 2 == 0 else 0) - (1 if big and even and big % 2 else 0)) \
            if big else (2 if even else 1)
        return int(round((v - size / 2) * T)), int(round((v + size / 2) * T))
    (x0, x1), (z0, z1) = axis(o["x"]), axis(o["y"])
    return x0, x1, z0, z1


def place_objects(objects, players, cols, rng):
    E = Edits(cols)
    T = cols.T
    stats = Counter()
    walls, gates = buildings.plan_walls(objects)
    cliffs = []
    objects, hidden = buildings.drop_covered(objects)
    if hidden:
        stats["buildings hidden under a larger building"] = hidden
    E.blocked = buildings.footprint_mask(objects, cols)
    objects = sorted(objects, key=lambda o: o["kind"] == "B")      # buildings last: they win
    for o in objects:
        name, kind = o["name"], o["kind"]
        bx, bz = int(o["x"] * T), int(o["y"] * T)
        if not cols.inside(bx, bz):
            continue
        y = cols.surface(bx, bz)
        E.footprint = object_footprint(o, T) if kind == "O" else None
        E.natural = kind == "O" and "PYRAMID" not in name
        if kind == "B" and name == "RUINS":
            for i in range(3 * T):
                dx, dz = rng.integers(-T - 1, T + 2, 2)
                if cols.inside(bx + dx, bz + dz):
                    yy = cols.surface(bx + dx, bz + dz)
                    E.box(bx + dx, bx + dx + 1, yy, yy + int(rng.integers(1, 4)), bz + dz, bz + dz + 1,
                          ["mossy_stone_bricks", "cracked_stone_bricks", "sandstone", "mossy_cobblestone"][i % 4], hard=False)
            stats["ruins"] += 1
        elif kind == "B":
            buildings.place_building(E, cols, B, o, players, walls, gates)
            stats["buildings"] += 1
        elif kind == "O" and name.startswith(MONUMENTS):
            buildings.place_building(E, cols, B, dict(o, kind="B"), players, set(), {})
            stats["monuments"] += 1
        elif kind == "O" and "TREE" in name:
            make_tree(E, tree_kind(name), bx, y, bz, rng)
            stats["trees"] += 1
        elif kind == "O" and name == "GOLD_MINE":
            tile_heap(E, cols, E.footprint, 3, ["gold_ore", "gold_ore", "raw_gold_block", "stone"], rng)
            stats["gold mines"] += 1
        elif kind == "O" and name == "STONE_MINE":
            tile_heap(E, cols, E.footprint, 3, ["cobblestone", "andesite", "stone", "tuff"], rng)
            stats["stone mines"] += 1
        elif kind == "O" and name.startswith(MOUNTAINS):
            mound(E, cols, bx, bz, T * 2, T * 4, ["stone", "snow_block", "andesite", "snow_block", "packed_ice"]
                  if name.startswith("SNOW") else ["stone", "stone", "andesite", "cobblestone", "tuff"], rng)
            for dx, dz in ((0, 0), (1, 0), (0, 1), (1, 1)):
                if cols.inside(bx + dx, bz + dz):
                    top = max(cols.surface(bx + dx, bz + dz), y) + T * 4
                    E.add([bx + dx], [top], [bz + dz], "snow_block")
            stats["mountains"] += 1
        elif kind == "O" and name == "QUARRY":
            mound(E, cols, bx, bz, T * 1.5, 3, ["stone", "cobblestone", "andesite"], rng)
            stats["rocks"] += 1
        elif kind == "O" and name == "GRAVE":
            E.add([bx, bx], [y, y + 1], [bz, bz], [B("mossy_cobblestone_wall"), B("stone_button[face=floor]")])
            stats["graves"] += 1
        elif kind == "O" and "RUIN" in name:
            for i in range(max(3, T)):
                dx, dz = rng.integers(-T, T + 1, 2)
                if cols.inside(bx + dx, bz + dz):
                    yy = cols.surface(bx + dx, bz + dz)
                    E.box(bx + dx, bx + dx + 1, yy, yy + int(rng.integers(1, 5)), bz + dz, bz + dz + 1,
                          ["mossy_stone_bricks", "cracked_stone_bricks", "quartz_pillar"][i % 3])
            stats["ruins"] += 1
        elif kind == "O" and "SHIPWRECK" in name:
            E.box(bx - 2, bx + 3, y, y + 1, bz - 1, bz + 1, "dark_oak_planks")
            E.box(bx, bx + 1, y + 1, y + 4, bz, bz + 1, "dark_oak_log")
            stats["shipwrecks"] += 1
        elif kind == "O" and decor(E, cols, name, E.footprint, rng):
            stats["decorations"] += 1
        elif kind == "O" and name == "CHAPEL":
            buildings.place_building(E, cols, B, dict(o, kind="B", name="CHAPEL"), players, set(), {})
            stats["buildings"] += 1
        elif kind == "O" and name == "GRANARY":
            buildings.place_building(E, cols, B, dict(o, kind="B", name="MILL_GRANARY"), players | {o["player"]: dict(players.get(o["player"], {"color": "light_gray", "arch": "western"}), arch="middle_eastern")}, set(), {})
            stats["buildings"] += 1
        elif kind == "O" and name.startswith("CLIFF"):
            cliffs.append(E.footprint)
            stats["cliffs"] += 1
        elif kind == "O" and "PYRAMID" in name:
            buildings.place_building(E, cols, B, dict(o, kind="B", x=int(o["x"]) + 0.5, y=int(o["y"]) + 0.5),
                                     players, set(), {})
            stats["buildings"] += 1
        elif kind == "O" and name.startswith("ROCK_FORMATION"):
            tile_heap(E, cols, E.footprint, T, ["stone", "andesite", "granite", "sandstone", "stone"], rng)
            stats["rocks"] += 1
        elif kind == "O" and name == "CACTUS":
            E.box(bx, bx + 1, y, y + 2, bz, bz + 1, "cactus")
            stats["plants"] += 1
        elif kind == "O" and name.startswith("PLANT"):
            plant = "fern" if ("FERN" in name or "JUNGLE" in name or "UNDERBRUSH" in name) else \
                "oak_leaves[persistent=true]" if ("SHRUB" in name or "BUSH" in name) else \
                ["poppy", "dandelion", "cornflower", "allium"][int(rng.integers(4))] if "FLOWER" in name else \
                "dead_bush" if "DEAD" in name else "short_grass"
            E.add([bx], [y], [bz], plant, hard=False)
            stats["plants"] += 1
        elif kind == "O" and (name.startswith("RUBBLE") or "SKELETON" in name or name in ("LUMBER", "FLOWER_BED")
                              or "CART" in name or name.startswith("TORCH") or name == "SIGN"):
            things = (["cobblestone", "gravel", "mossy_cobblestone"] if name.startswith("RUBBLE") else
                      ["bone_block[axis=x]", "bone_block[axis=z]"] if "SKELETON" in name else
                      ["oak_log[axis=x]", "oak_log[axis=x]", "spruce_log[axis=x]"] if name == "LUMBER" else
                      ["poppy", "dandelion", "allium", "azure_bluet"] if name == "FLOWER_BED" else
                      ["spruce_slab[type=bottom]", "spruce_log[axis=z]", "barrel[facing=up]"] if "CART" in name else
                      ["oak_fence"])
            k = 1 if things == ["oak_fence"] else min(len(things), 3)
            E.add([bx, bx + 1, bx][:k], [y] * k, [bz, bz, bz + 1][:k],
                  [B(things[int(rng.integers(len(things)))]) for _ in range(k)], hard=not name == "FLOWER_BED")
            if name.startswith("TORCH") or name == "SIGN":
                E.add([bx], [y + 1], [bz], "torch" if name.startswith("TORCH") else "oak_fence")
            stats["decorations"] += 1
        elif kind == "O" and (name in ("CRATER", "SMOKE", "CRACKS") or name.startswith("WATERFALL")):
            pass
        elif kind == "O" and "ROCK" in name:
            mound(E, cols, bx, bz, T * 0.4, 2, ["mossy_cobblestone", "cobblestone", "stone"], rng)
            stats["rocks"] += 1
        elif kind == "O" and ("FORAGE" in name or "FRUIT_BUSH" in name):
            for dx, dz in ((0, 0), (1, 0), (0, 1)):
                if cols.inside(bx + dx, bz + dz):
                    E.add([bx + dx], [cols.surface(bx + dx, bz + dz)], [bz + dz], "sweet_berry_bush[age=3]")
            stats["berry bushes"] += 1
        elif kind == "O" and "RELIC" in name:
            E.add([bx], [y], [bz], "decorated_pot[facing=south,cracked=false]")
            stats["relics"] += 1
        elif kind == "O" and "FLAG" in name:
            E.box(bx, bx + 1, y, y + 3, bz, bz + 1, "oak_fence")
            E.add([bx], [y + 3], [bz], f"{player_color(o['player'], players)}_wool")
            stats["flags"] += 1
        elif kind == "O" and name.startswith("BUSH"):
            E.add([bx, bx + 1, bx], [y, y, y + 1], [bz, bz, bz], "oak_leaves[persistent=true]", hard=False)
            stats["plants"] += 1
        elif kind == "O" and ("BUSH" in name or "PLANT" in name or name.startswith("GRASS")):
            E.add([bx], [y], [bz], "fern" if "PLANT" in name else "short_grass", hard=False)
            stats["plants"] += 1
        elif kind == "O" and units.invisible(name):
            stats["invisible (skipped on purpose)"] += 1
        else:
            if name.startswith("UNKNOWN"):
                stats["skipped (unknown to the parser)"] += 1
            elif kind != "U" and not object_mob(name):
                stats["skipped (other objects)"] += 1
        if kind == "O" and (("TREE" in name and "STUMP" not in name) or name in ("GOLD_MINE", "STONE_MINE", "QUARRY")
                            or "FORAGE" in name or "FRUIT_BUSH" in name or name.startswith(("CLIFF", *MOUNTAINS, "ROCK", "STATUE", "TROPAION",
                            "STELAE", "THOLOS", "HERO_SHRINE", "WELL", "HAY_STACK", "MARKET_STALL"))):
            obstacle(E, cols, E.footprint)
        elif kind == "O" and E.footprint and not any(k in name for k in PASSABLE_OBJECTS):
            x0, x1, z0, z1 = E.footprint            # other objects with blocks: no units on top of them
            cols.blocked[max(0, x0):max(0, x1), max(0, z0):max(0, z1)] = True
    E.footprint = None
    E.natural = True
    cliff_ridges(E, cols, cliffs, rng)
    E.natural = False
    return E, stats


# --------------------------------------------------------------------------------------------
# Units -> entities
# --------------------------------------------------------------------------------------------
FISH = [("SALMON", "salmon"), ("DORADO", "tropical_fish"), ("SNAPPER", "tropical_fish"), ("FISH", "cod"),
        ("DOLPHIN", "dolphin"), ("BOX_TURTLES", "turtle"), ("HOWLER_MONKEY", "ocelot")]
OBJECT_MOBS = {"WHALE": "dolphin"}    # exact names: BEACHED_WHALE is a carcass, not a mob. No whale mob: the dolphin
LAND_MOBS = ("turtle", "ocelot")      # is the nearest large sea animal


def object_mob(name):
    """Minecraft mob for an AoE2 'other object' that is an animal (fish, dolphin, whale, turtles, monkey), else None."""
    return OBJECT_MOBS.get(name) or next((k for key, k in FISH if key in name), None)
PASSABLE = ("short_grass", "tall_grass", "large_fern", "petals", "moss_carpet", "mushroom", "allium", "bluet",
            "tulip", "lily_of", "fern", "wheat", "poppy", "dandelion", "cornflower", "daisy", "water",
            "seagrass", "dead_bush", "sweet_berry", "rail", "carpet", "banner", "button", "lantern", "snow[", "kelp",
            "lily_pad")


SEATS = {"minecraft:boat": 2, "minecraft:chest_boat": 1}


def plan_units(objects, players, cols, rng, stats, birds=True, garrison="outside", silent=False):
    """Entities per chunk: {(cx, cz): [(nbt, x, z, is_boat)]}. silent: also the passive animals (--ambience off).
    garrison="outside": a garrisoned unit rides its ship if a seat is free, else stands next to its holder."""
    T = cols.T
    out = {}
    refs = {o["ref"]: o for o in objects if o.get("ref") is not None}
    boats = {}                  # reference ID of a ship -> its boat NBT
    taken = set()               # columns that garrisoned units use, so that they do not stand in one column
    # The holders come first: a ship must exist before its passengers board it.
    for o in sorted(objects, key=lambda o: bool(o.get("garrisoned"))):
        src = o                 # gets the UUID of the entity for aoe2mc.json
        held = bool(o.get("garrisoned")) and o["kind"] == "U"
        if o["kind"] == "U":
            if held and garrison == "skip":
                stats["units (garrisoned, skipped)"] += 1
                continue
            if not birds and units.is_bird(o["name"]):
                stats["birds (skipped)"] += 1
                continue
            desc = units.classify(o["name"], o.get("hero", False))
            if desc is None:
                continue
            nbt = units.make_entity(o, players, (0, 0, 0), rng, desc)
            if silent:
                nbt["Silent"] = Byte(1)
            boat = units.is_boat(desc)
            if held:
                holder = refs.get(o.get("holder"))
                if o.get("holder") in boats:
                    ship = boats[o["holder"]]
                    if len(ship.get("Passengers", [])) < SEATS[str(ship["id"])]:
                        ship.setdefault("Passengers", List[Compound]([])).append(nbt)
                        src["uuid"] = units.uuid_str(nbt["UUID"])
                        stats["units (garrisoned, in a ship)"] += 1
                    else:
                        stats["units (garrisoned, no free seat in the ship, skipped)"] += 1
                    continue
                o = dict(o, x=holder["x"], y=holder["y"]) if holder else o
                stats["units (garrisoned, next to the holder)"] += 1
            elif boat and o.get("ref") is not None:
                boats[o["ref"]] = nbt
            stats["units"] += 1
        elif o["kind"] == "O" and object_mob(o["name"]):
            kind = object_mob(o["name"])
            nbt = units.to_nbt(units.mob(kind), (0, 0, 0), 0.0, rng)
            boat = "fish" if kind not in LAND_MOBS else False
            stats["fish" if kind in ("cod", "salmon", "tropical_fish") else "animals (objects)"] += 1
        else:
            continue
        x, z = o["x"] * T, o["y"] * T
        bx, bz = int(x), int(z)
        if not cols.inside(bx, bz):
            continue
        blocked = cols.blocked[bx, bz]      # a ship in a dock moves to free water, else its crew suffocates (#190)
        if (blocked or held) and (boat is not True or blocked):
            spot = free_spot(cols, bx, bz, 6 * T, water=bool(boat), taken=taken if held else ())
            if spot is None:
                stats["units (inside a building, no free space)"] += 1
                continue
            x, z = spot[0] + 0.5, spot[1] + 0.5
            bx, bz = spot
            if held:
                taken.add(spot)
            else:
                stats["units moved out of a building or obstacle"] += 1
        if o["kind"] == "U":
            src["uuid"] = units.uuid_str(nbt["UUID"])
        out.setdefault((bx >> 4, bz >> 4), []).append((nbt, x, z, boat))
    return out


def top_name(nbt):
    t = units.top_entity(nbt)
    return t.get("CustomName", t["id"])


def free_spot(cols, bx, bz, r, water=False, taken=()):
    """Nearest column that is not blocked or taken (and on land, unless water=True), or None."""
    x0, x1 = max(0, bx - r), min(cols.n, bx + r + 1)
    z0, z1 = max(0, bz - r), min(cols.n, bz + r + 1)
    ok = ~cols.blocked[x0:x1, z0:z1]
    for tx, tz in taken:
        if x0 <= tx < x1 and z0 <= tz < z1:
            ok[tx - x0, tz - z0] = False
    wet = cols.wtop[x0:x1, z0:z1] - cols.top[x0:x1, z0:z1]
    ok &= (wet >= 2) if water else (wet <= 1)
    xs, zs = np.nonzero(ok)
    if not len(xs):
        return None
    d = (xs + x0 - bx) ** 2 + (zs + z0 - bz) ** 2
    i = int(np.argmin(d))
    return int(xs[i] + x0), int(zs[i] + z0)


def find_spawn(cols, objects, players, tile=None):
    """Spawn block (x, y, z): the tile given (--spawn), else the start view of player 1, else in front of
    (south of) the first town center of player 1, else the map center. Moved to the nearest free land column."""
    if tile is None:
        tile = players.get(1, {}).get("view")
    if tile is None:
        tc = next((o for o in objects if o["kind"] == "B" and o["player"] == 1 and "TOWN_CENTER" in o["name"]), None)
        if tc:
            dx, dy = turn_tile(0, buildings.footprint(tc["name"]) / 2 + 0.5, 0, buildings.TURN)   # the front
            tile = (tc["x"] + dx, tc["y"] + dy)
    T, n = cols.T, cols.n
    bx, bz = (n // 2, n // 2) if tile is None else (int(min(max(tile[0] * T, 0), n - 1)),
                                                    int(min(max(tile[1] * T, 0), n - 1)))
    bx, bz = free_spot(cols, bx, bz, 8 * T) or (bx, bz)
    return bx, cols.surface(bx, bz) + 2, bz


CHAPTERS = {"instructions": "Instructions", "hints": "Hints", "victory": "Victory", "loss": "Loss",
            "history": "History", "scouts": "Scouts"}
BLOCK_DATA = {}        # (x, y, z) -> extra block entity fields (the book of the lectern)


def book_pages(texts, cols=19, rows=14):
    """Pages of the scenario texts: one chapter per text that is not empty, its title in bold.
    A book page shows 14 lines of about 19 characters. AoE2 color tags (<BLUE>) are removed."""
    pages = []
    for key, title in CHAPTERS.items():
        text = re.sub(r"<[^<>]*>", "", texts.get(key) or "").replace("\r", "").strip()
        if not text:
            continue
        # wrap only to count the lines: the game wraps the text itself, so only the paragraphs keep "\n"
        lines = [(w, i == len(ws) - 1) for para in text.split("\n")
                 for ws in [textwrap.wrap(para, cols) or [""]] for i, w in enumerate(ws)]
        first, n = True, rows - 2                     # the title and an empty line
        while lines or first:
            page = "".join(w + ("\n" if end else " ") for w, end in lines[:n]).rstrip()
            pages.append((title if first else None, page))
            lines, first, n = lines[n:], False, rows
    return pages[:100]                                 # the maximum of a written book


def text_nbt(parts):
    """A text component of (text, bold) parts in the format of the target version."""
    extra = [dict(text=t, bold=True) if b else dict(text=t) for t, b in parts]
    if MC["data_version"] < 4325:                      # before 1.21.5 text components are JSON strings
        return String(json.dumps({"text": "", "extra": extra}))
    return Compound({"text": String(""), "extra": List[Compound](
        [Compound({k: Byte(1) if k == "bold" else String(v) for k, v in e.items()}) for e in extra])})


def place_book(cols, edits, spawn, texts, title):
    """A lectern with the scenario texts as a written book, 2 blocks in front of the spawn view.
    Returns the block position, or None when all texts are empty or no free land is near."""
    pages = book_pages(texts)
    if not pages:
        return None
    sx, _, sz = spawn
    dx, dz = turn_tile(2, -2, 0, buildings.TURN)         # the spawn view turns with --orientation
    spot = free_spot(cols, min(max(sx + dx, 0), cols.n - 1), min(max(sz + dz, 0), cols.n - 1), 4)
    if spot is None or spot == (sx, sz) or cols.wtop[spot] > cols.top[spot]:
        return None
    x, z = spot
    y = cols.surface(x, z)
    facing = ("west" if x > sx else "east") if abs(x - sx) >= abs(z - sz) else ("north" if z > sz else "south")
    edits.footprint = None
    edits.add([x], [y], [z], f"lectern[facing={facing},has_book=true,powered=false]")
    cols.blocked[x, z] = True                          # no unit stands in the lectern
    book = Compound({"title": Compound({"raw": String(title[:32])}), "author": String("aoe2mc"),
                     "pages": List[Compound]([Compound({"raw": text_nbt(([(t + "\n\n", True)] if t else []) + [(b, False)])})
                                              for t, b in pages]), "resolved": Byte(1)})
    BLOCK_DATA[(x, y, z)] = {"Page": Int(0), "Book": Compound({
        "id": String("minecraft:written_book"), "count": Int(1),
        "components": Compound({"minecraft:written_book_content": book})})}
    return x, y, z


def set_pos(nbt, x, y, z):
    nbt["Pos"] = List[Double]([Double(x), Double(y), Double(z)])
    for p in nbt.get("Passengers", []):
        set_pos(p, x, y, z)


MOVED = Counter()


def entity_chunk(cx, cz, ents, cols, vol, passable):
    """Place the entities of one chunk on the first free space and return the chunk NBT bytes."""
    out = []
    for nbt, x, z, boat in ents:
        bx, bz = int(x), int(z)
        top, wtop = int(cols.top[bx, bz]), int(cols.wtop[bx, bz])
        if boat == "fish":
            if wtop - top < 2:
                continue
            y = (top + wtop) / 2 + 0.3
        elif boat and wtop > top:
            col = vol[:, bz & 15, bx & 15]
            h = 3 if nbt.get("Passengers") else 2                # the boat and its crew need free space
            y = wtop
            while y < MAX_Y - 3 and not all(passable[col[y + k - MIN_Y]] for k in range(h)):
                y += 1
            if y > wtop:
                MOVED[str(top_name(nbt))] += 1
            y += 0.5
        else:
            col = vol[:, bz & 15, bx & 15]
            y = top + 1
            if wtop > top:                   # water: stand on a bridge or dock deck if there is one
                for yy in range(wtop + 1, min(wtop + 40, MAX_Y - 2)):
                    if not passable[col[yy - 1 - MIN_Y]] and passable[col[yy - MIN_Y]] and passable[col[yy + 1 - MIN_Y]]:
                        y = yy
                        MOVED["(on a bridge)"] += 1
                        break
            while y < MAX_Y - 2 and not (passable[col[y - MIN_Y]] and passable[col[y + 1 - MIN_Y]]):
                y += 1
            if y > top + 1 and not wtop > top:
                if (bx, bz) in buildings.BRIDGE_CELLS:
                    MOVED["(on a bridge)"] += 1
                else:
                    MOVED[str(top_name(nbt))] += 1
                if os.environ.get("AOE2MC_DEBUG"):
                    print("   in block:", str(top_name(nbt)), bx, top + 1, bz, B.states[col[top + 1 - MIN_Y]],
                          B.states[col[top + 2 - MIN_Y]])
        if units.top_entity(nbt).get("NoGravity"):               # a flying bird
            y += units.FLY_LOW.get(str(units.top_entity(nbt)["id"]), units.FLY_HEIGHT)
        set_pos(nbt, x, float(y), z)
        out.append(nbt)
    if not out:
        return None
    root = Compound({"DataVersion": Int(MC["data_version"]), "Position": IntArray([cx, cz]),
                     "Entities": List[Compound]([units.to_version(e, MC["data_version"]) for e in out])})
    buf = io.BytesIO()
    buf.write(b"\x0a\x00\x00")
    root.write(buf)
    return buf.getvalue()


# --------------------------------------------------------------------------------------------
# Chunk and region writer (Anvil format)
# --------------------------------------------------------------------------------------------
def pack(values, bits):
    """Pack integers into longs. Since 1.16 an entry does not cross a long boundary."""
    per = 64 // bits
    n = -(-len(values) // per)
    a = np.zeros(n * per, np.uint64)
    a[:len(values)] = values
    a = a.reshape(n, per) << (np.arange(per, dtype=np.uint64) * np.uint64(bits))
    return np.bitwise_or.reduce(a, axis=1).view(np.int64)


PALETTE_CACHE = {}

# Blocks that need a block entity, or Minecraft shows them wrong (banners are invisible without one).
BE_TYPES = [("decorated_pot", "decorated_pot"), ("oak_sign", "sign"), ("wall_banner", "banner"), ("_banner", "banner"), ("bell", "bell"), ("campfire", "campfire"),
            ("barrel", "barrel"), ("chest", "chest"), ("blast_furnace", "blast_furnace"),
            ("smoker", "smoker"), ("furnace", "furnace"), ("lectern", "lectern"), ("_bed", "bed")]


def block_entity_type(state):
    name = state.split(":")[1].split("[")[0]
    for key, be in BE_TYPES:
        if key in name:
            return None if be == "bed" and MC["data_version"] >= V26_3 else be    # 26.3 has no bed block entity
    return None


def palette_entry(i):
    if i not in PALETTE_CACHE:
        PALETTE_CACHE[i] = B.nbt(i)
    return PALETTE_CACHE[i]


SHORT_GRASS = B("short_grass")
BARRIER = B("barrier")
TALL_PLANTS = [(B("tall_grass[half=lower]"), B("tall_grass[half=upper]")),
               (B("large_fern[half=lower]"), B("large_fern[half=upper]"))]


def build_chunk(cx, cz, cols, edits, origin=(0, 0)):
    """origin: the block x and z of cols[0, 0] (a chunk outside the map has its own 16 x 16 columns)."""
    x0, z0 = cx * 16, cz * 16
    ox, oz = x0 - origin[0], z0 - origin[1]
    sl = (slice(ox, ox + 16), slice(oz, oz + 16))
    g = lambda a: a[sl].T[None]          # (1, z, x) for broadcasting against Y
    top, wtop, top_id, sub_id = g(cols.top), g(cols.wtop), g(cols.top_id), g(cols.sub_id)
    ice, deco, sub = g(cols.ice), cols.deco[sl].T, top - g(cols.sub_depth)
    Y = np.arange(MIN_Y, MAX_Y, dtype=np.int32)[:, None, None]

    vol = np.where(Y < sub, np.where(Y < 0, DEEPSLATE, STONE), AIR).astype(np.uint16)
    vol = np.where((Y >= sub) & (Y < top), sub_id, vol)
    vol = np.where(Y == top, top_id, vol)
    water = (Y > top) & (Y <= wtop)
    vol = np.where(water, np.where(ice & (Y == wtop), ICE, WATER), vol)
    vol[0] = np.where(top[0] > NONE, BEDROCK, AIR)
    if cols.floor > MIN_Y:              # --border diorama, island, table: the map stands on a floor with air under it
        vol[:cols.floor - MIN_Y] = AIR
    zz, xx = np.nonzero(deco)
    if len(zz):
        ys = top[0][zz, xx].astype(int) + 1 - MIN_Y
        ok = (ys < HEIGHT) & (vol[np.minimum(ys, HEIGHT - 1), zz, xx] != ICE)
        vol[ys[ok], zz[ok], xx[ok]] = deco[zz[ok], xx[ok]]

    d2 = cols.deco2[sl].T
    zz, xx = np.nonzero(d2)
    if len(zz):
        ys = top[0][zz, xx].astype(int) + 2 - MIN_Y
        ok = (ys < HEIGHT) & (vol[np.minimum(ys, HEIGHT - 1), zz, xx] == AIR)
        vol[ys[ok], zz[ok], xx[ok]] = d2[zz[ok], xx[ok]]

    if edits is not None:
        ex, ey, ez, eid, hard = edits
        ey = ey - MIN_Y
        soft = ~hard
        free = vol[ey[soft], ez[soft], ex[soft]] == AIR
        vol[ey[soft][free], ez[soft][free], ex[soft][free]] = eid[soft][free]
        vol[ey[hard], ez[hard], ex[hard]] = eid[hard]

    # Tall plants: remove an upper half without its lower half (when an object took the place of the lower half)
    counts = np.bincount(vol.ravel(), minlength=len(B.states))
    for lower, upper in TALL_PLANTS:
        if not (counts[lower] or counts[upper]):        # the full scans below are slow: skip them when possible
            continue
        ys, zs, xs = np.nonzero(vol[1:] == upper)
        bad = vol[ys, zs, xs] != lower
        vol[ys[bad] + 1, zs[bad], xs[bad]] = AIR
        ys, zs, xs = np.nonzero(vol[:-1] == lower)
        bad = vol[ys + 1, zs, xs] != upper
        vol[ys[bad], zs[bad], xs[bad]] = SHORT_GRASS

    # Blocks under the water surface are waterlogged, else they leave a dry gap in the water
    wet = water & (vol != WATER) & (vol != ICE)
    if wet.any():
        vals, inv = np.unique(vol[wet], return_inverse=True)
        vol[wet] = np.array([B.wet(int(v)) for v in vals], np.uint16)[inv]

    # Biomes: one per 4x4 block cell, the same for all heights.
    cells = cols.biome[ox + 2:ox + 16:4, oz + 2:oz + 16:4].T            # (z, x) 4x4
    bvals, binv = np.unique(np.tile(cells.ravel(), 4), return_inverse=True)
    biomes = Compound({"palette": List[String]([String(cols.biome_names[v]) for v in bvals])})
    if len(bvals) > 1:
        biomes["data"] = LongArray(pack(binv, max(1, int(np.ceil(np.log2(len(bvals)))))))

    # Sections: an empty or full section has one palette entry; else bincount is faster than np.unique
    flat = vol.reshape(HEIGHT // 16, 4096)              # one row per section, index = y*256 + z*16 + x
    lo, hi = flat.min(1), flat.max(1)
    lut = np.zeros(len(B.states), np.int64)
    present = set()
    sections = []
    for s in range(HEIGHT // 16):
        vals = lo[s:s + 1] if lo[s] == hi[s] else np.flatnonzero(np.bincount(flat[s], minlength=len(B.states)))
        present.update(vals.tolist())
        states = Compound({"palette": List[Compound]([palette_entry(int(v)) for v in vals])})
        if len(vals) > 1:
            lut[vals] = np.arange(len(vals))
            states["data"] = LongArray(pack(lut[flat[s]], max(4, int(np.ceil(np.log2(len(vals)))))))
        sections.append(Compound({"Y": Byte(s + MIN_Y // 16), "block_states": states,
                                  "biomes": biomes}))

    block_entities = []
    be_ids = [i for i in sorted(present) if block_entity_type(B.states[i])]
    for i in be_ids:
        for y, z, x in zip(*np.nonzero(vol == i)):
            pos = (x0 + int(x), int(y) + MIN_Y, z0 + int(z))
            block_entities.append(Compound({
                "id": String("minecraft:" + block_entity_type(B.states[i])), "keepPacked": Byte(0),
                "x": Int(pos[0]), "y": Int(pos[1]), "z": Int(pos[2]), **BLOCK_DATA.get(pos, {})}))

    chunk = Compound({
        "DataVersion": Int(MC["data_version"]), "xPos": Int(cx), "zPos": Int(cz), "yPos": Int(MIN_Y // 16),
        "Status": String("minecraft:full"), "LastUpdate": Long(0), "InhabitedTime": Long(0),
        "isLightOn": Byte(0),            # Minecraft calculates the light when it loads the chunk
        "sections": List[Compound](sections),
        "block_entities": List[Compound](block_entities),
        "Heightmaps": Compound({}),       # Minecraft calculates missing heightmaps
        "structures": Compound({"References": Compound({}), "starts": Compound({})}),
        "fluid_ticks": List[Compound]([]), "block_ticks": List[Compound]([]),
    })
    buf = io.BytesIO()
    buf.write(b"\x0a\x00\x00")            # root compound tag with an empty name
    chunk.write(buf)
    return buf.getvalue(), vol


def write_region(path, chunks):
    """chunks: {(local_x, local_z): nbt_bytes}. A chunk of more than 255 sectors goes to c.<x>.<z>.mcc, as in
    Minecraft: the region file then holds only the compression byte with the 'external' bit (0x82)."""
    header = bytearray(8192)
    body = bytearray()
    now = int(time.time())
    rx, rz = (int(v) for v in os.path.basename(path).split(".")[1:3])
    for (lx, lz), data in chunks.items():
        comp = zlib.compress(data, 6)
        payload = (len(comp) + 1).to_bytes(4, "big") + b"\x02" + comp
        if len(payload) > 255 * 4096:
            with open(os.path.join(os.path.dirname(path), f"c.{rx * 32 + lx}.{rz * 32 + lz}.mcc"), "wb") as f:
                f.write(comp)
            payload = (1).to_bytes(4, "big") + b"\x82"
        payload += b"\x00" * (-len(payload) % 4096)
        offset = 2 + len(body) // 4096
        sectors = len(payload) // 4096
        i = 4 * (lx + lz * 32)
        header[i:i + 4] = offset.to_bytes(3, "big") + bytes([sectors])
        header[4096 + i:4096 + i + 4] = now.to_bytes(4, "big")
        body += payload
    with open(path, "wb") as f:
        f.write(header + body)


def write_objects(path, size, T, H, players, objects, cols, ground):
    """aoe2mc.json: the data that a game program needs (docs/research/gameplay.md). Tiles are in the turned grid
    (--orientation): block x = tile x × T, block z = tile y × T. Units have the UUID of their entity, buildings
    their footprint [x0, z0, x1, z1) in blocks. Objects that the converter did not place are not in the list.
    "ground" has one string per block row z: for each x the y where a unit stands, or "-" for water."""
    kinds = {"U": "unit", "B": "building", "O": "other"}
    objs = []
    for o in objects:
        if o["kind"] not in kinds or not cols.inside(int(o["x"] * T), int(o["y"] * T)):
            continue
        if (o["kind"] == "U" and "uuid" not in o) or (o["kind"] == "B" and "footprint" not in o):
            continue
        e = {"id": o.get("id"), "name": o["name"], "kind": kinds[o["kind"]], "player": o["player"],
             "tile": [round(float(o["x"]), 3), round(float(o["y"]), 3)], "rotation": round(o.get("rotation", 0.0), 4)}
        if o.get("hero"):
            e["hero"] = True
        for k in ("uuid", "footprint"):
            if k in o:
                e[k] = o[k]
        objs.append(e)
    data = {"map_size": size, "tile_size": T, "level_height": H,
            "players": {str(pid): {"civ": p["civ"], "color": p["color"], "arch": p["arch"]}
                        for pid, p in sorted(players.items())},
            "objects": objs}
    n, wet = cols.n, cols.wtop > cols.top
    data["ground"] = [" ".join("-" if wet[x, z] else str(ground[x, z]) for x in range(n)) for z in range(n)]
    with open(path, "w") as f:
        json.dump(data, f, indent=1)


# Work sounds at buildings (#220): name part -> (sound, predicate, particle). Only Minecraft sounds; the villager
# work sounds exist in 1.21.1 and 26.3. The first matching rule wins.
WORK_SOUNDS = [
    ("BLACKSMITH", "block.anvil.use", "sometimes", "lava"), ("MARKET", "entity.villager.trade", "sometimes", None),
    ("TOWN_CENTER", "block.bell.use", "rare", None), ("LUMBER_CAMP", "item.axe.strip", "sometimes", None),
    ("MINING_CAMP", "block.stone.break", "sometimes", None), ("DOCK", "entity.villager.work_fisherman", "sometimes", None),
    ("MONASTERY", "entity.villager.work_cleric", "sometimes", None), ("MILL", "entity.villager.work_farmer", "sometimes", None),
    ("ARCHERY_RANGE", "entity.villager.work_fletcher", "sometimes", None),
    ("UNIVERSITY", "entity.villager.work_librarian", "sometimes", None),
    ("SIEGE_WORKSHOP", "entity.villager.work_mason", "sometimes", None),
]
CHANCE = {"sometimes": 0.25, "rare": 0.03}      # per pulse of 2 s

# Ambience per terrain group (#219): vanilla biomes of `terrain_style` -> particle and sound near each player in such
# a biome (datapack function, no warning), and the colors of the custom biome of `--ambience full` (the client shows
# the "Experimental Settings" warning for it, docs/datapack.md). Particles: only types without options that exist in
# 1.21.1 and 26.3. Colors: sky, fog, water, water fog (0xRRGGBB), then extra `effects` (the same in both versions).
AMBIENCE = {
    "forest": (("forest", "birch_forest", "taiga", "jungle", "bamboo_jungle"), "spore_blossom_air",
               "entity.parrot.ambient", (0.7, 0.8, True), (0x79a6ff, 0xc0d8ff, 0x3f76e4, 0x050533), {}),
    "snow": (("snowy_plains", "snowy_taiga", "frozen_ocean"), "snowflake", None, (0.0, 0.5, True),
             (0x7fa1ff, 0xdde4f0, 0x3938c9, 0x050533), {}),
    "desert": (("desert", "savanna"), "white_ash", None, (2.0, 0.0, False), (0x6eb1ff, 0xe2d3a8, 0x32a598, 0x050533), {}),
    "swamp": (("swamp", "mangrove_swamp"), None, "entity.frog.ambient", (0.8, 0.9, True),
              (0x78a7ff, 0xa4b3a0, 0x617b64, 0x232317), {"grass_color_modifier": "swamp"}),
    "water": (("ocean", "deep_ocean", "warm_ocean", "river", "beach"), None, "block.water.ambient", (0.5, 0.5, True),
              (0x7ba4ff, 0xc0d8ff, 0x3f76e4, 0x050533), {}),
    "grass": (("plains", "meadow"), None, None, (0.8, 0.4, True), (0x78a7ff, 0xc0d8ff, 0x3f76e4, 0x050533), {}),
}
AMBIENCE_GROUP = {b: g for g, (biomes, *_) in AMBIENCE.items() for b in biomes}


def custom_biomes(names):
    """--ambience full: minecraft:<biome> -> aoe2mc:<group> for the biomes of an AMBIENCE group."""
    return [f"aoe2mc:{AMBIENCE_GROUP[n[10:]]}" if n[10:] in AMBIENCE_GROUP else n for n in names]


def biome_file(group):
    """The custom biome of a group in the format of the output version (docs/datapack.md, "Biome files")."""
    (t, rain, precip), (sky, fog, water, water_fog), extra = AMBIENCE[group][3:]
    data = {"has_precipitation": precip, "temperature": t, "downfall": rain}
    if MC["data_version"] >= V26_1:             # 26.x: colors are "#rrggbb", sky and fog are attributes
        hx = "#{:06x}".format
        return data | {"effects": {"water_color": hx(water)} | extra,
                       "attributes": {"minecraft:visual/sky_color": hx(sky), "minecraft:visual/fog_color": hx(fog),
                                      "minecraft:visual/water_fog_color": hx(water_fog)},
                       "features": [], "carvers": []}
    return data | {"effects": {"sky_color": sky, "fog_color": fog, "water_color": water, "water_fog_color": water_fog}
                   | extra, "spawners": {}, "spawn_costs": {}, "features": [], "carvers": {}}


def ambience_lines(biome_names):
    """Pulse lines: particles and sounds near each player in the biome of a group (the biomes of the map only)."""
    lines = []
    for group, (_, particle, sound, *_) in AMBIENCE.items():
        names = [n for n in biome_names if n == f"aoe2mc:{group}" or AMBIENCE_GROUP.get(n[10:]) == group]
        for n in sorted(set(names)):
            at = f"execute as @a at @s if biome ~ ~ ~ {n}"
            if particle:
                lines.append(f"{at} run particle minecraft:{particle} ~ ~4 ~ 8 3 8 0 20")
            if sound:
                lines.append(f"{at} if predicate aoe2mc:sometimes run playsound minecraft:{sound} ambient @s ~ ~ ~ 0.5")
    return lines


def write_datapack(out, objects, ground, biome_names=(), ambience="basic"):
    """datapacks/aoe2mc: a function every 2 s plays a work sound at each building with a player near it
    (docs/datapack.md). Fixed positions, no marker entities: the check costs nothing that /tick query shows.
    Ambience (#219): particles and sounds near the players by biome; "full" also writes the custom biomes, "off"
    writes no pack.
    Returns (work sounds, ambience lines)."""
    root = os.path.join(out, "datapacks", "aoe2mc")
    if ambience == "off":           # the world as before #188: no pack
        return 0, 0
    lines = []
    for o in objects:
        rule = next((r for r in WORK_SOUNDS if r[0] in o["name"]), None) if o["kind"] == "B" else None
        if rule is None or "footprint" not in o:
            continue
        x0, z0, x1, z1 = o["footprint"]
        x, z = (x0 + x1) // 2, (z0 + z1) // 2
        if not (0 <= x < ground.shape[0] and 0 <= z < ground.shape[1]):
            continue
        at = f"execute positioned {x} {int(ground[x, z]) + 1} {z} if entity @a[distance=..24] " \
             f"if predicate aoe2mc:{rule[2]} run"
        lines.append(f"{at} playsound minecraft:{rule[1]} ambient @a ~ ~ ~ 1 {0.9 + 0.1 * (x % 3):.1f}")
        if rule[3]:
            lines.append(f"{at} particle minecraft:{rule[3]} ~ ~1 ~ 0.4 0.2 0.4 0 4")
    work = len(lines)
    lines += ambience_lines(biome_names)
    groups = sorted({n.split(":")[1] for n in biome_names if n.startswith("aoe2mc:")})
    if not lines and not groups:    # the server finds a new pack by itself; level.dat needs no entry
        return 0, 0
    files = {
        "pack.mcmeta": {"pack": {"description": "aoe2mc: work sounds and ambience", "pack_format": MC["pack_format"]}
                        | ({"min_format": MC["pack_format"], "max_format": MC["pack_format"]}
                           if MC["data_version"] >= V26_1 else {})},
        "data/minecraft/tags/function/load.json": {"values": ["aoe2mc:load"]},
        "data/aoe2mc/function/load.mcfunction": "schedule function aoe2mc:pulse 40t replace\n",
        "data/aoe2mc/function/pulse.mcfunction": "\n".join(lines + ["schedule function aoe2mc:pulse 40t replace"]) + "\n",
    }
    key = "type" if MC["data_version"] >= V26_1 else "condition"     # 26.x renamed the key of a predicate
    for name, chance in CHANCE.items():
        files[f"data/aoe2mc/predicate/{name}.json"] = {key: "minecraft:random_chance", "chance": chance}
    for g in groups:
        files[f"data/aoe2mc/worldgen/biome/{g}.json"] = biome_file(g)
    for name, data in files.items():
        path = os.path.join(root, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(data if isinstance(data, str) else json.dumps(data))
    return sum("playsound" in line for line in lines[:work]), len(lines) - work


def write_level_dat(path, name, spawn, yaw=SPAWN_YAW, size=None):
    """size: the map size in blocks; the vanilla world border goes around the map (#172)."""
    def dim(kind, gen):
        return Compound({"type": String(f"minecraft:{kind}"), "generator": gen})
    void = Compound({"type": String("minecraft:flat"), "settings": Compound({
        "biome": String("minecraft:the_void"), "features": Byte(0), "lakes": Byte(0),
        "layers": List[Compound]([Compound({"block": String("minecraft:air"), "height": Int(1)})]),
        "structure_overrides": List[String]([])})})
    nether = Compound({"type": String("minecraft:noise"), "settings": String("minecraft:nether"),
                       "biome_source": Compound({"type": String("minecraft:multi_noise"),
                                                 "preset": String("minecraft:nether")})})
    end = Compound({"type": String("minecraft:noise"), "settings": String("minecraft:end"),
                    "biome_source": Compound({"type": String("minecraft:the_end")})})
    data = Compound({
        "DataVersion": Int(MC["data_version"]), "version": Int(19133),
        "Version": Compound({"Id": Int(MC["data_version"]), "Name": String(MC["name"]),
                             "Series": String("main"), "Snapshot": Byte(0)}),
        "LevelName": String(name), "GameType": Int(1), "Difficulty": Byte(1),   # not peaceful: peaceful removes the soldiers
        "allowCommands": Byte(1), "hardcore": Byte(0), "initialized": Byte(1),
        "SpawnX": Int(spawn[0]), "SpawnY": Int(spawn[1]), "SpawnZ": Int(spawn[2]), "SpawnAngle": Float(yaw),
        "LastPlayed": Long(int(time.time() * 1000)), "Time": Long(0), "DayTime": Long(6000),
        "raining": Byte(0), "thundering": Byte(0), "rainTime": Int(0), "thunderTime": Int(0),
        "clearWeatherTime": Int(0), "WasModded": Byte(0),
        "DragonFight": Compound({"NeedsStateScanning": Byte(1), "DragonKilled": Byte(0),   # else "key missing" on load
                                 "PreviouslyKilled": Byte(0)}),
        "GameRules": Compound({"doDaylightCycle": String("false"), "doWeatherCycle": String("false"),
                               "doMobSpawning": String("false"), "doFireTick": String("false")}),
        "DataPacks": Compound({"Enabled": List[String]([String("vanilla")]), "Disabled": List[String]([])}),
        "WorldGenSettings": Compound({
            "seed": Long(0), "generate_features": Byte(0), "bonus_chest": Byte(0),
            "dimensions": Compound({"minecraft:overworld": dim("overworld", void),
                                    "minecraft:the_nether": dim("the_nether", nether),
                                    "minecraft:the_end": dim("the_end", end)})}),
    })
    c = size / 2 if size else 0.0
    edge = {"center_x": Double(c), "center_z": Double(c), "size": Double(size or 5.9999968e7),
            "lerp_time": Long(0), "lerp_target": Double(size or 5.9999968e7), "safe_zone": Double(5),
            "damage_per_block": Double(0.2), "warning_blocks": Int(5), "warning_time": Int(15)}
    if MC["data_version"] < V26_1:
        for k, old in (("center_x", "BorderCenterX"), ("center_z", "BorderCenterZ"), ("size", "BorderSize"),
                       ("lerp_time", "BorderSizeLerpTime"), ("lerp_target", "BorderSizeLerpTarget"),
                       ("safe_zone", "BorderSafeZone"), ("damage_per_block", "BorderDamagePerBlock"),
                       ("warning_blocks", "BorderWarningBlocks"), ("warning_time", "BorderWarningTime")):
            v = edge[k]
            data[old] = Double(v) if isinstance(v, Int) else v        # 1.21.1 reads the warnings as doubles
        File({"Data": data}, gzipped=True).save(path)
        return
    # 26.1: most fields leave level.dat for files in data/minecraft/ (docs/minecraft-versions.md)
    level = Compound({k: data[k] for k in ("DataVersion", "version", "Version", "LevelName", "GameType",
                                           "allowCommands", "initialized", "LastPlayed", "Time", "WasModded",
                                           "DataPacks")})
    level["spawn"] = Compound({"pos": IntArray(list(spawn)), "dimension": String("minecraft:overworld"),
                               "yaw": Float(yaw), "pitch": Float(0)})
    level["difficulty_settings"] = Compound({"difficulty": String("easy"), "hardcore": Byte(0), "locked": Byte(0)})
    File({"Data": level}, gzipped=True).save(path)
    files = {
        "game_rules": {"minecraft:advance_time": Byte(0), "minecraft:advance_weather": Byte(0),
                       "minecraft:spawn_mobs": Byte(0), "minecraft:fire_spread_radius_around_player": Int(0)},
        "world_gen_settings": {"seed": Long(0), "generate_structures": Byte(0), "bonus_chest": Byte(0),
                               "dimensions": data["WorldGenSettings"]["dimensions"]},
        "weather": {"raining": Byte(0), "thundering": Byte(0), "rain_time": Int(0), "thunder_time": Int(0),
                    "clear_weather_time": Int(0)},
        "world_clocks": {"minecraft:overworld": Compound({"total_ticks": Long(6000), "paused": Byte(0)})},
    }
    d = os.path.join(os.path.dirname(path), "data", "minecraft")
    os.makedirs(d, exist_ok=True)
    for f, v in files.items():
        File({"data": Compound(v), "DataVersion": Int(MC["data_version"])}, gzipped=True).save(os.path.join(d, f + ".dat"))
    # The world border is data of the overworld (DimensionStorageFileFix in the 26.3 server)
    d = os.path.join(os.path.dirname(path), "dimensions", "minecraft", "overworld", "data", "minecraft")
    os.makedirs(d, exist_ok=True)
    File({"data": Compound(edge), "DataVersion": Int(MC["data_version"])}, gzipped=True).save(
        os.path.join(d, "world_border.dat"))


# --------------------------------------------------------------------------------------------
# Border (#172): blocks outside the map square for --border. The map itself does not change.
# --------------------------------------------------------------------------------------------
BORDERS = {"none": 0, "diorama": 2, "natural": 16, "wall": 8, "island": 1, "table": 3}  # design -> ring width


def ring(n, r):
    """x, z and distance d (1..r) of the columns outside the map square 0..n-1."""
    x, z = (a.ravel() for a in np.meshgrid(np.arange(-r, n + r), np.arange(-r, n + r), indexing="ij"))
    d = np.maximum.reduce([-x, x - n + 1, -z, z - n + 1])
    return x[d > 0], z[d > 0], d[d > 0]


def fill(E, x, z, y0, y1, block):
    """Fill y0..y1-1 of each column (x, z). block: a state, or block IDs per column."""
    y0, y1 = (np.broadcast_to(np.asarray(v, np.int32), x.shape) for v in (y0, y1))
    k = np.maximum(y1 - y0, 0)
    i = np.repeat(np.arange(len(x)), k)
    ys = y0[i] + np.arange(len(i)) - np.repeat(np.cumsum(k) - k, k)
    ids = np.full(len(x), B(block), np.uint16) if isinstance(block, str) else np.broadcast_to(block, x.shape)
    E.add(x[i], ys, z[i], ids[i])


def border(cols, design, colors, E):
    """Draw the edge design around the map into E. colors: one dye per player, for the corner towers.
    Returns the width of the ring in blocks."""
    r = BORDERS[design]
    if not r:
        return 0
    n = cols.n
    x, z, d = ring(n, r)
    ex, ez = np.clip(x, 0, n - 1), np.clip(z, 0, n - 1)
    h = cols.wtop[ex, ez].astype(np.int32)        # surface of the nearest map column (ground or water)
    g = cols.top[ex, ez].astype(np.int32)
    if design == "diorama":
        # A model on a plinth: the faces are stone bricks with a trim, and the bottom is 6 blocks under the lowest
        # ground of the map (build_chunk cuts the map there). The trim is flush with the ground and holds the water.
        f = cols.floor = int(cols.top[:n, :n].min()) - 6
        a, b = d == 1, d == 2
        fill(E, x[a], z[a], f, h[a], "stone_bricks")
        fill(E, x[a], z[a], h[a], h[a] + 1, "polished_andesite")
        fill(E, x[a], z[a], f, f + 2, "polished_deepslate")
        fill(E, x[b], z[b], f, f + 2, "polished_deepslate")
        fill(E, x[b], z[b], f + 2, f + 3, "polished_deepslate_slab[type=bottom]")
        fill(E, x[b], z[b], h[b] - 1, h[b], "stone_brick_slab[type=top]")
    elif design == "natural":
        # The ground slopes down into a ring of sea, like the dark edge of the AoE2 map. Barriers hold the water.
        bed = WATER_Y - 4
        gy = np.maximum(bed, g - d - np.maximum(0, d - 2))
        land = gy >= WATER_Y
        edge_land = h == g
        top = np.where(land & edge_land, cols.top_id[ex, ez], np.where((x + z) % 5 == 0, B("gravel"), B("sand")))
        sub = np.where(land & edge_land, cols.sub_id[ex, ez], B("sand"))
        fill(E, x, z, gy - 8, gy - 3, "stone")
        fill(E, x, z, gy - 3, gy, sub)
        fill(E, x, z, gy, gy + 1, top)
        fill(E, x, z, gy + 1, WATER_Y + 1, "water")
        o = d == r
        fill(E, x[o], z[o], gy[o] + 1, WATER_Y + 1, "barrier")
    elif design == "island":
        # A floating island (#262): a rim of earth holds the water, and a cone of rock and earth hangs under the
        # map, deepest at the center. Hanging roots grow under the shallow parts.
        f = cols.floor = int(cols.top[:n, :n].min()) - 6
        land = h == g
        fill(E, x, z, f, h + 1, np.where(land, cols.sub_id[ex, ez], B("dirt")))
        fill(E, x, z, h, h + 1, np.where(land, cols.top_id[ex, ez], B("sand")))
        mx, mz = (a.ravel() for a in np.meshgrid(np.arange(n), np.arange(n), indexing="ij"))
        rr = np.hypot(mx - (n - 1) / 2, mz - (n - 1) / 2) / (n / 2 * 1.42)
        e = np.minimum.reduce([mx, n - 1 - mx, mz, n - 1 - mz])        # distance to the map edge
        rng = np.random.default_rng(n)
        # steep sides (2 blocks down per block in), so that a view from above sees them; a round tip
        depth = 3 + (np.minimum(2 * e, min(n * 0.6, f - MIN_Y - 8) * np.clip(1 - rr, 0, 1))
                     + rng.integers(0, 3, mx.size)).astype(int)
        bot = np.maximum(f - depth, MIN_Y + 2)
        fill(E, mx, mz, f - 3, f, "dirt")
        rock = np.where(rng.random(mx.size) < 0.15, B("andesite"), np.where(rng.random(mx.size) < 0.03,
                                                                            B("coal_ore"), B("stone")))
        fill(E, mx, mz, bot, f - 3, rock)
        hang = (depth < 8) & (rng.random(mx.size) < 0.25)
        fill(E, mx[hang], mz[hang], f - 4, f - 3, "rooted_dirt")
        fill(E, mx[hang], mz[hang], f - 5, f - 4, "hanging_roots[waterlogged=false]")
    elif design == "table":
        # A map table (#262): a frame of dark oak with a raised lip, a leg under each corner, a banner in a player
        # color on each corner and lanterns on the lip.
        f = cols.floor = int(cols.top[:n, :n].min()) - 6
        lip = d <= 2
        fill(E, x[lip], z[lip], f, h[lip] + 2, "dark_oak_planks")
        o = d == 3
        fill(E, x[o], z[o], f, h[o] + 1, "dark_oak_planks")
        fill(E, x[o], z[o], h[o] + 1, h[o] + 2, "dark_oak_slab[type=bottom,waterlogged=false]")
        fill(E, x, z, f - 1, f, "stripped_dark_oak_log[axis=y]")
        along = np.where((x < 0) | (x >= n), z, x)
        lamp = (d == 2) & (along % 12 == 6) & (along > 0) & (along < n - 1)
        fill(E, x[lamp], z[lamp], h[lamp] + 2, h[lamp] + 3, "lantern[hanging=false,waterlogged=false]")
        for i, (cx, cz) in enumerate(((-2, -2), (n + 1, -2), (n + 1, n + 1), (-2, n + 1))):
            t = (np.abs(x - cx) <= 1) & (np.abs(z - cz) <= 1)
            fill(E, x[t], z[t], max(f - 40, MIN_Y + 1), f - 1, "dark_oak_log[axis=y]")
            c = t & (x == cx) & (z == cz)
            color = colors[i % len(colors)] if colors else "white"
            fill(E, x[c], z[c], h[c] + 2, h[c] + 3, f"{color}_banner[rotation={(2 + 4 * i) % 16}]")
    elif design == "wall":
        # A low wall of stone bricks with merlons, and a tower in a player color at each corner.
        a = d <= 2
        fill(E, x[a], z[a], h[a] - 8, h[a] + 4, "stone_bricks")
        along = np.where((x < 0) | (x >= n), z, x)
        m = (d == 2) & (along % 2 == 0)
        fill(E, x[m], z[m], h[m] + 4, h[m] + 5, "stone_bricks")
        for i, (cx, cz) in enumerate(((-4, -4), (n + 3, -4), (n + 3, n + 3), (-4, n + 3))):
            t = (np.abs(x - cx) <= 3) & (np.abs(z - cz) <= 3)
            top = int(h[t].max()) + 8
            fill(E, x[t], z[t], int(h[t].min()) - 8, top, "stone_bricks")
            band = colors[i % len(colors)] + "_concrete" if colors else "chiseled_stone_bricks"
            fill(E, x[t], z[t], top - 3, top - 1, band)
            rim = (np.maximum(np.abs(x - cx), np.abs(z - cz)) == 3) & ((x + z) % 2 == 0) & t
            fill(E, x[rim], z[rim], top, top + 1, "stone_bricks")
    return r


# --------------------------------------------------------------------------------------------
# Preview image (top view)
# --------------------------------------------------------------------------------------------
COLORS = [("leaves", (40, 110, 40)), ("snow[", (240, 240, 245)), ("tall_grass", (95, 150, 65)), ("large_fern", (75, 130, 55)), ("moss", (90, 115, 45)), ("petals", (235, 165, 200)), ("poppy", (200, 30, 30)), ("tulip", (220, 120, 60)),
          ("dandelion", (240, 220, 50)), ("cornflower", (70, 100, 220)), ("allium", (180, 110, 220)),
          ("bluet", (225, 230, 235)), ("daisy", (235, 235, 225)), ("lily_of", (235, 240, 235)),
          ("mushroom", (160, 110, 80)), ("stone_brick", (122, 122, 122)), ("cobblestone", (110, 110, 110)), ("white_terracotta", (215, 200, 190)),
          ("glass", (170, 200, 220)), ("banner", None), ("terracotta", (200, 180, 160)),
          ("calcite", (225, 225, 220)), ("quartz", (235, 230, 225)), ("bricks", (150, 70, 55)),
          ("brick", (150, 70, 55)), ("deepslate_tile", (55, 55, 60)), ("dark_oak", (65, 45, 25)),
          ("spruce", (105, 75, 45)), ("acacia", (170, 90, 50)), ("jungle", (160, 115, 80)),
          ("crimson", (140, 50, 60)), ("mud_brick", (140, 105, 80)), ("packed_mud", (140, 105, 80)),
          ("red_sandstone", (180, 95, 40)), ("copper", (80, 160, 140)), ("smooth_stone", (160, 160, 160)),
          ("hay", (200, 170, 50)), ("chain", (60, 60, 70)), ("iron_bars", (90, 90, 90)), ("fence", (120, 90, 60)),
          ("door", (110, 80, 50)), ("bell", (240, 200, 40)), ("campfire", (230, 120, 30)),
          ("water", (52, 92, 200)), ("ice", (160, 190, 240)), ("seagrass", (52, 92, 200)),
          ("leaves", (40, 110, 40)), ("bamboo", (90, 160, 40)), ("grass_block", (100, 160, 70)),
          ("short_grass", (100, 160, 70)), ("fern", (80, 140, 60)), ("podzol", (110, 80, 40)),
          ("snow", (240, 240, 245)), ("sandstone", (215, 200, 150)), ("sand", (220, 210, 160)),
          ("gravel", (140, 135, 130)), ("mud", (70, 60, 60)), ("dirt", (130, 95, 65)),
          ("farmland", (110, 75, 45)), ("wheat", (200, 180, 80)), ("gold", (240, 200, 40)),
          ("log", (100, 75, 45)), ("planks", (160, 130, 80)), ("concrete", None), ("wool", None), ("carpet", None),
          ("stone", (125, 125, 125)), ("cobble", (110, 110, 110)), ("andesite", (135, 135, 135))]
DYE = {"white": (240, 240, 240), "light_gray": (160, 160, 160), "gray": (80, 80, 80),
       "blue": (40, 60, 180), "red": (180, 40, 40), "green": (40, 140, 40), "yellow": (230, 200, 40),
       "cyan": (30, 160, 170), "purple": (130, 50, 170), "orange": (230, 120, 20)}


def block_color(state):
    n = state.split(":")[1].split("[")[0]
    for key, col in COLORS:
        if key in n:
            if col is None:
                base = n.replace("_wall_banner", "").replace("_banner", "").rsplit("_", 1)[0] \
                    if "banner" not in n else n.replace("_wall_banner", "").replace("_banner", "")
                return DYE.get(base, (200, 200, 200))
            return col
    return (150, 150, 150)


# --------------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------------
def convert(src, out, T=4, H=3, name=None, seed=1, preview=False, arch=None, player_arch=(), with_units=True,
            barriers=True, mc_version=VERSION_NAME, spawn=None, birds=True, orientation="ne", verbose=False,
            garrison="outside", border_design="diorama", ambience="basic"):
    global MC
    MC = VERSIONS[mc_version]
    PALETTE_CACHE.clear()   # the cached entries can have the block names of another version
    try:
        _convert(src, out, T, H, name, seed, preview, arch, player_arch, with_units, barriers, spawn, birds, orientation,
                 verbose, garrison, border_design, ambience)
    finally:
        MC = VERSIONS[VERSION_NAME]
        PALETTE_CACHE.clear()
        buildings.TURN = 0


def _convert(src, out, T, H, name, seed, preview, arch, player_arch, with_units, barriers, spawn, birds, orientation,
             verbose, garrison, border_design, ambience):
    buildings.BARRIERS = barriers
    buildings.TURN, yaw = ORIENTATIONS[orientation]
    MOVED.clear()           # the counts of an earlier conversion in this process
    BLOCK_DATA.clear()
    rng = np.random.default_rng(seed)
    t0 = time.time()
    times, clock = {}, [t0]

    def tick(phase):        # add the time since the last tick to the phase (--verbose)
        now = time.time()
        times[phase] = times.get(phase, 0.0) + now - clock[0]
        clock[0] = now

    size, terrain, elevation, tnames, texts, objects, players = read_map(src)
    tick("read")
    name = name or os.path.splitext(os.path.basename(src))[0]
    terrain, elevation = turn_map(buildings.TURN, size, terrain, elevation, objects, players)
    if spawn is not None:       # --spawn is in AoE2 tiles
        spawn = turn_tile(*spawn, size, buildings.TURN)
    if arch:
        for p in players.values():
            p["arch"] = arch
    for spec in player_arch:
        pid, a = player_arch_spec(spec) if isinstance(spec, str) else spec
        if pid not in players:
            raise OptionError(f"--player-architecture: player {pid} is not in the scenario "
                              f"(players: {', '.join(map(str, sorted(players)))})")
        players[pid]["arch"] = a
    print(f"Read {os.path.basename(src)}: {size}x{size} tiles, {len(objects)} objects "
          f"({time.time() - t0:.1f}s)")
    unknown = Counter(int(o["name"][8:]) for o in objects if o["kind"] == "?")
    if unknown:                 # users can report these IDs, so that the parser data can get them
        print("  unknown object IDs (skipped): " + ", ".join(f"{i} ×{n}" for i, n in sorted(unknown.items())))

    cols = Columns(size, terrain, elevation, tnames, T, H, rng)
    if ambience == "full":
        cols.biome_names = custom_biomes(cols.biome_names)
    tick("columns")
    for pid, p in sorted(players.items()):
        if pid and any(o["player"] == pid for o in objects):
            print(f"  player {pid}: {p['civ'].lower()}, {p['color']}, {p['arch']} buildings")
    edits, stats = place_objects(objects, players, cols, rng)
    for k, v in sorted(stats.items()):
        print(f"  {k}: {v}")
    spawn = find_spawn(cols, objects, players, spawn)
    book = place_book(cols, edits, spawn, texts, name)
    if book:
        print(f"  book with the scenario texts: lectern at {book}")
    colors = [player_color(pid, players) for pid in sorted(players) if pid and any(o["player"] == pid for o in objects)]
    r = border(cols, border_design, colors, edits)
    edits.connect()
    per_chunk = edits.by_chunk(max(cols.width, cols.n + r), -r)
    tick("objects")
    before = set(stats)
    unit_chunks = plan_units(objects, players, cols, rng, stats, birds, garrison, ambience == "off") if with_units else {}
    tick("units")
    print(f"  units: {stats['units']}, fish: {stats['fish']}")
    for k in sorted(set(stats) - before - {"units", "fish"}):
        print(f"  {k}: {stats[k]}")
    passable = np.array([st.split(":")[1].split("[")[0] in ("air", "cave_air") or
                         any(k in st.split(":")[1] for k in PASSABLE) and "grass_block" not in st
                         for st in B.states] + [True] * 1024)

    dim = os.path.join(out, "dimensions", "minecraft", "overworld") if MC["data_version"] >= V26_1 else out
    for d in ("region", "entities"):
        os.makedirs(os.path.join(dim, d), exist_ok=True)
    entity_regions = {}
    nchunks = cols.width // 16
    outside = cols.outside()
    rim = [c for c in per_chunk if not (0 <= c[0] < nchunks and 0 <= c[1] < nchunks)]     # chunks of the border
    regions = {}
    top_view = np.zeros((cols.width, cols.width), np.uint16)     # for icon.png and preview.png
    ground = np.zeros((cols.width, cols.width), np.int16)        # y where a unit stands, for aoe2mc.json
    ys = np.arange(MIN_Y, MAX_Y - 1)[:, None, None]
    for cx in range(nchunks):
        for cz in range(nchunks):
            data, vol = build_chunk(cx, cz, cols, per_chunk.get((cx, cz)))
            regions.setdefault((cx >> 5, cz >> 5), {})[(cx & 31, cz & 31)] = data
            solid = (vol != AIR) & (vol != BARRIER)
            hi = HEIGHT - 1 - np.argmax(solid[::-1], axis=0)
            top_view[cx * 16:cx * 16 + 16, cz * 16:cz * 16 + 16] = np.take_along_axis(vol, hi[None], 0)[0].T
            top = cols.top[cx * 16:cx * 16 + 16, cz * 16:cz * 16 + 16].T                   # [z, x] as vol
            lo = max(int(top.min()) + 1 - MIN_Y, 0)                    # the padding outside the map is void
            p = passable[vol[lo:]]
            stand = np.argmax(p[:-1] & p[1:] & (ys[lo:] > top), axis=0) + lo + MIN_Y   # first 2 free blocks over the ground
            ground[cx * 16:cx * 16 + 16, cz * 16:cz * 16 + 16] = stand.T
            tick("chunks")
            if (cx, cz) in unit_chunks:
                ed = entity_chunk(cx, cz, unit_chunks[(cx, cz)], cols, vol, passable)
                if ed:
                    entity_regions.setdefault((cx >> 5, cz >> 5), {})[(cx & 31, cz & 31)] = ed
                tick("units")
    for cx, cz in sorted(rim):
        data, _ = build_chunk(cx, cz, outside, per_chunk[(cx, cz)], (cx * 16, cz * 16))
        regions.setdefault((cx >> 5, cz >> 5), {})[(cx & 31, cz & 31)] = data
    tick("chunks")
    for (rx, rz), chunks in regions.items():
        write_region(os.path.join(dim, "region", f"r.{rx}.{rz}.mca"), chunks)
    for (rx, rz), chunks in entity_regions.items():
        write_region(os.path.join(dim, "entities", f"r.{rx}.{rz}.mca"), chunks)

    write_level_dat(os.path.join(out, "level.dat"), name, spawn, yaw, cols.n)
    write_objects(os.path.join(out, "aoe2mc.json"), size, T, H, players, objects, cols, ground)
    n, amb = write_datapack(out, objects, ground, cols.biome_names, ambience)
    if n:
        print(f"  work sounds at buildings: {n}")
    if amb:
        print(f"  ambience (particles and sounds by biome): {amb} lines"
              + (", custom biomes (Minecraft shows the experimental warning)" if ambience == "full" else ""))

    from PIL import Image
    lut = np.array([block_color(s) for s in B.states], np.uint8)
    img = lut[top_view[:cols.n, :cols.n].T]                     # rows = z, columns = x
    shade = np.clip(1 + (cols.wtop[:cols.n, :cols.n].T - WATER_Y) * 0.02, 0.6, 1.4)
    img = Image.fromarray(np.clip(img * shade[..., None], 0, 255).astype(np.uint8))
    if preview:
        img.save(os.path.join(out, "preview.png"))
    # the world list shows icon.png; keep the pixels sharp when the map is smaller than the icon
    img.resize((64, 64), Image.LANCZOS if cols.n >= 64 else Image.NEAREST).save(os.path.join(out, "icon.png"))

    bridge = MOVED.pop("(on a bridge)", 0)
    if bridge:
        print(f"  units on bridges: {bridge}")
    print(f"  units in a block (moved up): {sum(MOVED.values())}")
    tick("write")
    if verbose:
        print("  time: " + ", ".join(f"{k} {v:.1f}s" for k, v in times.items()))
    print(f"Wrote {sum(map(len, regions.values()))} chunks, {cols.n}x{cols.n} blocks, to {out} "
          f"({time.time() - t0:.1f}s). Spawn: {spawn}")


class OptionError(ValueError):
    """A command-line option that does not match the scenario."""


def int_range(lo, hi):
    def parse(v):
        try:
            n = int(v)
        except ValueError:
            raise argparse.ArgumentTypeError(f"{v!r} is not an integer") from None
        if not lo <= n <= hi:
            raise argparse.ArgumentTypeError(f"{n} is not in the range {lo}-{hi}")
        return n
    return parse


def player_arch_spec(v):
    """'6=western' -> (6, 'western')."""
    pid, eq, a = v.partition("=")
    if not eq or not pid.strip().isdigit():
        raise argparse.ArgumentTypeError(f"{v!r} is not P=SET, for example 6=western")
    if a not in buildings.ARCH:
        raise argparse.ArgumentTypeError(f"unknown set {a!r} (choose from {', '.join(sorted(buildings.ARCH))})")
    return int(pid), a


def spawn_spec(v):
    """'12,30' -> (12.0, 30.0)."""
    try:
        x, z = (float(t) for t in v.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError(f"{v!r} is not X,Z, for example 12,30") from None
    return x, z


class CampaignError(ValueError):
    """A campaign file that aoe2mc cannot read."""


def read_campaign(path):
    """.aoe2campaign or .cpx/.cpn -> (version, campaign name, [(scenario file name, scenario bytes)]).
    Layout: docs/campaign-formats.md."""
    import struct
    with open(path, "rb") as f:
        b = f.read()

    def text(raw):                                                  # old files use the code page of the author
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("cp1252", "replace")

    def de_string(o):
        if b[o:o + 2] != b"\x60\x0a":
            raise CampaignError(f"{path}: no string at byte {o}: the file is not a valid campaign")
        n = struct.unpack_from("<H", b, o + 2)[0]
        return text(b[o + 4:o + 4 + n]), o + 4 + n

    version = b[:4]
    if version not in (b"1.00", b"2.00"):
        raise CampaignError(f"{path}: version {version!r} is not 1.00 (.cpx, .cpn) or 2.00 (.aoe2campaign)")
    try:
        o = 4 if version == b"1.00" else 8 + 4 * struct.unpack_from("<I", b, 4)[0]   # 2.00: DLC dependencies
        name = text(b[o:o + 256].split(b"\0")[0])
        n = struct.unpack_from("<I", b, o + 256)[0]
        o += 260
        entries = []
        for _ in range(n):
            size, off = struct.unpack_from("<II", b, o)
            if version == b"1.00":                                   # fixed strings of 255 bytes, 2 bytes padding
                file_name = text(b[o + 263:o + 518].split(b"\0")[0])
                o += 520
            else:
                _, o = de_string(o + 8)                                 # the scenario name
                file_name, o = de_string(o)
            if off + size > len(b):
                raise CampaignError(f"{path}: scenario {file_name!r} ends after the end of the file")
            entries.append((file_name, b[off:off + size]))
    except struct.error:
        raise CampaignError(f"{path}: the file ends in the header: the file is not a valid campaign") from None
    return version, name, entries


OLD_CAMPAIGN_STEPS = """\
The scenarios of this campaign use the old scenario format ({ext}). aoe2mc cannot read it.
aoe2mc wrote the scenario files to {out}:
{files}
Do these steps to convert them:
  1. Copy the files to the scenario folder of AoE2 DE:
     <Steam user folder>/Games/Age of Empires 2 DE/<number>/resources/_common/scenario
  2. Start AoE2 DE. In the scenario editor, open each scenario and save it. DE saves it as .aoe2scenario.
  3. Convert each .aoe2scenario file with aoe2mc. Or, in the DE campaign editor, make a campaign of the
     scenarios and convert the .aoe2campaign file."""


def convert_campaign(src, out, only=None, name=None, **kw):
    """One world per scenario: out/<number> <scenario name>/. only: the number of one scenario (1 = first).
    An old campaign (.cpx, .cpn): write the old scenario files to out/ and stop with the steps for the DE editor."""
    import tempfile
    version, title, entries = read_campaign(src)
    if only is not None and not 1 <= only <= len(entries):
        raise OptionError(f"--scenario {only}: the campaign {title!r} has {len(entries)} scenarios")
    print(f"Campaign {title!r}: {len(entries)} scenarios")
    chosen = [(i, re.sub(r'[\\/:*?"<>|]', "_", fn), data) for i, (fn, data) in enumerate(entries, 1)
              if only is None or i == only]
    if version == b"1.00":
        os.makedirs(out, exist_ok=True)
        for i, fn, data in chosen:
            with open(os.path.join(out, f"{i} {fn}"), "wb") as f:
                f.write(data)
        exts = sorted({os.path.splitext(fn)[1] or "?" for _, fn, _ in chosen})
        raise SystemExit(OLD_CAMPAIGN_STEPS.format(ext=", ".join(exts), out=out,
                                                   files="\n".join(f"  {i} {fn}" for i, fn, _ in chosen)))
    for i, fn, data in chosen:
        stem = re.sub(r"\.aoe2scenario$", "", fn, flags=re.I)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, stem + ".aoe2scenario")
            with open(path, "wb") as f:
                f.write(data)
            convert(path, os.path.join(out, f"{i} {stem}"), name=f"{name} {i}" if name else stem, **kw)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Convert an AoE2 DE scenario to a Minecraft Java world.")
    ap.add_argument("scenario", help=".aoe2scenario file, .aoe2record (the start state of a recorded game), .scx "
                    "(an old scenario, format 1.21), or "
                    ".aoe2campaign (one world per scenario; .cpx and .cpn: the steps for the DE editor)")
    ap.add_argument("output", help="output world folder (put it in .minecraft/saves/); for a campaign the folder of "
                    "the worlds")
    ap.add_argument("--scenario", dest="only", type=int_range(1, 999), metavar="N",
                    help="campaign: convert only scenario N (1 = the first)")
    ap.add_argument("--tile-size", type=int_range(1, 16), default=4, help="blocks per tile (default 4)")
    ap.add_argument("--level-height", type=int_range(1, 16), default=3, help="blocks per elevation level (default 3)")
    ap.add_argument("--name", help="world name in the Minecraft menu")
    ap.add_argument("--seed", type=int, default=1, help="seed for random details (default 1)")
    ap.add_argument("--preview", action="store_true", help="also write preview.png")
    ap.add_argument("--architecture", choices=sorted(buildings.ARCH),
                    help="use one architecture set for all players (default: from each player's civilization)")
    ap.add_argument("--no-units", action="store_true", help="do not convert units (mobs, boats, minecarts)")
    ap.add_argument("--no-birds", action="store_true", help="do not convert birds")
    ap.add_argument("--no-barriers", action="store_true",
                    help="do not fill building footprints with invisible barrier blocks")
    ap.add_argument("--player-architecture", action="append", default=[], metavar="P=SET",
                    type=player_arch_spec,
                    help="architecture set for one player, for example 6=western (can be repeated)")
    ap.add_argument("--spawn", type=spawn_spec, metavar="X,Z",
                    help="player spawn in tiles (default: start view or town center of player 1)")
    ap.add_argument("--garrison", choices=("outside", "skip"), default="outside",
                    help="garrisoned units: ride their ship or stand next to their holder (default), or skip them")
    ap.add_argument("--mc-version", choices=sorted(VERSIONS), default=VERSION_NAME,
                    help=f"Minecraft Java version of the output (default {VERSION_NAME})")
    ap.add_argument("--orientation", choices=sorted(ORIENTATIONS), default="ne",
                    help="Minecraft corner of the top corner of the AoE2 screen (default ne)")
    ap.add_argument("--border", choices=sorted(BORDERS), default="diorama",
                    help="design of the edge outside the map (default diorama); all keep the vanilla world border at the edge")
    ap.add_argument("--ambience", choices=("basic", "full", "off"), default="basic",
                    help="work sounds at buildings, animal sounds, and particles and sounds by terrain (default basic); "
                         "full also gives each terrain group a custom biome with its own sky, fog and water colors, but "
                         "Minecraft then shows an \"Experimental Settings\" warning when the world opens; off: a "
                         "silent world without a datapack")
    ap.add_argument("--verbose", action="store_true", help="print the time of each phase")
    a = ap.parse_args(argv)
    kw = dict(T=a.tile_size, H=a.level_height, seed=a.seed, preview=a.preview, arch=a.architecture,
              player_arch=a.player_architecture, with_units=not a.no_units, barriers=not a.no_barriers,
              mc_version=a.mc_version, spawn=a.spawn, birds=not a.no_birds, orientation=a.orientation,
              verbose=a.verbose, garrison=a.garrison, border_design=a.border, ambience=a.ambience)
    try:
        if a.scenario.lower().endswith((".aoe2campaign", ".cpx", ".cpn")):
            convert_campaign(a.scenario, a.output, a.only, a.name, **kw)
        elif a.only is not None:
            ap.error("--scenario needs a campaign file (.aoe2campaign, .cpx, .cpn)")
        else:
            convert(a.scenario, a.output, name=a.name, **kw)
    except (OptionError, CampaignError) as e:
        ap.error(str(e))


if __name__ == "__main__":
    main()
