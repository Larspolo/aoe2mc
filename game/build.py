"""
Construction sites in the game program (#417, part of #394). A player chooses a building with `/trigger aoe_build
set N` (players without operator rights can run /trigger), then right clicks the ground with the command stick.
When the footprint is free and the stock pays the cost, a foundation appears: a ring of wool in the player color.
The ring stays until the building is complete, so a player sees which buildings are not finished.
The footprint is blocked for paths. gather.Gather.click calls place().
A right click on a foundation sends the selected villagers there to build it (#418): the blocks of the design
(replay.Replay.building) appear from the bottom up, in the AoE2 build time. gather.Gather.step calls rise().
A complete building works (#419): a camp, mill or town center is a drop site, a farm can be farmed.
A right click on a selected villager opens the build menu (#621): a chest menu (menu.py) with one item per building.
A click chooses the building as /trigger does and closes the menu, so the next right click places it.
Ages (#674): a Feudal Age building or unit (AGE) is locked until the player researches the Feudal Age (train.py):
its item is gray, says "Needs the Feudal Age", and a click does nothing.
Ghost (#794): while a player has a building chosen, a ghost of its design follows the ground that he looks at (block
displays of the Paper plugin, Ghost.java): green where it can stand, red where not. ghosts() sends the shape once.
"""
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aoe2mc import VERSION_NAME  # noqa: E402
from buildings import footprint  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import menu as chest  # noqa: E402  (menu() below is the chat text)
from replay import Replay  # noqa: E402

COSTS = {"HOUSE": {"wood": 25}, "LUMBER_CAMP": {"wood": 100}, "MINING_CAMP": {"wood": 100},   # as in AoE2
         "MILL": {"wood": 100}, "FARM": {"wood": 60}, "BARRACKS": {"wood": 175},
         "BLACKSMITH": {"wood": 150},
         "ARCHERY_RANGE": {"wood": 175}, "STABLE": {"wood": 175}, "TOWN_CENTER": {"wood": 275, "stone": 100}}
BUILD_TIMES = {"HOUSE": 25, "LUMBER_CAMP": 35, "MINING_CAMP": 35, "MILL": 35, "FARM": 15,   # AoE2 seconds,
               "BARRACKS": 50, "ARCHERY_RANGE": 50, "STABLE": 50, "TOWN_CENTER": 150,                              # one builder
               "BLACKSMITH": 40}
MENU = list(COSTS)                                                 # trigger value N -> MENU[N - 1]
OBJECTIVE = "aoe_build"
ICONS = {"HOUSE": "spruce_stairs", "LUMBER_CAMP": "oak_log", "MINING_CAMP": "raw_gold_block",   # a block of the
         "MILL": "white_wool", "FARM": "wheat", "BARRACKS": "stone_brick_wall", "ARCHERY_RANGE": "target",
         "BLACKSMITH": "anvil", "STABLE": "hay_block",
         "TOWN_CENTER": "cobblestone"}                                  # design
AGE_TECHS = ("FEUDAL_AGE",)                                        # the technologies of the ages, in order
AGE = dict.fromkeys(("ARCHERY_RANGE", "STABLE", "BLACKSMITH", "MARKET", "WATCH_TOWER",   # the AoE2 age of each
                     "ARCHER", "SKIRMISHER", "SPEARMAN", "SCOUT_CAVALRY"), 1)            # building and unit (0: Dark)
GHOST = 400                                                        # block displays of one ghost: a coarser shape above
LOCKED = "gray_dye"                                                # the item of a locked building or unit


def pretty(name):
    return name.replace("_", " ").title()


def setup(g):
    g.command(f"scoreboard objectives add {OBJECTIVE} trigger")
    g.ghosts, g.shapes = {}, {}                                        # player -> [building, color]; building -> shape


def tick(g):
    """Players who joined since the last tick get the menu; all players may use the trigger (it locks after use)."""
    g.command(f"execute as @a unless score @s {OBJECTIVE} matches 0.. run tellraw @s {menu()}")
    g.command(f"scoreboard players add @a {OBJECTIVE} 0")
    g.command(f"scoreboard players enable @a {OBJECTIVE}")
    if getattr(g, "paper", False):
        ghosts(g)


