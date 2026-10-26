"""
Replay a recorded game live (#374): play the "timeline" of aoe2mc.json (aoe2mc.read_timeline, #372) on a running
server. Each building appears at its command time (the blocks of its design, as with --at, #373), chat lines are
/tellraw in the player color, age-ups are a title, research is an action bar line, and RESIGN is a title.

Replay(game, data).run(speed) plays it; commands(e) gives the commands of one event (the unit tests use it).
"""
import json
import os
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import aoe2mc  # noqa: E402
import buildings  # noqa: E402

# Dye color of a player (aoe2mc.PLAYER_COLORS) -> text color of /tellraw and /title
TEXT_COLORS = {"light_gray": "gray", "blue": "blue", "red": "red", "green": "green", "yellow": "yellow",
               "cyan": "aqua", "purple": "light_purple", "gray": "dark_gray", "orange": "gold"}
FLAT = 16                   # tiles of the flat map that draws one design
MAX_FILL = 32768            # blocks of one /fill command


def pretty(name):
    return name.replace("_", " ").title()


def text(s, color=None):
    return {"text": s, "color": color} if color else {"text": s}


class Replay:
    """The timeline of aoe2mc.json `data` on a server (game.command sends one command)."""

    def __init__(self, game, data, version=aoe2mc.VERSION_NAME):
        self.game, self.data = game, data
        self.T, self.n = data["tile_size"], len(data["ground"])
        self.ground = [[None if v == "-" else int(v) for v in row.split()] for row in data["ground"]]
        self.renames = aoe2mc.VERSIONS[version]["renames"]
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
                out += self.building(name, e["player"], x, y)
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

    def state(self, i):
        name, _, props = aoe2mc.B.states[i].partition("[")
        return self.renames.get(name, name) + (f"[{props}" if props else "")

    @staticmethod
    def fill(x0, y0, z0, x1, y1, z1, what):
        """/fill commands for a box, cut into layers of at most MAX_FILL blocks."""
        step = max(1, MAX_FILL // ((x1 - x0 + 1) * (z1 - z0 + 1)))
        return [f"fill {x0} {y} {z0} {x1} {min(y + step - 1, y1)} {z1} {what}" for y in range(y0, y1 + 1, step)]

    def send(self, cmds):
        t = time.perf_counter()
        for c in cmds:
            self.game.command(c)
        self.sent += len(cmds)
        self.busy += time.perf_counter() - t

    def run(self, speed=1.0, start=0, clock=time.monotonic, sleep=time.sleep, log=print):
        """Play the timeline from game time `start` (ms) at `speed` times the game speed. Returns the stats:
        commands, events, the seconds of sending, the largest lag behind the timeline (s), commands per second
        (rate) and the commands per second that the timeline needs on average (need)."""
        events = [e for e in self.data.get("timeline", ()) if e["time"] >= start]
        t0, lag, n = clock(), 0.0, 0
        for e in events:
            due = (e["time"] - start) / 1000 / speed
            wait = due - (clock() - t0)
            if wait > 0:
                sleep(wait)
            lag = max(lag, clock() - t0 - due)
            cmds = self.commands(e)
            if cmds:
                n += 1
                self.send(cmds)
                if log and e["kind"] in ("build", "wall", "age", "resign"):
                    m, s = divmod(e["time"] // 1000, 60)
                    log(f"{m:02d}:{s:02d} {e['kind']} {e.get('name') or e.get('age') or ''} "
                        f"player {e.get('player')}: {len(cmds)} commands")
        span = (events[-1]["time"] - start) / 1000 / speed if events else 0
        return {"events": n, "commands": self.sent, "busy": round(self.busy, 2), "lag": round(lag, 2),
                "rate": round(self.sent / self.busy) if self.busy else 0, "need": round(self.sent / span) if span else 0}
