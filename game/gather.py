"""
Villagers gather wood: the first playable milestone of docs/research/gameplay.md (#138).

The player holds the command stick (`carrot_on_a_stick`). A right click on a villager of player 1 selects it
(glowing). A right click on a tree sends the selected villagers there. A villager walks on a path around
buildings, trees and water (one /tp per block), chops, carries the wood to the nearest drop site that takes wood
(town center or lumber camp, `DROP_SITES`), and goes back to the tree. It gets the lumberjack look
(`units.VILLAGER_JOBS`, as in AoE2). A right click on a fruit bush sends them to forage (#391): they carry the food
to a town center or a mill, with the forager look, and go on to the nearest bush when one is empty. A right click
on a gold or stone mine sends them to mine (#390): they carry the gold or stone to a town center or a mining camp,
with the miner look. An empty mine disappears, and they go on to the nearest mine of the same kind. A right click
on a farm sends one villager onto it (#392): one farmer per farm, as in AoE2. The wheat gets younger as the food
goes down, and an empty farm is dirt.
A right click on a construction site (build.py) sends them to build it, with the builder look (#418).
A right click on a deer, a boar or a herdable animal (HUNT_FOOD) sends them to hunt it (#1058), with the hunter look: they
walk to it and hit it with the vanilla `damage` command (a boar hits back with its vanilla AI). The dead animal leaves a
carcass with its AoE2 food on its tile (Map.carcasses): the hunters gather it as a bush and carry it to a town center or
a mill. With the cheat "aegis" the first hit kills the animal.
A right click on an own town center opens its menu: a click queues a villager for 50 food, a shift click 5 (train.py, #612, #620).
A right click on a selected villager opens the build menu, a chest menu (build.py, #621).
A right click on a military unit of player 1 selects it; more clicks add more military units (#516). A right
click on a unit of another player then sends them to attack it (`aoe attack` of the plugin, ai.py): one command
for the selection, by the tag `SELECT`. A unit of player 1 is no target: a click on it selects it.
A click with selected military units on a building of another player sends them to attack its target (#608,
combat.building). When the plugin removes the target (0 hit points), its footprint is free ground for paths.
On a Paper server, the villagers walk with Minecraft path finding (`aoe moveto` of game/plugin, at the AoE2 walk
speed of game/ai.py), and `aoe stop` stops them when they arrive (#437). The own path code (Map.path, one /tp per
block) is only for the vanilla server.
A sidebar scoreboard shows wood, food, gold and stone of player 1. A boss bar shows the selected unit (bossbar.py, #659).
The action bar shows the actions that the player can do in the selection state now (hints.py, #798).
A right click on free ground with selected units moves them there (walk_to, #1368): each unit to its own free cell
near the click; military units with the plugin path finding, villagers stop their work.

The program sees a click in two statistics: the use of the stick, and "talked to villager" (a right click on a
villager is an interaction with the entity, not a use of the item). Then it reads the position and the view of
the player, and finds the villager or the tree on that ray with the data of aoe2mc.json.
"""
import collections
import heapq
import json
import math
import os
import random
import re
import sys
import time
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aoe2mc import PASSABLE_OBJECTS, WOODS, object_footprint, object_mob, player_color, tree_kind  # noqa: E402
from units import IDLE_JOB, TEAM_COLOR, VILLAGER_JOBS, animal, pretty  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import amounts  # noqa: E402
import autoscout  # noqa: E402
import battle_royale  # noqa: E402
import bossbar  # noqa: E402
import build  # noqa: E402
import capture_relic  # noqa: E402
import challenge  # noqa: E402
import cheats  # noqa: E402
import civs  # noqa: E402
import conquest  # noqa: E402
import defend_wonder  # noqa: E402
import demolish  # noqa: E402
import diplomacy  # noqa: E402
import feitoria  # noqa: E402
import flare  # noqa: E402
import fleet  # noqa: E402
import fog  # noqa: E402
import follow  # noqa: E402
import gaia  # noqa: E402
import garrison  # noqa: E402
import goto  # noqa: E402
import herd  # noqa: E402
import hill  # noqa: E402
import hints  # noqa: E402
import map_table  # noqa: E402
import market  # noqa: E402
import menu  # noqa: E402
import monk  # noqa: E402
import near  # noqa: E402
import record  # noqa: E402
import regen  # noqa: E402
import regicide  # noqa: E402
import relic_victory  # noqa: E402
import repair  # noqa: E402
import replay  # noqa: E402  (build imports it too)
import ruins  # noqa: E402
import scenario  # noqa: E402
import score  # noqa: E402
import siege_tower  # noqa: E402
import spectator  # noqa: E402
import stance  # noqa: E402
import sudden_death  # noqa: E402
import table  # noqa: E402
import techtree  # noqa: E402
import time_limit  # noqa: E402
import trade  # noqa: E402
import train  # noqa: E402
import transport  # noqa: E402
import treaty  # noqa: E402
import trebuchet  # noqa: E402
import wonder  # noqa: E402

RESOURCES = ("Wood", "Food", "Gold", "Stone")
# The gather tables: one line per name in data/gather.jsonl (#2033, `table.load`), values as in AoE2 (#389)
ROWS = table.load("gather.jsonl")
DROP_SITES = {r.lower(): tuple(t["name"] for t in ROWS if r.lower() in t.get("drop", ())) for r in RESOURCES}
MEAT_SITES = tuple(t["name"] for t in ROWS if "meat" in t.get("drop", ()))   # hunted food only (mule cart, #2194)
START = replay.START                                               # the AoE2 standard start resources (#973)
# AoE2 DE setting "Starting resources" (wiki "Random map", without the civilization bonus): run.py --resources (#2264)
LEVELS = {r["name"]: r["resources"] for r in table.load("setup.jsonl") if "resources" in r}
INFINITE = {r["name"] for r in table.load("setup.jsonl") if r.get("infinite")}   # "Infinite": no cost lowers it (#2489)
RANDOM = {r["name"]: r["random"] for r in table.load("setup.jsonl") if "random" in r}   # "Random": one of the levels
NOMAD = {"wood": 275, "stone": 100}     # AoE2 Nomad (wiki "Nomad (map)"): no building at the start, the cost of a town center
TREE_WOOD = 100                                                    # wood in one tree, as in AoE2
# plants of the ground that are not in #minecraft:replaceable: the trunk on a slope removes them from its row (#1124)
PLANTS = ("#minecraft:buttons", "#minecraft:flowers", "#minecraft:saplings", "#minecraft:wool_carpets",
          "minecraft:brown_mushroom", "minecraft:moss_carpet", "minecraft:pale_moss_carpet", "minecraft:red_mushroom")
BUSH_FOOD = 125                                                    # food in one fruit bush, as in AoE2 DE
# AoE2 DE work rates per game second (#393): lumberjack 0.39 (empires2_x2_p1.dat, #267), the others the published
# DE gather rates. Normal game speed is 1.7 game seconds per real second (#413).
AOE2_WORK, NORMAL = {"wood": 0.39, "food": 0.31, "farm": 0.33, "gold": 0.38, "stone": 0.36, "hunt": 0.41,
                     "fish": 0.43, "oyster": 0.38}, 1.7            # fish: a fisherman at a shore fish (#1283)
WORK_SECONDS = {r: 1 / (w * NORMAL) for r, w in AOE2_WORK.items()}    # real seconds per unit, as at Normal speed
WATCH_ROWS = {t['name']: t['watch'] for t in ROWS if t.get('watch')}   # true: combat.WATCH tiles, a number: that many
CARRY = {t['name']: t['carry'] for t in ROWS if 'carry' in t}
FOOD_CARRY = {"HEAVY_PLOW": 1}                                     # more food only per trip, as in AoE2 (#1424)
PACE = {t['name']: t['pace'] for t in ROWS if 'pace' in t}
WORK_TECHS = {t['name']: t['work'] for t in ROWS if 'work' in t}   # work rate factors (#1577)
# Food of a hunted animal, as in AoE2 DE (a "COW_..." name is a cow, #1058).
HUNT_FOOD = {t['name']: t['hunt'] for t in ROWS if 'hunt' in t}
DECAY = {t['name']: t['decay'] for t in ROWS if 'decay' in t}   # food per game second that a carcass loses (#2310)
# Food of a fish, as in AoE2 DE (the AoE2 wiki, "Fishing", #1283). Villagers reach the shore fish from the land.
FISH_FOOD = {t['name']: t['fish'] for t in ROWS if 'fish' in t}
SHORE_FISH = {t['name'] for t in ROWS if t.get('shore')}
# Oysters (AoE2 DE wiki "Oysters", #2465): gold in place of food, gathered as a fish; villagers 22.8 a minute (AOE2_WORK
# "oyster"), fishing ships 24 (SHIP_WORK). The gather kind "oyster" has its own civilization bonuses (Puru, Dravidians).
OYSTERS = {t['name'] for t in ROWS if t.get('res') == "gold"}
SHIP_WORK = {"deep": 0.42, "shore": 0.24, "trap": 0.35, "oyster": 0.4}   # the work rate of a fishing ship (AoE2 DE wiki)
TRAP_FOOD = 715                                                    # food in one fish trap, as in AoE2 DE (#1438)
SHIP_TECHS = {t['name']: tuple(t['ship']) for t in ROWS if 'ship' in t}   # the work rate factor and the more food of a trip (#1439)
HERDS = {t['name'] for t in ROWS if t.get('herd')}   # herdable animals: shepherds (civs.WORK)
VILLAGER_HIT = 3, 2.0                                              # AoE2 villager attack and reload (game seconds)
FARM_FOOD = 175                                                    # food in one farm, as in AoE2 DE (no upgrades)
PASTURE = next((r for r in table.load("build.jsonl") if r["name"] == "PASTURE"), {"food": 0})   # Khitans (#4118); antiquity: none
FARM_TECHS = {t['name']: t['farm'] for t in ROWS if 'farm' in t}
MINES = {t['name']: tuple(t['mine']) for t in ROWS if 'mine' in t}   # as in AoE2
MINE_BLOCKS = {"gold": ("gold_ore", "raw_gold_block", "stone"),                # the blocks of the converter's heap
               "stone": ("cobblestone", "andesite", "stone", "tuff")}
STEPS = [(dx, dz) for dx in (-1, 0, 1) for dz in (-1, 0, 1) if dx or dz]
CLOSED = 2000                # cells: a search this long checks if its goals are in a closed region (Map.closed, #2881)
NUMBER = r"(-?[\d.]+(?:E-?\d+)?)[df]"
CIVILIANS = tuple(t['name'] for t in ROWS if t.get('civilian'))
SELECT = "aoe2mc.selected"                                         # entity tag of the selected units
VOICES = {r["name"]: r for r in table.load("sounds.jsonl")}   # unit class -> its select voice (#3499)
TYPE_REACH = 16                                                    # blocks: a second click selects its type this near (#743)
WAND = "warped_fungus_on_a_stick"     # the selection wand: a second item with its own "used" statistic (#778)
LEFT = "aoe_left"                     # score of a left click with the command stick (Paper plugin, #1788)
RELEASE = 0.45   # seconds without a wand use: the player released the held right click (uses come each 0.2 s, #992)
HOLD = 0.2       # seconds: a held right click sends its next command stick use in this time, so a use with no next use
                 # is a click (on Paper the stick also draws the selection box, #1786)
# Control groups (#779, owner choice #745): carrots on a stick with custom_data {aoe_group:N} in hotbar slots 4..8
# (keys 5-9), with the model of a dye. A shift right click saves the selection as group N, a right click selects it.
GROUPS = {n: (3 + n, dye) for n, dye in enumerate(("red_dye", "yellow_dye", "lime_dye", "light_blue_dye",
                                                     "magenta_dye"), 1)}   # group: hotbar slot, item model
GROUP_GIVE = 20                                                    # clicks() calls between two checks of the items
SNEAK = '{type:"minecraft:entity_properties",entity:"this",predicate:{flags:{is_sneaking:true}}}'
MARK = {"go": "[0.2,1.0,0.2]", "attack": "[1.0,0.15,0.15]"}       # dust colors of the order marker (#796): green, red
SIEGE_GLOW = 3                                                     # seconds of the glow of an attacked building (#991)
MARK_POINTS = 12                                                   # dust points on the ring of the order marker
# The pointing mark (#989): a smaller ring than the order marker, in the color of the target under the crosshair.
POINT = {"own": "[0.3,0.7,1.0]", "enemy": "[1.0,0.15,0.15]", "resource": "[1.0,0.85,0.2]", "ground": "[0.9,0.9,0.9]"}
POINT_POINTS, POINT_SCALE, POINT_GROW = 8, 0.8, 0.05            # dust points, least scale, scale per block away
WHERE_PAGE = 40                                                    # units in one answer of `aoe where` (AoePlugin)
# The look and sound of one gather step at the resource (#592): block particles and a vanilla sound. A villager has
# no arm swing, so it turns to the resource (`rotate ... facing`). 26.3 block particles take
# `{id:...,Properties:{...}}`, not `Name`.
WORK_LOOK = {"wood": ("minecraft:oak_log", "minecraft:block.wood.hit"),
             "food": ("minecraft:sweet_berry_bush[age=3]", "minecraft:block.sweet_berry_bush.pick_berries"),
             "farm": ("minecraft:wheat[age=7]", "minecraft:item.hoe.till"),
             "hunt": ("minecraft:red_wool", "minecraft:block.wool.hit"),
             "fish": ("minecraft:water", "minecraft:entity.fishing_bobber.splash"),
             "gold": ("minecraft:gold_ore", "minecraft:block.stone.hit"),
             "stone": ("minecraft:stone", "minecraft:block.stone.hit")}
EVENTS = {"idle": "idle", "to_tree": "walk", "chop": "chop", "to_drop": "carry",    # state -> event in the log
          "to_site": "walk", "build": "build", "to_rally": "walk", "to_prey": "walk", "hunt": "hunt",
          "to_repair": "walk", "repair": "build"}


def breach(g, fort):
    """True when the villagers of g may attack the enemy building fort: a wall, a gate or a tower, after a technology
    with the key "breach" (Siegecraft of Antiquity Mode, #3916)."""
    import combat  # combat imports this module
    name = g.fort_names.get(fort, "")
    if not any(train.value("breach", t) for t in getattr(g, "techs", ())):
        return False
    s = combat.wall(name, 0) if name in combat.WALLS else combat.stats(name)
    return bool({combat.WALL, combat.STONE} & set(s.classes)) or name.endswith("_TOWER")


def only(who, *filters):
    """The selector who ("@a" or "@a[team=p2]") with more filters: only("@a[team=p2]", "name=!Alex")."""
    return who[:-1] + "," + ",".join(filters) + "]" if who.endswith("]") else who + "[" + ",".join(filters) + "]"


def has_mode(g, name):
    """True when the game mode name is on: the --mode of g, or a mode on top of it (g.modes: --regicide,
    --sudden-death, --empire-wars, the AoE2 "Advanced Settings", #2490)."""
    return getattr(g, "mode", None) == name or name in getattr(g, "modes", ())


def allied(players, a, b):
    """True when AoE2 players a and b are allies: the same player, or the same team number of the players of
    aoe2mc.json (`team`). A player with no team is an enemy of all other players (#1312)."""
    t = (players.get(str(a)) or {}).get("team")
    return a == b or t is not None and t == (players.get(str(b)) or {}).get("team")


def allies_command(players):
    """The plugin command that makes the allied players of aoe2mc.json (`team`) one side (AoePlugin.allied, #1315):
    "aoe allies p1,p3 p2,p4", or "aoe allies -" with no alliance."""
    teams = {}
    for n, p in sorted(players.items(), key=lambda e: int(e[0])):
        if p.get("team") is not None:
            teams.setdefault(p["team"], []).append(f"p{n}")
    return "aoe allies " + (" ".join(",".join(t) for t in teams.values() if len(t) > 1) or "-")


def neutral_command(players):
    """The plugin command of the neutral stances of aoe2mc.json (`neutral`, AoePlugin.calm, #1645): "aoe neutral
    p1:p2,p3 p2:p1", or "aoe neutral -" with none. The units of p1 do not attack those of p2 and p3 by themselves."""
    return "aoe neutral " + (" ".join(f"p{n}:" + ",".join(f"p{m}" for m in p["neutral"])
                                      for n, p in sorted(players.items(), key=lambda e: int(e[0])) if p.get("neutral"))
                             or "-")


def hunt_food(name):
    """The food of a hunted animal (HUNT_FOOD), else 0."""
    return HUNT_FOOD.get("COW" if name.startswith("COW_") else name, 0)


def predator(name):
    """True for a predator (an "aggressive" animal of data/animals.jsonl: wolves, big cats, bears): villagers can kill it,
    and it has no food (#2310)."""
    return (animal(name) or ("",))[0] == "aggressive"


def herdable(name):
    """True for a herdable animal (HERDS): an own one takes move orders (#1791)."""
    return ("COW" if name.startswith("COW_") else name) in HERDS


def group_item(n, units=0):
    """The hotbar item of control group n with units saved units: its name and lore say how to use it (#1812)."""
    name, lore = ((f"Group {n}: {units} unit{'s' * (units != 1)}", "Right click: select · Shift + right click: save again")
                  if units else (f"Group {n} (empty)", "Shift + right click: save the selection"))
    return (f'minecraft:carrot_on_a_stick[item_model="minecraft:{GROUPS[n][1]}",item_name="{name}",lore=["{lore}"],'
            f"custom_data={{aoe_group:{n}}}]")


