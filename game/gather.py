"""
Villagers gather wood: the first playable milestone of docs/research/gameplay.md (#138).

The player holds the command stick (`carrot_on_a_stick`). A right click on a villager of player 1 selects it
(glowing). A right click on a tree sends the selected villagers there. A villager walks on a path around
buildings, trees and water (one /tp per block), chops, carries the wood to the nearest town center or lumber
camp, and goes back to the tree. A sidebar scoreboard shows wood, food, gold and stone of player 1.

The program sees a click in two statistics: the use of the stick, and "talked to villager" (a right click on a
villager is an interaction with the entity, not a use of the item). Then it reads the position and the view of
the player, and finds the villager or the tree on that ray with the data of aoe2mc.json.
"""
import heapq
import math
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aoe2mc import PASSABLE_OBJECTS  # noqa: E402

RESOURCES = ("Wood", "Food", "Gold", "Stone")
DROP_SITES = ("TOWN_CENTER", "LUMBER_CAMP")
TREE_WOOD = 100                                                    # wood in one tree, as in AoE2
STEPS = [(dx, dz) for dx in (-1, 0, 1) for dz in (-1, 0, 1) if dx or dz]
NUMBER = r"(-?[\d.]+(?:E-?\d+)?)[df]"


class Map:
    """The block grid of aoe2mc.json: where a unit can stand, the trees and the drop sites of a player."""

    def __init__(self, data, player=1):
        self.T = data["tile_size"]
        self.ground = [[None if v == "-" else int(v) for v in row.split()] for row in data["ground"]]
        self.n = len(self.ground)
        self.blocked, self.trees, self.drops = set(), {}, []
        for o in data["objects"]:
            if o["kind"] == "building":
                x0, z0, x1, z1 = o["footprint"]
                cells = {(x, z) for x in range(x0, x1) for z in range(z0, z1)}
                self.blocked |= cells
                if o["player"] == player and any(k in o["name"] for k in DROP_SITES):
                    self.drops.append(cells)
            elif o["kind"] == "other" and not any(k in o["name"] for k in PASSABLE_OBJECTS):
                tile = int(o["tile"][0]), int(o["tile"][1])
                self.blocked |= self.cells(tile)
                if "TREE" in o["name"]:
                    self.trees[tile] = TREE_WOOD

    def cells(self, tile):
        T = self.T
        return {(x, z) for x in range(tile[0] * T, tile[0] * T + T) for z in range(tile[1] * T, tile[1] * T + T)}

    def y(self, x, z):
        return self.ground[z][x] if 0 <= x < self.n and 0 <= z < self.n else None

    def free(self, x, z):
        return self.y(x, z) is not None and (x, z) not in self.blocked

    def around(self, cells):
        """The free cells next to a group of cells (a tree tile, a footprint)."""
        return {(x + dx, z + dz) for x, z in cells for dx, dz in STEPS if self.free(x + dx, z + dz)} - cells

    def path(self, start, goals):
        """Shortest path (list of cells after start) to one of goals. 8 neighbours, no cut corners, steps of at
        most 1 block up or down. None: no path."""
        if not goals:
            return None
        dist, prev, todo = {start: 0}, {}, [(0, start)]
        while todo:
            d, c = heapq.heappop(todo)
            if c in goals:
                out = []
                while c != start:
                    out.append(c)
                    c = prev[c]
                return out[::-1]
            if d > dist[c]:
                continue
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
                    heapq.heappush(todo, (nd, n))
        return None

    def pick_tree(self, eye, d, reach=64):
        """The tree tile that the ray from eye in direction d hits first, or None."""
        for k in range(1, reach * 4):
            x, y, z = (eye[i] + d[i] * k / 4 for i in range(3))
            bx, bz = math.floor(x), math.floor(z)
            if not (0 <= bx < self.n and 0 <= bz < self.n):
                return None
            tile = bx // self.T, bz // self.T
            g = self.y(bx, bz)
            if tile in self.trees and (g is None or y < g + 12):
                return tile
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


class Villager:
    def __init__(self, uuid, pos):
        self.uuid, self.pos = uuid, pos
        self.state, self.path, self.tree, self.load, self.timer = "idle", [], None, 0, 0.0

    @property
    def cell(self):
        return math.floor(self.pos[0]), math.floor(self.pos[2])


