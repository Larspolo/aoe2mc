"""
Replay a recorded game live (#374): play the "timeline" of aoe2mc.json (aoe2mc.read_timeline, #372) on a running
server. Each building appears at its command time (the blocks of its design, as with --at, #373), chat lines are
/tellraw in the player color, age-ups are a title, research is an action bar line, and RESIGN is a title.
A trained unit appears in front of its building when its training ends (#408, aoe2mc.training). The units that a
MOVE or ORDER command selects walk to its target: on Paper the plugin walks them on a Minecraft path at their walk speed
(`aoe moveto`, game/ai.py, #438), else one /tp per block on the path of gather.Map (#409, gather.walk);
a group that goes to a tile stops there in rows (#410).
Fights (#632): on Paper an ORDER on a unit or a start building of another player sends the military units of the
selection to attack it (`aoe attack`, the mob AI and the AoE2 values of game/combat.py); a unit at 0 hit points dies by
itself. A trained unit gets its AoE2 values at its spawn (`aoe stats`, `aoe range`); game/run.py gives them to the
units and buildings of the start state (combat.setup).

Replay(game, data).run(speed) plays it; commands(e) gives the commands of one event (the unit tests use it).
With bar=True (game/run.py --replay) a boss bar shows the game time, the speed and the progress (#684).
"""
import json
import math
import os
import sys
import time
import types

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import aoe2mc  # noqa: E402
import buildings  # noqa: E402
import units  # noqa: E402

# Dye color of a player (aoe2mc.PLAYER_COLORS) -> text color of /tellraw and /title
TEXT_COLORS = {"light_gray": "gray", "blue": "blue", "red": "red", "green": "green", "yellow": "yellow",
               "cyan": "aqua", "purple": "light_purple", "gray": "dark_gray", "orange": "gold"}
FLAT = 16                   # tiles of the flat map that draws one design
MAX_FILL = 32768            # blocks of one /fill command
FORMATION = 2              # blocks between the units of a group in a formation (#410)
LEG = 48                    # path cells of one plugin order: within the reach of a Minecraft path search (#438)
TALL = 48                   # blocks above the ground that a DELETE clears for a start building (no height in aoe2mc.json)
BAR = "aoe2mc:replay"       # the boss bar with the game time (#684)
POLL = 0.2                  # seconds between two calls of the poll of Replay.run while it waits (#685)
NEXT = 5                    # tiles: an empty resource sends its villager to the next one this near (#720)
PATH_CELLS = 20000          # cells that one path search may look at: a unit with no path stays (no time lag)
SPEEDS = {"VILLAGER": 0.8, "MILITIA": 0.9, "MAN_AT_ARMS": 0.9, "SPEARMAN": 1.0, "PIKEMAN": 1.0, "EAGLE": 1.1,
          "ARCHER": 0.96, "SKIRMISHER": 0.96, "CROSSBOWMAN": 0.96, "CAVALRY_ARCHER": 1.4, "SCOUT": 1.2,
          "LIGHT_CAVALRY": 1.5, "KNIGHT": 1.35, "CAMEL": 1.45, "MONK": 0.7, "BATTERING_RAM": 0.5, "MANGONEL": 0.6,
          "SCORPION": 0.65, "TRADE_CART": 1.0}   # walk speed of common units, tiles per game second (AoE2 DE)


def pretty(name):
    return name.replace("_", " ").title()


def text(s, color=None):
    return {"text": s, "color": color} if color else {"text": s}