class Map:
    """The block grid of aoe2mc.json: where a unit can stand, the trees and the drop sites of a player."""

    def __init__(self, data, player=1):
        self.T = data["tile_size"]
        self.ground = [[None if v == "-" else int(v) for v in row.split()] for row in data["ground"]]
        self.n = len(self.ground)
        self.blocked, self.trees, self.feet, self.woods, self.bushes = set(), {}, {}, {}, {}
        self.drops = {r: [] for r in (*DROP_SITES, "meat")}            # resource -> footprints of the drop sites
        self.mines = {r: {} for r, _, _ in MINES.values()}             # resource -> {tile: amount}
        self.mine_at = {}                                              # block cell -> tile of its mine
        self.farms, self.farm_at = {}, {}                              # farm tile -> food; block cell -> farm tile
        self.farm_food, self.own_farms = FARM_FOOD, set()              # food of a new farm (FARM_TECHS), own farm tiles
        self.pastures = set()                                          # farm tiles that are pastures (#4118)
        self.carcasses = {}                                            # tile -> food of the carcasses of hunts (#1058)
        self.herds = set()                                             # carcass tiles of herdable animals (HERDS)
        self.rot = {}                                                  # carcass tile -> food per game second (DECAY)
        self.fish, self.shore = {}, set()                              # tile -> food of a fish (#1283), shore fish
        self.oysters = set()                                           # the fish tiles that hold gold (OYSTERS, #2465)
        self.fish_mobs, self.docks = {}, []                            # tile -> mob of a fish; own dock cells (#1384)
        self.traps = {}                                                # own fish trap tile -> its cells (#1438)
        civ = None if data.get("full_tech_tree") else data.get("players", {}).get(str(player), {}).get("civ")   # #2354
        self.trap_food = round(TRAP_FOOD * civs.value("trap_food", civ, 1))   # food of a new own fish trap (Malay, #2333)
        self.farm_food += civs.value("farm_food", civ, 0)              # more food of a new own farm (Sumerians, #4444)
        self.aura = civs.AURA.get(civ, {})                             # Thracians (#2378)
        self.auras = []                                                # the cells of own aura buildings
        for o in data["objects"]:
            if o["kind"] == "building" and "footprint" in o:           # not the drawn monument (hill.mark, #3692)
                x0, z0, x1, z1 = o["footprint"]
                self.building(o["name"], (x0, x1, z0, z1), (int(o["tile"][0]), int(o["tile"][1])) if "tile" in o
                              else None, o["player"] == player, o.get("open", ()))
            elif o["kind"] == "other" and o["name"] in FISH_FOOD:      # a fish is passable: no barrier
                tile = int(o["tile"][0]), int(o["tile"][1])
                self.fish[tile] = FISH_FOOD[o["name"]]
                self.fish_mobs[tile] = object_mob(o["name"])
                if o["name"] in SHORE_FISH:                            # the tiles of the shore fish
                    self.shore.add(tile)
                if o["name"] in OYSTERS:
                    self.oysters.add(tile)
            elif o["kind"] == "other" and not any(k in o["name"] for k in PASSABLE_OBJECTS):
                tile = int(o["tile"][0]), int(o["tile"][1])
                if o["name"] in MINES:                                 # a mine at x.0 covers 2 tiles
                    res, amount, _ = MINES[o["name"]]
                    self.mines[res][tile] = amount + o.get("resource_delta", 0)   # resource_delta of a random map (#4429)
                    self.feet[tile] = object_footprint({"name": o["name"], "x": o["tile"][0], "y": o["tile"][1]}, self.T)
                    self.mine_at.update(dict.fromkeys(self.spot(tile), tile))
                    self.blocked |= self.spot(tile)
                    continue
                self.blocked |= self.cells(tile)
                if "FRUIT_BUSH" in o["name"] or "FORAGE" in o["name"]:
                    self.bushes[tile] = BUSH_FOOD
                if "TREE" in o["name"]:
                    self.trees[tile] = TREE_WOOD
                    self.feet[tile] = object_footprint({"name": o["name"], "x": o["tile"][0], "y": o["tile"][1]}, self.T)
                    kind = tree_kind(o["name"])                # log and leaves of the felled trunk (None: no crown)
                    self.woods[tile] = ("minecraft:bamboo_block", None) if kind == "bamboo" else \
                        ("minecraft:oak_log", None) if kind == "dead" else \
                        (f"minecraft:{WOODS.get(kind, 'oak')}_log", f"minecraft:{WOODS.get(kind, 'oak')}_leaves[persistent=true]")

    def heights(self, cells):
        """The ground heights around cells (at least one)."""
        return [y for x, z in self.around(cells) if (y := self.y(x, z)) is not None] or [0]

    def emptied(self, cells):
        """The cells of an empty mine or bush are free ground again, at the lowest height around them (Gather.dig,
        Gather.berries; savegame.load for the ones that were empty at the save, #2453)."""
        y = min(self.heights(cells))
        for x, z in cells:
            self.ground[z][x] = y
            self.mine_at.pop((x, z), None)
        self.blocked -= set(cells)

    def building(self, name, rect, tile, own, open_cells=()):
        """Add a building with the block footprint rect = (x0, x1, z0, z1) and its center tile. A farm is ground
        that a farmer stands on; own buildings are drop sites. Construction sites call it when they are complete.
        open_cells: the cells that units walk through (under a town center, #865)."""
        x0, x1, z0, z1 = rect
        cells = {(x, z) for x in range(x0, x1) for z in range(z0, z1)}
        if name == "PASTURE":                                          # a farm in a fenced building: the herders stand
            self.farms[tile], self.feet[tile] = PASTURE["food"], rect   # next to it, and its yurt takes their food
            self.pastures.add(tile)
            self.farm_at.update(dict.fromkeys(cells, tile))
        if "FARM" in name:                                             # no barriers: the farmer stands on it
            self.farms[tile], self.feet[tile] = self.farm_food, rect
            if own:
                self.own_farms.add(tile)
            self.farm_at.update(dict.fromkeys(cells, tile))
            return
        self.blocked |= cells - {tuple(c) for c in open_cells}
        if own and "FISH_TRAP" in name and tile:                       # the food of the fishing ships (#1438)
            self.fish[tile], self.traps[tile] = self.trap_food, cells
        if own:
            self.drop_site(name, cells)
        if own and "DOCK" in name:                                     # the drop site of the fishing ships (#1384)
            self.docks.append(cells)

    def drop_site(self, name, cells):
        """Add the cells of an own drop site to the drops of each resource that building name takes."""
        for r, names in [*DROP_SITES.items(), ("meat", MEAT_SITES)]:
            if any(k in name for k in names) or r in self.aura.get("resources", ()) and name in self.aura["buildings"]:
                self.drops[r].append(cells)
        if name in self.aura.get("buildings", ()):
            self.auras.append(cells)

    def unbuild(self, rect, y):
        """Undo Map.building for a fallen own building with block footprint rect = (x0, x1, z0, z1): its cells are ground
        again at height y (the bottom of its box), and no drop site, dock or aura is left there (#3009)."""
        cells = {(x, z) for x in range(rect[0], rect[1]) for z in range(rect[2], rect[3])}
        for r in self.drops:
            self.drops[r] = [d for d in self.drops[r] if d != cells]
        self.docks = [d for d in self.docks if d != cells]
        self.auras = [d for d in self.auras if d != cells]
        self.blocked -= cells
        for x, z in cells:
            self.ground[z][x] = y

    def cells(self, tile):
        T = self.T
        return {(x, z) for x in range(tile[0] * T, tile[0] * T + T) for z in range(tile[1] * T, tile[1] * T + T)}

    def spot(self, tile):
        """The cells of a resource: the footprint of a mine or a farm, else the tile."""
        if tile in self.farms or any(tile in m for m in self.mines.values()):
            x0, x1, z0, z1 = self.feet[tile]
            return {(x, z) for x in range(x0, x1) for z in range(z0, z1)}
        return self.cells(tile)

    def resource(self, tile):
        """The resource of the tile of a tree, bush, mine or fish (an oyster: gold)."""
        if tile in self.oysters:
            return "gold"
        return next((r for r, m in self.mines.items() if tile in m),
                    "food" if tile in self.bushes or tile in self.farms or tile in self.carcasses or tile in self.fish
                    else "wood")

    def y(self, x, z):
        return self.ground[z][x] if 0 <= x < self.n and 0 <= z < self.n else None

    def free(self, x, z):
        return self.y(x, z) is not None and (x, z) not in self.blocked

    def wet(self, x, z):
        """True for a water cell where a ship can be: in the map, no ground and no building (a dock, #866)."""
        return 0 <= x < self.n and 0 <= z < self.n and self.ground[z][x] is None and (x, z) not in self.blocked

    def sea(self, x, z, reach=16):
        """The y of a boat on the water cell (x, z): one block under the lowest land next to the water within reach
        blocks (the shore is 1 to 2 blocks above the water surface, #166). A boat floats up or falls on the water."""
        for r in range(1, reach + 1):
            ys = [y for d in range(-r, r + 1) for c in ((x + d, z - r), (x + d, z + r), (x - r, z + d), (x + r, z + d))
                  if (y := self.y(*c)) is not None]
            if ys:
                return float(min(ys) - 1)
        return float(min((y for row in self.ground for y in row if y is not None), default=64) - 1)

    def around(self, cells, water=False):
        """The free cells next to a group of cells (a tree tile, a footprint); water: the water cells (wet)."""
        ok = self.wet if water else self.free
        return {(x + dx, z + dz) for x, z in cells for dx, dz in STEPS if ok(x + dx, z + dz)} - cells

    def front(self, rect, mounted=False, water=False):
        """The spawn cells of a unit trained at the building with block footprint rect: the free cells next to it,
        south side first, the middle first. A mounted unit (a horse with a rider) one cell farther out: the rider
        sits about 0.7 blocks behind the middle of the horse, so next to the walls its head is in them (#767).
        water: the water cells, for a ship of a dock (#866)."""
        x0, x1, z0, z1 = rect
        cells = {(x, z) for x in range(x0, x1) for z in range(z0, z1)}
        ring = self.around(cells, water)
        if mounted and not water:
            ring = {c for c in self.around(cells | ring) if all(self.free(c[0] + dx, c[1] + dz) for dx, dz in STEPS)}
        return sorted(ring, key=lambda c: (abs(c[1] - z1 - mounted), abs(2 * c[0] + 1 - x0 - x1), c))

    def path(self, start, goals, limit=None, water=False):
        """Shortest path (list of cells after start) to one of goals. 8 neighbours, no cut corners, steps of at
        most 1 block up or down. A* with the distance to the box of the goals. None: no path, or no path after
        `limit` cells (a far or unreachable goal on a large map). water: on water cells (wet), for a ship (#866)."""
        ok = self.wet if water else self.free
        if not goals:
            return None
        gx0, gx1 = min(x for x, _ in goals), max(x for x, _ in goals)
        gz0, gz1 = min(z for _, z in goals), max(z for _, z in goals)

        def h(x, z):
            dx, dz = max(gx0 - x, 0, x - gx1), max(gz0 - z, 0, z - gz1)
            return max(dx, dz) + 0.414 * min(dx, dz)
        dist, prev, todo, seen = {start: 0}, {}, [(h(*start), 0, start)], 0
        while todo:
            _, d, c = heapq.heappop(todo)
            d = -d                                                     # equal sums: the longest walk first
            if c in goals:
                out = []
                while c != start:
                    out.append(c)
                    c = prev[c]
                return out[::-1]
            if d > dist[c]:
                continue
            seen += 1
            if limit and seen > limit or seen == CLOSED and self.closed(start, goals, ok, water):
                return None
            x, z = c
            for dx, dz in STEPS:
                n = (x + dx, z + dz)
                if not ok(*n) or c != start and not water and abs(self.y(*n) - self.y(x, z)) > 1:
                    continue
                if dx and dz and not (ok(x + dx, z) and ok(x, z + dz)):
                    continue
                nd = d + (1.414 if dx and dz else 1)
                if nd < dist.get(n, 1e9):
                    dist[n], prev[n] = nd, c
                    heapq.heappush(todo, (nd + h(*n), -nd, n))
        return None

    def closed(self, start, goals, ok, water=False, cap=None):
        """True when the goals are in a closed region of fewer than cap cells without start: a flood from the goals
        (the steps of path() are the same both ways) ends before cap cells. path() stops then after CLOSED cells: a
        search to an enclosed goal looked at all PATH_CELLS cells, 0.7 s each, and an order of 13 units of de-64.3
        held the live replay for 8 s (#2881). A flood before each search made the many short searches slow."""
        todo, cap = [c for c in goals if ok(*c)], cap or 2 * CLOSED
        seen = set(todo)
        while todo:
            x, z = todo.pop()
            for dx, dz in STEPS:
                n = (x + dx, z + dz)
                if n == start and (not dx or not dz or ok(x + dx, z) and ok(x, z + dz)):
                    return False                                    # a step from start ignores the height (path())
                if n in seen or not ok(*n) or not water and abs(self.y(*n) - self.y(x, z)) > 1 or \
                        dx and dz and not (ok(x + dx, z) and ok(x, z + dz)):
                    continue
                if len(seen) >= cap:
                    return False
                seen.add(n)
                todo.append(n)
        return True

    def pick_ground(self, eye, d, reach=64):
        """The block cell (x, z) of the ground that the ray from eye in direction d hits first, or None."""
        for k in range(1, reach * 4):
            x, y, z = (eye[i] + d[i] * k / 4 for i in range(3))
            bx, bz = math.floor(x), math.floor(z)
            if not (0 <= bx < self.n and 0 <= bz < self.n):
                return None
            g = self.y(bx, bz)
            if g is not None and y < g:
                return bx, bz
        return None

    def pick_tree(self, eye, d, reach=64):
        """The tree, fruit bush, mine or farm tile that the ray from eye in direction d hits first, or None."""
        for k in range(1, reach * 4):
            x, y, z = (eye[i] + d[i] * k / 4 for i in range(3))
            bx, bz = math.floor(x), math.floor(z)
            if not (0 <= bx < self.n and 0 <= bz < self.n):
                return None
            tile = bx // self.T, bz // self.T
            g = self.y(bx, bz)
            if tile in self.trees and (g is None or y < g + 12) or tile in self.bushes and (g is None or y < g + 2):
                return tile
            if (bx, bz) in self.mine_at and (g is None or y < g + 1):    # "ground" over a mine is its top
                return self.mine_at[bx, bz]
            if (bx, bz) in self.farm_at and g is not None and y < g + 0.5:     # the crop on the farm
                return self.farm_at[bx, bz]
            if g is not None and y < g:                                # the ray hits the ground or a building
                return None
        return None


def direction(yaw, pitch):
    """View direction of a Minecraft rotation (yaw 0 = south, +z; 90 = west; pitch 90 = down)."""
    y, p = math.radians(yaw), math.radians(pitch)
    return -math.sin(y) * math.cos(p), -math.sin(p), math.cos(y) * math.cos(p)


def pick_unit(eye, d, units, reach=64, radius=0.8):
    """The unit (key of units: {key: (x, y, z) of the feet}) nearest to the eye on the ray, or None."""
    best = None
    for key, (x, y, z) in units.items():
        v = (x - eye[0], y + 1 - eye[1], z - eye[2])
        t = sum(v[i] * d[i] for i in range(3))
        if 0 < t < reach and math.dist(v, [t * d[i] for i in range(3)]) < radius and (best is None or t < best[0]):
            best = t, key
    return best and best[1]


def profession(uuid, job):
    """The command that gives villager uuid the Minecraft profession job: the clothes change at once. A new profession
    clears the trade list, so the command sets it empty again: no trade menu on a right click (#988)."""
    return f'data merge entity {uuid} {{VillagerData:{{profession:"minecraft:{job}"}},Offers:{{Recipes:[]}}}}'


def job_of(m, tile):
    """The AoE2 task (`LUMBERJACK` ..., units.VILLAGER_JOBS) of a villager at the resource on tile of gather.Map m."""
    res = m.resource(tile)
    return "FARMER" if tile in m.farms else "HUNTER" if tile in m.carcasses else "OYSTER" if tile in m.oysters else \
        "FISHERMAN" if tile in m.fish else \
        {"wood": "LUMBERJACK", "food": "FORAGER"}.get(res) or next(j for r, _, j in MINES.values() if r == res)


def fish_kind(m, tile):
    """The gather kind of a fish on tile of gather.Map m: "oyster" (gold, #2465), "fish", else None."""
    return "oyster" if tile in m.oysters else "fish" if tile in m.fish else None


def military(name):
    """True for an AoE2 unit that fights: not a villager, monk, king, trade or transport unit, and no animal."""
    return not name.startswith(CIVILIANS) and (animal(name) or ("military",))[0] == "military"


def rank(name):
    """The place of a unit in an AoE2 formation, from the front (AoE2 wiki "Unit formation", #3414): 0 melee cavalry,
    camels and elephants, 1 infantry, 2 archers (also on horse), 3 gunpowder foot units, 4 the siege units and the
    civilians (monks, trade carts, kings)."""
    import combat  # combat imports this module
    s = combat.stats(name)
    if "siege" in s.classes or not military(name):
        return 4
    if "gunpowder" in s.classes and "cavalry" not in s.classes:
        return 3
    return 2 if s.range > 0 else 0 if {"cavalry", "camel", "elephant"} & set(s.classes) else 1


def soldier(name):
    """True for a unit that takes move orders as a soldier (g.soldiers), not the jobs of a villager: a military unit, a
    monk, a trade cart, a ship, and the units with the key "orders" or "moves" (train.ORDERS, build.MOVES). One rule for
    Gather.__init__, train.summon and owners.give (#2993): a converted trade cart was a villager."""
    return military(name) or name in monk.MONKS or name.startswith(trade.CART) or replay.ship(name) \
        or name in train.ORDERS or name in build.MOVES


def walk(g, v):
    """Move unit v one cell on its path with /tp, facing the step (g.map, g.command: Gather or replay.Replay)."""
    x, z = v.path.pop(0)
    dx, dz = x + 0.5 - v.pos[0], z + 0.5 - v.pos[2]
    v.pos = (x + 0.5, float(g.map.y(x, z)), z + 0.5)
    v.walked += math.hypot(dx, dz)
    yaw = math.degrees(math.atan2(-dx, dz))
    g.command(f"tp {v.uuid} {v.pos[0]} {v.pos[1]} {v.pos[2]} {yaw:.0f} 0")
    return math.hypot(dx, dz)


