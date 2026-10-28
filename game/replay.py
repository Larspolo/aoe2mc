"""
Replay a recorded game live (#374): play the "timeline" of aoe2mc.json (aoe2mc.read_timeline, #372) on a running
server. Each building appears at its command time (the blocks of its design, as with --at, #373), chat lines are
/tellraw in the player color, age-ups are a title, research is an action bar line and, for 10 game seconds, its name
above the building with particles (#843), and RESIGN is a title.
A trained unit appears in front of its building when its training ends (#408, aoe2mc.training). The units that a
MOVE or ORDER command selects walk to its target: on Paper the plugin walks them on a Minecraft path at their walk speed
(`aoe moveto`, game/ai.py, #438), else one /tp per block on the path of gather.Map (#409, gather.walk);
a group that goes to a tile stops there in rows (#410).
Fights (#632): on Paper an ORDER on a unit or a start building of another player sends the military units of the
selection to attack it (`aoe attack`, the mob AI and the AoE2 values of game/combat.py); a unit at 0 hit points dies by
itself. A trained unit gets its AoE2 values at its spawn (`aoe stats`, `aoe range`); game/run.py gives them to the
units and buildings of the start state (combat.setup).
A villager gets the look of its AoE2 task (#868, gather.Gather.task): an ORDER on a resource, a BUILD (builder);
a MOVE, an ORDER on something else, or the end of its work without a next resource gives it the idle look (units.IDLE_JOB).
Garrisons (#809): a GARRISON command, or an ORDER on an own start building with garrison room (game/garrison.py SIZES),
puts the units inside it when they arrive (the state of the converter, #807), and UNGARRISON lets them out next to it.
A villager with resources and an ORDER on a drop site drops them and does not go in.
Gather points (#1227): a trained unit walks to the last GATHER POINT of its building, and a villager there gathers, as
after an ORDER. The record names the unit only in its first command, so until then it has a temporary negative ID
(rally()); unit() gives its state to the real ID.

Replay(game, data).run(speed) plays it; commands(e) gives the commands of one event (the unit tests use it).
With bar=True (game/run.py --replay) a boss bar shows the game time, the speed and the progress (#684).
"""
import collections
import functools
import json
import math
import os
import re
import sys
import textwrap
import time
import types

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import aoe2mc  # noqa: E402
import buildings  # noqa: E402
import table  # noqa: E402
import replay_input  # noqa: E402
import units  # noqa: E402

# Dye color of a player (aoe2mc.PLAYER_COLORS) -> text color of /tellraw and /title
TEXT_COLORS = {"light_gray": "gray", "blue": "blue", "red": "red", "green": "green", "yellow": "yellow",
               "cyan": "aqua", "purple": "light_purple", "gray": "dark_gray", "orange": "gold"}
# The firework color of each dye (DyeColor.getFireworkColor), for the age-up fireworks (#844).
FIREWORK_COLORS = {"black": 0x1E1B1B, "blue": 0x253192, "brown": 0x51301A, "cyan": 0x287697, "gray": 0x434343,
                   "green": 0x3B511A, "light_blue": 0x6689D3, "light_gray": 0xABABAB, "lime": 0x41CD34,
                   "magenta": 0xC354CD, "orange": 0xEB8844, "pink": 0xD88198, "purple": 0x7B2FBE, "red": 0xB3312C,
                   "white": 0xF0F0F0, "yellow": 0xDECF2A}
FLAT = 16                   # tiles of the flat map that draws one design
MAX_FILL = 32768            # blocks of one /fill command
FORMATION = 2              # blocks between the units of a group in a formation (#410)
LEG = 48                    # path cells of one plugin order: within the reach of a Minecraft path search (#438)
CATCH_UP = 1.5              # the largest factor of the walk speed of a unit behind its replay position (#1168)
CLOSE = 5000                # ms of game time in which a unit behind its replay position closes the lag (#1291)
PATH = 1.15                 # the walk speed factor of each plugin leg: a Minecraft path is longer than the leg (#1168)
POCKET = 64                 # cells: less free land around a builder is a pocket of its walls and the water (#1275)
RECENT = 10000              # ms: a unit whose last leg ended this short a time ago can still walk it (catch_up)
TALL = 48                   # blocks above the ground that a DELETE clears for a start building (no height in aoe2mc.json)
BAR = "aoe2mc:replay"       # the boss bar with the game time (#684)
POP = "aoe_pop"             # the sidebar objective with the population of each player (#741)
BURST = 500                 # ms of game time between two bursts of a flare column: a burst lives about 1 s (#2506)
TEAM_STEP = 10000           # sidebar score of a team game: team key × TEAM_STEP + population, the panel sorts by it (#1189)
COUNTED = "aoe2mc.pop"      # entity tag of the units that the population counts (#787)
EFFECT = "aoe2mc.effect"    # entity tag of the texts above a building (#843)
FOLLOWED = "aoe2mc.followed"  # the tag of the entity that the spectators of --follow look through (#1095)
TRAIL = 3                   # tiles: a follower farther than this from its target walks to it again (#2551)
TRAIL_MS = 1000             # ms of game time between two checks of the followers (#2551)
FIGHT_MS = 60000            # ms of game time: an attack order this near in time to one of a fight joins it (#2948)
FIGHT_TILES = 12            # tiles: an attack order this near to one of a fight joins it (#2948)
FIGHT_UNITS = 10            # attacking units of a large fight (#2948)
CAMERA_MS = 10000           # ms of game time: a shot of the camera plan is held at least this long (#3366)
CAMERA_TILES = 10           # tiles: the new buildings of a build shot lie this near to each other (#3366)
CAMERA_BUILDS = 5           # new buildings in CAMERA_MS near each other that make a build shot (#3366)
FAR = 8                     # tiles: a target unit this far from the tile of the ORDER (its place in AoE2) is no attack
                            # target: in de-64.3 a spearman chased a villager 200 blocks from it across the map (#2635)
FOLLOW_MS = 15000           # ms of game time: the camera of --follow changes its unit at most this often (#738)
EFFECT_MS = 10000           # ms of game time that the research text stays
SCALE = 4                   # size of the research text: a spectator sees it from 40 blocks
START = {"food": 200, "wood": 200, "gold": 100, "stone": 200}   # the AoE2 standard start resources (#932)
FRAME = 27                  # tiles of a side of the view square on map 0 (#1762): AoE2 DE at 1920 × 1080 shows about
                            # 1920 × 850 pixels of land (no HUD), a tile is 96 × 48 pixels (2304 px²): 708 tiles = 27²
VIEWER = "aoe_viewer"        # player tag: the player got the overview of the map (#737)
VIEW_PITCH = 60             # degrees down of the overview
VIEW_FALL = 60              # seconds of slow falling after the overview
VIEW_DIST = 150             # blocks from the overview to the map center: in the vanilla render distance 12 (192, #1094)
CLOUDS = 192                # the vanilla cloud height: the overview stays below it, else it shows only clouds (#1094)
RCON_MAX = 1446             # bytes of one RCON command: the server closes the connection after a longer one
BOOK_COLS, BOOK_ROWS = 19, 14   # characters per line and lines of a book page (aoe2mc.book_pages)
POLL = 0.2                  # seconds between two calls of the poll of Replay.run while it waits (#685)
CENSUS = 1.0                # seconds of real time between two censuses: each count is one RCON round trip (2 to 5 ms
                            # at a 45 ms server tick); once per game second at speed 4 took 23 % of the loop (#2761)
NEXT = 5                    # tiles: an empty resource sends its villager to the next one this near (#720)
NEAR = 2                    # blocks: a unit of the plugin this near to its replay position is at its resource (#766)
SEEN = 32                   # blocks: the server sends a particle only to the players this near (a sound of volume 1
                            # carries 16): a gather step farther from each player sends no look (#2761, the loop lag)
WAIT = 1000                 # ms of game time between two position checks of a unit that is late on its path (#766)
LATE = 60000                # ms of game time: a unit that is still not at its resource then goes there with /tp
STILL = 4000                # ms of game time: a walking unit that stands this long on one place gets free (unstick)
HOME = 4                    # blocks: a unit farther than this from the end of its walk walks to it again (settle, #2633)
HOME_MS = 20000             # ms of game time after the end of a walk: then settle() uses /tp (replay_drift: stuck at 30 s)
PATH_CELLS = 20000          # cells that one path search may look at: a unit with no path stays (no time lag)
# The walk speed of common units, tiles per game second (AoE2 DE), the ages and the Society buildings: one line per
# name in data/replay.jsonl (#2034). A walk speed name is the start of the unit names.
ROWS = table.load("replay.jsonl")
SPEEDS = {r["name"]: r["walk"] for r in ROWS if "walk" in r}
AGES = tuple(r["name"] for r in sorted((r for r in ROWS if "age" in r), key=lambda r: r["age"]))   # (#1067)
SOCIETY = tuple(r["name"] for r in ROWS if r.get("society"))      # the buildings of the Society tab (#1086)
TAUNTS = {r["name"]: r["text"] for r in table.load("taunts.jsonl")}   # number: the AoE2 text (wiki "Taunt", #2234)
TAUNT_SOUNDS = {r["name"]: r["sound"] for r in table.load("taunts.jsonl") if "sound" in r}   # a good vanilla match only (#2233, #2662)


def pretty(name):
    return name.replace("_", " ").title()


def start_job(name):
    """The profession that units.make_entity gives a unit of this name (gather.Villager.job)."""
    return next((j for k, j in units.VILLAGER_JOBS if k in name), units.IDLE_JOB)


def text(s, color=None):
    return {"text": s, "color": color} if color else {"text": s}


def taunt(chat):
    """The chat line with the AoE2 text of its taunt: "11" and "11 haha" (a number, then other text) are taunt 11,
    "11 (Herb laugh)" (#2234). Other lines stay as they are."""
    n = chat.strip().split(" ", 1)[0]
    if n not in TAUNTS:
        return chat
    return f"{chat} ({TAUNTS[n].removeprefix('(').removesuffix(')')})"


def taunt_sound(chat):
    """The playsound command of the taunt of this chat line, or none: the other taunts are text only (#2233, #2662)."""
    n = chat.strip().split(" ", 1)[0]
    return [f"playsound minecraft:{TAUNT_SOUNDS[n]} master @a ~ ~ ~ 1 1 1"] if n in TAUNT_SOUNDS else []


