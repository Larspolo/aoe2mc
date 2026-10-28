#!/usr/bin/env python3
"""
aoe2mc - Convert an Age of Empires II: DE scenario (.aoe2scenario) or the start state of a recorded game
(.aoe2record) or an old scenario (.scx, format 1.21) to a Minecraft Java world. A campaign (.aoe2campaign) gives one world per scenario; an old campaign
(.cpx, .cpn) too; its scenarios that are not .scx 1.21 give the files and the steps to save them in the DE editor.

Usage:
    python aoe2mc.py MAP.aoe2scenario OUTPUT_WORLD_FOLDER [options]

Options:
    --tile-size N      Minecraft blocks per AoE2 tile, in each direction (default 4)
    --level-height N   Minecraft blocks per AoE2 elevation level (default 3)
    --name TEXT        World name in the Minecraft menu (default: file name)
    --seed N           Seed for the random details (tree heights, flowers), of a random map script (.rms) and
                       of --random-map (default 1)
    --random-map KIND  Make the map with an own generator (arabia, arena, black_forest, gold_rush, highland,
                       islands, mediterranean, nomad), no input file:
                       aoe2mc.py --random-map arabia OUT
    --preview          Also write preview.png (top view) into the world folder
    --mc-version V     Minecraft Java version of the output: 26.3 (default, the only one)
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
The world is saved with Minecraft data version 26.3. Newer Minecraft versions upgrade it on load.
"""
import argparse
import contextlib
import functools
import hashlib
import io
import json
import math
import os
import re
import sys
import textwrap
import time
import zlib
from collections import Counter, namedtuple

import numpy as np
from nbtlib import File
from nbtlib.tag import Byte, ByteArray, Compound, Double, Float, Int, IntArray, List, Long, LongArray, String

import buildings
import units

# Blocks with the 'waterlogged' property. A block of this list under the water surface gets waterlogged=true (#19).
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools", "mcdata", "26.3.json")) as _f:
    BLOCK_PROPS = {"minecraft:" + k: v for k, v in json.load(_f)["blocks"].items()}
WATERLOGGABLE = {k for k, v in BLOCK_PROPS.items() if "waterlogged" in v}

# Output format per Minecraft Java version (docs/minecraft-versions.md): only 26.3 (#427); a later 26.x version can
# get its own entry. The code uses the 26.3 block and entity names (#428).
VERSIONS = {
    "26.3": dict(name="26.3", data_version=5023, pack_format=121, resource_format=97),   # resource: version.json
}
VERSION_NAME = "26.3"        # the default output version
DATA_VERSION = VERSIONS[VERSION_NAME]["data_version"]
MC = VERSIONS[VERSION_NAME]  # the version of the running conversion; convert() sets it
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
        """Palette entry for block id i: {Name, Properties}."""
        name, _, props = self.states[i].partition("[")
        if not props:
            return Compound({"id": String(name)})
        p = dict(kv.split("=") for kv in props[:-1].split(","))
        return Compound({"id": String(name), "properties": Compound({k: String(v) for k, v in p.items()})})


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
    if "SHALLOW" in n and n.startswith("WATER"):    # "Water, Shallow": only ships go on it, not the shallows (#1198)
        return S("sand", "sand", 2, "sand", "river", [("seagrass", .05)])
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
                 deco=[("dead_bush", .01), ("short_dry_grass", .01)])
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
        return S("grass_block", biome="savanna", deco=[("short_dry_grass", .08), ("tall_dry_grass", .02)])
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
def object_kinds(old=True):
    """Object ID -> (kind prefix, name). Scenarios and recorded games use the same IDs. old: also the IDs that DE
    keeps only in its data file (OLD_IDS), with the name of the DE object: a recorded game builds a town center
    as 621 (#876)."""
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo
    from AoE2ScenarioParser.datasets.heroes import HeroInfo
    from AoE2ScenarioParser.datasets.other import OtherInfo
    from AoE2ScenarioParser.datasets.units import UnitInfo
    kinds = {}
    for prefix, enum in (("H", HeroInfo), ("U", UnitInfo), ("O", OtherInfo), ("B", BuildingInfo)):
        for e in enum:          # later enums win: Building > Other > Unit > Hero
            kinds[e.ID] = (prefix, e.name)
    prefixes = {name: prefix for prefix, name in kinds.values()}
    for i, name in OLD_IDS.items() if old else ():
        kinds.setdefault(i, (prefixes.get(name, "O"), name))
    return kinds


RECORDS = (".aoe2record", ".mgz", ".mgx", ".mgl")      # recorded games: DE, HD; UserPatch, AoC; AoK
RANDOM_MAP = "random-map:"          # the source name of --random-map KIND (#993): read_map makes the map of the seed


def read_map(path, seed=1):
    """read_record for recorded games (RECORDS), read_scx for old .scx scenarios, read_json for a map in JSON,
    read_rms for a random map script (the land of seed), rmap.random_map for RANDOM_MAP + kind, else read_scenario."""
    p = path.lower()
    if p.startswith(RANDOM_MAP):
        import rmap
        return map_description(rmap.random_map(p[len(RANDOM_MAP):], seed), path)
    if p.endswith(".rms"):
        return read_rms(path, seed)
    return (read_record if p.endswith(RECORDS) else read_scx if p.endswith(".scx") else
            read_json if p.endswith(".json") else read_scenario)(path)


def read_rms(path, seed):
    """The land of a random map script (#963): rmap.generate makes a map description of the seed (read_json)."""
    import rmap
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    try:
        return map_description(rmap.generate(text, seed), path)
    except rmap.RmsError as e:
        raise OptionError(f"{path}: {e}") from None


# Object IDs of old scenarios that DE keeps only in its data file (the DE editor hides them, #576) -> the DE object of
# the same look. Buildings of later ages take the base building. Not here: projectiles. The corner of a palisade gate
# (795) is a palisade post, the battering ram (35) has a new ID in DE (#772).
OLD_IDS = {r["id"]: r["name"] for r in units.rows("old_ids.jsonl")}
FLAGX, SHALLOWS_OBJECT = 162, 447   # an invisible editor flag (units.INVISIBLE); shallows: the terrain of its tile


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
    kinds = object_kinds(old=False)                                  # OLD_IDS go to the DE IDs below
    ids = {name: i for i, (_, name) in kinds.items()}
    players = {}
    for pid, p in s["players"].items():
        color = buildings.COLOR_NAMES[p["color"]] if pid and p["color"] is not None and 0 <= p["color"] < 8 else "light_gray"
        players[pid] = {"color": color, "arch": buildings.CIV_TO_ARCH.get(p["civ"], "western"), "civ": p["civ"],
                        "view": p["view"]}
    objects = []
    for o in s["objects"]:
        if o["type"] == SHALLOWS_OBJECT and 0 <= o["x"] < size and 0 <= o["y"] < size:
            terrain[int(o["x"]), int(o["y"])] = TerrainId.SHALLOWS.value
            continue
        t = ids[OLD_IDS[o["type"]]] if o["type"] not in kinds and o["type"] in OLD_IDS else o["type"]
        prefix, name = ("O", "INVISIBLE_OBJECT") if t == FLAGX else kinds.get(t, ("?", f"UNKNOWN_{t}"))
        holder = o["garrisoned_in"]
        objects.append(dict(kind="U" if prefix == "H" else prefix, hero=prefix == "H", name=name, id=t,
                            player=o["player"], x=o["x"], y=o["y"], rotation=float(o["angle"]),
                            garrisoned=holder is not None, ref=o["id"], holder=holder))
    texts = {k: "" for k in CHAPTERS}
    return size, terrain, elevation, {t.value: t.name for t in TerrainId}, texts, objects, players


def read_json(path):
    """A map description in JSON (#960), as read_scenario returns it: {"size": N, "terrain": N × N terrain IDs,
    "elevation": N × N levels (default 0), "objects": [{"name", "player", "x", "y", "rotation"} ...],
    "players": {"1": {"civ": "BRITONS", "color": 0} ...}}. The IDs and names are those of AoE2ScenarioParser
    (TerrainId, object_kinds). The color is an index of buildings.COLOR_NAMES (default: the player number - 1)."""
    with open(path) as f:
        return map_description(json.load(f), path)


def map_description(d, path):
    """read_json of the description d (a dict); path names the source in the errors."""
    from AoE2ScenarioParser.datasets.terrains import TerrainId
    size = d.get("size")
    if not isinstance(size, int) or size < 1:
        raise OptionError(f"{path}: \"size\" must be a positive integer")
    terrain_names = {t.value: t.name for t in TerrainId}
    arrays = {}
    for key, default in (("terrain", None), ("elevation", 0)):
        a = np.array(d.get(key, default if default is None else [[default] * size] * size))
        if a.shape != (size, size):
            raise OptionError(f"{path}: \"{key}\" must be {size} lists of {size} numbers, not shape {a.shape}")
        arrays[key] = a
    if (bad := sorted(set(arrays["terrain"].ravel().tolist()) - set(terrain_names))):
        raise OptionError(f"{path}: unknown terrain IDs {bad[:10]} (see AoE2ScenarioParser TerrainId)")
    kinds = object_kinds(old=False)
    ids = {name: (i, prefix) for i, (prefix, name) in kinds.items()}
    objects = []
    for ref, o in enumerate(d.get("objects", ())):
        if o.get("name") not in ids:
            raise OptionError(f"{path}: object {ref}: unknown name {o.get('name')!r} (see aoe2mc.object_kinds)")
        t, prefix = ids[o["name"]]
        objects.append(dict(kind="U" if prefix == "H" else prefix, hero=prefix == "H", name=o["name"], id=t,
                            player=int(o.get("player", 0)), x=float(o["x"]), y=float(o["y"]),
                            rotation=float(o.get("rotation", 0)), garrisoned=False, ref=ref, holder=None))
    players = {0: {"color": "light_gray", "arch": "western", "civ": "GAIA", "view": None}}
    for pid, p in d.get("players", {}).items():
        pid, civ, color = int(pid), p.get("civ", "?").upper(), p.get("color", int(pid) - 1)
        players[pid] = {"color": buildings.COLOR_NAMES[color] if pid and 0 <= color < 8 else "light_gray",
                        "arch": buildings.CIV_TO_ARCH.get(civ, "western"), "civ": civ, "view": None}
    for pid in {o["player"] for o in objects} - set(players):          # an object of a player without an entry
        players[pid] = {"color": buildings.COLOR_NAMES[(pid - 1) % 8], "arch": "western", "civ": "?", "view": None}
    return (size, arrays["terrain"].astype(np.int16), arrays["elevation"].astype(np.float32), terrain_names,
            {k: "" for k in CHAPTERS}, objects, players)


def read_scenario(path):
    from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
    from AoE2ScenarioParser.datasets.terrains import TerrainId
    from AoE2ScenarioParser.datasets.techs import TechInfo
    from AoE2ScenarioParser.datasets.trigger_lists import ColorMood, VictoryCondition

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
        if p.player_id:                         # the tab "Players" of the editor: for a scenario game (#2539)
            players[p.player_id] |= {"resources": {r: int(getattr(p, r) or 0) for r in ("food", "wood", "gold", "stone")},
                                     "pop_limit": int(p.population_cap or 200), "computer": not p.human}
        neutral = [i for i, d in enumerate(p.diplomacy or [], 1) if d == 1 and i != p.player_id and i <= 8]
        if p.player_id and neutral:             # the stance neutral (1) of DiplomacyState: no automatic attack (#1645)
            players[p.player_id]["neutral"] = neutral
    for n, t in scenario_teams(scn.player_manager.players).items():
        players[n]["team"] = t

    msg = scn.message_manager
    texts = {k: getattr(msg, k, "") or "" for k in CHAPTERS}
    goals = sorted((t.description_order, i, (t.description or t.name or "").strip())   # the objectives that the game lists
                   for i, t in enumerate(scn.trigger_manager.triggers) if t.display_as_objective)
    texts["objectives"] = "\n".join(f"- {g}" for _, _, g in goals if g)
    techs = {t.ID: t.name for t in TechInfo}                    # the names of game/data/train.jsonl
    entities = {u.reference_id for us in scn.unit_manager.units for u in us   # the objects that are entities with the
                if kinds.get(u.unit_const, ("?",))[0] in ("U", "H")}         # tag aoe2mc.r<ref> (#2617), not blocks
    texts["triggers"] = [dict(id=t.trigger_id, name=t.name, enabled=bool(t.enabled), looping=bool(t.looping),
                              conditions=[dict(type=c.condition_type, timer=c.timer, inverted=bool(c.inverted),
                                               **{k: v(c, entities, techs) if callable(v) else getattr(c, v)   # #2832
                                                  for k, v in ((OBJECT_KEYS if c.condition_type in OBJECT_TESTS else {})
                                                               | CONDITION_KEYS.get(c.condition_type, {})).items()})
                                          for c in in_order(t.conditions, t.condition_order)],
                              effects=[dict(type=e.effect_type, message=e.message or "", player=e.source_player,
                                            time=e.display_time, object=kinds.get(e.object_list_unit_id),
                                            tile=[e.location_x, e.location_y],
                                            area=[e.area_x1, e.area_y1, e.area_x2, e.area_y2],
                                            **{k: v(e, kinds, techs) if callable(v) else getattr(e, v)   # #2792
                                               for k, v in EFFECT_KEYS.get(e.effect_type, {}).items()},
                                            **({"mood": ColorMood(e.color_mood).name}     # "Change Color Mood" (#1876)
                                               if e.effect_type == CHANGE_COLOR_MOOD and
                                               getattr(e, "color_mood", None) in set(ColorMood) else {}),
                                            **({"trigger": e.trigger_id}       # "(De)activate Trigger" (#2575)
                                               if e.effect_type in (ACTIVATE_TRIGGER, DEACTIVATE_TRIGGER) else {}),
                                            **({"quantity": e.quantity}
                                               if e.effect_type in (DAMAGE_OBJECT, HEAL_OBJECT, CHANGE_OBJECT_SPEED)
                                               else {}),
                                            **({"cost": [[e.resource_1, e.resource_1_quantity],   # (#2776)
                                                         [e.resource_2, e.resource_2_quantity],
                                                         [e.resource_3, e.resource_3_quantity]]}
                                               if e.effect_type in (CHANGE_OBJECT_COST, CHANGE_TECHNOLOGY_COST) else {}),
                                            **({"technology": techs.get(e.technology, str(e.technology))}   # #2819
                                               if e.effect_type == CHANGE_TECHNOLOGY_COST else {}),
                                            **({"operation": e.operation, "quantity": e.quantity}   # (#2693)
                                               if e.effect_type == CHANGE_OBJECT_HP else {}),
                                            **({"attribute": e.object_attributes, "operation": e.operation,   # #2763
                                                "quantity": e.quantity, "class": e.armour_attack_class,
                                                "aa": e.armour_attack_quantity}
                                               if e.effect_type == MODIFY_ATTRIBUTE else {}),
                                            **({"enabled": e.enabled,                     # (#2775)
                                                "technology": techs.get(e.technology, str(e.technology))}
                                               if e.effect_type in (ENABLE_DISABLE_OBJECT, ENABLE_DISABLE_TECHNOLOGY) else {}),
                                            **({"stance": e.attack_stance}                # (#2705)
                                               if e.effect_type == CHANGE_OBJECT_STANCE else {}),
                                            **({"quantity": e.quantity, "variable": e.variable,   # (#2611)
                                                "operation": e.operation}
                                               if e.effect_type == CHANGE_VARIABLE else {}),
                                            **({"variable": e.variable, "variable2": e.variable2,   # (#2713)
                                                "operation": e.operation}
                                               if e.effect_type == MODIFY_VARIABLE_BY_VARIABLE else {}),
                                            **({"target": e.target_player}                # "Change Ownership" (#2570)
                                               if e.effect_type == CHANGE_OWNERSHIP else {}),
                                            **({"color": e.player_color}                 # (#2712, #2824)
                                               if e.effect_type in (CHANGE_OBJECT_PLAYER_COLOR, CHANGE_PLAYER_COLOR) else {}),
                                            **({"target": e.target_player,                # "Replace Object" (#2703)
                                                "object2": kinds.get(e.object_list_unit_id_2)}
                                               if e.effect_type == REPLACE_OBJECT else {}),
                                            **({"object2": kinds.get(e.object_list_unit_id_2),   # (#2764)
                                                "selected": list(e.selected_object_ids or [])}
                                               if e.effect_type == CREATE_GARRISONED_OBJECT else {}),
                                            **({"selected": list(e.selected_object_ids or [])}   # (#2762)
                                               if e.effect_type in (LOCK_GATE, UNLOCK_GATE) else {}),
                                            **({"selected": list(e.selected_object_ids or [])}   # (#2773)
                                               if e.effect_type == UNLOAD else {}),
                                            **({"target": e.target_player, "diplomacy": e.diplomacy}   # (#2645)
                                               if e.effect_type == CHANGE_DIPLOMACY else {}),
                                            **({"target": e.target_player}                # (#2822)
                                               if e.effect_type == MIRROR_DIPLOMACY else {}),
                                            **({"target": e.target_player, "visibility": e.visibility_state}   # (#2774)
                                               if e.effect_type == SET_PLAYER_VISIBILITY else {}),
                                            **({"target": e.target_player, "visibility": e.visibility_state,   # #2862
                                                "selected": list(e.selected_object_ids or [])}
                                               if e.effect_type == CHANGE_OBJECT_VISIBILITY else {}),
                                            **({"target": e.target_player, "quantity": e.quantity,   # (#2576)
                                                "resource": e.tribute_list} if e.effect_type == TRIBUTE else {}),
                                            **({"operation": e.operation, "quantity": e.quantity,
                                                "resource": e.tribute_list} if e.effect_type == MODIFY_RESOURCE else {}),
                                            **({"operation": e.operation, "quantity": e.quantity}   # (#2767)
                                               if e.effect_type == CHANGE_OBJECT_RANGE else {}),
                                            **({"operation": e.operation, "quantity": e.armour_attack_quantity,   # (#2755)
                                                "armour_class": e.armour_attack_class}
                                               if e.effect_type in (CHANGE_OBJECT_ARMOR, CHANGE_OBJECT_ATTACK) else {}),
                                            **({"operation": e.operation, "variable": e.variable,   # (#2768)
                                                "resource": e.tribute_list}
                                               if e.effect_type == MODIFY_RESOURCE_BY_VARIABLE else {}),
                                            **({"operation": e.operation, "variable": e.variable,   # (#2823)
                                                "resource": e.tribute_list}
                                               if e.effect_type == MODIFY_VARIABLE_BY_RESOURCE else {}),
                                            **({"technology": techs.get(e.technology, str(e.technology))}   # #2577
                                               if e.effect_type in (CHANGE_TECHNOLOGY_NAME, RESEARCH_TECHNOLOGY) else {}),
                                            **({"unit": e.time_unit, "timer": e.timer}   # "Display Timer" (#2572)
                                               if e.effect_type == DISPLAY_TIMER else {}),
                                            **({"timer": e.timer} if e.effect_type == CLEAR_TIMER else {}),   # (#2696)
                                            **({"sound": e.sound_name or ""}             # "Play Sound" (#2644)
                                               if e.effect_type == PLAY_SOUND else {}))
                                       for e in t.effects])
                         for t in scn.trigger_manager.triggers]
    mood = mm.map_color_mood                 # a ColorMood, or a string that the parser does not know (#1594)
    texts["mood"] = (getattr(mood, "name", None) or str(mood or "DEFAULT")).upper()
    om = scn.option_manager                  # the tab "Global Victory" for the scenario mode (#2566, run.VICTORIES)
    win = VictoryCondition(om.victory_condition).name.lower().replace("_", "-") \
        if om.victory_condition in set(VictoryCondition) else "standard"
    texts["global_victory"] = {"condition": win, **({"score": int(om.victory_score)} if win == "score" else {}),
                              **({"years": int(om.victory_years)} if win == "time-limit" else {})}

    objects = []
    for player, player_units in enumerate(scn.unit_manager.units):
        for u in player_units:
            prefix, name = kinds.get(u.unit_const, ("?", f"UNKNOWN_{u.unit_const}"))
            garrisoned = u.garrisoned_in_id not in (None, -1)
            objects.append(dict(kind="U" if prefix == "H" else prefix, hero=prefix == "H", name=name, id=u.unit_const,
                                player=player, x=u.x, y=u.y, rotation=float(u.rotation or 0), garrisoned=garrisoned,
                                ref=u.reference_id, holder=u.garrisoned_in_id if garrisoned else None,
                                ref_tag=True))      # the tag aoe2mc.r<ref> for the triggers (#2617), not in a record
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
    try:
        with open(path, "rb") as f:
            match = parse_match(f)
    except RuntimeError as e:      # the mgz model reads DE 13.34 and later only: read the header of older games
        return read_old_record(path, e)
    size = match.map.dimension
    terrain = np.zeros((size, size), np.int16)
    elevation = np.zeros((size, size), np.float32)
    for t in match.map.tiles:
        terrain[t.position.x, t.position.y] = t.terrain
        elevation[t.position.x, t.position.y] = t.elevation
    terrain_names = {t.value: t.name for t in TerrainId}

    players = {0: {"color": "light_gray", "arch": "western", "civ": "GAIA", "view": None, "team": None}}
    teams = team_numbers([[q.number for q in t] for t in match.teams])        # for the live replay (#1188)
    for p in match.players:
        civ = (p.civilization or "?").upper()
        players[p.number] = {"team": teams.get(p.number), "color": buildings.COLOR_NAMES[p.color_id] if 0 <= p.color_id < 8 else "light_gray",
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


def scenario_teams(players):
    """{player: team number} of the allies of a scenario (#1793): the stance ally (0 of DiplomacyState) is one way,
    so only the players that are allies of each other count. Allies of an ally join its team."""
    ally = {p.player_id: {i for i, d in enumerate(p.diplomacy or [], 1) if d == 0 and i != p.player_id and i <= 8}
            for p in players if p.player_id}
    teams = []
    for a in sorted(ally):
        team, todo = set(), [a]
        while todo:
            b = todo.pop()
            if b not in team:
                team.add(b)
                todo += [c for c in ally.get(b, ()) if b in ally.get(c, ())]
        if len(team) > 1 and team not in teams:
            teams.append(team)
    return team_numbers(teams)


def team_numbers(teams):
    """{player: team number} of the teams of a record (lists of player numbers). The team of the lowest player
    number is team 1: mgz gives the teams in no fixed order (a set in the header parser)."""
    return {p: n for n, t in enumerate(sorted(teams, key=min), 1) for p in t}


def read_old_record(path, error):
    """read_record for the recorded games that the mgz model cannot read (HD, UserPatch, DE before 13.34, #376),
    with the header parser of mgz. That parser skips the sleeping objects of GAIA (the trees) of these versions
    "for performance reasons": read them too. error: the error of the mgz model, for the message."""
    import sys
    from importlib.metadata import version
    from AoE2ScenarioParser.datasets.terrains import TerrainId
    from mgz.summary.full import FullSummary
    skip = trees_switch(sys.modules["mgz.header.initial"].player)
    keyfunc, skip.keyfunc = skip.keyfunc, lambda ctx: True
    try:
        with open(path, "rb") as f:
            s = FullSummary(f)
        s.get_dataset()
    except (RuntimeError, ValueError) as e:
        raise SystemExit(f"{path}: mgz {version('mgz')} cannot read this recorded game ({error}; {e})") from None
    finally:
        skip.keyfunc = keyfunc
    h = s.get_header()
    size = h.map_info.size_x
    tiles = h.map_info.tile                                       # row by row: index y * size + x
    terrain = np.array([t.terrain_type for t in tiles], np.int16).reshape(size, size).T.copy()
    elevation = np.array([t.elevation for t in tiles], np.float32).reshape(size, size).T.copy()
    civs = s.reference.get("civilizations", {})
    players = {0: {"color": "light_gray", "arch": "western", "civ": "GAIA", "view": None, "team": None}}
    teams = team_numbers(s.get_teams())
    for p in s.get_players():
        civ = civs.get(str(p["civilization"]), {}).get("name", "?").upper()
        players[p["number"]] = {"team": teams.get(p["number"]), "color": buildings.COLOR_NAMES[p["color_id"]] if 0 <= p["color_id"] < 8 else
                                "light_gray", "arch": buildings.CIV_TO_ARCH.get(civ, "western"), "civ": civ,
                                "view": p["position"]}
    kinds, objects = object_kinds(), []
    for p in h.initial.players:
        for o in list(p.objects) + (list(p.sleeping_objects) if p.type == 2 else []):     # 2: GAIA
            if o.type not in (10, 20, 30, 70, 80) or o.object_type in ANNEXES or o.player_id not in players:
                continue
            prefix, name = kinds.get(o.object_type, ("?", f"UNKNOWN_{o.object_type}"))
            objects.append(dict(kind="U" if prefix == "H" else prefix, hero=prefix == "H", name=name,
                                player=o.player_id, x=o.x, y=o.y, rotation=0.0, garrisoned=False,
                                ref=o.object_id, holder=None))
    return size, terrain, elevation, {t.value: t.name for t in TerrainId}, {k: "" for k in CHAPTERS}, objects, players


def trees_switch(con):
    """The Switch in the mgz player struct that skips the sleeping objects of GAIA (its True case reads s_size)."""
    from construct import Switch
    if isinstance(con, Switch) and any(getattr(c, "name", None) == "s_size"
                                       for c in getattr(con.cases.get(True), "subcons", [])):
        return con
    for sub in [getattr(con, "subcon", None)] + list(getattr(con, "subcons", [])) + \
            list(getattr(con, "cases", {}).values()):
        if sub is not None and (found := trees_switch(sub)):
            return found


def de_queue(parse_action):
    """mgz 1.8.51 reads DE_QUEUE of new records (an object count, 4 bytes, building type, unit, amount, the object
    IDs) with 4 bytes too many before the IDs, and returns ERROR (469 times in samples/, #372). Read it here."""
    import struct
    from mgz.fast import Action

    def parse(action_type, data):
        try:
            return parse_action(action_type, data)
        except struct.error:
            if action_type != Action.DE_QUEUE or len(data) < 15:
                raise
            player_id, n, _, unit_id, amount = struct.unpack_from("<bxxh4xhhh", data)
            return dict(player_id=player_id, object_ids=list(struct.unpack_from(f"<{n}I", data, 15)),
                        unit_id=unit_id, amount=amount)
    return parse


@contextlib.contextmanager
def own_selection():
    """mgz 1.8.51 (model.inputs.Inputs.add_action) gives a command without own object IDs the last IDs of its action
    type of any player: so player 2 moved the villagers of player 1 (#828). In this block the last IDs of the same
    player and action type fill them."""
    from mgz.model.inputs import Inputs
    add = Inputs.add_action

    def add_action(self, action):
        last = self.__dict__.setdefault("own_ids", {})
        key = (action.player.number if action.player else None, action.type)
        if action.payload.get("object_ids"):
            last[key] = action.payload["object_ids"]
        elif "object_ids" in action.payload and key in last:
            action.payload["object_ids"] = last[key]
        self._oid_cache = {}                                       # mgz copies no IDs of other players
        add(self, action)
    Inputs.add_action = add_action
    try:
        yield
    finally:
        Inputs.add_action = add


TIMELINE_KEYS = {"building_id": "type", "unit_id": "type", "technology_id": "technology_id", "object_ids": "objects",
                 "target_id": "target", "amount": "amount", "resource": "resource", "stance": "stance",
                 "formation": "formation", "order": "order", "command": "command",
                 "player_id_to": "to"}                               # the receiver of a tribute (#1086)


def read_timeline(path):
    """The commands of a recorded game in time order (#372): a list of events {"time": ms, "player": number or
    None, "kind": "build", "wall", "queue", "research", "move", "order", "garrison", "chat" ..., and the data of the
    kind: "type" and "name" (building or unit, as in read_record), "tile" [x, y], "end" [x, y] (wall),
    "technology", "objects" (the object IDs that the command selects), "target" (object ID), "text" (chat)}.
    Tiles are AoE2 tiles. Actions that mgz cannot read are left out. None for the games that the mgz model
    cannot read (read_old_record reads only their start state, #376)."""
    import mgz.fast as fast
    from mgz.model import parse_match
    names, parse = object_kinds(), fast.parse_action
    fast.parse_action = de_queue(parse)
    try:
        with open(path, "rb") as f, own_selection():
            match = parse_match(f)
    except RuntimeError:
        return None
    finally:
        fast.parse_action = parse
    ms = lambda t: int(round(t.total_seconds() * 1000))           # noqa: E731
    events = []
    for a in match.actions:
        kind = a.type.name.lower().removeprefix("de_")
        if kind == "error":
            continue
        e = {"time": ms(a.timestamp), "player": a.player.number if a.player else None, "kind": kind}
        for k, v in a.payload.items():
            if k in TIMELINE_KEYS and v is not None and v != -1:
                e[TIMELINE_KEYS[k]] = v
        if "type" in e:
            e["name"] = names.get(e["type"], ("?", f"UNKNOWN_{e['type']}"))[1]
        if a.payload.get("technology"):
            e["technology"] = a.payload["technology"]
        if a.position:
            e["tile"] = [round(float(a.position.x), 3), round(float(a.position.y), 3)]
        if "x_end" in a.payload:
            e["end"] = [a.payload["x_end"], a.payload["y_end"]]
        if kind == "tribute" and "target_player_id" in a.payload:   # AoE2 DE: the receiver is one byte (#1086)
            to = a.payload["target_player_id"]
            e["to"] = int.from_bytes(to, "little") if isinstance(to, bytes) else int(to)
            e.update((r, int(round(a.payload.get(r) or 0))) for r in ("food", "wood", "gold", "stone"))
        if kind == "flare" and "targets" in a.payload:             # one flag per player slot: the receivers (#2403)
            e["to"] = [i for i, f in enumerate(a.payload["targets"]) if f]
        if kind == "special" and e.get("order") == "Garrison":     # the garrison command of AoE2 DE (#809)
            ids = e.get("objects", [])                              # mgz reads the IDs one byte early
            e["kind"], e["objects"] = "garrison", [i >> 8 for i in ids] if all(i & 255 == 0 for i in ids) else ids
        events.append(e)
    for c in match.chat:
        events.append({"time": ms(c.timestamp), "player": c.player.number if c.player else None, "kind": "chat",
                       "text": c.message})
    for u in match.uptimes:
        events.append({"time": ms(u.timestamp), "player": u.player.number if u.player else None, "kind": "age",
                       "age": u.age.name})
    return sorted(events, key=lambda e: e["time"])


def wall_tiles(x0, y0, x1, y1):
    """The tiles of a wall that a player drags from tile (x0, y0) to (x1, y1): a straight line in tile steps."""
    n = int(max(abs(x1 - x0), abs(y1 - y0)))
    return [(int(round(x0 + (x1 - x0) * i / n)), int(round(y0 + (y1 - y0) * i / n))) for i in range(n + 1)] if n \
        else [(int(x0), int(y0))]


def apply_timeline(objects, timeline, at):
    """The objects of a recorded game at time `at` (ms, --at, #373): the start state with the commands until then.
    BUILD and WALL place buildings (also gates), DELETE removes start objects (the record has no IDs of new
    objects), QUEUE adds the trained units at their building (the record has no positions), or at the first
    building of the player when the building is not in the start state. Returns (objects, stats)."""
    kinds, stats = object_kinds(), Counter()
    refs = {o["ref"]: o for o in objects if o.get("ref") is not None}
    first = {}
    for o in objects:
        if o["kind"] == "B":
            first.setdefault(o["player"], o)
    out, deleted, seen = list(objects), set(), set()
    for e in timeline:
        if e["time"] > at:
            break
        kind, player = e["kind"], e["player"]
        if kind in ("build", "wall") and "type" in e and "tile" in e:
            prefix, name = kinds.get(e["type"], ("?", ""))
            if prefix != "B":
                continue
            tiles = [(x + 0.5, y + 0.5) for x, y in wall_tiles(*e["tile"], *e["end"])] if kind == "wall" \
                else [tuple(e["tile"])]
            for x, y in tiles:
                if (name, x, y) not in seen:            # the same foundation again (a second click)
                    seen.add((name, x, y))
                    out.append(dict(kind="B", hero=False, name=name, player=player, x=x, y=y, rotation=0.0,
                                    garrisoned=False, ref=None, holder=None))
                    stats["buildings (BUILD and WALL commands)"] += 1
        elif kind == "delete":
            deleted.update(i for i in e.get("objects", ()) if i in refs)
        elif kind == "queue" and "type" in e:
            prefix, name = kinds.get(e["type"], ("?", ""))
            at_b = next((refs[i] for i in e.get("objects", ()) if i in refs and refs[i]["kind"] == "B"), None)
            at_b = at_b or first.get(player)
            if prefix not in ("U", "H") or at_b is None or at_b.get("ref") in deleted:
                continue
            for _ in range(max(1, int(e.get("amount", 1)))):
                out.append(dict(kind="U", hero=prefix == "H", name=name, player=player, x=at_b["x"], y=at_b["y"],
                                rotation=0.0, garrisoned=False, ref=None, holder=None))
                stats["units (QUEUE commands, at their building)"] += 1
    stats["start objects removed (DELETE commands)"] = len(deleted)
    return [o for o in out if o.get("ref") is None or o["ref"] not in deleted], stats


# Common units: seconds of training (DE), building. The first name that starts the unit name wins.
TRAIN = {r["name"]: (r["seconds"], r["building"]) for r in units.rows("train.jsonl")}
RESEARCH_S = {"Loom": 25, "Town Watch": 25, "Town Patrol": 40, "Wheelbarrow": 75, "Hand Cart": 55,
              "Feudal Age": 130, "Castle Age": 160, "Imperial Age": 190}   # the town center researches: they delay units
UNIT_USE = {"move", "order", "build", "wall", "patrol", "follow", "formation", "attack_move", "back_to_work", "stance",
            "garrison", "autoscout"}
BUILDING_USE = {"queue", "research", "gather_point", "ungarrison", "sell", "buy"}
WORK = re.compile(r"TREE|.*BUSH|.*_MINE|.*FARM")                     # an ORDER on these: a villager gathers


def train(unit):
    """(seconds, building) of TRAIN for a unit name, or None."""
    return next((v for k, v in TRAIN.items() if unit.startswith(k)), None)


def train_ms(unit):
    """The training time of a unit name in ms: TRAIN, else 30 s."""
    return (train(unit) or (30,))[0] * 1000


def training(timeline, research=False):
    """The trainings of a recorded game: (end time ms, QUEUE event, building ID) for each unit, in the order of the
    QUEUE commands. A building trains one unit after the other; its research (RESEARCH_S) delays them. The record
    does not show a cancelled queue or the population limit. research: also (end, RESEARCH event, building ID) for
    each technology with a RESEARCH_S value (#2810)."""
    busy, out = {}, []                   # building -> free at
    for e in timeline:
        kind, t = e["kind"], e["time"]
        if kind in ("queue", "research") and e.get("objects"):
            name = e.get("name", "") if kind == "queue" else e.get("technology", "")
            s = train_ms(name) if kind == "queue" else RESEARCH_S.get(name, 0) * 1000
            for n in range(max(1, int(e.get("amount", 1))) if kind == "queue" else 1):
                b = e["objects"][n % len(e["objects"])]
                busy[b] = max(busy.get(b, 0), t) + s
                if kind == "queue" or research and s:
                    out.append((busy[b], e, b))
    return out


SHORE = 2                   # tiles: a click this near the water can move a ship (name_timeline, #2629)


def near(mask, r):
    """The tiles at most r tiles (also diagonal) from a True tile of the bool array mask."""
    pad, (w, h) = np.pad(np.asarray(mask, bool), r), np.shape(mask)
    return np.any([pad[r + dx:r + dx + w, r + dy:r + dy + h] for dx in range(-r, r + 1) for dy in range(-r, r + 1)], 0)


def name_timeline(objects, timeline, window=16, water=None):
    """The object IDs of a recorded game (#407). Start objects keep the ID of the record (`ref`, also GAIA animals
    that a player takes). The game gives each new object the next free ID, in the order that it makes them:
    a foundation at its BUILD or WALL command (one per wall tile), a unit when its training ends (the queue of its
    building, TRAIN_S and RESEARCH_S). Objects that the record does not show (for example dead animals) take IDs
    too, so match each predicted object to the first ID in the next `window` IDs that the commands use in the same
    way (a building ID in QUEUE and RESEARCH, of the building that trains its units; a unit ID in MOVE, ORDER and
    BUILD; a building or ship ID as the target of GARRISON) and not before the object exists. A building that is not matched gets the name of its units' building.
    water (a bool array of the water tiles): a ship is not matched to an ID whose first MOVE goes to a land tile more
    than SHORE tiles from the water (#2629): a ship cannot go there, a click on the shore can. Such an ID gets the
    last land unit that its player trained before its first use (a military unit when it does not build or gather).
    Adds "names" (a name or None per ID of "objects") and the "target_name" of a new target ID to the events and
    returns {id: name}."""
    names = {o["ref"]: o["name"] for o in objects if o.get("ref") is not None}
    top = max(names, default=0)
    used = {}             # new ID -> [time of its first use, "B", "U" or None, {building of its units}, a worker,
    #                       its first MOVE goes inland (None: no MOVE yet), the player of its first use]
    far = None if water is None else ~near(water, SHORE)       # the tiles that a ship cannot go to
    for e in timeline:                                   # not SPECIAL and others: their numbers are not all IDs
        role = "U" if e["kind"] in UNIT_USE else "B" if e["kind"] in BUILDING_USE else None
        work = e["kind"] in ("build", "wall") or e["kind"] == "order" and WORK.match(names.get(e.get("target"), ""))
        for i in e.get("objects", ()) if role else ():
            if i > top:
                u = used.setdefault(i, [e["time"], None, set(), False, None, e.get("player")])
                u[1], u[3] = u[1] or role, u[3] or bool(work)
                if e["kind"] == "move" and u[4] is None and far is not None and "tile" in e:
                    x, y = (min(max(int(v), 0), n - 1) for v, n in zip(e["tile"], far.shape))
                    u[4] = bool(far[x, y])
                if e["kind"] == "queue" and train(e.get("name", "")):
                    u[2].add(train(e["name"])[1])
        if role == "U" and e.get("target", 0) > top:
            u = used.setdefault(e["target"], [e["time"], None, set(), False, None, None])
            if e["kind"] == "garrison":                  # its target is a building or a ship (#912)
                u[1] = u[1] or "G"
    made, seen, inland = [], set(), set()   # (time ms, command time, "B" or "U", name); IDs that no ship takes
    for e in timeline:
        kind, t = e["kind"], e["time"]
        if kind in ("build", "wall") and "tile" in e and e.get("name"):
            tiles = wall_tiles(*e["tile"], *e["end"]) if kind == "wall" else [tuple(e["tile"])]
            for tile in tiles:
                if (e["name"], *tile) not in seen:       # the same foundation again (a second click)
                    seen.add((e["name"], *tile))
                    made.append((t, t, "B", e["name"]))
    made += [(end, e["time"], "U", e.get("name", "")) for end, e, _ in training(timeline)]
    firsts = sorted((u[0], i) for i, u in used.items())
    nxt, k, below = top + 1, 0, top
    for t, cmd, role, name in sorted(made):
        while k < len(firsts) and firsts[k][0] < cmd:   # an ID in use before the command is older than the object
            below, k = max(below, firsts[k][1]), k + 1
        nxt = max(nxt, below + 1)
        ids = [i for i in range(nxt, nxt + window) if i in used and i not in names and
               (used[i][1] in (role, None) or used[i][1] == "G" and (role == "B" or "SHIP" in name)) and
               used[i][0] >= t - 5000 and used[i][2] <= {name} and   # 5 s: the training times are estimates
               not (used[i][3] and "VILLAGER" not in name)]         # only villagers build and gather on land (#765)
        if (train(name) or (0, ""))[1] == "DOCK":           # a ship does not go inland (#2629): a land unit
            inland |= {i for i in ids[:1] if used[i][4]}     # takes the ID (below)
            ids = [i for i in ids if not used[i][4]]
        i = ids[0] if ids else nxt if nxt not in used else None
        if i is not None:
            names[i] = name             # a unit skips a GARRISON target: a later building can take it
            nxt = next((j for j in range(nxt, i) if used.get(j, (0, None))[1] == "G" and j not in names), i + 1)
    trained = [(end, e.get("player"), e.get("name", "")) for end, e, _ in training(timeline)
               if (train(e.get("name", "")) or (0, "DOCK"))[1] != "DOCK"]
    for i, u in sorted(used.items()):
        if i not in names and len(u[2]) == 1:
            names[i] = next(iter(u[2]))
        elif i not in names and i in inland:             # the last land unit of its player (#2629), a soldier
            land = [(end, n) for end, p, n in trained if p == u[5] and end <= u[0] + 5000]   # when it does not work
            if pick := [x for x in land if "VILLAGER" not in x[1]] * (not u[3]) or land:
                names[i] = max(pick)[1]
    for e in timeline:
        if e.get("objects"):
            e["names"] = [names.get(i) for i in e["objects"]]
        if names.get(e.get("target")) and e["target"] > top:          # a new building: GARRISON in it (#876)
            e["target_name"] = names[e["target"]]
    return names


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
        deco[field & (r2 < 0.06)] = B("golden_dandelion")               # a few of the new 26.3 flower in each field
        petals = grass & free & (n3 < 0.1) & (r < 0.5)
        deco[petals] = B("pink_petals[facing=north,flower_amount=3]")
        deco2[field | petals] = AIR                                     # no tall grass top above a flower
        faces = ("east", "north", "south", "west")
        def clumps(name, prop, mask):                   # a random facing and amount (1-4) for each clump
            ids = np.array([B(f"{name}[facing={f},{prop}={k}]") for f in faces for k in range(1, 5)], np.uint16)
            deco[mask] = ids[(r2[mask] * len(ids)).astype(int)]
        clumps("wildflowers", "flower_amount", grass & (deco == AIR) & (n3 >= 0.1) & (n3 < 0.16) & (r < 0.4))
        # forest floor: ferns, moss, mushrooms
        floor = forest & free
        deco[floor & (r < 0.18)] = B("fern")
        big = floor & (r >= 0.18) & (r < 0.22)
        deco[big], deco2[big] = B("large_fern[half=lower]"), B("large_fern[half=upper]")
        deco[floor & (r >= 0.22) & (r < 0.24)] = B("brown_mushroom")
        deco[floor & (r >= 0.24) & (r < 0.25)] = B("red_mushroom")
        deco[floor & (r >= 0.25) & (r < 0.45) & (n2 > 0.6)] = B("moss_carpet")
        deco[floor & (r >= 0.45) & (r < 0.6)] = B("short_grass")
        clumps("leaf_litter", "segment_amount", floor & (r >= 0.6) & (r < 0.6 + 0.35 * n1))   # fallen leaves
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

        # dry ground (steppe): patches of grass with dry grass (the dry grass blocks of 26.3, #523), dead bushes
        steppe_grass = dirt & (top == B("coarse_dirt")) & (n1 < 0.3)
        top[steppe_grass] = B("grass_block")
        top[dirt & ~steppe_grass & (n3 > 0.75)] = B("dirt")
        deco[steppe_grass & free & (r < 0.12)] = B("short_grass")
        deco[steppe_grass & free & (r >= 0.12) & (r < 0.30)] = B("short_dry_grass")
        deco[steppe_grass & free & (r >= 0.30) & (r < 0.34)] = B("tall_dry_grass")
        bare = dirt & ~steppe_grass & free
        deco[bare & (r < 0.02)] = B("dead_bush")
        deco[bare & (r >= 0.02) & (r < 0.10)] = B("short_dry_grass")
        deco[bare & (r >= 0.10) & (r < 0.12)] = B("tall_dry_grass")
        deco[sand & free & (r < 0.012)] = B("dead_bush")
        deco[sand & free & (r >= 0.012) & (r < 0.02)] = B("short_dry_grass")

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
              "cauldron", "flower", "short_grass", "tall_grass", "dry_grass", "fern", "bush", "sapling", "leaves", "air", "water",
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
    if name.endswith(("_pane", "copper_bars")) or name == "minecraft:iron_bars":
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
        hard = np.broadcast_to(np.asarray(hard, bool), xs.shape)        # one flag, or one for each block
        if self.natural and self.blocked is not None and len(xs):
            n = self.blocked.shape[0]
            inside = (xs >= 0) & (zs >= 0) & (xs < n) & (zs < n)
            keep = ~inside.copy()
            keep[inside] = ~self.blocked[xs[inside], zs[inside]]
            xs, ys, zs, ids, hard = xs[keep], ys[keep], zs[keep], ids[keep], hard[keep]
        if self.footprint is not None and self.cols is not None and len(xs):
            x0, x1, z0, z1 = self.footprint
            outside = (xs < x0) | (xs >= x1) | (zs < z0) | (zs >= z1)
            if outside.any():
                n = self.cols.n
                cx, cz = np.clip(xs, 0, n - 1), np.clip(zs, 0, n - 1)
                ground = self.cols.wtop[cx, cz].astype(np.int32)
                keep = ~outside | (ys >= ground + self.HEAD)
                xs, ys, zs, ids, hard = xs[keep], ys[keep], zs[keep], ids[keep], hard[keep]
        self.parts.append((xs, ys, zs, ids, hard.copy()))

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
    if "AUTUMN" in n: return "poplar"                    # 26.3 poplar: yellow, orange and red leaves
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


WOODS = {"palm": "jungle", "jungle": "jungle", "acacia": "acacia", "spruce": "spruce", "birch": "birch",
         "mangrove": "mangrove", "poplar": "poplar"}                         # tree kind -> wood (log and leaves); else oak


TREE_SHAPES = {}        # (kind, h, leaf) -> (dx, dy, dz, ids, hard): the blocks of a tree at (0, 0, 0)


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
        fungus(E, x, y, z, h - 1, ("north", "south"))   # the branches are on the east and west sides
        return
    wood = WOODS.get(kind, "oak")
    log, leaf = f"{wood}_log", leaves(wood)
    if kind == "poplar":                                 # one autumn color per tree
        leaf = leaves(f"{('yellow', 'orange', 'red')[int(rng.integers(3))]}_poplar")
    shape = TREE_SHAPES.get((kind, h, leaf))
    if shape is None:                                    # one add for each tree: a large map has 30 000 (#702)
        S = Edits()
        tree_shape(S, kind, h, log, leaf)
        shape = TREE_SHAPES[kind, h, leaf] = tuple(np.concatenate(p) for p in zip(*S.parts))
    dx, dy, dz, ids, hard = shape
    E.add(x + dx, y + dy, z + dz, ids, hard)
    if kind == "oak":
        fungus(E, x, y, z, h - 2, ("north", "south", "west", "east"))


def tree_shape(E, kind, h, log, leaf):
    """Draw the blocks of a tree without random numbers at (0, 0, 0)."""
    x = y = z = 0
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
    else:  # round trees: oak, birch, jungle, mangrove, poplar
        if kind == "jungle":
            h += 3
        for dy, r in ((h - 2, 2), (h - 1, 2), (h, 1), (h + 1, 1)):
            disc(E, x, y + dy, z, r, leaf)
        E.box(x, x + 1, y, y + h, z, z + 1, log)


FACE = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}