class Villager:
    def __init__(self, uuid, pos):
        self.uuid, self.pos = uuid, pos
        self.state, self.path, self.tree, self.load, self.timer = "idle", [], None, 0, 0.0
        self.job = None                                                # profession that the program set
        self.task = None                                               # AoE2 task of the look (#3755): LUMBERJACK ...
        self.walked = 0.0                                              # blocks, for the log
        self.res = "wood"                                              # the resource of the load
        self.site = None                                               # the construction site that it builds
        self.goal, self.moved, self.tries = None, 0.0, 0               # Paper: walk cell, time of the last step, orders
        self.anchor, self.anchor_far = pos, math.inf                   # the place and the distance to the goal of the last progress (#3372)
        self.lap = 0                                                   # step of a farmer over its farm (#591)
        self.prey = None                                               # the UUID of the animal that it hunts (#1058)

    @property
    def cell(self):
        return math.floor(self.pos[0]), math.floor(self.pos[2])


def marker(m, cells, kind, who, colors=MARK, points=MARK_POINTS, scale=1.5):
    """The commands of the order marker (#796) for player selector who: a ring of dust particles on the ground of
    gather.Map m around the block cells. Dust fades in about 1 second by itself (Minecraft feature): no remove command.
    The live replay uses it too (#845), and the pointing mark with other colors, points and scale (#989)."""
    xs, zs = [c[0] for c in cells], [c[1] for c in cells]
    cx, cz = (min(xs) + max(xs) + 1) / 2, (min(zs) + max(zs) + 1) / 2
    r = max(max(xs) - min(xs) + 1, max(zs) - min(zs) + 1) / 2 + 0.5
    y = m.y(int(cx), int(cz))
    y = m.sea(int(cx), int(cz)) if y is None and hasattr(m, "sea") else y or 0    # a ship order on the water (#1383)
    return [f"particle minecraft:dust{{color:{colors[kind]},scale:{scale}}} {cx + r * math.cos(a):.2f} {y + 0.2:.2f} "
            f"{cz + r * math.sin(a):.2f} 0 0 0 0 1 force {who}"
            for a in (2 * math.pi * k / points for k in range(points))]


def glow(uuid, seconds=1):
    """The order marker of an attack on a unit (#796): the target glows for a moment (Minecraft effect)."""
    return f"effect give {uuid} minecraft:glowing {seconds} 0 true"


def siege_mark(uuid, name, hp, who):
    """The mark of an attack order on building `name` (#991), as the flash of AoE2: its target (an invisible slime that
    fills the footprint) glows SIEGE_GLOW seconds (an invisible mob shows its outline in the team color), and the action
    bar of player who shows the name and the hit points (the score aoe_hp of the plugin) of the full hp."""
    text = [{"text": f"Attack: {build.pretty(name)} (", "color": "red"}, {"score": {"name": uuid, "objective": "aoe_hp"}},
            {"text": f"/{hp})"}]
    return [glow(uuid, SIEGE_GLOW), f"title {who} actionbar " + json.dumps(text)]


def level(name, data):
    """The level of the AoE2 starting resources name. "Random" (RANDOM) is one of its levels, the same for each player
    and in each run of the world (a seed from the map, as the other random choices of the game program)."""
    if name not in RANDOM:
        return name
    return random.Random(f"{data.get('map_size')}-{len(data.get('objects', ()))}").choice(RANDOM[name])


class Endless(dict):
    """The stock of the AoE2 starting resources "Infinite" (#2489): a cost does not lower an amount, an income raises it."""

    def __setitem__(self, key, value):
        super().__setitem__(key, max(value, self.get(key, value)))