def mmss(ms):
    """Game time in ms -> "MM:SS"."""
    m, s = divmod(int(ms) // 1000, 60)
    return f"{m:02d}:{s:02d}"


@functools.lru_cache(maxsize=None)
def ship(name):
    """True for a unit that the converter makes a boat (a fishing ship, a galley ...): it stays on the water (#866)."""
    return units.is_boat(units.classify(name or ""))


def fisher(name):
    """True for a fishing ship: it gathers at a fish (#1283)."""
    return name.startswith("FISHING_SHIP")


Seen = collections.namedtuple("Seen", "player name pos")            # a place of a unit for seen() (#1801)
CIRCLES = {}                                                        # (x, y, sight) -> the tiles of seen()


def seen(mobs, placed, player, T, sight=None):
    """The tiles (x, y) in the line of sight of the units and buildings of player (#1300): a circle of combat.sight()
    tiles around each one, from the tile center. mobs: units with name, player and pos (blocks, Replay.units), placed:
    (player, name, (x0, x1, z0, z1) in blocks) as Replay.placed. sight: name -> tiles with the technologies of the
    player (the game program, #1475), default combat.sight."""
    import combat                                                   # combat -> gather -> build -> replay
    objs = [(v.pos[0] / T, v.pos[2] / T, v.name) for v in mobs if v.player == player and v.pos is not None]
    objs += [((x0 + x1) / 2 / T, (z0 + z1) / 2 / T, name) for p, name, (x0, x1, z0, z1) in placed if p == player]
    out = set()
    if len(CIRCLES) > 20000:                                        # the places of units that stand: no growth
        CIRCLES.clear()
    for x, y, name in objs:
        r = (sight or combat.sight)(name)
        if (key := (x, y, r)) not in CIRCLES:                       # most units stand still between two calls (#1801)
            xs, ys = np.meshgrid(np.arange(math.floor(x - r), math.ceil(x + r)), np.arange(math.floor(y - r), math.ceil(y + r)))
            keep = (xs + 0.5 - x) ** 2 + (ys + 0.5 - y) ** 2 <= r * r
            CIRCLES[key] = list(zip(xs[keep].tolist(), ys[keep].tolist()))
        out.update(CIRCLES[key])
    return out


def runs(cmd, tiles):
    """Commands `cmd Y,X0,X1 ...` for the tiles (x, y): the runs of tiles X0 to X1 in row Y, each command below
    RCON_MAX (#1567)."""
    out, line = [], cmd
    for y, x in sorted((y, x) for x, y in tiles):
        if line.endswith(f",{x - 1}") and line.rsplit(" ", 1)[1].startswith(f"{y},"):
            line = line[:line.rfind(",")] + f",{x}"           # the run goes on
            continue
        if len(line) + 20 > RCON_MAX:
            out, line = out + [line], cmd
        line += f" {y},{x},{x}"
    return out + [line] * (line != cmd)


def owners(objects, events):
    """{object ID: player} of a record (#2948): the start objects (`ref`, no animals: a herd changes its owner) and
    each ID that a player selects in a command (a player selects only own units and buildings)."""
    out = {o["ref"]: o["player"] for o in objects
           if o.get("ref") is not None and o.get("player") and not units.animal(o["name"])}
    for e in events:
        if e["kind"] in aoe2mc.UNIT_USE | aoe2mc.BUILDING_USE and e.get("player"):
            out.update(dict.fromkeys(e.get("objects", ()), e["player"]))
    return out


def fights(events, owner):
    """The large fights of a record (#2948): the record has no deaths (#1086), so a fight is a group of attack orders
    (an ORDER on a unit or building of another player, not of Gaia, and an ATTACK_MOVE), each less than FIGHT_MS and FIGHT_TILES from
    another one of the group, of two or more players and FIGHT_UNITS or more attacking units. owner: owners().
    Returns [{"start", "end" (ms), "tile" [x, y], "players", "units"}], the largest first."""
    groups = []
    for e in events:
        p, t = e.get("player"), e.get("target")
        if "tile" not in e or not p or not (e["kind"] == "attack_move" or
                                            e["kind"] == "order" and owner.get(t) not in (None, 0, p)):
            continue
        near = [g for g in groups if e["time"] - g[-1]["time"] <= FIGHT_MS
                and any(math.dist(e["tile"], f["tile"]) <= FIGHT_TILES for f in g)]
        for g in near[1:]:                                          # the order joins two groups
            near[0] += g
            groups.remove(g)
        if near:
            near[0].append(e)
        else:
            groups.append([e])
    out = []
    for g in groups:
        players, ids = sorted({e["player"] for e in g}), {i for e in g for i in e.get("objects", ())}
        if len(players) > 1 and len(ids) >= FIGHT_UNITS:
            out.append({"start": min(e["time"] for e in g), "end": max(e["time"] for e in g), "players": players,
                        "tile": [round(sum(e["tile"][k] for e in g) / len(g), 1) for k in (0, 1)], "units": len(ids)})
    return sorted(out, key=lambda f: (-f["units"], f["start"]))


def camera_plan(events, owner):
    """Where the automatic camera looks during a record (#3366): a fight shot at the start of each large fight
    (fights()), and a build shot where CAMERA_BUILDS or more new buildings lie within CAMERA_TILES of each other
    in CAMERA_MS. A fight wins: a build shot less than CAMERA_MS from a fight shot is left out, and two shots
    are at least CAMERA_MS apart. The camera holds a shot until the next one. owner: owners().
    Returns [{"time" (ms), "tile" [x, y], "why": "fight" or "build"}], sorted by time."""
    plan = [{"time": f["start"], "tile": f["tile"], "why": "fight"} for f in fights(events, owner)]
    builds = sorted((e for e in events if e["kind"] == "build" and "tile" in e), key=lambda e: e["time"])
    for e in builds:
        near = [b for b in builds if 0 <= b["time"] - e["time"] < CAMERA_MS and math.dist(b["tile"], e["tile"]) <= CAMERA_TILES]
        if len(near) < CAMERA_BUILDS or any(abs(s["time"] - e["time"]) < CAMERA_MS for s in plan):
            continue
        tile = [round(sum(b["tile"][k] for b in near) / len(near), 1) for k in (0, 1)]
        plan.append({"time": e["time"], "tile": tile, "why": "build"})
    return sorted(plan, key=lambda s: s["time"])


def sail(g, v):
    """Move ship v one cell on its water path with /tp, facing the step. The y of the boat stays (`at @s`, `~`):
    the water carries it, and aoe2mc.json has no height for the water."""
    x, z = v.path.pop(0)
    dx, dz = x + 0.5 - v.pos[0], z + 0.5 - v.pos[2]
    v.pos = (x + 0.5, v.pos[1], z + 0.5)
    g.command(f"execute as {v.uuid} at @s run tp @s {v.pos[0]} ~ {v.pos[2]} {math.degrees(math.atan2(-dx, dz)):.0f} 0")


def live(make, speed=1.0, start=0, restart=None, **kw):
    """Play a replay that can jump back (#979). make() gives a fresh Replay. A jump back to time T calls restart()
    (it puts the world back to its start state), then a fresh replay from `start` jumps forward to T: the same state
    as a new replay with a jump to T. Speed and pause stay. Without restart a jump back changes nothing. Returns the
    stats of the last run."""
    to, paused, stats = start or None, False, {}              # the first run jumps to start: its state (#3025)
    while True:
        r = make()
        r.pov = stats.get("view", r.pov)                            # the view stays too (#1303)
        stats = r.run(speed, 0, to=to, paused=paused, rewind=restart is not None, **kw)   # events before start: the jump
        if stats.get("rewind") is None:
            return stats
        to, speed, paused = max(start, stats["rewind"]), stats["speed"], stats["paused"]
        restart()


class Replay:
    """The timeline of aoe2mc.json `data` on a server (game.command sends one command)."""

    def __init__(self, game, data, version=aoe2mc.VERSION_NAME, ai=False, follow=None, pov=None):
        self.game, self.data, self.ai, self.speed, self.paused = game, data, ai, 1.0, False  # ai: plugin walks
        self.follow, self.followed = follow, (None, -math.inf)  # the spectators follow player N: (UUID, game time)
        self.pov, self.hidden = pov, set()      # the view of player N (#1302): UUIDs of the enemy units hidden from @a
        self.explored, self.fogged = {}, None   # player -> tiles it saw once; (view, seen, explored) on the minimap (#1567)
        self.drawn, self.known = {}, {}         # footprint -> player on the minimap; view -> the enemy ones it saw (#1678)
        self.heights = {}                       # (building, player) -> height(), see height (#3048)
        self.T, self.n = data["tile_size"], len(data["ground"])
        self.ground = [[None if v == "-" else int(v) for v in row.split()] for row in data["ground"]]
        self.starts = [(o.get("ref"), o["player"], o["name"], (o["footprint"][0], o["footprint"][2], o["footprint"][1],
                        o["footprint"][3])) for o in data["objects"] if o["kind"] == "building" and "footprint" in o]
        self.placed, self.map, self.added = [], None, 0        # buildings of the replay, gather.Map, placed in the map
        self.open = {}                                          # footprint -> cells that units walk through (#865)
        self.lifted = None                                      # cells where "ground" is the top of an object (#870)
        self.tops = {}                                          # top block y per footprint of a replay building
        self.trained = {}                                       # units per building footprint
        self.units, self.new = {}, []           # object ID -> gather.Villager; spawned units without a known ID
        self.moving = {}                        # object ID -> game time (ms) of its next step
        self.idle = {}                          # object ID -> (game time (ms) of its next check, end of its walk) (#2633)
        self.working = {}                       # object ID -> game time (ms) of its next gather step (#631)
        self.arriving = {}                      # object ID -> game time (ms) of its work start, until it is there (#766)
        self.entering = {}                      # object ID -> [footprint, building entry, arrival (ms) or None] (#809)
        self.builds = {}                        # object ID of a builder -> (game time (ms) of the build end, order then) (#1282)
        self.garrisons = {}                     # building footprint -> object IDs of the units inside it
        self.work = {}                          # object ID -> the resource tile that it left for a garrison (#1179)
        self.ids = {}                           # new object ID of a building -> footprint of its replay building (#876)
        self.hunted = {}                        # object ID of a hunted animal -> the tile of its carcass (#1229)
        self.prey = {}                          # carcass tile -> UUID of its animal that is still alive (#1281)
        self.points = {}                        # object ID of a building -> its last GATHER POINT event (#1227)
        self.stances, self.charging = {}, {}    # object ID -> stance of the record; its stance after an attack-move (#2552)
        self.patrols = {}                       # object ID -> [patrol tiles, index of the tile it walks to, step] (#2550)
        self.follows = {}                       # object ID -> [target ID, "follow" or "guard", goal, enemy UUID] (#2551)
        self.scouts = {}                        # object ID on AUTOSCOUT -> the tiles that it walked to (#2678)
        self.trail = math.inf                   # game time (ms) of the next check of the followers (#2551)
        self.adopted, self.rallied = {}, 0      # temporary ID of a unit at a gather point -> its object ID (#1227)
        self.effects = {}                       # entity tag of a research text -> game time (ms) of its end (#843)
        self.flares = []                        # (x, y, z, game time (ms) of the end, RGB) of the live flares (#2402)
        self.formations = {}                    # object ID -> the AoE2 formation of the record: Line, Box ... (#2553)
        self.burst = math.inf                   # game time (ms) of the next burst of the live flares (#2506)
        self.refs = {o["ref"]: o for o in data["objects"] if o.get("ref") is not None}
        self.rng = np.random.default_rng(1)
        self.kinds, self.seen = aoe2mc.object_kinds(), set()
        self.sent, self.busy = 0, 0.0           # commands sent, seconds spent sending them
        self.pop, self.shown = {}, None         # player -> live units (no animals), the value in the sidebar (#741)
        self.ages, self.named = {}, {}          # player -> age ("Feudal"); the age in its sidebar name (#805)
        self.counted = []                       # UUIDs of the start units that the population counts
        self.stock = {}                         # player -> estimated resources: START + gather steps - costs (#932)
        self.gathered, self.villagers = {}, {}  # player -> resources of the gather steps, trained villagers (#1065)
        self.army, self.lost, self.razed = {}, {}, {}   # player -> military units trained, units lost, buildings lost (#1066)
        self.censused = False                   # a census counted the live units (the base of the units lost)
        self.reached, self.researched = {}, {}  # player -> {age: game time (ms)}, researched technologies (#1067)
        self.vills, self.vhigh = {}, {}         # player -> live villagers (est.), the highest count (#1086)
        self.eyes = None                        # (x, y, z) of each player; None: not known, each gather step shows (#2761)
        self.queue = None                       # in run() on Paper: the commands that wait for flush() (#2761)
        for o in data["objects"]:
            if o["kind"] == "unit" and o.get("player") and not units.animal(o["name"]):
                self.pop[o["player"]] = self.pop.get(o["player"], 0) + 1
                self.counted += [o["uuid"]] * ("uuid" in o)
            if o["kind"] == "unit" and o.get("player") and o["name"].startswith("VILLAGER"):
                self.villager(o["player"], 1)

    def player(self, p):
        info = self.data["players"].get(str(p), {})
        return f"Player {p}" + (f" ({pretty(info['civ'])})" if info.get("civ") else ""), \
            TEXT_COLORS.get(info.get("color"), "white")

    def team(self, p):
        """The team number of player p, or None when no team has two players (a game of one player per team, #1189)."""
        teams = [info.get("team") for q, info in self.data["players"].items() if q != "0"]
        return self.data["players"].get(str(p), {}).get("team") if any(
            t is not None and teams.count(t) > 1 for t in teams) else None

    def label(self, p):
        """The name (with "Team N" in a team game) and the text color of player p for the panel and the summary."""
        name, color = self.player(p)
        return (f"Team {t} · {name}" if (t := self.team(p)) else name), color

    def ranked(self, players):
        """The players in panel order: the players of one team together, team 1 first (#1189)."""
        return sorted(players, key=lambda p: (self.team(p) or 0, p))

    def age(self, e):
        self.ages[e.get("player")] = pretty(e["age"]).removesuffix(" Age")
        self.reached.setdefault(e.get("player"), {})[e["age"]] = e.get("time", 0)
        self.pay(e.get("player"), e["age"])

    def learn(self, e):
        """Count a research of the timeline for the summary (#1067)."""
        self.researched[e.get("player")] = self.researched.get(e.get("player"), 0) + 1

    def villager(self, p, n, live=None):
        """n more live villagers of player p, or the `live` count of the census: keep the highest count (#1086)."""
        self.vills[p] = live if live is not None else self.vills.get(p, 0) + n
        self.vhigh[p] = max(self.vhigh.get(p, 0), self.vills[p])

    def resources(self, p):
        return self.stock.setdefault(p, dict(START))

    def pay(self, p, name):
        """The record has no resources: subtract the AoE2 cost of a unit, building or age (train and build COSTS)."""
        import build                                                # gather -> build -> replay: import it late
        import train
        for r, v in (train.COSTS.get(name) or build.COSTS.get(name) or {}).items():
            self.resources(p)[r] -= v

    def commands(self, e):
        """The commands of one timeline event (an empty list for the events that change nothing visible)."""
        kind = e["kind"]
        if kind in ("attack_move", "move", "order", "stop", "delete", "garrison", "follow", "guard", "autoscout"):
            for i in e.get("objects") or ():                    # another order ends the patrol (#2550), the scouting (#2678)
                self.patrols.pop(i, None)
                self.scouts.pop(i, None)
        if kind in aoe2mc.UNIT_USE - {"stance"} | {"delete", "stop"}:   # a new order ends a FOLLOW or GUARD (#2551)
            for i in e.get("objects") or ():
                self.follows.pop(i, None)
                self.idle.pop(i, None)                                # a new order: settle() does not check it
                self.scouts.pop(i, None)
        if kind == "patrol" and e.get("objects") and e.get("tile"):
            return self.patrol(e)
        if kind == "autoscout" and e.get("objects"):
            return self.autoscout(e)
        if kind in ("follow", "guard") and e.get("objects") and e.get("target") is not None:
            return self.escort(e)
        if kind in ("build", "wall") and "type" in e and "tile" in e:
            return self.build(e)
        if kind == "spawn":
            return self.spawn(e)
        if kind == "summon" and e.get("objects") and e.get("tile"):
            return self.summon(e)
        if kind == "gather_point" and e.get("objects"):
            self.points.update(dict.fromkeys(e["objects"], e))
            return []
        if kind in ("move", "order") and e.get("objects"):
            return self.calm(e["objects"]) + self.move(e)
        if kind == "attack_move" and e.get("objects") and e.get("tile"):
            return self.attack_move(e)
        if kind == "garrison" and e.get("objects"):
            return self.move(dict(e, kind="order", garrison=True))
        if kind == "ungarrison" and e.get("objects"):
            return [c for r in self.holders(e) for c in self.release(r)]
        if kind == "back_to_work" and e.get("objects"):
            return self.back(e)[0]
        if kind == "delete" and e.get("objects"):
            return self.delete(e)
        if kind == "stance" and e.get("objects"):
            return self.stance(e)
        if kind == "stop" and e.get("objects"):
            return self.stop(e)
        if kind == "formation" and e.get("objects"):                # the shape of the next walks of the group (#2553)
            self.formations.update(dict.fromkeys(e["objects"], e.get("formation", "Line")))
            return []
        if kind == "chat" and e.get("text"):
            name, color = self.player(e["player"]) if e.get("player") else ("Game", "white")
            return (["tellraw @a " + json.dumps([text(f"<{name}> ", color), text(taunt(e["text"]))])]
                    + taunt_sound(e["text"]))
        name, color = self.player(e.get("player"))
        if kind == "flare" and e.get("tile"):                     # a view player sees only its flares (#2403)
            seen = self.pov is None or self.pov == e.get("player") or self.pov in e.get("to", [self.pov])
            return self.flare(e, name, color) if seen else []
        if kind == "age" and e.get("age"):
            self.age(e)
            return ["title @a subtitle " + json.dumps(text(name, color)),
                    "title @a title " + json.dumps(text(pretty(e["age"])))] + self.fireworks(e.get("player"))
        if kind == "research" and e.get("technology"):
            self.learn(e)
            return ["title @a actionbar " + json.dumps([text(name, color), text(f" researches {e['technology']}")])] + \
                self.research(e, color)
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
                if not e.get("free"):                               # a setup of the game program (#3028)
                    self.pay(e["player"], name)
                k = len(self.placed)
                out += self.building(name, e["player"], x, y)
                if len(self.placed) > k:
                    out += self.push_out(self.placed[-1][2])               # it finds the units (grid())
                    for i, n in zip(e.get("objects", ()), e.get("names") or [None] * len(e.get("objects", ()))):
                        out += self.side(i, self.unit(i, n, e["player"]), self.placed[-1][2])
                        out += self.look(self.unit(i, n, e["player"]), "BUILDER")
                    then = None
                    if "FARM" in name and e.get("objects"):       # AoE2: the builders of a farm farm it (#719)
                        x0, x1, z0, z1 = self.placed[-1][2]
                        then = dict(e, kind="order", target=-1, tile=[(x0 + x1) / 2 / self.T, (z0 + z1) / 2 / self.T])
                    elif (kinds := [r for r, s in self.gather.DROP_SITES.items() if name in s and name != "TOWN_CENTER"]) \
                            and e.get("objects") and (k := self.near(kinds, self.placed[-1][2])) is not None:
                        then = dict(e, kind="order", target=-1, tile=[k[0] + 0.5, k[1] + 0.5], resource=k)
                    if e["kind"] == "build":
                        out += self.construct(e, name, self.placed[-1][2], then)
        return out

    def construct(self, e, name, rect, then):
        """The builders of a BUILD stop their work, walk next to the foundation rect and build for the AoE2 build time
        with n builders, t × 3 / (n + 2) (t: build.BUILD_TIMES, one builder; 0 for a building that it does not
        list). Then the ORDER `then` starts (built()), else they stand idle: before, the builders of a house gathered
        while they built (#1282). Returns the commands."""
        import build                                                # gather -> build -> replay: import it late
        group = [(i, v) for i, n in zip(e.get("objects", ()), e.get("names") or [None] * len(e.get("objects", ())))
                 if (v := self.unit(i, n, e["player"])) is not None and v.name.startswith("VILLAGER")]
        x0, x1, z0, z1 = rect
        goals = self.map.around({(x, z) for x in range(x0, x1) for z in range(z0, z1)})
        work = 1000 * build.BUILD_TIMES.get(name, 0) * 3 / (len(group) + 2)
        out = []
        for i, v in group:
            for state in (self.working, self.arriving, self.entering):
                state.pop(i, None)
            if self.ai:
                v.pos = self.at(v, e["time"])                       # it stops its leg where it is
            v.path = self.map.path(v.cell, goals, PATH_CELLS) or []
            due = self.walk_end(v, e["time"]) + work
            out += self.go(i, v, None, v.path, e["time"])
            self.builds[i] = due, then and dict(then, time=due, objects=[i], names=[None])
        return out

    def built(self, t):
        """The builders whose build ends until game time t (ms), in time order: (object ID, ORDER or None) (#1282)."""
        done = sorted((due, i, then) for i, (due, then) in self.builds.items() if due <= t)
        for _, i, _ in done:
            del self.builds[i]
        return [(i, then) for _, i, then in done]

    def near(self, kinds, rect):
        """The tile of the nearest tree, bush or mine of the resources `kinds` within NEXT tiles of the building rect,
        or None: AoE2 sends the builders of a lumber camp, mill or mining camp to gather there (#1229)."""
        m, T = self.map, self.T
        c = (rect[0] + rect[1]) / 2 / T, (rect[2] + rect[3]) / 2 / T
        src = {"wood": m.trees, "food": m.bushes, **m.mines}
        far = sorted((math.dist(c, (k[0] + 0.5, k[1] + 0.5)), k) for r in kinds for k, n in src.get(r, {}).items() if n > 0)
        return far[0][1] if far and far[0][0] <= NEXT else None

    def research(self, e, color):
        """The name of the technology 2 blocks above the roof of its building, and particles at the roof (#843).
        The text goes after EFFECT_MS (`expire`). No known building: no commands."""
        i, name = (e.get("objects") or [None])[0], (e.get("names") or [None])[0]
        start = next((s for s in self.starts if s[0] == i), None)
        rect = start[3] if start else name and self.new_building(i, name, e.get("player"))
        if not rect:
            return []
        x0, x1, z0, z1 = rect
        if start:                                                   # no height in aoe2mc.json: that of its design
            m = self.grid()
            ys = [y for x, z in m.around({(x, z) for x in range(x0, x1) for z in range(z0, z1)})
                  if (y := m.y(x, z)) is not None]
            if not ys:
                return []
            top = max(ys) + self.height(start[2], start[1])
        else:
            top = self.tops.get(rect)
        if top is None:
            return []
        tag = f"{EFFECT}.{len(self.effects)}.{e['time']}"
        self.effects[tag] = e["time"] + EFFECT_MS
        x, z = (x0 + x1) / 2, (z0 + z1) / 2
        return [f"summon text_display {x} {top + 3} {z} {{text:{json.dumps(text(e['technology'], color))},"
                f'billboard:"center",shadow:1b,transformation:{{left_rotation:[0f,0f,0f,1f],right_rotation:[0f,0f,0f,1f],'
                f'translation:[0f,0f,0f],scale:[{SCALE}f,{SCALE}f,{SCALE}f]}},Tags:["{EFFECT}","{tag}"]}}',
                f"particle minecraft:enchant {x} {top + 1} {z} {(x1 - x0) / 4} 0.5 {(z1 - z0) / 4} 1 60"]

    def expire(self, t):
        """The commands that remove the research texts whose time ended at game time t (ms), and the particles of the
        live flares (a particle burst lives less than a second, as flare.tick in the game program)."""
        done = [tag for tag, end in self.effects.items() if end <= t]
        for tag in done:
            del self.effects[tag]
        import flare                                                # game/: on the path of the replay
        self.flares = [f for f in self.flares if f[3] > t]
        self.burst = t + BURST                                      # a step of run() while a flare lives (#2506)
        return [f"kill @e[type=text_display,tag={tag}]" for tag in done] + \
            [flare.particles(x, y, z, "@a", rgb) for x, y, z, _, rgb in self.flares]

    def flare(self, e, name, color):
        """A flare of the record (#2402): the bell, the light column of the game program (flare.py) in the player color
        at the block of its tile for flare.SECONDS of game time, and a chat line in the player color. On Paper
        also a mark on the live minimap (#2405)."""
        import flare
        x, z = (min(self.n - 1, max(0, int(c * self.T))) for c in e["tile"])
        y = self.ground[z][x] if self.ground[z][x] is not None else next(
            (g for row in self.ground for g in row if g is not None), 64)    # water: the height of the land
        rgb = FIREWORK_COLORS.get(self.data["players"].get(str(e.get("player")), {}).get("color"), FIREWORK_COLORS["white"])
        self.flares.append((x, y, z, e["time"] + flare.SECONDS * 1000, rgb))    # the column in the player color (#2442)
        self.burst = min(self.burst, e["time"] + BURST) if len(self.flares) > 1 else e["time"] + BURST
        ticks = max(1, round(flare.SECONDS * 20 / self.speed))          # the game time of the flare at the replay speed
        return [f"playsound {flare.SOUND} master @a {x} {y} {z} 1 1 1", flare.particles(x, y, z, "@a", rgb),
                "tellraw @a " + json.dumps([text(f"<{name}> ", color), text("Flare", "gold")])] + \
            [f"aoe minimap flare {x} {z} p{e.get('player')} {ticks}"] * self.ai   # a blinking cross on the minimap (#2405)

    def height(self, name, player):
        """Blocks of the design of building `name` above the ground of its footprint (its top block).
        Cached on this Replay only: a lru_cache would keep each old Replay alive after a jump back (#3048)."""
        if (name, player) not in self.heights:
            x = y = FLAT // 2
            cols, E, o = self.draw(name, player, x, y)
            ys = [by for xs, bys, zs, ids, _ in E.parts for by, i in zip(bys.tolist(), ids.tolist()) if i]
            self.heights[name, player] = max(ys) - cols.surface(*o["footprint"][:2]) if ys and "footprint" in o else TALL
        return self.heights[name, player]

    def draw(self, name, player, x, y, along_z=False):
        """(Columns, Edits, object) of one building at tile (x, y) of a flat map whose corner is tile
        (x - FLAT // 2, y - FLAT // 2), rounded down. along_z: a gate along z (no walls next to it tell it, #1324)."""
        T, info = self.T, self.data["players"].get(str(player), {})
        ox, oy = int(x) - FLAT // 2, int(y) - FLAT // 2            # whole tiles: the same rounding as in place_building
        cols = aoe2mc.Columns(FLAT, np.zeros((FLAT, FLAT), np.int16), np.zeros((FLAT, FLAT), np.float32),
                              {0: "GRASS_1"}, T, self.data["level_height"], np.random.default_rng(1))
        E = aoe2mc.Edits(cols)
        players = {player: {"arch": info.get("arch", "western"), "color": info.get("color", "light_gray")}}
        o = dict(kind="B", name=name, player=player, x=x - ox, y=y - oy, rotation=0.0, hero=False, garrisoned=False)
        walls, gates = buildings.plan_walls([o])
        gates[id(o)] = gates.get(id(o)) or along_z
        turn, buildings.TURN = buildings.TURN, self.data.get("turn", 0)     # the map turn of --orientation (#3035)
        try:
            buildings.place_building(E, cols, aoe2mc.B, o, players, walls, gates)
        finally:
            buildings.TURN = turn                                  # the tests share the process
        return cols, E, o

    def push_out(self, rect):
        """The units in the footprint of a new building step out to the nearest free cell, as in AoE2 (a unit in a
        block suffocates; the replay does not know all walks)."""
        x0, x1, z0, z1 = rect
        cells = {(x, z) for x in range(x0, x1) for z in range(z0, z1)}
        self.grid()
        free = self.map.around(cells)
        cells -= self.open.get(rect, set())                         # units under a town center stay (#865)
        out = []
        for i, v in list(self.units.items()) + [(None, v) for _, v in self.new]:
            if v.cell in cells and free and "FARM" not in self.placed[-1][1]:
                v.path = [min(free, key=lambda c: (math.dist(c, v.cell), c))]
                self.gather.walk(types.SimpleNamespace(map=self.map, command=out.append), v)
                self.moving.pop(i, None)                                # it stops there
        return out

    def pocket(self, cell):
        """The free land cells that a unit at cell reaches when they are fewer than POCKET (walls, buildings and water
        close it in), else None. 4 neighbours: gather.Map.path cuts no corner, so a diagonal gap is closed."""
        m, seen, todo = self.map, {cell}, [cell]
        while todo and len(seen) < POCKET:
            x, z = todo.pop()
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (x + dx, z + dz)
                if n not in seen and m.free(*n) and abs(m.y(*n) - (m.y(x, z) or m.y(*n))) <= 1:
                    seen.add(n)
                    todo.append(n)
        return seen if len(seen) < POCKET else None

    def side(self, i, v, rect=None):
        """A unit in a pocket steps to the nearest free cell out of it, as in AoE2: a builder that the new building
        rect closes in goes next to rect on the open side (it walks around the foundation), a unit in an older pocket
        (an order with no path on land, rect None) over the nearest wall. Else its next walk swims (#1275)."""
        if v is None or v.cell is None or not (inside := self.pocket(v.cell)):
            return []
        if rect:
            x0, x1, z0, z1 = rect
            near = self.map.around({(x, z) for x in range(x0, x1) for z in range(z0, z1)})
        else:
            x, z, r = *v.cell, self.T * 2
            near = {(x + dx, z + dz) for dx in range(-r, r + 1) for dz in range(-r, r + 1) if self.map.free(x + dx, z + dz)}
        c = next((c for c in sorted(near - inside, key=lambda c: (math.dist(c, v.cell), c)) if not self.pocket(c)), None)
        if c is None:
            return []
        out = []
        v.path = [c]
        self.gather.walk(types.SimpleNamespace(map=self.map, command=out.append), v)
        self.moving.pop(i, None)
        return out

    def building(self, name, player, x, y, along_z=False, water=None):
        """The commands that draw one building at tile (x, y): its design on a flat map (like render.py), moved to
        the ground of the world. The footprint is cleared first; a foundation fills the air under the floor.
        water: the ground y of a building on the open water (a fish trap, #1438), else the land next to it counts."""
        T, arch = self.T, self.data["players"].get(str(player), {}).get("arch", "western")
        ox, oy = int(x) - FLAT // 2, int(y) - FLAT // 2
        cols, E, o = self.draw(name, player, x, y, along_z)
        if not E.parts or "footprint" not in o:
            return []
        fx0, fz0, fx1, fz1 = o["footprint"]
        dx, dz = ox * T, oy * T
        m = self.grid()
        if self.lifted is None:                                     # the cells of the trees, bushes and mines
            self.lifted = set().union(*map(m.spot, [*m.trees, *m.bushes, *(t for r in m.mines.values() for t in r)]))
        foot = {(x, z) for x in range(max(0, fx0 + dx), min(self.n, fx1 + dx))
                for z in range(max(0, fz0 + dz), min(self.n, fz1 + dz))}
        # "ground" over a tree is the top of its barriers and trunk (#870): take the other cells, else the free cells
        # next to the footprint
        free = foot - self.lifted or m.around(foot) or foot
        cells = [g for x, z in free if (g := self.ground[z][x]) is not None] or \
            [g for x, z in m.around(foot) if (g := self.ground[z][x]) is not None] or \
            [water] * (water is not None)                           # a dock on water: the shore (#1382)
        if not cells:                                               # outside the map or on water only
            return []
        trees = [t for t in m.trees if m.cells(t) & foot]          # in AoE2 the tree is gone (chopped)
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
        self.open[self.placed[-1][2]] = {(x + dx, z + dz) for x, z in o.get("open", ())}
        out = [f"aoe minimap building {x0} {z0} {x1 + 1} {z1 + 1} p{player}"] * (self.ai and self.pov is None)   # on the
        if self.ai and self.pov is None:                            # map item (#1238); with a view player: fog() (#1678)
            self.drawn[self.placed[-1][2]] = player
        for t in trees:                                             # as gather.Gather.clear: logs, leaves and bamboo
            m.trees.pop(t)
            tx, tz = t[0] * T, t[1] * T
            out += [f"fill {tx - 2} {low - 2} {tz - 2} {tx + T + 1} {low + 22} {tz + T + 1} air replace {b}"
                    for b in ("#minecraft:logs", "#minecraft:leaves", "minecraft:bamboo")]
        out += self.fill(x0, base, z0, x1, top, z1, "air")
        if low < base - 1:                                          # the floor replaces the top ground block
            out += self.fill(x0, low, z0, x1, base - 2, z1, self.state(aoe2mc.B(buildings.ARCH[arch].stone2)) + " keep")
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
                out += self.release(rect)                           # AoE2: the units come out alive
                self.razed[e["player"]] = self.razed.get(e["player"], 0) + 1
                if start:
                    self.starts.remove(start)
                    import combat
                    if self.ai and start[2] in combat.BUILDINGS:    # its target takes no more attacks or arrows (#3037)
                        out += [f"kill {combat.target_uuid([rect[0], rect[2], rect[1], rect[3]])}"]
                else:
                    del self.placed[new]
                    self.added -= 1
                out += [f"aoe minimap unbuild {rect[0]} {rect[2]}"] * (self.pov is None and self.drawn.pop(rect, 0) != 0)
                out += self.fall(rect)
            elif (v := self.unit(i, name, e["player"])) is not None:
                del self.units[i]
                self.refs.pop(i, None)
                self.moving.pop(i, None)
                self.working.pop(i, None)
                self.arriving.pop(i, None)
                self.entering.pop(i, None)
                self.builds.pop(i, None)
                for us in self.garrisons.values():
                    us[:] = [u for u in us if u != i]
                self.pop[e["player"]] = max(0, self.pop.get(e["player"], 0) - 1)
                self.lost[v.player] = self.lost.get(v.player, 0) + (not e.get("free"))   # a scout swap (#3028)
                out.append(f"kill {v.uuid}")
        return out

    def fall(self, rect):
        """The commands that clear the building with the block footprint rect = (x0, x1, z0, z1), from the lowest
        ground at its edge (the ground in a start footprint is the barrier top) to its top."""
        x0, x1, z0, z1 = rect
        cells = {(x, z) for x in range(x0, x1) for z in range(z0, z1)}
        m = self.map
        m.blocked -= cells
        for t in [t for t in m.farms if m.feet.get(t) == rect]:    # a deleted farm: no food, its farmer stops
            del m.farms[t]
            m.farm_at = {c: f for c, f in m.farm_at.items() if f != t}
        for r in m.drops:
            m.drops[r] = [d for d in m.drops[r] if d != cells]
        ys = [y for x, z in cells | m.around(cells) if (y := m.y(x, z)) is not None]
        if not ys:
            return []
        top = self.tops.pop(rect, None) or max(ys) + TALL
        return self.fill(max(0, x0), min(ys), max(0, z0), min(self.n, x1) - 1, top, min(self.n, z1) - 1, "air destroy")

    def spectate(self, e):
        """--follow N (#738): the spectators follow the first unit of a MOVE, ORDER or spawn of player N, the unit with
        the tag FOLLOWED. On Paper the plugin moves each spectator over the shoulder of that unit each tick (Follow.java,
        #1660); a vanilla server has no plugin, so there the spectators look through its eyes (/spectate; it takes one
        player, so `execute as` each spectator). The camera changes at most once per
        FOLLOW_MS of game time, at once when its unit is gone (DELETE). A unit with a rider (a horse, a siege crew):
        the spectators look through the rider, else its legs fill the screen (#1095). `execute on passengers` finds
        it: the replay does not know the UUID of the rider."""
        if self.follow is None or e.get("player") != self.follow or e["kind"] not in ("move", "order", "spawn"):
            return []
        uuid, at = self.followed
        alive = {v.uuid for v in self.units.values()} | {v.uuid for _, v in self.new}
        if uuid in alive and e["time"] - at < FOLLOW_MS:
            return []
        if e["kind"] == "spawn":
            v = self.new[-1][1] if self.new and self.new[-1][0] == self.follow else None
        else:
            v = next((self.units[i] for i in e["objects"] if i in self.units), None)
        if v is None or v.uuid == uuid:
            return []
        self.followed = (v.uuid, e["time"])
        return [f"tag @e[tag={FOLLOWED}] remove {FOLLOWED}", f"tag {v.uuid} add {FOLLOWED}",
                f"execute as {v.uuid} on passengers run tag {v.uuid} remove {FOLLOWED}",
                f"execute as {v.uuid} on passengers run tag @s add {FOLLOWED}"] + \
            [f"execute as @a[gamemode=spectator] run spectate @e[tag={FOLLOWED},limit=1] @s"] * \
            (getattr(self.game, "kind", "paper") == "vanilla")

    @functools.cached_property
    def trainings(self):
        """aoe2mc.training of the timeline: (end ms, QUEUE event, building ID) for each unit."""
        self.unknown_research
        return aoe2mc.training(self.data.get("timeline", ()), research=True)

    def production(self, t):
        """{player: [(name, count, start, end), ...]}: the units in training or in the queue of their building at game
        time t (ms, #2809), grouped by name in the order of the next end; start and end are those of the first one.
        A technology in research or in the queue is (name, start, end, kind), kind "age" for an age-up (#2810)."""
        out, tech = {}, {}
        for end, e, _ in self.trainings:
            if e["kind"] == "research" and e["time"] <= t < end:
                n = e["technology"]
                tech.setdefault(e["player"], []).append(
                    (n, end - aoe2mc.RESEARCH_S[n] * 1000, end, "age" if n.endswith(" Age") else "research"))
            elif e["time"] <= t < end and e.get("name"):
                out.setdefault(e["player"], {}).setdefault(e["name"], []).append(end)
        return {p: sorted([(n, len(ends), min(ends) - aoe2mc.train_ms(n), min(ends))
                           for n, ends in out.get(p, {}).items()] + tech.get(p, []), key=lambda item: item[2] if isinstance(item[3], str) else item[3])
                for p in sorted(set(out) | set(tech))}

    @functools.cached_property
    def unknown_research(self):
        """The technologies of the timeline with no RESEARCH_S value: no production item, one log line (#2810)."""
        names = sorted({e.get("technology", "") for e in self.data.get("timeline", ())
                        if e["kind"] == "research" and e.get("technology", "") not in aoe2mc.RESEARCH_S})
        if names:
            print(f"research with no time (not in the production): {', '.join(names)}", file=sys.stderr)
        return names

    def spawns(self):
        """A "spawn" event for each unit that a QUEUE command trains, at the end of its training."""
        return [{"time": end, "player": e["player"], "kind": "spawn", "type": e["type"], "name": e["name"],
                 "building": b, "where": (e.get("names") or [None] * len(e["objects"]))[e["objects"].index(b)]}
                for end, e, b in aoe2mc.training(self.data.get("timeline", ())) if "type" in e and e.get("name")]

    def fireworks(self, player):
        """Three firework rockets in the player color above the first town center of the player, and one sound for
        all (#844): a spectator sees which player advanced. No town center: no fireworks (the title stays)."""
        rect = next((r for p, n, r in [s[1:] for s in self.starts] + self.placed
                     if p == player and n == "TOWN_CENTER"), None)
        if rect is None:
            return []
        x0, x1, z0, z1 = rect
        ys = [g for z in range(max(0, z0), min(self.n, z1)) for x in range(max(0, x0), min(self.n, x1))
              if (g := self.ground[z][x]) is not None]
        if not ys:
            return []
        y = self.tops.get(rect) or max(ys)
        info = self.data["players"].get(str(player), {})
        rgb = FIREWORK_COLORS.get(info.get("color"), FIREWORK_COLORS["white"])
        out = []
        for k, (dx, dz) in enumerate(((0, 0), (-2, 1), (2, -1))):
            fw = {"explosions": [{"shape": ("large_ball", "star", "burst")[k], "colors": [rgb],
                                  "fade_colors": [FIREWORK_COLORS["white"]], "has_trail": True, "has_twinkle": True}],
                  "flight_duration": 1}
            item = {"id": "minecraft:firework_rocket", "count": 1, "components": {"minecraft:fireworks": fw}}
            nbt = json.dumps({"LifeTime": 25 + 5 * k, "FireworksItem": item}).replace('"colors": [', '"colors": [I; ') \
                .replace('"fade_colors": [', '"fade_colors": [I; ')
            out.append(f"summon minecraft:firework_rocket {(x0 + x1) / 2 + dx} {y + 2} {(z0 + z1) / 2 + dz} {nbt}")
        return out + ["playsound minecraft:ui.toast.challenge_complete master @a ~ ~ ~ 1 1 1"]

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
        self.pay(e["player"], e["name"])
        if e["name"].startswith("VILLAGER"):
            self.villagers[e["player"]] = self.villagers.get(e["player"], 0) + 1
            self.villager(e["player"], 1)
        import gather                                               # gather -> build -> replay: import it late
        if gather.military(e["name"]):
            self.army[e["player"]] = self.army.get(e["player"], 0) + 1
        rect = self.home(e) if prefix in ("U", "H") else None
        if rect is None:
            return []
        self.grid()
        boat = ship(e["name"])                                      # a dock puts its ships on the water (#866)
        cells = self.map.front(rect, "Passengers" in (units.classify(e["name"]) or {}) and not boat, boat)
        if not cells:
            return []
        k = self.trained[rect] = self.trained.get(rect, -1) + 1
        x, z = cells[k % len(cells)]
        pos = (x + 0.5, self.map.sea(x, z) if boat else float(self.map.y(x, z)), z + 0.5)
        v, out = self.newcomer(e, pos, prefix == "H")
        if v is None:
            return []
        self.new.append((e["player"], v))
        return out + self.rally(e, v)

    def newcomer(self, e, pos, hero=False):
        """(gather.Villager, the summon commands) of the unit e["name"] of player e["player"] at pos (it faces south),
        or (None, [])."""
        o = dict(name=e["name"], player=e["player"], rotation=math.pi / 2, hero=hero)
        nbt = units.make_entity(o, {int(p): v for p, v in self.data["players"].items()}, pos, self.rng)
        if nbt is None:
            return None, []
        kind = str(nbt.pop("id"))
        del nbt["Pos"]
        v = self.gather.Villager(units.uuid_str(nbt["UUID"]), pos)
        v.name, v.player, v.job = e["name"], e["player"], start_job(e["name"])
        self.pop[e["player"]] = self.pop.get(e["player"], 0) + 1
        out = [f"summon {kind} {pos[0]} {pos[1]} {pos[2]} {units.summon_snbt(nbt)}"]
        if self.ai:                                                 # the AoE2 values: plugin commands (#632)
            import combat                                           # combat -> gather -> build -> replay
            out += [combat.stats_command(v.uuid, v.name)] + [c for c in [combat.range_command(v.uuid, v.name, self.T)] if c]
            out.append(f"tag {v.uuid} add {COUNTED}")              # census() counts it
        return v, out

    def summon(self, e):
        """A unit that a setup of the game program summoned (record.summoned: the scout of a civilization, the
        villagers of Empire Wars, #3028): at the block of its tile, with the ID of the record. No cost."""
        prefix, _ = self.kinds.get(e["type"], ("?", ""))
        if prefix not in ("U", "H"):
            return []
        m = self.grid()
        x, z = (min(self.n - 1, max(0, int(c * self.T))) for c in e["tile"])
        y = m.sea(x, z) if ship(e["name"]) else m.y(x, z)
        v, out = self.newcomer(e, (x + 0.5, float(y if y is not None else m.sea(x, z)), z + 0.5), prefix == "H")
        if v is None:
            return []
        self.units[e["objects"][0]] = v
        if e["name"].startswith("VILLAGER"):
            self.villager(e["player"], 1)
        return out

    def rally(self, e, v):
        """The unit v of spawn event e walks to the gather point of its building, with a temporary negative ID, as
        after a MOVE (a point on the ground) or an ORDER (a point on a resource or an object). Returns the commands.
        A point on the ground: the free cell nearest to it that no other unit stands on or walks to (#2880), so that
        the collision of the entities does not push the units of one gather point apart."""
        p = self.points.get(e.get("building"))
        if p is None:
            return []
        self.rallied += 1
        i = -self.rallied
        self.units[i] = v
        if p.get("target") is None and p.get("tile"):
            m, T = self.grid(), self.T
            tx, tz = p["tile"][0] * T, p["tile"][1] * T
            taken = {tuple(u.path[-1]) if u.path else u.cell for u in self.units.values() if u is not v}
            free = [(x, z) for x in range(int(tx) - 2 * T, int(tx) + 2 * T + 1)
                    for z in range(int(tz) - 2 * T, int(tz) + 2 * T + 1) if m.free(x, z) and (x, z) not in taken]
            if free:                                                    # formation() keeps a cell of a group of one
                c = min(free, key=lambda c: ((c[0] - tx) ** 2 + (c[1] - tz) ** 2, c))
                p = dict(p, tile=[c[0] / T, c[1] / T])
        return self.move(dict(p, time=e["time"], kind="order" if p.get("target") is not None else "move",
                              objects=[i], names=[v.name]))

    def grid(self):
        """The gather.Map of the world with the buildings of the replay. The first call also finds the units of the
        start state (the entities of aoe2mc.json with an object ID)."""
        T = self.T                                                  # also for the buildings of later calls (#788)
        if self.map is None:
            import gather                                           # gather -> build -> replay: import it late
            self.gather, self.map = gather, gather.Map(self.data)
            self.crew = gather.Gather.__new__(gather.Gather)       # adapter: the resource looks of gather.Gather
            self.crew.map, self.crew.trunks, self.crew.bushes, self.crew.crops = self.map, {}, {}, {}
            for o in self.data["objects"]:
                if o["kind"] == "unit" and "uuid" in o and o.get("ref") is not None:
                    x, z = o["tile"][0] * T, o["tile"][1] * T
                    self.units[o["ref"]] = v = gather.Villager(o["uuid"], (x, float(self.map.y(int(x), int(z)) or 0), z))
                    v.name, v.player, v.job = o["name"], o["player"], start_job(o["name"])
        for _, name, r in self.placed[self.added:]:              # a farm: its center tile is its key (#719)
            self.map.building(name, r, ((r[0] + r[1]) // 2 // T, (r[2] + r[3]) // 2 // T) if "FARM" in name else None,
                              False, self.open.get(r, ()))
        self.added = len(self.placed)
        return self.map

    def unit(self, i, name, player):
        """The unit with object ID i. A new ID takes the oldest spawned unit of the player with its name (the game
        gives the IDs in the order of the trainings, aoe2mc.name_timeline)."""
        if i not in self.units and name:
            k = next((k for k, (p, v) in enumerate(self.new) if p == player and v.name == name), None)
            if k is not None:
                self.units[i] = v = self.new.pop(k)[1]
                for j in [j for j, u in self.units.items() if j < 0 and u is v]:   # it was at a gather point
                    del self.units[j]
                    self.adopted[j] = i
                    for state in (self.moving, self.working, self.arriving, self.entering, self.work, self.builds, self.idle):
                        if j in state:
                            state[i] = state.pop(j)
                    for us in self.garrisons.values():                     # a gather point on a building
                        us[:] = [i if u == j else u for u in us]
        return self.units.get(i)

    def goals(self, e, water=False):
        """The cells that the units of a MOVE or ORDER go to: next to the target object of an ORDER (not a unit that
        is far() from the tile), else the target tile (or next to it, when it is blocked). water: the water cells for a
        ship, next to the target object, else the water cell nearest to the target tile within 3 tiles (#866)."""
        m, T, t = self.map, self.T, e.get("target")
        if e["kind"] == "order" and t is not None and (t in self.units or t in self.refs) and not self.far(e):
            o = self.refs.get(t, {})
            if t in self.units:
                cells = {self.units[t].cell}
            elif "footprint" in o:
                x0, z0, x1, z1 = o["footprint"]
                cells = {(x, z) for x in range(x0, x1) for z in range(z0, z1)}
            else:
                cells = m.cells((int(o["tile"][0]), int(o["tile"][1])))
            if (near := m.around(cells, water)) or not water:
                return near
        if "tile" not in e:
            return set()
        c = int(e["tile"][0] * T), int(e["tile"][1] * T)
        if water:
            r = 3 * T
            wet = [(x, z) for x in range(c[0] - r, c[0] + r + 1) for z in range(c[1] - r, c[1] + r + 1) if m.wet(x, z)]
            return {min(wet, key=lambda w: (math.dist(w, c), w))} if wet else set()
        return {c} if m.free(*c) else m.around(m.cells((c[0] // T, c[1] // T)))

    def enemy(self, e):
        """The entity UUID of the target of an ORDER when it is a unit or a start building (with a target of
        combat.building) of another player than e["player"], else None."""
        import combat
        t, p = e.get("target"), e["player"]
        if e["kind"] != "order" or t is None:
            return None
        if t in self.units:
            return self.units[t].uuid if self.units[t].player not in (0, p) and not self.far(e) else None
        o = self.refs.get(t, {})
        if o.get("kind") == "building" and "footprint" in o and o["name"] in combat.BUILDINGS and o["player"] not in (0, p):
            return combat.target_uuid(o["footprint"])
        return None

    def far(self, e):
        """True when the target unit of ORDER e stands more than FAR tiles from the tile of e in the replay: the
        record has the target at the tile, so the units walk to the tile (#2635)."""
        u, tile = self.units.get(e.get("target")), e.get("tile")
        if u is None or tile is None:
            return False
        x, _, z = self.at(u, e["time"])
        return math.hypot(x / self.T - tile[0], z / self.T - tile[1]) > FAR

    def target_mark(self, e):
        """The red order marker at the target of an attack ORDER, as the game program shows it (#796, #845): a unit
        glows for a moment, a building gets a ring of dust around its footprint."""
        if (t := e["target"]) in self.units:
            return [self.gather.glow(self.units[t].uuid)]
        x0, z0, x1, z1 = self.refs[t]["footprint"]
        return self.gather.marker(self.map, {(x0, z0), (x1 - 1, z1 - 1)}, "attack", "@a")

    def attack(self, group, target, e=None):
        """The military units of group attack entity target, with their AoE2 walk speed; they walk no more legs.
        With the ORDER e that has a tile, their replay place goes to the tile on a leg at their walk speed: the mob
        fights there, not at the place of the order (#2635). Returns the commands and the rest of the group."""
        import ai
        out, rest = [], []
        for i, v in group:
            if self.gather.military(v.name):
                out += [ai.speed_command(v.uuid, v.name, self.T, self.speed), f"aoe attack {v.uuid} {target}"]
                self.moving.pop(i, None)
                if e and e.get("tile"):
                    x, z = int(e["tile"][0] * self.T), int(e["tile"][1] * self.T)
                    start = self.at(v, e["time"])
                    y = self.map.y(x, z)                                # water has no ground: the unit keeps its height (#3000)
                    v.pos, v.path = (x + 0.5, float(v.pos[1] if y is None else y), z + 0.5), []
                    speed = next((s for k, s in SPEEDS.items() if v.name.startswith(k)), 1.0) * self.T
                    v.leg = (start, e["time"], e["time"] + 1000 * math.dist(start[::2], v.pos[::2]) / speed)
            else:
                rest.append((i, v))
        return out, rest

    def escort(self, e):
        """FOLLOW and GUARD (#2551): each unit of the selection walks after the target unit, and a guarding military
        unit attacks an enemy next to the target (chase()). A target that is no unit of the replay changes nothing."""
        if e["target"] not in self.units:
            return []
        self.grid()
        for i, name in zip(e["objects"], e.get("names") or [None] * len(e["objects"])):
            if i != e["target"] and self.unit(i, name, e["player"]) is not None:
                self.follows[i] = [e["target"], e["kind"], None, None]
        return self.chase(e["time"])

    def chase(self, t):
        """The commands of the followers at game time t (#2551): a unit farther than TRAIL tiles from its target walks
        to the place of the target (the path finding of the plugin, move()) when it does not walk there already; a
        guard on Paper attacks the nearest enemy within TRAIL tiles of its target (attack()). A dead follower or target
        ends the follow."""
        out, reach, self.trail = [], TRAIL * self.T, t + TRAIL_MS
        for i, f in sorted(self.follows.items()):
            v, w = self.units.get(i), self.units.get(f[0])
            if v is None or w is None:
                del self.follows[i]
                continue
            to = self.at(w, t)
            if f[1] == "guard" and self.ai and self.gather.military(v.name):
                foes = [(math.dist((p[0], p[2]), (to[0], to[2])), u.uuid) for u in self.units.values()
                        if u.player not in (0, v.player) and math.dist(((p := self.at(u, t))[0], p[2]), (to[0], to[2])) <= reach]
                if foes:
                    enemy = min(foes)[1]
                    if f[3] != enemy:
                        f[3] = enemy
                        out += self.attack([(i, v)], enemy)[0]
                    continue
                f[3] = None
            at = self.at(v, t)
            if math.dist((at[0], at[2]), (to[0], to[2])) > reach and (
                    f[2] is None or i not in self.moving and f[2] != to or math.dist(f[2], to) > reach):
                f[2] = to
                out += self.move(dict(time=t, player=v.player, kind="move", objects=[i], tile=[to[0] / self.T, to[2] / self.T]))
        return out

    def stance(self, e):
        """STANCE: the military units of the selection get the AoE2 stance of the record on Paper (#2548): the stance
        goals of the plugin (combat.stance_command, #1104). An unknown stance changes nothing."""
        import combat                                                   # combat -> gather -> build -> replay
        stance = str(e.get("stance", "")).lower().replace(" ", "_")
        if not self.ai or stance not in combat.STANCES:
            return []
        self.grid()
        group = [(i, self.unit(i, name, e["player"])) for i, name in zip(e["objects"], e.get("names") or [None] * len(e["objects"]))]
        group = [(i, v) for i, v in group if v is not None and self.gather.military(v.name)]
        for i, _ in group:
            self.stances[i] = stance
            self.charging.pop(i, None)                                  # the new stance stays after an attack-move
        return [combat.stance_command(v.uuid, stance) for _, v in group]

    def attack_move(self, e):
        """ATTACK MOVE (#2552): the group walks to the tile as with MOVE, and on Paper its military units take the
        aggressive stance for the walk, so the mob AI attacks each enemy in sight on the way (the stance goals of the
        plugin, #1104). A unit that the record set to another stance gets it back at the end of the walk (calm())."""
        import combat                                                   # combat -> gather -> build -> replay
        out = self.calm(e["objects"]) + self.move(dict(e, kind="move"))
        if not self.ai:
            return out
        for i in e["objects"]:
            if (v := self.units.get(i)) is None or not self.gather.military(v.name):
                continue
            out.append(combat.stance_command(v.uuid, "aggressive"))
            if self.stances.get(i, "aggressive") != "aggressive":
                self.charging[i] = self.stances[i]
        return out

    def calm_at(self, i):
        """The game time (ms) at the end of the last leg of unit i (0: no leg, or no unit)."""
        return (getattr(self.units.get(i), "leg", None) or (0, 0, 0))[2]

    def calm(self, ids):
        """The stance commands that give the units of an ended attack-move their stance of the record again (#2552)."""
        import combat
        back = {i: self.charging.pop(i) for i in ids if i in self.charging}
        return [combat.stance_command(self.units[i].uuid, s) for i, s in back.items() if i in self.units]

    def stop(self, e):
        """STOP: the selected units stand where they are (#2549): no more legs, steps or gather steps. On Paper
        `aoe stop` ends the walk order and the attack of the plugin (the mob has no AI until its next order, as at the
        end of a walk). The replay takes the unit where its entity stands (#2636). An unknown ID changes nothing."""
        self.grid()
        out = []
        for i, name in zip(e["objects"], e.get("names") or [None] * len(e["objects"])):
            if (v := self.unit(i, name, e["player"])) is None:
                continue
            for state in (self.moving, self.working, self.arriving, self.entering, self.builds):
                state.pop(i, None)
            v.pos, v.path = self.at(v, e["time"]), []
            at = self.entity(v) if self.ai else None               # Paper: the entity walks behind its leg (#2636)
            if at is not None and (y := self.map.y(math.floor(at[0]), math.floor(at[1]))) is not None:
                v.pos = (at[0], float(y), at[1])
            v.leg = (v.pos, e["time"], e["time"])                  # a new order starts here, not on the old leg
            out += self.look(v, "none") + [f"aoe stop {v.uuid}"] * self.ai
        return out

    def move(self, e):
        """MOVE and ORDER: each selected unit gets a path to the target. Its steps come later (steps()). A group
        that goes to a tile stops in a formation there (formation()), a unit with no path to its cell goes to the
        target tile."""
        self.grid()
        goals = self.goals(e)
        inside = {u: r for r, us in self.garrisons.items() for u in us}   # AoE2 selects no unit inside: an order
        out0 = [c for i in e["objects"] if i in inside for c in self.leave(i, inside[i])]   # says it is out (#1229)
        group = [(i, v) for i, name in zip(e["objects"], e.get("names") or [None] * len(e["objects"]))
                 if (v := self.unit(i, name, e["player"])) is not None]
        tile = self.resource(e)
        if tile in self.map.farms or tile in self.map.carcasses:    # a farmer stands on the farm, a hunter at the carcass
            goals = self.crew.goals(tile)
        home = self.holder(e)
        if home and e.get("target") not in self.refs:              # a building of the replay: next to it (#876)
            x0, x1, z0, z1 = home[0]
            goals = self.map.around({(x, z) for x in range(x0, x1) for z in range(z0, z1)})
        for i, v in group:                                          # a new MOVE or ORDER stops the work
            self.working.pop(i, None)
            self.builds.pop(i, None)
            self.arriving.pop(i, None)
            self.entering.pop(i, None)
            if e.get("garrison"):                                   # BACK TO WORK sends it there again
                self.work[i] = v.tree
            fish = fisher(v.name) and tile in self.map.fish         # a fishing ship only fishes (#1283)
            v.tree = tile if v.name.startswith("VILLAGER") or fish else None    # a sheep of the selection does not gather
            if home and not (not e.get("garrison") and v.load and v.name.startswith("VILLAGER")
                             and home[1]["name"] in self.gather.DROP_SITES.get(v.res, ())):   # it drops its load
                self.entering[i] = [*home, None]
        boats = [(i, v) for i, v in group if ship(v.name)]          # ships sail on the water (#866)
        wet = self.goals(e, True) if boats else set()
        group = [(i, v) for i, v in group if not ship(v.name)]
        if not goals:                                               # no free cell next to the target (#869)
            near = [(i, v, self.detour(i, v, tile, e["time"])) for i, v in group]
            group, first = [], [c for i, v, cmds in near if cmds is not None
                                for c in self.look(v, self.gather.job_of(self.map, tile)) + cmds]
        else:
            first = []
        boats = boats if wet else []
        if not group and not boats:
            return out0 + first
        looks = [c for _, v in group for c in self.look(v, self.gather.job_of(self.map, tile) if tile else "none")]
        to_tile = not (e["kind"] == "order" and e.get("target") is not None)
        slots = self.formation([v for _, v in group], e["tile"]) if to_tile and group else {}
        out = []
        if self.ai:
            out, group = self.attack(group, target, e) if (target := self.enemy(e)) else ([], group)
            out += self.target_mark(e) if target else []            # the red order marker (#845)
            for i, v in group:
                v.pos = self.at(v, e["time"])                       # it stops its leg where it is
                end = slots.get(v) or min(goals, key=lambda c: (math.dist(c, v.cell), c))
                path = self.map.path(v.cell, {end}, PATH_CELLS)
                if path is None and (cmds := self.side(i, v)):
                    out += cmds
                    path = self.map.path(v.cell, {end}, PATH_CELLS)
                if path is None and (cmds := self.detour(i, v, tile, e["time"])) is not None:
                    out += cmds
                    continue
                path = path or []
                cmds, due = self.order(v, path[LEG - 1:-1:LEG] + [end], e["time"])
                out += cmds
                if v.path or (i in self.patrols or i in self.scouts) and due > e["time"]:   # a patrol turns at the end
                    # (steps(), #2550), a scout walks on (#2678)
                    self.moving[i] = due
                else:
                    self.moving.pop(i, None)
                    self.start(i, v, due)
                    self.rest(i, due)
            group = []
        for i, v in group + boats:                                  # a boat has no path finding: /tp steps
            w = ship(v.name)
            v.path = (self.map.path(v.cell, {slots[v]}, PATH_CELLS) if v in slots else None) or \
                self.map.path(v.cell, wet if w else goals, PATH_CELLS, w)
            if v.path is None and not w and (cmds := self.side(i, v)):
                out += cmds
                v.path = self.map.path(v.cell, goals, PATH_CELLS)
            if v.path is None and not w and self.detour(i, v, tile, e["time"]) is not None:
                continue
            v.path = v.path or []
            due = self.moving[i] if i in self.moving and v.path else self.next_step(v, e["time"])
            if due is None:
                self.moving.pop(i, None)
                self.start(i, v, e["time"])
            else:
                self.moving[i] = due
        return out0 + first + looks + out

    def patrol(self, e):
        """PATROL: the units walk between their place and the tile, again and again, until another order (AoE2). A
        second PATROL of a unit on patrol adds a point to its route (AoE2 shift patrol): it walks on through all
        points and back. The aggressive stance of a military unit attacks the enemies on the way (#1104)."""
        self.grid()
        new = []
        for i, name in zip(e["objects"], e.get("names") or [None] * len(e["objects"])):
            if i in self.patrols:
                self.patrols[i][0].append(list(e["tile"]))
            elif (v := self.unit(i, name, e["player"])) is not None:
                self.patrols[i] = [[[v.pos[0] / self.T, v.pos[2] / self.T], list(e["tile"])], 1, 1]
                new.append(i)
        return self.move(dict(e, kind="move", objects=new, names=None)) if new else []

    def patrol_on(self, i, t):
        """The walk of unit i on patrol to the next point of its route at game time t (ms): at the last point it
        turns back (#2550)."""
        points, k, d = self.patrols[i]
        if not 0 <= k + d < len(points):
            d = -d
        self.patrols[i] = [points, k + d, d]
        return self.move({"time": t, "player": self.units[i].player, "kind": "move", "objects": [i],
                          "tile": points[k + d]})

    def autoscout(self, e):
        """AUTOSCOUT (AoE2 DE): the units walk to the nearest tile that their player did not explore, then to the next
        one, until another order or until the player explored all tiles. The record has no positions of the scout.
        Minecraft has no "explore" goal: own choice of the tile, the plugin walks (#2678)."""
        self.explore()                                              # the sight of the units now
        out = []
        for i, name in zip(e["objects"], e.get("names") or [None] * len(e["objects"])):
            if self.unit(i, name, e["player"]) is not None:             # a trained scout: its name gives its unit
                self.scouts[i] = set()
                out += self.scout_on(i, e["time"])
        return out

    def scout_on(self, i, t):
        """The walk of scout i at game time t (ms) to the nearest tile that its player did not explore and that it did
        not walk to before (a tile out of reach stays unexplored), or [] at the end of the scouting (#2678)."""
        v, tried = self.units[i], self.scouts[i]
        tried.add((int(v.pos[0] // self.T), int(v.pos[2] // self.T)))     # its own tile: no walk of length 0
        n = self.data.get("map_size") or self.n // self.T                 # tiles of a map side
        free = np.ones((n, n), bool)
        old = [(x, y) for x, y in self.explored.get(v.player, set()) | tried if 0 <= x < n and 0 <= y < n]
        if old:
            free[tuple(np.array(old).T)] = False
        if not free.any():
            del self.scouts[i]
            return []
        xs, ys = np.nonzero(free)
        k = np.argmin((xs + 0.5 - v.pos[0] / self.T) ** 2 + (ys + 0.5 - v.pos[2] / self.T) ** 2)
        tried.add((int(xs[k]), int(ys[k])))
        return self.move({"time": t, "player": v.player, "kind": "move", "objects": [i],
                          "tile": [float(xs[k]) + 0.5, float(ys[k]) + 0.5]})

    def look(self, v, task):
        """The command that gives villager v the look of the AoE2 task (`LUMBERJACK` ..., "none": no work), when it
        changes (gather.Gather.task)."""
        if v is None or not v.name.startswith("VILLAGER"):
            return []
        out, keep = [], getattr(self.crew, "command", None)         # steps() sends the gather looks to its list
        self.crew.command = out.append
        self.crew.task(v, task)
        self.crew.command = keep
        return out

    def order(self, v, legs, t, behind=False):
        """The plugin walks unit v on a Minecraft path to the first cell of `legs`, at its walk speed times the replay
        speed (#438). The path search of Minecraft reaches only about 128 blocks, so a long way goes in legs of
        LEG cells of the path of gather.Map: the next leg starts when the unit is due at the end of this one.
        The replay takes the unit at the end of its leg (only the first gather step reads the entity, #766). Returns the commands
        and the game time (ms) at the end of the leg (the next leg starts then, if v.path has one). behind: the next
        leg of a long walk. It and a walk less than RECENT ms after the last leg read the entity to catch up (catch_up)."""
        import ai                                                   # ai -> replay: import it late
        x, z = legs[0]
        chain, v.stand = behind, getattr(v, "stand", None) if behind else None   # a new walk: no old place
        behind = behind or (getattr(v, "leg", None) or (0, 0, -RECENT))[2] > t - RECENT
        start = x0, _, z0 = v.pos
        y = self.map.y(x, z)                                        # water has no ground: the unit keeps its height (#3000)
        v.pos, v.path = (x + 0.5, float(v.pos[1] if y is None else y), z + 0.5), legs[1:]
        speed = next((s for k, s in SPEEDS.items() if v.name.startswith(k)), 1.0) * self.T    # blocks per second
        d = math.hypot(v.pos[0] - x0, v.pos[2] - z0)
        due = t + 1000 * d / speed
        v.leg = (start, t, due)                                     # at() reads it
        v.check = t + CLOSE if due - t > 2 * CLOSE else None        # a long leg reads the entity again (recheck())
        at = self.entity(v) if chain or behind and d >= 1 else None
        free = self.unstick(v, start, t, at) if chain else []
        f = min(CATCH_UP, PATH * (self.catch_up(v, d, speed * CLOSE / 1000, at) if behind and not free else 1.0))
        return free + [ai.speed_command(v.uuid, v.name, self.T, self.speed * f),
                       "aoe moveto {} {} {} {}".format(v.uuid, *v.pos)], due

    def recheck(self, v, t):
        """The walk speed command of unit v at game time t, CLOSE ms after the start of its long leg: its lag to the
        replay position on the leg (at()) closes in the next CLOSE ms (catch_up), and a unit with no lag walks at its
        speed again. A turn on a leg (an order back) costs the mob 1 to 3 s of game time that order() cannot see: a
        villager of de-64.3 stayed 5 to 11 blocks behind for 30 s (#1293). One command per long leg, and the /tp of a
        unit that stands still (unstick)."""
        import ai                                                   # ai -> replay: import it late
        v.check = None
        speed = next((s for k, s in SPEEDS.items() if v.name.startswith(k)), 1.0) * self.T    # blocks per second
        at = self.entity(v)
        if free := self.unstick(v, v.leg[0], t, at):
            return free + [ai.speed_command(v.uuid, v.name, self.T, self.speed * PATH)]
        f = self.catch_up(v, math.dist(self.at(v, t)[::2], v.pos[::2]), speed * CLOSE / 1000, at)
        return [ai.speed_command(v.uuid, v.name, self.T, self.speed * min(CATCH_UP, PATH * f))]

    def entity(self, v):
        """(x, z) of the entity of unit v, or None."""
        self.flush()
        m = re.findall(self.gather.NUMBER, self.game.command(f"data get entity {v.uuid} Pos").rsplit(":", 1)[-1])
        return (float(m[0]), float(m[2])) if len(m) == 3 else None

    def unstick(self, v, start, t, at):
        """The /tp of walking unit v to start (the start of its leg: a free cell of its path) when its entity at stands
        on the place of the last check of this walk, STILL ms ago or more, and more than NEAR blocks from start.
        A Minecraft path can have a step that the mob cannot take: in de-64.3 two villagers stood for minutes at the
        edge of a forest with an order, as the step onto a moss carpet (1/16 block) lifted their heads into the leaves 2
        blocks over their column (#2304). Returns the commands."""
        last, v.stand = getattr(v, "stand", None), at and (*at, t)
        if at is None or last is None or t - last[2] < STILL or math.dist(at, last[:2]) >= 0.5 \
                or math.dist(at, (start[0], start[2])) <= NEAR:
            return []
        v.stand = None
        return ["tp {} {} {} {}".format(v.uuid, *start)]

    def catch_up(self, v, d, reach=None, at=()):
        """The factor of the walk speed of unit v on a leg of d blocks to v.pos (1 to CATCH_UP): the lag of the entity
        (its distance to v.pos less d) is closed in the first `reach` blocks of the leg (default: all of it). The
        Minecraft path is longer than the straight leg (trees, steps on a slope), and each leg starts at the replay
        time, not at the arrival: without it, villagers of de-64.3 walked at 89 to 94 % of their AoE2 speed (#1168).
        With the whole leg, a lag of 10 blocks on a long leg stayed above 4 blocks for 30 s (#1291). One command per
        leg that order() gives as behind. at: the (x, z) of the entity (or None) that the caller read (entity())."""
        if d < 1:
            return 1.0
        if (at := self.entity(v) if at == () else at) is None:
            return 1.0
        lag = math.dist(at, (v.pos[0], v.pos[2])) - d
        return min(CATCH_UP, max(1.0, 1 + lag / min(d, reach or d)))

    def at(self, v, t):
        """The replay position of unit v at game time t (ms): on the line of its leg while it walks, else v.pos.
        A new order starts there, not at the end of the leg: a scout gets a new order every 2 to 5 s, and its
        replay position jumped up to 250 blocks ahead of it (#851)."""
        start, t0, t1 = getattr(v, "leg", None) or (v.pos, 0, 0)
        if not t0 <= t < t1:
            return v.pos
        f = (t - t0) / (t1 - t0)
        return tuple(a + f * (b - a) for a, b in zip(start, v.pos))

    def formation(self, group, tile):
        """The end cell of each unit of a group that walks to a tile (#410): rows across the walk direction, the
        first row on the target and the others behind it, FORMATION blocks apart (AoE2 line formation). A slot
        snaps to the next free cell, one unit per cell. The units nearest to the target take the first row, and
        in a row they keep their order from left to right, so that the paths do not cross. The formation of the
        record (#2553): Staggered doubles the gaps, Flank splits each row into two halves 4 slots apart, Box puts
        the ranged and civilian units inside a square of the others."""
        import combat                                                   # combat -> gather -> build -> replay
        m, n, S = self.map, len(group), FORMATION
        ids = {v: i for i, v in self.units.items()}
        kind = collections.Counter(self.formations.get(ids.get(v), "Line") for v in group).most_common(1)[0][0]
        S *= 2 if kind == "Staggered" else 1
        tx, tz = tile[0] * self.T, tile[1] * self.T
        cx, cz = (sum(v.pos[k] for v in group) / n for k in (0, 2))
        d = math.hypot(tx - cx, tz - cz)
        dx, dz = ((tx - cx) / d, (tz - cz) / d) if d > 0.5 else (0.0, -1.0)    # walk direction (else north)
        cols = min(n, max(1, math.ceil(math.sqrt(n)) if kind == "Box" else round(math.sqrt(2 * n))))
        rows = -(-n // cols)
        r = max(2 * self.T, math.ceil(max(cols, rows) * S) + 4 * S * (kind == "Flank"))
        x0, z0 = int(tx), int(tz)
        todo = {(x, z) for x in range(x0 - r, x0 + r + 1) for z in range(z0 - r, z0 + r + 1) if m.free(x, z)}
        group = sorted(group, key=lambda v: (tx - v.pos[0]) * dx + (tz - v.pos[2]) * dz)
        slots = []                                                      # (unit, row, offset across the walk)
        if kind == "Box":
            cells = [(q, j) for q in range(rows) for j in range(cols)][:n]
            inner = [c for c in cells if 0 < c[0] < rows - 1 and 0 < c[1] < cols - 1]
            outer = [c for c in cells if c not in inner]
            weak = [v for v in group if combat.stats(v.name).range > 0 or not self.gather.military(v.name)]
            order = weak + [v for v in group if v not in weak]
            cells = inner[:len(weak)] + outer + inner[len(weak):]
            slots = [(v, q, (j - (cols - 1) / 2) * S) for v, (q, j) in zip(order, cells)]
        else:
            for q in range(rows):
                row = sorted(group[q * cols:q * cols + cols], key=lambda v: v.pos[0] * -dz + v.pos[2] * dx)
                for j, v in enumerate(row):
                    gap = (2 * S if j >= len(row) / 2 else -2 * S) if kind == "Flank" and len(row) > 1 else 0
                    slots.append((v, q, (j - (len(row) - 1) / 2) * S + gap))
        out = {}
        for v, q, off in slots:
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
        out = self.expire(t) + self.chase(t)
        for i, then in self.built(t):                               # the builders gather or stand idle (#1282)
            out += self.move(then) if then else self.look(self.units[i], "none")
        sink = types.SimpleNamespace(map=self.map, command=out.append)
        for i, due in list(self.moving.items()):
            v, at = self.units[i], due
            w = ship(v.name)
            ok = self.map.wet if w else self.map.free
            if self.ai and not w and t < due and (getattr(v, "check", None) or due) <= t:
                out += self.recheck(v, t)
            if self.ai and not w and due <= t:
                legs = [c for c in v.path if self.map.free(*c)]        # a new building on a leg end: skip it
                cmds, at = self.order(v, legs, due, behind=True) if legs else ([], due)
                due = at if v.path and legs else None
                out += cmds
            while (not self.ai or w) and due is not None and due <= t:
                if not v.path:                                          # no cell left: it stops (#1177)
                    due = None
                    break
                if not ok(*v.path[0]):                                  # a new building on the way: a new path
                    goal = v.path[-1]
                    v.path = (self.map.path(v.cell, {goal}, PATH_CELLS, w) or []) if ok(*goal) else []
                    if not v.path:
                        due = None
                        break
                (sail if w else self.gather.walk)(sink, v)
                at, due = due, self.next_step(v, due)
            if due is None:
                del self.moving[i]
                self.start(i, v, at)
                if self.ai and not w:
                    self.rest(i, at)
                out += self.patrol_on(i, at) if i in self.patrols else []
                out += self.scout_on(i, at) if i in self.scouts else []
            else:
                self.moving[i] = due
        out += self.calm([i for i in self.charging if i not in self.moving and self.calm_at(i) <= t])   # (#2552)
        out += self.settle(t)
        out += self.enter(t)
        self.crew.command = out.append
        for i, due in list(self.working.items()):
            v = self.units[i]
            if i in self.arriving and due <= t:                     # Paper: the real unit can be late (#766)
                late = due - self.arriving[i] >= LATE
                if not late and (at := self.entity(v)) and math.dist(at, v.pos[::2]) > NEAR:
                    if v.stand is None or math.dist(at, v.stand[:2]) >= 0.5:
                        v.stand = (*at, due)
                    stuck = due - v.stand[2] >= STILL                   # it stands: the plugin dropped its walk (#2709)
                    if not stuck or not v.again:
                        self.working[i] = due + WAIT
                        if stuck:                                       # one new walk order, then /tp
                            v.again, v.stand = True, None
                            out.append("aoe moveto {} {} {} {}".format(v.uuid, *v.pos))
                        continue
                    late = True
                out.append(f"aoe stop {v.uuid}")                     # ends its walk order: no brain turns it (#867)
                if late:
                    out.append("tp {} {} {} {}".format(v.uuid, *v.pos))
                del self.arriving[i]
            src = self.crew.source(v)
            if due <= t and v.tree in self.prey:
                out += self.kill(v.tree, v)
            while due <= t and src.get(v.tree, 0) > 0:
                src[v.tree] -= 1
                v.load += 1
                self.resources(v.player)[v.res] += 1
                g = self.gathered.setdefault(v.player, dict.fromkeys(START, 0))
                g[v.res] += 1
                if self.eyes is None or any(math.dist(e, (v.pos[0], v.pos[1] + 1, v.pos[2])) <= SEEN for e in self.eyes):
                    self.crew.work(v)                               # the look and sound of the step (#592, #2761)
                if v.tree in self.map.farms:                            # the wheat gets younger, the farmer walks
                    self.crew.harvest(v.tree)
                    self.crew.tend(v)
                elif v.tree in self.map.carcasses or v.tree in self.map.fish:   # a carcass or a fish has no blocks
                    pass
                elif v.res == "food":
                    self.crew.berries(v.tree)
                elif v.res != "wood":
                    if src[v.tree] == 0:
                        self.crew.dig(v.tree, v.res)
                elif src[v.tree] == 0:
                    self.crew.fell(v.tree)
                else:
                    self.crew.trunk(v.tree)
                due += 1000 / self.rate(v)
            if src.get(v.tree, 0) > 0:
                self.working[i] = due
            else:
                del self.working[i]
                out += self.next_resource(i, v, due - 1000 / self.rate(v))
        return out

    def rest(self, i, t):
        """Unit i of the plugin ends its walk at game time t with no work there: settle() checks that it got there."""
        if i not in self.working and i not in self.entering:
            self.idle[i] = (t + STILL, t)

    def settle(self, t):
        """The commands for the units with no order that stand far from the end of their walk at game time t: the
        replay takes a unit at the end of its last leg, so nothing else checks it. A unit more than HOME blocks from it
        walks there again with the plugin (from its own place), each STILL ms; HOME_MS after the end of the walk it
        goes there with /tp. In de-64.3 three villagers stood 42 blocks from their replay position for 10 minutes
        (#2633). A unit at a resource or a building has its own checks (arrived(), enter())."""
        out = []
        for i, (due, end) in list(self.idle.items()):
            if due > t:
                continue
            v = self.units.get(i)
            if v is None or i in self.moving or i in self.working or i in self.entering:
                del self.idle[i]
                continue
            at = self.entity(v)
            if at is None or math.dist(at, (v.pos[0], v.pos[2])) <= HOME:
                del self.idle[i]
            elif t - end >= HOME_MS:
                out.append("tp {} {} {} {}".format(v.uuid, *v.pos))
                del self.idle[i]
            else:
                out.append("aoe moveto {} {} {} {}".format(v.uuid, *v.pos))
                self.idle[i] = (t + STILL, end)
        return out

    def next_resource(self, i, v, t):
        """Unit i gathered the last of its resource at game time t: as in AoE2 it walks to the nearest resource of
        the same kind within NEXT tiles that has something left, and gathers there (#720). Else it stays (the record
        has no drop-off). Returns the commands (Paper: the first leg)."""
        way = self.reachable(v, v.cell)
        return self.look(v, "none") if way is None else self.go(i, v, *way, t)

    def reachable(self, v, at):
        """(tile, path) of the resource of the kind of v within NEXT tiles of cell `at` that has something left and
        is nearest on a path from v (one path search for all of them, #869), or None."""
        T, w = self.T, ship(v.name)
        far = {k: math.dist((at[0] / T, at[1] / T), (k[0] + 0.5, k[1] + 0.5)) for k, n in self.crew.source(v).items()
               if n > 0}
        goals = {}
        for d, k in sorted((d, k) for k, d in far.items() if d <= NEXT):
            for c in self.map.around(self.map.spot(k), w):        # a fishing ship: the water next to the fish
                goals.setdefault(c, k)                              # a cell next to two of them: the nearer one
        path = self.map.path(v.cell, goals, PATH_CELLS, w)
        return None if path is None else (goals[path[-1] if path else v.cell], path)

    def go(self, i, v, tile, path, t):
        """Unit i walks on path to its resource `tile` from game time t on, and gathers there. Returns the commands
        (Paper: the first leg). An empty path on Paper: an order to its cell all the same. The replay unit is there, but
        its entity can be on the way to an old goal: a builder of de-64.3 walked on 30 blocks and stood there (#2634)."""
        v.tree = tile
        if self.ai and not ship(v.name):                            # a boat has no path finding: /tp steps
            cmds, due = self.order(v, path[LEG - 1:-1:LEG] + [path[-1]] if path else [v.cell], t)
            if v.path:
                self.moving[i] = due
            else:
                self.moving.pop(i, None)                            # it was on a walk: it stops (#1177)
                self.start(i, v, due)
                self.rest(i, due)                                   # a builder has no work check: settle()
            return cmds
        v.path = path
        due = self.next_step(v, t)
        if due is None:
            self.moving.pop(i, None)
            self.start(i, v, t)
        else:
            self.moving[i] = due
        return []

    def detour(self, i, v, tile, t):
        """A villager whose ORDER on a tree, bush or mine `tile` found no path takes the nearest one of the same kind
        that it can reach, as in AoE2 (#869). Returns the commands, or None (no such resource: the order stays)."""
        if tile is None or tile in self.map.farms or not v.name.startswith("VILLAGER"):
            return None
        v.res = self.map.resource(tile)
        way = self.reachable(v, (tile[0] * self.T, tile[1] * self.T))
        return None if way is None else self.go(i, v, *way, t)

    def holder(self, e):
        """(footprint, entry of aoe2mc.json) of the own start building with garrison room that an ORDER targets, or
        None. The record has no IDs of the buildings of the replay."""
        import garrison
        t = e.get("target") if e["kind"] == "order" else None
        o = self.refs.get(t)
        if o is None and t is not None and t not in self.units and e.get("target_name") in garrison.SIZES:
            r = self.new_building(t, e["target_name"], e["player"], e.get("tile"))   # a building of the replay (#876)
            return (r, {"name": e["target_name"], "player": e["player"]}) if r else None
        if not o or o["kind"] != "building" or o["name"] not in garrison.SIZES or o["player"] != e["player"]:
            return None
        return next(((s[3], o) for s in self.starts if s[0] == o["ref"]), None)

    def new_building(self, i, name, player, tile=None, full=False):
        """The footprint of the replay building with the new object ID i (aoe2mc.name_timeline gives its name), or
        None. The record has no IDs of new buildings (#876): the first command on i takes the building of the player
        with that name under the tile of the click, else the newest one that no other ID has (full: one with units
        inside first, for UNGARRISON). Later commands on i take the same building."""
        rects = [r for p, n, r in self.placed if (p, n) == (player, name)]
        if self.ids.get(i) in rects:
            return self.ids[i]
        c = (int(tile[0] * self.T), int(tile[1] * self.T)) if tile else None
        under = [r for r in rects if c and r[0] <= c[0] < r[1] and r[2] <= c[1] < r[3]]
        free = [r for r in rects if r not in self.ids.values()]
        r = (under or [r for r in free if r in self.garrisons] * full or free or [None])[-1]
        if r:
            self.ids[i] = r
        return r

    def enter(self, t):
        """The units that arrived at their building until game time t (ms) go inside (garrison.enter). A full
        building: they stay next to it, as in AoE2."""
        import garrison
        out, full = [], set()
        for i, (rect, o, at) in list(self.entering.items()):
            if at is None or at > t:
                continue
            del self.entering[i]
            units, v = self.garrisons.setdefault(rect, []), self.units[i]
            if len(units) >= garrison.SIZES[o["name"]]:
                continue
            x, y, z = garrison.cell(self.map, rect, o, len(units))
            units.append(i)
            full.add(rect)
            v.pos, v.path = (x + 0.5, float(y), z + 0.5), []
            self.moving.pop(i, None)                                # inside: no walk (#1177)
            out += [f"aoe stop {v.uuid}"] * self.ai + garrison.enter(v.uuid, x, y, z)
        return out + [c for r in sorted(full) for c in self.arrows(r)]

    def arrows(self, rect):
        """`aoe arrows` of the plugin for the start building rect with the units inside it (#1203), as the game program
        (#1113): only with the plugin, and only for a building with a target entity that shoots (combat.setup)."""
        import combat, garrison
        name = next((s[2] for s in self.starts if s[3] == rect), None)
        s = combat.stats(name) if self.ai and name in combat.BUILDINGS else None
        if not (s and s.attack and s.range):
            return []
        inside = [self.units[i].name for i in self.garrisons.get(rect, []) if i in self.units]
        return [f"aoe arrows {combat.target_uuid([rect[0], rect[2], rect[1], rect[3]])} {garrison.arrows(name, inside)}"]

    def holders(self, e):
        """The footprints of the buildings of an UNGARRISON or BACK TO WORK event that the replay knows."""
        import garrison
        starts = {s[0]: s[3] for s in self.starts}
        rects = [starts[i] if i in starts else name in garrison.SIZES and self.new_building(i, name, e["player"],
                                                                                          full=True)
                 for i, name in zip(e["objects"], e.get("names") or [None] * len(e["objects"]))]
        return [r for r in rects if r]

    def back(self, e):
        """BACK TO WORK (#1179): the units inside the buildings come out, and each goes back to the resource that it
        left for the garrison, as in AoE2. Returns the commands and the IDs of the units that work again."""
        out, work = [], {}
        for r in self.holders(e):
            units = list(self.garrisons.get(r, []))
            out += self.release(r)
            for i in units:
                if (tile := self.work.pop(i, None)) is not None:
                    work.setdefault(tile, []).append(i)
        for (x, z), ids in sorted(work.items()):                    # an order on the resource tile
            out += self.move(dict(time=e["time"], player=e["player"], kind="order", target=-1, objects=ids,
                                  names=[None] * len(ids), tile=[x + 0.5, z + 0.5], resource=(x, z)))
        return out, [i for ids in work.values() for i in ids]

    def release(self, rect):
        """The units inside the building rect come out on the free cells next to it, the door side first."""
        import garrison
        ring, out = self.map.front(rect) or [((rect[0] + rect[1]) // 2, rect[3])], []
        for k, i in enumerate(self.garrisons.pop(rect, [])):
            x, z = ring[k % len(ring)]
            v, y = self.units[i], self.map.y(x, z) or 0
            v.pos = (x + 0.5, float(y), z + 0.5)
            out += garrison.leave(v.uuid, x, y, z) + [f"aoe label {v.uuid}"] * self.ai
        return out + self.arrows(rect)

    def leave(self, i, rect):
        """Unit i comes out of the building rect alone, on the first free cell next to it (release()). Returns the
        commands."""
        import garrison
        self.garrisons[rect].remove(i)
        self.work.pop(i, None)                                      # a new order: no BACK TO WORK
        if not self.garrisons[rect]:
            del self.garrisons[rect]
        (x, z), v = (self.map.front(rect) or [((rect[0] + rect[1]) // 2, rect[3])])[0], self.units[i]
        y = self.map.y(x, z) or 0
        v.pos = (x + 0.5, float(y), z + 0.5)
        return garrison.leave(v.uuid, x, y, z) + [f"aoe label {v.uuid}"] * self.ai + self.arrows(rect)

    def resource(self, e):
        """The tile of the tree, fruit bush, mine, fish or farm that an ORDER targets, else None. A target that the replay
        does not know (a farm of the replay: the record has no IDs of new objects) is the farm under the order tile."""
        t, m = e.get("target"), self.map
        if "resource" in e:                                         # BACK TO WORK: the tile that the unit left
            return e["resource"]
        o = self.refs.get(t) if e["kind"] == "order" else None
        if e["kind"] == "order" and t is not None and o is None and t not in self.units and "tile" in e:
            return m.farm_at.get((int(e["tile"][0] * self.T), int(e["tile"][1] * self.T)))
        if not o or "tile" not in o:
            return None
        if o["kind"] == "unit" and (food := self.gather.hunt_food(o["name"])) and "tile" in e:
            if t not in self.hunted:                                # the hunt: its carcass at the order tile (#1229)
                self.hunted[t] = tile = self.free_tile(int(e["tile"][0]), int(e["tile"][1]))
                if uuid := o.get("uuid"):                               # the first hunter there kills it (#1281)
                    self.prey[tile] = uuid
                m.carcasses[tile] = m.carcasses.get(tile, 0) + food
                if o["name"] in self.gather.HERDS:
                    m.herds.add(tile)
            return self.hunted[t]
        tile = int(o["tile"][0]), int(o["tile"][1])
        if o["kind"] == "building":
            return tile if "FARM" in o["name"] and tile in m.farms else None
        if o["kind"] != "other":
            return None
        return tile if tile in m.trees or tile in m.bushes or tile in m.fish or any(tile in s for s in m.mines.values()) \
            else None

    def free_tile(self, x, y):
        """The tile nearest to (x, y) with no tree, bush, mine, fish or farm: a carcass on it would give the wrong
        resource (gather.Map.resource, #1281)."""
        m = self.map
        taken = m.trees.keys() | m.bushes.keys() | m.fish.keys() | m.farms.keys() | {c for s in m.mines.values() for c in s}
        return min(((x + dx, y + dy) for dx in range(-3, 4) for dy in range(-3, 4)
                    if (x + dx, y + dy) not in taken), key=lambda c: (abs(c[0] - x) + abs(c[1] - y), c), default=(x, y))

    def kill(self, tile, v=None):
        """The command that kills the hunted animal of a carcass tile, once (the vanilla death, as gather.Gather)."""
        uuid = self.prey.pop(tile, None)
        return [f"damage {uuid} 1000 minecraft:mob_attack" + (f" by {v.uuid}" if v else "")] if uuid else []

    def start(self, i, v, t):
        """A unit with a resource that ends its walk next to it gathers from game time t on, at the AoE2 work rate
        of the resource (gather.AOE2_WORK, per game second). The record has no drop-off: it does not carry.
        A farmer works on its farm (gather.Gather.goals). A unit that goes into a building arrives (enter())."""
        if i in self.entering:
            x0, x1, z0, z1 = self.entering[i][0]
            if v.cell in self.map.around({(x, z) for x in range(x0, x1) for z in range(z0, z1)}):
                self.entering[i][2] = t
            return
        if v.tree is None or v.cell not in (self.map.around(self.map.spot(v.tree), True) if ship(v.name)
                                            else self.crew.goals(v.tree)):
            return
        v.res, v.load = self.map.resource(v.tree), 0
        if self.crew.source(v).get(v.tree, 0) > 0:
            self.working[i] = t + 1000 / self.rate(v)
            if self.ai and not ship(v.name):                        # a boat sails with /tp steps: it is there
                self.arriving[i], v.again, v.stand = t, False, None

    def rate(self, v):
        """The AoE2 work rate of unit v at its resource (per game second): a farm, a hunt and a fish have their own
        rates, and a fishing ship has its own rates (#1283)."""
        m, t = self.map, v.tree
        if t in m.fish and ship(v.name):
            return self.gather.SHIP_WORK["shore" if t in m.shore else "deep"]
        return self.gather.AOE2_WORK["farm" if t in m.farms else "hunt" if t in m.carcasses else "fish" if t in m.fish
                                     else m.resource(t)]

    def state(self, i):
        return aoe2mc.B.states[i]

    @staticmethod
    def fill(x0, y0, z0, x1, y1, z1, what):
        """/fill commands for a box, cut into layers of at most MAX_FILL blocks."""
        step = max(1, MAX_FILL // ((x1 - x0 + 1) * (z1 - z0 + 1)))
        return [f"fill {x0} {y} {z0} {x1} {min(y + step - 1, y1)} {z1} {what}" for y in range(y0, y1 + 1, step)]

    @staticmethod
    def clock_commands(now, end, speed, done=False, jump=False):
        """The boss bar commands for game time `now` (ms) of a replay that ends at `end` (ms): the time and speed as
        its name, the game seconds as its value (#684). `players @a` also adds the players who joined later.
        jump: the loading text while a jump to `now` sends its commands (#871)."""
        m, s = divmod(int(now) // 1000, 60)
        name = (f"End {m:02d}:{s:02d}" if done else f"Jump to {m:02d}:{s:02d} ..." if jump else
                f"{m:02d}:{s:02d} · speed {speed:g}×")
        return [f"bossbar set {BAR} name {json.dumps(text(name), ensure_ascii=False)}",
                f"bossbar set {BAR} value {min(int(now) // 1000, max(1, int(end) // 1000))}", f"bossbar set {BAR} players @a"]

    def fog(self):
        """With a view player `pov`: hide the enemy units out of the sight of it and its allies for the spectators
        (Paper Player#hideEntity, plugin `aoe hide`), show the ones that came in again (#1302). Only the changes:
        at most one hide and one show command. Without a view player again: show all hidden units (#1303).
        On Paper also the fog of the terrain on the minimap (#1567, minimap_fog)."""
        mobs, sight = self.explore()                                # also without a view player (#1801)
        if self.pov is None and not self.hidden and not self.fogged:
            return []
        import gather                                               # gather -> build -> replay: import it late
        teams = self.data.get("players", {})
        own = {p for p in sight if gather.allied(teams, self.pov, p)}
        tiles = set().union(*(sight[p] for p in own))               # allies share the sight (#1567)
        out = {v.uuid for v in mobs if v.player not in (0, None) and v.player not in own and v.pos is not None
               and (int(v.pos[0] // self.T), int(v.pos[2] // self.T)) not in tiles} if self.pov is not None else set()
        hide, show = sorted(out - self.hidden), sorted(self.hidden & {v.uuid for v in mobs} - out)   # not the dead
        self.hidden = out
        k = (RCON_MAX - 20) // 37                                    # UUIDs per command (36 characters and a space)
        return [f"aoe {verb} @a {' '.join(u[i:i + k])}" for verb, u in (("hide", hide), ("show", show))
                for i in range(0, len(u), k)] + self.minimap_fog(own, tiles) * self.ai + self.minimap_buildings(own, tiles)

    def explore(self, trail=()):
        """Add the sight of each player now to the tiles that it explored (#1801): from the start of the replay, also
        without a view player and around a jump, so that a view chosen later shows all that the player saw, as in
        AoE2. trail: more places (Seen) of the units, on the walks of a jump. Returns (the units, {player: tiles in its
        sight})."""
        self.grid()                                                 # the start units
        mobs = {v.uuid: v for v in [*self.units.values(), *(v for _, v in self.new)]
                if v.uuid and hasattr(v, "player")}.values()
        placed = [s[1:] for s in self.starts] + self.placed
        sight = {p: seen([*mobs, *trail], placed, p, self.T) for p in ({v.player for v in mobs} | {p for p, _, _ in placed}) - {0, None}}
        import gather                                               # gather -> build -> replay: import it late
        teams = self.data.get("players", {})
        for p in sight:                                             # allies share the sight (#1567)
            self.explored.setdefault(p, set()).update(*(t for q, t in sight.items() if gather.allied(teams, p, q)))
        return mobs, sight

    def minimap_fog(self, own, tiles):
        """The fog of the view player on the map item (#1567, Minimap.java): the tiles that the view player and its
        allies `own` never saw are black, the explored tiles out of sight `tiles` are dark. Only the changes; a new
        view player starts the fog again (all unexplored), no view player removes it."""
        if self.pov is None:
            out, self.fogged = ["aoe minimap fog off"] * (self.fogged is not None), None
            return out
        n = self.data.get("map_size") or self.n // self.T                 # tiles of a map side
        inside = {(x, y) for x, y in tiles if 0 <= x < n and 0 <= y < n}
        dim = {(x, y) for p in own for x, y in self.explored.get(p, ()) if 0 <= x < n and 0 <= y < n} - inside
        new = self.fogged is None or self.fogged[0] != self.pov
        old_see, old_dim = (set(), set()) if new else self.fogged[1:]
        self.fogged = (self.pov, inside, dim)
        return [f"aoe minimap fog {self.T} {n}"] * new + runs("aoe minimap see", inside - old_see) + \
            runs("aoe minimap dim", dim - old_dim)

    def minimap_buildings(self, own, tiles):
        """The buildings of the replay on the map item (#1238) with a view player (#1678): the ones of the view player
        and its allies `own`, and the enemy ones that they saw, in the last seen state, as in AoE2: an enemy building
        shows when a tile of it comes into the sight `tiles`, and one that died out of sight stays until its place
        comes into sight. Only the changes; no view player: all buildings again."""
        if not self.ai:
            return []
        T, placed = self.T, {rect: p for p, _, rect in [s[1:] for s in self.starts] + self.placed}   # the start ones too (#1940)
        want = placed
        if self.pov is not None:
            known = self.known.setdefault(self.pov, {})
            for rect, p in [*known.items(), *placed.items()]:
                if p not in own and tiles & {(x, z) for x in range(rect[0] // T, (rect[1] - 1) // T + 1)
                                             for z in range(rect[2] // T, (rect[3] - 1) // T + 1)}:
                    if rect in placed:
                        known[rect] = p
                    else:
                        known.pop(rect, None)                       # its place is in sight: it is gone
            want = {r: p for r, p in placed.items() if p in own} | known
        out = [f"aoe minimap unbuild {r[0]} {r[2]}" for r in sorted(set(self.drawn) - set(want))] + \
            [f"aoe minimap building {r[0]} {r[2]} {r[1]} {r[3]} p{p}" for r, p in sorted(want.items()) if self.drawn.get(r) != p]
        self.drawn = dict(want)
        return out

    def overview(self, join=False):
        """The view of a player at the start of the replay (#737, owner decision #782): adventure mode, a text about
        the spectator view, and a place high above the map that looks down at its center (VIEW_PITCH) in the
        direction of the spawn of the converter, at most VIEW_DIST blocks from it and below the clouds (#1094). join: only for the players without the tag VIEWER (a player who
        joins later gets it once, and keeps the game mode that it selects after it, #910). Adventure mode has no
        flight before #910: slow falling (VIEW_FALL s) brings the player down with no fall damage."""
        if getattr(self, "view", None) is None:                    # once: each game second calls it
            c = self.n / 2
            land = [y for row in self.ground for y in row if y is not None] or [64]
            top, low = max(land), min(land)
            i, r = int(c), 16
            near = sorted(low if y is None else y                      # water: the lowest ground (all water is at
                          for row in self.ground[max(0, i - r):i + r] for y in row[max(0, i - r):i + r])  # elevation 0)
            mid = near[len(near) // 2] if near else top                # the ground at the center (a lake: #1150)
            pitch = math.radians(VIEW_PITCH)
            y = min(self.n // 3, VIEW_DIST * math.sin(pitch), CLOUDS - 4 - mid)     # the height above the center
            y = min(319, max(top + 8, round(mid + y)))                 # above the highest ground, below the build limit
            d = (y - mid) / math.tan(pitch)                            # the center is this far in front
            yaw = math.radians(aoe2mc.SPAWN_YAW)
            self.view = f"{c + d * math.sin(yaw):.1f} {y} {c - d * math.cos(yaw):.1f} facing {c:.1f} {mid} {c:.1f}"
        say = text("Double-tap Shift: spectator view (fly through blocks). Right click the hotbar items: replay control.")
        sel, run = (f"@a[tag=!{VIEWER}]", f"execute as @a[tag=!{VIEWER}] run ") if join else ("@a", "")
        me = "@s" if join else "@a"
        return [f"{run}gamemode adventure {me}", f"{run}effect give {me} minecraft:slow_falling {VIEW_FALL} 0 true",
                f"{run}tellraw {me} {json.dumps(say)}",
                f"{run}tp {me} {self.view}", f"tag {sel} add {VIEWER}"]

    @staticmethod
    def end_commands(end):
        """A title, the end time as subtitle and one sound when the replay is over (#872): the boss bar alone was not
        seen. The title stays 5 s (a resign title just before it shows only 3.5 s)."""
        m, s = divmod(int(end) // 1000, 60)
        return ["title @a times 10 100 20", "title @a subtitle " + json.dumps(text(f"Game time {m:02d}:{s:02d}")),
                "title @a title " + json.dumps(text("Replay ended")),
                "playsound minecraft:ui.toast.challenge_complete master @a ~ ~ ~ 1 1 1"]

    def summary_commands(self):
        """Two chat lines per player at the end of the replay, as the AoE2 achievements screen: the economy (#1065):
        trained villagers and the resources of the gather steps (estimated: the record has no resources); the military
        (#1066): trained military units, lost units (DELETE, and the fights of the plugin: census) and lost buildings."""
        out = ['tellraw @a {"text": "Summary (est.)", "bold": true}']
        for p in self.ranked(self.pop.keys() | self.villagers.keys() | self.gathered.keys() | self.army.keys()
                             | self.lost.keys() | self.razed.keys()):
            name, color = self.label(p)
            g = self.gathered.get(p, dict.fromkeys(START, 0))
            res = ", ".join(f"{r} {v}" for r, v in g.items())
            out.append("tellraw @a " + json.dumps([text(name, color), text(
                f": villagers trained {self.villagers.get(p, 0)}, gathered {res}")]))
            out.append("tellraw @a " + json.dumps([text(name, color), text(              # military (#1066)
                f": military units trained {self.army.get(p, 0)}, units lost {self.lost.get(p, 0)}, "
                f"buildings lost {self.razed.get(p, 0)}")]))
        return out + self.tech_commands() + self.society_commands()

    def tech_commands(self):
        """One chat line per player with the game time of each age-up (MM:SS, "-": not reached) and the number of
        researched technologies (#1067)."""
        out = []
        for p in self.ranked(self.pop.keys() | self.reached.keys() | self.researched.keys()):
            name, color = self.label(p)
            times = self.reached.get(p, {})
            ages = ", ".join(f"{pretty(a).removesuffix(' Age')} {mmss(times[a]) if a in times else '-'}"
                             for a in AGES)
            out.append("tellraw @a " + json.dumps([text(name, color), text(
                f": {ages}, technologies {self.researched.get(p, 0)}")]))
        return out

    def society_commands(self):
        """One chat line per player with the values of the AoE2 Society tab (#1086): castles and wonders built (each
        foundation once, as build()), tribute sent and received (all resources), and the highest villager count
        (est.: the start and the trained villagers, the census of the plugin counts the losses)."""
        built, sent, got, seen = {}, {}, {}, set()
        for e in self.data.get("timeline", []):
            p = e.get("player")
            name = e.get("name") or self.kinds.get(e.get("type"), ("?", ""))[1]
            if e["kind"] == "build" and name in SOCIETY and (p, tuple(e.get("tile", ()))) not in seen:
                seen.add((p, tuple(e.get("tile", ()))))
                built[p, name] = built.get((p, name), 0) + 1
            elif e["kind"] == "tribute" and e.get("to"):
                n = sum(e.get(r, 0) for r in START) or int(e.get("amount", 0))   # old records: one resource
                sent[p], got[e["to"]] = sent.get(p, 0) + n, got.get(e["to"], 0) + n
        out = []
        for p in self.ranked(self.pop.keys() | self.vhigh.keys() | sent.keys() | got.keys() | {q for q, _ in built}
                             - {None}):
            name, color = self.label(p)
            counts = "".join(f"{n.lower()}s {built.get((p, n), 0)}, " for n in SOCIETY)   # castles N, wonders N
            out.append("tellraw @a " + json.dumps([text(name, color), text(
                f": {counts}tribute sent {sent.get(p, 0)}, received {got.get(p, 0)}, villager high "
                f"{self.vhigh.get(p, 0)} (est.)")]))
        return out

    def timeline_commands(self, end):
        """A written book "Timeline" for each viewer at the end of the replay (#1068): per player its age-ups, its
        first military unit, its first castle and its resign, in time order, from the whole timeline (also the time
        of a jump) up to `end` (ms). Each player starts a page with a heading in its player color and its team (#1643); a
        long list goes on to the next page. One RCON
        command holds at most RCON_MAX bytes: the last lines go first."""
        import gather                                               # gather -> build -> replay: import it late
        lines, army, castle = {}, set(), set()
        for e in sorted(self.data.get("timeline", []) + self.spawns(), key=lambda e: e["time"]):
            p, line = e.get("player"), None
            if e["time"] > end or p is None:
                continue
            if e["kind"] == "age" and e.get("age"):
                line = pretty(e["age"])
            elif e["kind"] == "spawn" and p not in army and gather.military(e["name"]):
                army.add(p)
                line = f"1st military: {units.pretty(e['name'])}"
            elif e["kind"] == "build" and p not in castle and self.kinds.get(e.get("type"), ("?", ""))[1] == "CASTLE":
                castle.add(p)
                line = "Castle"
            elif e["kind"] == "resign":
                line = "Resigns"
            if line:
                lines.setdefault(p, []).append(f"{mmss(e['time'])} {line}")
        if not lines:
            return []
        while True:
            pages = []
            for p in sorted(lines):
                name, color = self.player(p)                            # the heading and an empty line
                team = self.team(p)
                name = f"■ {f'Team {team} · ' if team is not None else ''}{name}"
                rows, page = BOOK_ROWS - 1 - len(textwrap.wrap(name, BOOK_COLS)), ""
                head = {"text": name, "color": color if color != "white" else "black"}   # the sidebar color (#1643)
                for line in lines[p]:
                    n = len(textwrap.wrap(line, BOOK_COLS))
                    if n > rows:
                        pages.append({"text": "", "extra": [head, {"text": "\n" + page.rstrip("\n")}]} if head
                                     else {"text": page.strip("\n")})
                        rows, page, head = BOOK_ROWS, "", None
                    rows, page = rows - n, page + "\n" + line
                pages.append({"text": "", "extra": [head, {"text": "\n" + page.rstrip("\n")}]} if head
                             else {"text": page.strip("\n")})       # only the heading has a color, the lines are black
            book = {"title": "Timeline", "author": "aoe2mc", "pages": pages}
            cmd = "give @a minecraft:written_book[minecraft:written_book_content=" + \
                json.dumps(book, ensure_ascii=False, separators=(",", ":")) + "]"
            if len(cmd.encode()) <= RCON_MAX:
                return [cmd]
            longest = max(lines, key=lambda p: len(lines[p]))
            lines[longest].pop()

    def score_commands(self):
        """The sidebar commands for the population of each player that changed since the last call (#741). The score
        holder is "P<n>" (a holder name has no space); its display name is the player name in the player color, the
        age of the player (#805) and its estimated resources (#932). In a team game the score is a team key plus the
        population, so the sidebar shows each team together, and a fixed number format shows the population (#1189)."""
        out, top = [], max((self.team(p) or 0 for p in self.pop), default=0)
        if self.shown is None:
            self.shown, out = {}, [f'scoreboard objectives add {POP} dummy "Population"',
                                   f"scoreboard objectives setdisplay sidebar {POP}"]
        for p in sorted(self.pop):
            name, color = self.label(p)
            res = " ".join(f"{r[0].upper()} {max(0, v)}" for r, v in self.resources(p).items())
            if self.named.get(p) != (line := f"{name} · {self.ages.get(p, 'Dark')} · {res} (est.)"):
                out.append(f"scoreboard players display name P{p} {POP} {json.dumps(text(line, color))}")
                self.named[p] = line
            if self.shown.get(p) != self.pop[p]:
                self.shown[p] = self.pop[p]
                if (t := self.team(p)) is None:
                    out.append(f"scoreboard players set P{p} {POP} {self.pop[p]}")
                    continue
                out += [f"scoreboard players set P{p} {POP} {(top - t + 1) * TEAM_STEP + self.pop[p]}",
                        f"scoreboard players display numberformat P{p} {POP} fixed {json.dumps(text(str(self.pop[p])))}"]
        return out

    def census(self):
        """With the fights of the plugin (ai) a unit dies without a timeline event (#787): count the live units of
        each player with the entity selector of their tags (a dead entity does not match). The chunks are loaded
        (run.py --replay: forceload)."""
        self.flush()
        for p in self.pop:
            m = re.search(r"Count: (\d+)", self.game.command(f"execute if entity @e[tag={COUNTED},tag=aoe2mc.p{p}]"))
            n = int(m[1]) if m else 0
            if self.censused and n < self.pop[p]:                   # died in a fight (#1066); the first census sets
                self.lost[p] = self.lost.get(p, 0) + self.pop[p] - n    # the base: a start unit can have no entity
            self.pop[p] = n
            m = re.search(r"Count: (\d+)", self.game.command(
                f"execute if entity @e[tag={COUNTED},tag=aoe2mc.p{p},type=minecraft:villager]"))
            self.villager(p, 0, int(m[1]) if m else 0)               # the record has no deaths (#1086)
        self.censused = True

    def flush(self):
        """Send the commands of the queue in one batch (run.Game.batch): before each wait of run() and each read of
        the server, so a read sees the changes before it. Each RCON round trip waits for the main thread of the
        server (2 to 5 ms at a 45 ms tick): one send per step was a third of the loop of de-63.0 at speed 4 (#2761)."""
        if self.queue:
            cmds, self.queue = self.queue, None
            self.send(cmds)
            self.queue = []

    def look_around(self):
        """Read the places of the players with each census (#2761): with many villagers at speed 4 the gather looks
        were about half of all commands, and the replay loop fell behind its clock (de-63.0 after 16 minutes). A
        server answer that is no player list (a test without a server) keeps `eyes` None: each step shows."""
        self.flush()
        m = re.search(r"There are (\d+)", self.game.command("list") or "")
        out = self.game.command("execute as @a run data get entity @s Pos") if m and int(m[1]) else ""
        self.eyes = None if m is None else [tuple(map(float, p)) for p in re.findall(
            r"\[{0}d, {0}d, {0}d\]".format(r"(-?[\d.]+(?:E-?\d+)?)"), out or "")]

    def send(self, cmds):
        """Send cmds to the server; in run() on Paper add them to the queue (flush)."""
        if self.queue is not None:
            self.queue += cmds
            return
        t = time.perf_counter()
        if many := getattr(self.game, "batch", None):               # Paper: many commands per round trip (#2761)
            many(cmds)
        else:
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
            # a unit on its last or only leg is not in self.moving, but the plugin still walks it (#3024)
            walking = set(self.moving) | {i for i, v in self.units.items() if (getattr(v, "leg", None) or (0, 0, 0))[2] > g}
            self.send([ai.speed_command(v.uuid, v.name, self.T, 0 if paused else speed * PATH)
                       for v in map(self.units.get, sorted(walking)) if v and v.uuid])
        return g, r

    def jump(self, events, to, start=None):
        """Apply the events up to game time `to` (ms) at once (#687): buildings appear, deletes remove, trained units
        appear, and each unit that a MOVE or ORDER sent, or that walks now, stands at its target (tp, no walk). The
        chat, age and research texts of the skipped time do not show (the sidebar shows the age, #805). The estimate
        of the resources gets the gather of the skipped time (skipped()). Returns the commands."""
        out, moved, trail = [], set(), []
        self.explore()                                              # the sight before the skipped time (#1801)
        jobs = {i: v.job for i, v in self.units.items()}            # move() gives the looks: send the last ones
        since = {} if start is None else {i: start if i in self.working else self.walk_end(v, start)
                                          for i, v in self.units.items()
                                          if (i in self.moving or i in self.working) and v.tree is not None}

        def walks(ids):                                             # a place each tile on the paths (#1801)
            trail.extend(Seen(v.player, v.name, (x + 0.5, 0.0, z + 0.5)) for i in ids
                         if (v := self.units.get(i)) is not None and hasattr(v, "player") for x, z in v.path[::self.T])

        def order(e):
            for i in e["objects"]:                                  # a new order ends the work at the old resource
                self.skipped(i, since.pop(i, None), e["time"])
            inside = {u: r for r, us in self.garrisons.items() for u in us}
            out.extend(c for i in e["objects"] if i in inside for c in self.leave(i, inside[i]))   # out for good (#3023)
            out.extend(c for c in self.commands(e) if c.startswith("aoe stance "))   # the paths, targets, stances
            moved.update(e["objects"])
            walks(e["objects"])
            since.update((i, self.walk_end(v, e["time"])) for i in e["objects"]
                         if (v := self.units.get(i)) is not None and v.tree is not None)
            for i in set(e["objects"]) & self.entering.keys():      # it is at its building at once
                self.entering[i][2] = e["time"]

        def built(t):                                               # the builders of a farm farm it, of a camp
            for i, then in self.built(t):                           # gather next to it after the build (#1282)
                order(then) if then else self.look(self.units[i], "none")

        walks(self.moving)                                          # the walks of now
        for e in events:
            built(e["time"])
            if e["kind"] in aoe2mc.UNIT_USE | {"stop"} and e.get("objects"):
                for i, name in zip(e["objects"], e.get("names") or [None] * len(e["objects"])):
                    self.unit(i, name, e["player"])                 # a unit of a gather point gets its ID (#1227)
                since.update((self.adopted[j], since.pop(j)) for j in list(since) if j in self.adopted)
            if e["kind"] in ("move", "order", "garrison", "patrol", "attack_move", "follow", "guard", "autoscout") \
                    and e.get("objects"):                           # also the orders of #2550 to #2553, #2678 (#2734)
                order(e)
            elif e["kind"] in ("stance", "formation", "stop") and e.get("objects"):   # only their state (#2734)
                for i in e["objects"] if e["kind"] == "stop" else ():
                    self.skipped(i, since.pop(i, None), e["time"])
                out += self.commands(e)
            elif e["kind"] in ("build", "wall", "spawn", "delete", "ungarrison"):
                builders = e.get("objects", ()) if e["kind"] in ("build", "wall") else ()
                for i in builders:                                  # a builder ends the work at its resource
                    self.skipped(i, since.pop(i, None), e["time"])
                rallied = self.rallied
                out += self.enter(e["time"]) + self.commands(e)
                if self.rallied > rallied and (v := self.units[-self.rallied]).tree is not None:   # (#1227)
                    since[-self.rallied] = self.walk_end(v, e["time"])
            elif e["kind"] == "back_to_work" and e.get("objects"):  # the units work again from now (#1179)
                out += self.enter(e["time"])
                cmds, ids = self.back(e)
                out += cmds
                moved.update(ids)
                since.update((i, self.walk_end(self.units[i], e["time"])) for i in ids)
            elif e["kind"] == "gather_point":
                self.commands(e)
            elif e["kind"] == "age" and e.get("age"):                 # the sidebar shows it, no title
                self.age(e)
            elif e["kind"] == "research" and e.get("technology"):     # no text, but the summary counts it
                self.learn(e)
        built(to)
        out += self.enter(to) + self.expire(to)
        for tile in list(self.prey):                                # the hunters were there in the skipped time
            out += self.kill(tile)
        for i, t in since.items():                                  # a unit that still works: steps() catch up
            if i not in self.working or (i in moved and not self.ai):
                self.skipped(i, t, to)
        inside = {u for us in self.garrisons.values() for u in us}
        for i in sorted(moved | self.moving.keys()):
            if (v := self.units.get(i)) is None or i in inside:
                continue
            x, z = v.path[-1] if v.path else v.cell
            y = self.map.sea(x, z) if ship(v.name) else self.map.y(x, z)    # water has no ground height (#1030)
            v.pos, v.path = (x + 0.5, float(v.pos[1] if y is None else y), z + 0.5), []
            self.moving.pop(i, None)
            out.append("tp {} {} {} {}".format(v.uuid, *v.pos))
            if self.ai:                                             # ends the walk order of the plugin at once
                out.append("aoe moveto {} {} {} {}".format(v.uuid, *v.pos))
                if i not in self.working:                           # a long walk ends here: it gathers (#3022)
                    self.start(i, v, to)
                    self.rest(i, to)
            else:                                                   # at its resource: it gathers (#887)
                self.start(i, v, to)
        for i in sorted(self.patrols.keys() | self.scouts.keys()):  # they walk on after the jump (#2734)
            if i in self.units and i not in self.moving and i not in inside:
                out += self.patrol_on(i, to) if i in self.patrols else self.scout_on(i, to)
        self.explore(trail)                                         # the sight on the walks and at the targets (#1801)
        return out + [self.gather.profession(v.uuid, v.job) for i, v in self.units.items() if v.job != jobs.get(i)]

    def walk_end(self, v, t):
        """The game time (ms) at which unit v ends its walk to the last cell of its path when it leaves at t."""
        speed = next((s for k, s in SPEEDS.items() if v.name.startswith(k)), 1.0) * self.T    # blocks per second
        return t + (1000 * math.dist(v.cell, v.path[-1]) / speed if v.path else 0)

    def skipped(self, i, t0, t1):
        """Add to the estimate the resources that unit i gathers at its resource from game time t0 to t1 (ms) in a
        jump: the jump runs no gather steps, so without it the costs of the skipped time take the estimate below 0
        (#1056). The AoE2 rate for the whole skipped time, with no cap of the one resource: in play the villager walks
        to the next resource when its resource is empty (#1147). The resource itself keeps its amount (the world shows
        no gather)."""
        v = self.units.get(i)
        if t0 is None or t1 <= t0 or v is None or not (v.name.startswith("VILLAGER") or fisher(v.name)) \
                or v.tree is None:
            return
        res = self.map.resource(v.tree)
        if res not in self.gather.AOE2_WORK:
            return
        m = self.map
        left = (m.farms if v.tree in m.farms else m.carcasses if v.tree in m.carcasses else m.fish if v.tree in m.fish
                else m.bushes if res == "food" else m.trees if res == "wood" else m.mines.get(res, {})).get(v.tree, 0)
        n = int(self.rate(v) * (t1 - t0) / 1000) if left > 0 else 0         # left 0: no resource, `res` is not sure
        self.resources(v.player)[res] += n
        self.gathered.setdefault(v.player, dict.fromkeys(START, 0))[res] += n     # the summary (#1097)

    def run(self, *args, **kw):
        """Play the timeline (`play`). On Paper the commands wait in `queue` and go out in batches (flush, #2761)."""
        self.queue = [] if getattr(self.game, "batch", None) else None
        try:
            return self.play(*args, **kw)
        finally:
            self.flush()
            self.queue = None

    def play(self, speed=1.0, start=0, clock=time.monotonic, sleep=time.sleep, log=print, bar=False, poll=None,
             finish=False, to=None, paused=False, rewind=False):
        """Play the timeline from game time `start` (ms) at `speed` times the game speed; `bar`: show the game time
        in a boss bar (`clock_commands`). Returns the stats:
        commands, events, the seconds of sending, the largest lag behind the timeline (s), commands per second
        (rate) and the commands per second that the timeline needs on average (need).
        poll(control) may change `self.control` ("speed", "paused") while the replay runs: run calls it before
        each event and each POLL seconds while it waits (#685). "jump" (game time, ms) skips forward to that time
        (`jump`, #687); a time before the game time now changes nothing, except with `rewind`: then run stops and
        the stats have "rewind" (the time), "speed" and "paused" (#979: the replay keeps no earlier states, `live`
        starts a fresh replay). "time" is the game time now (ms) for poll. `to`: jump to this time at the start;
        `paused`: start in a pause. The replay ends at the time of its last event, as the record (#978); `finish`:
        play the walks and the trainings to their end (tests of one walk or one queue)."""
        last = math.inf if finish else max((e["time"] for e in self.data.get("timeline", [])), default=start)
        events = sorted((e for e in self.data.get("timeline", []) + self.spawns() if start <= e["time"] <= last),
                        key=lambda e: e["time"])                     # the record ends at `last`: no spawn after it
        g0, r0, lag, n, k = start, clock(), 0.0, 0, 0                 # game time g0 (ms) at real time r0
        self.speed, self.paused = speed, paused
        self.control = {"speed": speed, "paused": paused, "view": self.pov,     # the view: replay_input VIEW (#1303)
                        "players": {p: self.player(p) for p in sorted(int(q) for q in self.data["players"]) if p}} | \
            ({"jump": to} if to is not None else {})
        self.control["fights"] = fights(self.data.get("timeline", []), owners(self.data.get("objects", []),
                                                                             self.data.get("timeline", [])))
        end, shown, counted = events[-1]["time"] if events else start, None, -math.inf
        send = self.send if bar else lambda cmds: None
        send([f'bossbar add {BAR} ""', f"bossbar set {BAR} color white",
                   f"bossbar set {BAR} max {max(1, int(end) // 1000)}"] +
             ([f"tag {u} add {COUNTED}" for u in self.counted] + ["aoe deathmarks on", "aoe minimap on", f"aoe minimap frame {FRAME * self.T}"]) * self.ai +
             # the death marks (#846) and the live units on the map item (#1237); the plugin paints the bare ground
             # over the start objects of the base image, so the start buildings get their squares (#1940)
             self.minimap_buildings(set(), set()) * (self.pov is None) +
             self.overview())
        if to is None:                                              # not again after a jump back (#2949)
            send(replay_input.fight_lines(self.control["fights"], self.control["players"]))
        census = self.census if bar and self.ai else lambda: None
        look = self.look_around if bar and self.ai else lambda: None          # as census: a server of run.py --replay
        while k < len(events) or self.moving or self.builds or self.charging or self.idle:
            step = min([*self.moving.values(), *self.working.values(), *self.effects.values(),   # walk, gather, text
                        *[self.calm_at(i) for i in self.charging if i not in self.moving],         # an attack-move ends
                        *[self.burst] * bool(self.flares),                                        # a flare column
                        *[self.trail] * bool(self.follows),                                       # a follow (#2551)
                        *(due for due, _ in self.builds.values()),                                # a build ends
                        *(due for due, _ in self.idle.values()),                                  # settle() (#2633)
                        *(at for _, _, at in self.entering.values() if at is not None),            # go in
                        *[c for i in self.moving if self.ai and (c := getattr(self.units[i], "check", None))]],
                       default=math.inf)                            # the recheck of a long leg (#1293)
            if k == len(events) and step > end and not finish:        # the record ends at its last event: do not wait for walks (#978)
                break
            e = events[k] if k < len(events) and events[k]["time"] <= step else None
            k += e is not None
            now = e["time"] if e else step
            to = None
            while True:
                self.flush()                                        # the commands so far go out before the wait
                if poll:
                    self.control["time"] = g0 if self.paused else g0 + (clock() - r0) * 1000 * self.speed
                    poll(self.control)
                    g0, r0 = self.retime(g0, r0, clock())
                    if self.control.get("view") != self.pov:
                        self.pov = self.control.get("view")
                        self.send(self.fog())
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
                if rewind and to < (g0 if self.paused else g0 + (clock() - r0) * 1000 * self.speed):
                    say = text("The server restarts for the jump back: join it again.", "yellow")
                    send(self.clock_commands(to, end, self.speed, jump=True) + [f"tellraw @a {json.dumps(say)}"])
                    return {"rewind": to, "speed": self.speed, "paused": self.paused, "view": self.pov, "events": n,
                            "commands": self.sent, "busy": round(self.busy, 2), "lag": round(lag, 2)}
                if to > (at := g0 if self.paused else g0 + (clock() - r0) * 1000 * self.speed):
                    skip = [x for x in events[k:] if x["time"] <= to]
                    k += len(skip)
                    send(self.clock_commands(to, end, self.speed, jump=True))    # the player sees why it waits
                    self.send(self.jump(skip, to, at))
                    if self.moving or self.working:                 # the gather steps of the skipped time at once,
                        self.send(self.steps(to))                   # and no step before `to`: an older time on the
                        self.moving = {i: max(t, to) for i, t in self.moving.items()}     # bar and fast catch-up
                        self.working = {i: max(t, to) for i, t in self.working.items()}   # walks after it (#1125)
                    g0, r0 = to, clock()
                    shown = int(to) // 1000
                    send(self.clock_commands(to, end, self.speed) + self.score_commands())
                continue
            lag = max(lag, clock() - r0 - (now - g0) / 1000 / self.speed)
            if int(now) // 1000 != shown:                              # at most once per game second
                shown = int(now) // 1000
                if clock() - counted >= CENSUS:
                    census()
                    look()
                    counted = clock()
                send(self.clock_commands(now, end, self.speed) + self.score_commands() + self.overview(join=True))
                self.send(self.fog())
            if e is None:                                           # behind its clock: all the steps up to the
                late = g0 if self.paused else g0 + (clock() - r0) * 1000 * self.speed    # game time now in one
                nxt = events[k]["time"] if k < len(events) else math.inf     # send, before the next event (#2761)
                self.send(self.steps(max(now, min(late, nxt - 1))))
                continue
            cmds = self.commands(e) + self.spectate(e)
            if cmds:
                n += 1
                self.send(cmds)
                if log and e["kind"] in ("build", "wall", "age", "resign"):
                    m, s = divmod(e["time"] // 1000, 60)
                    log(f"{m:02d}:{s:02d} {e['kind']} {e.get('name') or e.get('age') or ''} "
                        f"player {e.get('player')}: {len(cmds)} commands")
        census()
        self.send(self.expire(math.inf))
        send(self.clock_commands(end, end, speed, done=True) + self.score_commands() + self.end_commands(end) +
             self.summary_commands() + self.timeline_commands(end))
        span = (events[-1]["time"] - start) / 1000 / speed if events else 0                 # at the start speed
        return {"events": n, "commands": self.sent, "busy": round(self.busy, 2), "lag": round(lag, 2),
                "rate": round(self.sent / self.busy) if self.busy else 0, "need": round(self.sent / span) if span else 0}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Information of a recorded game for the live replay.")
    ap.add_argument("record", help="the .aoe2record file")
    ap.add_argument("--fights", action="store_true", help="print the large fights of the record (#2948)")
    a = ap.parse_args()
    if a.fights:
        timeline = aoe2mc.read_timeline(a.record) or []
        for f in fights(timeline, owners(aoe2mc.read_record(a.record)[5], timeline)):
            print(f"{mmss(f['start'])}-{mmss(f['end'])} tile ({f['tile'][0]:g}, {f['tile'][1]:g}) "
                  f"players {', '.join(map(str, f['players']))} units {f['units']}")