class Gather:
    """The gather game on a running server (game.command sends one command). Call setup(), then step() in a loop."""

    def __init__(self, game, data, player=1, tick=0.25, carry=10, chop=1.0):
        self.game, self.map, self.player = game, Map(data, player), player
        self.tick, self.carry, self.chop = tick, carry, chop
        self.units = [o for o in data["objects"] if o["kind"] == "unit" and o["player"] == player
                      and "VILLAGER" in o["name"]]
        self.villagers, self.selected = {}, set()

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
        for o in self.units:                                           # the entities must be loaded (forceload)
            pos = self.pos(o["uuid"])
            if pos:
                self.villagers[o["uuid"]] = Villager(o["uuid"], pos)
        return self

    def select(self, uuid):
        """Select one villager (glowing), as a click in AoE2 does."""
        for u in self.selected - {uuid}:
            self.command(f"data merge entity {u} {{Glowing:0b}}")
        self.selected = {uuid}
        self.command(f"data merge entity {uuid} {{Glowing:1b}}")

    def send(self, tile):
        """Send the selected villagers to the tree on tile."""
        for u in self.selected:
            v = self.villagers[u]
            v.tree = tile
            self.go(v, "to_tree", self.map.around(self.map.cells(tile)))

    def go(self, v, state, goals):
        path = self.map.path(v.cell, goals)
        v.state, v.path = (state, path) if path is not None else ("idle", [])

    def clicks(self):
        """Players who clicked since the last call."""
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
        u = pick_unit(eye, d, {k: v.pos for k, v in self.villagers.items()})
        if u:
            self.select(u)
            return
        tile = self.map.pick_tree(eye, d)
        if tile and self.selected:
            self.send(tile)

    def step(self):
        """One tick: walk one block, chop, or drop the wood."""
        for v in self.villagers.values():
            if v.state in ("to_tree", "to_drop") and v.path:
                x, z = v.path.pop(0)
                dx, dz = x + 0.5 - v.pos[0], z + 0.5 - v.pos[2]
                v.pos = (x + 0.5, float(self.map.y(x, z)), z + 0.5)
                yaw = math.degrees(math.atan2(-dx, dz))
                self.command(f"tp {v.uuid} {v.pos[0]} {v.pos[1]} {v.pos[2]} {yaw:.0f} 0")
            elif v.state == "to_tree":
                v.state, v.timer = ("chop", 0.0) if self.map.trees.get(v.tree, 0) > 0 else ("idle", 0.0)
            elif v.state == "to_drop":
                self.command(f"scoreboard players add Wood aoe_res {v.load}")
                v.load = 0
                if self.map.trees.get(v.tree, 0) > 0:
                    self.go(v, "to_tree", self.map.around(self.map.cells(v.tree)))
                else:
                    v.state = "idle"
            elif v.state == "chop":
                v.timer += self.tick
                while v.timer >= self.chop and v.load < self.carry and self.map.trees.get(v.tree, 0) > 0:
                    v.timer -= self.chop
                    v.load += 1
                    self.map.trees[v.tree] -= 1
                    if self.map.trees[v.tree] == 0:
                        self.fell(v.tree)
                if v.load >= self.carry or self.map.trees.get(v.tree, 0) <= 0:
                    self.go(v, "to_drop", set().union(*map(self.map.around, self.map.drops)))

    def fell(self, tile):
        """An empty tree disappears (logs and leaves)."""
        T, ys = self.map.T, [y for x, z in self.map.cells(tile) if (y := self.map.y(x, z)) is not None]
        x0, z0, y0 = tile[0] * T, tile[1] * T, min(ys, default=0) - 2
        for b in ("#minecraft:logs", "#minecraft:leaves"):
            self.command(f"fill {x0 - 2} {y0} {z0 - 2} {x0 + T + 1} {y0 + 24} {z0 + T + 1} air replace {b}")

    def run(self, seconds=None):
        end = seconds and time.time() + seconds
        while not end or time.time() < end:
            t = time.time()
            for name in self.clicks():
                self.click(name)
            self.step()
            time.sleep(max(0.0, self.tick - (time.time() - t)))