class Gather:
    """The gather game on a running server (game.command sends one command). Call setup(), then step() in a loop.
    log: a text file that gets one JSON line per event (state change or drop), to measure the timing (#289).
    chop: seconds per unit, one number for all resources or {resource: seconds} ("farm" for farms); default
    WORK_SECONDS, the AoE2 rates at Normal speed (#413). start: the start resources, default START as in AoE2 (#973),
    and NOMAD more for a player with units and no building (#1212); a missing resource starts at 0 ({} for none)."""
    work_on = True                                                     # #3271: work on after a build or a tree; a bot gives its own tasks
    cheats = False                                                     # also for the adapters of Gather.__new__
    aegis = False                                                      # the cheat "aegis": all work is instant (#817)
    beyond = free_techs = noui = False                                 # cheats: repeat and free technologies, no UI (#968)
    sharing = False                                                    # cheat "sharing is caring": income to the allies (#969)
    who = "@a"                                                         # the Minecraft players: "@a[team=pN]" for two people (#1310)
    person = ""                                                        # the name of the click that it handles now (#3486)
    pop_cap = None                                                     # the cheat "my cpu can handle it" (#968): 1000
    ended = None                                                       # "Victory" or "Defeat": run() stops (#819)
    board = "aoe_res"                                                  # the objective of the resources (the sidebar)
    bots = ()                                                          # run() steps them too (bot.Bot, #856)
    peers = ()                                                         # the Gathers of the other people (fog.py, #1631)
    reveal = "normal"                                                  # AoE2 "Reveal map"; "all": no fog (fog.py, #1389)
    speed = 1.0                                                        # times the Normal speed: shorter real steps (#2057)
    later = {}                                                         # the bonus of the first town center (civs.TOWN_CENTER)
    nomad = False                                                      # a Nomad start: no town center yet (#2466)
    challenge = None                                                   # an Art of War challenge (challenge.py, #3900)
    victory = "standard"                                               # AoE2 "Victory"; "conquest": no wonder, no relics (#2316)
                                                                       # "king-of-the-hill": hill.py (#2360)
                                                                       # "time-limit", "score": time_limit.py (#2356)
    mode = "standard"                                                  # AoE2 game mode; "regicide": the King (#2347),
                                                                       # "wonder-race" (#2406)
    modes = frozenset()                                                # the modes on top of it (has_mode, #2490)

    def __init__(self, game, data, player=1, tick=0.25, carry=10, chop=None, log=None, clock=time.monotonic,
                 cheats=False, start=None, resources="standard", pop_limit=None):
        self.game, self.data, self.map, self.player = game, data, Map(data, player), player
        if player != 1:
            self.board = f"aoe_res{player}"                            # its own resources: its team sidebar (#1309)
        self.paper = getattr(game, "kind", None) == "paper"           # walks with the plugin (#437)
        chop = WORK_SECONDS if chop is None else chop
        self.tick, self.carry = tick, carry
        self.chop = dict(chop) if isinstance(chop, dict) else dict.fromkeys(WORK_SECONDS, chop)
        self.log, self.clock, self.t0 = log, clock, clock()
        self.cheats = cheats                                           # the AoE2 cheat codes in the chat (#816)
        self.pop_limit = pop_limit                                     # AoE2 "Population limit", else train.LIMIT (#2266)
        resources = level(resources, data)
        if start is None:                                              # units, no building: a Nomad start (#1212)
            kinds = {o["kind"] for o in data["objects"] if o.get("player") == player}
            nomad = "unit" in kinds and "building" not in kinds
            base = LEVELS[resources]
            tc = civs.TOWN_CENTER.get(civs.civ(self), {})              # Tupi: with the first town center (#2293)
            self.later, self.nomad = dict(tc) if nomad else {}, nomad
            start = civs.start(self, {r: v + NOMAD.get(r, 0) * nomad + tc.get(r, 0) * (not nomad)
                                      for r, v in base.items()})       # #1269
        self.stock = {**dict.fromkeys(DROP_SITES, 0), **start}             # at the drop sites (#973)
        if resources in INFINITE:
            self.stock = Endless(self.stock)
        self.spare = {}                                                # the fractions of the drop-off bonus (#2111)
        self.units = [o for o in data["objects"] if o["kind"] == "unit" and o["player"] == player
                      and "VILLAGER" in o["name"]]
        self.villagers, self.selections = {}, {}                      # Minecraft name -> selected units (#3486)
        self.soldiers = {o["uuid"]: o["name"] for o in data["objects"] if o["kind"] == "unit"
                         and o["player"] == player and soldier(o["name"])}
        # military units, monks, trade carts and ships of the player: they take move orders (#1243, #1253, #1383)
        self.ships = {}                         # UUID of an own ship -> Villager with its water path (fleet.py, #1383)
        self.enemies = {o["uuid"]: o["name"] for o in data["objects"] if o["kind"] == "unit" and o["player"]
                        and not allied(data.get("players", {}), player, o["player"])}   # no allies (#1312)
        self.prey = {o["uuid"]: o["name"] for o in data["objects"] if o["kind"] == "unit" and o.get("uuid")
                     and o["player"] in (0, player) and (hunt_food(o["name"]) or predator(o["name"]))}
        # animals to hunt (#1058), and the predators that villagers kill (#2310)
        self.flock = {o["uuid"] for o in data["objects"] if o["kind"] == "unit" and o.get("uuid")
                      and o["player"] == player and herdable(o["name"])}   # own herdables: select and move (#1791)
        self.seen, self.dead = {}, {}                                  # hunted animal -> last feet position, carcass tile
        self.players, self.sites = data.get("players", {}), []         # construction sites (#417)
        self.farmers, self.crops = {}, {}                              # farm tile -> UUID of its farmer, wheat age
        self.herders = {}                                              # pasture tile -> UUID of its second herder (#4118)
        self.trunks = {}                                               # tree tile -> logs of its trunk on the ground
        self.seconds = {}                                              # resource -> fraction of civs.EXTRA (#2113)
        self.bushes = {}                                               # bush tile -> the block of its last look
        self.menus = {}                                                # player -> handler of its open menu (#619)
        self.stances = {}                                              # uuid -> stance other than aggressive (#1107)
        self.bar = None                                                # the unit on the boss bar (bossbar.py, #659)
        self.queues, self.trained = {}, {}                             # town center -> its queue, units it trained
        self.techs = set()                                             # the researched technologies (train.TECHS)
        self.repeats = {}                                              # technology -> researches after the first (#968)
        self.rally, self.rallying, self.marks = {}, {}, {}             # building -> rally point, player -> building,
        self.ordering = {}                                             # player -> a pending menu order ("patrol", #3355)
        #                                                                tag of a rally marker -> AoE2 seconds left
        self.pop, self.census, self.shown = 0, 0.0, {}                 # live units, AoE2 seconds since the count, sidebar
        import combat  # combat imports this module
        ground = [r.split() for r in data["ground"]]
        self.forts = {combat.target_uuid(o["footprint"]): combat.building_box(o, ground) for o in data["objects"]
                      if o["kind"] == "building" and o["player"] not in (0, player) and "footprint" in o
                      and o["name"] in combat.BUILDINGS}               # target UUID -> box of an enemy building
        self.fort_names = {combat.target_uuid(o["footprint"]): o["name"] for o in data["objects"]
                           if o["kind"] == "building" and "footprint" in o}   # target UUID -> AoE2 name (#991)
        self.fort_players = {combat.target_uuid(o["footprint"]): o["player"] for o in data["objects"]
                             if o["kind"] == "building" and "footprint" in o}  # target UUID -> owner (bot.forts, #1819)
        self.sieged = set()                                            # the targets of attack orders
        self.ruins = set()                                             # footprints of fallen start buildings (ruins.py)
        self.wands, self.corners = set(), {}                           # players who clicked the wand, player -> corner 1
        self.holds = {}                                                # player -> time of the last wand use of a drag
        self.pending, self.looks = {}, {}                              # player -> (time, look) of a stick use (#1786)
        self.groups, self.grouping, self.calls = {}, {}, 0             # group -> units, player -> (group, shift)
        self.hints = {}                                                # target -> (hint text, time) (hints.py, #798)
        self.pointing = {}                                             # player -> text of its pointed target (#989)
        self.sided = set()                                             # players in the team of the units (#1241)
        self.garrisons, self.entering = garrison.start(self), {}       # building -> units inside, unit -> building (#808)
        self.trade = {}                                                # trade cart -> its trade route (trade.py, #1253)
        self.monk_at, self.heal_time = {}, 0.0                         # monk -> feet at the last heal pass (#1244)
        self.converting, self.faith = {}, {}                           # monk -> conversion order, monk -> rest (#1245)
        self.chance = random.Random(1)                                 # the conversion chance: the same in each run
        monk.relics(self)                                              # the relics of the map and their monks (#1246)

    @property
    def wood(self):
        return self.stock["wood"]

    def command(self, cmd):
        if isinstance(getattr(self, "stock", None), Endless) and cmd.startswith("scoreboard players remove ") \
                and cmd.split()[4:5] == [self.board]:
            return ""                                                  # "Infinite" resources: the sidebar stays (#2489)
        return self.game.command(cmd)

    def pos(self, target):
        m = re.findall(NUMBER, self.command(f"data get entity {target} Pos").rsplit(":", 1)[-1])
        return tuple(map(float, m)) if len(m) == 3 else None

    def color(self):
        """The Minecraft team color of the player (units.TEAM_COLOR)."""
        name = self.data.get("players", {}).get(str(self.player), {}).get("color") or player_color(self.player)
        return TEAM_COLOR.get(name, "white")

    def sidebars(self):
        """The display slots of the resources of the player (#1309): the sidebar of its team color, so each team sees its
        own player; player 1 also the sidebar of all, for a Minecraft player in no team."""
        return ["sidebar"] * (self.player == 1) + [f"sidebar.team.{self.color()}"]

    def show_stock(self):
        """Write each resource of the stock to the board (the sidebar). Each path that sets the stock calls it, so the
        board and the stock never differ (#3111); a cost and a gathered load then add to or remove from both."""
        for r in RESOURCES:
            self.command(f"scoreboard players set {r} {self.board} {self.stock[r.lower()]}")

    def setup(self):
        for cmd in ("scoreboard objectives add aoe_use minecraft.used:minecraft.carrot_on_a_stick",
                    f"scoreboard objectives add aoe_box minecraft.used:minecraft.{WAND}",
                    "scoreboard objectives add aoe_talk minecraft.custom:minecraft.talked_to_villager",
                    f'scoreboard objectives add {self.board} dummy "Resources"'):
            self.command(cmd)
        for cmd in [f'team add p{self.player} "Player {self.player}"', f"team modify p{self.player} color {self.color()}"] \
                + [f"scoreboard objectives setdisplay {slot} {self.board}" for slot in self.sidebars()]:
            self.command(cmd)
        self.show_stock()                                              # the start resources
        self.command(f'scoreboard players display name Idle {self.board} "Idle villagers"')   # a name has no space
        # The players get the side of the units for the attack alerts of the plugin (AoePlugin.side, #1241): the team,
        # not the tag aoe2mc.pN, because cheats.destroy kills and conquest.alive counts the entities with that tag.
        self.command(f"team modify p{self.player} seeFriendlyInvisibles false")   # worlds before #1538: no cube at a building
        if self.who == "@a":                                           # two people: run.py puts each one on its team
            self.command(f"team join p{self.player} @a")
        build.setup(self)
        menu.setup(self)
        flare.setup(self)
        techtree.setup(self)
        if self.paper:
            self.command(f'scoreboard objectives add {LEFT} dummy "Left click"')    # set by the plugin (#1788)
            train.lore(self)                                           # the help lines of the menus (#1160)
            self.command(allies_command(self.data.get("players", {})))   # allies do not shoot each other (#1315)
            self.command(neutral_command(self.data.get("players", {})))  # no automatic attack on neutrals (#1645)
        self.forage()
        if self.paper:
            map_table.setup(self)                                      # the framed minimap (#2586)
        cheats.setup(self)
        bossbar.setup(self)
        for o in self.units:                                           # the entities must be loaded (forceload)
            pos = self.pos(o["uuid"])
            if pos:
                self.villagers[o["uuid"]] = Villager(o["uuid"], pos)
        train.census(self)                                             # the population and the limit (#613)
        self.idle()
        return self

    def forage(self):
        """The start forage bushes of the civilization (civs.BUSHES, Gurjaras: 2 of 175 food, #2293) on the free tiles
        next to the own town center of the map, the south side first: AoE2 puts them under the town center, where here
        the villagers walk through. The blocks of a converted bush: berries around, leaves in the middle, dirt below."""
        count, food = civs.BUSHES.get(civs.civ(self), (0, 0))
        tc = next((o for o in self.data["objects"] if o["kind"] == "building" and o["name"] == "TOWN_CENTER"
                   and o["player"] == self.player), None)
        if not count or tc is None:
            return
        m, T = self.map, self.map.T
        x0, z0, x1, z1 = tc["footprint"]
        tx0, tz0, tx1, tz1 = x0 // T, z0 // T, (x1 - 1) // T, (z1 - 1) // T
        units = {(int(o["tile"][0]), int(o["tile"][1])) for o in self.data["objects"] if o["kind"] == "unit" and "tile" in o}
        ring = [(x, z) for x in range(tx0 - 1, tx1 + 2) for z in range(tz0 - 1, tz1 + 2)
                if not (tx0 <= x <= tx1 and tz0 <= z <= tz1) and (x, z) not in units
                and all(m.free(*c) for c in m.cells((x, z)))]
        ring.sort(key=lambda t: (abs(t[0] - (tx0 + tx1) / 2) + abs(t[1] - (tz0 + tz1) / 2), -t[1], t[0]))
        for tile in ring[:count]:
            m.bushes[tile] = food
            m.blocked |= m.cells(tile)
            bx, bz = tile[0] * T, tile[1] * T
            for x, z in sorted(m.cells(tile)):
                y = m.y(x, z)
                self.command(f"setblock {x} {y - 1} {z} minecraft:grass_block")
                if x in (bx, bx + T - 1) or z in (bz, bz + T - 1):
                    self.command(f"setblock {x} {y} {z} minecraft:sweet_berry_bush[age=3]")
                else:
                    self.command(f"fill {x} {y} {z} {x} {y + 1} {z} minecraft:oak_leaves[persistent=true]")

    def town_center(self, rect=None):
        """The first own town center is complete (build.rise): the bonus of a Nomad start comes now (civs.TOWN_CENTER,
        Tupi +25 of each resource, #2293), and the unit of the key "nomad_unit" (Huns: a tamed Hunnic Horse in front
        of the town center rect, #2466)."""
        for r, n in sorted(self.later.items()):
            self.stock[r] += n
            self.command(f"scoreboard players add {r.capitalize()} {self.board} {n}")
        self.later = {}
        if self.nomad and rect and (unit := civs.value("nomad_unit", civs.civ(self))) and (cells := self.map.front(rect)):
            x, z = cells[0]
            name = json.dumps({"text": pretty(unit), "color": self.color()})
            self.command(f"summon minecraft:horse {x + 0.5} {self.map.y(x, z)} {z + 0.5} {{Tame:1b,PersistenceRequired:1b,"
                         f"Tags:[\"aoe2mc.p{self.player}\"],CustomName:{name}}}")
        self.nomad = False

    def idle(self):
        """Show the number of idle villagers in the sidebar, as the idle villager button of AoE2 (#744), only when it
        changed."""
        n = sum(v.state == "idle" for v in self.villagers.values())
        if self.shown.get("Idle") != n:
            self.shown["Idle"] = n
            self.command(f"scoreboard players set Idle {self.board} {n}")

    @property
    def selected(self):
        """The selection of Gather.person, the Minecraft player whose click this Gather handles now (#3486): each
        person of one AoE2 player selects and orders on its own, as in AoE2 co-op. A bot and code with no click have
        the person "": the first named person takes that selection over (a setup or a test selects, then a click)."""
        return self.selections_of()[self.person]

    @selected.setter
    def selected(self, units):
        self.selections_of()[self.person] = units

    def selections_of(self):
        """The selections {name: units}, with an entry for Gather.person (see selected)."""
        sel = vars(self).setdefault("selections", {})
        if self.person not in sel:
            sel[self.person] = sel.pop("", set()) if self.person else set()
        return sel

    @property
    def groups(self):
        """The control groups {n: units} of Gather.person (#3490): each person of one AoE2 player has own groups, as in
        AoE2 co-op. As with selected, the first named person takes the groups of the person "" over."""
        own = vars(self).setdefault("person_groups", {})
        if self.person not in own:
            own[self.person] = own.pop("", {}) if self.person else {}
        return own[self.person]

    @groups.setter
    def groups(self, groups):
        vars(self).setdefault("person_groups", {})[self.person] = groups

    def others(self):
        """The units that another person of this Gather has selected: they keep their glow and their tag."""
        return set().union(*(s for n, s in vars(self).get("selections", {}).items() if n != self.person))

    def drop(self, uuid):
        """Unit uuid leaves the selection of each person (a dead unit, a unit of another owner now)."""
        for s in vars(self).get("selections", {}).values():
            s.discard(uuid)

    def voice_class(self, uuid):
        """The class of unit uuid in game/data/sounds.jsonl, or None (#3499)."""
        import combat  # combat imports this module
        if uuid in getattr(self, "ships", {}):
            return "ship"
        if uuid in getattr(self, "villagers", {}):
            return "villager"
        name = getattr(self, "soldiers", {}).get(uuid)
        if name is None:
            return None
        cs = set(combat.STATS[name].classes) if name in combat.STATS else set()
        return "monk" if name == "MONK" else next((v for v, k in (
            ("ship", {"ship", "warship", "fireship"}), ("siege", {"siege", "ram", "heavysiege"}),
            ("cavalry", {"cavalry", "camel", "elephant"}), ("archer", {"archer", "skirmisher"})) if cs & k), "infantry")

    def voice(self, uuid, key="select"):
        """Play the select (or order, #3500) voice of unit uuid to the person who clicked, one line per click as in
        AoE2 DE (#3499)."""
        if (v := VOICES.get(self.voice_class(uuid))) and not self.noui:
            self.command(f"playsound minecraft:{v[key]} voice {self.person or self.who} ~ ~ ~ 1 {v['pitch']}")

    def order_voice(self):
        """Play the order voice of the first selected unit once, for an order of the person (a click, #3500). The
        orders of a bot or of the game program (rally point, next_task, a trigger) do not come here."""
        if self.selected:
            self.voice(min(self.selected), "order")

    def select(self, uuid, voice=True):
        """Select one villager (glowing), as a click in AoE2 does. A click on a military unit adds it to selected
        military units, as a shift click in AoE2 does."""
        keep = {uuid} | (self.selected if uuid in self.soldiers and self.selected <= set(self.soldiers) else set())
        for u in self.selected - keep - self.others():
            self.command(f"data merge entity {u} {{Glowing:0b}}")
            self.command(f"tag {u} remove {SELECT}")
        self.command(f"data merge entity {uuid} {{Glowing:1b}}")
        self.command(f"tag {uuid} add {SELECT}")
        for u in sorted(self.selected ^ keep | {uuid}):                 # the name line shows the selection (#661)
            self.command(f"aoe label {u}")
        self.selected = keep
        if voice:
            self.voice(uuid)
        bossbar.show(self, uuid)                                        # the boss bar of the selection (#659)

    def select_type(self, uuid):
        """Select all own military units with the name of unit uuid within TYPE_REACH blocks of it, as a double
        click in AoE2 does (#743). The other units leave the selection."""
        pos = self.positions([u for u, n in self.soldiers.items() if n == self.soldiers[uuid]])
        if uuid not in pos:
            return
        near = {u for u, p in pos.items() if math.dist(p, pos[uuid]) <= TYPE_REACH} - self.unpickable()
        for u in sorted(self.selected - near - self.others()):
            self.command(f"data merge entity {u} {{Glowing:0b}}")
            self.command(f"tag {u} remove {SELECT}")
            self.command(f"aoe label {u}")
        self.selected &= near
        for u in sorted(near - self.selected - {uuid}) + [uuid]:      # the clicked unit last: its boss bar
            self.select(u, voice=u == uuid)

    def choose(self, uuids, last=None):
        """Make uuids the selection: the other units leave it, the new ones glow. The boss bar shows unit last."""
        for u in sorted(self.selected - uuids - self.others()):
            self.command(f"data merge entity {u} {{Glowing:0b}}")
            self.command(f"tag {u} remove {SELECT}")
        for u in sorted(uuids - self.selected):
            self.command(f"data merge entity {u} {{Glowing:1b}}")
            self.command(f"tag {u} add {SELECT}")
        for u in sorted(self.selected ^ uuids):                        # the name line shows the selection (#661)
            self.command(f"aoe label {u}")
        new, self.selected = uuids - self.selected, set(uuids)
        if new and last is not None:                                   # a pick, not a unit that left (#3499)
            self.voice(last)
        bossbar.show(self, last)

    def box(self, name, cell):
        """A click of player name with the selection wand on the ground cell (#778, owner choice #745). The first click
        sets a corner, the second selects the own units whose feet are in the rectangle of the two corners, as the
        selection box of AoE2: military units win over villagers, and an empty box clears the selection. Between the
        clicks the Paper plugin draws the border of the box to the ground under the look (Border.java, #795). On Paper
        the player holds the right click instead (owner choice A, #992): see drag."""
        if cell is None:
            return
        self.person = name
        if (first := self.corners.pop(name, None)) is None:
            self.corners[name], (x, z) = cell, cell
            self.command(f"particle minecraft:happy_villager {x + 0.5} {(self.map.y(x, z) or 0) + 0.5} {z + 0.5} "
                         f"0.3 0.3 0.3 0 12 force {name}")
            text = "Selection box: look at the other corner and release" if self.paper else \
                "Selection box: click the other corner"
            self.command(f"title {name} actionbar " + json.dumps({"text": text}))
            if self.paper:                                             # the border follows the look (#795)
                color = self.players.get(str(self.player), {}).get("color") or player_color(self.player)
                self.command(f"aoe box {name} {x} {z} {color}")
            return
        if self.paper:
            self.command(f"aoe box-clear {name}")
        (x0, x1), (z0, z1) = sorted((first[0], cell[0])), sorted((first[1], cell[1]))
        pos = {k: v.pos for k, v in self.villagers.items()} | self.positions(list(self.soldiers) + sorted(self.herd()))
        inside = {u for u, p in pos.items() if x0 <= p[0] < x1 + 1 and z0 <= p[2] < z1 + 1} - self.unpickable()
        pick = inside & self.soldiers.keys() or inside - self.flock or inside   # herdables come last (#1791)
        self.choose(pick, min(pick, default=None))
        self.command(f"title {name} actionbar " + json.dumps({"text": f"Selected: {len(pick)} units"}))

    def drag(self, name, cell):
        """A wand use on Paper: a held right click sends a use each 4 ticks, so the first use sets corner 1 and the next
        ones only show that the player still holds the button. release ends the drag (#992)."""
        if name not in self.holds:
            self.box(name, cell)
            if name not in self.corners:                               # no ground under the look: no drag
                return
        self.holds[name] = self.clock()

    def release(self):
        """End the drags with no wand use for RELEASE seconds: the cell under the look is corner 2, as the release of
        the mouse in AoE2. A release on corner 1 cancels the box (a click with no drag)."""
        for name in sorted(n for n, t in self.holds.items() if self.clock() - t > RELEASE):
            del self.holds[name]
            cell = (look := self.look(name)) and fleet.pick(self, *look)   # also on deep water (#2060)
            if cell and cell != self.corners.get(name):
                self.box(name, cell)
                continue
            self.corners.pop(name, None)
            self.command(f"aoe box-clear {name}")
            self.command(f"title {name} actionbar " + json.dumps({"text": "Selection box: cancelled"}))

    def look(self, name):
        """(eye, direction) of player name, or None."""
        pos = self.pos(name)
        rot = re.findall(NUMBER, self.command(f"data get entity {name} Rotation").rsplit(":", 1)[-1])
        if not pos or len(rot) != 2:
            return None
        return (pos[0], pos[1] + 1.62, pos[2]), direction(*map(float, rot))

    def attack(self, target, units=None):
        """Send the selected military units (or units: a queue of #3516) to attack the unit target, with their AoE2
        walk speed (ai.py). A monk does not attack: it converts (monk.convert_order, #1245) or stays."""
        import ai  # ai imports this module
        sel = self.selected if units is None else set(units)
        monks = {u for u in sel if self.soldiers.get(u) in monk.MONKS}
        converts = {m for m in monks if self.converting.get(m, [None])[0] == target}   # the order of the same click
        self.new_order(sel - converts)
        trebs = {u for u in sel if self.soldiers.get(u) == trebuchet.NAME}
        for u in sorted(trebs):                                        # it unpacks first (#1351)
            trebuchet.unpack(self, u, target)
        fleet.attack(self, {u for u in sel if replay.ship(self.soldiers.get(u, ""))}, target)   # (#1386)
        for u in sorted(sel - monks - trebs):
            self.command(ai.speed_command(u, self.soldiers[u], self.map.T, NORMAL * train.speed(self, self.soldiers[u], u)))
        record.ordered(self, "order", sel, target=target)              # Record Game (#2649)
        if not monks and not trebs and units is None:
            return self.command(f"aoe attack @e[tag={SELECT}] {target}")
        return [self.command(f"aoe attack {u} {target}") for u in sorted(sel - monks - trebs)]

    def monks(self):
        """The selected monks."""
        return {u for u in self.selected if self.soldiers.get(u) in monk.MONKS}

    def positions(self, uuids):
        """{uuid: feet position} of the loaded units; a dead unit is not in it."""
        return {u: p for u in uuids if (p := self.pos(u))}

    def seen_tiles(self, pos=None, alive=None):
        """The tiles (x, y) in the AoE2 line of sight of the own units and complete buildings (#1388, the
        fog of war: epic #1387), with replay.seen. pos: {uuid: feet position} of the own units, else from the server.
        alive: the UUIDs of the live entities (Gather.where); an own building whose target is not in it is destroyed
        and sees nothing (#1470). None: all buildings stand."""
        names = dict.fromkeys(self.villagers, "VILLAGER") | self.soldiers
        pos = self.positions(list(names)) if pos is None else pos
        mobs = [types.SimpleNamespace(name=names[u], player=self.player, pos=p) for u, p in pos.items() if u in names]
        placed = [(o["name"], tuple(o["footprint"][i] for i in (0, 2, 1, 3)), 1.0) for o in self.data["objects"]
                  if o["kind"] == "building" and o["player"] == self.player and "footprint" in o]
        placed += [(s["name"], s["footprint"], s["progress"]) for s in self.sites
                   if s["progress"] >= 1]                              # a foundation sees nothing until complete (#4176)
        if alive is not None:                                          # only a complete building of BUILDINGS or
            import combat  # WALLS has a target (combat.setup, build.target)
            hp = combat.BUILDINGS.keys() | combat.WALLS.keys()
            placed = [(n, fp, k) for n, fp, k in placed
                      if n not in hp or k < 1 or combat.target_uuid([fp[i] for i in (0, 2, 1, 3)]) in alive]
        import combat  # combat imports this module
        techs = set(getattr(self, "techs", ()))
        printing = monk.PRINTING * ("BLOCK_PRINTING" in techs) + sum(train.value("reach", t, 0) for t in techs)   # the monks see more (#1475, #3988)
        watch = sum(combat.WATCH if w is True else w for n, w in WATCH_ROWS.items() if n in techs)   # (#1454, #1579; a number: tiles, #3915)
        lit = {n for n, _, _ in placed} - combat.WALLS.keys() - {t['name'] for t in ROWS if t.get('dark')}   # as in AoE2
        return replay.seen(mobs, [(self.player, n, fp) for n, fp, _ in placed], self.player, self.map.T,
                           lambda n: combat.sight(n) + printing * (n in monk.MONKS) + watch * (n in lit)
                           + civs.SIGHT.get(civs.civ(self), {}).get(n, 0)   # the Chinese town center (#2118)
                           + train.sight_more(techs, n, combat.stats(n))    # Engineering (#3981)
                           + civs.sight_units(self, n, combat.stats(n)))    # Macedonian units (#4448)

    def task(self, v, name):
        """Give the villager the look of its AoE2 task (`LUMBERJACK` ...), with the table of the converter."""
        job = dict(VILLAGER_JOBS).get(name, IDLE_JOB)
        v.task = name                                                  # also when the profession stays (FORAGER, FARMER)
        if v.job != job:                                             # a merge keeps the level and the type
            v.job = job
            self.command(profession(v.uuid, job))

    def send(self, tile, who=None):
        """Send the selected villagers (or the villagers who) to the tree, the fruit bush, the mine or the farm on tile.
        A farm takes one farmer: the next villagers go to the nearest free farms, or stop."""
        res, job = self.map.resource(tile), job_of(self.map, tile)
        who = (self.selected if who is None else who) & self.villagers.keys()   # a scout cannot (#589)
        self.new_order(who)
        for u in sorted(who):
            v = self.villagers[u]
            to = tile
            if tile in self.map.farms:
                v.tree = None
                free = [t for t, k in self.map.farms.items() if k > 0 and not self.tended(t)]
                to = tile if tile in free else min(free, key=lambda t: math.dist(t, tile), default=None)
                if to is None:
                    self.set(v, "idle")
                    continue
                (self.herders if to in self.farmers else self.farmers)[to] = u   # a pasture: a second one (#4118)
            self.task(v, job)
            if v.load and v.res != res:
                v.load = 0                                             # AoE2 drops a load of another resource
            v.res, v.tree, v.site = res, to, None
            self.go(v, "to_tree", self.goals(to))

    def build(self, site, who=None):
        """Send the selected villagers (or the villagers who) to build the construction site, with the builder look
        (#418). They keep their load, as in AoE2."""
        x0, x1, z0, z1 = site["footprint"]
        goals = self.map.around({(x, z) for x in range(x0, x1) for z in range(z0, z1)})
        who = (self.selected if who is None else who) & self.villagers.keys()   # not a scout (#589)
        self.new_order(who)
        for u in sorted(who):
            v = self.villagers[u]
            v.tree, v.site = None, site
            self.task(v, "BUILDER")
            self.go(v, "to_site", goals)

    def row_busy(self, site):
        """An earlier site of the row of site is not complete: its builders come to site after it (#1805)."""
        return any(s.get("row") == site.get("row") and s["progress"] < 1 for s in self.sites[:self.sites.index(site)])

    def hunt(self, prey, who=None):
        """Send the selected villagers (or the villagers who) to hunt the animal prey, with the hunter look (#1058)."""
        if prey in self.forts:                                         # a wall or tower: next to it (breach, #3916)
            who = (self.selected if who is None else who) & self.villagers.keys()
            self.new_order(who)
            x0, _, z0, x1, _, z1 = self.forts[prey]
            cells = self.map.around({(x, z) for x in range(x0, x1 + 1) for z in range(z0, z1 + 1)})
            for u in sorted(who):
                v = self.villagers[u]
                v.tree, v.site, v.prey = None, None, prey
                self.go(v, "to_prey", cells or {(x0, z0)})
            return
        if not (pos := self.pos(prey)):
            return
        self.seen[prey] = pos
        cell = math.floor(pos[0]), math.floor(pos[2])
        who = (self.selected if who is None else who) & self.villagers.keys()
        self.new_order(who)
        for u in sorted(who):
            v = self.villagers[u]
            self.task(v, "HUNTER")
            if v.load and v.res != "food":
                v.load = 0                                             # AoE2 drops a load of another resource
            v.res, v.tree, v.site, v.prey = "food", None, None, prey
            self.go(v, "to_prey", self.map.around({cell}) or {cell})

    def strike(self, v):
        """A hunter hits its animal once per AoE2 villager reload (VILLAGER_HIT), with aegis at once and to death
        (#817). The `damage` source is the villager, so a boar hits back. A dead animal leaves its carcass on the tile
        of its last place, and its hunters gather it: the work of a bush."""
        if v.prey in self.forts:                                      # a wall or tower (breach, #3916)
            return self.batter(v)
        if v.prey not in self.dead and (pos := self.pos(v.prey)):
            self.seen[v.prey] = pos
            if math.dist((pos[0], pos[2]), (v.pos[0], v.pos[2])) > 3:   # it ran away: follow it
                self.hunt(v.prey, {v.uuid})
                return
            v.timer += self.tick
            if self.aegis or v.timer >= VILLAGER_HIT[1] / NORMAL:
                v.timer = 0.0
                self.command(f"rotate {v.uuid} facing entity {v.prey}")
                hit = VILLAGER_HIT[0] + civs.predator_hit(self) * predator(self.prey.get(v.prey, ""))
                self.command(f"damage {v.prey} {1000 if self.aegis else hit} minecraft:mob_attack by {v.uuid}")
                if not re.search(r" 0\.0f$", self.command(f"data get entity {v.prey} Health")):
                    return                                             # a dead mob stays 20 ticks: no more hits
            else:
                return
        if v.prey in self.prey:                                        # dead: the first hunter that sees it makes the carcass
            x, _, z = self.seen.get(v.prey, v.pos)
            tile = int(x // self.map.T), int(z // self.map.T)
            name = self.prey.pop(v.prey)
            if hunt_food(name):                                        # a predator leaves no food (#2310)
                self.dead[v.prey] = tile
                self.map.carcasses[tile] = self.map.carcasses.get(tile, 0) + hunt_food(name)
                self.map.rot[tile] = DECAY.get("COW" if name.startswith("COW_") else name, 0) * civs.decay(self)
                self.body(tile)
                if herdable(name):
                    self.map.herds.add(tile)
        v.tree, v.prey, v.path = self.dead.get(v.prey), None, []
        self.set(v, "to_tree" if v.tree else "idle")                   # it stands at the carcass: the next step gathers

    def batter(self, v):
        """A villager hits the enemy wall or tower v.prey once per AoE2 villager reload (#3916). The `damage` source is
        the villager: the plugin gives the AoE2 damage of the villager (AoePlugin.onHit). A fallen building leaves
        self.forts (fall): the villager stops."""
        x0, _, z0, x1, _, z1 = self.forts[v.prey]
        if max(x0 - v.pos[0], v.pos[0] - x1 - 1, z0 - v.pos[2], v.pos[2] - z1 - 1) > 2:   # not next to it: walk again
            return self.hunt(v.prey, {v.uuid})
        v.timer += self.tick
        if self.aegis or v.timer >= VILLAGER_HIT[1] / NORMAL:
            v.timer = 0.0
            self.command(f"rotate {v.uuid} facing entity {v.prey}")
            self.command(f"damage {v.prey} {1000 if self.aegis else VILLAGER_HIT[0]} minecraft:mob_attack by {v.uuid}")

    def decay(self, dt):
        """The carcasses lose food at their AoE2 rate (Map.rot, AoE2 wiki "Hunt": "decay ... begins to subtract from the
        total food amount as soon as the animal is killed", also while villagers gather it), dt game seconds (#2310)."""
        for tile, rate in list(self.map.rot.items()):
            food = self.map.carcasses[tile] = max(0, self.map.carcasses.get(tile, 0) - rate * dt)
            if not food:
                del self.map.rot[tile]
                self.unbody(tile)

    def body(self, tile):
        """Show the body of a carcass: a raw beef item display that lies flat on the middle of its tile, until its food
        is gone (#3272). A display entity has no AI, hit box or drops, and a kill by its tag removes it."""
        x, z = (int(c * self.map.T + self.map.T // 2) for c in tile)
        self.command(f"kill @e[type=item_display,tag=aoe_carcass_{tile[0]}_{tile[1]}]")   # a second kill on the tile
        self.command(f"summon item_display {x + 0.5} {self.map.y(x, z) + 0.05} {z + 0.5} {{Tags:[\"aoe_carcass\","
                     f"\"aoe_carcass_{tile[0]}_{tile[1]}\"],item:{{id:\"minecraft:beef\",count:1}},"
                     f"transformation:{{left_rotation:[0.7071f,0f,0f,0.7071f],right_rotation:[0f,0f,0f,1f],"
                     f"translation:[0f,0f,0f],scale:[1.2f,1.2f,1.2f]}}}}")

    def unbody(self, tile):
        """Remove the body of an empty carcass (#3272)."""
        self.command(f"kill @e[type=item_display,tag=aoe_carcass_{tile[0]}_{tile[1]}]")

    def goals(self, tile):
        """The cells where a villager works a resource: on a farm, else next to it."""
        spot = self.map.spot(tile)
        return {c for c in spot if self.map.free(*c)} if tile in self.map.farms and tile not in self.map.pastures \
            else self.map.around(spot)

    def tended(self, tile):
        """True when the farm on tile has all its farmers: one, a pasture two (#4118)."""
        return tile in self.farmers and (tile not in self.map.pastures or tile in self.herders)

    def drop_goals(self, v):
        """The cells next to the drop sites of the load of a villager (a carcass: also the mule cart, #2194)."""
        build.moved_carts(self)                                        # a mule cart can be at a new place (#2209)
        if v.tree in self.map.pastures:                                # a herder drops at the yurt of its pasture (#4118)
            return self.map.around({c for c, t in self.map.farm_at.items() if t == v.tree})
        meat = self.map.drops["meat"] if v.res == "food" and v.tree in self.map.carcasses else []
        return set().union(*map(self.map.around, self.map.drops[v.res] + meat))

    def source(self, v):
        """The resources left in the tree, bush, mine or farm of a villager: {tile: amount} of its kind."""
        if v.tree in self.map.farms:
            return self.map.farms
        if v.tree in self.map.carcasses:
            return self.map.carcasses
        if v.tree in self.map.fish:
            return self.map.fish
        return self.map.bushes if v.res == "food" else self.map.trees if v.res == "wood" else self.map.mines[v.res]

    def nearest(self, v):
        """The nearest bush or mine of the resource of v with something left and a free cell next to it, or None. A fish:
        a fish of the same kind (an oyster after an oyster, #2465). An inner tree has no free cell (#3791)."""
        T, oyster = self.map.T, v.tree in self.map.oysters
        full = [t for t, k in self.home(self.source(v)).items() if k > 0 and (t in self.map.oysters) == oyster]
        near = sorted(full, key=lambda t: math.dist(v.cell, ((t[0] + 0.5) * T, (t[1] + 0.5) * T)))
        return next((t for t in near if self.goals(t)), None)

    def next_task(self, site, who):
        """AoE2: the builders of a complete own site work on (#3271). A farm: one builder farms it. A camp (a drop site of
        one or two resources, not a town center): the builders gather the nearest source of its resources. Else idle."""
        if not who or not self.work_on or site.get("player", self.player) != self.player:
            return
        x0, x1, z0, z1 = site["footprint"]
        if "FARM" in site["name"]:
            if (tile := self.map.farm_at.get((x0, z0))) and not self.tended(tile):
                self.send(tile, {min(who)})
            return
        res = [r for r, names in DROP_SITES.items() if site["name"] in names]
        if not 0 < len(res) < 3:
            return
        T, mid = self.map.T, ((x0 + x1) / 2, (z0 + z1) / 2)
        full = [t for r in res for t, k in self.home(self.map.bushes if r == "food" else self.map.trees if r == "wood"
                                                     else self.map.mines.get(r, {})).items() if k > 0]
        near = sorted(full, key=lambda t: (math.dist(mid, ((t[0] + 0.5) * T, (t[1] + 0.5) * T)), t))
        if tile := next((t for t in near if self.goals(t)), None):      # a free cell next to it (#3791)
            self.send(tile, who)

    def home(self, sources):
        """The sources {tile: amount} that nearest() may take: all. The bot takes only the ones at its base (#1810)."""
        return sources

    def go(self, v, state, goals):
        if self.paper:                                                 # Minecraft finds the path (#437)
            v.goal = min(goals, key=lambda c: (math.dist(c, v.cell), c), default=None)
            v.path, v.tries = [v.goal] if v.goal else [], 0
            self.move(v)
            self.set(v, state if v.goal else "idle")
            return
        path = self.map.path(v.cell, goals)
        v.path = path or []
        self.set(v, state if path is not None else "idle")

    def set(self, v, state):
        v.state = state
        self.event(v, EVENTS[state])

    def earn(self, res, n):
        """Add the income n of resource res to the stock and the sidebar. After the cheat "sharing is caring" (#969) the
        income goes to the allied Gathers (fog.gathers) in equal parts, as in AoE2; with no ally the player keeps it."""
        import fog  # fog imports gather
        to = [h for h in fog.gathers(self) if h.player != self.player and allied(self.players, self.player, h.player)]
        to = to if self.sharing and to else [self]
        for i, h in enumerate(to):
            if part := n // len(to) + (i < n % len(to)):
                h.stock[res] += part
                h.command(f"scoreboard players add {res.capitalize()} {h.board} {part}")

    def deliver(self, res, n, forage=False, kind=None):
        """Earn the load n of resource res at a drop site with the drop-off bonus of the civilization (civs.DROP: food,
        forage for a load of a fruit bush, #2111), and the second resource of gather kind (civs.DROP_EXTRA: "hunt",
        "fish", "ship", #2308). AoE2 keeps the fractions: the next load gets them."""
        f = civs.drop(self, res) * (civs.drop(self, "forage") if forage else 1)
        for r, m in [(res, n * f)] + [(b[0], n * b[1]) for b in [civs.drop_extra(self, kind)] if b]:
            self.spare[r] = self.spare.get(r, 0) + m
            if whole := int(self.spare[r] + 1e-9):
                self.spare[r] -= whole
                self.earn(r, whole)

    def event(self, v, name):
        if self.log:
            self.log.write(json.dumps({"t": round(self.clock() - self.t0, 3), "villager": v.uuid, "event": name,
                                       "pos": [round(c, 2) for c in v.pos], "walked": round(v.walked, 2),
                                       "load": v.load, "wood": self.wood}) + "\n")
            self.log.flush()

    def clicks(self):
        """Players who clicked since the last call. Clicks in a chest menu go to the handler of the menu (#619)."""
        build.tick(self)
        flare.tick(self)
        techtree.tick(self)
        hints.tick(self)
        map_table.tick(self)
        menu.clicks(self)
        cheats.clicks(self)
        self.taunted = getattr(self, "taunted", []) + [n for _, n in cheats.taunts(self)]   # for AI scripts (#4827)
        self.command(f"execute as {self.who} unless items entity @s container.* minecraft:carrot_on_a_stick[!custom_data] "
                     "run give @s minecraft:carrot_on_a_stick")       # not a group item
        if self.calls % GROUP_GIVE == 0:
            for name in filter(None, self.people()):                   # the groups of each person (#3490)
                self.person = name
                for n, (slot, _) in GROUPS.items():
                    self.command(f"execute as {name} unless items entity @s hotbar.{slot} *[custom_data={{aoe_group:{n}}}] "
                                 f"run item replace entity @s hotbar.{slot} with {group_item(n, len(self.groups.get(n, ())))}")
            diplomacy.give(self)                                       # the Game menu item (#1588)
            goto.give(self)                                            # the "Go to" compass (#1830)
        self.calls += 1
        if not self.paper:                                             # Paper: hold right click with the stick (#1786)
            self.command(f"execute as {self.who} unless items entity @s container.* minecraft:{WAND} "
                         f'run give @s minecraft:{WAND}[item_name="Selection box"]')
        self.release()                                                 # the drags of the selection box (#992)
        if getattr(self, "paper", False):                               # a partial Gather of tests/test_menu.py
            self.deselect()
        objs = ("aoe_use", "aoe_talk", "aoe_box")
        if "passed" not in "".join(self.command(f"execute if entity {only(self.who, f'scores={{{o}=1..}}')}") for o in objs):
            return self.short()
        out = []
        for name in self.people():
            scores = {o: self.command(f"scoreboard players get {name} {o}") for o in objs} if name else {}
            used = [o for o in objs if re.search(r"has [1-9]", scores.get(o, ""))]
            if used:
                out.append(name)
                self.person = name                                     # group_in_hand, hold: the selection of name
                if "aoe_box" in used:
                    self.wands.add(name)
                if "aoe_use" in used and (n := self.group_in_hand(name)):
                    self.grouping[name] = n, "passed" in self.command(f"execute as {name} if predicate {SNEAK}")
                elif "aoe_use" in used and diplomacy.in_hand(self, name):   # the Game menu item (#1588): no ray
                    out.remove(name)
                    diplomacy.open_menu(self, name)
                elif "aoe_use" in used and goto.in_hand(self, name):    # the "Go to" compass (#1830): no ray
                    out.remove(name)
                    goto.open_menu(self, name)
                elif "aoe_use" in used and self.paper and not (name in self.rallying or name in self.ordering or build.chosen(self, name)):
                    out.remove(name)                                   # a click or a hold: short() or drag decides
                    self.hold(name, int(re.search(r"has (\d+)", scores["aoe_use"])[1]))
                for obj in objs:
                    self.command(f"scoreboard players reset {name} {obj}")
        return out + self.short()

    def hold(self, name, uses):
        """A command stick use on Paper (#1786, owner feedback): the first use of a held right click is also a click,
        so it waits for HOLD seconds, but corner 1 shows at once (#3268). A next use in that time (or two uses in one call) is a held right click: the cell
        of the first use is corner 1 of the selection box, and the drag of #992 goes on until the release. A hold never
        gives an order first: a held click on the ground would send the selected villagers to walk."""
        if name in self.holds:
            self.holds[name] = self.clock()
            return
        if name in self.pending or uses > 1:
            look = self.pending.pop(name, (None, None))[1] or self.look(name)
            if name in self.corners:                                   # corner 1 of the first use (#3268)
                self.holds[name] = self.clock()
            else:
                self.drag(name, look and fleet.pick(self, *look))
            return
        self.pending[name] = self.clock(), (look := self.look(name))
        if (cell := look and fleet.pick(self, *look)) and name not in self.corners:
            self.box(name, cell)                                       # the box shows at once, no wait (#3268)

    def short(self):
        """The players whose stick use got no next use in HOLD seconds: a short click, with the look of the use.
        Call it after the uses of this call: a next use that came since the last call makes a hold."""
        due = sorted(n for n, (t, _) in self.pending.items() if self.clock() - t >= HOLD)
        for n in due:
            self.looks[n] = self.pending.pop(n)[1]
            if self.corners.pop(n, None) is not None:                  # a click: no box (#3268)
                self.command(f"aoe box-clear {n}")
        return due

    def deselect(self):
        """Paper: a left click with the command stick (the score LEFT of the plugin, AoePlugin.onLeftClick) clears the
        selection, as a click on empty ground in AoE2 (#1788); a click on an own unit selects it, and with a chosen
        building it places the foundation (#4703). Vanilla has no event for it: the empty box (#992)."""
        if "passed" not in self.command(f"execute if entity {only(self.who, f'scores={{{LEFT}=1..}}')}"):
            return
        for name in self.people():
            if name and re.search(r"has [1-9]", self.command(f"scoreboard players get {name} {LEFT}")):
                self.command(f"scoreboard players reset {name} {LEFT}")
                self.person = name
                if self.left(name):                                    # select or place (#4703)
                    continue
                self.choose(set())

    def cancel(self, name):
        """End the choice of a building of name (#2056): a right click on Paper, as in AoE2 (#4703)."""
        vars(self).get("rows", {}).pop(name, None)                     # the sneak clicks of build.place (#1805)
        vars(self).get("wall_start", {}).pop(name, None)
        if re.search(r"has [1-9]", self.command(f"scoreboard players get {name} {build.OBJECTIVE}")):
            self.command(f"scoreboard players set {name} {build.OBJECTIVE} 0")   # build.ghosts clears the ghost

    def place(self, name, building, eye, d):
        """Place the foundation of the chosen building at the look of name; the selected builders build it."""
        if (site := build.place(self, name, building, eye, d)) and building in build.WATER:
            fleet.build_site(self, self.selected, site)                # the selected fishing ships build it (#1438)
        elif site and self.selected & self.villagers.keys() and not self.row_busy(site):
            self.build(site)                                           # the selected villagers build it at once, as in AoE2 (#1654)
            self.order_voice()
        if site:
            repair.build_order(self, site, self.selected)              # the selected Serjeants build a Donjon (#2129)

    def left(self, name):
        """A left click of name as in AoE2 (#4703): place the chosen building, or select the own unit under the look.
        True: done. False: a click on the ground or the air, which clears the selection."""
        if getattr(diplomacy.main(self), "paused", False) or not (look := self.look(name)):
            return False
        if building := build.chosen(self, name):
            self.place(name, building, *look)
            return True
        kind, u, _ = self.target(*look, self.positions(sorted(self.pickable()))) or (None, None, None)
        if kind == "unit":
            self.select(u)
            return True
        return False

    def people(self):
        """The names of the Minecraft players of this Gather: all, or the players of its team (#1310). Not `team list`:
        the units are on the team too, and the server cuts a long list."""
        names = [n.strip() for n in self.command("list").split(":", 1)[-1].split(",")]
        if self.who == "@a":
            return names
        return [n for n in names if n and "passed" in self.command(f"execute if entity {only(self.who, 'name=' + n)}")]

    def group_in_hand(self, name):
        """The control group of the item in the main hand of player name, or None."""
        return next((n for n in GROUPS if "passed" in self.command(
            f"execute if items entity {name} weapon.mainhand *[custom_data={{aoe_group:{n}}}]")), None)

    def group(self, name, n, save):
        """Control group n, as Ctrl+N and N in AoE2 (#779): save the selection as group n, or select the live units
        of group n (a dead unit leaves its group). The boss bar shows the first unit of the group."""
        if save:
            self.groups[n] = set(self.selected)
            text = f"Group {n}: {len(self.selected)} units saved"
        else:
            self.groups[n] = set(self.positions(sorted(self.groups.get(n, ()))))
            out = self.groups[n] - garrison.inside(self)                # units inside a building stay there (#808)
            self.choose(out, min(out, default=None))
            text = f"Group {n}: {len(out)} units"
        self.command(f"title {name} actionbar " + json.dumps({"text": text}))
        # the item names the units of the group now (#1812), only in the hotbar of this person (#3490)
        self.command(f"item replace entity {name} hotbar.{GROUPS[n][0]} with {group_item(n, len(self.groups[n]))}")

    def click(self, name):
        self.person = name                                             # its own selection (#3486)
        if getattr(diplomacy.main(self), "paused", False):             # no orders and menus while paused (#3376)
            self.looks.pop(name, None), self.grouping.pop(name, None), self.wands.discard(name)
            self.command(f'title {name} actionbar "The game is paused."')
            return
        if (n := self.grouping.pop(name, None)) is not None:          # a group item (#779): no ray
            self.group(name, *n)
            return
        if not (look := self.looks.pop(name, None) or self.look(name)):   # a short click of hold() (#1786)
            return
        eye, d = look
        if name in self.wands:                                        # the selection wand (#778)
            self.wands.discard(name)
            (self.drag if self.paper else self.box)(name, fleet.pick(self, eye, d))   # the water too (#2060)
            return
        if (rect := self.rallying.pop(name, None)) and (cell := self.map.pick_ground(eye, d)):   # the menu item (#707)
            train.rally(self, rect, cell, self.map.pick_tree(eye, d))
            return
        order = vars(self).get("ordering", {}).pop(name, None)
        if order == "patrol" and (cell := self.map.pick_ground(eye, d)):
            stance.patrol(self, name, cell)                            # the Patrol menu item (#3355)
            return
        if order == "attack_move" and (cell := self.map.pick_ground(eye, d)):
            stance.attack_move(self, name, cell)                       # the Attack Move menu item (#3357)
            return
        if order == "attack_ground" and (cell := self.map.pick_ground(eye, d)):
            stance.attack_ground(self, name, cell)                     # the Attack Ground menu item (#4079)
            return
        kind, u, cells = self.target(eye, d, self.positions(sorted(self.pickable()))) or (None, None, None)
        if order in ("follow", "guard"):                               # the Follow and Guard menu items (#3358)
            if kind == "unit" or kind == "building" and order == "guard":
                follow.start(self, name, order, u)
                if kind == "unit":
                    self.command(glow(u))                              # the order marker, as an attack (#796)
                else:
                    for c in marker(self.map, cells or {(sum(u[:2]) // 2, sum(u[2:]) // 2)}, "go", name):
                        self.command(c)
            else:
                follow.refuse(self, name, order)
            return
        if kind in ("enemy", "fort") and treaty.refuse(self, name):   # no attack before the end of the treaty (#2297)
            return
        if kind in ("enemy", "fort") and add_attack(self, name, u):   # a sneak click queues the target (#3516)
            self.order_voice()
            self.command(glow(u)) if kind == "enemy" else self.mark(name, set(cells), "attack")
            return
        if kind == "enemy":
            monk.convert_order(self, self.monks(), u)                    # the monks convert it, the others attack (#1245)
            self.attack(u)
            queue_attack(self, u)
            self.order_voice()
            self.command(glow(u))                                     # the order marker of an attack (#796)
            return
        if kind == "prey":
            self.hunt(u)
            self.order_voice()
            self.command(glow(u))
            return
        import combat  # combat imports this module
        if kind == "unit" and u in self.selected and (u in self.villagers   # a click on a selected villager (#621)
                                                      or self.soldiers.get(u) in combat.REPAIRS):   # or Serjeant (#2129)
            build.open_menu(self, name)
            return
        if kind == "unit" and u in self.selected and siege_tower.out(self, u):   # its units come out (#1362)
            return
        if kind == "unit" and u in self.selected and transport.out(self, u):   # on the nearest land (#1385)
            return
        if kind == "unit" and u in self.selected and u in self.soldiers:    # a click on a selected soldier (#1107)
            stance.open_menu(self, name, u)
            return
        if kind == "unit" and repair.unit_order(self, name, u):        # villagers repair an own damaged siege unit or ship (#1331, #1661)
            return
        if kind == "unit" and siege_tower.order(self, name, u):        # the selection goes into a siege tower (#1362)
            return
        if kind == "unit" and transport.order(self, name, u):          # the selection goes into a transport ship (#1385)
            return
        if kind == "unit":
            self.select(u)
            return
        if kind == "fort" and self.selected and self.selected <= self.villagers.keys():   # Siegecraft (#3916)
            self.sieged.add(u)
            self.hunt(u)
            self.order_voice()
            x0, _, z0, x1, _, z1 = self.forts[u]
            self.mark(name, {(x0, z0), (x1, z1)}, "attack")
            return
        if kind == "fort":
            monk.convert_order(self, self.monks(), u)                 # with Redemption (#1264)
            self.sieged.add(u)
            self.attack(u)
            queue_attack(self, u)
            self.order_voice()
            x0, _, z0, x1, _, z1 = self.forts[u]
            self.mark(name, {(x0, z0), (x1, z1)}, "attack")
            import combat  # combat imports this module
            what = self.fort_names.get(u, "")
            owner = self.fort_players.get(u, 0)                        # Persians (#1895), Byzantines in the own age (#2116)
            full = civs.hp(civs.civ(self, owner), what, combat.stats(what), build.ages(self) if owner == self.player else 0,
                           civs.handicap(self.data, owner)).hp
            for c in siege_mark(u, what, full, name):
                self.command(c)
            return
        if building := build.chosen(self, name):                      # a chosen building: place its foundation
            if self.paper:                                             # Paper: the left click places it, the right click cancels (#4703)
                self.cancel(name)
            else:                                                      # vanilla has no left click event
                self.place(name, building, eye, d)
            return
        if monk.order(self, name, self.map.pick_ground(eye, d)):      # a monk to a relic or to a monastery (#1246)
            return
        if trade.order(self, name, self.map.pick_ground(eye, d)):     # the trade carts trade with an own market (#1253)
            return
        if fleet.trade_order(self, name, fleet.pick(self, eye, d)):   # the trade cogs trade with an own dock (#1485)
            return
        if repair.order(self, name, self.map.pick_ground(eye, d)):    # villagers repair an own damaged building (#1330)
            return
        if garrison.order(self, name, self.map.pick_ground(eye, d)):   # the selection goes into an own building (#808)
            return
        if garrison.order(self, name, fleet.pick(self, eye, d)):     # fishing ships go into a dock on the water (#1949)
            return
        if train.open_menu(self, name, self.map.pick_ground(eye, d), True):  # an own town center or barracks (#620, #654)
            return
        if train.open_menu(self, name, fleet.pick(self, eye, d), True):     # a dock is on the water (#1383)
            return
        if market.open_menu(self, name, self.map.pick_ground(eye, d)):  # an own market: buy and sell (#1252)
            return
        if garrison.open_menu(self, name, self.map.pick_ground(eye, d)) or \
                garrison.open_menu(self, name, fleet.pick(self, eye, d)):   # units inside an own tower come out (#2970)
            return
        if fleet.build_order(self, name, eye, d):                    # the fishing ships build a fish trap (#1438)
            return
        if fleet.fish_order(self, name, eye, d):                     # the fishing ships fish (#1384)
            return
        tile = self.map.pick_tree(eye, d) or self.shore_fish(eye, d)
        if tile and self.selected:
            self.send(tile)
            self.order_voice()
            self.mark(name, self.map.spot(tile))
        elif self.selected and (site := build.pick(self, eye, d)):
            if not build.queue(self, name, site):                      # a sneak click queues the site (#3517)
                self.build(site)
            self.order_voice()
            repair.build_order(self, site, self.selected)              # Serjeants build a Donjon (#2129)
            x0, x1, z0, z1 = site["footprint"]
            self.mark(name, {(x0, z0), (x1 - 1, z1 - 1)})
        elif self.selected and (cell := self.map.pick_ground(eye, d)) and self.map.free(*cell):
            if not add_waypoint(self, name, cell):                     # a sneak click adds a waypoint (#3515)
                queue_move(self, self.walk_to(name, cell))             # the move order of AoE2 (#1368)
            self.order_voice()
        elif any(replay.ship(self.soldiers.get(u, "")) for u in self.selected) \
                and (cell := fleet.pick(self, eye, d)) and self.map.wet(*cell):
            self.walk_to(name, cell)                                   # the ships sail on the water (#1383)
            self.order_voice()
        else:                                                          # an own house, tower, wall or site: Delete (#3452)
            demolish.open_menu(self, name, self.map.pick_ground(eye, d)) or demolish.open_menu(self, name, fleet.pick(self, eye, d))

    def new_order(self, units):
        """A new order ends each old order of the units, as in AoE2 (#3007): the repair of a Serjeant (#2128), the
        trigger patrols (#2674), the walk into a building, a siege tower or a transport ship, a conversion, a relic
        trip, the farm of a farmer and the route of a trade cart (#3278). Each order function calls it before it sets its own state."""
        units = set(units)
        repair.drop(self, units)
        self.end_patrols(units)
        stance.end_attack_moves(self, units)
        follow.end(self, units)
        autoscout.end(self, units)                                     # the Auto Scout order (#3702)
        for key in ("entering", "boarding", "loading", "converting", "fetching", "trade"):
            table = vars(self).get(key, {})
            for u in units & table.keys():
                del table[u]
        for t in [t for t, f in self.farmers.items() if f in units]:
            del self.farmers[t]
        for t in [t for t, f in self.herders.items() if f in units]:
            del self.herders[t]
        for u in units & vars(self).get("waypoints", {}).keys():      # a new order ends the waypoints (#3515)
            del self.waypoints[u]

    def end_patrols(self, units):
        """A new order ends the trigger patrols of the units, as in AoE2 DE (#2674): their patrol tags of
        scenario.orders go, so the next leg does not walk them back. No command when no patrol walks."""
        for tag, _, _ in vars(self).get("patrols", ()):
            for u in sorted(units):
                self.command(f"tag {u} remove {tag}")

    def shore_fish(self, eye, d):
        """The tile of the shore fish under the water surface that the ray from eye in direction d hits (fleet.pick), or
        None: villagers fish it from the land (#1283, #2349)."""
        cell = fleet.pick(self, eye, d)
        tile = cell and (cell[0] // self.map.T, cell[1] // self.map.T)
        return tile if tile in self.map.shore and self.map.fish.get(tile, 0) > 0 else None

    def walk_to(self, name, cell, units=None):
        """The selected units walk to the free block cell (x, z), as the move order of AoE2 (#1368): each one to its own
        free cell near it, the nearest cells first; 2 or more military units end in the AoE2 line formation (#3414:
        replay.formation_cells, rank). Military units walk with the plugin path finding at their AoE2 speed; villagers
        stop their work and walk there. Ships sail to the water near it (fleet.order, also at a water cell). units: these
        units, not the selection, and no mark (transport.tick, #1515). Returns the cells {uuid: cell}."""
        import ai  # ai imports this module
        units = self.selected if units is None else set(units)
        self.new_order(units)
        boats = {u for u in units if replay.ship(self.soldiers.get(u, ""))}
        out = fleet.order(self, boats, cell)                           # a ship sails on the water (#1383)
        transport.aim(self, out, cell)                                 # a loaded ship unloads at a land cell (#1385)
        herd = self.herd()
        army = sorted(u for u in units - boats - herd if u in self.soldiers)
        pos = self.positions(army) if len(army) > 1 else {}            # 2 or more: the AoE2 line formation (#3414)
        if len(pos) > 1:                                               # the most common formation of the group (#3416)
            kind = collections.Counter(stance.formation(self, u) for u in pos).most_common(1)[0][0]
            weak = (lambda u: rank(self.soldiers[u]) >= 2) if kind == "Box" else (lambda u: False)
            out |= replay.formation_cells(self.map.free, [(u, p[0], p[2], rank(self.soldiers[u]), weak(u))
                                                          for u, p in pos.items()], (cell[0] + 0.5, cell[1] + 0.5), kind, self.map.T,
                                                          long=True)
        # a group in formation walks at the speed of its slowest unit (#3415): tiles per AoE2 second
        pace = min(ai.walk_speed(self.soldiers[u], 1) * train.speed(self, self.soldiers[u], u) for u in pos) if len(pos) > 1 else None
        who = sorted(u for u in units - boats - out.keys() if u in self.villagers or u in self.soldiers or u in herd)
        r = math.isqrt(len(who)) + 2
        cells = sorted(((x, z) for x in range(cell[0] - r, cell[0] + r + 1) for z in range(cell[1] - r, cell[1] + r + 1)
                        if self.map.free(x, z) and (x, z) not in out.values()), key=lambda c: (math.dist(c, cell), c))
        out |= dict(zip(who, cells))
        for u, (x, z) in [(u, c) for u, c in out.items() if u not in boats]:
            if u in self.villagers:
                v = self.villagers[u]
                v.tree, v.site, v.prey = None, None, None
                self.go(v, "to_rally", {(x, z)})
            else:
                unit = self.soldiers.get(u) or self.prey[u]            # an own herdable walks too (#1791)
                speed = pace / ai.walk_speed(unit, 1) if pace is not None and u in pos else train.speed(self, unit, u)
                ai.move(self, u, unit, self.map.T, x + 0.5, self.map.y(x, z), z + 0.5, NORMAL * speed)
        if out and name:
            self.mark(name, {cell})
            record.ordered(self, "move", set(out), cell)               # Record Game (#2649)
        return out

    def pickable(self):
        """The UUIDs of the soldiers and enemies that a right click can pick (villagers: their own positions). Units
        inside a building take no click (#808); an enemy only with an army selected."""
        army = self.selected and self.selected <= set(self.soldiers)
        hunters = self.selected & self.villagers.keys()               # villagers take an animal to hunt (#1058)
        return (set(self.soldiers) | (set(self.enemies) if army else set()) | (set(self.prey) if hunters else set())
                | self.herd()) - self.unpickable()

    def unpickable(self):
        """The UUIDs that no click selects: the units inside a building (garrison.inside, #808) and the units of a
        trigger "Disable Object Selection" (scenario.selection, #2854)."""
        return garrison.inside(self) | vars(self).get("unselectable", set())

    def herd(self):
        """The UUIDs of the live own herdable animals (#1791): a right click selects them, as in AoE2."""
        return self.flock & self.prey.keys()

    def target(self, eye, d, places):
        """What a right click from eye in the view direction d picks, in the order of click(): (kind, key, block cells
        of the mark) or None. kind: "enemy" or "unit" (key: UUID), "fort" (target UUID), "building" (an own footprint
        that takes a garrison or trains units), "tree", "mine", "bush", "farm" (tile) or "ground" (block cell).
        places: {UUID: feet} of pickable(). The click and the pointing mark use it, so both pick the same (#989)."""
        held = self.unpickable()
        at = {k: v.pos for k, v in self.villagers.items() if k not in held} | \
            {k: p for k, p in places.items() if k in self.pickable()}
        if u := pick_unit(eye, d, at):
            hunters = self.selected & self.villagers.keys()            # villagers hunt an own herdable (#1058, #1791)
            kind = "enemy" if u in self.enemies else "prey" if u in self.prey and (hunters or u not in self.flock) \
                else "unit"
            return kind, u, {(math.floor(at[u][0]), math.floor(at[u][2]))}
        if self.selected and (self.selected <= set(self.soldiers) or self.selected <= self.villagers.keys()) \
                and (fort := self.pick_fort(eye, d)) and (self.selected <= set(self.soldiers) or breach(self, fort)):
            x0, _, z0, x1, _, z1 = self.forts[fort]
            return "fort", fort, {(x0, z0), (x1, z1)}
        cell = self.map.pick_ground(eye, d)
        if rect := next((r for r in garrison.holders(self) | train.homes(self)
                         if cell and r[0] <= cell[0] < r[1] and r[2] <= cell[1] < r[3]), None):
            return "building", rect, {(rect[0], rect[2]), (rect[1] - 1, rect[3] - 1)}
        if tile := self.map.pick_tree(eye, d):
            m = self.map
            kind = "farm" if tile in m.farms else "bush" if tile in m.bushes else "tree" if tile in m.trees else "mine"
            return kind, tile, m.spot(tile)
        return cell and ("ground", cell, {cell})

    def says(self, kind, key):
        """The action bar text of a pointed target (#989): its name and what a right click on it does now."""
        workers = self.selected & self.villagers.keys()
        if kind == "prey":
            name, act = pretty(self.prey[key]), ("attack" if predator(self.prey[key]) else "hunt") if workers else None
        elif kind in ("enemy", "unit"):
            name = ("Enemy " if kind == "enemy" else "") + pretty(self.enemies.get(key) or self.soldiers.get(key)
                                                                  or self.prey.get(key) or "VILLAGER")
            act = "attack" if kind == "enemy" else "build menu" if key in workers else \
                "select all of the type" if key in self.selected and key in self.soldiers else "select"
        elif kind == "fort":
            name, act = "Enemy " + (pretty(self.fort_names[key]) if key in self.fort_names else "building"), "attack"
        elif kind == "building":
            homes, holders = train.homes(self), garrison.holders(self)
            name = pretty(homes.get(key) or holders[key]["name"])
            carts = any(self.soldiers.get(u, "").startswith(trade.CART) for u in self.selected)
            act = "trade" if carts and homes.get(key) == "MARKET" and len(trade.markets(self)) > 1 and self.paper else \
                "garrison" if key in holders and self.selected and self.paper else "train" if key in homes else None
        elif kind == "ground":
            name, act = "Ground", "move" if self.selected else None    # the move order (#1368)
        else:
            res = self.map.resource(key)
            name = {"tree": "Tree", "bush": "Berry bush", "farm": "Farm"}.get(kind, f"{res.capitalize()} mine")
            act = "gather" if workers else None
        return name + f" · Right click: {act}" * bool(act)

    def places(self):
        """{UUID: feet} of pickable() for the pointing mark. On Paper one `aoe where` answer has WHERE_PAGE units
        (#813): the units of the players are on their teams (the pulse of the datapack, #358). Else one `data get`
        for each unit."""
        return self.where(self.pickable())

    def where(self, want, sel="@e[type=!player,team=!]"):
        """{UUID: feet} of the units want: on Paper `aoe where` answers (WHERE_PAGE units each), else `data get`.
        want None: all units of the selector sel (Paper only)."""
        if not self.paper:
            return self.positions(sorted(want or ()))
        out, start = {}, 0
        while m := re.search(r"Where (\d+): ?(.*)", self.command(f"aoe where {sel} {start}")):
            for part in filter(None, m[2].split(", ")):
                u, x, y, z = part.split()[:4]
                if want is None or u in want:
                    out[u] = float(x), float(y), float(z)
            start += WHERE_PAGE
            if start >= int(m[1]):
                break
        return out

    def point(self):
        """Mark the target that a right click of each player picks now (#989): a small ring of dust that only this
        player sees, in the color of the target (POINT), up to the reach of the click; far away the dust is larger.
        hints.py writes its name and action into the action bar. Minecraft outlines a block only up to about 5
        blocks, and the order marker (#796) shows only after the click."""
        names = [n for n in self.people() if n]
        for name in sorted(set(names) - self.sided):                   # a player who joins later (#1241)
            self.command(f"team join p{self.player} {name}")
            self.sided.add(name)
        self.pointing = {}
        places = self.places() if names else {}
        for name in names:
            if not (look := self.look(name)) or not (t := self.target(*look, places)):
                continue
            kind, key, cells = t
            self.pointing[name] = self.says(kind, key)
            color = {"enemy": "enemy", "fort": "enemy", "unit": "own", "building": "own", "ground": "ground"}
            far = math.dist((look[0][0], look[0][2]), [sum(c[i] for c in cells) / len(cells) + 0.5 for i in (0, 1)])
            scale = round(min(4.0, max(POINT_SCALE, far * POINT_GROW)), 1)   # the dust stays visible far away
            for c in marker(self.map, cells, color.get(kind, "resource"), name, POINT, POINT_POINTS, scale):
                self.command(c)

    def mark(self, name, cells, kind="go"):
        """Show the target of an order to player name, as the flag of AoE2 (#796): marker() around the block cells."""
        for c in marker(self.map, cells, kind, name):
            self.command(c)

    def pick_fort(self, eye, d, reach=64):
        """The target UUID of the enemy building that the ray from eye in direction d hits first (up to 3 tiles
        above its ground: about the height of a building), or None."""
        for k in range(1, reach * 4):
            x, y, z = (eye[i] + d[i] * k / 4 for i in range(3))
            for uuid, (x0, y0, z0, x1, _, z1) in self.forts.items():
                if x0 <= x < x1 + 1 and z0 <= z < z1 + 1 and y0 <= y < y0 + 3 * self.map.T:
                    return uuid
        return None

    def fall(self):
        """Free the footprints of the buildings whose target the plugin removed: paths go through them."""
        for uuid in [u for u in self.sieged if "passed" not in self.command(f"execute if entity {u}")]:
            self.sieged.discard(uuid)
            import spoils  # spoils imports this module
            spoils.loot(self, uuid)                                    # Danes (#2271)
            score.razed(self, uuid)                                    # the military score (#2355)
            self.free(uuid)

    def free(self, uuid):
        """Free the footprint of a target that fell: the other sides attack it no more (#1819), its square leaves the
        minimap (#2582) and its cells are walkable again. A target with no box has no footprint and no square."""
        box = self.forts.pop(uuid, None)
        for o in build.sides(self):
            o.forts.pop(uuid, None)
            o.sieged.discard(uuid)                                     # one side handles the fall (#3005)
        if box is None:
            return
        x0, y0, z0, x1, _, z1 = box
        if self.paper:
            self.command(f"aoe minimap unbuild {x0} {z0}")
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                self.map.blocked.discard((x, z))
                self.map.ground[z][x] = y0                             # the plugin filled the box with air

    def step(self):
        """One tick: walk one block, chop, drop the wood, or build."""
        self.fall()
        ruins.tick(self)
        garrison.tick(self)
        siege_tower.tick(self)
        transport.tick(self)
        for v in self.villagers.values():
            if v.state in ("to_tree", "to_drop", "to_site", "to_rally", "to_prey", "to_repair") and v.path:
                self.follow(v) if self.paper else walk(self, v)
            elif v.state == "to_rally":
                self.set(v, "idle")
            elif v.state == "to_site":
                self.set(v, "build" if v.site["progress"] < 1 else "idle")
            elif v.state == "to_repair":
                self.set(v, "repair")
            elif v.state == "to_prey":
                v.timer = 0.0
                self.set(v, "hunt")
            elif v.state == "hunt":
                self.strike(v)
            elif v.state == "to_tree":
                v.timer = 0.0
                self.set(v, "chop" if self.source(v).get(v.tree, 0) > 0 else "idle")
            elif v.state == "to_drop":
                self.deliver(v.res, v.load, v.res == "food" and v.tree in self.map.bushes,
                             "hunt" if v.tree in self.map.carcasses else fish_kind(self.map, v.tree))
                v.load = 0
                self.event(v, "drop")
                if v.tree in self.map.farms:
                    if self.map.farms[v.tree] <= 0:                    # an empty farm: the farmer stops
                        self.farmers.pop(v.tree, None)
                        self.herders.pop(v.tree, None)
                        v.tree = None
                elif (v.res != "wood" or self.work_on) and self.source(v).get(v.tree, 0) <= 0:
                    v.tree = self.nearest(v)                           # as in AoE2: the next tree, bush or mine, or stop (#3271)
                if self.source(v).get(v.tree, 0) > 0:
                    self.go(v, "to_tree", self.goals(v.tree))
                else:
                    self.set(v, "idle")
            elif v.state == "chop":
                v.timer += self.tick
                src = self.source(v)
                kind = "farm" if v.tree in self.map.farms else "hunt" if v.tree in self.map.carcasses else \
                    fish_kind(self.map, v.tree) or v.res                # a fisherman: no forage rate (#2349)
                work = self.work_time(kind, v.tree in self.map.herds, (v.pos[0], v.pos[2])) / self.aura_rate(v, kind)
                last = civs.last(self, "sheep" if v.tree in self.map.herds else kind)
                take = 1 if last == 1 else 1 / last                    # 1: the amounts stay whole numbers
                most = self.limit(v.res, "sheep" if v.tree in self.map.herds else kind)
                if v.load < most and src.get(v.tree, 0) > 0:
                    self.trickle(kind, self.tick)
                while v.timer >= work and v.load < most and src.get(v.tree, 0) > 0:
                    v.timer -= work
                    v.load += 1
                    src[v.tree] -= take
                    if src[v.tree] < 1e-6:                             # 455 takes of 1 / 1.3 empty 350 stone
                        src[v.tree] = 0
                    self.work(v)
                    self.second(v)
                    if v.tree in self.map.pastures:                    # no wheat and no reseed (#4118)
                        if src[v.tree] <= 0:
                            self.clear_farm(v.tree)
                    elif v.tree in self.map.farms:
                        self.harvest(v.tree)
                        if src[v.tree] <= 0 and getattr(self, "reseeds", 0) > 0:   # a queued reseed: new at once (#3283)
                            self.reseeds -= 1
                            src[v.tree] = self.map.farm_food
                            self.harvest(v.tree)
                        elif src[v.tree] <= 0 and getattr(self, "auto_reseed", False) \
                                and (cost := build.price(self, "FARM")) and all(self.stock[r] >= n for r, n in cost.items()):
                            for r, n in cost.items():                  # auto reseed: the farm cost now (#3422)
                                self.stock[r] -= n
                                self.command(f"scoreboard players remove {r.capitalize()} {self.board} {n}")
                            src[v.tree] = self.map.farm_food
                            self.harvest(v.tree)
                        self.tend(v)
                        if src[v.tree] <= 0:                           # no reseed: the place is free to build (#3423)
                            self.clear_farm(v.tree)
                    elif v.tree in self.map.carcasses:
                        if src[v.tree] <= 0:                           # a carcass has no blocks, only its body
                            self.unbody(v.tree)
                    elif v.tree in self.map.fish:                      # a shore fish: its mob goes when empty (#2349)
                        if src[v.tree] <= 0:
                            fleet.remove(self, v.tree)
                    elif v.res == "food":
                        self.berries(v.tree)
                    elif v.res != "wood":
                        if src[v.tree] <= 0:
                            self.dig(v.tree, v.res)
                    elif src[v.tree] <= 0:
                        self.fell(v.tree)
                    else:
                        self.trunk(v.tree)
                if v.load >= most or src.get(v.tree, 0) <= 0:
                    self.go(v, "to_drop", self.drop_goals(v))
        self.decay(self.tick * NORMAL)
        train.tick(self, self.tick * NORMAL)
        monk.heal(self, self.tick * NORMAL)
        monk.convert(self, self.tick * NORMAL)
        garrison.heal(self, self.tick * NORMAL)
        garrison.pasture(self, self.tick * NORMAL)
        regen.tick(self, self.tick * NORMAL)
        near.tick(self, self.tick * NORMAL)                            # Shield Wall (#4333)
        repair.tick(self, self.tick * NORMAL)
        trebuchet.tick(self, self.tick * NORMAL)
        fleet.tick(self, self.tick * NORMAL)
        monk.relic_tick(self, self.tick * NORMAL)
        feitoria.tick(self, self.tick * NORMAL)
        trade.tick(self)
        trade.heal(self, self.tick * NORMAL)
        train.haste(self, self.tick * NORMAL)
        amounts.tick(self)                                             # before the bar: tests read its last command
        bossbar.tick(self)
        for site in self.sites:
            builders = [v for v in [*self.villagers.values(), *self.ships.values()] if v.state == "build" and v.site is site]
            men = repair.raisers(self, site)                           # Serjeants at their Donjon site (#2129)
            # AoE2: n builders need 3 / (n + 2) of the time of one
            n = len(builders) + len(men)
            if n and build.rise(self, site, math.inf if self.aegis else self.tick * NORMAL * (n + 2) / 3):
                repair.drop(self, men)                                 # complete: the Serjeants stand
                if nxt := build.next_tile(self, site):                 # a wall line: on to its next tile (#1322)
                    self.build(nxt, {v.uuid for v in builders})
                    ships = {v.uuid for v in builders if v.uuid in self.ships}
                    sail = fleet.build_site(self, ships, nxt) if nxt["name"] in build.WATER else set()   # the next trap (#3114)
                    builders = [v for v in builders if v.uuid in ships - sail]   # the ships that stay: they fish below
                x0, x1, z0, z1 = site["footprint"]                     # the AoE2 sound of a complete site (#3502)
                self.command(f"playsound {train.EVENT_SOUNDS['built']} master @a[team=p{site['player']}] "
                             f"{(x0 + x1) / 2} ~ {(z0 + z1) / 2} 1 1")
                for v in builders:                                     # complete: the builders stop
                    v.site = None
                    if v.uuid in self.ships:                           # a fishing ship fishes its new fish trap
                        v.state = "idle"
                        fleet.fish(self, {v.uuid}, fleet.trap(self, site))
                    else:
                        self.set(v, "idle")
                if not nxt:
                    self.next_task(site, {v.uuid for v in builders if v.uuid in self.villagers})
        self.idle()

    def work_time(self, res, herd=False, pos=None):
        """Real seconds per unit of resource res ("farm" for farms) with the technologies of the player (WORK_TECHS) and
        the work-rate bonus of its civilization (civs.WORK; herd: the carcass of a herdable animal, for shepherds).
        civs.MORE multiplies the change of a technology (Armenians: the mule cart technologies 40 % more, #2309). At the
        block position pos (x, z) of the villager, a building near it can add its bonus (civs.church_rate, #2377)."""
        if self.aegis:
            return 0.0                                                 # a full load in one work step
        rate, more = civs.work(self, "sheep" if herd else res), civs.MORE.get(civs.civ(self), {})
        rate *= civs.church_rate(self, pos) if pos else 1
        return self.chop.get(res, self.chop.get("food")) / rate / civs.turbo(self) / math.prod(
            (1 + (WORK_TECHS.get(t, {}).get(res, 1) - 1) * more.get(t, 1)) ** train.count(self, t) for t in self.techs)

    def aura_rate(self, v, kind):
        """The factor of the work rate of v for resource kind: the "rate" of civs.AURA within its "range" (tiles from the
        footprint) of an own complete aura building that is still a drop site of kind (AoE2 wiki "Thracians"), else 1;
        times the best "aura" of an upgraded own building near v (train.ONE_BUILDING: Economic Town Center, #2484)."""
        a, m = self.map.aura, self.map
        x, z = v.pos[0], v.pos[2]
        best = max([1] + [aura.get("rate", 1) for rect, name in getattr(self, "upgraded", {}).items()
                          if (aura := train.ONE_BUILDING.get(name)) and rect in train.homes(self)
                          and max(rect[0] - x, x - rect[1], rect[2] - z, z - rect[3]) <= aura["range"] * m.T])
        if kind not in a.get("resources", ()):
            return best
        near = a["range"] * m.T
        return best * a["rate"] if any(max(min(c[0] for c in cs) - x, x - max(c[0] for c in cs) - 1,
                                           min(c[1] for c in cs) - z, z - max(c[1] for c in cs) - 1) <= near
                                       for cs in m.auras if cs in m.drops[kind]) else best

    def move(self, v):
        import ai  # ai imports gather
        if v.goal:
            x, z = v.goal
            ai.move(self, v.uuid, "VILLAGER", self.map.T, x + 0.5, self.map.y(x, z), z + 0.5,
                    NORMAL * train.speed(self, "VILLAGER", v.uuid) * math.prod(PACE.get(t, 1) ** train.count(self, t) for t in self.techs))
        v.moved, v.tries = self.clock(), v.tries + 1
        v.anchor, v.anchor_far = v.pos, math.inf

    def second(self, v):
        """One unit that v gathers earns the second resource of the civilization (civs.EXTRA, #2113): Poles and Puru
        stone miners, Portuguese foragers, Shu lumberjacks. The fractions add up, so small amounts earn the exact sum."""
        if bonus := civs.extra(self, "forage" if v.tree in self.map.bushes else v.res):
            res, n = bonus
            self.seconds[res] = self.seconds.get(res, 0) + n
            if whole := int(self.seconds[res] + 1e-9):
                self.seconds[res] -= whole
                self.earn(res, whole)

    def trickle(self, kind, dt):
        """dt real seconds of work at gather kind earn the resource of the civilization for each AoE2 minute
        (civs.PER_MINUTE, #2308: Thracian hunters and shepherds 3 gold). The fractions add up as in second."""
        if bonus := civs.per_minute(self, kind):
            res, n = bonus
            self.seconds[res] = self.seconds.get(res, 0) + n * dt * NORMAL / 60
            if whole := int(self.seconds[res] + 1e-9):
                self.seconds[res] -= whole
                self.earn(res, whole)

    def limit(self, res=None, kind=None):
        """The resources res that a villager carries, with the technologies of the player (CARRY, and FOOD_CARRY for
        food) and the bonus of its civilization for gather kind (civs.carry, #2270)."""
        more = CARRY | FOOD_CARRY if res == "food" else CARRY
        n = self.carry + sum(more.get(t, 0) * train.count(self, t) for t in self.techs) + civs.carry(self, kind or res)
        return n if civs.turbo(self) == 1 else round(n * civs.turbo(self))   # Turbo Mode carries more (#2359)

    def follow(self, v):
        """Paper: read the position of a walking villager. It arrives 1.5 blocks from the center of its goal cell (there
        the plugin stops a villager, #438), or when it stands still for 1 s near it; still for 5 s far from it after
        two orders, it found no path and stops (#437)."""
        pos = self.pos(v.uuid)
        if not pos:
            return
        step, v.pos, now = math.dist(pos, v.pos), pos, self.clock()
        v.walked += step
        far = math.dist((pos[0], pos[2]), (v.goal[0] + 0.5, v.goal[1] + 0.5))
        # a crowd pushes a villager back and forth: only a move of 0.5 blocks or a nearer goal counts as progress (#3372)
        if math.dist(pos, v.anchor) >= 0.5 or v.anchor_far - far >= 0.25:
            v.anchor, v.anchor_far, v.moved = pos, far, now
        still = now - v.moved
        if still >= 5 and far >= 2 and v.tries < 2:                    # a second order, as the plugin drops one
            self.move(v)
        elif far < 1.5 or still >= 1 and far < 2 or still >= 5:
            self.command(f"aoe stop {v.uuid}")
            v.path = []
            if far >= 2:
                self.set(v, "idle")

    def work(self, v):
        """One gather step shows: the villager turns to the middle of the resource, block particles of the resource
        fly to its point next to the villager, and the work sound plays (#592)."""
        tile, T = v.tree, self.map.T
        x0, x1, z0, z1 = self.map.feet.get(tile, (tile[0] * T, tile[0] * T + T, tile[1] * T, tile[1] * T + T))
        x, y, z = min(max(v.pos[0], x0 + 0.5), x1 - 0.5), v.pos[1] + 1, min(max(v.pos[2], z0 + 0.5), z1 - 0.5)
        kind = "farm" if tile in self.map.farms else "hunt" if tile in self.map.carcasses else \
            "fish" if tile in self.map.fish else v.res
        block, sound = WORK_LOOK[kind]
        if kind == "wood":
            block = self.map.woods.get(tile, (block,))[0]
        name, _, props = block.partition("[")
        props = ",".join(f'{k}:"{w}"' for k, w in (p.split("=") for p in props.rstrip("]").split(",") if p))
        state = f'{{id:"{name}"' + (f",Properties:{{{props}}}" if props else "") + "}"
        at = f"{x:.2f} {y:.2f} {z:.2f}"
        # face the middle of the resource: a replay unit of the plugin stands up to replay.NEAR blocks from v.pos,
        # and from there the point next to v.pos can be 40° off the tree (#867). A farmer stands on its farm.
        fx, fz = (x, z) if kind == "farm" else ((x0 + x1) / 2, (z0 + z1) / 2)
        self.command(f"rotate {v.uuid} facing {fx:.2f} {y:.2f} {fz:.2f}")
        self.command(f"particle minecraft:block{{block_state:{state}}} {at} 0.2 0.2 0.2 0 8")
        self.command(f"playsound {sound} block @a {at} 1 {0.9 + 0.2 * (v.load % 2):.1f}")

    def site(self, tile):
        """Footprint (x0, x1, z0, z1), ground heights next to it, stump cell and trunk row z of a tree."""
        T = self.map.T
        fx0, fx1, fz0, fz1 = self.map.feet.get(tile, (tile[0] * T, tile[0] * T + T, tile[1] * T, tile[1] * T + T))
        feet = {(x, z) for x in range(fx0, fx1) for z in range(fz0, fz1)}
        # "ground" over the footprint is the top of the barriers: take the ground of the free cells next to it
        ys = [self.map.y(x, z) for x, z in self.map.around(feet)] or \
             [y for x, z in feet if (y := self.map.y(x, z)) is not None] or [0]
        tops = {y for x, z in feet if (y := self.map.y(x, z)) is not None}
        if len(tops) > 1:   # a hill: in a forest the few free cells can all be at its foot (#1157); barriers 3 high
            ys += [y - 3 for y in tops]
        sx, sz = (fx0 + fx1) // 2, (fz0 + fz1) // 2
        return (fx0, fx1, fz0, fz1), ys, (sx, sz), max(fz0, sz - 1)

    def clear(self, tile, ys):
        """Remove the standing tree: logs, leaves and bamboo around the tile."""
        T, y0 = self.map.T, min(ys) - 2
        x0, z0 = tile[0] * T, tile[1] * T
        for b in ("#minecraft:logs", "#minecraft:leaves", "minecraft:bamboo"):
            self.command(f"fill {x0 - 2} {y0} {z0 - 2} {x0 + T + 1} {y0 + 24} {z0 + T + 1} air replace {b}")

    def ground(self, x, z, ys, run, top=False, down=0):
        """Commands that run `run` (with {y}) at the first free block over the ground of column (x, z) of a footprint.
        Its "ground" in aoe2mc.json is the barrier top, so on a slope (#1124) a probe per height finds the ground
        block: the block is free (air, a plant or a barrier) and the block under it is not. top: the probe goes from
        the top down; down: `run` gets the y of that many blocks lower. Flat ground (one height next to the footprint)
        needs no probe: the ground is min(ys) - 1."""
        if min(ys) == max(ys):
            return [run.format(y=min(ys) - down)]
        hs = range(min(ys) - 1, max(ys) + 2)
        return [f"execute if block {x} {y} {z} {free} unless block {x} {y - 1} {z} #minecraft:replaceable "
                f"unless block {x} {y - 1} {z} minecraft:barrier run {run.format(y=y - down)}"
                for y in (reversed(hs) if top else hs) for free in ("#minecraft:replaceable", "minecraft:barrier")]

    def trunk(self, tile):
        """From the first chop the tree lies on the ground next to its stump, as in AoE2 (#308). The trunk is a row
        of logs in the footprint, with leaves on its tip, and gets one log shorter per 25 wood (at most 4 logs).
        On a slope each log lies on the ground of its column (#1124)."""
        (fx0, fx1, fz0, fz1), ys, (sx, sz), rz = self.site(tile)
        n = math.ceil(self.map.trees[tile] * min(4, fx1 - fx0) / TREE_WOOD)
        if self.trunks.get(tile) == n:
            return
        log, leaf = self.map.woods.get(tile, ("minecraft:oak_log", None))
        y, flat = min(ys), min(ys) == max(ys)
        y0, y1 = (y, y + 1) if flat else (min(ys) - 1, max(ys) + 2)
        if tile not in self.trunks:
            self.clear(tile, ys)
            self.stump(sx, sz, ys)
            for plant in () if flat else PLANTS:                     # the probe takes them for the ground
                self.command(f"fill {fx0} {y0} {rz} {fx1 - 1} {y1} {rz} air replace {plant}")
        self.trunks[tile] = n
        for old in (log, leaf) if leaf else (log,):                   # the row again as the converter made it
            self.command(f"fill {fx0} {y0} {rz} {fx1 - 1} {y1} {rz} minecraft:barrier replace {old.split('[')[0]}")
        if flat:
            for keep in ("replace minecraft:barrier", "keep"):        # not into the ground of a slope
                self.command(f"fill {fx1 - n} {y} {rz} {fx1 - 1} {y} {rz} {log}[axis=x] {keep}")
                if leaf:
                    self.command(f"fill {fx1 - n} {y + 1} {rz} {fx1 - n} {y + 1} {rz} {leaf} {keep}")
            return
        for x in range(fx1 - n, fx1):
            for c in self.ground(x, rz, ys, f"setblock {x} {{y}} {rz} {log}[axis=x]", top=True):
                self.command(c)
        if leaf:                                                      # the crown on the log of the tip
            for h in range(y0, y1 + 1):
                for free in ("#minecraft:replaceable", "minecraft:barrier"):
                    self.command(f"execute if block {fx1 - n} {h} {rz} {free} if block {fx1 - n} {h - 1} {rz} "
                                 f"{log}[axis=x] run setblock {fx1 - n} {h} {rz} {leaf}")

    def stump(self, sx, sz, ys):
        """The stump: the top of a log level with the ground of the footprint, so that nothing stops the player."""
        for c in self.ground(sx, sz, ys, f"setblock {sx} {{y}} {sz} minecraft:spruce_log[axis=y]", down=1):
            self.command(c)

    def fell(self, tile):
        """An empty tree disappears (logs, leaves, its trunk and the barriers of its footprint). A stump stays: the top
        of a log level with the ground, so that nothing stops the player (#307). The first chop (trunk) removed the
        standing tree and made the stump: on a slope fell keeps them, as a new clear removes the stump and the
        probe then finds the hole under it (#1124)."""
        (fx0, fx1, fz0, fz1), ys, (sx, sz), rz = self.site(tile)
        felled, flat = tile in self.trunks, min(ys) == max(ys)
        if not felled:
            self.clear(tile, ys)
        log, leaf = self.map.woods.get(tile, ("minecraft:oak_log", None))
        y0, y1 = (min(ys), min(ys) + 1) if flat else (min(ys) - 1, max(ys) + 2)
        for b in (log, leaf) if leaf else (log,):
            self.command(f"fill {fx0} {y0} {rz} {fx1 - 1} {y1} {rz} air replace {b.split('[')[0]}")
        self.command(f"fill {fx0} {min(ys) - 2} {fz0} {fx1 - 1} {max(ys) + 3} {fz1 - 1} air replace minecraft:barrier")
        if flat or not felled:
            self.stump(sx, sz, ys)
        feet = {(x, z) for x in range(fx0, fx1) for z in range(fz0, fz1)}
        near = [self.map.y(x, z) for x, z in self.map.around(feet)]
        if flat or near and max(near) - min(near) <= 1:            # a building may go on the stump, as in AoE2 (#3265);
            for x, z in feet:                                       # a walker crosses a step of 1 block: in de-64.3 cut
                self.map.blocked.discard((x, z))                    # trees shut lumberjacks in (#4063)
                self.map.ground[z][x] = ys[0] if flat else min(near)
        self.trunks.pop(tile, None)

    def berries(self, tile):
        """A fruit bush shows its food: full berries, fewer berries below half, a dead bush when it is empty. Only a full
        bush has the leaves in its middle: they become barriers, so the bush is small and still blocks (#590). An empty
        bush loses its barriers: its cells are free ground again."""
        food = self.map.bushes[tile]
        look = "minecraft:sweet_berry_bush[age=3]" if food > BUSH_FOOD // 2 else \
            "minecraft:sweet_berry_bush[age=2]" if food > 0 else "minecraft:dead_bush"
        if self.bushes.get(tile, "minecraft:sweet_berry_bush[age=3]") == look:      # as the converter made it
            return
        self.bushes[tile] = look
        cells = self.map.cells(tile)
        (x0, z0), (x1, z1) = min(cells), max(cells)
        ys = self.map.heights(cells)
        self.command(f"fill {x0} {min(ys) - 2} {z0} {x1} {max(ys) + 2} {z1} {look} replace minecraft:sweet_berry_bush")
        self.command(f"fill {x0} {min(ys) - 2} {z0} {x1} {max(ys) + 2} {z1} minecraft:barrier replace minecraft:oak_leaves")
        if food <= 0:                                  # as in AoE2, an empty bush frees its tile (#602)
            self.command(f"fill {x0} {min(ys) - 2} {z0} {x1} {max(ys) + 4} {z1} air replace minecraft:barrier")
            self.map.emptied(cells)

    def dig(self, tile, res):
        """An empty mine disappears: its heap and the barriers of its footprint. Its cells are free ground again."""
        spot = self.map.spot(tile)
        ys = self.map.heights(spot)
        (x0, z0), (x1, z1) = min(spot), max(spot)
        for b in MINE_BLOCKS[res] + ("barrier",):
            self.command(f"fill {x0} {min(ys)} {z0} {x1} {max(ys) + 4} {z1} air replace minecraft:{b}")
        self.map.emptied(spot)

    def tend(self, v):
        """A farmer walks over its farm while it works, as in AoE2 (#591): one cell per food, row by row (the rows
        in turn east and west), and at the last cell back the same way, so that each step goes to a next cell."""
        cells = sorted(self.goals(v.tree), key=lambda c: (c[1], c[0] if c[1] % 2 == 0 else -c[0]))
        if len(cells) < 2:
            return
        cycle = cells + cells[-2:0:-1]
        if cycle[v.lap % len(cycle)] != v.cell:                        # a new farm or another start cell
            v.lap = min(range(len(cycle)), key=lambda i: math.dist(cycle[i], v.cell))
        v.lap += 1
        walked, v.path = v.walked, [cycle[v.lap % len(cycle)]]
        walk(self, v)
        v.walked = walked                                              # work, not a walk (tools/measure_gather.py)

    def harvest(self, tile):
        """A farm shows its food: the wheat gets younger (age 7 when full), and an empty farm is dirt."""
        food = self.map.farms[tile]
        age = min(7, math.ceil(7 * food / self.map.farm_food))
        before = self.crops.get(tile, 7)
        if before == age:                                              # the converter's farm: mostly age 7
            return
        self.crops[tile] = age
        x0, x1, z0, z1 = self.map.feet[tile]
        ys = [y for x in range(x0, x1) for z in range(z0, z1) if (y := self.map.y(x, z)) is not None] or [0]
        box = f"{x0} {min(ys) - 1} {z0} {x1 - 1} {max(ys)} {z1 - 1}"
        if food > 0 and before == 0:                                   # a reseeded farm (#3283): farmland and wheat again
            self.command(f"fill {box} minecraft:farmland replace minecraft:dirt")
            self.command(f"fill {x0} {min(ys)} {z0} {x1 - 1} {max(ys)} {z1 - 1} minecraft:wheat[age={age}] replace air")
        elif food > 0:
            self.command(f"fill {box} minecraft:wheat[age={age}] replace minecraft:wheat")
        else:
            self.command(f"fill {box} air replace minecraft:wheat")
            self.command(f"fill {box} minecraft:dirt replace minecraft:farmland")

    def clear_farm(self, tile):
        """An empty farm with no reseed is ground again (#3423): no farm, no site, so a new building can stand there."""
        rect = self.map.feet.pop(tile, None)
        self.map.farms.pop(tile, None)
        self.map.own_farms.discard(tile)
        self.crops.pop(tile, None)
        self.farmers.pop(tile, None)
        self.herders.pop(tile, None)
        self.map.pastures.discard(tile)
        for c in [c for c, t in self.map.farm_at.items() if t == tile]:
            del self.map.farm_at[c]
        self.sites[:] = [s for s in self.sites if not ("FARM" in s["name"] and rect and tuple(s["footprint"]) == tuple(rect))]

    def run(self, seconds=None, until=None):
        """Play in real time until seconds passed, until() is true or the game ended (a cheat, #819)."""
        end = seconds and time.monotonic() + seconds
        while (not end or time.monotonic() < end) and not (until and until()) and not self.ended:
            t = time.monotonic()
            self.point()                                               # before clicks(): hints.tick shows its text
            for name in self.clicks():
                self.click(name)
            if getattr(self, "paused", False):                         # pause.toggle: only the clicks continue (#3374)
                time.sleep(max(0.0, self.tick / self.speed - (time.monotonic() - t)))
                continue
            self.step()
            for b in self.bots:
                b.step()
            conquest.tick(self)                                        # not in step(): the bot steps its own Gather
            if has_mode(self, "regicide"):                             # a player without its King loses (#2347)
                regicide.tick(self)
            if has_mode(self, "sudden-death"):                         # a player without its town center loses (#2407)
                sudden_death.tick(self)
            if self.mode == "battle-royale":                           # the Corruption takes the map (#2439)
                battle_royale.tick(self, self.tick * NORMAL)
            elif self.mode == "capture-the-relic":                     # the center relic in a monastery wins (#2440)
                capture_relic.tick(self)
            elif self.mode == "defend-the-wonder":                     # the attackers win when the Wonder falls (#2441)
                defend_wonder.tick(self)
            elif self.mode == "scenario":                              # the book (#2541), a trigger "Declare Victory" (#2542)
                scenario.victory(self)
                scenario.tick(self)
                scenario.resources(self)                               # "Tribute", "Modify Resource" (#2576)
            else:
                scenario.patrol(self)                                  # the patrols of the players (#3355)
            waypoint(self)                                             # the next waypoint of a move (#3515)
            stance.arrive(self)                                        # the attack moves: the old stance at the point (#3357)
            follow.tick(self)                                          # the Follow and Guard orders (#3358)
            autoscout.tick(self)                                       # the Auto Scout order (#3702)
            fog.tick(self)                                             # after the bots: their units too (#1389)
            herd.tick(self)                                            # all players: the bots capture too (#1792)
            gaia.tick(self)                                            # a Gaia unit joins the first player near it (#5108)
            if self.victory == "standard" or self.mode in wonder.RACE:  # a wonder or all relics win too (#2316)
                wonder.tick(self, self.tick * NORMAL)                  # game seconds, as train.tick
            if self.victory == "standard" and self.mode not in wonder.RACE:   # Defend the Wonder (#2441),
                                                                       # Wonder Race (#2406): only a wonder
                relic_victory.tick(self, self.tick * NORMAL)
            elif self.victory == "king-of-the-hill":                   # the monument in the center (#2360)
                hill.tick(self, self.tick * NORMAL)
            score.tick(self)
            spectator.tick(self)                                       # the sidebar of the spectators (#2900)
            if self.victory in ("time-limit", "score"):                # after the conquest: it wins before (#2356)
                time_limit.tick(self, self.tick * NORMAL)
            if self.challenge:                                         # an Art of War challenge: its goal (#3900)
                challenge.tick(self)
            treaty.tick(self, self.tick * NORMAL)
            record.tick(self, self.tick * NORMAL)                      # the game time of Record Game (#2649)
            time.sleep(max(0.0, self.tick / self.speed - (time.monotonic() - t)))   # a step stays tick game seconds


def add_waypoint(g, name, cell):
    """A sneak right click on the ground adds a waypoint, as the Shift click of AoE2 (#3515). The selected units with
    no queue walk to cell at once (the first point) and start a queue; the units with a queue get cell at the end of
    it. g.waypoints: {uuid: [cell, ...]} (the points after the present target), g.waypoint_at: {uuid: target cell}.
    Returns False without sneak: the click is a normal move order, and walk_to ends the queue (new_order)."""
    if "passed" not in g.command(f"execute as {name} if predicate {SNEAK}"):
        return False
    ways = vars(g).setdefault("waypoints", {})
    if queued := g.selected & ways.keys():
        for u in queued:
            ways[u].append(cell)
        g.mark(name, {cell})
    if new := g.selected - ways.keys():
        out = g.walk_to(name, cell, None if not queued else new)
        ways.update({u: [] for u in out})
        g.waypoint_at = vars(g).get("waypoint_at", {}) | out
    return True


def add_attack(g, name, target):
    """A sneak right click on an enemy unit or building adds an attack target, as the Shift click of AoE2 (#3516). It
    goes into the queue of the waypoints (add_waypoint) as {"attack": target}, in the click order. The selected units
    with no queue attack it at once. Returns False without sneak: the click is a normal attack order."""
    if "passed" not in g.command(f"execute as {name} if predicate {SNEAK}"):
        return False
    ways = vars(g).setdefault("waypoints", {})
    queued = g.selected & ways.keys()
    for u in queued:
        ways[u].append({"attack": target})
    if new := g.selected - queued:
        start_attack(g, new, target, None if not queued else new)
        ways.update({u: [] for u in new})
    return True


def queue_move(g, out):
    """A normal move order starts an empty queue: a later sneak click adds a point after it (#3805). out: walk_to."""
    vars(g).setdefault("waypoints", {}).update({u: [] for u in out})
    g.waypoint_at = vars(g).get("waypoint_at", {}) | out


def queue_attack(g, target):
    """A normal attack order starts an empty queue: a later sneak click adds to it (#3516)."""
    units = g.selected & g.soldiers.keys()
    vars(g).setdefault("waypoints", {}).update({u: [] for u in units})
    g.waypoint_at = vars(g).get("waypoint_at", {}) | {u: {"attack": target} for u in units}


def start_attack(g, units, target, only=None):
    """units attack target; only: the units of a queue (not the whole selection, Gather.attack). waypoint_at holds
    the target until it is dead."""
    if target in g.forts:
        g.sieged.add(target)
    g.attack(target, only)
    if only is None:
        queue_attack(g, target)
    g.waypoint_at |= {u: {"attack": target} for u in units}


def dead(g, target):
    """A queued attack target is dead: its building fell (not in g.forts) or its unit is not loaded."""
    return target not in g.forts and not g.pos(target)


def waypoint(g):
    """The units of a queue walk to its next point when one of them is scenario.NEAR blocks from its present target
    (#3515), or attack its next target when the present target is dead (#3516: a dead queued target is skipped). The
    group of a queue (the units with the same points) walks one leg at a time, in its formation (walk_to, #3414). A
    dead unit leaves its queue; an empty list ends it."""
    ways = vars(g).get("waypoints")
    if not ways:
        return
    pos = g.positions(sorted(ways))
    for u in [u for u in ways if u not in pos]:
        del ways[u]
    at = g.waypoint_at
    groups = collections.defaultdict(set)
    for u, rest in ways.items():
        groups[tuple(map(repr, rest))].add(u)
    for _, units in sorted(groups.items(), key=lambda kv: sorted(kv[1])):
        rest = ways[min(units)]
        if not any(u in at and (dead(g, at[u]["attack"]) if isinstance(at[u], dict) else
                                math.dist((pos[u][0], pos[u][2]), (at[u][0] + 0.5, at[u][1] + 0.5)) <= scenario.NEAR)
                   for u in units):
            continue
        while rest and isinstance(rest[0], dict) and dead(g, rest[0]["attack"]):
            rest = rest[1:]                                            # a dead target of the queue is skipped
        if not rest:                                                   # the last point: the queue ends
            for u in units:
                del ways[u]
            continue
        for u in units:                                                # walk_to ends the queue (new_order): keep the rest
            del ways[u]
        if isinstance(rest[0], dict):
            start_attack(g, units, rest[0]["attack"], units)
        else:
            at.update(g.walk_to(None, rest[0], units))
        ways.update({u: list(rest[1:]) for u in units})


def reseed(g, entry):
    """FARM_RESEED (the mill, #3283): one more queued reseed. An empty own farm takes it in Gather.run, as in AoE2."""
    g.reseeds = getattr(g, "reseeds", 0) + 1
    for player in g.people():
        g.command(f"tellraw {player} " + json.dumps({"text": f"Reseeds queued: {g.reseeds}", "color": "gray"}))