def fungus(E, x, y, z, top, faces):
    """Bracket fungus (shelf_mushroom) on 1 old tree in 10: 1 or 2 on the trunk, 1 to 3 blocks up, below `top`.

    Its own generator, seeded by the position: the trees after it keep their random numbers."""
    r = np.random.default_rng([x % 65536, y % 65536, z % 65536, 558])
    if r.random() >= 0.1:
        return
    for f in r.permutation(faces)[:int(r.integers(1, 3))]:
        dx, dz = FACE[f]
        E.add([x + dx], [y + int(r.integers(1, max(2, min(4, top))))], [z + dz],
              f"shelf_mushroom[age={int(r.integers(2))},facing={f}]")


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
    kind = OBJECT.get(n, {}).get("decor")
    if n.startswith(STATUES):
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
    elif "MARKET_STALL" in n or "GOODS" in n or kind == "stall":
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
            put(-1, 0, 1, "barrel[facing=up]"); put(1, 0, -1, "iron_chain")
    elif "BARREL" in n:
        for dx, dz in ((0, 0), (1, 0), (0, 1)):
            put(dx, 0, dz, "barrel[facing=up]")
        put(0, 1, 0, "barrel[facing=up]")
    elif "WEAPON" in n:
        put(0, 0, 0, "grindstone[face=floor,facing=north]"); put(1, 0, 0, "anvil[facing=east]")
        put(-1, 0, 0, "oak_fence"); put(-1, 1, 0, "lightning_rod")
    elif "TARGET" in n:
        put(0, 0, 0, "hay_block"); put(0, 1, 0, "target")
    elif n == "RUNESTONES":                            # one tall carved stone and two small ones
        put(0, 0, 0, "tuff"); put(0, 1, 0, "chiseled_tuff"); put(0, 2, 0, "tuff_wall")
        put(-1, 0, 1, "polished_andesite"); put(-1, 1, 1, "andesite_wall")
        put(1, 0, -1, "mossy_cobblestone"); put(1, 1, 0, "red_carpet"); put(1, 0, 0, "chiseled_tuff_bricks")
    elif n == "NORSE_COLUMN":                          # a carved wooden pole on a stone base
        put(0, 0, 0, "stone_bricks")
        for dy in range(1, 5):
            put(0, dy, 0, "spruce_log[axis=y]" if dy % 2 == 0 else "stripped_spruce_log[axis=y]")
        put(0, 5, 0, "lantern[hanging=false]")
    elif n == "NORSE_BANNER":
        put(0, 0, 0, "spruce_fence"); put(0, 1, 0, "spruce_fence"); put(0, 2, 0, "red_banner[rotation=8]")
    elif n == "WOODEN_ROAD":                           # flat: planks in the ground, units walk on it
        for x in range(x0, x1):
            for z in range(z0, z1):
                yy = cols.surface(x, z)
                if yy - 1 == cols.top[min(max(x, 0), cols.n - 1), min(max(z, 0), cols.n - 1)]:
                    E.add([x], [yy - 1], [z], "spruce_planks" if rng.random() < 0.8 else "stripped_spruce_wood[axis=x]")
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
        put(0, -1, 0, "stripped_bamboo_block[axis=y]" if "BAMBOO" in n else "spruce_log[axis=y]")   # level: walk over it
        put(0, 0, 0, "air")                                     # no grass or flower on the log
    elif n.startswith(("PATH_", "BLACK_TILE")):        # flat: a path in the ground, black carpet on it
        for x in range(x0, x1):
            for z in range(z0, z1):
                yy = cols.surface(x, z)
                if n == "BLACK_TILE":
                    E.add([x], [yy], [z], "black_carpet", hard=False)
                elif rng.random() < 0.8 and yy - 1 == cols.top[min(max(x, 0), cols.n - 1), min(max(z, 0), cols.n - 1)]:
                    E.add([x], [yy - 1], [z], "dirt_path")
    elif kind == "head":
        h = 2 if n.startswith("IMPALED_CORPSE") else 0
        for dy in range(h):
            put(0, dy, 0, "spruce_fence")
        put(0, h, 0, "skeleton_skull[rotation=8]")
        if h:
            put(1, 0, 0, "bone_block[axis=x]")
    elif kind == "loot":
        put(0, 0, 0, "chest[facing=south]" if n == "TREASURE_CHEST" else "barrel[facing=up]")
        put(1, 0, 0, "gold_block" if n == "TREASURE_CHEST" else "raw_gold_block")
    elif n == "LEATHERWORKING_EQUIPMENT":
        put(0, 0, 0, "loom[facing=south]"); put(1, 0, 0, "spruce_fence"); put(1, 1, 0, "brown_carpet")
    elif kind == "fence":
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
    elif n.startswith("FOUNTAIN"):                     # a basin: the rim around the source keeps the water in
        rim = "smooth_quartz" if "ANTIQUITY" in n else "stone_bricks"
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                if dx or dz:
                    put(dx, 0, dz, rim)
        put(0, 0, 0, "water[level=0]" if min(x1 - x0, z1 - z0) >= 3 else rim)     # small tiles: no rim, no water
        for dx, dz in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            put(dx, 1, dz, "quartz_pillar" if "ANTIQUITY" in n else "stone_brick_wall")
    elif kind == "pots":
        pot = "decorated_pot[facing=south,cracked=false]"
        for dx, dz in ((0, 0), (1, 0), (0, 1)):
            put(dx, 0, dz, pot)
        put(0, 1, 0, pot if n == "AMPHORAE" else "water_cauldron[level=3]")
    elif n == "GRAIN_STORAGE":
        put(0, 0, 0, "barrel[facing=up]"); put(1, 0, 0, "hay_block"); put(0, 0, 1, "hay_block")
        put(0, 1, 0, "composter[level=8]")
    elif n == "FURNACE":
        put(0, 0, 0, "blast_furnace[facing=south,lit=true]"); put(0, 1, 0, "brick_wall")
        put(1, 0, 0, "coal_block")
    elif n == "WATER_TROUGH":
        for dx in (-1, 0, 1):
            put(dx, 0, 0, "water_cauldron[level=3]")
    elif n.startswith("BENCH_"):
        wood = n == "BENCH_WOODEN"
        for dx in (-1, 0, 1):
            put(dx, 0, 0, f"{'spruce' if wood else 'stone_brick'}_stairs[facing=north,half=bottom,shape=straight]")
    elif "GALLOW" in n:
        put(-1, 0, 0, "dark_oak_fence"); put(-1, 1, 0, "dark_oak_fence"); put(-1, 2, 0, "dark_oak_fence")
        E.box(cx - 1, cx + 2, y + 3, y + 4, cz, cz + 1, "dark_oak_log[axis=x]"); put(1, 2, 0, "iron_chain")
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
    X, Z = np.meshgrid(np.arange(max(0, x0), min(cols.n, x1)), np.arange(max(0, z0), min(cols.n, z1)), indexing="ij")
    Y = cols.wtop[X, Z].astype(np.int32)[..., None] + 1 + np.arange(height)      # one add: columns in x, z order
    E.add(np.repeat(X, height), Y, np.repeat(Z, height), "barrier", hard=False)


def player_color(p, players=None):
    if players and p in players:
        return players[p]["color"]
    return PLAYER_COLORS[p] if 0 <= p < len(PLAYER_COLORS) else "white"


# --------------------------------------------------------------------------------------------
# Place all objects of the scenario.
# --------------------------------------------------------------------------------------------
MOUNTAINS = ("MOUNTAIN", "SNOW_MOUNTAIN")
# The other objects of AoE2 (#2036). "mob": a part of the name, the first line wins; "monument" (a buildings.py
# design), "obstacle": the start of the name; "passable": a part of the name; "decor": the design in decor() (a
# start of the name for "statue", else the full name); "map_color", "scatter", "no_blocks": the full name.
OBJECTS = units.rows("objects.jsonl")
OBJECT = {r["name"]: r for r in OBJECTS}
MONUMENTS = tuple(r["name"] for r in OBJECTS if r.get("monument"))
PASSABLE_OBJECTS = tuple(r["name"] for r in OBJECTS if r.get("passable"))
OBSTACLES = tuple(r["name"] for r in OBJECTS if r.get("obstacle"))
STATUES = tuple(r["name"] for r in OBJECTS if r.get("decor") == "statue")


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


DRY_GROUND = ("sand", "red_sand", "coarse_dirt", "dirt", "terracotta")


