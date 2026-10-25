#!/usr/bin/env python3
"""
aoe2mc - Convert an Age of Empires II: DE scenario (.aoe2scenario) to a Minecraft Java world.

Usage:
    python aoe2mc.py MAP.aoe2scenario OUTPUT_WORLD_FOLDER [options]

Options:
    --tile-size N      Minecraft blocks per AoE2 tile, in each direction (default 4)
    --level-height N   Minecraft blocks per AoE2 elevation level (default 3)
    --name TEXT        World name in the Minecraft menu (default: file name)
    --seed N           Seed for the random details (tree heights, flowers) (default 1)
    --preview          Also write preview.png (top view) into the world folder
    --no-units         Do not convert units (mobs, boats, minecarts)
    --no-barriers      Do not fill building footprints with invisible barrier blocks
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
import os
import time
import zlib
from collections import Counter

import numpy as np
from nbtlib import File
from nbtlib.tag import Byte, Compound, Double, Float, Int, IntArray, List, Long, LongArray, String

import buildings
import units

DATA_VERSION = 3955          # Minecraft Java 1.21.1
VERSION_NAME = "1.21.1"
MIN_Y, MAX_Y = -64, 320      # world height range (MAX_Y exclusive)
HEIGHT = MAX_Y - MIN_Y
WATER_Y = 62                 # Y of the highest water block (sea level)
NONE = -10000                # marker for "no column here" (outside the map)


# --------------------------------------------------------------------------------------------
# Block registry: one integer per block state, so that the world can be numpy arrays.
# --------------------------------------------------------------------------------------------
class Blocks:
    def __init__(self):
        self.states = ["minecraft:air"]
        self.index = {"minecraft:air": 0}

    def __call__(self, state):
        if not state.startswith("minecraft:"):
            state = "minecraft:" + state
        i = self.index.get(state)
        if i is None:
            i = len(self.states)
            self.states.append(state)
            self.index[state] = i
        return i

    def nbt(self, i):
        """Palette entry for block id i: {Name, Properties}."""
        state = self.states[i]
        if "[" not in state:
            return Compound({"Name": String(state)})
        name, props = state[:-1].split("[", 1)
        p = dict(kv.split("=") for kv in props.split(","))
        return Compound({"Name": String(name),
                         "Properties": Compound({k: String(v) for k, v in p.items()})})


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
    if "GRAVEL" in n:
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
def read_scenario(path):
    from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
    from AoE2ScenarioParser.datasets.terrains import TerrainId
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo
    from AoE2ScenarioParser.datasets.other import OtherInfo
    from AoE2ScenarioParser.datasets.units import UnitInfo

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

    from AoE2ScenarioParser.datasets.heroes import HeroInfo
    kinds = {}
    for prefix, enum in (("H", HeroInfo), ("U", UnitInfo), ("O", OtherInfo), ("B", BuildingInfo)):
        for e in enum:          # later enums win: Building > Other > Unit > Hero
            kinds[e.ID] = (prefix, e.name)

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
        players[p.player_id] = {"color": color if p.player_id else "light_gray", "arch": arch,
                                "civ": getattr(civ, "name", "?")}

    objects = []
    for player, player_units in enumerate(scn.unit_manager.units):
        for u in player_units:
            prefix, name = kinds.get(u.unit_const, ("?", f"UNKNOWN_{u.unit_const}"))
            garrisoned = u.garrisoned_in_id not in (None, -1)
            objects.append(dict(kind="U" if prefix == "H" else prefix, hero=prefix == "H", name=name,
                                player=player, x=u.x, y=u.y, rotation=float(u.rotation or 0), garrisoned=garrisoned))
    return size, terrain, elevation, terrain_names, objects, players


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
        water_bottom = (WATER_Y - np.maximum(1, np.rint(depth))).astype(np.int16)

        def full(fill, dtype):
            a = np.full((W, W), fill, dtype)
            return a

        self.top = full(NONE, np.int16)
        self.wtop = full(NONE, np.int16)
        self.top[:n, :n] = np.where(is_water, water_bottom, land)
        self.wtop[:n, :n] = np.where(is_water, WATER_Y, self.top[:n, :n])

        lut = lambda key: np.array([B(s[key]) for s in styles], np.uint16)
        sub_lut = np.array([B(s["bottom"] if s["depth"] else s["sub"]) for s in styles], np.uint16)
        self.top_id = full(AIR, np.uint16)
        self.sub_id = full(AIR, np.uint16)
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
        # roads: a mix of stones with worn patches, rough edges and worn verges next to the road
        road = g == 5
        if road.any():
            def near(mask):
                m = np.zeros_like(mask)
                m[1:] |= mask[:-1]; m[:-1] |= mask[1:]; m[:, 1:] |= mask[:, :-1]; m[:, :-1] |= mask[:, 1:]
                return m
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

        # roads: a mix of stones, moss in quiet places, and worn edges
        cobble = (top == B("cobblestone")) & (g == 0)
        gravel_road = (top == B("gravel")) & (g == 0)
        road = cobble | gravel_road
        mix = [("andesite", .12), ("gravel", .08), ("stone", .06), ("polished_andesite", .04), ("tuff", .03)]
        acc = 0.0
        for b, share in mix:
            top[cobble & (r >= acc) & (r < acc + share)] = B(b)
            acc += share
        top[cobble & (r >= acc) & (r < acc + 0.25) & (n2 > 0.55)] = B("mossy_cobblestone")
        top[gravel_road & (r < 0.15)] = B("coarse_dirt")
        top[gravel_road & (r >= 0.15) & (r < 0.22)] = B("cobblestone")
        top[gravel_road & (r >= 0.22) & (r < 0.3)] = B("dirt_path")
        land = (g > 0)
        near_land = np.zeros_like(road)
        near_road = np.zeros_like(road)
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            near_land |= np.roll(np.roll(land, dx, 0), dz, 1)
            near_road |= np.roll(np.roll(road, dx, 0), dz, 1)
        edge = road & near_land
        top[edge & (r2 < 0.35)] = B("dirt_path")
        top[edge & (r2 >= 0.35) & (r2 < 0.5)] = B("coarse_dirt")
        worn = land & near_road & ~road
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

    def by_chunk(self, width):
        """Return {(cx, cz): (x, y, z, id, hard)} with local x/z, in the order of addition."""
        if not self.parts:
            return {}
        x, y, z, ids, hard = (np.concatenate(p) for p in zip(*self.parts))
        ok = (x >= 0) & (z >= 0) & (x < width) & (z < width) & (y >= MIN_Y) & (y < MAX_Y)
        x, y, z, ids, hard = x[ok], y[ok], z[ok], ids[ok], hard[ok]
        key = (x >> 4) * 100000 + (z >> 4)
        order = np.argsort(key, kind="stable")
        x, y, z, ids, hard, key = x[order], y[order], z[order], ids[order], hard[order], key[order]
        keys, starts = np.unique(key, return_index=True)
        ends = list(starts[1:]) + [len(key)]
        out = {}
        for k, s, e in zip(keys, starts, ends):
            out[(int(k // 100000), int(k % 100000))] = (x[s:e] & 15, y[s:e], z[s:e] & 15, ids[s:e], hard[s:e])
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
    elif "BONFIRE" in n:
        put(0, 0, 0, "campfire[lit=true,signal_fire=false]")
    elif n == "SIGN":
        put(0, 0, 0, "oak_sign[rotation=8]")
    elif "GALLOW" in n:
        put(-1, 0, 0, "dark_oak_fence"); put(-1, 1, 0, "dark_oak_fence"); put(-1, 2, 0, "dark_oak_fence")
        E.box(cx - 1, cx + 2, y + 3, y + 4, cz, cz + 1, "dark_oak_log[axis=x]"); put(1, 2, 0, "chain")
    elif "OYSTER" in n:
        x, z = min(max(cx, 0), cols.n - 1), min(max(cz, 0), cols.n - 1)
        if cols.wtop[x, z] > cols.top[x, z]:
            E.add([x], [int(cols.top[x, z]) + 1], [z], "sea_pickle[pickles=3]")
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
PASSABLE_OBJECTS = ("FLOWER", "FERN", "RUG", "GRASS", "PLANT", "OYSTER", "FISH", "RELIC", "GRAVE", "BONFIRE")


def object_footprint(o, T):
    """Block area (x0, x1, z0, z1) of a non-building object. An object at x.0 has an even size, at x.5 an odd size."""
    n = o["name"]
    big = 4 if n.startswith("MOUNTAIN") else 3 if n.startswith("CLIFF") or "QUARRY" in n or "TEMPLE" in n else 0

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
        elif kind == "O" and "TREE" in name:
            make_tree(E, tree_kind(name), bx, y, bz, rng)
            stats["trees"] += 1
        elif kind == "O" and name == "GOLD_MINE":
            tile_heap(E, cols, E.footprint, 3, ["gold_ore", "gold_ore", "raw_gold_block", "stone"], rng)
            stats["gold mines"] += 1
        elif kind == "O" and name == "STONE_MINE":
            tile_heap(E, cols, E.footprint, 3, ["cobblestone", "andesite", "stone", "tuff"], rng)
            stats["stone mines"] += 1
        elif kind == "O" and name.startswith("MOUNTAIN"):
            mound(E, cols, bx, bz, T * 2, T * 4, ["stone", "stone", "andesite", "cobblestone", "tuff"], rng)
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
        elif kind == "O" and (name.startswith("STATUE") or name.startswith("STELAE")):
            h = 2 if name.startswith("STELAE") else 4
            E.box(bx, bx + 1, y, y + h, bz, bz + 1, "chiseled_sandstone" if name.startswith("STELAE") else "quartz_pillar")
            E.add([bx], [y + h], [bz], "chiseled_quartz_block" if name.startswith("STATUE") else "sandstone_slab[type=bottom]")
            stats["decorations"] += 1
        elif kind == "O" and name == "RUGS":
            E.box(bx - 1, bx + 1, y, y + 1, bz - 1, bz + 2, ["red_carpet", "orange_carpet", "brown_carpet"][int(rng.integers(3))], hard=False)
            stats["decorations"] += 1
        elif kind == "O" and name in ("VASES", "GOODS", "BARRELS"):
            things = {"VASES": ["decorated_pot[facing=south,cracked=false]"] * 3,
                      "GOODS": ["barrel[facing=up]", "hay_block", "chest[facing=south]"],
                      "BARRELS": ["barrel[facing=up]"] * 3}[name]
            E.add([bx, bx + 1, bx], [y, y, y], [bz, bz, bz + 1], [B(t) for t in things])
            stats["decorations"] += 1
        elif kind == "O" and name == "CACTUS":
            E.box(bx, bx + 1, y, y + 2, bz, bz + 1, "cactus")
            stats["plants"] += 1
        elif kind == "O" and (name.startswith("PLANT") or name == "FERN_PATCH"):
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
        elif kind == "O" and name in ("CRATER", "SMOKE", "CRACKS") or name.startswith("WATERFALL"):
            pass
        elif kind == "O" and name == "BONFIRE":
            E.add([bx], [y], [bz], "campfire[lit=true,signal_fire=false]")
            stats["decorations"] += 1
        elif kind == "O" and "DISMANTLED_CART" in name:
            E.add([bx, bx + 1, bx - 1, bx], [y, y, y, y + 1], [bz, bz, bz + 1, bz],
                  [B("spruce_slab[type=bottom]"), B("spruce_log[axis=x]"), B("barrel[facing=up]"), B("spruce_trapdoor[facing=north,half=bottom,open=true]")])
            stats["decorations"] += 1
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
        else:
            if name.startswith("UNKNOWN"):
                stats["skipped (unknown to the parser)"] += 1
            elif kind != "U" and "FISH" not in name:
                stats["skipped (other objects)"] += 1
        if kind == "O" and (("TREE" in name and "STUMP" not in name) or name in ("GOLD_MINE", "STONE_MINE", "QUARRY")
                            or "FORAGE" in name or "FRUIT_BUSH" in name or name.startswith(("CLIFF", "MOUNTAIN", "ROCK", "STATUE", "TROPAION",
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
FISH = [("SALMON", "salmon"), ("DORADO", "tropical_fish"), ("SNAPPER", "tropical_fish"), ("FISH", "cod")]
PASSABLE = ("short_grass", "tall_grass", "large_fern", "petals", "moss_carpet", "mushroom", "allium", "bluet",
            "tulip", "lily_of", "fern", "wheat", "poppy", "dandelion", "cornflower", "daisy", "water",
            "seagrass", "dead_bush", "sweet_berry", "rail", "carpet", "banner", "button", "lantern", "snow[")


def plan_units(objects, players, cols, rng, stats):
    """Entities per chunk: {(cx, cz): [(nbt, x, z, is_boat)]}."""
    T = cols.T
    out = {}
    for o in objects:
        if o["kind"] == "U":
            if o.get("garrisoned"):
                stats["units (garrisoned, skipped)"] += 1
                continue
            desc = units.classify(o["name"], o.get("hero", False))
            if desc is None:
                continue
            nbt = units.make_entity(o, players, (0, 0, 0), rng, desc)
            boat = units.is_boat(desc)
            stats["units"] += 1
        elif o["kind"] == "O" and "FISH" in o["name"]:
            kind = next(k for key, k in FISH if key in o["name"])
            nbt = units.to_nbt(units.mob(kind), (0, 0, 0), 0.0, rng)
            boat = "fish"
            stats["fish"] += 1
        else:
            continue
        x, z = o["x"] * T, o["y"] * T
        bx, bz = int(x), int(z)
        if not cols.inside(bx, bz):
            continue
        if cols.blocked[bx, bz] and boat is not True:
            spot = free_spot(cols, bx, bz, 6 * T, water=boat == "fish")
            if spot is None:
                stats["units (inside a building, no free space)"] += 1
                continue
            x, z = spot[0] + 0.5, spot[1] + 0.5
            bx, bz = spot
            stats["units moved out of a building or obstacle"] += 1
        out.setdefault((bx >> 4, bz >> 4), []).append((nbt, x, z, boat))
    return out


def top_name(nbt):
    t = units.top_entity(nbt)
    return t.get("CustomName", t["id"])


def free_spot(cols, bx, bz, r, water=False):
    """Nearest column that is not blocked (and on land, unless water=True), or None."""
    x0, x1 = max(0, bx - r), min(cols.n, bx + r + 1)
    z0, z1 = max(0, bz - r), min(cols.n, bz + r + 1)
    ok = ~cols.blocked[x0:x1, z0:z1]
    wet = cols.wtop[x0:x1, z0:z1] - cols.top[x0:x1, z0:z1]
    ok &= (wet >= 2) if water else (wet <= 1)
    xs, zs = np.nonzero(ok)
    if not len(xs):
        return None
    d = (xs + x0 - bx) ** 2 + (zs + z0 - bz) ** 2
    i = int(np.argmin(d))
    return int(xs[i] + x0), int(zs[i] + z0)


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
            y = WATER_Y + 0.5
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
        set_pos(nbt, x, float(y), z)
        out.append(nbt)
    if not out:
        return None
    root = Compound({"DataVersion": Int(DATA_VERSION), "Position": IntArray([cx, cz]),
                     "Entities": List[Compound](out)})
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
            ("smoker", "smoker"), ("furnace", "furnace"), ("lectern", "lectern")]


def block_entity_type(state):
    name = state.split(":")[1].split("[")[0]
    for key, be in BE_TYPES:
        if key in name:
            return be
    return None


def palette_entry(i):
    if i not in PALETTE_CACHE:
        PALETTE_CACHE[i] = B.nbt(i)
    return PALETTE_CACHE[i]


SHORT_GRASS = B("short_grass")
BARRIER = B("barrier")
TALL_PLANTS = [(B("tall_grass[half=lower]"), B("tall_grass[half=upper]")),
               (B("large_fern[half=lower]"), B("large_fern[half=upper]"))]


def build_chunk(cx, cz, cols, edits):
    x0, z0 = cx * 16, cz * 16
    sl = (slice(x0, x0 + 16), slice(z0, z0 + 16))
    g = lambda a: a[sl].T[None]          # (1, z, x) for broadcasting against Y
    top, wtop, top_id, sub_id = g(cols.top), g(cols.wtop), g(cols.top_id), g(cols.sub_id)
    ice, deco = g(cols.ice), cols.deco[sl].T
    Y = np.arange(MIN_Y, MAX_Y, dtype=np.int32)[:, None, None]

    vol = np.where(Y < top - 3, np.where(Y < 0, DEEPSLATE, STONE), AIR).astype(np.uint16)
    vol = np.where((Y >= top - 3) & (Y < top), sub_id, vol)
    vol = np.where(Y == top, top_id, vol)
    water = (Y > top) & (Y <= wtop)
    vol = np.where(water, np.where(ice & (Y == wtop), ICE, WATER), vol)
    vol[0] = np.where(top[0] > NONE, BEDROCK, AIR)
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
    for lower, upper in TALL_PLANTS:
        ys, zs, xs = np.nonzero(vol[1:] == upper)
        bad = vol[ys, zs, xs] != lower
        vol[ys[bad] + 1, zs[bad], xs[bad]] = AIR
        ys, zs, xs = np.nonzero(vol[:-1] == lower)
        bad = vol[ys + 1, zs, xs] != upper
        vol[ys[bad], zs[bad], xs[bad]] = SHORT_GRASS

    # Biomes: one per 4x4 block cell, the same for all heights.
    cells = cols.biome[x0 + 2:x0 + 16:4, z0 + 2:z0 + 16:4].T            # (z, x) 4x4
    bvals, binv = np.unique(np.tile(cells.ravel(), 4), return_inverse=True)
    biomes = Compound({"palette": List[String]([String(cols.biome_names[v]) for v in bvals])})
    if len(bvals) > 1:
        biomes["data"] = LongArray(pack(binv, max(1, int(np.ceil(np.log2(len(bvals)))))))

    block_entities = []
    be_ids = [i for i in np.unique(vol) if block_entity_type(B.states[i])]
    for i in be_ids:
        for y, z, x in zip(*np.nonzero(vol == i)):
            block_entities.append(Compound({
                "id": String("minecraft:" + block_entity_type(B.states[i])), "keepPacked": Byte(0),
                "x": Int(x0 + int(x)), "y": Int(int(y) + MIN_Y), "z": Int(z0 + int(z))}))

    sections = []
    for s in range(HEIGHT // 16):
        sec = vol[s * 16:(s + 1) * 16].ravel()            # index = y*256 + z*16 + x
        vals, inv = np.unique(sec, return_inverse=True)
        states = Compound({"palette": List[Compound]([palette_entry(int(v)) for v in vals])})
        if len(vals) > 1:
            states["data"] = LongArray(pack(inv, max(4, int(np.ceil(np.log2(len(vals)))))))
        sections.append(Compound({"Y": Byte(s + MIN_Y // 16), "block_states": states,
                                  "biomes": biomes}))

    chunk = Compound({
        "DataVersion": Int(DATA_VERSION), "xPos": Int(cx), "zPos": Int(cz), "yPos": Int(MIN_Y // 16),
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
    """chunks: {(local_x, local_z): nbt_bytes}"""
    header = bytearray(8192)
    body = bytearray()
    now = int(time.time())
    for (lx, lz), data in chunks.items():
        comp = zlib.compress(data, 6)
        payload = (len(comp) + 1).to_bytes(4, "big") + b"\x02" + comp
        payload += b"\x00" * (-len(payload) % 4096)
        offset = 2 + len(body) // 4096
        sectors = len(payload) // 4096
        i = 4 * (lx + lz * 32)
        header[i:i + 4] = offset.to_bytes(3, "big") + bytes([sectors])
        header[4096 + i:4096 + i + 4] = now.to_bytes(4, "big")
        body += payload
    with open(path, "wb") as f:
        f.write(header + body)


def write_level_dat(path, name, spawn):
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
        "DataVersion": Int(DATA_VERSION), "version": Int(19133),
        "Version": Compound({"Id": Int(DATA_VERSION), "Name": String(VERSION_NAME),
                             "Series": String("main"), "Snapshot": Byte(0)}),
        "LevelName": String(name), "GameType": Int(1), "Difficulty": Byte(1),   # not peaceful: peaceful removes the soldiers
        "allowCommands": Byte(1), "hardcore": Byte(0), "initialized": Byte(1),
        "SpawnX": Int(spawn[0]), "SpawnY": Int(spawn[1]), "SpawnZ": Int(spawn[2]), "SpawnAngle": Float(0),
        "LastPlayed": Long(int(time.time() * 1000)), "Time": Long(0), "DayTime": Long(6000),
        "raining": Byte(0), "thundering": Byte(0), "rainTime": Int(0), "thunderTime": Int(0),
        "clearWeatherTime": Int(0), "WasModded": Byte(0),
        "GameRules": Compound({"doDaylightCycle": String("false"), "doWeatherCycle": String("false"),
                               "doMobSpawning": String("false"), "doFireTick": String("false")}),
        "DataPacks": Compound({"Enabled": List[String]([String("vanilla")]), "Disabled": List[String]([])}),
        "WorldGenSettings": Compound({
            "seed": Long(0), "generate_features": Byte(0), "bonus_chest": Byte(0),
            "dimensions": Compound({"minecraft:overworld": dim("overworld", void),
                                    "minecraft:the_nether": dim("the_nether", nether),
                                    "minecraft:the_end": dim("the_end", end)})}),
    })
    File({"Data": data}, gzipped=True).save(path)


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
            barriers=True):
    buildings.BARRIERS = barriers
    MOVED.clear()           # the counts of an earlier conversion in this process
    rng = np.random.default_rng(seed)
    t0 = time.time()
    size, terrain, elevation, tnames, objects, players = read_scenario(src)
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

    cols = Columns(size, terrain, elevation, tnames, T, H, rng)
    for pid, p in sorted(players.items()):
        if pid and any(o["player"] == pid for o in objects):
            print(f"  player {pid}: {p['civ'].lower()}, {p['color']}, {p['arch']} buildings")
    edits, stats = place_objects(objects, players, cols, rng)
    for k, v in sorted(stats.items()):
        print(f"  {k}: {v}")
    per_chunk = edits.by_chunk(cols.width)
    unit_chunks = plan_units(objects, players, cols, rng, stats) if with_units else {}
    print(f"  units: {stats['units']}, fish: {stats['fish']}")
    passable = np.array([st.split(":")[1].split("[")[0] in ("air", "cave_air") or
                         any(k in st.split(":")[1] for k in PASSABLE) and "grass_block" not in st
                         for st in B.states] + [True] * 1024)

    os.makedirs(os.path.join(out, "region"), exist_ok=True)
    os.makedirs(os.path.join(out, "entities"), exist_ok=True)
    entity_regions = {}
    nchunks = cols.width // 16
    regions = {}
    top_view = np.zeros((cols.width, cols.width), np.uint16) if preview else None
    for cx in range(nchunks):
        for cz in range(nchunks):
            data, vol = build_chunk(cx, cz, cols, per_chunk.get((cx, cz)))
            regions.setdefault((cx >> 5, cz >> 5), {})[(cx & 31, cz & 31)] = data
            if (cx, cz) in unit_chunks:
                ed = entity_chunk(cx, cz, unit_chunks[(cx, cz)], cols, vol, passable)
                if ed:
                    entity_regions.setdefault((cx >> 5, cz >> 5), {})[(cx & 31, cz & 31)] = ed
            if preview:
                solid = (vol != AIR) & (vol != BARRIER)
                hi = HEIGHT - 1 - np.argmax(solid[::-1], axis=0)
                top_view[cx * 16:cx * 16 + 16, cz * 16:cz * 16 + 16] = \
                    np.take_along_axis(vol, hi[None], 0)[0].T
    for (rx, rz), chunks in regions.items():
        write_region(os.path.join(out, "region", f"r.{rx}.{rz}.mca"), chunks)
    for (rx, rz), chunks in entity_regions.items():
        write_region(os.path.join(out, "entities", f"r.{rx}.{rz}.mca"), chunks)

    c = cols.n // 2
    spawn = (c, cols.surface(c, c) + 2, c)
    write_level_dat(os.path.join(out, "level.dat"), name or os.path.splitext(os.path.basename(src))[0], spawn)

    if preview:
        from PIL import Image
        lut = np.array([block_color(s) for s in B.states], np.uint8)
        img = lut[top_view[:cols.n, :cols.n].T]                 # rows = z, columns = x
        shade = np.clip(1 + (cols.wtop[:cols.n, :cols.n].T - WATER_Y) * 0.02, 0.6, 1.4)
        img = np.clip(img * shade[..., None], 0, 255).astype(np.uint8)
        Image.fromarray(img).save(os.path.join(out, "preview.png"))

    bridge = MOVED.pop("(on a bridge)", 0)
    if bridge:
        print(f"  units on bridges: {bridge}")
    print(f"  units in a block (moved up): {sum(MOVED.values())}")
    print(f"Wrote {nchunks * nchunks} chunks, {cols.n}x{cols.n} blocks, to {out} "
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


def main(argv=None):
    ap = argparse.ArgumentParser(description="Convert an AoE2 DE scenario to a Minecraft Java world.")
    ap.add_argument("scenario", help=".aoe2scenario file")
    ap.add_argument("output", help="output world folder (put it in .minecraft/saves/)")
    ap.add_argument("--tile-size", type=int_range(1, 16), default=4, help="blocks per tile (default 4)")
    ap.add_argument("--level-height", type=int_range(1, 16), default=3, help="blocks per elevation level (default 3)")
    ap.add_argument("--name", help="world name in the Minecraft menu")
    ap.add_argument("--seed", type=int, default=1, help="seed for random details (default 1)")
    ap.add_argument("--preview", action="store_true", help="also write preview.png")
    ap.add_argument("--architecture", choices=sorted(buildings.ARCH),
                    help="use one architecture set for all players (default: from each player's civilization)")
    ap.add_argument("--no-units", action="store_true", help="do not convert units (mobs, boats, minecarts)")
    ap.add_argument("--no-barriers", action="store_true",
                    help="do not fill building footprints with invisible barrier blocks")
    ap.add_argument("--player-architecture", action="append", default=[], metavar="P=SET",
                    type=player_arch_spec,
                    help="architecture set for one player, for example 6=western (can be repeated)")
    a = ap.parse_args(argv)
    try:
        convert(a.scenario, a.output, a.tile_size, a.level_height, a.name, a.seed, a.preview, a.architecture,
                a.player_architecture, not a.no_units, not a.no_barriers)
    except OptionError as e:
        ap.error(str(e))


if __name__ == "__main__":
    main()
