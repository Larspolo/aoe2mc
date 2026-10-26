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

The program sees a click in two statistics: the use of the stick, and "talked to villager" (a right click on a
villager is an interaction with the entity, not a use of the item). Then it reads the position and the view of
the player, and finds the villager or the tree on that ray with the data of aoe2mc.json.
"""
import heapq
import json
import math
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aoe2mc import PASSABLE_OBJECTS, WOODS, object_footprint, tree_kind  # noqa: E402
from units import VILLAGER_JOBS, animal  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402
import bossbar  # noqa: E402
import menu  # noqa: E402
import train  # noqa: E402

RESOURCES = ("Wood", "Food", "Gold", "Stone")
DROP_SITES = {"wood": ("TOWN_CENTER", "LUMBER_CAMP"), "food": ("TOWN_CENTER", "MILL"),   # as in AoE2 (#389)
              "gold": ("TOWN_CENTER", "MINING_CAMP"), "stone": ("TOWN_CENTER", "MINING_CAMP")}
TREE_WOOD = 100                                                    # wood in one tree, as in AoE2
BUSH_FOOD = 125                                                    # food in one fruit bush, as in AoE2 DE
# AoE2 DE work rates per game second (#393): lumberjack 0.39 (empires2_x2_p1.dat, #267), the others the published
# DE gather rates. Normal game speed is 1.7 game seconds per real second (#413).
AOE2_WORK, NORMAL = {"wood": 0.39, "food": 0.31, "farm": 0.33, "gold": 0.38, "stone": 0.36}, 1.7
WORK_SECONDS = {r: 1 / (w * NORMAL) for r, w in AOE2_WORK.items()}    # real seconds per unit, as at Normal speed
WORK_TECHS = {"DOUBLE_BIT_AXE": {"wood": 1.2}}                     # work rate factors of the economy technologies (AoE2)
FARM_FOOD = 175                                                    # food in one farm, as in AoE2 DE (no upgrades)
MINES = {"GOLD_MINE": ("gold", 800, "GOLD_MINER"), "STONE_MINE": ("stone", 350, "STONE_MINER")}   # as in AoE2
MINE_BLOCKS = {"gold": ("gold_ore", "raw_gold_block", "stone"),                # the blocks of the converter's heap
               "stone": ("cobblestone", "andesite", "stone", "tuff")}
STEPS = [(dx, dz) for dx in (-1, 0, 1) for dz in (-1, 0, 1) if dx or dz]
NUMBER = r"(-?[\d.]+(?:E-?\d+)?)[df]"
CIVILIANS = ("VILLAGER", "REPAIRER", "MONK", "KING", "TRADE", "FISHING_SHIP", "TRANSPORT")
SELECT = "aoe2mc.selected"                                         # entity tag of the selected units
# The look and sound of one gather step at the resource (#592): block particles and a vanilla sound. A villager has
# no arm swing, so it turns to the resource (`rotate ... facing`). 26.3 block particles take
# `{id:...,Properties:{...}}`, not `Name`.
WORK_LOOK = {"wood": ("minecraft:oak_log", "minecraft:block.wood.hit"),
             "food": ("minecraft:sweet_berry_bush[age=3]", "minecraft:block.sweet_berry_bush.pick_berries"),
             "farm": ("minecraft:wheat[age=7]", "minecraft:item.hoe.till"),
             "gold": ("minecraft:gold_ore", "minecraft:block.stone.hit"),
             "stone": ("minecraft:stone", "minecraft:block.stone.hit")}
EVENTS = {"idle": "idle", "to_tree": "walk", "chop": "chop", "to_drop": "carry",    # state -> event in the log
          "to_site": "walk", "build": "build", "to_rally": "walk"}


class Map:
    """The block grid of aoe2mc.json: where a unit can stand, the trees and the drop sites of a player."""

    def __init__(self, data, player=1):
        self.T = data["tile_size"]
        self.ground = [[None if v == "-" else int(v) for v in row.split()] for row in data["ground"]]
        self.n = len(self.ground)
        self.blocked, self.trees, self.feet, self.woods, self.bushes = set(), {}, {}, {}, {}
        self.drops = {r: [] for r in DROP_SITES}                       # resource -> footprints of the drop sites
        self.mines = {r: {} for r, _, _ in MINES.values()}             # resource -> {tile: amount}
        self.mine_at = {}                                              # block cell -> tile of its mine
        self.farms, self.farm_at = {}, {}                              # farm tile -> food; block cell -> farm tile
        for o in data["objects"]:
            if o["kind"] == "building":
                x0, z0, x1, z1 = o["footprint"]
                self.building(o["name"], (x0, x1, z0, z1), (int(o["tile"][0]), int(o["tile"][1])) if "tile" in o
                              else None, o["player"] == player)
            elif o["kind"] == "other" and not any(k in o["name"] for k in PASSABLE_OBJECTS):
                tile = int(o["tile"][0]), int(o["tile"][1])
                if o["name"] in MINES:                                 # a mine at x.0 covers 2 tiles
                    res, amount, _ = MINES[o["name"]]
                    self.mines[res][tile] = amount
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

    def building(self, name, rect, tile, own):
        """Add a building with the block footprint rect = (x0, x1, z0, z1) and its center tile. A farm is ground
        that a farmer stands on; own buildings are drop sites. Construction sites call it when they are complete."""
        x0, x1, z0, z1 = rect
        cells = {(x, z) for x in range(x0, x1) for z in range(z0, z1)}
        if "FARM" in name:                                             # no barriers: the farmer stands on it
            self.farms[tile], self.feet[tile] = FARM_FOOD, rect
            self.farm_at.update(dict.fromkeys(cells, tile))
            return
        self.blocked |= cells
        for r, names in DROP_SITES.items():
            if own and any(k in name for k in names):
                self.drops[r].append(cells)

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
        """The resource of the tile of a tree, bush or mine."""
        return next((r for r, m in self.mines.items() if tile in m),
                    "food" if tile in self.bushes or tile in self.farms else "wood")

    def y(self, x, z):
        return self.ground[z][x] if 0 <= x < self.n and 0 <= z < self.n else None

    def free(self, x, z):
        return self.y(x, z) is not None and (x, z) not in self.blocked

    def around(self, cells):
        """The free cells next to a group of cells (a tree tile, a footprint)."""
        return {(x + dx, z + dz) for x, z in cells for dx, dz in STEPS if self.free(x + dx, z + dz)} - cells

    def path(self, start, goals, limit=None):
        """Shortest path (list of cells after start) to one of goals. 8 neighbours, no cut corners, steps of at
        most 1 block up or down. A* with the distance to the box of the goals. None: no path, or no path after
        `limit` cells (a far or unreachable goal on a large map)."""
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
            if limit and seen > limit:
                return None
            x, z = c
            for dx, dz in STEPS:
                n = (x + dx, z + dz)
                if not self.free(*n) or c != start and abs(self.y(*n) - self.y(x, z)) > 1:
                    continue
                if dx and dz and not (self.free(x + dx, z) and self.free(x, z + dz)):
                    continue
                nd = d + (1.414 if dx and dz else 1)
                if nd < dist.get(n, 1e9):
                    dist[n], prev[n] = nd, c
                    heapq.heappush(todo, (nd + h(*n), -nd, n))
        return None

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


def military(name):
    """True for an AoE2 unit that fights: not a villager, monk, king, trade or transport unit, and no animal."""
    return not name.startswith(CIVILIANS) and (animal(name) or ("military",))[0] == "military"


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
        self.walked = 0.0                                              # blocks, for the log
        self.res = "wood"                                              # the resource of the load
        self.site = None                                               # the construction site that it builds
        self.goal, self.moved, self.tries = None, 0.0, 0               # Paper: walk cell, time of the last step, orders
        self.lap = 0                                                   # step of a farmer over its farm (#591)

    @property
    def cell(self):
        return math.floor(self.pos[0]), math.floor(self.pos[2])


class Gather:
    """The gather game on a running server (game.command sends one command). Call setup(), then step() in a loop.
    log: a text file that gets one JSON line per event (state change or drop), to measure the timing (#289).
    chop: seconds per unit, one number for all resources or {resource: seconds} ("farm" for farms); default
    WORK_SECONDS, the AoE2 rates at Normal speed (#413)."""

    def __init__(self, game, data, player=1, tick=0.25, carry=10, chop=None, log=None, clock=time.monotonic):
        self.game, self.data, self.map, self.player = game, data, Map(data, player), player
        self.paper = getattr(game, "kind", None) == "paper"           # walks with the plugin (#437)
        chop = WORK_SECONDS if chop is None else chop
        self.tick, self.carry = tick, carry
        self.chop = dict(chop) if isinstance(chop, dict) else dict.fromkeys(WORK_SECONDS, chop)
        self.log, self.clock, self.t0 = log, clock, clock()
        self.stock = dict.fromkeys(DROP_SITES, 0)                      # resources at the drop sites
        self.units = [o for o in data["objects"] if o["kind"] == "unit" and o["player"] == player
                      and "VILLAGER" in o["name"]]
        self.villagers, self.selected = {}, set()
        self.soldiers = {o["uuid"]: o["name"] for o in data["objects"] if o["kind"] == "unit"
                         and o["player"] == player and military(o["name"])}       # military units of the player
        self.enemies = {o["uuid"]: o["name"] for o in data["objects"] if o["kind"] == "unit"
                        and o["player"] not in (0, player)}                     # units of the other players
        self.players, self.sites = data.get("players", {}), []         # construction sites (#417)
        self.farmers, self.crops = {}, {}                              # farm tile -> UUID of its farmer, wheat age
        self.trunks = {}                                               # tree tile -> logs of its trunk on the ground
        self.bushes = {}                                               # bush tile -> the block of its last look
        self.menus = {}                                                # player -> handler of its open menu (#619)
        self.bar = None                                                # the unit on the boss bar (bossbar.py, #659)
        self.queues, self.trained = {}, {}                             # town center -> its queue, units it trained
        self.techs = set()                                             # the researched technologies (train.TECHS)
        self.rally, self.rallying, self.marks = {}, {}, {}             # building -> rally point, player -> building,
        #                                                                tag of a rally marker -> AoE2 seconds left
        self.pop, self.census, self.shown = 0, 0.0, {}                 # live units, AoE2 seconds since the count, sidebar
        import combat                                                  # combat imports this module
        ground = [r.split() for r in data["ground"]]
        self.forts = {combat.target_uuid(o["footprint"]): combat.building_box(o, ground) for o in data["objects"]
                      if o["kind"] == "building" and o["player"] not in (0, player) and "footprint" in o
                      and o["name"] in combat.BUILDINGS}               # target UUID -> box of an enemy building
        self.sieged = set()                                            # the targets of attack orders

    @property
    def wood(self):
        return self.stock["wood"]

    def command(self, cmd):
        return self.game.command(cmd)

    def pos(self, target):
        m = re.findall(NUMBER, self.command(f"data get entity {target} Pos").rsplit(":", 1)[-1])
        return tuple(map(float, m)) if len(m) == 3 else None

    def setup(self):
        for cmd in ("scoreboard objectives add aoe_use minecraft.used:minecraft.carrot_on_a_stick",
                    "scoreboard objectives add aoe_talk minecraft.custom:minecraft.talked_to_villager",
                    'scoreboard objectives add aoe_res dummy "Resources"',
                    "scoreboard objectives setdisplay sidebar aoe_res"):
            self.command(cmd)
        for r in RESOURCES:
            self.command(f"scoreboard players add {r} aoe_res 0")
        build.setup(self)
        menu.setup(self)
        bossbar.setup(self)
        for o in self.units:                                           # the entities must be loaded (forceload)
            pos = self.pos(o["uuid"])
            if pos:
                self.villagers[o["uuid"]] = Villager(o["uuid"], pos)
        train.census(self)                                             # the population and the limit (#613)
        return self

    def select(self, uuid):
        """Select one villager (glowing), as a click in AoE2 does. A click on a military unit adds it to selected
        military units, as a shift click in AoE2 does."""
        keep = {uuid} | (self.selected if uuid in self.soldiers and self.selected <= set(self.soldiers) else set())
        for u in self.selected - keep:
            self.command(f"data merge entity {u} {{Glowing:0b}}")
            self.command(f"tag {u} remove {SELECT}")
        self.command(f"data merge entity {uuid} {{Glowing:1b}}")
        self.command(f"tag {uuid} add {SELECT}")
        for u in sorted(self.selected ^ keep | {uuid}):                 # the name line shows the selection (#661)
            self.command(f"aoe label {u}")
        self.selected = keep
        bossbar.show(self, uuid)                                        # the boss bar of the selection (#659)

    def attack(self, target):
        """Send the selected military units to attack the unit target, with their AoE2 walk speed (ai.py)."""
        import ai                                                      # ai imports this module
        for u in sorted(self.selected):
            self.command(ai.speed_command(u, self.soldiers[u], self.map.T))
        return self.command(f"aoe attack @e[tag={SELECT}] {target}")

    def positions(self, uuids):
        """{uuid: feet position} of the loaded units; a dead unit is not in it."""
        return {u: p for u in uuids if (p := self.pos(u))}

    def task(self, v, name):
        """Give the villager the look of its AoE2 task (`LUMBERJACK` ...), with the table of the converter."""
        job = dict(VILLAGER_JOBS).get(name, "none")
        if v.job != job:                                               # a merge keeps the level and the type
            v.job = job
            self.command(f'data merge entity {v.uuid} {{VillagerData:{{profession:"minecraft:{job}"}}}}')

    def send(self, tile, who=None):
        """Send the selected villagers (or the villagers who) to the tree, the fruit bush, the mine or the farm on tile.
        A farm takes one farmer: the next villagers go to the nearest free farms, or stop."""
        res = self.map.resource(tile)
        job = "FARMER" if tile in self.map.farms else {"wood": "LUMBERJACK", "food": "FORAGER"}.get(res) or \
            next(j for r, _, j in MINES.values() if r == res)
        for u in sorted((self.selected if who is None else who) & self.villagers.keys()):   # a scout cannot (#589)
            v = self.villagers[u]
            for t in [t for t, f in self.farmers.items() if f == u]:
                del self.farmers[t]
            to = tile
            if tile in self.map.farms:
                v.tree = None
                free = [t for t, k in self.map.farms.items() if k > 0 and t not in self.farmers]
                to = tile if tile in free else min(free, key=lambda t: math.dist(t, tile), default=None)
                if to is None:
                    self.set(v, "idle")
                    continue
                self.farmers[to] = u
            self.task(v, job)
            if v.load and v.res != res:
                v.load = 0                                             # AoE2 drops a load of another resource
            v.res, v.tree, v.site = res, to, None
            self.go(v, "to_tree", self.goals(to))

    def build(self, site):
        """Send the selected villagers to build the construction site, with the builder look (#418). They keep
        their load, as in AoE2."""
        x0, x1, z0, z1 = site["footprint"]
        goals = self.map.around({(x, z) for x in range(x0, x1) for z in range(z0, z1)})
        for u in sorted(self.selected & self.villagers.keys()):         # a scout cannot gather or build (#589)
            v = self.villagers[u]
            for t in [t for t, f in self.farmers.items() if f == u]:
                del self.farmers[t]
            v.tree, v.site = None, site
            self.task(v, "BUILDER")
            self.go(v, "to_site", goals)

    def goals(self, tile):
        """The cells where a villager works a resource: on a farm, else next to it."""
        spot = self.map.spot(tile)
        return {c for c in spot if self.map.free(*c)} if tile in self.map.farms else self.map.around(spot)

    def source(self, v):
        """The resources left in the tree, bush, mine or farm of a villager: {tile: amount} of its kind."""
        if v.tree in self.map.farms:
            return self.map.farms
        return self.map.bushes if v.res == "food" else self.map.trees if v.res == "wood" else self.map.mines[v.res]

    def nearest(self, v):
        """The nearest bush or mine of the resource of v with something left, or None."""
        T = self.map.T
        full = [t for t, k in self.source(v).items() if k > 0]
        return min(full, key=lambda t: math.dist(v.cell, ((t[0] + 0.5) * T, (t[1] + 0.5) * T)), default=None)

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

    def event(self, v, name):
        if self.log:
            self.log.write(json.dumps({"t": round(self.clock() - self.t0, 3), "villager": v.uuid, "event": name,
                                       "pos": [round(c, 2) for c in v.pos], "walked": round(v.walked, 2),
                                       "load": v.load, "wood": self.wood}) + "\n")
            self.log.flush()

    def clicks(self):
        """Players who clicked since the last call. Clicks in a chest menu go to the handler of the menu (#619)."""
        build.tick(self)
        menu.clicks(self)
        self.command("execute as @a unless items entity @s container.* minecraft:carrot_on_a_stick "
                     "run give @s minecraft:carrot_on_a_stick")
        if "passed" not in self.command("execute if entity @a[scores={aoe_use=1..}]") + \
                self.command("execute if entity @a[scores={aoe_talk=1..}]"):
            return []
        out = []
        for name in (n.strip() for n in self.command("list").split(":", 1)[-1].split(",")):
            if name and any(re.search(r"has [1-9]", self.command(f"scoreboard players get {name} {obj}"))
                            for obj in ("aoe_use", "aoe_talk")):
                out.append(name)
                for obj in ("aoe_use", "aoe_talk"):
                    self.command(f"scoreboard players reset {name} {obj}")
        return out

    def click(self, name):
        pos = self.pos(name)
        rot = re.findall(NUMBER, self.command(f"data get entity {name} Rotation").rsplit(":", 1)[-1])
        if not pos or len(rot) != 2:
            return
        eye, d = (pos[0], pos[1] + 1.62, pos[2]), direction(*map(float, rot))
        if (rect := self.rallying.pop(name, None)) and (cell := self.map.pick_ground(eye, d)):   # the menu item (#707)
            train.rally(self, rect, cell, self.map.pick_tree(eye, d))
            return
        army = self.selected and self.selected <= set(self.soldiers)
        u = pick_unit(eye, d, {k: v.pos for k, v in self.villagers.items()} |
                      self.positions(list(self.soldiers) + (list(self.enemies) if army else [])))
        if u in self.enemies:
            self.attack(u)
            return
        if u and u in self.selected and u in self.villagers:         # a click on a selected villager (#621)
            build.open_menu(self, name)
            return
        if u:
            self.select(u)
            return
        if army and (fort := self.pick_fort(eye, d)):
            self.sieged.add(fort)
            self.attack(fort)
            return
        building = build.chosen(self, name)
        if building:                                                   # a chosen building: place its foundation
            build.place(self, name, building, eye, d)
            return
        if train.open_menu(self, name, self.map.pick_ground(eye, d)):  # an own town center or barracks (#620, #654)
            return
        tile = self.map.pick_tree(eye, d)
        if tile and self.selected:
            self.send(tile)
        elif self.selected and (site := build.pick(self, eye, d)):
            self.build(site)

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
            x0, y0, z0, x1, _, z1 = self.forts.pop(uuid)
            for x in range(x0, x1 + 1):
                for z in range(z0, z1 + 1):
                    self.map.blocked.discard((x, z))
                    self.map.ground[z][x] = y0                         # the plugin filled the box with air

    def step(self):
        """One tick: walk one block, chop, drop the wood, or build."""
        self.fall()
        for v in self.villagers.values():
            if v.state in ("to_tree", "to_drop", "to_site", "to_rally") and v.path:
                self.follow(v) if self.paper else walk(self, v)
            elif v.state == "to_rally":
                self.set(v, "idle")
            elif v.state == "to_site":
                self.set(v, "build" if v.site["progress"] < 1 else "idle")
            elif v.state == "to_tree":
                v.timer = 0.0
                self.set(v, "chop" if self.source(v).get(v.tree, 0) > 0 else "idle")
            elif v.state == "to_drop":
                self.command(f"scoreboard players add {v.res.capitalize()} aoe_res {v.load}")
                self.stock[v.res] += v.load
                v.load = 0
                self.event(v, "drop")
                if v.tree in self.map.farms:
                    if self.map.farms[v.tree] <= 0:                    # an empty farm: the farmer stops
                        self.farmers.pop(v.tree, None)
                        v.tree = None
                elif v.res != "wood" and self.source(v).get(v.tree, 0) <= 0:
                    v.tree = self.nearest(v)                           # as in AoE2: the next bush or mine, or stop
                if self.source(v).get(v.tree, 0) > 0:
                    self.go(v, "to_tree", self.goals(v.tree))
                else:
                    self.set(v, "idle")
            elif v.state == "chop":
                v.timer += self.tick
                src = self.source(v)
                work = self.work_time("farm" if v.tree in self.map.farms else v.res)
                while v.timer >= work and v.load < self.carry and src.get(v.tree, 0) > 0:
                    v.timer -= work
                    v.load += 1
                    src[v.tree] -= 1
                    self.work(v)
                    if v.tree in self.map.farms:
                        self.harvest(v.tree)
                        self.tend(v)
                    elif v.res == "food":
                        self.berries(v.tree)
                    elif v.res != "wood":
                        if src[v.tree] == 0:
                            self.dig(v.tree, v.res)
                    elif src[v.tree] == 0:
                        self.fell(v.tree)
                    else:
                        self.trunk(v.tree)
                if v.load >= self.carry or src.get(v.tree, 0) <= 0:
                    self.go(v, "to_drop", set().union(*map(self.map.around, self.map.drops[v.res])))
        train.tick(self, self.tick * NORMAL)
        bossbar.tick(self)
        for site in self.sites:
            builders = [v for v in self.villagers.values() if v.state == "build" and v.site is site]
            # AoE2: n builders need 3 / (n + 2) of the time of one
            if builders and build.rise(self, site, self.tick * NORMAL * (len(builders) + 2) / 3):
                for v in builders:                                     # complete: the builders stop
                    v.site = None
                    self.set(v, "idle")

    def work_time(self, res):
        """Real seconds per unit of resource res ("farm" for farms) with the technologies of the player (WORK_TECHS)."""
        return self.chop[res] / math.prod(WORK_TECHS.get(t, {}).get(res, 1) for t in self.techs)

    def move(self, v):
        import ai                                                      # ai imports gather
        if v.goal:
            x, z = v.goal
            ai.move(self, v.uuid, "VILLAGER", self.map.T, x + 0.5, self.map.y(x, z), z + 0.5)
        v.moved, v.tries = self.clock(), v.tries + 1

    def follow(self, v):
        """Paper: read the position of a walking villager. It arrives 1.5 blocks from the center of its goal cell (there
        the plugin stops a villager, #438), or when it stands still for 1 s near it; still for 5 s far from it after
        two orders, it found no path and stops (#437)."""
        pos = self.pos(v.uuid)
        if not pos:
            return
        step, v.pos, now = math.dist(pos, v.pos), pos, self.clock()
        v.walked += step
        v.moved = now if step >= 0.05 else v.moved
        far, still = math.dist((pos[0], pos[2]), (v.goal[0] + 0.5, v.goal[1] + 0.5)), now - v.moved
        if still >= 5 and far >= 2 and v.tries < 2:                    # a second order, as the plugin drops one
            self.move(v)
        elif far < 1.5 or still >= 1 and far < 2 or still >= 5:
            self.command(f"aoe stop {v.uuid}")
            v.path = []
            if far >= 2:
                self.set(v, "idle")

    def work(self, v):
        """One gather step shows: the villager turns to the point of the resource next to it, block particles of the
        resource fly there, and the work sound plays (#592)."""
        tile, T = v.tree, self.map.T
        x0, x1, z0, z1 = self.map.feet.get(tile, (tile[0] * T, tile[0] * T + T, tile[1] * T, tile[1] * T + T))
        x, y, z = min(max(v.pos[0], x0 + 0.5), x1 - 0.5), v.pos[1] + 1, min(max(v.pos[2], z0 + 0.5), z1 - 0.5)
        kind = "farm" if tile in self.map.farms else v.res
        block, sound = WORK_LOOK[kind]
        if kind == "wood":
            block = self.map.woods.get(tile, (block,))[0]
        name, _, props = block.partition("[")
        props = ",".join(f'{k}:"{w}"' for k, w in (p.split("=") for p in props.rstrip("]").split(",") if p))
        state = f'{{id:"{name}"' + (f",Properties:{{{props}}}" if props else "") + "}"
        at = f"{x:.2f} {y:.2f} {z:.2f}"
        self.command(f"rotate {v.uuid} facing {at}")
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
        sx, sz = (fx0 + fx1) // 2, (fz0 + fz1) // 2
        return (fx0, fx1, fz0, fz1), ys, (sx, sz), max(fz0, sz - 1)

    def clear(self, tile, ys):
        """Remove the standing tree: logs, leaves and bamboo around the tile."""
        T, y0 = self.map.T, min(ys) - 2
        x0, z0 = tile[0] * T, tile[1] * T
        for b in ("#minecraft:logs", "#minecraft:leaves", "minecraft:bamboo"):
            self.command(f"fill {x0 - 2} {y0} {z0 - 2} {x0 + T + 1} {y0 + 24} {z0 + T + 1} air replace {b}")

    def trunk(self, tile):
        """From the first chop the tree lies on the ground next to its stump, as in AoE2 (#308). The trunk is a row
        of logs in the footprint, with leaves on its tip, and gets one log shorter per 25 wood (at most 4 logs)."""
        (fx0, fx1, fz0, fz1), ys, (sx, sz), rz = self.site(tile)
        n = math.ceil(self.map.trees[tile] * min(4, fx1 - fx0) / TREE_WOOD)
        if self.trunks.get(tile) == n:
            return
        log, leaf = self.map.woods.get(tile, ("minecraft:oak_log", None))
        y = min(ys)
        if tile not in self.trunks:
            self.clear(tile, ys)
            self.command(f"setblock {sx} {y - 1} {sz} minecraft:spruce_log[axis=y]")
        self.trunks[tile] = n
        for old in (log, leaf) if leaf else (log,):                   # the row again as the converter made it
            self.command(f"fill {fx0} {y} {rz} {fx1 - 1} {y + 1} {rz} minecraft:barrier replace {old.split('[')[0]}")
        for keep in ("replace minecraft:barrier", "keep"):            # not into the ground of a slope
            self.command(f"fill {fx1 - n} {y} {rz} {fx1 - 1} {y} {rz} {log}[axis=x] {keep}")
            if leaf:
                self.command(f"fill {fx1 - n} {y + 1} {rz} {fx1 - n} {y + 1} {rz} {leaf} {keep}")

    def fell(self, tile):
        """An empty tree disappears (logs, leaves, its trunk and the barriers of its footprint). A stump stays: the top
        of a log level with the ground, so that nothing stops the player (#307)."""
        (fx0, fx1, fz0, fz1), ys, (sx, sz), rz = self.site(tile)
        self.clear(tile, ys)
        log = self.map.woods.get(tile, ("minecraft:oak_log", None))[0]
        self.command(f"fill {fx0} {min(ys)} {rz} {fx1 - 1} {min(ys) + 1} {rz} air replace {log}")
        self.command(f"fill {fx0} {min(ys) - 2} {fz0} {fx1 - 1} {max(ys) + 3} {fz1 - 1} air replace minecraft:barrier")
        self.command(f"setblock {sx} {min(ys) - 1} {sz} minecraft:spruce_log[axis=y]")
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
        ys = [y for x, z in self.map.around(cells) if (y := self.map.y(x, z)) is not None] or [0]
        self.command(f"fill {x0} {min(ys) - 2} {z0} {x1} {max(ys) + 2} {z1} {look} replace minecraft:sweet_berry_bush")
        self.command(f"fill {x0} {min(ys) - 2} {z0} {x1} {max(ys) + 2} {z1} minecraft:barrier replace minecraft:oak_leaves")
        if food <= 0:                                  # as in AoE2, an empty bush frees its tile (#602)
            self.command(f"fill {x0} {min(ys) - 2} {z0} {x1} {max(ys) + 4} {z1} air replace minecraft:barrier")
            for x, z in cells:
                self.map.ground[z][x] = min(ys)
            self.map.blocked -= cells

    def dig(self, tile, res):
        """An empty mine disappears: its heap and the barriers of its footprint. Its cells are free ground again."""
        spot = self.map.spot(tile)
        ys = [y for x, z in self.map.around(spot) if (y := self.map.y(x, z)) is not None] or [0]
        (x0, z0), (x1, z1) = min(spot), max(spot)
        for b in MINE_BLOCKS[res] + ("barrier",):
            self.command(f"fill {x0} {min(ys)} {z0} {x1} {max(ys) + 4} {z1} air replace minecraft:{b}")
        for x, z in spot:
            self.map.ground[z][x] = min(ys)
            self.map.mine_at.pop((x, z), None)
        self.map.blocked -= spot

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
        age = math.ceil(7 * food / FARM_FOOD)
        if self.crops.get(tile, 7) == age:                             # the converter's farm: mostly age 7
            return
        self.crops[tile] = age
        x0, x1, z0, z1 = self.map.feet[tile]
        ys = [y for x in range(x0, x1) for z in range(z0, z1) if (y := self.map.y(x, z)) is not None] or [0]
        box = f"{x0} {min(ys) - 1} {z0} {x1 - 1} {max(ys)} {z1 - 1}"
        if food > 0:
            self.command(f"fill {box} minecraft:wheat[age={age}] replace minecraft:wheat")
        else:
            self.command(f"fill {box} air replace minecraft:wheat")
            self.command(f"fill {box} minecraft:dirt replace minecraft:farmland")

    def run(self, seconds=None, until=None):
        """Play in real time until seconds passed or until() is true."""
        end = seconds and time.time() + seconds
        while (not end or time.time() < end) and not (until and until()):
            t = time.time()
            for name in self.clicks():
                self.click(name)
            self.step()
            time.sleep(max(0.0, self.tick - (time.time() - t)))