def bush_block(cols, x, z, name):
    """The bush block of 26.3 for an AoE2 bush or shrub: a firefly bush next to water, a red shrub on dry ground
    (or for a "DRY" or "RED" name), else a green bush (#524)."""
    x0, z0 = max(x - 2, 0), max(z - 2, 0)
    if (cols.wtop[x0:x + 3, z0:z + 3] > cols.top[x0:x + 3, z0:z + 3]).any():
        return "firefly_bush"
    ground = B.states[cols.top_id[min(x, cols.n - 1), min(z, cols.n - 1)]].split(":")[-1].split("[")[0]
    return "red_shrub" if "DRY" in name or "RED" in name or ground in DRY_GROUND else "bush"


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
            if (bx * 7 + bz * 13) % 3 == 0:     # one in three blooms; from the position, so the rng stream stays the same
                E.box(bx, bx + 1, y + 2, y + 3, bz, bz + 1, "cactus_flower")
            stats["plants"] += 1
        elif kind == "O" and name.startswith("PLANT"):
            plant = "fern" if ("FERN" in name or "JUNGLE" in name or "UNDERBRUSH" in name) else \
                bush_block(cols, bx, bz, name) if ("SHRUB" in name or "BUSH" in name) else \
                ["poppy", "dandelion", "cornflower", "allium"][int(rng.integers(4))] if "FLOWER" in name else \
                "dead_bush" if "DEAD" in name else "short_grass"
            E.add([bx], [y], [bz], plant, hard=False)
            stats["plants"] += 1
        elif kind == "O" and (name.startswith("RUBBLE") or "SKELETON" in name or OBJECT.get(name, {}).get("scatter")
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
        elif kind == "O" and (OBJECT.get(name, {}).get("no_blocks") or name.startswith("WATERFALL")):
            pass
        elif kind == "O" and "ROCK" in name:
            mound(E, cols, bx, bz, T * 0.4, 2, ["mossy_cobblestone", "cobblestone", "stone"], rng)
            stats["rocks"] += 1
        elif kind == "O" and ("FORAGE" in name or "FRUIT_BUSH" in name):
            x0, z0 = bx // T * T, bz // T * T          # a full bush fills its tile, 2 blocks high (#590): berries
            for x in range(x0, x0 + T):                 # around, leaves in the middle (a berry bush needs dirt below)
                for z in range(z0, z0 + T):
                    if cols.inside(x, z):
                        ring = x in (x0, x0 + T - 1) or z in (z0, z0 + T - 1)
                        mid = not ring or T <= 2 and (x, z) == (x0, z0)
                        y = cols.surface(x, z)
                        E.add([x] * (1 + mid), [y, y + 1][:1 + mid], [z] * (1 + mid),
                              "oak_leaves[persistent=true]" if mid else "sweet_berry_bush[age=3]")
            stats["berry bushes"] += 1
        elif kind == "O" and "RELIC" in name:
            E.add([bx], [y], [bz], "decorated_pot[facing=south,cracked=false]")
            stats["relics"] += 1
        elif kind == "O" and "FLAG" in name:
            E.box(bx, bx + 1, y, y + 3, bz, bz + 1, "oak_fence")
            E.add([bx], [y + 3], [bz], f"{player_color(o['player'], players)}_wool")
            stats["flags"] += 1
        elif kind == "O" and name.startswith("BUSH"):                 # a bush with leaves around it
            E.add([bx, bx + 1, bx + 1], [y, y, y + 1], [bz, bz, bz],
                  [B(bush_block(cols, bx, bz, name)), B("oak_leaves[persistent=true]"), B("oak_leaves[persistent=true]")],
                  hard=False)
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
        if kind == "O" and (("TREE" in name and "STUMP" not in name) or "FORAGE" in name or "FRUIT_BUSH" in name
                            or name.startswith(("CLIFF", *MOUNTAINS, "ROCK", *OBSTACLES))):
            obstacle(E, cols, E.footprint)
        elif kind == "O" and E.footprint and not any(k in name for k in PASSABLE_OBJECTS):
            x0, x1, z0, z1 = E.footprint            # other objects with blocks: no units on top of them
            cols.blocked[max(0, x0):max(0, x1), max(0, z0):max(0, z1)] = True
    E.footprint = None
    E.natural = True
    cliff_ridges(E, cols, cliffs, rng)
    E.natural = False
    free_carpets(E, cols)
    return E, stats


# --------------------------------------------------------------------------------------------
# Units -> entities
# --------------------------------------------------------------------------------------------
FISH = [(r["name"], r["mob"]) for r in OBJECTS if "mob" in r]
OBJECT_MOBS = {"WHALE": "dolphin"}    # exact names: BEACHED_WHALE is a carcass, not a mob. No whale mob: the dolphin
LAND_MOBS = ("turtle", "ocelot")      # is the nearest large sea animal


def object_mob(name):
    """Minecraft mob for an AoE2 'other object' that is an animal (fish, dolphin, whale, turtles, monkey), else None."""
    return OBJECT_MOBS.get(name) or next((k for key, k in FISH if key in name), None)
PASSABLE = ("short_grass", "tall_grass", "large_fern", "petals", "moss_carpet", "mushroom", "allium", "bluet",
            "tulip", "lily_of", "fern", "wheat", "poppy", "dandelion", "cornflower", "daisy", "water",
            "seagrass", "dead_bush", "sweet_berry", "rail", "carpet", "banner", "button", "lantern", "snow[", "kelp",
            "lily_pad", "bush[", "shrub", "dry_grass")


def passable_states(states):
    """True for each state that a unit can stand in (air, plants, carpets ...), with spare room for new ids."""
    return np.array([st.split(":")[1].split("[")[0] in ("air", "cave_air") or       # the name only: a fence has
                     any(k in st.split(":")[1].split("[")[0] + "[" for k in PASSABLE)  # "waterlogged=false" (#465)
                     and "grass_block" not in st for st in states] + [True] * 1024)


GROUND_MASKS = {}


def ground_masks():
    """(carpet, passable): bool arrays over the block ids of B (cached for the present number of states)."""
    n = len(B.states)
    if n not in GROUND_MASKS:
        GROUND_MASKS.clear()
        carpet = [st.split(":")[1].split("[")[0].endswith("carpet") for st in B.states] + [False] * 1024
        GROUND_MASKS[n] = np.array(carpet), passable_states(B.states)
    return GROUND_MASKS[n]


def free_carpets(E, cols):
    """Take away each ground carpet with a solid block 3 over its ground in its column or a next one (#2390).
    The step onto the carpet (1/16 block) lifts the head of a unit (1.95 blocks) into that block: the path search
    takes the step, and the unit cannot move."""
    if not E.parts:
        return
    n = cols.n
    carpet, passable = ground_masks()
    x, y, z, ids = (np.concatenate(p) for p in list(zip(*E.parts))[:4])
    ok = (x >= 0) & (z >= 0) & (x < n) & (z < n) & ~passable[ids]
    x, y, z = x[ok], y[ok], z[ok]
    wtop = cols.wtop[:n, :n].astype(np.int32)
    over = y > wtop[x, z]
    low = np.full((n, n), 1 << 20, np.int32)                    # the lowest solid object block over the ground
    np.minimum.at(low, (x[over], z[over]), y[over])
    pad = np.pad(low, 1, constant_values=1 << 20)
    bad = np.zeros((n, n), bool)
    for dx in (-1, 0, 1):
        for dz in (-1, 0, 1):
            bad |= pad[1 + dx:1 + dx + n, 1 + dz:1 + dz + n] == wtop + 3
    deco = cols.deco[:n, :n]
    deco[bad & carpet[deco]] = AIR
    for i, (px, py, pz, pids, hard) in enumerate(E.parts):
        inside = (px >= 0) & (pz >= 0) & (px < n) & (pz < n)
        drop = np.zeros(len(px), bool)
        cx, cz = px[inside], pz[inside]
        drop[inside] = carpet[pids[inside]] & bad[cx, cz] & (py[inside] == wtop[cx, cz] + 1)
        if drop.any():
            E.parts[i] = (px[~drop], py[~drop], pz[~drop], pids[~drop], hard[~drop])


def seat_count(ship):
    return 1 if "_chest_" in str(ship["id"]) else 2      # a chest boat has one seat
CHAIN = 4                   # units per boat seat: each garrisoned unit rides the unit below it (#382)
NAME_HIDDEN = "aoe2mc.name_hidden"  # entity tag of a unit whose name tag a trigger hid with the unit (#2862)
GARRISONED = "aoe2mc.garrisoned"    # entity tag of a unit inside its building (#807; the game program: #808)
NO_TARGET = "aoe2mc.notarget"       # entity tag: no unit or tower chooses it as a target (AoePlugin calm, #2826)
UNSELECTABLE = "aoe2mc.unselectable"   # entity tag: no click of a person selects it (game/scenario.py, #2854)
MADE_INSIDE = "aoe2mc.made_inside"  # entity tag of a unit that a trigger made inside a building: the game program adds
                                    # it to the garrison of the building (#2764)
GARRISON_CELLS = 20         # free cells of a building in aoe2mc.json: the largest AoE2 garrison (castle, #808)
SUN = ("minecraft:zombie", "minecraft:zombie_villager", "minecraft:skeleton", "minecraft:stray", "minecraft:drowned")


def depth(nbt):
    """Number of rider levels above an entity."""
    return max((1 + depth(p) for p in nbt.get("Passengers", [])), default=0)


def sun_helmet(nbt):
    """A mob of a ship stack that burns in the sun gets a helmet if it has none."""
    for p in nbt.get("Passengers", []):
        sun_helmet(p)
    if str(nbt["id"]) in SUN:
        eq = nbt.setdefault("equipment", Compound({}))
        if "head" not in eq:
            eq["head"] = units.item("leather_helmet", unbreakable=True)


def plan_units(objects, players, cols, rng, stats, birds=True, garrison="inside", silent=False):
    """Entities per chunk: {(cx, cz): [(nbt, x, z, is_boat)]}. silent: also the passive animals (--ambience off).
    A garrisoned unit rides its ship if a seat is free. Else garrison="inside": it stands in the rooms of its building
    (is_boat = ("inside", y)), invulnerable and without a visible name (#807); "outside": it stands next to its holder."""
    T = cols.T
    out = {}
    refs = {o["ref"]: o for o in objects if o.get("ref") is not None}
    boats = {}                  # reference ID of a ship -> its boat NBT
    stacks = {}                 # reference ID of a ship -> units per seat
    full = Counter()            # reference ID of a ship -> garrisoned units without room (on its name tag)
    labels = {}                 # reference ID of a ship -> the entity with its name tag
    taken = set()               # columns that garrisoned units use, so that they do not stand in one column
    garrisons = Counter()       # reference ID of a building -> units inside it
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
                    ship, ref = boats[o["holder"]], o["holder"]
                    seats, n = ship.setdefault("Passengers", List[Compound]([])), stacks[ref]
                    sun_helmet(nbt)
                    if len(seats) < seat_count(ship):
                        seats.append(nbt)
                        n.append(1)
                    elif n and min(n) < CHAIN:          # a full seat: ride the top of its stack
                        i = n.index(min(n))
                        units.top_entity(seats[i])["Passengers"] = List[Compound]([nbt])
                        n[i] += 1
                    else:
                        full[ref] += 1
                        stats["units (garrisoned, ship full, counted on its name tag)"] += 1
                        continue
                    src["uuid"] = units.uuid_str(nbt["UUID"])
                    stats["units (garrisoned, in a ship)"] += 1
                    continue
                if garrison == "inside" and o.get("holder") in buildings.INSIDE:
                    cells, y, center = buildings.INSIDE[o["holder"]]
                    bx, bz = cells[garrisons[o["holder"]] % len(cells)] if cells else center   # more units share cells
                    garrisons[o["holder"]] += 1
                    label = units.top_entity(nbt)
                    label["CustomNameVisible"] = Byte(0)            # a name tag shows through the walls
                    label["Tags"] = List[String](list(label.get("Tags", [])) + [String(GARRISONED)])
                    e = nbt
                    while e is not None:                            # no damage in the barrier blocks of the rooms
                        e["Invulnerable"], e["NoAI"] = Byte(1), Byte(1)
                        e = e["Passengers"][0] if e.get("Passengers") else None
                    src["uuid"] = units.uuid_str(nbt["UUID"])
                    out.setdefault((bx >> 4, bz >> 4), []).append((nbt, bx + 0.5, bz + 0.5, ("inside", y)))
                    stats["units (garrisoned, inside the holder)"] += 1
                    stats["units"] += 1
                    continue
                o = dict(o, x=holder["x"], y=holder["y"]) if holder else o
                stats["units (garrisoned, next to the holder)"] += 1
            elif boat and o.get("ref") is not None:
                boats[o["ref"]], labels[o["ref"]] = nbt, units.top_entity(nbt)
                stacks[o["ref"]] = [1] * len(nbt.get("Passengers", []))      # the crew
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
            feet = holder.get("footprint") if held and holder else None     # next to it, not under it (#865)
            near = {(x, z) for x in range(feet[0], feet[2]) for z in range(feet[1], feet[3])} if feet else set()
            spot = free_spot(cols, bx, bz, 6 * T, water=bool(boat), taken=taken | near if held else ())
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
    for ref, k in full.items():                 # the units without room: "Transport Ship (+6)"
        labels[ref]["CustomName"]["text"] = String(f"{labels[ref]['CustomName']['text']} (+{k})")
    return out


def top_name(nbt):
    t = units.top_entity(nbt)
    return t["CustomName"]["text"] if "CustomName" in t else t["id"]


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


CHAPTERS = {"instructions": "Instructions", "objectives": "Objectives", "hints": "Hints", "victory": "Victory",
            "loss": "Loss", "history": "History", "scouts": "Scouts"}          # objectives: from the triggers
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
    """A text component of (text, bold) parts (NBT since 1.21.5)."""
    extra = [dict(text=t, bold=True) if b else dict(text=t) for t, b in parts]
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


def map_item():
    """The item of the locked map of the world (map id 0, #838): in the frame at the spawn (#839) and in the
    off-hand of a new player (#966)."""
    return Compound({"id": String("minecraft:filled_map"), "count": Int(1),
                     "components": Compound({"minecraft:map_id": Int(0)})})


def place_map(cols, edits, spawn, book):
    """A glow item frame with the map of write_map (map id 0, #839) on the ground next to the lectern `book`, or in
    its place (2 blocks in front of the spawn view) when there is no book: it shows also at night. Fixed 1b: no
    player takes it, and it needs no support block.
    Returns the entity (nbt, x, z, (None, y)) for entity_chunk, or None when no free land is near."""
    sx, _, sz = spawn
    if book:
        x, _, z = book
        spot = next(((x + dx, z + dz) for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))
                     if 0 <= x + dx < cols.n and 0 <= z + dz < cols.n and not cols.blocked[x + dx, z + dz]
                     and cols.wtop[x + dx, z + dz] <= cols.top[x + dx, z + dz]), None)
    else:
        dx, dz = turn_tile(2, -2, 0, buildings.TURN)
        spot = free_spot(cols, min(max(sx + dx, 0), cols.n - 1), min(max(sz + dz, 0), cols.n - 1), 4)
    if spot is None or spot == (sx, sz) or cols.wtop[spot] > cols.top[spot]:
        return None
    fx, fz = spot
    fy = cols.surface(fx, fz)
    edits.footprint = None
    edits.add([fx], [fy], [fz], "air")                 # grass and flowers hide the map
    cols.blocked[fx, fz] = True                        # no unit stands in the frame
    nbt = units.to_nbt({"id": String("minecraft:glow_item_frame"), "Facing": Byte(1), "Item": map_item(), "Fixed": Byte(1),
                        "block_pos": IntArray([fx, fy, fz]), "ItemRotation": Byte(0), "ItemDropChance": Float(0)},
                       (fx + 0.5, fy, fz + 0.5), 0, np.random.default_rng(839))
    nbt["Invulnerable"] = Byte(1)
    return nbt, fx + 0.5, fz + 0.5, (None, fy + 1 / 32)


def shelf_data(items):
    """Block entity fields of a shelf (26.3) with one item in each of its 3 slots (#526)."""
    return {"Items": List[Compound]([Compound({"Slot": Byte(i), "id": String("minecraft:" + n), "count": Int(1)})
                                     for i, n in enumerate(items)])}


def set_pos(nbt, x, y, z):
    nbt["Pos"] = List[Double]([Double(x), Double(y), Double(z)])
    for p in nbt.get("Passengers", []):
        set_pos(p, x, y, z)


MOVED = Counter()


def moved(key, nbt, x, y, z, col):
    """Count a unit that stands above the ground (key: its name, or "(on a bridge)"); AOE2MC_DEBUG=1 names it,
    with the two blocks above the ground (#773)."""
    MOVED[key] += 1
    if os.environ.get("AOE2MC_DEBUG"):
        print("   on a bridge:" if key == "(on a bridge)" else "   in block:", str(top_name(nbt)), x, y, z,
              B.states[col[y - MIN_Y]], B.states[col[y + 1 - MIN_Y]])
TICKS = []                  # (time, phase) of each phase end of the last convert(): tools/measure_convert.py (#690)


def entity_chunk(cx, cz, ents, cols, vol, passable):
    """Place the entities of one chunk on the first free space and return the chunk NBT bytes."""
    out = []
    for nbt, x, z, boat in ents:
        bx, bz = int(x), int(z)
        top, wtop = int(cols.top[bx, bz]), int(cols.wtop[bx, bz])
        if isinstance(boat, tuple):                 # a garrisoned unit in the rooms of its building (#807)
            y = boat[1]
        elif boat == "fish":
            if wtop - top < 2:
                continue
            y = (top + wtop) / 2 + 0.3
        elif boat and wtop > top:
            col = vol[:, bz & 15, bx & 15]
            h = 1 + 2 * depth(nbt) if nbt.get("Passengers") else 2   # the boat and its crew (or stacks) need free space
            ice = bool(cols.ice[bx, bz])          # frozen water: the boat stands on the ice block at wtop (#1024)
            y = base = wtop + ice
            while y < MAX_Y - 3 and not all(passable[col[y + k - MIN_Y]] for k in range(h)):
                y += 1
            if y > base:
                moved(str(top_name(nbt)), nbt, bx, base, bz, col)
            y += 0 if ice and y == base else 0.5
        else:
            col = vol[:, bz & 15, bx & 15]
            y = top + 1
            if wtop > top:                   # water: stand on a bridge or dock deck if there is one
                for yy in range(wtop + 1, min(wtop + 40, MAX_Y - 2)):
                    if not passable[col[yy - 1 - MIN_Y]] and passable[col[yy - MIN_Y]] and passable[col[yy + 1 - MIN_Y]]:
                        y = yy
                        moved("(on a bridge)", nbt, bx, yy, bz, col)
                        break
            while y < MAX_Y - 2 and not (passable[col[y - MIN_Y]] and passable[col[y + 1 - MIN_Y]]):
                y += 1
            if y == buildings.FLOORS.get((bx, bz)):         # on the raised floor of a gate passage (#773)
                top = y - 1
            if y > top + 1 and not wtop > top and (bx, bz) not in buildings.BRIDGE_CELLS:
                for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):   # a shrub or leaves in the block: stand next to it (#415)
                    nx, nz = bx + dx, bz + dz
                    if nx >> 4 != cx or nz >> 4 != cz or cols.wtop[nx, nz] > cols.top[nx, nz]:
                        continue
                    nt, ncol = int(cols.top[nx, nz]), vol[:, nz & 15, nx & 15]
                    if passable[ncol[nt + 1 - MIN_Y]] and passable[ncol[nt + 2 - MIN_Y]]:
                        x, z, bx, bz, top, col, y = x + dx, z + dz, nx, nz, nt, ncol, nt + 1
                        break
            if y > top + 1 and not wtop > top:
                moved("(on a bridge)" if (bx, bz) in buildings.BRIDGE_CELLS else str(top_name(nbt)), nbt, bx, top + 1, bz, col)
        if units.top_entity(nbt).get("NoGravity"):               # a flying bird
            y += units.FLY_LOW.get(str(units.top_entity(nbt)["id"]), units.FLY_HEIGHT)
        set_pos(nbt, x, float(y), z)
        out.append(nbt)
    if not out:
        return None
    root = Compound({"DataVersion": Int(MC["data_version"]), "Position": IntArray([cx, cz]),
                     "Entities": List[Compound]([e for e in out])})
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
            ("smoker", "smoker"), ("furnace", "furnace"), ("lectern", "lectern"), ("_shelf", "shelf"), ("_bed", "bed")]