class Replay:
    """The timeline of aoe2mc.json `data` on a server (game.command sends one command)."""

    def __init__(self, game, data, version=aoe2mc.VERSION_NAME, ai=False):
        self.game, self.data, self.ai, self.speed, self.paused = game, data, ai, 1.0, False  # ai: plugin walks
        self.T, self.n = data["tile_size"], len(data["ground"])
        self.ground = [[None if v == "-" else int(v) for v in row.split()] for row in data["ground"]]
        self.starts = [(o.get("ref"), o["player"], o["name"], (o["footprint"][0], o["footprint"][2], o["footprint"][1],
                        o["footprint"][3])) for o in data["objects"] if o["kind"] == "building" and "footprint" in o]
        self.placed, self.map, self.added = [], None, 0        # buildings of the replay, gather.Map, placed in the map
        self.tops = {}                                          # top block y per footprint of a replay building
        self.trained = {}                                       # units per building footprint
        self.units, self.new = {}, []           # object ID -> gather.Villager; spawned units without a known ID
        self.moving = {}                        # object ID -> game time (ms) of its next step
        self.working = {}                       # object ID -> game time (ms) of its next gather step (#631)
        self.refs = {o["ref"]: o for o in data["objects"] if o.get("ref") is not None}
        self.rng = np.random.default_rng(1)
        self.kinds, self.seen = aoe2mc.object_kinds(), set()
        self.sent, self.busy = 0, 0.0           # commands sent, seconds spent sending them

    def player(self, p):
        info = self.data["players"].get(str(p), {})
        return f"Player {p}" + (f" ({pretty(info['civ'])})" if info.get("civ") else ""), \
            TEXT_COLORS.get(info.get("color"), "white")

    def commands(self, e):
        """The commands of one timeline event (an empty list for the events that change nothing visible)."""
        kind = e["kind"]
        if kind in ("build", "wall") and "type" in e and "tile" in e:
            return self.build(e)
        if kind == "spawn":
            return self.spawn(e)
        if kind in ("move", "order") and e.get("objects"):
            return self.move(e)
        if kind == "delete" and e.get("objects"):
            return self.delete(e)
        if kind == "chat" and e.get("text"):
            name, color = self.player(e["player"]) if e.get("player") else ("Game", "white")
            return ["tellraw @a " + json.dumps([text(f"<{name}> ", color), text(e["text"])])]
        name, color = self.player(e.get("player"))
        if kind == "age" and e.get("age"):
            return ["title @a subtitle " + json.dumps(text(name, color)),
                    "title @a title " + json.dumps(text(pretty(e["age"])))]
        if kind == "research" and e.get("technology"):
            return ["title @a actionbar " + json.dumps([text(name, color), text(f" researches {e['technology']}")])]
        if kind == "resign":
            return ["title @a subtitle " + json.dumps(text("The game ends")),
                    "title @a title " + json.dumps(text(f"{name} resigns", color))]
        return []

    def build(self, e):
        """BUILD and WALL as in aoe2mc.apply_timeline: one building per tile, a second click on the same
        foundation places nothing."""
        prefix, name = self.kinds.get(e["type"], ("?", ""))
        if prefix != "B":
            return []
        tiles = [(x + 0.5, y + 0.5) for x, y in aoe2mc.wall_tiles(*e["tile"], *e["end"])] if e["kind"] == "wall" \
            else [tuple(e["tile"])]
        out = []
        for x, y in tiles:
            if (name, x, y) not in self.seen:
                self.seen.add((name, x, y))
                k = len(self.placed)
                out += self.building(name, e["player"], x, y)
                if len(self.placed) > k:
                    out += self.push_out(self.placed[-1][2])
        return out

    def push_out(self, rect):
        """The units in the footprint of a new building step out to the nearest free cell, as in AoE2 (a unit in a
        block suffocates; the replay does not know all walks)."""
        x0, x1, z0, z1 = rect
        cells = {(x, z) for x in range(x0, x1) for z in range(z0, z1)}
        self.grid()
        free = self.map.around(cells)
        out = []
        for i, v in list(self.units.items()) + [(None, v) for _, v in self.new]:
            if v.cell in cells and free and "FARM" not in self.placed[-1][1]:
                v.path = [min(free, key=lambda c: (math.dist(c, v.cell), c))]
                self.gather.walk(types.SimpleNamespace(map=self.map, command=out.append), v)
                self.moving.pop(i, None)                                # it stops there
        return out

    def building(self, name, player, x, y):
        """The commands that draw one building at tile (x, y): its design on a flat map (like render.py), moved to
        the ground of the world. The footprint is cleared first; a foundation fills the air under the floor."""
        T, info = self.T, self.data["players"].get(str(player), {})
        ox, oy = int(x) - FLAT // 2, int(y) - FLAT // 2            # whole tiles: the same rounding as in place_building
        cols = aoe2mc.Columns(FLAT, np.zeros((FLAT, FLAT), np.int16), np.zeros((FLAT, FLAT), np.float32),
                              {0: "GRASS_1"}, T, self.data["level_height"], np.random.default_rng(1))
        E = aoe2mc.Edits(cols)
        players = {player: {"arch": info.get("arch", "western"), "color": info.get("color", "light_gray")}}
        o = dict(kind="B", name=name, player=player, x=x - ox, y=y - oy, rotation=0.0, hero=False, garrisoned=False)
        walls, gates = buildings.plan_walls([o])
        buildings.place_building(E, cols, aoe2mc.B, o, players, walls, gates)
        if not E.parts or "footprint" not in o:
            return []
        fx0, fz0, fx1, fz1 = o["footprint"]
        dx, dz = ox * T, oy * T
        cells = [self.ground[z][x] for x in range(max(0, fx0 + dx), min(self.n, fx1 + dx))
                 for z in range(max(0, fz0 + dz), min(self.n, fz1 + dz))]
        cells = [g for g in cells if g is not None]
        if not cells:                                               # outside the map or on water only
            return []
        flat = cols.surface(fx0, fz0)                               # the floor of the flat map
        base, low = max(cells), min(cells)
        dy = base - flat
        last = {}                                                   # later edits replace earlier ones
        for xs, ys, zs, ids, _ in E.parts:
            for p in zip(xs.tolist(), ys.tolist(), zs.tolist(), ids.tolist()):
                last[p[:3]] = p[3]
        blocks = {(bx + dx, by + dy, bz + dz): i for (bx, by, bz), i in last.items() if i}
        if not blocks:
            return []
        top = max(k[1] for k in blocks)
        x0, x1, z0, z1 = fx0 + dx, fx1 + dx - 1, fz0 + dz, fz1 + dz - 1
        self.placed.append((player, name, (x0, x1 + 1, z0, z1 + 1)))
        self.tops[self.placed[-1][2]] = top
        out = self.fill(x0, base, z0, x1, top, z1, "air")
        if low < base - 1:                                          # the floor replaces the top ground block
            out += self.fill(x0, low, z0, x1, base - 2, z1, self.state(aoe2mc.B(buildings.ARCH[players[player][
                "arch"]].stone2)) + " keep")
        rows = {}
        for (bx, by, bz), i in blocks.items():
            rows.setdefault((by, bz), []).append((bx, i))
        for (by, bz), row in sorted(rows.items()):                 # from the bottom up, runs along x as one /fill
            row.sort()
            start = 0
            for k in range(1, len(row) + 1):
                if k == len(row) or row[k][1] != row[start][1] or row[k][0] != row[k - 1][0] + 1:
                    (ax, i), bx = row[start], row[k - 1][0]
                    s = self.state(i)
                    out.append(f"setblock {ax} {by} {bz} {s}" if ax == bx else f"fill {ax} {by} {bz} {bx} {by} {bz} {s}")
                    start = k
        return out

    def delete(self, e):
        """DELETE: a unit dies (/kill: the death animation of Minecraft) and stops; a building falls (/fill ... air
        destroy: the block particles and drops) and its cells are free for the paths again. A new ID with a building
        name takes the newest replay building of the player with that name (a cancelled foundation, as in AoE2). An
        ID that the replay does not know changes nothing."""
        self.grid()
        out = []
        for i, name in zip(e["objects"], e.get("names") or [None] * len(e["objects"])):
            start = next((s for s in self.starts if s[0] == i), None)
            new = None if start or not name else next(
                (k for k in range(len(self.placed) - 1, -1, -1) if self.placed[k][:2] == (e["player"], name)), None)
            if start or new is not None:
                self.refs.pop(i, None)                              # no ORDER goes to it
                rect = start[3] if start else self.placed[new][2]
                if start:
                    self.starts.remove(start)
                else:
                    del self.placed[new]
                    self.added -= 1
                out += self.fall(rect)
            elif (v := self.unit(i, name, e["player"])) is not None:
                del self.units[i]
                self.refs.pop(i, None)
                self.moving.pop(i, None)
                self.working.pop(i, None)
                out.append(f"kill {v.uuid}")
        return out

    def fall(self, rect):
        """The commands that clear the building with the block footprint rect = (x0, x1, z0, z1), from the lowest
        ground at its edge (the ground in a start footprint is the barrier top) to its top."""
        x0, x1, z0, z1 = rect
        cells = {(x, z) for x in range(x0, x1) for z in range(z0, z1)}
        m = self.map
        m.blocked -= cells
        for r in m.drops:
            m.drops[r] = [d for d in m.drops[r] if d != cells]
        ys = [y for x, z in cells | m.around(cells) if (y := m.y(x, z)) is not None]
        if not ys:
            return []
        top = self.tops.pop(rect, None) or max(ys) + TALL
        return self.fill(max(0, x0), min(ys), max(0, z0), min(self.n, x1) - 1, top, min(self.n, z1) - 1, "air destroy")

    def spawns(self):
        """A "spawn" event for each unit that a QUEUE command trains, at the end of its training."""
        return [{"time": end, "player": e["player"], "kind": "spawn", "type": e["type"], "name": e["name"],
                 "building": b, "where": (e.get("names") or [None] * len(e["objects"]))[e["objects"].index(b)]}
                for end, e, b in aoe2mc.training(self.data.get("timeline", ())) if "type" in e and e.get("name")]

    def home(self, e):
        """The block footprint (x0, x1, z0, z1) of the building that trains the unit of a spawn event: a start
        building by its ID, else the last building of the player with the name of its ID (name_timeline) or of the
        building of the unit (aoe2mc.TRAIN), else the first building of the player."""
        start = next((r for i, _, _, r in self.starts if i == e["building"]), None)
        if start:
            return start
        own = [(n, r) for p, n, r in [s[1:] for s in self.starts] + self.placed if p == e["player"]]
        for name in (e.get("where"), (aoe2mc.train(e["name"]) or (0, None))[1]):
            rects = [r for n, r in own if n == name]
            if name and rects:
                return rects[-1]
        return own[0][1] if own else None

    def spawn(self, e):
        """The summon command of a trained unit, on a free cell in front of its building (south side first). The
        units of one building take the cells one after the other."""
        prefix, _ = self.kinds.get(e["type"], ("?", ""))
        rect = self.home(e) if prefix in ("U", "H") else None
        if rect is None:
            return []
        self.grid()
        x0, x1, z0, z1 = rect
        cells = sorted(self.map.around({(x, z) for x in range(x0, x1) for z in range(z0, z1)}),
                       key=lambda c: (abs(c[1] - z1), abs(2 * c[0] + 1 - x0 - x1), c))
        if not cells:
            return []
        k = self.trained[rect] = self.trained.get(rect, -1) + 1
        x, z = cells[k % len(cells)]
        pos = (x + 0.5, float(self.map.y(x, z)), z + 0.5)
        o = dict(name=e["name"], player=e["player"], rotation=math.pi / 2, hero=prefix == "H")   # it faces south
        nbt = units.make_entity(o, {int(p): v for p, v in self.data["players"].items()}, pos, self.rng)
        if nbt is None:
            return []
        kind = str(nbt.pop("id"))
        del nbt["Pos"]
        v = self.gather.Villager(units.uuid_str(nbt["UUID"]), pos)
        v.name, v.player = e["name"], e["player"]
        self.new.append((e["player"], v))
        out = [f"summon {kind} {pos[0]} {pos[1]} {pos[2]} {nbt.snbt()}"]
        if self.ai:                                                 # the AoE2 values: plugin commands (#632)
            import combat                                           # combat -> gather -> build -> replay
            out += [combat.stats_command(v.uuid, v.name)] + [c for c in [combat.range_command(v.uuid, v.name, self.T)] if c]
        return out

    def grid(self):
        """The gather.Map of the world with the buildings of the replay. The first call also finds the units of the
        start state (the entities of aoe2mc.json with an object ID)."""
        if self.map is None:
            import gather                                           # gather -> build -> replay: import it late
            self.gather, self.map, T = gather, gather.Map(self.data), self.T
            self.crew = gather.Gather.__new__(gather.Gather)       # adapter: the resource looks of gather.Gather
            self.crew.map, self.crew.trunks, self.crew.bushes = self.map, {}, {}
            for o in self.data["objects"]:
                if o["kind"] == "unit" and "uuid" in o and o.get("ref") is not None:
                    x, z = o["tile"][0] * T, o["tile"][1] * T
                    self.units[o["ref"]] = v = gather.Villager(o["uuid"], (x, float(self.map.y(int(x), int(z)) or 0), z))
                    v.name, v.player = o["name"], o["player"]
        for _, name, r in self.placed[self.added:]:
            if "FARM" not in name:
                self.map.building(name, r, None, False)
        self.added = len(self.placed)
        return self.map

    def unit(self, i, name, player):
        """The unit with object ID i. A new ID takes the oldest spawned unit of the player with its name (the game
        gives the IDs in the order of the trainings, aoe2mc.name_timeline)."""
        if i not in self.units and name:
            k = next((k for k, (p, v) in enumerate(self.new) if p == player and v.name == name), None)
            if k is not None:
                self.units[i] = self.new.pop(k)[1]
        return self.units.get(i)

    def goals(self, e):
        """The cells that the units of a MOVE or ORDER go to: next to the target object of an ORDER, else the
        target tile (or next to it, when it is blocked)."""
        m, T, t = self.map, self.T, e.get("target")
        if e["kind"] == "order" and t is not None and (t in self.units or t in self.refs):
            o = self.refs.get(t, {})
            if t in self.units:
                cells = {self.units[t].cell}
            elif "footprint" in o:
                x0, z0, x1, z1 = o["footprint"]
                cells = {(x, z) for x in range(x0, x1) for z in range(z0, z1)}
            else:
                cells = m.cells((int(o["tile"][0]), int(o["tile"][1])))
            return m.around(cells)
        if "tile" not in e:
            return set()
        c = int(e["tile"][0] * T), int(e["tile"][1] * T)
        return {c} if m.free(*c) else m.around(m.cells((c[0] // T, c[1] // T)))

    def enemy(self, e):
        """The entity UUID of the target of an ORDER when it is a unit or a start building (with a target of
        combat.building) of another player than e["player"], else None."""
        import combat
        t, p = e.get("target"), e["player"]
        if e["kind"] != "order" or t is None:
            return None
        if t in self.units:
            return self.units[t].uuid if self.units[t].player not in (0, p) else None
        o = self.refs.get(t, {})
        if o.get("kind") == "building" and "footprint" in o and o["name"] in combat.BUILDINGS and o["player"] not in (0, p):
            return combat.target_uuid(o["footprint"])
        return None

    def attack(self, group, target):
        """The military units of group attack entity target, with their AoE2 walk speed; they walk no more legs.
        Returns the commands and the rest of the group."""
        import ai
        out, rest = [], []
        for i, v in group:
            if self.gather.military(v.name):
                out += [ai.speed_command(v.uuid, v.name, self.T, self.speed), f"aoe attack {v.uuid} {target}"]
                self.moving.pop(i, None)
            else:
                rest.append((i, v))
        return out, rest

    def move(self, e):
        """MOVE and ORDER: each selected unit gets a path to the target. Its steps come later (steps()). A group
        that goes to a tile stops in a formation there (formation()), a unit with no path to its cell goes to the
        target tile."""
        self.grid()
        goals = self.goals(e)
        group = [(i, v) for i, name in zip(e["objects"], e.get("names") or [None] * len(e["objects"]))
                 if (v := self.unit(i, name, e["player"])) is not None]
        tile = self.resource(e)
        for i, v in group:                                          # a new MOVE or ORDER stops the work
            self.working.pop(i, None)
            v.tree = tile
        if not goals or not group:
            return []
        to_tile = not (e["kind"] == "order" and e.get("target") is not None)
        slots = self.formation([v for _, v in group], e["tile"]) if to_tile else {}
        if self.ai:
            out, group = self.attack(group, target) if (target := self.enemy(e)) else ([], group)
            for i, v in group:
                end = slots.get(v) or min(goals, key=lambda c: (math.dist(c, v.cell), c))
                path = self.map.path(v.cell, {end}, PATH_CELLS) or []
                cmds, due = self.order(v, path[LEG - 1:-1:LEG] + [end], e["time"])
                out += cmds
                if v.path:
                    self.moving[i] = due
                else:
                    self.moving.pop(i, None)
                    self.start(i, v, due)
            return out
        for i, v in group:
            v.path = (self.map.path(v.cell, {slots[v]}, PATH_CELLS) if v in slots else None) or \
                self.map.path(v.cell, goals, PATH_CELLS) or []
            due = self.moving[i] if i in self.moving and v.path else self.next_step(v, e["time"])
            if due is None:
                self.moving.pop(i, None)
                self.start(i, v, e["time"])
            else:
                self.moving[i] = due
        return []

    def order(self, v, legs, t):
        """The plugin walks unit v on a Minecraft path to the first cell of `legs`, at its walk speed times the replay
        speed (#438). The path search of Minecraft reaches only about 128 blocks, so a long way goes in legs of
        LEG cells of the path of gather.Map: the next leg starts when the unit is due at the end of this one.
        The replay does not read the positions back: it takes the unit at the end of its leg. Returns the commands
        and the game time (ms) at the end of the leg (the next leg starts then, if v.path has one)."""
        import ai                                                   # ai -> replay: import it late
        x, z = legs[0]
        x0, _, z0 = v.pos
        v.pos, v.path = (x + 0.5, float(self.map.y(x, z)), z + 0.5), legs[1:]
        speed = next((s for k, s in SPEEDS.items() if v.name.startswith(k)), 1.0) * self.T    # blocks per second
        due = t + 1000 * math.hypot(v.pos[0] - x0, v.pos[2] - z0) / speed
        return [ai.speed_command(v.uuid, v.name, self.T, self.speed), "aoe moveto {} {} {} {}".format(v.uuid, *v.pos)], due

    def formation(self, group, tile):
        """The end cell of each unit of a group that walks to a tile (#410): rows across the walk direction, the
        first row on the target and the others behind it, FORMATION blocks apart (AoE2 line formation). A slot
        snaps to the next free cell, one unit per cell. The units nearest to the target take the first row, and
        in a row they keep their order from left to right, so that the paths do not cross."""
        m, n, S = self.map, len(group), FORMATION
        tx, tz = tile[0] * self.T, tile[1] * self.T
        cx, cz = (sum(v.pos[k] for v in group) / n for k in (0, 2))
        d = math.hypot(tx - cx, tz - cz)
        dx, dz = ((tx - cx) / d, (tz - cz) / d) if d > 0.5 else (0.0, -1.0)    # walk direction (else north)
        cols = min(n, max(1, round(math.sqrt(2 * n))))
        rows = -(-n // cols)
        r = max(2 * self.T, math.ceil(max(cols, rows) * S))
        x0, z0 = int(tx), int(tz)
        todo = {(x, z) for x in range(x0 - r, x0 + r + 1) for z in range(z0 - r, z0 + r + 1) if m.free(x, z)}
        group = sorted(group, key=lambda v: (tx - v.pos[0]) * dx + (tz - v.pos[2]) * dz)
        out = {}
        for q in range(rows):
            row = sorted(group[q * cols:q * cols + cols], key=lambda v: v.pos[0] * -dz + v.pos[2] * dx)
            for j, v in enumerate(row):
                off = (j - (len(row) - 1) / 2) * S
                px, pz = tx - dx * q * S - dz * off, tz - dz * q * S + dx * off
                if todo:
                    out[v] = c = min(todo, key=lambda c: ((c[0] - px) ** 2 + (c[1] - pz) ** 2, c))
                    todo.discard(c)
        return out

    def next_step(self, v, t):
        """The game time (ms) at which unit v reaches the next cell of its path when it leaves at t, or None."""
        if not v.path:
            return None
        speed = next((s for k, s in SPEEDS.items() if v.name.startswith(k)), 1.0) * self.T    # blocks per second
        x, z = v.path[0]
        return t + 1000 * math.hypot(x + 0.5 - v.pos[0], z + 0.5 - v.pos[2]) / speed

    def steps(self, t):
        """The commands of the steps (/tp), legs (plugin orders) and gather steps that are due at game time t (ms)."""
        out = []
        sink = types.SimpleNamespace(map=self.map, command=out.append)
        for i, due in list(self.moving.items()):
            v, at = self.units[i], due
            if self.ai and due <= t:
                legs = [c for c in v.path if self.map.free(*c)]        # a new building on a leg end: skip it
                cmds, at = self.order(v, legs, due) if legs else ([], due)
                due = at if v.path and legs else None
                out += cmds
            while not self.ai and due is not None and due <= t:
                if not self.map.free(*v.path[0]):                       # a new building on the way: a new path
                    goal = v.path[-1]
                    v.path = (self.map.path(v.cell, {goal}, PATH_CELLS) or []) if self.map.free(*goal) else []
                    if not v.path:
                        due = None
                        break
                self.gather.walk(sink, v)
                at, due = due, self.next_step(v, due)
            if due is None:
                del self.moving[i]
                self.start(i, v, at)
            else:
                self.moving[i] = due
        self.crew.command = out.append
        for i, due in list(self.working.items()):
            v = self.units[i]
            src = self.crew.source(v)
            while due <= t and src.get(v.tree, 0) > 0:
                src[v.tree] -= 1
                v.load += 1
                self.crew.work(v)
                if v.res == "food":
                    self.crew.berries(v.tree)
                elif v.res != "wood":
                    if src[v.tree] == 0:
                        self.crew.dig(v.tree, v.res)
                elif src[v.tree] == 0:
                    self.crew.fell(v.tree)
                else:
                    self.crew.trunk(v.tree)
                due += 1000 / self.gather.AOE2_WORK[v.res]
            if src.get(v.tree, 0) > 0:
                self.working[i] = due
            else:
                del self.working[i]
                out += self.next_resource(i, v, due - 1000 / self.gather.AOE2_WORK[v.res])
        return out

    def next_resource(self, i, v, t):
        """Unit i gathered the last of its resource at game time t: as in AoE2 it walks to the nearest resource of
        the same kind within NEXT tiles that has something left, and gathers there. Else it stays (the record has no
        drop-off). Returns the commands (Paper: the first leg)."""
        T, (x, z) = self.T, v.cell
        far = {k: math.dist((x / T, z / T), (k[0] + 0.5, k[1] + 0.5)) for k, n in self.crew.source(v).items() if n > 0}
        near = sorted((d, k) for k, d in far.items() if d <= NEXT)
        if not near:
            return []
        v.tree = near[0][1]
        path = self.map.path(v.cell, self.map.around(self.map.spot(v.tree)), PATH_CELLS)
        if path is None:
            return []
        if self.ai and path:
            cmds, due = self.order(v, path[LEG - 1:-1:LEG] + [path[-1]], t)
            if v.path:
                self.moving[i] = due
            else:
                self.start(i, v, due)
            return cmds
        v.path = path
        due = self.next_step(v, t)
        if due is None:
            self.start(i, v, t)
        else:
            self.moving[i] = due
        return []

    def resource(self, e):
        """The tile of the tree, fruit bush or mine that an ORDER targets, else None."""
        o = self.refs.get(e.get("target")) if e["kind"] == "order" else None
        if not o or o["kind"] != "other" or "tile" not in o:
            return None
        tile = int(o["tile"][0]), int(o["tile"][1])
        m = self.map
        return tile if tile in m.trees or tile in m.bushes or any(tile in s for s in m.mines.values()) else None

    def start(self, i, v, t):
        """A unit with a resource that ends its walk next to it gathers from game time t on, at the AoE2 work rate
        of the resource (gather.AOE2_WORK, per game second). The record has no drop-off: it does not carry."""
        if v.tree is None or v.cell not in self.map.around(self.map.spot(v.tree)):
            return
        v.res, v.load = self.map.resource(v.tree), 0
        if self.crew.source(v).get(v.tree, 0) > 0:
            self.working[i] = t + 1000 / self.gather.AOE2_WORK[v.res]

    def state(self, i):
        return aoe2mc.B.states[i]

    @staticmethod
    def fill(x0, y0, z0, x1, y1, z1, what):
        """/fill commands for a box, cut into layers of at most MAX_FILL blocks."""
        step = max(1, MAX_FILL // ((x1 - x0 + 1) * (z1 - z0 + 1)))
        return [f"fill {x0} {y} {z0} {x1} {min(y + step - 1, y1)} {z1} {what}" for y in range(y0, y1 + 1, step)]

    @staticmethod
    def clock_commands(now, end, speed, done=False):
        """The boss bar commands for game time `now` (ms) of a replay that ends at `end` (ms): the time and speed as
        its name, the game seconds as its value (#684). `players @a` also adds the players who joined later."""
        m, s = divmod(int(now) // 1000, 60)
        name = f"End {m:02d}:{s:02d}" if done else f"{m:02d}:{s:02d} · speed {speed:g}×"
        return [f"bossbar set {BAR} name {json.dumps(text(name), ensure_ascii=False)}",
                f"bossbar set {BAR} value {min(int(now) // 1000, max(1, int(end) // 1000))}", f"bossbar set {BAR} players @a"]

    def send(self, cmds):
        t = time.perf_counter()
        for c in cmds:
            self.game.command(c)
        self.sent += len(cmds)
        self.busy += time.perf_counter() - t

    def retime(self, g0, r0, r):
        """Apply a change of `self.control` at real time r: returns the new anchor (game time g0 at real time r0).
        The game time stays where it is, so no event plays twice; a pause stops it (#685). Walking units of the
        plugin get the new walk speed (0 in a pause)."""
        speed, paused = self.control["speed"], self.control["paused"]
        if (speed, paused) == (self.speed, self.paused):
            return g0, r0
        g = g0 if self.paused else g0 + (r - r0) * 1000 * self.speed
        self.speed, self.paused = speed, paused
        if self.ai:
            import ai                                               # ai -> replay: import it late
            self.send([ai.speed_command(v.uuid, v.name, self.T, 0 if paused else speed)
                       for v in map(self.units.get, self.moving) if v and v.uuid])
        return g, r

    def jump(self, events, to):
        """Apply the events up to game time `to` (ms) at once (#687): buildings appear, deletes remove, trained units
        appear, and each unit that a MOVE or ORDER sent, or that walks now, stands at its target (tp, no walk). The
        chat, age and research texts of the skipped time do not show. Returns the commands."""
        out, moved = [], set()
        for e in events:
            if e["kind"] in ("move", "order") and e.get("objects"):
                self.move(e)                                        # the paths and the targets; no walk orders
                moved.update(e["objects"])
            elif e["kind"] in ("build", "wall", "spawn", "delete"):
                out += self.commands(e)
        for i in sorted(moved | self.moving.keys()):
            if (v := self.units.get(i)) is None:
                continue
            x, z = v.path[-1] if v.path else v.cell
            v.pos, v.path = (x + 0.5, float(self.map.y(x, z)), z + 0.5), []
            self.moving.pop(i, None)
            out.append("tp {} {} {} {}".format(v.uuid, *v.pos))
            if self.ai:                                             # ends the walk order of the plugin at once
                out.append("aoe moveto {} {} {} {}".format(v.uuid, *v.pos))
        return out

    def run(self, speed=1.0, start=0, clock=time.monotonic, sleep=time.sleep, log=print, bar=False, poll=None):
        """Play the timeline from game time `start` (ms) at `speed` times the game speed; `bar`: show the game time
        in a boss bar (`clock_commands`). Returns the stats:
        commands, events, the seconds of sending, the largest lag behind the timeline (s), commands per second
        (rate) and the commands per second that the timeline needs on average (need).
        poll(control) may change `self.control` ("speed", "paused") while the replay runs: run calls it before
        each event and each POLL seconds while it waits (#685). "jump" (game time, ms) skips forward to that time
        (`jump`, #687); a time before the game time now changes nothing."""
        events = sorted((e for e in self.data.get("timeline", []) + self.spawns() if e["time"] >= start),
                        key=lambda e: e["time"])
        g0, r0, lag, n, k = start, clock(), 0.0, 0, 0                 # game time g0 (ms) at real time r0
        self.speed, self.paused = speed, False
        self.control = {"speed": speed, "paused": False}
        end, shown = events[-1]["time"] if events else start, None
        send = self.send if bar else lambda cmds: None
        send([f'bossbar add {BAR} ""', f"bossbar set {BAR} color white",
                   f"bossbar set {BAR} max {max(1, int(end) // 1000)}"])
        while k < len(events) or self.moving:
            step = min([*self.moving.values(), *self.working.values()], default=math.inf)   # walk or gather step
            e = events[k] if k < len(events) and events[k]["time"] <= step else None
            k += e is not None
            now = e["time"] if e else step
            to = None
            while True:
                if poll:
                    poll(self.control)
                    g0, r0 = self.retime(g0, r0, clock())
                    if (to := self.control.pop("jump", None)) is not None:
                        break
                wait = POLL if self.paused else (now - g0) / 1000 / self.speed - (clock() - r0)
                if wait <= 1e-6:                                    # rounding: no endless wait
                    break
                sleep(min(wait, POLL) if poll else wait)
                if not poll:
                    break
            if to is not None:
                k -= e is not None                                  # the event waits for the jump
                if to > (g0 if self.paused else g0 + (clock() - r0) * 1000 * self.speed):
                    skip = [x for x in events[k:] if x["time"] <= to]
                    k += len(skip)
                    self.send(self.jump(skip, to))
                    g0, r0 = to, clock()
                continue
            lag = max(lag, clock() - r0 - (now - g0) / 1000 / self.speed)
            if int(now) // 1000 != shown:                              # at most once per game second
                shown = int(now) // 1000
                send(self.clock_commands(now, end, self.speed))
            if e is None:
                self.send(self.steps(now))
                continue
            cmds = self.commands(e)
            if cmds:
                n += 1
                self.send(cmds)
                if log and e["kind"] in ("build", "wall", "age", "resign"):
                    m, s = divmod(e["time"] // 1000, 60)
                    log(f"{m:02d}:{s:02d} {e['kind']} {e.get('name') or e.get('age') or ''} "
                        f"player {e.get('player')}: {len(cmds)} commands")
        send(self.clock_commands(end, end, speed, done=True))
        span = (events[-1]["time"] - start) / 1000 / speed if events else 0                 # at the start speed
        return {"events": n, "commands": self.sent, "busy": round(self.busy, 2), "lag": round(lag, 2),
                "rate": round(self.sent / self.busy) if self.busy else 0, "need": round(self.sent / span) if span else 0}