def shape(blocks, limit=GHOST):
    """The ghost of a design: its outer blocks {(x, y, z): state} (a block with a free side), and the scale. Above
    limit blocks, each cell of k × k × k blocks becomes one block of size k (k = 2, 4 ...)."""
    k, cells = 1, dict(blocks)
    while True:
        out = {p: v for p, v in cells.items()
               if any((p[0] + a, p[1] + b, p[2] + c) not in cells for a, b, c in
                      ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)))}
        if len(out) <= limit:
            return out, k
        k *= 2
        cells = {}
        for (x, y, z), v in sorted(blocks.items()):
            cells.setdefault((x // k, y // k, z // k), v)


def ghost_commands(g, player, name, rect):
    """The plugin commands that give player the ghost of building name: its design at rect (x0, x1, z0, z1) without
    the cleared air and the foundation, relative to the floor of the north-west corner. At most 1446 bytes per RCON
    command: the shape goes in parts. An empty list where the design does not stand (outside the map, on water)."""
    if name not in g.shapes:
        cmds = Replay(g, g.data, getattr(g.game, "version", VERSION_NAME)).building(
            name, g.player, rect[0] / g.map.T + footprint(name) / 2, rect[2] / g.map.T + footprint(name) / 2)
        blocks, base = {}, None
        for c in cmds:
            b, state = box(c) or (None, None)
            if b is None or c.endswith(" keep"):                       # the foundation under the floor
                continue
            if base is None:                                           # the first fill clears the footprint
                base = b[1]
            if state.split("[")[0] in ("air", "minecraft:air", "barrier", "minecraft:barrier"):
                continue
            for x in range(b[0], b[3] + 1):
                blocks[x - rect[0], b[1] - base, b[2] - rect[2]] = state.removeprefix("minecraft:")
        if not blocks:
            return []
        g.shapes[name] = shape(blocks)
    parts, k = g.shapes[name]
    out, line = [f"aoe ghost-clear {player}"], ""
    for (x, y, z), state in sorted(parts.items()):
        t = f" {x}/{y}/{z}/{state}"
        if len(line) + len(t) > 1300:
            out.append(f"aoe ghost-shape {player} {k}{line}")
            line = ""
        line += t
    return out + [f"aoe ghost-shape {player} {k}{line}"] * bool(line) + [f"aoe ghost {player} {g.map.T} {footprint(name)}"]


def ghosts(g):
    """Each tick: the players who chose a building see its ghost (#794), green over a free footprint and red over a
    blocked one, as place() tests it; the ghost goes away when the choice ends (placed, cancelled)."""
    import gather                                                      # gather imports build
    who = {}
    if "passed" in g.command(f"execute if entity @a[scores={{{OBJECTIVE}=1..}}]"):
        for p in (n.strip() for n in g.command("list").split(":", 1)[-1].split(",")):
            if p and (name := chosen(g, p)) and not locked(g, name):
                who[p] = name
    for p in [p for p in g.ghosts if p not in who]:
        g.command(f"aoe ghost-clear {p}")
        del g.ghosts[p]
    for p, name in who.items():
        pos = g.pos(p)
        rot = [float(v) for v in re.findall(gather.NUMBER, g.command(f"data get entity {p} Rotation").rsplit(":", 1)[-1])]
        cell = pos and len(rot) == 2 and g.map.pick_ground((pos[0], pos[1] + 1.62, pos[2]), gather.direction(*rot))
        if not cell:
            continue
        rect = area(g, name, cell)
        if g.ghosts.get(p, [None])[0] != name:
            if not (cmds := ghost_commands(g, p, name, rect)):
                continue
            for c in cmds:
                g.command(c)
            g.ghosts[p] = [name, None]
        color = "green" if free(g, rect) else "red"
        if g.ghosts[p][1] != color:
            g.command(f"aoe ghost-color {p} {color}")
            g.ghosts[p][1] = color


def ages(g):
    """The number of ages that the player researched: 0 in the Dark Age."""
    return sum(t in getattr(g, "techs", ()) for t in AGE_TECHS)


def locked(g, name):
    """The text "Needs the ... Age" when the player is not yet in the AoE2 age of building or unit name, else None."""
    if g is not None and AGE.get(name, 0) > ages(g):
        return "Needs the Feudal Age"


def menu():
    lines = [f"/trigger {OBJECTIVE} set {i}: {pretty(n)} ({', '.join(f'{v} {r}' for r, v in COSTS[n].items())})"
             for i, n in enumerate(MENU, 1)]
    return json.dumps({"text": "Build: " + "\n".join(lines), "color": "gray"})


def items(g=None):
    """The items of the build menu: (slot, icon, name, lore) with the cost and the build time. With g: a building of
    a later age is gray and says which age it needs."""
    return [(i, LOCKED if locked(g, n) else ICONS[n], pretty(n),
             "\n".join([", ".join(f"{v} {r}" for r, v in COSTS[n].items()), f"{BUILD_TIMES[n]} s"]
                       + [locked(g, n)] * bool(locked(g, n)))) for i, n in enumerate(MENU)]


def open_menu(g, player):
    """Show the build menu. A click sets the trigger score, as /trigger aoe_build set N does, and closes the menu."""
    def choose(p, slot, shift):                                        # shift: one building all the same
        if slot < len(MENU) and not locked(g, MENU[slot]):
            g.command(f"scoreboard players set {p} {OBJECTIVE} {slot + 1}")
            chest.close(g, p)
    return chest.show(g, player, "Build", items(g), choose)


def chosen(g, player):
    """The building that the player chose with /trigger, or None."""
    out = g.command(f"scoreboard players get {player} {OBJECTIVE}")
    n = int(out.split(" has ")[1].split()[0]) if " has " in out else 0
    return MENU[n - 1] if 0 < n <= len(MENU) else None


def say(g, player, text):
    g.command(f"tellraw {player} " + json.dumps({"text": text, "color": "red"}))


def area(g, name, cell):
    """The block footprint (x0, x1, z0, z1) of building name with the block cell under the cursor in its middle tile."""
    T, s = g.map.T, footprint(name)
    tx, tz = cell[0] // T - s // 2, cell[1] // T - s // 2
    return tx * T, (tx + s) * T, tz * T, (tz + s) * T


def free(g, rect):
    x0, x1, z0, z1 = rect
    return all(g.map.free(x, z) and (x, z) not in g.map.farm_at for x in range(x0, x1) for z in range(z0, z1))


def place(g, player, name, eye, d):
    """Place a foundation of name at the ground that the player looks at. Returns the site or None."""
    if need := locked(g, name):                                        # a /trigger choice of a later age
        say(g, player, f"{pretty(name)}: {need}.")
        return None
    cell = g.map.pick_ground(eye, d)
    if cell is None:
        return None
    rect = area(g, name, cell)
    if not free(g, rect):
        say(g, player, f"No space for the {pretty(name).lower()} here.")
        return None
    cost = COSTS[name]
    if any(g.stock[r] < v for r, v in cost.items()):
        say(g, player, f"Not enough resources: a {pretty(name).lower()} costs "
                       + ", ".join(f"{v} {r}" for r, v in cost.items()) + ".")
        return None
    for r, v in cost.items():
        g.stock[r] -= v
        g.command(f"scoreboard players remove {r.capitalize()} aoe_res {v}")
    x0, x1, z0, z1 = rect
    color = g.players.get(str(g.player), {}).get("color", "light_gray")
    ring = [(x, g.map.y(x, z), z) for x in range(x0, x1) for z in range(z0, z1) if x in (x0, x1 - 1) or z in (z0, z1 - 1)]
    for c in ring:
        g.command("setblock {} {} {} ".format(*c) + f"minecraft:{color}_wool")
    g.map.blocked |= {(x, z) for x in range(x0, x1) for z in range(z0, z1)}
    s = footprint(name)                                                # the design, bottom up (one command each)
    cmds = Replay(g, g.data, getattr(g.game, "version", VERSION_NAME)).building(name, g.player, x0 / g.map.T + s / 2, z0 / g.map.T + s / 2)
    site = {"name": name, "player": g.player, "footprint": rect, "commands": cmds, "sent": 0, "progress": 0.0,
            "ring": dict.fromkeys(ring, f"minecraft:{color}_wool"), "under": {}}   # under: the design blocks on the ring
    g.sites.append(site)
    g.command(f"scoreboard players set {player} {OBJECTIVE} 0")
    return site


def pick(g, eye, d):
    """The unfinished construction site on the ground that the player looks at, or None."""
    cell = g.map.pick_ground(eye, d)
    return next((s for s in g.sites if s["progress"] < 1 and cell and s["footprint"][0] <= cell[0] < s["footprint"][1]
                 and s["footprint"][2] <= cell[1] < s["footprint"][3]), None)


def box(cmd):
    """The box (x0, y0, z0, x1, y1, z1) and the block state of a /setblock or /fill command, or None."""
    t = cmd.split()
    if t[0] == "setblock":
        return (*map(int, t[1:4]), *map(int, t[1:4])), t[4]
    if t[0] == "fill":
        return tuple(map(int, t[1:7])), t[7]
    return None


def rise(g, site, work):
    """Add work (game seconds of one builder) to the site and send the commands of the blocks that are due.
    The wool ring stays on top of the design until the building is complete. Returns True when it is complete."""
    site["progress"] = min(1.0, site["progress"] + work / BUILD_TIMES[site["name"]])
    cmds, ring = site["commands"], site.get("ring", {})
    k = len(cmds) if site["progress"] >= 1 else math.floor(site["progress"] * len(cmds))
    hit = set()
    for c in cmds[site["sent"]:k]:
        g.command(c)
        if ring and (b := box(c)):                                     # remember the design block, keep the wool
            (x0, y0, z0, x1, y1, z1), state = b
            for p in ring:
                if x0 <= p[0] <= x1 and y0 <= p[1] <= y1 and z0 <= p[2] <= z1:
                    site["under"][p] = state
                    hit.add(p)
    site["sent"] = max(site["sent"], k)
    if site["progress"] < 1:
        for p in sorted(hit):
            g.command("setblock {} {} {} ".format(*p) + ring[p])
    if site["progress"] >= 1 and not site.get("done"):                 # complete: the building works (#419)
        site["done"] = True
        for p in [p for p in ring if p not in hit]:                    # the ring goes: the design or air
            g.command("setblock {} {} {} ".format(*p) + site["under"].get(p, "minecraft:air"))
        x0, x1, z0, z1 = site["footprint"]
        s, T = footprint(site["name"]), g.map.T
        if "FARM" in site["name"]:                                     # free ground again: the farmer stands on it
            g.map.blocked -= {(x, z) for x in range(x0, x1) for z in range(z0, z1)}
        g.map.building(site["name"], site["footprint"], (x0 // T + s // 2, z0 // T + s // 2), site["player"] == g.player)
    return site["progress"] >= 1