def block_entity_type(state):
    name = state.split(":")[1].split("[")[0]
    for key, be in BE_TYPES:
        if key in name:
            return None if be == "bed" else be                       # 26.3 has no bed block entity
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
    # the terrain passes run only up to the highest ground or water: above it all is air (#701, 2× faster)
    n = int(np.clip(max(top.max(), wtop.max()) + 1 - MIN_Y, 1, HEIGHT))
    Y = np.arange(MIN_Y, MIN_Y + n, dtype=np.int32)[:, None, None]

    vol = np.zeros((HEIGHT, 16, 16), np.uint16)         # AIR
    low = np.where(Y < sub, np.where(Y < 0, DEEPSLATE, STONE), AIR).astype(np.uint16)
    low = np.where((Y >= sub) & (Y < top), sub_id, low)
    low = np.where(Y == top, top_id, low)
    water = (Y > top) & (Y <= wtop)
    vol[:n] = np.where(water, np.where(ice & (Y == wtop), ICE, WATER), low)
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

    # the scans below look only at the sections with blocks and one row of air over them (AIR = 0: the maximum of
    # an empty section is 0), so that a lower half of a plant at the top still sees the air above it
    full = np.flatnonzero(vol.reshape(HEIGHT // 16, 4096).max(1))
    used = vol[:min(HEIGHT, 16 * (int(full[-1]) + 1) + 1) if len(full) else 16]

    # Tall plants: remove an upper half without its lower half (when an object took the place of the lower half)
    counts = np.bincount(used.ravel(), minlength=len(B.states))
    for lower, upper in TALL_PLANTS:
        if not (counts[lower] or counts[upper]):        # the full scans below are slow: skip them when possible
            continue
        ys, zs, xs = np.nonzero(used[1:] == upper)
        bad = used[ys, zs, xs] != lower
        used[ys[bad] + 1, zs[bad], xs[bad]] = AIR
        ys, zs, xs = np.nonzero(used[:-1] == lower)
        bad = used[ys + 1, zs, xs] != upper
        used[ys[bad], zs[bad], xs[bad]] = SHORT_GRASS

    # A carpet on the ground with room above it but a solid block or leaves 2 above it: a unit (1.95 high) does not
    # fit on the 1/16 carpet, so Minecraft finds no path through the cell (moss under the low leaves of a forest, #889).
    # A barrier over it is a footprint: no unit walks there, and a rug stays
    carpet, passable = ground_masks()
    if counts[carpet[:len(counts)]].any():
        gy = np.clip(top[0].astype(int) + 1 - MIN_Y, 0, HEIGHT - 3)
        zs, xs = np.indices(gy.shape)
        over = vol[gy + 2, zs, xs]
        low = carpet[vol[gy, zs, xs]] & passable[vol[gy + 1, zs, xs]] & ~passable[over] & (over != BARRIER)
        vol[gy[low], zs[low], xs[low]] = AIR

    # Blocks under the water surface are waterlogged, else they leave a dry gap in the water
    low = vol[:n]                                       # a view: the water is below n
    wet = water & (low != WATER) & (low != ICE)
    if wet.any():
        vals, inv = np.unique(low[wet], return_inverse=True)
        low[wet] = np.array([B.wet(int(v)) for v in vals], np.uint16)[inv]

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
        for y, z, x in zip(*np.nonzero(used == i)):
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


def write_objects(path, size, T, H, players, objects, cols, ground, timeline=None, mood="DEFAULT", map_ground=None,
                  victory=None, messages=None, lists=None):
    """aoe2mc.json: the data that a game program needs (docs/research/gameplay.md). Tiles are in the turned grid
    (--orientation): block x = tile x × T, block z = tile y × T. Units have the UUID of their entity, buildings
    their footprint [x0, z0, x1, z1) in blocks. Objects of a recorded game have their object ID ("ref").
    Objects that the converter did not place are not in the list.
    A building has the free cells of its ground floor (the hall of a town center, #2054) and their y ("inside",
    buildings.INSIDE) for a garrison, and the cells of its footprint that units walk through ("open": the town
    center, #865).
    "ground" has one string per block row z: for each x the y where a unit stands, or "-" for water.
    "timeline" (recorded games only): the events of read_timeline, with tiles in the turned grid
    and the "names" of the selected objects (name_timeline).
    "players" of a scenario also have its "resources" (food, wood, gold, stone), "pop_limit" and "computer" (#2539).
    "mood": the map color mood of a DE scenario (ColorMood name, #1594), else "DEFAULT".
    lists: the lists of the scenario mode (key -> list, TRIGGER_LISTS), each one if it is not empty.
    "map_ground": the map bytes of map 0 without the objects (map_colors), one hex string per pixel row z: the live
    minimap of the plugin paints them where no live object is (#1940).
    "victory" (DE scenarios only): the victory setting of the scenario, {"condition": a name of run.VICTORIES or
    "custom" (only its triggers end the game), "score" or "years" of that condition} (#2566).
    "messages": the scenario texts of CHAPTERS that are not empty (chapter -> text): the book of the scenario mode (#2541)."""
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
        for k in ("uuid", "footprint", "open"):
            if k in o:
                e[k] = o[k]
        if o.get("ref") is not None:                    # the object ID of a recorded game (#407, #408)
            e["ref"] = o["ref"]
        if o["kind"] == "U" and o.get("garrisoned") and o.get("holder") is not None:
            e["holder"] = o["holder"]                   # the reference ID of its building or ship (#807)
        if o["kind"] == "B" and o.get("ref") in buildings.INSIDE:    # where the game program puts a garrison (#808)
            cells, y, _ = buildings.INSIDE[o["ref"]]
            e["inside"] = {"y": int(y), "cells": [[int(x), int(z)] for x, z in cells[:GARRISON_CELLS]]}
        objs.append(e)
    data = {"map_size": size, "tile_size": T, "level_height": H, "mood": mood,
            "players": {str(pid): {"civ": p["civ"], "color": p["color"], "arch": p["arch"]}
                        | {k: p[k] for k in ("team", "neutral", "resources", "pop_limit", "computer") if k in p} for pid, p in sorted(players.items())},
            "objects": objs}
    n, wet = cols.n, cols.wtop > cols.top
    data["ground"] = [" ".join("-" if wet[x, z] else str(ground[x, z]) for x in range(n)) for z in range(n)]
    if timeline is not None:
        data["timeline"] = timeline
    if victory is not None:
        data["victory"] = victory
    if messages and (texts := {k: v for k, v in messages.items() if k in CHAPTERS and (v or "").strip()}):
        data["messages"] = texts
    for key, items in (lists or {}).items():
        if items:
            data[key] = list(items)
    if map_ground is not None:
        data["map_ground"] = [bytes(row).hex() for row in np.asarray(map_ground, np.uint8)]
    with open(path, "w") as f:
        json.dump(data, f, indent=1)


# Work sounds at buildings (#220): name part -> (sound, predicate, particle). Only Minecraft sounds; the villager
# work sounds exist in 26.3. The first matching rule wins.
WORK_SOUNDS = [(r["name"], r["sound"], r["when"], r["particle"]) for r in units.rows("work_sounds.jsonl")]
CHANCE = {"sometimes": 0.25, "rare": 0.03}      # per pulse of 2 s

# Ambience per terrain group (#219): vanilla biomes of `terrain_style` -> particle and sound near each player in such
# a biome (datapack function, no warning), and the colors of the custom biome of `--ambience full` (the client shows
# the "Experimental Settings" warning for it, docs/datapack.md). Particles: only types without options.
# Colors: sky, fog, water, water fog (0xRRGGBB), then extra `effects`.
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
    """The custom biome of a group (docs/datapack.md, "Biome files"): colors are "#rrggbb", sky and fog are
    attributes (26.x)."""
    (t, rain, precip), (sky, fog, water, water_fog), extra = AMBIENCE[group][3:]
    hx = "#{:06x}".format
    return {"has_precipitation": precip, "temperature": t, "downfall": rain,
            "effects": {"water_color": hx(water)} | extra,
            "attributes": {"minecraft:visual/sky_color": hx(sky), "minecraft:visual/fog_color": hx(fog),
                           "minecraft:visual/water_fog_color": hx(water_fog)},
            "features": [], "carvers": []}


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


def team_lines(objects, players):
    """(load, pulse) commands: one team per player with units, in the player color (#358). The pulse puts new
    units in their team: a load function reaches only the entities of loaded chunks."""
    load, pulse = [], []
    for n in sorted({o["player"] for o in objects if o["kind"] == "U" and o["player"]}):
        p = players.get(n, {})
        civ = "" if p.get("civ") in (None, "RANDOM") else str(p["civ"]).replace("_", " ").title()
        load += [f'team add p{n} "Player {n}{f" ({civ})" if civ else ""}"',
                 f"team modify p{n} color {units.TEAM_COLOR.get(p.get('color'), 'white')}",
                 f"team modify p{n} seeFriendlyInvisibles false"]       # the invisible target slime of a building (#1538)
        pulse.append(f"team join p{n} @e[tag=aoe2mc.p{n},team=]")
    return load, pulse


# AoE2 condition and effect IDs (AoE2ScenarioParser), one per line in alphabetical order (#2613)
ACCUMULATE_ATTRIBUTE = 8                                           # a resource of a player (#2655)
AND = 57                                                           # the conditions "AND" and "OR" (#2765)
ATTACK_MOVE = 30                                                   # "Attack Move" (#2647)
BUILD_OBJECT = 108                                                 # "Build Object" (#2863)
CHANGE_COLOR_MOOD = 72
CHANGE_DIPLOMACY = 1                                               # "Change Diplomacy" (#2645)
CHANGE_OBJECT_ARMOR = 31                                           # "Change Object Armor" (#2755)
CHANGE_OBJECT_ATTACK = 28                                          # "Change Object Attack" (#2755)
CHANGE_OBJECT_COST = 40                                            # "Change Object Cost" (#2776)
CHANGE_OBJECT_HP = 27                                              # "Change Object HP" (#2693)
CHANGE_OBJECT_NAME = 26                                            # "Change Object Name" (#2616)
CHANGE_OBJECT_PLAYER_COLOR = 58                                    # "Change Object Player Color" (#2824)
CHANGE_OBJECT_RANGE = 32                                           # "Change Object Range" (#2767)
CHANGE_OBJECT_SPEED = 33                                           # "Change Object Speed" (#2694)
CHANGE_OBJECT_STANCE = 36                                          # "Change Object Stance" (#2705)
CHANGE_OBJECT_VISIBILITY = 107                                     # "Change Object Visibility" (#2862)
CHANGE_OWNERSHIP = 18
CHANGE_PLAYER_COLOR = 89                                           # "Change Player Color" (#2712)
CHANGE_PLAYER_NAME = 45                                            # "Change Player Name" (#2711)
CHANGE_TECHNOLOGY_COST = 63                                        # "Change Technology Cost" (#2819)
CHANGE_TECHNOLOGY_LOCATION = 47                                    # "Change Technology Location" (#2864)
CHANGE_TECHNOLOGY_NAME = 65                                        # "Change Technology Name" (#2821)
CHANGE_TRAIN_LOCATION = 46                                         # "Change Train Location" (#2864)
CHANGE_VARIABLE = 56                                               # the scenario variables (#2611)
CHANGE_VIEW = 16                                                   # "Change View" (#2610)
CLEAR_INSTRUCTIONS = 21                                            # "Clear Instructions" (#2609)
CLEAR_TIMER = 57                                                   # "Clear Timer" (#2696)
COMPARE_VARIABLES = 78                                             # the condition "Compare Variables" (#2698)
COUNT_UNITS_INTO_VARIABLE = 101                                    # "Count Units into Variable" (#2697)
CREATE_GARRISONED_OBJECT = 49                                      # "Create Garrisoned Object" (#2764)
CREATE_OBJECT = 11
CREATE_OBJECT_ARMOR = 78                                           # "Create Object Armor" (#2855)
CREATE_OBJECT_ATTACK = 77                                          # "Create Object Attack" (#2855)
DAMAGE_OBJECT = 24                                                 # "Damage Object" (#2571)
DECLARE_VICTORY = 13                                               # "Declare Victory" (#2542)
DISABLE_OBJECT_SELECTION = 70                                      # "Disable Object Selection" (#2854)
DISABLE_UNIT_ATTACKABLE = 98                                       # "Disable Unit Attackable" (#2695)
DISABLE_UNIT_TARGETING = 61                                        # "Disable Unit Targeting" (#2826)
DIFFICULTY_LEVEL = 19                                              # the condition "Difficulty Level" (#2704)
DIPLOMACY_STATE = 24                                               # the condition "Diplomacy State" (#2757)
DISPLAY_INSTRUCTIONS = 20
DISPLAY_TIMER = 37                                                 # "Display Timer" (#2572)
ENABLE_DISABLE_OBJECT = 38                                         # "Enable/Disable Object" (#2775)
ENABLE_DISABLE_TECHNOLOGY = 39                                     # "Enable/Disable Technology" (#2775)
ENABLE_OBJECT_SELECTION = 71                                       # "Enable Object Selection" (#2854)
ENABLE_UNIT_ATTACKABLE = 99                                       # "Enable Unit Attackable" (#2695)
ENABLE_UNIT_TARGETING = 62                                         # "Enable Unit Targeting" (#2826)
DISPLAY_TIMER_TRIGGERED = 55                                       # the condition of its score (#2702)
FREEZE_OBJECT = 22                                                 # "Freeze Object" (#2608)
HEAL_OBJECT = 34                                                   # "Heal Object" (#2692)
INITIATE_RESEARCH = 76                                             # "Initiate Research" (#2772)
IN_AREA = 5
KILL_OBJECT = 14
LOCK_GATE = 7                                                      # "Lock Gate", "Unlock Gate" (#2762)
MIRROR_DIPLOMACY = 109                                             # "Mirror Diplomacy" (#2822)
MODIFY_ATTRIBUTE = 51                                              # "Modify Attribute" (#2763)
MODIFY_ATTRIBUTE_FOR_CLASS = 104                                   # "Modify Attribute for Class" (#2859)
MODIFY_RESOURCE = 52                                               # "Modify Resource" (#2576)
MODIFY_RESOURCE_BY_VARIABLE = 53                                   # "Modify Resource by Variable" (#2768)
MODIFY_VARIABLE_BY_ATTRIBUTE = 87                                  # "Modify Variable by Attribute" (#2858)
MODIFY_VARIABLE_BY_RESOURCE = 86                                   # "Modify Variable by Resource" (#2823)
MODIFY_VARIABLE_BY_VARIABLE = 100                                  # "Modify Variable by Variable" (#2713)
OBJECT_HAS_ACTION = 28                                             # the condition "Object Has Action" (#2867)
OBJECT_HP = 23                                                     # "Object HP", the hit points of one object (#2701)
OBJECT_NOT_VISIBLE = 16                                            # the conditions "Object (Not) Visible" (#2756)
OBJECT_VISIBLE = 15
OBJECT_VISIBLE_MULTIPLAYER = 27
OR = 29
OWN_FEWER_OBJECTS = 4                                              # conditions on the units of a player (#2573)
OWN_OBJECTS = 3
PATROL = 19                                                        # "Patrol" (#2647)
PLAYER_DEFEATED = 13                                               # the condition "Player Defeated" (#2710)
PLACE_FOUNDATION = 25                                              # "Place Foundation" (#2825)
PLAY_SOUND = 4                                                     # "Play Sound" (#2644)
REMOVE_OBJECT = 15
REPLACE_OBJECT = 43                                                # "Replace Object" (#2703)
RESEARCHED = 9                                                     # the condition "Research Technology" (#2656)
RESEARCHING_TECH = 17                                              # the condition "Researching Technology" (#2769)
RESEARCH_TECHNOLOGY = 2                                            # "Research Technology" (#2577)
SEND_CHAT = 3
SET_PLAYER_VISIBILITY = 41                                         # "Set Player Visibility" (#2774)
STOP_OBJECT = 29                                                   # "Stop Object" (#2754)
TASK_OBJECT = 12                                                   # "Task Object" (#2646)
TECHNOLOGY_STATE = 21                                              # the condition "Technology State" (#2769)
TELEPORT_OBJECT = 35
ACTIVATE_TRIGGER, DEACTIVATE_TRIGGER = 8, 9
TIMER = 10
TRAIN_UNIT = 75                                                    # "Train Unit" (#2772)
TRIBUTE = 5                                                        # "Tribute" (#2576)
TRIGGER_ACTIVE = 79                                                # the condition "Trigger Active" (#2699)
TRIGGER_CHANCE = 20                                                # the condition "Chance" (#2574)
UNITS_GARRISONED = 18                                              # the condition "Units Garrisoned" (#2714)
UNLOAD = 17                                                        # "Unload" (#2773)
UNLOCK_GATE = 6
VARIABLE_VALUE = 22
# The AoE2 UnitAIAction values of "Object Has Action" that the game program knows (game/scenario.py ACTIONS, #2867):
# build, gather, hunt, move, enter (garrison), repair, idle. The others (attack, convert, heal ...): not supported yet.
OBJECT_ACTIONS = (3, 10, 11, 14, 18, 19, 24)
TIME_UNITS = {0: 5, 1: 60, 2: 1, 3: 1}  # TimeUnit (years, minutes, seconds, m:ss) -> game seconds; a year as game/wonder.py YEAR
COUNTED = (IN_AREA, OWN_OBJECTS, OWN_FEWER_OBJECTS)                # conditions that count units: the tick function
VISIBLE = (OBJECT_NOT_VISIBLE, OBJECT_VISIBLE, OBJECT_VISIBLE_MULTIPLAYER)  # the sight of a player: the game program
TICKED = COUNTED + (                                               # conditions of the tick function, one per line
    ACCUMULATE_ATTRIBUTE,
    COMPARE_VARIABLES,
    DIFFICULTY_LEVEL,
    DIPLOMACY_STATE,
    DISPLAY_TIMER_TRIGGERED,
    OBJECT_HAS_ACTION,
    OBJECT_HP,
    OBJECT_NOT_VISIBLE,
    OBJECT_VISIBLE,
    OBJECT_VISIBLE_MULTIPLAYER,
    PLAYER_DEFEATED,
    RESEARCHED,
    RESEARCHING_TECH,
    TECHNOLOGY_STATE,
    TRIGGER_ACTIVE,
    UNITS_GARRISONED,
    VARIABLE_VALUE,
)
ATTRIBUTES = ("Food", "Wood", "Stone", "Gold")     # attributes 0-3: the score holders of gather.RESOURCES (#2655)
BRING_OBJECT_TO_AREA = 1                                               # the condition "Bring Object to Area" (#2620)
BRING_OBJECT_TO_OBJECT = 2                                             # the condition "Bring Object to Object" (#2771)
DESTROY_OBJECT = 6                                                     # the condition "Destroy Object" (#2618)
CAPTURE_OBJECT = 7                                                     # the condition "Capture Object" (#2619)
OBJECT_ATTACKED = 76                                                   # the condition "Object Attacked" (#2779)
# The conditions on one object of the map (its tag aoe2mc.r<ref>, #2617): the test of the tick function when it holds,
# when it does not hold (a looping trigger fires again after that), and the tick lines before the test. "Destroy
# Object": a marker entity follows the unit; the unit is dead when the marker is loaded and the unit is not there. A
# unit in a chunk that is not loaded is no entity for a command, and its marker is not loaded too (#2618).
OBJECT_TESTS = {DESTROY_OBJECT: ("if entity @e[tag=aoe2mc.m{ref}] unless entity @e[tag=aoe2mc.r{ref}]",
                                 "if entity @e[tag=aoe2mc.r{ref}]",
                                 ("execute as @e[tag=aoe2mc.r{ref}] at @s unless entity @e[tag=aoe2mc.m{ref}] run "
                                  "summon marker ~ ~ ~ {{Tags:[\"aoe2mc.m{ref}\"]}}",
                                  "execute as @e[tag=aoe2mc.r{ref}] at @s run tp @e[tag=aoe2mc.m{ref}] ~ ~ ~")),
                 # "Capture Object": the unit has the tag of the player of the condition (its owner, #2570)
                 CAPTURE_OBJECT: ("if entity @e[tag=aoe2mc.r{ref},tag=aoe2mc.p{player}]",
                                  "unless entity @e[tag=aoe2mc.r{ref},tag=aoe2mc.p{player}]", ()),
                 # "Object Attacked": the unit took damage in the last 10 ticks (HurtTime, #2779). Vanilla has no
                 # attacker of a hurt entity in a selector: each attacker counts (a "near unit of the player" test
                 # misses the archers), the source player of the condition is not tested
                 OBJECT_ATTACKED: ("if entity @e[tag=aoe2mc.r{ref},nbt=!{{HurtTime:0s}}]",
                                   "unless entity @e[tag=aoe2mc.r{ref},nbt=!{{HurtTime:0s}}]", ()),
                 # "Bring Object to Area": the unit is in the box of the area ({box}: area_box, #2620)
                 BRING_OBJECT_TO_AREA: ("if entity @e[tag=aoe2mc.r{ref}{box}]",
                                        "unless entity @e[tag=aoe2mc.r{ref}{box}]", ()),
                 # "Bring Object to Object": the unit is next to the other unit, within one tile ({near} blocks, #2771)
                 BRING_OBJECT_TO_OBJECT: ("at @e[tag=aoe2mc.r{ref},limit=1] if entity @e[tag=aoe2mc.r{next},distance=..{near}]",
                                          "at @e[tag=aoe2mc.r{ref},limit=1] unless entity "
                                          "@e[tag=aoe2mc.r{next},distance=..{near}]", ())}
TICKED += tuple(OBJECT_TESTS)
INVERTED = tuple(OBJECT_TESTS) + (                                  # conditions with an inverted test in the tick
    COMPARE_VARIABLES,                                                 # function, one per line in alphabetical order
    OBJECT_HAS_ACTION,
    TRIGGER_ACTIVE,                                                    # (parallel tickets add lines, #2791)
)


def area_keys(c, entities, techs):
    return [c.area_x1, c.area_y1, c.area_x2, c.area_y2]


def tech_name(c, entities, techs):
    return techs.get(c.technology, str(c.technology))      # a name of game/data/train.jsonl


# The keys of the condition dict of read_scenario beyond the common ones: key -> attribute of the scenario condition,
# or (condition, entities, techs) -> value. A condition on one object (OBJECT_TESTS) also gets OBJECT_KEYS. A new
# condition is one line here, in alphabetical order (#2832): parallel trigger tickets conflicted in read_scenario.
OBJECT_KEYS = {"ref": "unit_object", "unit": lambda c, entities, techs: c.unit_object in entities,   # #2618
               "player": "source_player"}
COUNT_KEYS = {"quantity": "quantity", "player": "source_player", "area": area_keys, "object": "object_list",
              "group": "object_group", "class": "object_type"}
TECH_KEYS = {"player": "source_player", "technology": tech_name}                         # (#2656)
CONDITION_KEYS = {
    ACCUMULATE_ATTRIBUTE: {"quantity": "quantity", "player": "source_player", "attribute": "attribute"},   # (#2655)
    BRING_OBJECT_TO_AREA: {"area": area_keys},                                           # (#2620)
    BRING_OBJECT_TO_OBJECT: {"next": "next_object",                                      # (#2771)
                             "next_unit": lambda c, entities, techs: c.next_object in entities},
    COMPARE_VARIABLES: {"variable": "variable", "variable2": "variable2", "comparison": "comparison"},   # (#2698)
    DIFFICULTY_LEVEL: {"quantity": "quantity"},                                          # (#2704)
    DIPLOMACY_STATE: {"player": "source_player", "target": "target_player", "diplomacy": "quantity"},   # the stance (#2757)
    DISPLAY_TIMER_TRIGGERED: {"slot": "timer_id"},                                       # (#2702)
    IN_AREA: COUNT_KEYS,
    OBJECT_HAS_ACTION: {"ref": "unit_object", "next": "next_object", "action": "unit_ai_action"},   # (#2867)
    OBJECT_HP: {"quantity": "quantity", "ref": "unit_object", "comparison": "comparison"},   # (#2701)
    OBJECT_NOT_VISIBLE: {"ref": "unit_object", "player": lambda c, entities, techs: 1},   # player 1 sees (#2756)
    OBJECT_VISIBLE: {"ref": "unit_object", "player": lambda c, entities, techs: 1},
    OBJECT_VISIBLE_MULTIPLAYER: {"ref": "unit_object", "player": "source_player"},
    OWN_FEWER_OBJECTS: COUNT_KEYS,
    OWN_OBJECTS: COUNT_KEYS,
    PLAYER_DEFEATED: {"player": "source_player"},                                        # (#2710)
    RESEARCHED: TECH_KEYS,
    RESEARCHING_TECH: TECH_KEYS,                                                         # (#2769)
    TECHNOLOGY_STATE: TECH_KEYS | {"quantity": "quantity"},                              # (#2769)
    TRIGGER_ACTIVE: {"trigger": "trigger_id"},                                           # (#2699)
    TRIGGER_CHANCE: {"quantity": "quantity"},                                            # (#2574)
    UNITS_GARRISONED: {"quantity": "quantity", "unit": "unit_object"},                   # (#2714)
    VARIABLE_VALUE: {"quantity": "quantity", "variable": "variable", "comparison": "comparison"},   # (#2611)
}
STORES = ("food", "wood", "stone", "gold")      # the resource of a tribute_list (AoE2 attributes 0 to 3)
OPERATIONS = {1: "set", 2: "add", 3: "remove"}  # set, add, subtract of Modify Resource (AoE2ScenarioParser Operation)
HP_OPERATIONS = {1: "set", 2: "add", 3: "subtract", 4: "multiply", 5: "divide"}   # Change Object HP (#2693)
STANCES = (0, 1, 3)                                # DiplomacyState: ally, neutral, enemy
SOUNDS = [(r["name"], r["sound"]) for r in units.rows("sounds.jsonl")]  # AoE2 sound name part -> vanilla sound


def turn_area(area, size, k):
    """The tile area [x1, y1, x2, y2] (both ends included, -1: the whole map) after k quarter turns (turn_tile)."""
    if min(area) < 0:
        return area
    (a, b), (c, d) = (turn_tile(x + 0.5, y + 0.5, size, k) for x, y in (area[:2], area[2:]))
    return [int(min(a, c)), int(min(b, d)), int(max(a, c)), int(max(b, d))]


def area_selector(c, T):
    """The entity selector of the units of the player of an "Objects in Area" condition: the blocks of the tiles
    x1..x2, y1..y2 (z), all heights. An area of -1 is the whole map. A unit type filter is the tag aoe2mc.t<id>
    of the units (#681); the "object" of an effect (a name, #656) is not a filter here. The horse of a unit has the player
    tag too (units.MOUNT, #1045): it does not count."""
    obj = c.get("object")
    sel = [f"tag=aoe2mc.p{c['player']}", f"tag=!{units.MOUNT}"] + [f"tag=aoe2mc.t{obj}"] * (isinstance(obj, int) and obj >= 0)
    return f"@e[{','.join(sel)}{area_box(c['area'], T)}]"


def area_box(area, T):
    """The selector part ",x=..,dz=.." of the blocks of the tiles x1..x2, y1..y2 (z) of an area, all heights; "" for an
    area of -1 (the whole map)."""
    if min(area) < 0:
        return ""
    x1, y1, x2, y2 = area
    x1, x2, y1, y2 = min(x1, x2), max(x1, x2), min(y1, y2), max(y1, y2)
    return f",x={x1 * T},y={MIN_Y},z={y1 * T},dx={(x2 - x1 + 1) * T - 1},dy={HEIGHT - 1},dz={(y2 - y1 + 1) * T - 1}"


def object_lines(e, c):
    """The commands of "Create Object" and "Remove Object" (#656): a summon of the entity of units.make_entity at
    the middle of the tile, or a kill of the units of the player and type in the area (area_selector). "Kill Object"
    (#2568) is the same kill, also with no area (the whole map): Minecraft shows the death, as AoE2.
    Buildings and other objects are not supported yet: they count in stats."""
    t, T, ground, players, stats = c.t, c.T, c.ground, c.players, c.stats
    kind, name = e.get("object") or (None, None)
    if e["type"] == CREATE_OBJECT and min(e.get("tile", [-1])) >= 0:
        x, z = (int((v + 0.5) * T) for v in e["tile"])
        o = dict(name=name, player=max(e["player"], 0), rotation=math.pi / 2)
        nbt = units.make_entity(o, players or {}, (x + 0.5, 0.0, z + 0.5), np.random.default_rng(t["id"])) \
            if kind in ("U", "H") and 0 <= x < ground.shape[0] and 0 <= z < ground.shape[1] else None
        if nbt is None:
            stats["create (not supported yet)"] += 1
            return []
        stats["create"] += 1
        kind = str(nbt.pop("id"))
        del nbt["Pos"]
        parts = [nbt]                                                  # Minecraft gives new UUIDs: a looping
        while parts:                                                   # trigger or two effects never clash
            part = parts.pop()
            part.pop("UUID", None)
            parts += list(part.get("Passengers", []))
        return [f"summon {kind} {x + 0.5} {int(ground[x, z])} {z + 0.5} {nbt.snbt()}"]
    if e["type"] == KILL_OBJECT or e["type"] == REMOVE_OBJECT and min(e.get("area", [-1])) >= 0:
        word = "kill" if e["type"] == KILL_OBJECT else "remove"
        if name is None and e["player"] <= 0 and e["type"] == KILL_OBJECT:   # Gaia units have no tag: a kill
            stats["kill (not supported yet)"] += 1                     # of all would kill the decor entities too
            return []
        if (found := effect_units(e, T)) is None:
            stats[f"{word} (not supported yet)"] += 1
            return []
        at, top, nbt = found
        stats[word] += 1
        ride = [f"execute as {at} on vehicle run kill @s"] if top is not None and top is not nbt else []
        return ride + [f"kill {at}"]                                       # a rider: its mount goes too
    return []


def effect_units(e, T):
    """(selector, top entity, entity) of the units of an effect: its player (Gaia units have no player tag), area
    (area_selector) and unit type (the type of the top entity of units.make_entity). No type: (selector, None, None).
    A type with no entity (a building): None."""
    kind, name = e.get("object") or (None, None)
    at = area_selector(e, T)
    if e["player"] <= 0:                                           # never a player (#2568)
        at = re.sub(r"tag=aoe2mc\.p-?\d+,?", "type=!minecraft:player,", at)
    if name is None:
        return at, None, None
    nbt = units.make_entity(dict(name=name, player=0), {}, (0.0, 0.0, 0.0), np.random.default_rng(0)) \
        if kind in ("U", "H") else None
    if nbt is None:
        return None
    top = units.top_entity(nbt)
    return f"@e[type={top['id']},{at[3:]}".replace(",type=!minecraft:player", ""), top, nbt


def damage_lines(e, c):
    """The commands of "Damage Object" (#2571): a `damage` of each unit of the effect (effect_units) by its amount.
    The amount is in AoE2 hit points: the game program gives each unit max_health = its AoE2 hit points
    (combat.stats_command); a vanilla world keeps the health of the mob. A negative amount heals in AoE2: not yet."""
    q, stats = e.get("quantity") or 0, c.stats
    found = effect_units(e, c.T) if q > 0 else None
    if found is None:
        stats["damage (heal or building, not supported yet)" if q else "damage (no amount)"] += 1
        return []
    at = found[0]                                                      # Gaia: not the players (effect_units)
    stats["damage"] += 1
    return [f"execute as {at} run damage @s {q}"]                      # damage takes one entity


def attack_lines(e, c):
    """The commands of "Change Object Attack" and "Change Object Armor" (#2755): the units of the player in the area and
    the mounts of the riders get an attribute modifier of `quantity` AoE2 points, add or subtract: minecraft:attack_damage
    (the attack classes 3 pierce and 4 melee) or minecraft:armor. The game program sets these attributes from
    combat.STATS, so the points are AoE2 points. The modifier ID is the trigger and the effect: one modifier each."""
    q, stats = e.get("quantity") or 0, c.stats
    armor = e["type"] == CHANGE_OBJECT_ARMOR
    op = OPERATIONS.get(e.get("operation"))
    if op not in ("add", "remove") or not q or (not armor and e.get("armour_class") not in (3, 4)):
        stats["change object attack or armor (not supported yet)"] += 1
        return []
    stats["change object armor" if armor else "change object attack"] += 1
    at = unit_selector(e, c.T)
    attr = "minecraft:armor" if armor else "minecraft:attack_damage"
    value = q if op == "add" else -q
    return [f"execute as {at} run attribute @s {attr} modifier add aoe2mc:trig_{c.t['id']}_{effect_index(e, c)} {value} add_value"]


def garrisoned_lines(e, c):
    """The commands of "Create Garrisoned Object" (#2764): a summon of the unit (object2, units.make_entity) in the
    state of a garrisoned unit of the converter (plan_units, #807) on the inside cells of each selected building
    (buildings.INSIDE). The tag MADE_INSIDE lets the game program add it to the garrison, so UNGARRISON lets it out.
    A holder that is not a building with rooms (a ship, a ram) or no selected object: not supported yet."""
    kind, name = e.get("object2") or (None, None)
    holders = [r for r in e.get("selected", []) if r in buildings.INSIDE]
    nbt = units.make_entity(dict(name=name, player=max(e["player"], 0), rotation=math.pi / 2), c.players or {},
                            (0.0, 0.0, 0.0), np.random.default_rng(c.t["id"])) if kind in ("U", "H") else None
    if nbt is None or not holders:
        c.stats["create garrisoned (not supported yet)"] += 1
        return []
    c.stats["create garrisoned"] += 1
    label = units.top_entity(nbt)
    label["CustomNameVisible"] = Byte(0)
    label["Tags"] = List[String](list(label.get("Tags", [])) + [String(GARRISONED), String(MADE_INSIDE)])
    entity = str(nbt.pop("id"))
    del nbt["Pos"]
    parts = [nbt]                                                      # new UUIDs (object_lines), no damage inside
    while parts:
        part = parts.pop()
        part.pop("UUID", None)
        part["Invulnerable"], part["NoAI"] = Byte(1), Byte(1)
        parts += list(part.get("Passengers", []))
    lines = []
    for ref in holders:                                                # one unit per building, as in AoE2
        cells, y, center = buildings.INSIDE[ref]
        x, z = cells[0] if len(cells) else center
        lines.append(f"summon {entity} {x + 0.5} {int(y)} {z + 0.5} {nbt.snbt()}")
    return lines


def hp_lines(e, c):
    """The commands of "Change Object HP" (#2693): the max_health of the units of the effect (effect_units) is the new
    hit points. A set is one `attribute ... base set`. The other operations read the base of each unit into the score
    #hp of aoe_hp, compute it there and set it with the macro hp/apply (the value is in the storage aoe2mc:hp). The
    hit points stay in 1 to 1024 (the limit of the attribute). The function is named by the operation: the same
    effect in two triggers writes the same file."""
    op, q, stats = HP_OPERATIONS.get(e.get("operation")), e.get("quantity"), c.stats
    found = effect_units(e, c.T) if op and q is not None and (op != "divide" or q) else None
    if found is None:
        stats["change object hp (not supported yet)"] += 1
        return []
    stats["change object hp"] += 1
    at = found[0]
    if op == "set":
        return [f"execute as {at} run attribute @s minecraft:max_health base set {min(max(q, 1), 1024)}"]
    c.setup["scoreboard objectives add aoe_hp dummy"] = None
    if op in ("multiply", "divide"):
        change = [f"scoreboard players set #k aoe_hp {q}",
                  f"scoreboard players operation #hp aoe_hp {'*=' if op == 'multiply' else '/='} #k aoe_hp"]
    else:
        s = q if op == "add" else -q
        change = [f"scoreboard players {'add' if s >= 0 else 'remove'} #hp aoe_hp {abs(s)}"]
    name = f"hp/{op}_{q}"
    c.files[f"data/aoe2mc/function/{name}.mcfunction"] = "\n".join(
        ["execute store result score #hp aoe_hp run attribute @s minecraft:max_health base get"] + change +
        ["execute if score #hp aoe_hp matches 1025.. run scoreboard players set #hp aoe_hp 1024",
         "execute if score #hp aoe_hp matches ..0 run scoreboard players set #hp aoe_hp 1",
         "execute store result storage aoe2mc:hp value int 1 run scoreboard players get #hp aoe_hp",
         "function aoe2mc:hp/apply with storage aoe2mc:hp"]) + "\n"
    c.files["data/aoe2mc/function/hp/apply.mcfunction"] = "$attribute @s minecraft:max_health base set $(value)\n"
    return [f"execute as {at} run function aoe2mc:{name}"]


def heal_lines(e, c):
    """The commands of "Heal Object" (#2692): each unit of the effect (effect_units) gets `quantity` AoE2 hit points
    back, not above its maximum. The scores aoe_hp (Health) and aoe_max (max_health) of the unit give the new Health:
    the score is the Health without its decimals. The game program gives max_health = its AoE2 hit points."""
    q, stats = e.get("quantity") or 0, c.stats
    found = effect_units(e, c.T) if q > 0 else None
    if found is None:
        stats["heal (building or no amount, not supported yet)" if q else "heal (no amount)"] += 1
        return []
    c.setup["scoreboard objectives add aoe_hp dummy"] = c.setup["scoreboard objectives add aoe_max dummy"] = None
    stats["heal"] += 1
    at = found[0]                                                      # Gaia: not the players (effect_units)
    return [f"execute as {at} store result score @s aoe_hp run data get entity @s Health",
            f"execute as {at} store result score @s aoe_max run attribute @s minecraft:max_health get",
            f"execute as {at} run scoreboard players add @s aoe_hp {q}",
            f"execute as {at} run scoreboard players operation @s aoe_hp < @s aoe_max",
            f"execute as {at} store result entity @s Health float 1 run scoreboard players get @s aoe_hp"]


def speed_lines(e, c):
    """The commands of "Change Object Speed" (#2694): the units of the player in the area and the mounts of the riders
    get the walk speed of `quantity` tiles per AoE2 second. The attribute is the rule of the game program
    (game/ai.py movement_speed, WALK; NORMAL of game/gather.py): sqrt(speed * T * NORMAL / WALK). Constants copied:
    the converter does not import the game program."""
    q, T, stats = e.get("quantity") or 0, c.T, c.stats
    if q <= 0 or min(e.get("area", [-1])) < 0:
        stats["change object speed (not supported)"] += 1
        return []
    stats["change object speed"] += 1
    at, value = unit_selector(e, T), round(math.sqrt(q * T * 1.7 / 43.4), 4)
    return [f"execute as {at} on vehicle run attribute @s minecraft:movement_speed base set {value}",
            f"execute as {at} run attribute @s minecraft:movement_speed base set {value}"]


def name_lines(e, c):
    """The commands of "Change Object Name" (#2616): the new name (with no AoE2 color tags) on the CustomName text of
    each unit of the effect (effect_units). The label of a unit is on its top entity (units.make_entity), and the
    selector has no mounts: the rider gets the name. Only the text changes, so the player color stays."""
    msg, stats = re.sub(r"<[^<>]*>", "", e["message"]).replace("\r", "").strip(), c.stats
    found = effect_units(e, c.T) if msg else None
    if found is None:
        stats["change object name (not supported yet)" if msg else "change object name (no name)"] += 1
        return []
    stats["change object name"] += 1
    return [f"execute as {found[0]} run data modify entity @s CustomName.text set value "   # one entity
            f"{json.dumps(msg, ensure_ascii=False)}"]


def location_lines(e, c):
    """The command of "Change Train Location" and "Change Technology Location" (#2864): the unit or technology of the
    player, its new building and its AoE2 button go into the list of the data storage aoe2mc:places as one text
    "<player> <name> <building> <button>". A converted world has no menus: the scenario mode of the game program
    (game/scenario.py places) moves the item in the menus of the player."""
    _, name = (e.get("object") or (None, None)) if e["type"] == CHANGE_TRAIN_LOCATION else (None, e.get("technology"))
    _, building = e.get("object2") or (None, None)
    if e["player"] <= 0 or not all(re.fullmatch(r"[A-Z0-9_]+", x or "") for x in (name, building)):
        c.stats["change train or technology location (not supported)"] += 1
        return []
    c.stats["change train or technology location"] += 1
    return [f'data modify storage aoe2mc:places list append value "{e["player"]} {name} {building} {e.get("button", -1)}"']


def tech_name_lines(e, c):
    """The command of "Change Technology Name" (#2821): the new name (with no AoE2 color tags) of the technology of the
    player goes into the list of the data storage aoe2mc:names as one text "<player> <technology> <name>". A converted
    world has no menus: the scenario mode of the game program (game/scenario.py names) shows it in the menus. A name
    of the game files only (string_id, no message): not supported."""
    msg = re.sub(r"<[^<>]*>", "", e["message"]).replace("\r", "").replace("\n", " ").strip()
    tech = e.get("technology", "")
    if e["player"] <= 0 or not msg or not re.fullmatch(r"[A-Z0-9_]+", tech):
        c.stats["change technology name (not supported)"] += 1
        return []
    c.stats["change technology name"] += 1
    text = f"{e['player']} {tech} {msg}".replace("\\", "\\\\").replace('"', '\\"')
    return [f'data modify storage aoe2mc:names list append value "{text}"']


def player_name_lines(e, c):
    """The commands of "Change Player Name" (#2711): the new name (with no AoE2 color tags) is the display name of the
    team p<player> (team_lines), in the sidebar and the tab list. Gaia or no name: no line."""
    msg = re.sub(r"<[^<>]*>", "", e["message"]).replace("\r", "").strip()
    if e["player"] <= 0 or not msg:
        return []
    c.stats["change player name"] += 1
    return [f"team modify p{e['player']} displayName {json.dumps({'text': msg}, ensure_ascii=False)}"]


def owner_lines(e, c):
    """The commands of "Change Ownership" (#2570): the units of the player in the area (area_selector) and their
    mounts get the tag and the team of the target player. A temporary tag marks them first: the selector uses the old
    player tag. Gaia has no player tag and no team: not supported yet."""
    old, new, T, stats = e["player"], e.get("target", -1), c.T, c.stats
    if old <= 0 or new <= 0 or old == new:
        stats["change ownership (not supported yet)"] += old != new
        return []
    stats["change ownership"] += 1
    own = "@e[tag=aoe2mc.own]"
    return [f"tag {area_selector(e, T)} add aoe2mc.own",
            f"execute as {own} on vehicle run tag @s add aoe2mc.own",
            f"tag {own} remove aoe2mc.p{old}", f"tag {own} add aoe2mc.p{new}",
            f"team join p{new} {own}", f"tag {own} remove aoe2mc.own"]


def replace_lines(e, c):
    """The commands of "Replace Object" (#2703): a summon of the entity of the new type (units.make_entity, as "Create
    Object") of the target player at each unit of the effect (effect_units), then a kill of the old units and their
    mounts. Minecraft cannot change the type of a mob. A temporary tag marks the old units first: a new unit of the
    same entity type and player must stay. A type with no entity (a building) is not supported yet."""
    T, stats = c.T, c.stats
    kind, name = e.get("object2") or (None, None)
    found = effect_units(e, T) if e.get("object") else None
    nbt = units.make_entity(dict(name=name, player=max(e.get("target", -1), 0), rotation=math.pi / 2), c.players or {},
                            (0.0, 0.0, 0.0), np.random.default_rng(c.t["id"])) if kind in ("U", "H") else None
    if found is None or nbt is None:
        stats["replace (not supported yet)"] += 1
        return []
    stats["replace"] += 1
    at, top, old = found
    entity = str(nbt.pop("id"))
    del nbt["Pos"]
    parts = [nbt]                                                      # Minecraft gives new UUIDs (object_lines)
    while parts:
        part = parts.pop()
        part.pop("UUID", None)
        parts += list(part.get("Passengers", []))
    mark = "@e[tag=aoe2mc.replace]"
    ride = [f"execute as {mark} on vehicle run kill @s"] if top is not old else []   # a rider: its mount goes too
    return [f"tag {at} add aoe2mc.replace", f"execute at {mark} run summon {entity} ~ ~ ~ {nbt.snbt()}"] + ride + \
        [f"kill {mark}"]


def resource_lines(e, c):
    """The commands of "Tribute" and "Modify Resource" (#2576): a converted world has no stock, so they only change
    the scores #p<N>.<resource> of aoe_res (the change) and aoe_set (a "set"). scenario.resources of the game program
    reads them into the stock of player N and resets them. A tribute of a trigger has no tax (AoE2)."""
    if not 0 <= e.get("resource", -1) < len(STORES) or e["player"] <= 0:
        return []
    c.setup["scoreboard objectives add aoe_res dummy"] = c.setup["scoreboard objectives add aoe_set dummy"] = None
    res, q = STORES[e["resource"]], int(e["quantity"])

    def change(n, q):
        return [f"scoreboard players {'add' if q >= 0 else 'remove'} #p{n}.{res} aoe_res {abs(q)}"] * (n > 0)
    if e["type"] == TRIBUTE:
        return change(e["target"], q) + change(e["player"], -q)
    if (op := OPERATIONS.get(e["operation"])) == "set":               # a set drops the earlier changes
        return [f"scoreboard players set #p{e['player']}.{res} aoe_set {q}",
                f"scoreboard players reset #p{e['player']}.{res} aoe_res"]
    return change(e["player"], q if op == "add" else -q) if op else []


def resource_by_variable_lines(e, c):
    """The commands of "Modify Resource by Variable" (#2768): the amount is the score #vN of aoe_var (the AoE2 variable
    N). Add and Subtract change aoe_res, a Set goes to aoe_set, as in resource_lines. Multiply and Divide have no line."""
    if not 0 <= e.get("resource", -1) < len(STORES) or e["player"] <= 0 or e.get("variable", -1) < 0:
        return []
    c.setup["scoreboard objectives add aoe_res dummy"] = c.setup["scoreboard objectives add aoe_set dummy"] = None
    target, v = f"#p{e['player']}.{STORES[e['resource']]}", f"#v{e['variable']} aoe_var"
    if (op := OPERATIONS.get(e["operation"])) == "set":
        return [f"scoreboard players operation {target} aoe_set = {v}", f"scoreboard players reset {target} aoe_res"]
    return [f"scoreboard players operation {target} aoe_res {'+' if op == 'add' else '-'}= {v}"] if op in ("add", "remove") else []


def variable_by_resource_lines(e, c):
    """The command of "Modify Variable by Resource" (#2823): variable N (operation)= the stock of the resource, the
    score of the game program (Gather.board, as resource_score: aoe_res for player 1, aoe_res<P> for the others)."""
    r, p, v, op = e.get("resource", -1), e.get("player", 0), e.get("variable", -1), e.get("operation")
    if not 0 <= r < len(ATTRIBUTES) or p <= 0 or v < 0 or op not in (1, 2, 3, 4, 5):
        c.stats["modify variable by resource (not supported)"] += 1
        return []
    c.stats["modify variable by resource"] += 1
    return [f"scoreboard players operation #v{v} aoe_var {('', '+', '-', '*', '/')[op - 1]}= "
            f"{ATTRIBUTES[r]} aoe_res{p if p > 1 else ''}"]


def teleport_lines(e, c):
    """The commands of "Teleport Object" (#2569): a tp of the units of the player in the area (area_selector) to the
    middle of the target tile, on the ground. A rider is not in the selector of its horse (units.MOUNT): the first line
    moves the mounts of the riders in the area, and the riders go with them. Then the riders are out of the area, so
    the second line (a tp of a rider takes it off its horse) moves only the units on foot."""
    if min(e.get("tile", [-1])) < 0 or min(e.get("area", [-1])) < 0:
        return []
    T, ground = c.T, c.ground
    x, z = (int((v + 0.5) * T) for v in e["tile"])
    if not (0 <= x < ground.shape[0] and 0 <= z < ground.shape[1]):
        return []
    at, to = unit_selector(e, T), f"{x + 0.5} {int(ground[x, z])} {z + 0.5}"
    return [f"execute as {at} on vehicle run tp @s {to}", f"tp {at} {to}"]


def variable_lines(e, c):
    """The commands of "Change Variable" (#2611): the score #vN of aoe_var is the AoE2 variable N. Set, Add and
    Subtract are scoreboard commands; Multiply and Divide need a second score: the constant #cQ."""
    v, q, op, stats = f"#v{e.get('variable', -1)} aoe_var", e.get("quantity") or 0, e.get("operation"), c.stats
    if e.get("variable", -1) < 0 or op not in (1, 2, 3, 4, 5) or op == 5 and q == 0:
        stats["change variable (not supported)"] += 1
        return []
    stats["change variable"] += 1
    if op <= 3:
        return [f"scoreboard players {('set', 'add', 'remove')[op - 1]} {v} {q}"]
    return [f"scoreboard players set #c{q} aoe_var {q}", f"scoreboard players operation {v} {'*/'[op - 4]}= #c{q} aoe_var"]


def variable_by_variable_lines(e, c):
    """The command of "Modify Variable by Variable" (#2713): variable (operation)= variable2, both scores of aoe_var.
    A division by 0 leaves the score as it is in Minecraft."""
    a, b, op = e.get("variable", -1), e.get("variable2", -1), e.get("operation")
    if a < 0 or b < 0 or op not in (1, 2, 3, 4, 5):
        c.stats["modify variable by variable (not supported)"] += 1
        return []
    c.stats["modify variable by variable"] += 1
    return [f"scoreboard players operation #v{a} aoe_var {('', '+', '-', '*', '/')[op - 1]}= #v{b} aoe_var"]


def count_lines(e, c):
    """The command of "Count Units into Variable" (#2697): the score #vN of aoe_var (N: variable2) is the number of
    units of the player and type in the area (effect_units; no area: the whole map). A building has no entity: no line."""
    v = e.get("variable2", -1)
    found = effect_units(e, c.T) if v >= 0 else None
    if found is None:
        c.stats["count units into variable (not supported)"] += 1
        return []
    c.stats["count units into variable"] += 1
    return [f"execute store result score #v{v} aoe_var if entity {found[0]}"]


def variable_range(c):
    """The `matches` range of the comparison of a "Variable Value" condition (#2611): Equal, Less, Larger,
    Less or Equal, Larger or Equal."""
    q = c.get("quantity") or 0
    return {0: f"{q}", 1: f"..{q - 1}", 2: f"{q + 1}..", 3: f"..{q}", 4: f"{q}.."}.get(c.get("comparison"))


def compare_test(c):
    """The score test of a "Compare Variables" condition (#2698): `score #vA aoe_var <op> #vB aoe_var`. Comparison 5
    (not equal) is "=", negated by compare_negated; None for a missing variable."""
    a, b, cmp = c.get("variable", -1), c.get("variable2", -1), c.get("comparison")
    if a < 0 or b < 0 or cmp not in range(6):
        return None
    return f"score #v{a} aoe_var {('=', '<', '>', '<=', '>=', '=')[cmp]} #v{b} aoe_var"


def compare_negated(c):
    """True when the test of a "Compare Variables" condition fails on a match: "not equal", or "Inverted" (#2698)."""
    return (c.get("comparison") == 5) != c["inverted"]


def task_lines(e, c):
    """The commands of "Task Object" (#2646), effect i of trigger t: the units of the player in the area get the tag
    aoe_task<t>_<i>, and the storage aoe2mc:tasks gets the key k<t>_<i> with the block of the middle of the tile, on the
    ground. Vanilla has no walk-to command: the scenario mode of the game program reads the storage (scenario.tasks)
    and walks the tagged units there with the Paper plugin (aoe moveto). A rider gives its tag to its horse (units.MOUNT):
    the plugin walks the horse. No area or no tile: no line."""
    T, ground = c.T, c.ground
    if min(e.get("tile", [-1])) < 0 or min(e.get("area", [-1])) < 0:
        return []
    x, z = (int((v + 0.5) * T) for v in e["tile"])
    if not (0 <= x < ground.shape[0] and 0 <= z < ground.shape[1]):
        return []
    k = f"{c.t['id']}_{effect_index(e, c)}"
    return tag_lines(e, T, f"aoe_task{k}") + \
        [f"data modify storage aoe2mc:tasks k{k} set value [{x + 0.5}d, {int(ground[x, z])}.0d, {z + 0.5}d]"]


def effect_index(e, c):
    """The index of effect e in its trigger c.t: a score or a tag of one effect (research_lines, task_lines)."""
    return next(i for i, f in enumerate(c.t["effects"]) if f is e)


def tag_lines(e, T, tag):
    """The commands that give the units of the player of an effect in its area the tag (task_lines, order_lines). A
    rider gives its tag to its horse (units.MOUNT): the plugin walks the horse."""
    return [f"tag {unit_selector(e, T)} add {tag}", f"execute as @e[tag={tag}] on vehicle run tag @s add {tag}",
            f"execute as @e[tag={tag}] on vehicle on passengers run tag @s remove {tag}"]


def resource_score(c):
    """The score test of an "Accumulate Attribute" condition (#2655): the resource score of the game program (the
    holder Food, Wood, Stone or Gold of `Gather.board`: aoe_res for player 1, aoe_res<N> for the others) at the quantity
    or more; None for an attribute that is no resource. A world without the game program has no such score."""
    a, p = c.get("attribute", -1), c.get("player", 0)
    if not 0 <= a < len(ATTRIBUTES) or p <= 0:
        return None
    return f"score {ATTRIBUTES[a]} aoe_res{p if p > 1 else ''} matches {max(c.get('quantity') or 0, 0)}.."


def unit_selector(e, T):
    """The area_selector of the units of the player of an effect. A Gaia unit has no tag (units.make_entity): the
    entities with no tag and not the players."""
    at = area_selector(e, T)
    return re.sub(r"tag=aoe2mc\.p-?\d+", "tag=,type=!player", at) if e["player"] <= 0 else at


def sound_lines(e, c):
    """The command of "Play Sound" (#2644): the vanilla sound of the first SOUNDS part in the AoE2 sound name, for all
    players; at the target tile when the effect has one (heard up to 16 blocks), else at each player."""
    T, ground = c.T, c.ground
    name = e.get("sound", "").upper()
    sound = next(s for part, s in SOUNDS if part in name)
    x, z = (int((v + 0.5) * T) for v in e.get("tile", [-1, -1]))
    if min(e.get("tile", [-1])) < 0 or not (0 <= x < ground.shape[0] and 0 <= z < ground.shape[1]):
        return [f"execute as @a at @s run playsound minecraft:{sound} master @s"]
    return [f"playsound minecraft:{sound} master @a {x + 0.5} {int(ground[x, z])} {z + 0.5}"]


def attackable_lines(e, c):
    """The commands of "Disable Unit Attackable" and "Enable Unit Attackable" (#2695): the tag Invulnerable of the
    units of the player in the area. Enable keeps the garrisoned units invulnerable (#807)."""
    if min(e.get("area", [-1])) < 0:
        return []
    disable = e["type"] == DISABLE_UNIT_ATTACKABLE
    guard = "" if disable else f" unless entity @s[tag={GARRISONED}]"
    return [f"execute as {unit_selector(e, c.T)}{guard} run data merge entity @s {{Invulnerable:{int(disable)}b}}"]


def selection_lines(e, c):
    """The command of "Disable Object Selection" and "Enable Object Selection" (#2854): the tag UNSELECTABLE of the
    units of the player in the area. The game program selects no tagged unit (scenario.selection)."""
    if min(e.get("area", [-1])) < 0:
        return []
    return [f"tag {unit_selector(e, c.T)} {'add' if e['type'] == DISABLE_OBJECT_SELECTION else 'remove'} {UNSELECTABLE}"]


def object_visibility_lines(e, c):
    """The commands of "Change Object Visibility" (#2862): the selected units and the units of the player in the area,
    and the mounts of the riders, get the effect invisibility with no particles (the entity tag Invisible is only for
    armor stands), and a shown name tag hides with them. "Explored" hides them too: AoE2 shows no units in the fog.
    "Visible" clears the effect and shows the name tag again. Minecraft cannot hide an entity from one player only:
    all players see the change, whatever the target player."""
    if e.get("visibility") not in (0, 1, 2):
        return []
    sels = [f"@e[tag=aoe2mc.r{r}]" for r in e.get("selected", ())] + \
        [unit_selector(e, c.T)] * (min(e.get("area", [-1])) >= 0)
    c.stats["change object visibility"] += bool(sels)
    if e["visibility"] == 0:
        return [line for at in sels for line in (
            f"execute as {at} on vehicle run effect clear @s minecraft:invisibility",
            f"execute as {at} run effect clear @s minecraft:invisibility",
            f"execute as {at[:-1]},tag={NAME_HIDDEN}] run data merge entity @s {{CustomNameVisible:1b}}",
            f"tag {at[:-1]},tag={NAME_HIDDEN}] remove {NAME_HIDDEN}")]
    return [line for at in sels for line in (
        f"execute as {at} on vehicle run effect give @s minecraft:invisibility infinite 0 true",
        f"execute as {at} run effect give @s minecraft:invisibility infinite 0 true",
        f"tag {at[:-1]},nbt={{CustomNameVisible:1b}}] add {NAME_HIDDEN}",
        f"execute as {at} run data merge entity @s {{CustomNameVisible:0b}}")]


def targeting_lines(e, c):
    """The command of "Disable Unit Targeting" and "Enable Unit Targeting" (#2826): the tag NO_TARGET of the units of
    the player in the area. The game program chooses no tagged unit as a target; an attack order still hits it (AoE2)."""
    if min(e.get("area", [-1])) < 0:
        return []
    return [f"tag {unit_selector(e, c.T)} {'add' if e['type'] == DISABLE_UNIT_TARGETING else 'remove'} {NO_TARGET}"]


def freeze_lines(e, c):
    """The commands of "Freeze Object" (#2608): the units of the player in the area and the mounts of the riders get
    NoAI, so they stay in their place (AoE2: they do not move until a new order)."""
    if min(e.get("area", [-1])) < 0:
        return []
    at = unit_selector(e, c.T)
    return [f"execute as {at} on vehicle run data merge entity @s {{NoAI:1b}}",
            f"execute as {at} run data merge entity @s {{NoAI:1b}}"]


def research_lines(e, c):
    """The command of "Research Technology" (#2577): the score #r<trigger>.<effect index> of aoe_tech is 1. A
    converted world has no technologies: the scenario mode of the game program reads the score (research_list)."""
    if not e.get("technology") or e["player"] <= 0:
        return []
    c.setup["scoreboard objectives add aoe_tech dummy"] = None
    c.stats["research"] += 1
    i = effect_index(e, c)
    return [f"scoreboard players set #r{c.t['id']}.{i} aoe_tech 1"]   # the game program reads it


def cost_lines(e, c, what="change object cost"):
    """The command of "Change Object Cost" (#2776): the new cost of the unit or building type of the player (up to 3
    resources of ATTRIBUTES; a quantity of 0 drops the resource) goes into the list of the data storage aoe2mc:costs as
    one text "<player> <name> <resource>=<quantity> ...". A converted world has no costs: the scenario mode of the game
    program (game/scenario.py costs) empties the list and uses the cost in the menus."""
    cost = [f"{ATTRIBUTES[r].lower()}={q}" for r, q in e.get("cost", ()) if r in range(len(ATTRIBUTES)) and q > 0]
    _, name = e.get("object") or (None, None)
    if not name or name.isdigit() or e["player"] <= 0:
        c.stats[f"{what} (not supported)"] += 1
        return []
    c.stats[what] += 1
    return [f'data modify storage aoe2mc:costs list append value "{" ".join([str(e["player"]), name, *cost])}"']


def tech_cost_lines(e, c):
    """The command of "Change Technology Cost" (#2819): the text of cost_lines with the technology name of
    game/data/train.jsonl (an ID with no name: not supported). civs.cost gives the price to the menu (train.price)."""
    return cost_lines(dict(e, object=(None, e.get("technology"))), c, "change technology cost")


# The ObjectAttribute IDs of "Modify Attribute" that the game program has in combat.Stats (#2763): attribute ->
# the Stats field; armor (8) and attack (9) by their class (3 pierce, 4 melee), as in AoE2.
STAT_ATTRIBUTES = {0: "hp", 10: "reload", 12: "range"}
CLASS_ATTRIBUTES = {(8, 3): "pierce", (8, 4): "melee", (9, 3): "attack", (9, 4): "attack"}


def attribute_lines(e, c):
    """The command of "Modify Attribute" (#2763): the change "<player> <name> <Stats field> <operation> <quantity>"
    goes into the list of the data storage aoe2mc:attributes. A converted world has no combat values: the scenario mode
    of the game program (game/scenario.py attributes) empties the list and changes the values of the unit type of the
    player (train.stats). An attribute outside STAT_ATTRIBUTES and CLASS_ATTRIBUTES: not supported in the stats.
    "Modify Attribute for Class" (#2859): one line for the class, the name "@<ObjectClass name>" (train.applies)."""
    from AoE2ScenarioParser.datasets.trigger_lists import ObjectClass
    _, name = e.get("object") or (None, None)
    if e["type"] == MODIFY_ATTRIBUTE_FOR_CLASS:                        # also the units that the player trains later
        name = f"@{ObjectClass(e['group']).name.lower()}" if e.get("group") in set(ObjectClass) else None
    a = e.get("attribute")
    field = STAT_ATTRIBUTES.get(a) or CLASS_ATTRIBUTES.get((a, e.get("class")))
    q = e.get("aa") if a in (8, 9) else e.get("quantity")
    if not name or e["player"] <= 0 or not field or e.get("operation") not in range(1, 6) or q is None:
        c.stats["modify attribute (not supported)"] += 1
        return []
    c.stats["modify attribute"] += 1
    return [f'data modify storage aoe2mc:attributes list append value "{e["player"]} {name} {field} {e["operation"]} {q:g}"']


def create_lines(e, c):
    """The command of "Create Object Attack" and "Create Object Armor" (#2855): AoE2 gives the unit type of the player
    one more attack (armor) entry of the class, and the entries of one class add up. So the change is an add of the
    value to the Stats field of the class (CLASS_ATTRIBUTES), in the data storage aoe2mc:attributes as "Modify
    Attribute" (attribute_lines): the scenario mode of the game program applies it (train.stats). A class outside
    CLASS_ATTRIBUTES (a bonus class): not supported in the stats."""
    _, name = e.get("object") or (None, None)
    field = CLASS_ATTRIBUTES.get((9 if e["type"] == CREATE_OBJECT_ATTACK else 8, e.get("class")))
    q = e.get("aa")
    if not name or e["player"] <= 0 or not field or q is None or q < 0:
        c.stats["create object attack or armor (not supported)"] += 1
        return []
    c.stats["create object attack or armor"] += 1
    return [f'data modify storage aoe2mc:attributes list append value "{e["player"]} {name} {field} 2 {q:g}"']


def variable_by_attribute_lines(e, c):
    """The command of "Modify Variable by Attribute" (#2858): "<player> <name> <Stats field> <operation> <variable>"
    goes into the list of the data storage aoe2mc:reads. A converted world has no combat values: the scenario mode of
    the game program (game/scenario.py reads) empties the list and changes the score #v<variable> of aoe_var by the
    value of the unit type of the player (train.stats). The attributes: STAT_ATTRIBUTES and CLASS_ATTRIBUTES."""
    _, name = e.get("object") or (None, None)
    a, v = e.get("attribute"), e.get("variable", -1)
    field = STAT_ATTRIBUTES.get(a) or CLASS_ATTRIBUTES.get((a, e.get("class")))
    if not name or e["player"] <= 0 or not field or e.get("operation") not in range(1, 6) or v < 0:
        c.stats["modify variable by attribute (not supported)"] += 1
        return []
    c.stats["modify variable by attribute"] += 1
    return [f'data modify storage aoe2mc:reads list append value "{e["player"]} {name} {field} {e["operation"]} {v}"']


def menu_lines(e, c):
    """The command of "Enable/Disable Object" and "Enable/Disable Technology" (#2775): "<player> <name> on|off" goes
    into the list of the data storage aoe2mc:menus. A converted world has no menus: the scenario mode of the game
    program (game/scenario.py menus) empties the list and shows or hides the item in the menus of the player."""
    _, name = (e.get("object") or (None, None)) if e["type"] == ENABLE_DISABLE_OBJECT else (None, e.get("technology"))
    if not name or e["player"] <= 0 or e.get("enabled") not in (0, 1):
        c.stats["enable/disable (not supported)"] += 1
        return []
    c.stats["enable/disable"] += 1
    return [f'data modify storage aoe2mc:menus list append value "{e["player"]} {name} {"on" if e["enabled"] else "off"}"']


def order_lines(e, c):
    """The commands of "Patrol" and "Attack Move" (#2647). Vanilla has no walk-to command: the units of the player in
    the area get the tag aoe_order<trigger>_<effect index> (tag_lines: a rider gives it to its horse), and the order
    goes into the list of the data storage aoe2mc:orders as one text "<order> <tag> x y z" (the block of the tile on
    the ground; a patrol also the middle of the area, where it turns back). The scenario mode of the game program
    (game/scenario.py orders) empties the list with RCON and walks the tagged units with the Paper plugin."""
    T, ground = c.T, c.ground
    if min(e.get("tile", [-1])) < 0 or min(e.get("area", [-1])) < 0:
        return []
    a = e["area"]
    blocks = [(int((x + 0.5) * T), int((z + 0.5) * T)) for x, z in (e["tile"], ((a[0] + a[2]) / 2, (a[1] + a[3]) / 2))]
    if not all(0 <= x < ground.shape[0] and 0 <= z < ground.shape[1] for x, z in blocks):
        return []
    tag, order = f"aoe_order{c.t['id']}_{effect_index(e, c)}", "patrol" if e["type"] == PATROL else "attack_move"
    where = " ".join(f"{x} {int(ground[x, z])} {z}" for x, z in blocks[:1 + (e["type"] == PATROL)])
    return tag_lines(e, T, tag) + [f'data modify storage aoe2mc:orders list append value "{order} {tag} {where}"']


def stance_lines(e, c):
    """The commands of "Change Object Stance" (#2705). Vanilla has no stance: as order_lines, the units of the player in
    the area get the tag aoe_order<trigger>_<effect index>, and the order "stance <tag> <attack_stance>" (0 aggressive,
    1 defensive, 2 stand ground, 3 no attack) goes into the storage aoe2mc:orders for game/scenario.py orders."""
    if e.get("stance") not in (0, 1, 2, 3):
        return []
    tag = f"aoe_order{c.t['id']}_{effect_index(e, c)}"
    return tag_lines(e, c.T, tag) + [f'data modify storage aoe2mc:orders list append value "stance {tag} {e["stance"]}"']


def range_lines(e, c):
    """The commands of "Change Object Range" (#2767). The range of a unit is a value of the Paper plugin (`aoe range`):
    as stance_lines, the units of the player in the area get the tag aoe_order<trigger>_<effect index>, and the order
    "range <tag> <operation> <quantity>" (1 set, 2 add, 3 subtract, 4 multiply, 5 divide; tiles) goes into the storage
    aoe2mc:orders for game/scenario.py orders."""
    if e.get("operation") not in (1, 2, 3, 4, 5) or (e.get("quantity") or 0) < 0:
        c.stats["change object range (not supported)"] += 1
        return []
    c.stats["change object range"] += 1
    tag, op = f"aoe_order{c.t['id']}_{effect_index(e, c)}", f'{e["operation"]} {e["quantity"]}'
    return tag_lines(e, c.T, tag) + [f'data modify storage aoe2mc:orders list append value "range {tag} {op}"']


def stop_lines(e, c):
    """The commands of "Stop Object" (#2754). Vanilla has no command that ends the walk order of a mob: as order_lines,
    the units of the player in the area get the tag aoe_order<trigger>_<effect index>, and the order "stop <tag>" goes
    into the storage aoe2mc:orders. game/scenario.py orders stops them (`aoe stop`) and ends their patrols."""
    tag = f"aoe_order{c.t['id']}_{effect_index(e, c)}"
    return tag_lines(e, c.T, tag) + [f'data modify storage aoe2mc:orders list append value "stop {tag}"']


def foundation_lines(e, c):
    """The command of "Place Foundation" (#2825): the order "found <player> <building> <x> <y>" (its middle tile) goes
    into the storage aoe2mc:orders. The scenario mode of the game program (game/scenario.py orders) puts the
    construction site there when the place is free. Not a building, no tile or Gaia: no order."""
    kind, name = e.get("object") or (None, None)
    if kind != "B" or e["player"] <= 0 or min(e.get("tile", [-1])) < 0:
        return []
    (x, y), p = e["tile"], e["player"]
    return [f'data modify storage aoe2mc:orders list append value "found {p} {name} {x} {y}"']


def build_lines(e, c):
    """The command of "Build Object" (#2863): the order "build <player> <building> <x1> <y1> <x2> <y2>" goes into the
    storage aoe2mc:orders (ANY: no object type; -1: no area, the whole map). The scenario mode of the game program
    (game/scenario.py finish) completes the construction sites of the player with their middle tile in the area at
    once. The selected objects of the effect are converted buildings, never sites: no order for them. A unit type or
    Gaia: no order."""
    kind, name = e.get("object") or (None, None)
    a = e.get("area", [-1] * 4)
    if kind not in (None, "B") or e["player"] <= 0:
        return []
    x0, y0, x1, y1 = (min(a[0], a[2]), min(a[1], a[3]), max(a[0], a[2]), max(a[1], a[3])) if min(a) >= 0 else [-1] * 4
    p, name = e["player"], name or "ANY"
    return [f'data modify storage aoe2mc:orders list append value "build {p} {name} {x0} {y0} {x1} {y1}"']


def gate_lines(e, c):
    """The commands of "Lock Gate" and "Unlock Gate" (#2762): the order "lock <ref>" or "unlock <ref>" of each selected
    gate goes into the storage aoe2mc:orders. game/scenario.py orders puts the portcullis on the gate and locks it with
    the Paper plugin (`aoe gate lock`): vanilla has no gate that knows its player."""
    order = "lock" if e["type"] == LOCK_GATE else "unlock"
    return [f'data modify storage aoe2mc:orders list append value "{order} {ref}"' for ref in e.get("selected", ())
            if ref >= 0]


def unload_lines(e, c):
    """The commands of "Unload" (#2773): each selected building of the player that takes a garrison (buildings.INSIDE),
    or with no selection each such building with its center in the area, goes into the list of the storage
    aoe2mc:orders as one text "unload <player> <ref>", with the block of the target tile on the ground "x y z" when
    the effect has one. The scenario mode of the game program (game/scenario.py orders) lets the units of the holder
    out and walks them there (aoe moveto). A ship or a ram holder: not supported yet (the game program has no garrison
    of them from a trigger)."""
    T, ground, a = c.T, c.ground, e.get("area", [-1])
    refs = e.get("selected") or ([r for r, (_, _, (x, z)) in sorted(buildings.INSIDE.items())
                                  if a[0] * T <= x < (a[2] + 1) * T and a[1] * T <= z < (a[3] + 1) * T]
                                 if min(a, default=-1) >= 0 else [])
    holders = [r for r in refs if r in buildings.INSIDE]
    if not holders or e["player"] <= 0:
        c.stats["unload (not supported yet)"] += 1
        return []
    c.stats["unload"] += 1
    x, z = (int((v + 0.5) * T) for v in e.get("tile", [-1, -1]))
    where = f" {x} {int(ground[x, z])} {z}" if min(e.get("tile", [-1])) >= 0 and ground is not None and \
        0 <= x < ground.shape[0] and 0 <= z < ground.shape[1] else ""
    p = e["player"]
    return [f'data modify storage aoe2mc:orders list append value "unload {p} {r}{where}"' for r in holders]


def train_lines(e, c):
    """The commands of "Train Unit" and "Initiate Research" (#2772). A converted world has no queues: for each selected
    object the order "train <ref> <unit> <quantity>" or "research <ref> <technology>" goes into the list of the data
    storage aoe2mc:orders. The scenario mode of the game program (game/scenario.py orders) queues it at the building of
    that reference as a click of its menu does: the player pays, as in AoE2."""
    research = e["type"] == INITIATE_RESEARCH
    name = e.get("technology") if research else (e.get("object") or (None, None))[1]
    refs = [r for r in e.get("selected", []) if r >= 0]
    if not name or not refs or e["player"] <= 0:
        c.stats["train or research (not supported)"] += 1
        return []
    c.stats["train or research"] += 1
    order = f"research {{}} {name}" if research else f"train {{}} {name} {max(e.get('quantity', 1), 1)}"
    return [f'data modify storage aoe2mc:orders list append value "{order.format(r)}"' for r in refs]


def view_lines(e, c):
    """The commands of "Change View" (#2610): in Minecraft the player is the camera, so a tp of the players of the
    team pN (team_lines) to the middle of the tile, on the ground. Player -1 or 0: all players."""
    if min(e.get("tile", [-1])) < 0:
        return []
    x, z = (int((v + 0.5) * c.T) for v in e["tile"])
    if not (0 <= x < c.ground.shape[0] and 0 <= z < c.ground.shape[1]):
        return []
    who = f"@a[team=p{e['player']}]" if e["player"] > 0 else "@a"
    return [f"tp {who} {x + 0.5} {int(c.ground[x, z])} {z + 0.5}"]


def mood_lines(e, c):
    """The commands of "Change Color Mood" (#1876): the time of day (MOODS) and the rain (RAIN) of the new mood, as
    at the conversion, only with c.mood. The game rules advance_time and advance_weather are 0, so they stay. The fog
    (FOG) is a timeline of the dimension type: a command cannot change it, so the fog of the map mood stays."""
    if not c.mood or e.get("mood") not in MOODS:
        return []
    return [f"time set {MOODS[e['mood']]}", f"weather {'rain' if e['mood'] in RAIN else 'clear'}"]


def timer_lines(e, c):
    """The commands of "Display Timer" (#2572), and its function file in c.files: the boss bar aoe2mc:timer<slot>
    with the text of the effect, "%d" is the time left in the unit of the effect (TIME_UNITS; m:ss for minutes and
    seconds). The function aoe2mc:timer/<slot> runs each second (schedule): it lowers the score #t<slot> of aoe_timer, the bar and the
    text, and removes the bar at 0. A new timer in the same slot replaces the old one, as in AoE2."""
    unit, slot = e.get("unit", 2), e.get("timer", 0)
    sec, bar, fn = max(int(e["time"] * TIME_UNITS.get(unit, 1)), 1), f"aoe2mc:timer{slot}", f"aoe2mc:timer/{slot}"
    msg = re.sub(r"<[^<>]*>", "", e["message"]).replace("\r", "").strip() or "%d"   # AoE2 color tags
    score = lambda n: {"score": {"name": f"#{n}{slot}", "objective": "aoe_timer"}}  # noqa: E731
    per = TIME_UNITS.get(unit, 1) if unit in (0, 1) else 1
    left = [score("m"), {"text": ":"}, score("z"), score("s")] if unit == 3 else [score("u" if per > 1 else "t")]
    before, _, after = msg.partition("%d")
    name = json.dumps([{"text": before}] + left * ("%d" in msg) + [{"text": after}], ensure_ascii=False)
    show = [f"scoreboard players operation #u{slot} aoe_timer = #t{slot} aoe_timer",
            f"scoreboard players add #u{slot} aoe_timer {per - 1}",           # the years or minutes left, rounded up
            f"scoreboard players set #d{slot} aoe_timer {per}",
            f"scoreboard players operation #u{slot} aoe_timer /= #d{slot} aoe_timer"] if per > 1 else []
    if unit == 3:
        show += [f"scoreboard players set #d{slot} aoe_timer 60",
                 f"scoreboard players operation #m{slot} aoe_timer = #t{slot} aoe_timer",
                 f"scoreboard players operation #m{slot} aoe_timer /= #d{slot} aoe_timer",
                 f"scoreboard players operation #s{slot} aoe_timer = #t{slot} aoe_timer",
                 f"scoreboard players operation #s{slot} aoe_timer %= #d{slot} aoe_timer",
                 f"scoreboard players reset #z{slot} aoe_timer",                # a zero before 0-9 seconds
                 f"execute if score #s{slot} aoe_timer matches ..9 run scoreboard players set #z{slot} aoe_timer 0"]
    show += [f"execute store result bossbar {bar} value run scoreboard players get #t{slot} aoe_timer",
             f"bossbar set {bar} name {name}"]
    tick = [f"scoreboard players remove #t{slot} aoe_timer 1"] + show + \
        [f"execute if score #t{slot} aoe_timer matches ..0 run scoreboard players set #done{slot} aoe_timer 1",
         f"execute if score #t{slot} aoe_timer matches ..0 run bossbar remove {bar}",
         f"execute if score #t{slot} aoe_timer matches 1.. run schedule function {fn} 1s replace"]
    lines = ["scoreboard objectives add aoe_timer dummy", f"scoreboard players reset #done{slot} aoe_timer",
             f"bossbar remove {bar}", f"bossbar add {bar} \"\"",
             f"bossbar set {bar} max {sec}", f"bossbar set {bar} players @a",
             f"scoreboard players set #t{slot} aoe_timer {sec}"] + show + [f"schedule function {fn} 1s replace"]
    c.files[f"data/aoe2mc/function/timer/{slot}.mcfunction"] = "\n".join(tick) + "\n"
    return lines


def clear_timer_lines(e, c):
    """The commands of "Clear Timer" (#2696): the boss bar and the count of the slot of "Display Timer" (timer_lines)
    go away. A slot with no bar makes the bar command fail, which stops the rest of this trigger's function."""
    slot = e.get("timer") or 0
    c.stats["clear timer"] += 1
    return [f"bossbar remove aoe2mc:timer{slot}", f"schedule clear aoe2mc:timer/{slot}"]


def message_text(e):
    """The JSON text of the message of an effect with no AoE2 color tags, or None for no message."""
    msg = re.sub(r"<[^<>]*>", "", e["message"]).replace("\r", "").strip()
    return json.dumps({"text": msg}, ensure_ascii=False) if msg else None


def diplomacy_lines(e, c):
    """The commands of "Change Diplomacy" (#2645): the score #p<player>.p<target> of aoe_dip is the stance + 1 and #any
    of aoe_dip is 1: the scenario mode of the game program changes the stance."""
    a, b = e["player"], e.get("target", -1)
    if e.get("diplomacy") not in STANCES or a <= 0 or b <= 0 or a == b:
        return []
    c.setup["scoreboard objectives add aoe_dip dummy"] = None
    c.stats["change diplomacy"] += 1
    return [f"scoreboard players set #p{a}.p{b} aoe_dip {e['diplomacy'] + 1}", "scoreboard players set #any aoe_dip 1"]


def mirror_lines(e, c):
    """The commands of "Mirror Diplomacy" (#2822): the source player (player) takes the stances of the target player
    toward each other player. The score #m<player>.p<target> of aoe_dip is 1 and #any of aoe_dip is 1: the scenario
    mode of the game program copies the stances (scenario.diplomacy)."""
    a, b = e["player"], e.get("target", -1)
    if a <= 0 or b <= 0 or a == b:
        return []
    c.setup["scoreboard objectives add aoe_dip dummy"] = None
    c.stats["mirror diplomacy"] += 1
    return [f"scoreboard players set #m{a}.p{b} aoe_dip 1", "scoreboard players set #any aoe_dip 1"]


def color_lines(e, c):
    """The command of "Change Player Color" (#2712): the team p<player> gets the chat color of the new player color
    (PlayerColorId 1 to 8, units.TEAM_COLOR). It colors the names and the glow of the units; wool and banners stay."""
    n, color = e["player"], e.get("color")
    if n <= 0 or not isinstance(color, int) or not 1 <= color <= len(buildings.COLOR_NAMES):
        return []
    c.stats["change player color"] += 1
    return [f"team modify p{n} color {units.TEAM_COLOR[buildings.COLOR_NAMES[color - 1]]}"]


def object_color_lines(e, c):
    """The command of "Change Object Player Color" (#2824): the name of each unit of the effect (effect_units) gets the
    hex color of the player color (PlayerColorId 1 to 8, units.HEX: as the names of the converter). The owner and its
    team stay, so the glow keeps the team color: one unit cannot have another team color without another team."""
    color = e.get("color")
    found = effect_units(e, c.T) if isinstance(color, int) and 1 <= color <= len(buildings.COLOR_NAMES) else None
    if found is None:
        c.stats["change object player color (not supported yet)"] += 1
        return []
    c.stats["change object player color"] += 1
    return [f"execute as {found[0]} run data modify entity @s CustomName.color set value "
            f"\"{units.HEX[buildings.COLOR_NAMES[color - 1]]}\""]


def victory_lines(e, c):
    """The command of "Declare Victory" (#2542): the score #p<player> of aoe_win is 1, and the scenario mode of the
    game program ends the game. The load function adds the objective (c.setup)."""
    c.setup["scoreboard objectives add aoe_win dummy"] = None
    c.stats["declare victory"] += 1
    return [f"scoreboard players set #p{max(e['player'], 0)} aoe_win 1"]


def switch_lines(e, c):
    """The commands of "Activate Trigger" and "Deactivate Trigger" (#2575): the score #N of aoe_on of trigger N (in
    c.switch), and the start (c.timed: its ticks) or the clear of its timer. An area trigger can fire again. The
    timers of its "OR" groups (c.clocks: [(group, ticks)], #2815) start and stop the same way."""
    k, up = e.get("trigger"), e["type"] == ACTIVATE_TRIGGER
    if k not in c.switch:
        return []
    fn, clocks = f"aoe2mc:trigger/{k}", c.clocks.get(k, ())
    if up and k in c.timed:                                            # an active timer runs on: AoE2 counts from
        more = [f"execute unless score #{k} aoe_on matches 1 run schedule function {fn} {c.timed[k]}t replace"]   # now
    else:
        more = [f"scoreboard players reset #{k} aoe_trig"] if up else [f"schedule clear {fn}"] * (k in c.timed)
    for g, ticks in clocks:
        more += [f"execute unless score #{k} aoe_on matches 1 run {x}" for x in (
            f"scoreboard players reset #{k}.t{g} aoe_trig", f"schedule function {fn}_t{g} {ticks}t replace")] if up \
            else [f"schedule clear {fn}_t{g}"]
    return more + [f"scoreboard players set #{k} aoe_on {int(up)}"]


def clear_lines(e, c):
    """The command of "Clear Instructions" (#2609): no message, the shown instructions go."""
    return ["title @a clear"]


def chat_lines(e, c):
    """The command of "Send Chat": a tellraw to all players."""
    return [f"tellraw @a {text}"] if (text := message_text(e)) else []


def instruction_lines(e, c):
    """The commands of "Display Instructions": a subtitle for the display time of the effect (AoE2 default: 10 s)."""
    if not (text := message_text(e)):
        return []
    ticks = 20 * (e["time"] if e["time"] > 0 else 10)
    return [f"title @a times 10 {ticks} 20", f"title @a subtitle {text}", 'title @a title ""']


def visibility_lines(e, c):
    """The commands of "Set Player Visibility" (#2774): the score #p<player>.p<target> of aoe_vis is the state + 1
    (VisibilityState: 0 visible, 1 explored, 2 invisible) and #any of aoe_vis is 1: the scenario mode of the game
    program shows the units of the target to the player out of sight, or hides them again."""
    a, b = e["player"], e.get("target", -1)
    if e.get("visibility") not in (0, 1, 2) or a <= 0 or b <= 0 or a == b:
        return []
    c.setup["scoreboard objectives add aoe_vis dummy"] = None
    c.stats["set player visibility"] += 1
    return [f"scoreboard players set #p{a}.p{b} aoe_vis {e['visibility'] + 1}", "scoreboard players set #any aoe_vis 1"]


# The keys of the effect dict of read_scenario beyond the common ones: key -> attribute of the scenario effect, or
# (effect, kinds, techs) -> value. A new effect is one line here, in alphabetical order (#2792): parallel trigger
# tickets conflicted in one expression of read_scenario. The older effects still have their entry there.
EFFECT_KEYS = {
    CHANGE_TECHNOLOGY_LOCATION: {"button": "button_location", "object2": lambda e, kinds, techs: kinds.get(   # #2864
        e.object_list_unit_id_2), "technology": lambda e, kinds, techs: techs.get(e.technology, str(e.technology))},
    CHANGE_TRAIN_LOCATION: {"button": "button_location",                                                       # #2864
                            "object2": lambda e, kinds, techs: kinds.get(e.object_list_unit_id_2)},
    COUNT_UNITS_INTO_VARIABLE: {"variable2": "variable2"},   # (#2697)
    CREATE_OBJECT_ARMOR: {"class": "armour_attack_class", "aa": "armour_attack_quantity"},   # (#2855)
    CREATE_OBJECT_ATTACK: {"class": "armour_attack_class", "aa": "armour_attack_quantity"},  # (#2855)
    INITIATE_RESEARCH: {"selected": lambda e, kinds, techs: list(e.selected_object_ids or []),   # (#2772)
                        "technology": lambda e, kinds, techs: techs.get(e.technology, str(e.technology))},
    MODIFY_ATTRIBUTE_FOR_CLASS: {"attribute": "object_attributes", "operation": "operation", "quantity": "quantity",
                                 "class": "armour_attack_class", "aa": "armour_attack_quantity", "group": "object_group2"},
    MODIFY_VARIABLE_BY_ATTRIBUTE: {"attribute": "object_attributes", "class": "armour_attack_class",   # (#2858)
                                   "operation": "operation", "variable": "variable"},
    TRAIN_UNIT: {"quantity": "quantity", "selected": lambda e, kinds, techs: list(e.selected_object_ids or [])},   # (#2772)
}


# The handler of each trigger effect: (effect, Effect context) -> commands. A new effect is one line here, in
# alphabetical order, and its handler function (#2613): no change of trigger_files.
EFFECTS = {
    ACTIVATE_TRIGGER: switch_lines,
    ATTACK_MOVE: order_lines,
    BUILD_OBJECT: build_lines,
    CHANGE_COLOR_MOOD: mood_lines,
    CHANGE_DIPLOMACY: diplomacy_lines,
    CHANGE_OBJECT_ARMOR: attack_lines,
    CHANGE_OBJECT_ATTACK: attack_lines,
    CHANGE_OBJECT_COST: cost_lines,
    CHANGE_OBJECT_HP: hp_lines,
    CHANGE_OBJECT_NAME: name_lines,
    CHANGE_OBJECT_PLAYER_COLOR: object_color_lines,
    CHANGE_OBJECT_RANGE: range_lines,
    CHANGE_OBJECT_SPEED: speed_lines,
    CHANGE_OBJECT_STANCE: stance_lines,
    CHANGE_OBJECT_VISIBILITY: object_visibility_lines,
    CHANGE_OWNERSHIP: owner_lines,
    CHANGE_PLAYER_COLOR: color_lines,
    CHANGE_PLAYER_NAME: player_name_lines,
    CHANGE_TECHNOLOGY_COST: tech_cost_lines,
    CHANGE_TECHNOLOGY_LOCATION: location_lines,
    CHANGE_TECHNOLOGY_NAME: tech_name_lines,
    CHANGE_TRAIN_LOCATION: location_lines,
    CHANGE_VARIABLE: variable_lines,
    CHANGE_VIEW: view_lines,
    CLEAR_INSTRUCTIONS: clear_lines,
    CLEAR_TIMER: clear_timer_lines,
    COUNT_UNITS_INTO_VARIABLE: count_lines,
    CREATE_GARRISONED_OBJECT: garrisoned_lines,
    CREATE_OBJECT: object_lines,
    CREATE_OBJECT_ARMOR: create_lines,
    CREATE_OBJECT_ATTACK: create_lines,
    DAMAGE_OBJECT: damage_lines,
    DEACTIVATE_TRIGGER: switch_lines,
    DECLARE_VICTORY: victory_lines,
    DISABLE_OBJECT_SELECTION: selection_lines,
    DISABLE_UNIT_ATTACKABLE: attackable_lines,
    DISABLE_UNIT_TARGETING: targeting_lines,
    DISPLAY_INSTRUCTIONS: instruction_lines,
    DISPLAY_TIMER: timer_lines,
    ENABLE_DISABLE_OBJECT: menu_lines,
    ENABLE_DISABLE_TECHNOLOGY: menu_lines,
    ENABLE_OBJECT_SELECTION: selection_lines,
    ENABLE_UNIT_ATTACKABLE: attackable_lines,
    ENABLE_UNIT_TARGETING: targeting_lines,
    FREEZE_OBJECT: freeze_lines,
    HEAL_OBJECT: heal_lines,
    INITIATE_RESEARCH: train_lines,
    KILL_OBJECT: object_lines,
    LOCK_GATE: gate_lines,
    MIRROR_DIPLOMACY: mirror_lines,
    MODIFY_ATTRIBUTE: attribute_lines,
    MODIFY_ATTRIBUTE_FOR_CLASS: attribute_lines,
    MODIFY_RESOURCE: resource_lines,
    MODIFY_RESOURCE_BY_VARIABLE: resource_by_variable_lines,
    MODIFY_VARIABLE_BY_ATTRIBUTE: variable_by_attribute_lines,
    MODIFY_VARIABLE_BY_RESOURCE: variable_by_resource_lines,
    MODIFY_VARIABLE_BY_VARIABLE: variable_by_variable_lines,
    PATROL: order_lines,
    PLACE_FOUNDATION: foundation_lines,
    PLAY_SOUND: sound_lines,
    REMOVE_OBJECT: object_lines,
    REPLACE_OBJECT: replace_lines,
    RESEARCH_TECHNOLOGY: research_lines,
    SEND_CHAT: chat_lines,
    SET_PLAYER_VISIBILITY: visibility_lines,
    STOP_OBJECT: stop_lines,
    TASK_OBJECT: task_lines,
    TELEPORT_OBJECT: teleport_lines,
    TRAIN_UNIT: train_lines,
    TRIBUTE: resource_lines,
    UNLOAD: unload_lines,
    UNLOCK_GATE: gate_lines,
}
# The context of the effects of trigger t: a handler can add function files (files) and load lines (setup, the keys)
Effect = namedtuple("Effect", "t T ground players stats mood files setup switch timed clocks", defaults=((), {}, {}))


# The test of each condition on a score (execute if <test>), one line per condition in alphabetical order (#2613):
# "Difficulty Level" (#2704): the score #level of aoe_difficulty is the AoE2 value of the difficulty of the game
# (scenario.setup); "Research Technology" (#2656): the game program sets #p<player>.<technology> of aoe_tech;
# "Researching Technology" and "Technology State" (#2769): the game program sets #p<player>.<technology> of
# aoe_techstate to the AoE2 TechnologyState (2: researching); "Compare Variables" (#2698): two scores of aoe_var;
# "Variable Value" (#2611): the score #v<N> of aoe_var. A world with no game program has no score: no fire.
SCORE_TESTS = {
    ACCUMULATE_ATTRIBUTE: resource_score,
    COMPARE_VARIABLES: compare_test,
    DIFFICULTY_LEVEL: lambda c: f"score #level aoe_difficulty matches {c.get('quantity', 0)}",
    DIPLOMACY_STATE: lambda c: f"score #p{c['player']}.p{c['target']} aoe_dipstate matches {c['diplomacy'] + 1}",
    DISPLAY_TIMER_TRIGGERED: lambda c: f"score #done{c.get('slot', 0)} aoe_timer matches 1..",   # set at 0 (#2702)
    OBJECT_HAS_ACTION: lambda c: f"score #r{c['ref']} aoe_action matches {c['action']}",   # inverted: unless
    OBJECT_NOT_VISIBLE: lambda c: f"score #r{c['ref']}.p{c['player']} aoe_seen matches 0",
    OBJECT_VISIBLE: lambda c: f"score #r{c['ref']}.p{c['player']} aoe_seen matches 1",
    OBJECT_VISIBLE_MULTIPLAYER: lambda c: f"score #r{c['ref']}.p{c['player']} aoe_seen matches 1",
    PLAYER_DEFEATED: lambda c: f"score #p{c['player']} aoe_lost matches 1..",   # conquest, regicide (#2710)
    RESEARCHED: lambda c: f"score #p{c['player']}.{c['technology']} aoe_tech matches 1..",
    RESEARCHING_TECH: lambda c: f"score #p{c['player']}.{c['technology']} aoe_techstate matches 2",
    TECHNOLOGY_STATE: lambda c: f"score #p{c['player']}.{c['technology']} aoe_techstate matches {c.get('quantity', 0)}",
    TRIGGER_ACTIVE: lambda c: f"score #{c['trigger']} aoe_on matches {int(not c['inverted'])}",   # #2699
    UNITS_GARRISONED: lambda c: f"score #g{c['unit']} aoe_gar matches {max(c['quantity'], 1)}..",   # #2714
    VARIABLE_VALUE: lambda c: f"score #v{c['variable']} aoe_var matches {variable_range(c)}",
}


def in_order(items, order):
    """The conditions of a trigger in their display order (AoE2ScenarioParser condition_order): "OR" splits the list
    there (#2765). An order that is not a permutation of the items: the stored order."""
    return [items[k] for k in order] if sorted(order) == list(range(len(items))) else list(items)


def or_groups(conds):
    """The conditions of a trigger in groups (#2765): "OR" splits the list, and the trigger fires when all conditions
    of one group hold, as in AoE2 DE. "AND" is the default between two conditions. An empty group does not count."""
    groups = [[]]
    for c in conds:
        if c["type"] == OR:
            groups.append([])
        elif c["type"] != AND:
            groups[-1].append(c)
    return [g for g in groups if g]


def trigger_files(triggers, T=4, ground=None, players=None, stats=None, mood=True, live=None):
    """(load lines, files) for the triggers that only have timer conditions (#648) or only "Objects in Area",
    "Own Objects" and "Own Fewer Objects" conditions (#649, #2573): one function per trigger. "Own Objects" counts the
    units of the player on the whole map (Q or more), "Own Fewer Objects" Q or fewer; buildings are blocks with no
    entity, so they do not count. The load function schedules a timer trigger at the AoE2 time (all
    timers must pass: the largest). The tick function runs an area trigger when units of its player are in all its
    areas; the score #N of aoe_trig marks a fired trigger, so it fires once. A looping area trigger fires again after
    the units leave an area. A "Variable Value" condition runs in the tick function as an area (#2611), a "Research
    Technology" condition too: the game program sets the score #p<player>.<technology> of aoe_tech (#2656), and an
    "Accumulate Attribute" condition of a resource: resource_score (#2655), an "Object (Not) Visible" condition: the
    game program sets the score #r<ref>.p<player> of aoe_seen (#2756). A "Destroy Object" condition
    (OBJECT_TESTS) tests the tag aoe2mc.r<ref> of its unit and its marker (#2618), "Bring Object to Area" the tag in
    the box of the area (#2620), "Bring Object to Object" the other tag within one tile of it (#2771). An inverted
    object condition swaps the two tests of OBJECT_TESTS. "OR" splits the conditions into groups (or_groups, #2765):
    one tick line per group, and the trigger fires when one group holds; the timer of a group sets the score
    #N.t<group> of aoe_trig (#2791), the "Chance" of a group rolls the score #N.c<group> once per second (#2815).
    The commands of each effect come from its handler in EFFECTS.
    A disabled trigger runs only after an "Activate Trigger" (#2575): the score #N of aoe_on is 1 while a trigger that
    such an effect names is on (switch_lines). live: the triggers that get a function; None: all that give commands
    (an effect may name only a function that exists). A "Chance" trigger cannot be activated yet."""
    if live is None:
        live = {t["id"] for t in triggers}
        while any(e["type"] in (ACTIVATE_TRIGGER, DEACTIVATE_TRIGGER) for t in triggers for e in t["effects"]) and \
                live != (made := {int(k.split("/")[-1].split(".")[0]) for k in
                                trigger_files(triggers, T, ground, players, Counter(), mood, live)[1]
                                if re.fullmatch(r"data/aoe2mc/function/trigger/\d+\.mcfunction", k)}):
            live = made
    load, files, tick, setup = [], {}, [], {}
    stats = Counter() if stats is None else stats
    ground = np.zeros((0, 0), np.int16) if ground is None else ground
    chancy = {t["id"] for t in triggers if any(c["type"] == TRIGGER_CHANCE for c in t["conditions"])}
    on = {e.get("trigger") for t in triggers for e in t["effects"] if e["type"] == ACTIVATE_TRIGGER}
    active = [c for t in triggers for c in t["conditions"] if c["type"] == TRIGGER_ACTIVE]   # the state score (#2699)
    switch = ({e.get("trigger") for t in triggers for e in t["effects"]
               if e["type"] in (ACTIVATE_TRIGGER, DEACTIVATE_TRIGGER)} | {c.get("trigger") for c in active}) & live - chancy
    off = {c.get("trigger") for c in active if c["inverted"]} & switch   # an inverted test needs the score at 0
    load += [f"scoreboard players set #{t['id']} aoe_on 0" for t in triggers if t["id"] in off and not t["enabled"]]
    timed = {t["id"]: max(20 * min(max(c["timer"] for c in g) for g in gs), 1) for t in triggers   # 1 tick at least;
             if (gs := or_groups(t["conditions"])) and all(c["type"] == TIMER for g in gs for c in g)}   # OR: the first
    clocks = {t["id"]: ts for t in triggers if t["id"] not in timed and len(gs := or_groups(t["conditions"])) > 1
              and (ts := [(k, max(20 * max(x), 1)) for k, g in enumerate(gs)
                          if (x := [c["timer"] for c in g if c["type"] == TIMER])])}   # the OR timers (#2815)
    for t in triggers:
        groups = or_groups(t["conditions"])
        conds = sum(groups, [])
        which = [k for k, g in enumerate(groups) for _ in g]           # the group of each condition
        kinds = {(c["type"], c["inverted"]) for c in conds}
        # "Chance" (alone, after the timers or with the ticked conditions, #2574): a roll function checks the trigger
        # once per second, as AoE2 does, with `random value 1..100`
        chance = (TRIGGER_CHANCE, False) in kinds
        rest = kinds - {(TRIGGER_CHANCE, False)}
        if any(c["type"] in OBJECT_TESTS and (c.get("ref", -1) is None or c.get("ref", -1) < 0 or not c.get("unit"))
               or c["type"] == BRING_OBJECT_TO_OBJECT and (c.get("next") is None or c["next"] < 0 or not c.get("next_unit"))
               for c in conds):                                        # no object, or a building: blocks, no entity
            stats["object condition (not an entity, not supported yet)"] += t["enabled"]
            continue
        # "OR" with a timer and other conditions (#2791) or a chance (#2815): the timer of a group is a schedule that
        # sets the score #N.t<group> of aoe_trig, its chance a roll of the score #N.c<group>; the tick line of the
        # group tests them
        rolled = len(groups) > 1 and chance
        clocked = len(groups) > 1 and (TIMER, False) in rest and (rest != {(TIMER, False)} or rolled)
        if not (t["enabled"] or t["id"] in on and t["id"] not in chancy) or not conds or \
                not (rest == {(TIMER, False)} or rest <= {(k, False) for k in TICKED + (TIMER,) * clocked} | {(k, True) for k in INVERTED}) or \
                chance and len([c for c in conds if c["type"] == TRIGGER_CHANCE]) > 1 or \
                any(c.get("group", -1) >= 0 or c.get("class", -1) >= 0 for c in conds) or \
                any(c["type"] == VARIABLE_VALUE and (c.get("variable", -1) < 0 or variable_range(c) is None)
                    or c["type"] in (RESEARCHED, RESEARCHING_TECH, TECHNOLOGY_STATE)
                    and (c.get("player", -1) <= 0 or not c.get("technology"))
                    or c["type"] == ACCUMULATE_ATTRIBUTE and resource_score(c) is None
                    or c["type"] == COMPARE_VARIABLES and compare_test(c) is None
                    or c["type"] == OBJECT_HP and (c.get("ref", -1) < 0 or variable_range(c) is None)
                    or c["type"] == UNITS_GARRISONED and c.get("unit", -1) < 0
                    or c["type"] == OBJECT_HAS_ACTION and (c.get("ref", -1) < 0 or c.get("next", -1) >= 0
                                                           or c.get("action") not in OBJECT_ACTIONS)
                    or c["type"] in VISIBLE and (c.get("ref") is None or c["ref"] < 0 or c.get("player", -1) <= 0)
                    or c["type"] == PLAYER_DEFEATED and c.get("player", -1) <= 0   # Gaia: no defeat (#2710)
                    or c["type"] == TRIGGER_ACTIVE and c.get("trigger") not in switch
                    for c in conds):                                   # unit classes: not yet
            continue
        ctx = Effect(t, T, ground, players, stats, mood, files, setup, switch, timed, clocks)
        lines = [line for e in t["effects"] if e["type"] in EFFECTS for line in EFFECTS[e["type"]](e, ctx)]
        if not lines:
            continue
        fn, n = f"aoe2mc:trigger/{t['id']}", t["id"]
        if n in switch:
            load += [f"scoreboard players set #{n} aoe_on 1"] * t["enabled"]
            lines += [f"scoreboard players set #{n} aoe_on 0"] * (not t["looping"])   # it fired: off until activated
        groups_tests, groups_unless, counts = [[] for _ in groups], [[] for _ in groups], []
        for k, g in enumerate(groups) if clocked else ():
            if not (timers := [c["timer"] for c in g if c["type"] == TIMER]):
                continue
            clock, at = f"#{n}.t{k} aoe_trig", f"schedule function {fn}_t{k} {max(20 * max(timers), 1)}t replace"
            files[f"data/aoe2mc/function/trigger/{n}_t{k}.mcfunction"] = f"scoreboard players set {clock} 1\n"
            load += [at] * t["enabled"]                                # a disabled one: at its activation
            lines += [f"scoreboard players reset {clock}", at] * t["looping"]   # the timer starts again
            groups_tests[k].append(f"if score {clock} matches 1")
            groups_unless[k].append(f"unless score {clock} matches 1")
        for k, g in enumerate(groups) if rolled else ():
            if not (qs := [c["quantity"] for c in g if c["type"] == TRIGGER_CHANCE]):
                continue
            roll, again = f"#{n}.c{k} aoe_trig", f"schedule function {fn}_c{k} 20t replace"   # once per second
            files[f"data/aoe2mc/function/trigger/{n}_c{k}.mcfunction"] = "\n".join(
                [f"execute store result score {roll} run random value 1..100",
                 again if t["looping"] else f"execute unless score #{n} aoe_trig matches 1 run {again}"]) + "\n"
            load.append(again)
            groups_tests[k].append(f"if score {roll} matches ..{qs[0]}")
            groups_unless[k].append(f"unless score {roll} matches ..{qs[0]}")
        for i, c in enumerate(conds):
            tests, unless = groups_tests[which[i]], groups_unless[which[i]]
            if c["type"] in SCORE_TESTS:                               # a score of the world or the game
                test = SCORE_TESTS[c["type"]](c)
                no = c["type"] == COMPARE_VARIABLES and compare_negated(c) or \
                    c["type"] == OBJECT_HAS_ACTION and c["inverted"]   # "not equal" or "inverted": unless
                tests.append(f"{'unless' if no else 'if'} {test}")
                unless.append(f"{'if' if no else 'unless'} {test}")
                continue
            if c["type"] in OBJECT_TESTS:                              # the tag of the object (#2618)
                test, other, before = OBJECT_TESTS[c["type"]]
                at = dict(ref=c["ref"], player=c.get("player"), box=area_box(c.get("area", [-1] * 4), T), next=c.get("next"),
                          near=T)
                if c["inverted"]:                                      # the condition holds while the test fails
                    test, other = other, test
                counts += [x.format(**at) for x in before]
                tests.append(test.format(**at))
                unless.append(other.format(**at))
                continue
            if c["type"] == OBJECT_HP:                                 # the Health of the object (tag aoe2mc.r<ref>): none when dead
                tag = f"aoe2mc.r{c['ref']}"
                counts += [f"scoreboard players reset #{n}.{i} aoe_trig",
                           f"execute if entity @e[tag={tag},limit=1] store result score #{n}.{i} aoe_trig "
                           f"run data get entity @e[tag={tag},limit=1] Health"]
                tests.append(f"if score #{n}.{i} aoe_trig matches {variable_range(c)}")
                unless.append(f"unless score #{n}.{i} aoe_trig matches {variable_range(c)}")
            if c["type"] not in COUNTED:                               # a timer or the chance
                continue
            whole = c["type"] != IN_AREA                               # Own (Fewer) Objects: the whole map
            sel = area_selector(dict(c, area=[-1] * 4) if whole else c, T)
            q = max(c["quantity"], 0 if c["type"] == OWN_FEWER_OBJECTS else 1)
            if c["type"] == OWN_FEWER_OBJECTS:                         # count the units: q or fewer
                counts.append(f"execute store result score #{n}.{i} aoe_trig if entity {sel}")
                tests.append(f"if score #{n}.{i} aoe_trig matches ..{q}")
                unless.append(f"unless score #{n}.{i} aoe_trig matches ..{q}")
            elif q == 1:
                tests.append(f"if entity {sel}")
                unless.append(f"unless entity {sel}")
            else:                                                      # count the units: q or more
                counts.append(f"execute store result score #{n}.{i} aoe_trig if entity {sel}")
                tests.append(f"if score #{n}.{i} aoe_trig matches {q}..")
                unless.append(f"unless score #{n}.{i} aoe_trig matches {q}..")
        ticked = any(groups_tests)
        for tests in groups_tests:
            tests[:0] = [f"if score #{n} aoe_on matches 1"] * (ticked and n in switch)
        tests, unless = groups_tests[0], groups_unless[0]
        resets = [f"execute {u} run scoreboard players reset #{n} aoe_trig" for u in unless] * t["looping"]
        if len(groups) > 1 and t["looping"]:                           # "OR": it fires again after no group holds
            resets = [f"scoreboard players set #{n}.or aoe_trig 0"] + \
                [f"execute {' '.join(g)} run scoreboard players set #{n}.or aoe_trig 1" for g in groups_tests] + \
                [f"execute if score #{n}.or aoe_trig matches 0 run scoreboard players reset #{n} aoe_trig"]
        timers = [c["timer"] for c in conds if c["type"] == TIMER]
        ticks = timed.get(n) or max(20 * max(timers, default=0), 1)  # a schedule needs at least 1 tick
        if chance and not rolled:
            q = next(c["quantity"] for c in conds if c["type"] == TRIGGER_CHANCE)
            roll = f"{fn}_chance"
            again = f"schedule function {roll} 20t replace"
            lines += [f"schedule function {roll} {ticks}t replace"] if t["looping"] and timers else []
            lines += [] if t["looping"] and not ticked else [f"scoreboard players set #{n} aoe_trig 1"]
            files[f"data/aoe2mc/function/trigger/{n}_chance.mcfunction"] = "\n".join(
                [f"execute store result score #{n}.c aoe_trig run random value 1..100",
                 again if t["looping"] and ticked else f"execute unless score #{n} aoe_trig matches 1 run {again}"]
                + counts + [f"execute {' '.join(tests + [f'if score #{n}.c aoe_trig matches ..{q}'])} "
                            f"unless score #{n} aoe_trig matches 1 run function {fn}"]) + "\n"
            files[f"data/aoe2mc/function/trigger/{n}.mcfunction"] = "\n".join(lines) + "\n"
            load.append(f"schedule function {roll} {ticks if timers else 20}t replace")
            tick += counts + resets if resets else []
            continue
        if ticked:                                                     # one line per group: the score fires it once
            tick += counts + [f"execute {' '.join(g)} unless score #{n} aoe_trig matches 1 run function {fn}"
                              for g in groups_tests] + resets
            lines.append(f"scoreboard players set #{n} aoe_trig 1")
            files[f"data/aoe2mc/function/trigger/{n}.mcfunction"] = "\n".join(lines) + "\n"
            continue
        run = f"schedule function {fn} {ticks}t replace"
        files[f"data/aoe2mc/function/trigger/{n}.mcfunction"] = "\n".join(lines + [run] * t["looping"]) + "\n"
        load += [run] * t["enabled"]
    names = sorted({f"#v{x[k]}" for t in triggers for x in t["conditions"] + t["effects"]
                    for k in ("variable", "variable2")   # "Modify Variable by Variable" has two (#2713)
                    if x["type"] in (VARIABLE_VALUE, CHANGE_VARIABLE, COMPARE_VARIABLES, COUNT_UNITS_INTO_VARIABLE,
                                     MODIFY_VARIABLE_BY_ATTRIBUTE,
                                     MODIFY_VARIABLE_BY_RESOURCE, MODIFY_VARIABLE_BY_VARIABLE) and x.get(k, -1) >= 0})
    if names:
        load[:0] = ["scoreboard objectives add aoe_var dummy"] + \
            [f"scoreboard players add {v} aoe_var 0" for v in names]   # AoE2 variables start at 0
    for word in ("aoe_action", "aoe_difficulty", "aoe_gar", "aoe_lost", "aoe_seen", "aoe_tech", "aoe_techstate"):  # the game program
        if any(f" {word} " in x for x in tick):
            setup[f"scoreboard objectives add {word} dummy"] = None
    if switch:
        setup["scoreboard objectives add aoe_on dummy"] = None
    load[:0] = setup
    if tick or any(k.endswith("_chance.mcfunction") for k in files):
        load.insert(0, "scoreboard objectives add aoe_trig dummy")
    if tick:
        files["data/minecraft/tags/function/tick.json"] = {"values": ["aoe2mc:tick"]}
        files["data/aoe2mc/function/tick.mcfunction"] = "\n".join(tick) + "\n"
    return load, files


def action_list(triggers):
    """The refs of the units of the "Object Has Action" conditions that the tick function of trigger_files tests, for
    aoe2mc.json "actions" (#2867): the scenario mode of the game program sets their score of aoe_action."""
    tick = trigger_files(triggers)[1].get("data/aoe2mc/function/tick.mcfunction", "")
    return sorted({int(r) for r in re.findall(r"#r(\d+) aoe_action ", tick)})


def research_list(triggers):
    """The "Research Technology" effects that trigger_files writes, for aoe2mc.json "research" (#2577): the score of
    the effect in aoe_tech (1: the trigger fired), its player and its technology (a name of game/data/train.jsonl). A
    converted world has no technologies: the scenario mode of the game program gives them (game/scenario.py)."""
    found = "".join(trigger_files(triggers)[1].get(f"data/aoe2mc/function/trigger/{t['id']}.mcfunction", "")
                    for t in triggers)
    return [dict(score=f"#r{t['id']}.{i}", player=e["player"], technology=e["technology"])
            for t in triggers for i, e in enumerate(t["effects"]) if f"#r{t['id']}.{i} aoe_tech 1" in found]


def tech_state_list(triggers):
    """The [player, technology] pairs of the "Researching Technology" and "Technology State" conditions that the tick
    function of trigger_files tests, for aoe2mc.json "tech_states" (#2769): the scenario mode of the game program sets
    their score of aoe_techstate (game/scenario.py)."""
    tick = trigger_files(triggers)[1].get("data/aoe2mc/function/tick.mcfunction", "")
    return sorted({(int(n), t) for n, t in re.findall(r"#p(\d+)\.(\w+) aoe_techstate ", tick)})


def visible_list(triggers):
    """The [ref, player] pairs of the "Object (Not) Visible" conditions that trigger_files writes, for aoe2mc.json
    "visible" (#2756): the scenario mode of the game program sets the score #r<ref>.p<player> of aoe_seen."""
    tick = trigger_files(triggers)[1].get("data/aoe2mc/function/tick.mcfunction", "")
    return sorted({(int(r), int(p)) for r, p in re.findall(r"#r(\d+)\.p(\d+) aoe_seen", tick)})


# The lists of aoe2mc.json that the scenario mode of the game program reads: key -> function of the triggers. A new
# list is one line here, in alphabetical order (#2832): no new keyword of write_objects.
TRIGGER_LISTS = {
    "actions": action_list,                                     # the units of aoe_action (#2867)
    "research": research_list,                                  # the "Research Technology" effects (#2577)
    "tech_states": tech_state_list,                             # the [player, technology] pairs of aoe_techstate (#2769)
    "visible": visible_list,                                    # the [ref, player] pairs of aoe_seen (#2756)
}


# The map of the world goes into the off-hand of each player once, through the tag aoe2mc_map (#966).
MAP_PULSE = ["execute as @a[tag=!aoe2mc_map] run item replace entity @s weapon.offhand with "
             "minecraft:filled_map[minecraft:map_id=0]",
             "tag @a[tag=!aoe2mc_map] add aoe2mc_map"]


# The resource pack of --resource-pack (#2738): human textures for the zombie units. Boxes (u, v, w, h, d, part) of
# the 64 x 64 entity models (a box puts its six faces at u, v); the left limbs mirror the right ones.
SKIN_BOXES = {
    "zombie": [(0, 0, 8, 8, 8, "head"), (16, 16, 8, 12, 4, "shirt"), (40, 16, 4, 12, 4, "arm"), (0, 16, 4, 12, 4, "leg")],
    "villager": [(0, 0, 8, 10, 8, "head"), (24, 0, 2, 4, 2, "skin"), (16, 20, 8, 12, 6, "shirt"),
                 (44, 22, 4, 12, 4, "arm"), (0, 22, 4, 12, 4, "leg")],
    # the skeleton model (64 x 32, #2752): thin arms and legs; a pack cannot change the shape
    "skeleton": [(0, 0, 8, 8, 8, "head"), (16, 16, 8, 12, 4, "shirt"), (40, 16, 2, 12, 2, "arm"), (0, 16, 2, 12, 2, "leg")],
    # the ravager of the war elephants (#2745, RavagerModel of 26.3): the horns are the tusks, the nose the trunk
    "ravager": [(0, 0, 16, 20, 16, "head"), (0, 0, 4, 8, 4, "trunk"), (68, 73, 10, 10, 18, "hide"),
                (74, 55, 2, 14, 4, "tusk"), (0, 36, 16, 3, 16, "hide"), (0, 55, 14, 16, 20, "hide"),
                (0, 91, 12, 13, 18, "hide"), (64, 0, 8, 37, 8, "foot"), (96, 0, 8, 37, 8, "foot")],
}
# the drowned model has its own left arm and leg in the lower half (#2752)
SKIN_BOXES["drowned"] = SKIN_BOXES["zombie"] + [(32, 48, 4, 12, 4, "arm"), (16, 48, 4, 12, 4, "leg")]
SKIN_SIZE = {"skeleton": (64, 32)}                                     # the others: 64 x 64
SKINS = {   # texture -> (model, skin color); the hair, clothes and face colors are the same for all
    "entity/horse/horse_skeleton.png": ("horse", (112, 74, 44)),      # the cavalry archer horses (#2752)
    "entity/skeleton/skeleton.png": ("skeleton", (220, 170, 128)),    # the archers (#2752)
    "entity/zombie/drowned.png": ("drowned", (204, 150, 108)),        # the skirmishers (#2752)
    "entity/zombie/drowned_outer_layer.png": ("none", None),          # no seaweed over the clothes
    "entity/zombie/husk.png": ("zombie", (196, 140, 98)),
    "entity/zombie/zombie.png": ("zombie", (226, 176, 136)),
    "entity/zombie_villager/zombie_villager.png": ("villager", (214, 160, 120)),
    "entity/illager/ravager.png": ("ravager", (128, 124, 120)),     # elephant grey (no natural ravagers in a world)
}
HORSE_EYES = ((3, 21), (16, 21))                                       # the eyes of the 26.3 horse texture
# The cart of the War Wagon in the pack (#2746, the AoE2 model: a box wagon with plank walls, an iron rim, a plank roof
# and two large wheels): boxes (from, to) in pixels of a block at scale 1, 16 = 1 block, the ground at y 0, the horse
# at -z; vanilla block textures, the wheels have the rings of a log top on their sides. cart_model() scales them.
CART_BOXES = [((-2, 6, -8), (18, 8, 24), "smooth_stone"),                     # the iron rim of the floor
              ((-1, 8, -7), (17, 27, 23), "dark_oak_log"),                     # the walls of vertical planks
              ((-1.5, 17, -7.5), (17.5, 18, 23.5), "iron_block"),              # the band
              ((-1.5, 20, 3), (17.5, 24, 11), "black_concrete"),               # the windows
              ((-3, 27, -9), (19, 29, 25), "smooth_stone"),                    # the iron rim of the roof
              ((-2, 29, -8), (18, 30, 24), "oak_planks"),                      # the roof
              ((-4, 0, 8), (-2, 16, 24), "dark_oak_planks", "spruce_log_top"),   # the wheels
              ((18, 0, 8), (20, 16, 24), "dark_oak_planks", "spruce_log_top"),
              ((3, 8, -16), (4, 9, -8), "stripped_oak_log"),                   # the shafts to the horse
              ((12, 8, -16), (13, 9, -8), "stripped_oak_log")]
VANILLA_CHEST = {"type": "minecraft:select", "property": "minecraft:local_time", "pattern": "MM-dd",   # items/chest.json
                 "cases": [{"when": ["12-24", "12-25", "12-26"], "model": {
                     "type": "minecraft:special", "base": "minecraft:item/chest",
                     "model": {"type": "minecraft:chest", "texture": "minecraft:christmas"}}}],
                 "fallback": {"type": "minecraft:special", "base": "minecraft:item/chest",
                              "model": {"type": "minecraft:chest", "texture": "minecraft:normal"}}}


def cart_model():
    """The item model of the War Wagon cart (CART_BOXES): the cart display has the scale units.CART_SCALE for the
    vanilla chest, so the boxes shrink by it around the middle (8, 8, 8) of the model. Each face has its uv: a face
    out of 0..16 with no uv reads its texture from the neighbors in the atlas."""
    names = sorted({t for b in CART_BOXES for t in b[2:]})
    out = []
    for lo, hi, side, *wheel in CART_BOXES:
        at = [[round(8 + (v - 8) / k, 3) for v, k in zip(p, units.CART_SCALE)] for p in (lo, hi)]
        size = [h - v for v, h in zip(lo, hi)]                       # the uv in the texture: at most one texture
        faces = {f: {"uv": [0, 0, min(size[a], 16), min(size[b], 16)],
                     "texture": f"#t{names.index(wheel[0] if wheel and f in ('east', 'west') else side)}"}
                 for f, a, b in (("north", 0, 1), ("south", 0, 1), ("east", 2, 1), ("west", 2, 1), ("up", 0, 2),
                                 ("down", 0, 2))}
        out.append({"from": at[0], "to": at[1], "faces": faces})
    textures = {f"t{k}": f"minecraft:block/{t}" for k, t in enumerate(names)} | {"particle": "minecraft:block/dark_oak_log"}
    return {"textures": textures, "elements": out}


HAIR, SHIRT, PANTS, SHOES, EYE, MOUTH = (74, 50, 30), (122, 92, 56), (72, 64, 110), (52, 40, 30), (50, 90, 160), (140, 60, 50)
IVORY, NAIL = (236, 228, 200), (204, 198, 182)                       # the tusks and toenails of an elephant (#2745)


def hide_texture(model, tone):
    """A 128 x 128 entity texture of elephant skin (#2745): each box gets the grey tone with darker wrinkle rows on its
    sides, the tusks are ivory, the feet have toenails and the front of the head two small dark eyes."""
    from PIL import Image, ImageDraw
    im = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    dark = tuple(int(c * 0.8) for c in tone)
    for u, v, w, h, k, part in SKIN_BOXES[model]:
        color = IVORY if part == "tusk" else tone
        d.rectangle([u + k, v, u + k + 2 * w - 1, v + k - 1], fill=color)            # top and bottom
        d.rectangle([u, v + k, u + 2 * k + 2 * w - 1, v + k + h - 1], fill=color)    # the four sides
        if part == "tusk":
            d.rectangle([u, v + k + h - 3, u + 2 * k + 2 * w - 1, v + k + h - 1], fill=(250, 246, 232))   # the tip
            continue
        for y in range(v + k + 2, v + k + h, 3 if part in ("trunk", "foot") else 5):  # wrinkles: rows on the sides
            d.line([(u, y), (u + 2 * k + 2 * w - 1, y)], fill=dark)
        if part == "foot":
            for x in range(u + 1, u + 2 * k + 2 * w, 3):                               # toenails above the sole
                d.rectangle([x, v + k + h - 2, x + 1, v + k + h - 1], fill=NAIL)
        if part == "head":
            e = v + k + 11                                                             # the eye row of the face
            for x in (u + k + 3, u + k + w - 5):
                d.rectangle([x, e, x + 1, e], fill=(30, 26, 24))
    return im


def skin_texture(model, tone):
    """A 64 x 64 entity texture with a human skin tone and face (#2738): each box of the model gets the color of its
    part on all six faces, the head gets hair, and the front of the head eyes, brows and a mouth. A horse gets one
    coat color and eyes (#2752), the model "none" an empty overlay. The ravager of the war elephants: hide_texture."""
    if model == "ravager":
        return hide_texture(model, tone)
    from PIL import Image, ImageDraw
    im = Image.new("RGBA", SKIN_SIZE.get(model, (64, 64)), (0, 0, 0, 0))
    if model == "none":                                                # an empty overlay
        return im
    d = ImageDraw.Draw(im)
    if model == "horse":                                               # a brown coat on all faces, dark eyes (#2752)
        d.rectangle([0, 0, 63, 63], fill=tone)
        d.point(HORSE_EYES, fill=HAIR)
        return im
    dark = tuple(int(c * 0.8) for c in tone)

    def box(u, v, w, h, k, color, rows=None):                  # rows: only the top (>0) or bottom (<0) rows of the sides
        if rows is None or rows > 0:                            # top and bottom; with rows only the top
            d.rectangle([u + k, v, u + k + (1 if rows is None else 0) * w + w - 1, v + k - 1], fill=color)
        y0, y1 = (v + k, v + k + h - 1) if rows is None else (v + k, v + k + rows - 1) if rows > 0 else (v + k + h + rows, v + k + h - 1)
        d.rectangle([u, y0, u + 2 * k + 2 * w - 1, y1], fill=color)                # the four sides
    for u, v, w, h, k, part in SKIN_BOXES[model]:
        if part == "head":
            box(u, v, w, h, k, tone)
            box(u, v, w, h, k, HAIR, 2)
            d.rectangle([u + 2 * k + w, v + k, u + 2 * k + 2 * w - 1, v + k + h - 3], fill=HAIR)   # the back of the head
            e = v + k + h - 6                                       # the eye row: the face is 8 or 10 high
            for x, w2 in ((u + k + 1, 1), (u + k + 5, -1)):
                d.point([(x, e - 1), (x + w2, e - 1)], fill=HAIR)  # brows
                d.point([(x, e)], fill=(240, 240, 240))
                d.point([(x + w2, e)], fill=EYE)
            if model == "zombie":
                d.point([(u + k + 3, e + 1), (u + k + 4, e + 1)], fill=dark)   # nose (a villager has its own box)
            d.line([(u + k + 2, e + 3), (u + k + 5, e + 3)], fill=MOUTH)
        elif part == "skin":
            box(u, v, w, h, k, tone)
        elif part == "arm":
            box(u, v, w, h, k, SHIRT)
            box(u, v, w, h, k, tone, -3)                            # the hand
            d.rectangle([u + k + w, v, u + k + 2 * w - 1, v + k - 1], fill=tone)
        else:
            box(u, v, w, h, k, PANTS if part == "leg" else SHIRT)
            if part == "leg":
                box(u, v, w, h, k, SHOES, -2)
                d.rectangle([u + k + w, v, u + k + 2 * w - 1, v + k - 1], fill=SHOES)
    return im


# The armor of the units with a look (#2742, units.LOOKS): the boxes (u, v, w, h, d) of the 64 x 32 equipment layers
# "humanoid" (helmet, chestplate, boots) and "humanoid_leggings", by armor slot; the base layer is dyeable (dyed
# leather takes the color of its item, as vanilla leather does), the overlay has the accent and crest colors.
ARMOR_BOXES = {"head": [(0, 0, 8, 8, 8)], "chest": [(16, 16, 8, 12, 4), (40, 16, 4, 12, 4)], "feet": [(0, 16, 4, 12, 4)],
               "legs": [(16, 16, 8, 12, 4), (0, 16, 4, 12, 4)]}
# the horse armor (#2743, layer "horse_body", 64 x 64): the boxes (u, v, w, h, d) of the body, neck and head of the
# horse model; the legs and the tail stay bare
HORSE_BOXES = [(0, 32, 10, 10, 22), (0, 35, 4, 12, 7), (0, 13, 6, 5, 7)]
METAL = {"chainmail": (150, 152, 158), "diamond": (96, 214, 206), "golden": (232, 192, 64), "iron": (206, 206, 212),
         "leather": (160, 101, 64), "netherite": (74, 66, 70), "dyed": (236, 236, 236)}


def armor_shade(pattern, x, y):
    """The light factor of the pixel x, y of a pattern: cloth, quilted, mail, scale or plate (#2742)."""
    return {"cloth": 0.92 if (x * 7 + y * 3) % 5 == 0 else 1.0,
            "quilted": 0.78 if (x + y) % 4 == 0 or (x - y) % 4 == 0 else 1.0,
            "mail": 0.72 if (x + y) % 2 else 1.0 - 0.1 * (y % 2),
            "scale": 0.68 if y % 3 == 2 else 0.86 if (x + (y // 3) % 2 * 2) % 4 == 0 else 1.0,
            "plate": 1.12 if x % 8 in (3, 4) else 0.8 if y % 6 == 5 else 1.0}[pattern]


def armor_textures(name, hero=False):
    """The textures (base, overlay) of the layers "humanoid", "humanoid_leggings" and (a mount with horse armor)
    "horse_body" of a unit with armor (#2742, #2743): its look (units.look) and the material of each piece."""
    look, gear = units.look(name, hero), units.pieces(units.describe(name, hero))
    mats = tuple((slot, "dyed" if "minecraft:dyed_color" in p.get("components", {}) else str(p["id"]).split(":")[1].split("_")[0])
                 for slot, p in sorted(gear.items()))
    return armor_images(look["pattern"], look["accent"], look.get("crest"), mats)


@functools.lru_cache(maxsize=None)
def armor_images(pattern, accent, crest, mats):
    """The textures of armor_textures from the look and the materials ((slot, material), ...): each box gets the
    material of its armor piece in the pattern of the look; a helmet leaves the face open but the brow (a plate helmet
    with a crest closes it to an eye slit), boots cover the lower leg, leggings the waist and the legs. The horse armor
    covers the head, neck and body of the horse, with a hem in the accent color (HORSE_BOXES, #2743)."""
    from PIL import Image
    gear = dict(mats)
    accent, crest = (tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) if c else None for c in (accent, crest))
    out = {}
    for layer, slots in (("humanoid", ("head", "chest", "feet")), ("humanoid_leggings", ("legs",))):
        base, over = (Image.new("RGBA", (64, 32), (0, 0, 0, 0)) for _ in range(2))
        for slot in slots:
            if slot not in gear:
                continue
            color = METAL[gear[slot]]
            for u, v, w, h, d in ARMOR_BOXES[slot]:
                for x in range(u, u + 2 * d + 2 * w):
                    for y in range(v, v + d + h):
                        side = y >= v + d                               # the four sides, else top and bottom
                        if not side and not (u + d <= x < u + d + 2 * w):
                            continue
                        r = y - v - d                                   # the row on the sides
                        front = u + d <= x < u + d + w                  # the front face
                        if side and slot == "head" and r >= 3 and (front or pattern == "cloth") and not (
                                pattern == "plate" and crest and r != 3):
                            continue                                    # the face; a closed helm: only the eye slit
                        if side and slot == "feet" and r < h - 5 or side and slot == "legs" and w == 8 and r < h - 4:
                            continue
                        f = armor_shade(pattern, x, y)
                        base.putpixel((x, y), tuple(min(255, int(c * f)) for c in color) + (255,))
                        mid = x - u - d in (w // 2 - 1, w // 2) and front   # the middle of the front
                        if side and slot == "chest" and w == 8 and (r >= h - 2 or mid and pattern in ("mail", "plate")) \
                                or side and slot == "legs" and w == 8 and r == h - 4 or side and slot == "head" and r == 0:
                            over.putpixel((x, y), accent + (255,))      # a belt, a tabard stripe, a band
                        if crest and slot == "head" and (not side and x - u - d in (3, 4) or side and mid and r < 3):
                            over.putpixel((x, y), crest + (255,))       # the crest from the brow over the top
        out[layer] = base, over
    if "body" in gear:                                              # the horse armor (#2743)
        base, over = (Image.new("RGBA", (64, 64), (0, 0, 0, 0)) for _ in range(2))
        for i, (u, v, w, h, d) in enumerate(HORSE_BOXES):
            for x in range(u, u + 2 * d + 2 * w):
                for y in range(v, v + d + h):
                    side = y >= v + d
                    if not side and not (u + d <= x < u + d + 2 * w):
                        continue
                    base.putpixel((x, y), tuple(min(255, int(c * armor_shade(pattern, x, y))) for c in METAL[gear["body"]]) + (255,))
                    if i == 0 and side and y >= v + d + h - 2:
                        over.putpixel((x, y), accent + (255,))          # the hem of the body
        out["horse_body"] = base, over
    return out


# The AoE2 weapons of --resource-pack (#2744, units.WEAPONS): 16 x 16 item textures, drawn as the vanilla tools on the
# diagonal from the handle (bottom left) to the tip (top right). A part: (kind, from, to, color[, side]): "shaft" pixels
# of the diagonal, "blade" a two pixels wide diagonal, "head" crosswise pixels at each step (side: from, to; +
# is the lower right side), "arc" a bow limb (radius) with its string, "disc" a round shield.
WOOD, LIGHT, DARK, IRON, STEEL, STRING = (112, 78, 44), (160, 120, 70), (70, 48, 28), (205, 205, 215), (110, 110, 125), (225, 225, 225)
WEAPON_ART = {
    "axe": [("shaft", 1, 12, WOOD), ("head", 9, 12, IRON, (-3, -1)), ("head", 10, 11, STEEL, (1, 1))],
    "bow": [("arc", 11, 0, WOOD)],
    "club": [("shaft", 1, 8, WOOD), ("head", 9, 14, DARK, (-1, 1))],
    "crossbow": [("shaft", 1, 12, WOOD), ("head", 10, 10, DARK, (-5, 5)), ("shaft", 13, 13, STEEL)],
    "halberd": [("shaft", 0, 12, WOOD), ("blade", 13, 15, IRON), ("head", 9, 11, IRON, (-3, -1)),
                ("head", 10, 10, STEEL, (1, 2))],
    "javelin": [("shaft", 0, 12, LIGHT), ("shaft", 13, 15, IRON)],
    "longbow": [("arc", 15, 0, WOOD)],
    "mace": [("shaft", 1, 9, WOOD), ("head", 10, 13, STEEL, (-1, 1)), ("head", 11, 12, IRON, (-2, 2))],
    "shield": [("disc", 7, 0, WOOD)],
    "sickle": [("shaft", 1, 5, WOOD), ("blade", 6, 10, IRON), ("head", 11, 11, IRON, (-2, 0)),
               ("head", 11, 11, IRON, (-4, -3)), ("head", 10, 10, IRON, (-5, -5))],
    "spear": [("shaft", 0, 11, WOOD), ("blade", 12, 15, IRON), ("head", 12, 12, IRON, (-1, 1))],
    "sword": [("shaft", 1, 3, DARK), ("head", 4, 4, STEEL, (-2, 2)), ("blade", 5, 14, IRON)],
    "throwing_axe": [("shaft", 3, 10, LIGHT), ("head", 8, 10, IRON, (-2, -1))],
}


def weapon_texture(kind):
    """The 16 x 16 item texture of an AoE2 weapon (WEAPON_ART, #2744)."""
    from PIL import Image
    im = Image.new("RGBA", (16, 16), (0, 0, 0, 0))

    def put(x, y, color):
        if 0 <= x < 16 and 0 <= y < 16:
            im.putpixel((x, y), color + (255,))
    for part, a, b, color, *side in WEAPON_ART[kind]:
        for i in range(a, b + 1):
            if part in ("shaft", "blade"):
                put(i, 15 - i, color)
                if part == "blade":
                    put(i - 1, 15 - i, color)                   # the second pixel of the blade, its upper left
            elif part == "head":
                for k in range(side[0][0], side[0][1] + 1):    # crosswise: (1, 1) per step, no gaps
                    put(i + k, 15 - i + k, color)
                    put(i + k + 1, 15 - i + k, color) if k < side[0][1] else None
        if part == "arc":                                       # a limb around the corner (16, 16), the string across
            for t in range(64):
                ang = math.pi + t / 63 * math.pi / 2
                put(round(16 + a * math.cos(ang)), round(16 + a * math.sin(ang)), color)
            for i in range(16 - a, 16):
                put(i, 31 - a - i, STRING)
        if part == "disc":                                      # the rim of iron, the boss in the middle
            for y in range(16):
                for x in range(16):
                    r = math.hypot(x - 7.5, y - 7.5)
                    if r <= a + 0.5:
                        put(x, y, STEEL if r > a - 0.7 or r < 1.6 else color)
    return im


def write_resourcepack(out):
    """--resource-pack (#2738): resourcepacks/resources.zip in the world folder, which single player loads with the
    world (26.x: LevelResource.MAP_RESOURCE_FILE; a world of an older version had resources.zip at its top, and the
    client moves it there, ResourcePackLocationFileFix). The zombie, skeleton and drowned units get a human face, the
    skeleton horses a brown coat (#2752), the War Wagon its cart (cart_model, #2746), and each unit with armor its own
    armor (#2742, units.dressed, #2743). Same bytes for each conversion: sorted names, a fixed time."""
    import io
    import zipfile
    files = {"pack.mcmeta": json.dumps({"pack": {
        "description": "aoe2mc: units with a human face, their own armor and AoE2 weapons", "pack_format": MC["resource_format"],
        "min_format": MC["resource_format"], "max_format": MC["resource_format"]}}, indent=1).encode()}
    files["assets/minecraft/items/chest.json"] = json.dumps({"model": {   # a chest with the cart data: the cart (#2746)
        "type": "minecraft:select", "property": "minecraft:custom_model_data", "index": 0,
        "cases": [{"when": "aoe2mc:war_wagon", "model": {"type": "minecraft:model", "model": "aoe2mc:item/war_wagon"}}],
        "fallback": VANILLA_CHEST}}, indent=1).encode()
    files["assets/aoe2mc/models/item/war_wagon.json"] = json.dumps(cart_model(), indent=1).encode()
    for path, (model, tone) in SKINS.items():
        buf = io.BytesIO()
        skin_texture(model, tone).save(buf, "PNG")
        files["assets/minecraft/textures/" + path] = buf.getvalue()
    for name, hero in units.dressed().items():                      # the armor of each unit (#2742, #2743)
        if units.asset(name) != name:                                  # ELITE_X wears the asset of X
            continue
        n, layers = name.lower(), {}
        for layer, images in armor_textures(name, hero).items():
            pngs = []
            for im in images:
                buf = io.BytesIO()
                im.save(buf, "PNG")
                pngs.append(buf.getvalue())
            # a unit with no line in data/looks.jsonl shares the textures of the same look and materials
            tex = n if name in units.LOOKS else "look_" + hashlib.sha1(b"".join(pngs)).hexdigest()[:12]
            layers[layer] = [{"texture": f"aoe2mc:{tex}", "dyeable": {"color_when_undyed": 0xFFFFFF}}, {"texture": f"aoe2mc:{tex}_overlay"}]
            for png, end in zip(pngs, ("", "_overlay")):
                files[f"assets/aoe2mc/textures/entity/equipment/{layer}/{tex}{end}.png"] = png
        files[f"assets/aoe2mc/equipment/{n}.json"] = json.dumps({"layers": layers}, indent=1).encode()
    for w in sorted({w for _, w in units.WEAPONS}):                 # the AoE2 weapons (#2744)
        buf = io.BytesIO()
        weapon_texture(w).save(buf, "PNG")
        files[f"assets/aoe2mc/textures/item/{w}.png"] = buf.getvalue()
        files[f"assets/aoe2mc/models/item/{w}.json"] = json.dumps(
            {"parent": "minecraft:item/" + ("generated" if w == "shield" else "handheld"),
             "textures": {"layer0": f"aoe2mc:item/{w}"}}).encode()
        files[f"assets/aoe2mc/items/{w}.json"] = json.dumps(
            {"model": {"type": "minecraft:model", "model": f"aoe2mc:item/{w}"}}).encode()
    os.makedirs(os.path.join(out, "resourcepacks"), exist_ok=True)
    with zipfile.ZipFile(os.path.join(out, "resourcepacks", "resources.zip"), "w", zipfile.ZIP_DEFLATED) as z:
        for name in sorted(files):
            z.writestr(zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0)), files[name], zipfile.ZIP_DEFLATED)
    return sorted(files)


def write_datapack(out, objects, ground, biome_names=(), ambience="basic", players=None, triggers=(), T=4,
                   trigger_stats=None, fog=None, mood=True):
    """datapacks/aoe2mc: a function every 2 s plays a work sound at each building with a player near it
    (docs/datapack.md). Fixed positions, no marker entities: the check costs nothing that /tick query shows.
    Ambience (#219): particles and sounds near the players by biome; "full" also writes the custom biomes, "off"
    writes no pack (and so no teams). Teams: `team_lines`. Timer and area triggers: `trigger_files`.
    fog: (start, end) blocks of the fog of a fog mood (FOG, #1626), a timeline of the overworld clock.
    mood: the "Change Color Mood" effects of the triggers change the time of day (--mood on, #1876).
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
        # the feet height next to the building (the ground in the footprint is the roof or barrier top, #588)
        xa, za = max(x0 - 1, 0), max(z0 - 1, 0)
        edge = ground[xa:x1 + 1, za:z1 + 1]
        outer = np.ones(edge.shape, bool)
        outer[x0 - xa:x1 - xa, z0 - za:z1 - za] = False
        y = int(np.median(edge[outer])) if outer.any() else int(ground[x, z]) + 1
        # playsound at volume 1 is heard up to 16 blocks: a larger check plays it for nobody
        at = f"execute positioned {x} {y} {z} if entity @a[distance=..16] " \
             f"if predicate aoe2mc:{rule[2]} run"
        lines.append(f"{at} playsound minecraft:{rule[1]} ambient @a ~ ~ ~ 1 {0.9 + 0.1 * (x % 3):.1f}")
        if rule[3]:
            lines.append(f"{at} particle minecraft:{rule[3]} ~ ~1 ~ 0.4 0.2 0.4 0 4")
    work = len(lines)
    lines += ambience_lines(biome_names)
    groups = sorted({n.split(":")[1] for n in biome_names if n.startswith("aoe2mc:")})
    team_load, team_pulse = team_lines(objects, players or {})
    # each player gets the map of the world in the off-hand once, so the minimap is there without a search (#966)
    team_pulse = team_pulse + MAP_PULSE
    trigger_load, trigger_fns = trigger_files(triggers, T, ground, players, trigger_stats, mood)
    if not lines and not groups and not team_load and not trigger_load and not fog:   # the server finds a new pack itself
        return 0, 0
    files = {
        "pack.mcmeta": {"pack": {"description": "aoe2mc: work sounds and ambience", "pack_format": MC["pack_format"],
                                 "min_format": MC["pack_format"], "max_format": MC["pack_format"]}},
        "data/minecraft/tags/function/load.json": {"values": ["aoe2mc:load"]},
        "data/aoe2mc/function/load.mcfunction": "\n".join(team_load + trigger_load + ["schedule function aoe2mc:pulse 40t replace"]) + "\n",
        "data/aoe2mc/function/pulse.mcfunction": "\n".join(lines + team_pulse + ["schedule function aoe2mc:pulse 40t replace"]) + "\n",
    }
    files.update(trigger_fns)
    for name, chance in CHANCE.items():
        files[f"data/aoe2mc/predicate/{name}.json"] = {"type": "minecraft:random_chance", "chance": chance}
    for g in groups:
        files[f"data/aoe2mc/worldgen/biome/{g}.json"] = biome_file(g)
    if fog:                         # a worldgen registry: the client shows the "Experimental Settings" warning (#1597)
        files["data/aoe2mc/timeline/fog.json"] = {"clock": "minecraft:overworld", "tracks": {
            f"minecraft:visual/{track}": {"keyframes": [{"ticks": 0, "value": float(v)}]}
            for track, v in (("fog_start_distance", fog[0]), ("fog_end_distance", fog[1]),
                             ("sky_fog_end_distance", fog[1]))}}
        files["data/minecraft/tags/timeline/in_overworld.json"] = {"values": ["aoe2mc:fog"]}
    for name, data in files.items():
        path = os.path.join(root, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(data if isinstance(data, str) else json.dumps(data))
    return sum("playsound" in line for line in lines[:work]), len(lines) - work


# The time of day (world clock ticks) of each map color mood of a DE scenario (ColorMood, #1595): a dark mood at
# midnight, a late one at sunset, the others at noon. The game rule advance_time is 0, so the time stays.
NOON = 6000
MOODS = {
    "ARCTIC": NOON,
    "AUTUMN": NOON,
    "BRUMOUS": NOON,
    "DARKNESS": 18000,
    "DEFAULT": NOON,
    "DESERT": NOON,
    "EVENING": 12500,
    "JUNGLE": NOON,
    "MISTY": NOON,
    "MURKY": NOON,
    "NIGHT": 18000,
    "RAINFOREST": NOON,
    "SAVANNAH": NOON,
    "SPRING": NOON,
    "STEPPES": NOON,
    "SUMMER": NOON,
    "SWAMP": NOON,
    "TWILIGHT": 13000,
    "WINTER": NOON,
}
# The wet moods have rain (#1596); it falls as snow in the cold biomes. advance_weather is 0, so the rain stays. A set,
# not a column of MOODS: MOODS gives the ticks.
RAIN = {
    "MURKY",
    "RAINFOREST",
    "SWAMP",
}
# The fog moods (#1626): fog from start to end blocks, as the AoE2 haze (research #1597, owner decision #1625). Only
# with --fog or --ambience full: a timeline makes the client show the "Experimental Settings" warning.
FOG = {
    "BRUMOUS": (4, 48),
    "MISTY": (4, 48),
    "MURKY": (4, 48),
}


def write_level_dat(path, name, spawn, yaw=SPAWN_YAW, size=None, ticks=NOON, rain=False):
    """size: the map size in blocks; the vanilla world border goes around the map (#172). ticks: the time of day
    (MOODS, #1595). rain: it rains (RAIN, #1596)."""
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
    level = Compound({
        "DataVersion": Int(MC["data_version"]), "version": Int(19133),
        "Version": Compound({"Id": Int(MC["data_version"]), "Name": String(MC["name"]),
                             "Series": String("main"), "Snapshot": Byte(0)}),
        "LevelName": String(name), "GameType": Int(1), "allowCommands": Byte(1), "initialized": Byte(1),
        "LastPlayed": Long(int(time.time() * 1000)), "Time": Long(0), "WasModded": Byte(0),
        "DataPacks": Compound({"Enabled": List[String]([String("vanilla")]), "Disabled": List[String]([])}),
    })
    level["spawn"] = Compound({"pos": IntArray(list(spawn)), "dimension": String("minecraft:overworld"),
                               "yaw": Float(yaw), "pitch": Float(0)})
    # not peaceful: peaceful removes the soldiers
    level["difficulty_settings"] = Compound({"difficulty": String("easy"), "hardcore": Byte(0), "locked": Byte(0)})
    File({"Data": level}, gzipped=True).save(path)
    # 26.1: most fields left level.dat for files in data/minecraft/ (docs/minecraft-versions.md)
    files = {
        "game_rules": {"minecraft:advance_time": Byte(0), "minecraft:advance_weather": Byte(0),
                       "minecraft:spawn_mobs": Byte(0), "minecraft:fire_spread_radius_around_player": Int(0)},
        "world_gen_settings": {"seed": Long(0), "generate_structures": Byte(0), "bonus_chest": Byte(0),
                               "dimensions": Compound({"minecraft:overworld": dim("overworld", void),
                                                       "minecraft:the_nether": dim("the_nether", nether),
                                                       "minecraft:the_end": dim("the_end", end)})},
        "weather": {"raining": Byte(int(rain)), "thundering": Byte(0), "rain_time": Int(0), "thunder_time": Int(0),
                    "clear_weather_time": Int(0)},
        "world_clocks": {"minecraft:overworld": Compound({"total_ticks": Long(ticks), "paused": Byte(0)})},
    }
    d = os.path.join(os.path.dirname(path), "data", "minecraft")
    os.makedirs(d, exist_ok=True)
    for f, v in files.items():
        File({"data": Compound(v), "DataVersion": Int(MC["data_version"])}, gzipped=True).save(os.path.join(d, f + ".dat"))
    # The world border is data of the overworld (DimensionStorageFileFix in the 26.3 server)
    c = size / 2 if size else 0.0
    edge = {"center_x": Double(c), "center_z": Double(c), "size": Double(size or 5.9999968e7),
            "lerp_time": Long(0), "lerp_target": Double(size or 5.9999968e7), "safe_zone": Double(5),
            "damage_per_block": Double(0.2), "warning_blocks": Int(5), "warning_time": Int(15)}
    d = os.path.join(os.path.dirname(path), "dimensions", "minecraft", "overworld", "data", "minecraft")
    os.makedirs(d, exist_ok=True)
    File({"data": Compound(edge), "DataVersion": Int(MC["data_version"])}, gzipped=True).save(
        os.path.join(d, "world_border.dat"))


# The base colors of the map items (MapColor.java of the 26.3 server jar, ids 0 to 61; 0 = no color). A map byte is
# id * 4 + shade, and the shades multiply the color by 180, 220, 255 or 135 / 255 (MapColor$Brightness).
MAP_COLORS = [
    0x000000, 0x7FB238, 0xF7E9A3, 0xC7C7C7, 0xFF0000, 0xA0A0FF, 0xA7A7A7, 0x007C00,
    0xFFFFFF, 0xA4A8B8, 0x976D4D, 0x707070, 0x4040FF, 0x8F7748, 0xFFFCF5, 0xD87F33,
    0xB24CD8, 0x6699D8, 0xE5E533, 0x7FCC19, 0xF27FA5, 0x4C4C4C, 0x999999, 0x4C7F99,
    0x7F3FB2, 0x334CB2, 0x664C33, 0x667F33, 0x993333, 0x191919, 0xFAEE4D, 0x5CDBD5,
    0x4A80FF, 0x00D93A, 0x815631, 0x700200, 0xD1B1A1, 0x9F5224, 0x95576C, 0x706C8A,
    0xBA8524, 0x677535, 0xA04D4E, 0x392923, 0x876B62, 0x575C5C, 0x7A4958, 0x4C3E5C,
    0x4C3223, 0x4C522A, 0x8E3C2E, 0x251610, 0xBD3031, 0x943F61, 0x5C191D, 0x167E86,
    0x3A8E8C, 0x562C3E, 0x14B485, 0x646464, 0xD8AF93, 0x7FA796,
]
MAP_SHADES = (180, 220, 255, 135)


def map_palette():
    """RGB of each map byte (index = id * 4 + shade), as float rows."""
    rgb = np.array([[(c >> 16) & 255, (c >> 8) & 255, c & 255] for c in MAP_COLORS], float)
    return (rgb[:, None, :] * np.array(MAP_SHADES)[None, :, None] / 255).reshape(-1, 3)


def map_scale(n):
    """The smallest map scale (0 to 4) whose 128 * 2^scale blocks hold a world of n blocks."""
    return next((s for s in range(5) if 128 << s >= n), 4)


def map_colors(img):
    """The 128 x 128 map bytes (row z, column x) of the top view img (RGB array [z, x, 3] of an n x n world), and
    the scale and the center (x = z) in blocks. One block in the middle of each map pixel gives its color, and the
    nearest map color (all shades) its byte. Pixels outside the world have no color (0)."""
    n = img.shape[0]
    s = map_scale(n)
    f = 1 << s
    c = round(n / 2 / f) * f                                     # the server draws the pixels from a multiple of f
    pos = c - 64 * f + np.arange(128) * f + f // 2
    inside = (pos >= 0) & (pos < n)
    px = img[np.clip(pos, 0, n - 1)][:, np.clip(pos, 0, n - 1)].reshape(-1, 3).astype(float)
    pal = map_palette()
    pal[:4] = np.inf                                             # id 0 is transparent
    out = np.argmin(((px[:, None, :] - pal[None]) ** 2).sum(-1), axis=1).reshape(128, 128)
    return np.where(inside[:, None] & inside[None, :], out, 0).astype(np.uint8), s, c


# The map color id of each dye (MapColor.COLOR_*), and of the gaia mines: GOLD and STONE, so that they differ from
# the yellow and gray players (#840).
MAP_DYES = {"black": 29, "blue": 25, "brown": 26, "cyan": 23, "gray": 21, "green": 27, "light_blue": 17,
            "light_gray": 22, "lime": 19, "magenta": 16, "orange": 15, "pink": 20, "purple": 24, "red": 28,
            "white": 8, "yellow": 18}
MAP_MINES = {r["name"]: r["map_color"] for r in OBJECTS if "map_color" in r}


def map_objects(colors, s, c, objects, players=None, T=4):
    """Draw the objects on the map bytes, as on the AoE2 minimap (#840): a building is the square of its footprint
    in its player color, a unit one pixel, a gold or stone mine of gaia one pixel. Other gaia objects keep the
    terrain color. Shade 2 (the full color); units go on top of buildings."""
    f, base = 1 << s, c - (64 << s)
    def put(x0, z0, x1, z1, cid):                                # blocks [x0, x1) x [z0, z1); at least one pixel
        (i0, i1), (j0, j1) = ((max(0, (a - base) // f), min(128, (max(a, b - 1) - base) // f + 1)) for a, b in
                              ((z0, z1), (x0, x1)))
        colors[i0:i1, j0:j1] = cid * 4 + 2
    order = {"O": 0, "B": 1, "U": 2}
    for o in sorted(objects, key=lambda o: order.get(o["kind"], 3)):
        p, name = o.get("player", 0), o["name"]
        if o["kind"] == "O" and name in MAP_MINES:
            x, z = int(o["x"] * T), int(o["y"] * T)
            put(x, z, x + 1, z + 1, MAP_MINES[name])
        elif p and o["kind"] == "B" and "footprint" in o:
            put(*o["footprint"], MAP_DYES.get(player_color(p, players), 8))
        elif p and o["kind"] == "U" and not o.get("garrisoned"):
            x, z = int(o["x"] * T), int(o["y"] * T)
            put(x, z, x + 1, z + 1, MAP_DYES.get(player_color(p, players), 8))
    return colors


def write_map(out, img, objects=(), players=None, T=4):
    """Write a locked map of the world (map id 0, #838) with its objects (#840): `give @p filled_map[map_id=0]`
    shows it. The 26.3 server keeps maps in data/minecraft/maps/ (DimensionStorageFileFix: data/map_N.dat -> N.dat,
    idcounts.dat -> last_id.dat)."""
    colors, s, c = map_colors(np.asarray(img))
    colors = map_objects(colors, s, c, objects, players, T)
    d = os.path.join(out, "data", "minecraft", "maps")
    os.makedirs(d, exist_ok=True)
    data = {"colors": ByteArray(colors.reshape(-1).astype(np.int8)), "scale": Byte(s), "xCenter": Int(c),
            "zCenter": Int(c), "dimension": String("minecraft:overworld"), "locked": Byte(1),
            "trackingPosition": Byte(0), "unlimitedTracking": Byte(0), "banners": List[Compound]([]),
            "frames": List[Compound]([])}
    for f, v in (("0", data), ("last_id", {"map": Int(0)})):
        File({"data": Compound(v), "DataVersion": Int(MC["data_version"])}, gzipped=True).save(os.path.join(d, f + ".dat"))


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
COLORS = [("yellow_poplar_leaves", (215, 180, 40)), ("orange_poplar_leaves", (215, 115, 30)), ("red_poplar_leaves", (170, 40, 30)),
          ("leaves", (40, 110, 40)), ("snow[", (240, 240, 245)), ("tall_grass", (95, 150, 65)), ("large_fern", (75, 130, 55)), ("moss", (90, 115, 45)), ("petals", (235, 165, 200)), ("poppy", (200, 30, 30)), ("tulip", (220, 120, 60)),
          ("dandelion", (240, 220, 50)), ("cornflower", (70, 100, 220)), ("allium", (180, 110, 220)),
          ("bluet", (225, 230, 235)), ("daisy", (235, 235, 225)), ("lily_of", (235, 240, 235)),
          ("mushroom", (160, 110, 80)), ("stone_brick", (122, 122, 122)), ("cobblestone", (110, 110, 110)), ("white_terracotta", (215, 200, 190)),
          ("glass", (170, 200, 220)), ("banner", None), ("terracotta", (200, 180, 160)),
          ("calcite", (225, 225, 220)), ("quartz", (235, 230, 225)), ("cinnabar", (170, 55, 45)), ("sulfur", (195, 165, 70)), ("chiseled_resin", (175, 75, 30)), ("resin_brick", (205, 95, 35)), ("bricks", (150, 70, 55)),
          ("brick", (150, 70, 55)), ("deepslate_tile", (55, 55, 60)), ("dark_oak", (65, 45, 25)),
          ("spruce", (105, 75, 45)), ("acacia", (170, 90, 50)), ("jungle", (160, 115, 80)),
          ("crimson", (140, 50, 60)), ("mud_brick", (140, 105, 80)), ("packed_mud", (140, 105, 80)),
          ("red_sandstone", (180, 95, 40)), ("copper", (80, 160, 140)), ("smooth_stone", (160, 160, 160)),
          ("hay", (200, 170, 50)), ("chain", (60, 60, 70)), ("iron_bars", (90, 90, 90)), ("fence", (120, 90, 60)),
          ("door", (110, 80, 50)), ("bell", (240, 200, 40)), ("campfire", (230, 120, 30)),
          ("water", (52, 92, 200)), ("ice", (160, 190, 240)), ("seagrass", (52, 92, 200)),
          ("dry_grass", (190, 170, 100)), ("leaves", (40, 110, 40)), ("bamboo", (90, 160, 40)), ("grass_block", (100, 160, 70)),
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
    n = state.split(":")[1].split("[")[0].removesuffix("_stairs").removesuffix("_slab")   # white_wool_stairs: as white_wool
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
class Progress:
    """One line that changes in place (\\r) during a long phase, at most each `every` s, so that a large map does not
    look stuck (#691). Nothing when the output is not a terminal (CI, tests, a pipe): the output stays the same."""

    def __init__(self, label, total, out=None, every=2.0, clock=time.time):
        self.out = out or sys.stdout
        self.label, self.total, self.every, self.clock = label, total, every, clock
        self.on = total > 0 and self.out.isatty()
        self.t0 = self.last = clock()
        self.width = 0

    def step(self, done):
        if not self.on or self.clock() - self.last < self.every:
            return
        self.last = now = self.clock()
        text = f"\r  {self.label} {done}/{self.total} ({100 * done // self.total} %), {now - self.t0:.0f} s"
        self.width = max(self.width, len(text))
        self.out.write(text)
        self.out.flush()

    def close(self):        # clear the line, so that the next print starts at column 0
        if self.width:
            self.out.write("\r" + " " * self.width + "\r")
            self.out.flush()


def convert(src, out, T=4, H=3, name=None, seed=1, preview=False, arch=None, player_arch=(), with_units=True,
            barriers=True, mc_version=VERSION_NAME, spawn=None, birds=True, orientation="ne", verbose=False,
            garrison="inside", border_design="diorama", ambience="basic", at=None, mood="on", fog=False,
            resource_pack=False):
    """at: recorded games only, the time in ms (--at): convert the state at that time (apply_timeline).
    mood: "on" sets the time of day of the map color mood (MOODS), "off" keeps noon (#1595).
    fog: the fog of a fog mood (FOG, #1626); ambience "full" gives it too.
    resource_pack: resources.zip with human faces for the zombie units (#2738) and own armor (units.ASSETS, #2742)."""
    global MC
    MC = VERSIONS[mc_version]
    units.ASSETS = resource_pack
    PALETTE_CACHE.clear()   # the cached entries can have the block names of another version
    try:
        _convert(src, out, T, H, name, seed, preview, arch, player_arch, with_units, barriers, spawn, birds, orientation,
                 verbose, garrison, border_design, ambience, at, mood, fog, resource_pack)
    finally:
        MC = VERSIONS[VERSION_NAME]
        PALETTE_CACHE.clear()
        buildings.TURN = 0
        units.ASSETS = False


def _convert(src, out, T, H, name, seed, preview, arch, player_arch, with_units, barriers, spawn, birds, orientation,
             verbose, garrison, border_design, ambience, at=None, mood="on", fog=False, resource_pack=False):
    buildings.BARRIERS = barriers
    buildings.TURN, yaw = ORIENTATIONS[orientation]
    MOVED.clear()           # the counts of an earlier conversion in this process
    BLOCK_DATA.clear()
    buildings.SHELVES.clear()
    rng = np.random.default_rng(seed)
    t0 = time.time()
    times, clock = {}, [t0]
    TICKS[:] = [(t0, "start")]

    def tick(phase):        # add the time since the last tick to the phase (--verbose)
        now = time.time()
        TICKS.append((now, phase))
        times[phase] = times.get(phase, 0.0) + now - clock[0]
        clock[0] = now

    size, terrain, elevation, tnames, texts, objects, players = read_map(src, seed)
    record = src.lower().endswith(RECORDS)
    timeline = read_timeline(src) if record else None
    if timeline is not None:
        name_timeline(objects, timeline, water=np.vectorize(lambda t: terrain_style(tnames.get(int(t), "GRASS_1"))["depth"] > 0,
                                                            otypes=[bool])(terrain))
    at_stats = Counter()
    if at is not None:
        if timeline is None:
            raise OptionError("--at needs a recorded game (.aoe2record)" if not record else
                              "--at: mgz cannot read the commands of this recorded game (only its start state)")
        objects, at_stats = apply_timeline(objects, timeline, at)
    for c in (c for t in texts.get("triggers", ()) for c in t["conditions"] + t["effects"] if "area" in c):
        c["area"] = turn_area(c["area"], size, buildings.TURN)
    for e in (e for t in texts.get("triggers", ()) for e in t["effects"] if min(e.get("tile", [-1])) >= 0):
        e["tile"] = [int(v) for v in turn_tile(e["tile"][0] + 0.5, e["tile"][1] + 0.5, size, buildings.TURN)]
    for e in timeline or ():
        for k in ("tile", "end"):
            if k in e:
                e[k] = [round(float(v), 3) for v in turn_tile(*e[k], size, buildings.TURN)]
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
    if at is not None:
        print(f"  state at {at // 60000}:{at // 1000 % 60:02d}: " + ", ".join(f"{k}: {v}" for k, v in at_stats.items()))
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
    BLOCK_DATA.update({p: shelf_data(items) for p, items in buildings.SHELVES.items()})
    for k, v in sorted(stats.items()):
        print(f"  {k}: {v}")
    spawn = find_spawn(cols, objects, players, spawn)
    book = place_book(cols, edits, spawn, texts, name)
    if book:
        print(f"  book with the scenario texts: lectern at {book}")
    frame = place_map(cols, edits, spawn, book)   # before the units: they keep out of its column
    if frame:
        print("  map of the world: glow item frame at", tuple(int(v) for v in frame[0]["block_pos"]))
    colors = [player_color(pid, players) for pid in sorted(players) if pid and any(o["player"] == pid for o in objects)]
    r = border(cols, border_design, colors, edits)
    edits.connect()
    per_chunk = edits.by_chunk(max(cols.width, cols.n + r), -r)
    tick("objects")
    before = set(stats)
    unit_chunks = plan_units(objects, players, cols, rng, stats, birds, garrison, ambience == "off") if with_units else {}
    if frame:
        unit_chunks.setdefault((int(frame[1]) >> 4, int(frame[2]) >> 4), []).append(frame)
    tick("units")
    print(f"  units: {stats['units']}, fish: {stats['fish']}")
    for k in sorted(set(stats) - before - {"units", "fish"}):
        print(f"  {k}: {stats[k]}")
    passable = passable_states(B.states)

    dim = os.path.join(out, "dimensions", "minecraft", "overworld")
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
    progress = Progress("chunks", nchunks * nchunks + len(rim))
    for cx in range(nchunks):
        for cz in range(nchunks):
            progress.step(cx * nchunks + cz)
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
    for i, (cx, cz) in enumerate(sorted(rim)):
        progress.step(nchunks * nchunks + i)
        data, _ = build_chunk(cx, cz, outside, per_chunk[(cx, cz)], (cx * 16, cz * 16))
        regions.setdefault((cx >> 5, cz >> 5), {})[(cx & 31, cz & 31)] = data
    progress.close()
    tick("chunks")
    for (rx, rz), chunks in regions.items():
        write_region(os.path.join(dim, "region", f"r.{rx}.{rz}.mca"), chunks)
    for (rx, rz), chunks in entity_regions.items():
        write_region(os.path.join(dim, "entities", f"r.{rx}.{rz}.mca"), chunks)

    write_level_dat(os.path.join(out, "level.dat"), name, spawn, yaw, cols.n,
                    MOODS.get(texts.get("mood"), NOON) if mood == "on" else NOON, mood == "on" and texts.get("mood") in RAIN)
    from PIL import Image
    lut = np.array([block_color(s) for s in B.states], np.uint8)
    img = lut[top_view[:cols.n, :cols.n].T]                     # rows = z, columns = x
    shade = np.clip(1 + (cols.wtop[:cols.n, :cols.n].T - WATER_Y) * 0.02, 0.6, 1.4)
    depth = (cols.wtop - cols.top)[:cols.n, :cols.n].T
    shade *= np.where(depth > 0, np.clip(1.6 - 0.2 * depth, 1, 1.4), 1)     # shallow water is lighter, as on a map item
    img = Image.fromarray(np.clip(img * shade[..., None], 0, 255).astype(np.uint8))
    write_objects(os.path.join(out, "aoe2mc.json"), size, T, H, players, objects, cols, ground, timeline,
                  texts.get("mood", "DEFAULT"), map_colors(np.asarray(img))[0], texts.get("global_victory"), texts,
                  {k: f(texts.get("triggers", [])) for k, f in TRIGGER_LISTS.items()})
    triggers, tstats = texts.get("triggers", []), Counter()
    haze = FOG.get(texts.get("mood")) if mood == "on" and (fog or ambience == "full") else None
    n, amb = write_datapack(out, objects, ground, cols.biome_names, ambience, players, triggers, T, tstats, haze,
                            mood == "on")
    if resource_pack:
        print(f"  resource pack (resourcepacks/resources.zip): {len(write_resourcepack(out)) - 1} textures")
    k = sum(bool(re.search(r"/trigger/\d+\.mcfunction$", f))     # not the roll and timer functions (#2791)
            for f in trigger_files(triggers, T, ground, players, mood=mood == "on")[1]) \
        if ambience != "off" else 0
    if k:
        print(f"  timer and area triggers (chat, instructions, objects): {k}"
              + "".join(f", {v} {w}" for w, v in sorted(tstats.items())))
    if n:
        print(f"  work sounds at buildings: {n}")
    if amb:
        print(f"  ambience (particles and sounds by biome): {amb} lines"
              + (", custom biomes (Minecraft shows the experimental warning)" if ambience == "full" else ""))
    if haze:
        print(f"  fog of the map mood: {haze[0]} to {haze[1]} blocks (Minecraft shows the experimental warning)")

    if preview:
        img.save(os.path.join(out, "preview.png"))
    write_map(out, img, objects, players, T)
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
These scenarios of the campaign use an old scenario format ({ext}) that aoe2mc cannot read.
aoe2mc wrote them to {out}:
{files}
Do these steps to convert them:
  1. Copy the files to the scenario folder of AoE2 DE:
     <Steam user folder>/Games/Age of Empires 2 DE/<number>/resources/_common/scenario
  2. Start AoE2 DE. In the scenario editor, open each scenario and save it. DE saves it as .aoe2scenario.
  3. Convert each .aoe2scenario file with aoe2mc. Or, in the DE campaign editor, make a campaign of the
     scenarios and convert the .aoe2campaign file."""


def convert_campaign(src, out, only=None, name=None, **kw):
    """One world per scenario: out/<number> <scenario name>/. only: the number of one scenario (1 = first).
    An old campaign (.cpx, .cpn): convert its .scx scenarios of format 1.21 (#347); write the other scenario files to
    out/ and stop with the steps for the DE editor."""
    import tempfile
    version, title, entries = read_campaign(src)
    if only is not None and not 1 <= only <= len(entries):
        raise OptionError(f"--scenario {only}: the campaign {title!r} has {len(entries)} scenarios")
    print(f"Campaign {title!r}: {len(entries)} scenarios")
    chosen = [(i, re.sub(r'[\\/:*?"<>|]', "_", fn), data) for i, (fn, data) in enumerate(entries, 1)
              if only is None or i == only]
    if version == b"1.00":
        old = []
        for i, fn, data in chosen:
            stem = os.path.splitext(fn)[0]
            if fn.lower().endswith(".scx"):
                with tempfile.TemporaryDirectory() as tmp:
                    path = os.path.join(tmp, fn)       # "Read <fn>" names the scenario (#578)
                    with open(path, "wb") as f:
                        f.write(data)
                    try:
                        convert(path, os.path.join(out, f"{i} {stem}"), name=f"{name} {i}" if name else stem, **kw)
                        continue
                    except OptionError as e:      # another format version, or a file that scx.py cannot read
                        print(f"{i} {fn}: {e}")
            old.append((i, fn, data))
        if old:
            os.makedirs(out, exist_ok=True)
            for i, fn, data in old:
                with open(os.path.join(out, f"{i} {fn}"), "wb") as f:
                    f.write(data)
            exts = sorted({os.path.splitext(fn)[1] or "?" for _, fn, _ in old})
            raise SystemExit(OLD_CAMPAIGN_STEPS.format(ext=", ".join(exts), out=out,
                                                       files="\n".join(f"  {i} {fn}" for i, fn, _ in old)))
        return
    for i, fn, data in chosen:
        stem = re.sub(r"\.aoe2scenario$", "", fn, flags=re.I)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, stem + ".aoe2scenario")
            with open(path, "wb") as f:
                f.write(data)
            convert(path, os.path.join(out, f"{i} {stem}"), name=f"{name} {i}" if name else stem, **kw)


def game_time(text):
    """--at MM:SS (or H:MM:SS) -> ms."""
    m = re.fullmatch(r"(?:(\d+):)?(\d+):([0-5]\d)", text)
    if not m:
        raise argparse.ArgumentTypeError(f"{text!r}: use MM:SS, for example 12:30")
    h, mm, ss = int(m.group(1) or 0), int(m.group(2)), int(m.group(3))
    return ((h * 60 + mm) * 60 + ss) * 1000


def main(argv=None):
    ap = argparse.ArgumentParser(description="Convert an AoE2 DE scenario to a Minecraft Java world.")
    ap.add_argument("scenario", nargs="?", help=".aoe2scenario file, .aoe2record, .mgz, .mgx or .mgl (the start state of a recorded game), .scx "
                    "(an old scenario, format 1.21), .json (a map description, README), .rms (the land of a random map "
                    "script, with --seed), or "
                    ".aoe2campaign, .cpx or .cpn (one world per scenario; old scenarios that are not .scx 1.21: the "
                    "steps for the DE editor)")
    ap.add_argument("output", nargs="?", help="output world folder (put it in .minecraft/saves/); for a campaign the "
                    "folder of the worlds")
    ap.add_argument("--random-map", choices=("arabia", "arena", "black_forest", "gold_rush", "highland",
                                         "islands", "mediterranean", "nomad"),
                    metavar="KIND",
                    help="make the map with an own generator of the seed, no input file (arabia, arena, black_forest, "
                    "gold_rush, highland: a river with fords, islands: one island for each player, mediterranean: a sea in the middle, nomad: no town "
                    "center); give only the output")
    ap.add_argument("--scenario", dest="only", type=int_range(1, 999), metavar="N",
                    help="campaign: convert only scenario N (1 = the first)")
    ap.add_argument("--tile-size", type=int_range(1, 16), default=4, help="blocks per tile (default 4)")
    ap.add_argument("--level-height", type=int_range(1, 16), default=3, help="blocks per elevation level (default 3)")
    ap.add_argument("--name", help="world name in the Minecraft menu")
    ap.add_argument("--seed", type=int, default=1, help="seed for random details and random maps (default 1)")
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
    ap.add_argument("--garrison", choices=("inside", "outside", "skip"), default="inside",
                    help="garrisoned units: ride their ship, or stand inside their building (default) or next to it, "
                         "or skip them")
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
    ap.add_argument("--mood", choices=("on", "off"), default="on",
                    help="on: the time of day of the map color mood of a DE scenario (Night and Darkness at night, "
                         "Evening and Twilight at sunset); off: noon for all maps (default on)")
    ap.add_argument("--fog", action="store_true",
                    help="fog for the fog moods of a DE scenario (Misty, Murky, Brumous); Minecraft then shows an "
                         "\"Experimental Settings\" warning when the world opens (--ambience full gives it too)")
    ap.add_argument("--resource-pack", action="store_true",
                    help="write resourcepacks/resources.zip into the world: single player loads it with the world, and the zombie "
                         "units get a human face")
    ap.add_argument("--at", type=game_time, metavar="MM:SS",
                    help="recorded game: convert the state at this game time (buildings and trained units of the "
                         "commands until then; default: the start)")
    ap.add_argument("--verbose", action="store_true", help="print the time of each phase")
    a = ap.parse_args(argv)
    if a.fog and a.ambience == "off":
        ap.error("--fog writes a datapack: not with --ambience off")
    if a.random_map:
        if a.output is not None:
            ap.error("--random-map takes no input file: give only the output world folder")
        a.output, a.scenario = a.scenario, RANDOM_MAP + a.random_map
        a.name = a.name or f"{a.random_map.title()} {a.seed}"
    if a.output is None:
        ap.error("give the input file and the output world folder")
    kw = dict(T=a.tile_size, H=a.level_height, seed=a.seed, preview=a.preview, arch=a.architecture,
              player_arch=a.player_architecture, with_units=not a.no_units, barriers=not a.no_barriers,
              mc_version=a.mc_version, spawn=a.spawn, birds=not a.no_birds, orientation=a.orientation,
              verbose=a.verbose, garrison=a.garrison, border_design=a.border, ambience=a.ambience,
              mood=a.mood, fog=a.fog, resource_pack=a.resource_pack)
    try:
        if a.at is not None and not a.scenario.lower().endswith(RECORDS):
            ap.error("--at needs a recorded game (.aoe2record)")
        if a.scenario.lower().endswith((".aoe2campaign", ".cpx", ".cpn")):
            convert_campaign(a.scenario, a.output, a.only, a.name, **kw)
        elif a.only is not None:
            ap.error("--scenario needs a campaign file (.aoe2campaign, .cpx, .cpn)")
        else:
            convert(a.scenario, a.output, name=a.name, at=a.at, **kw)
    except (OptionError, CampaignError) as e:
        ap.error(str(e))


if __name__ == "__main__":
    main()
