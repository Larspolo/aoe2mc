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
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aoe2mc import VERSION_NAME  # noqa: E402
from buildings import footprint  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import menu as chest  # noqa: E402  (menu() below is the chat text)
from replay import Replay  # noqa: E402

COSTS = {"HOUSE": {"wood": 25}, "LUMBER_CAMP": {"wood": 100}, "MINING_CAMP": {"wood": 100},   # as in AoE2
         "MILL": {"wood": 100}, "FARM": {"wood": 60}, "BARRACKS": {"wood": 175},
         "TOWN_CENTER": {"wood": 275, "stone": 100}}
BUILD_TIMES = {"HOUSE": 25, "LUMBER_CAMP": 35, "MINING_CAMP": 35, "MILL": 35, "FARM": 15,   # AoE2 seconds,
               "BARRACKS": 50, "TOWN_CENTER": 150}                                # one builder
MENU = list(COSTS)                                                 # trigger value N -> MENU[N - 1]
OBJECTIVE = "aoe_build"
ICONS = {"HOUSE": "spruce_stairs", "LUMBER_CAMP": "oak_log", "MINING_CAMP": "raw_gold_block",   # a block of the
         "MILL": "white_wool", "FARM": "wheat", "BARRACKS": "stone_brick_wall", "TOWN_CENTER": "cobblestone"}  # design


def pretty(name):
    return name.replace("_", " ").title()


def setup(g):
    g.command(f"scoreboard objectives add {OBJECTIVE} trigger")


def tick(g):
    """Players who joined since the last tick get the menu; all players may use the trigger (it locks after use)."""
    g.command(f"execute as @a unless score @s {OBJECTIVE} matches 0.. run tellraw @s {menu()}")
    g.command(f"scoreboard players add @a {OBJECTIVE} 0")
    g.command(f"scoreboard players enable @a {OBJECTIVE}")


def menu():
    lines = [f"/trigger {OBJECTIVE} set {i}: {pretty(n)} ({', '.join(f'{v} {r}' for r, v in COSTS[n].items())})"
             for i, n in enumerate(MENU, 1)]
    return json.dumps({"text": "Build: " + "\n".join(lines), "color": "gray"})


def items():
    """The items of the build menu: (slot, icon, name, lore) with the cost and the build time."""
    return [(i, ICONS[n], pretty(n), "\n".join([", ".join(f"{v} {r}" for r, v in COSTS[n].items()),
                                                 f"{BUILD_TIMES[n]} s"])) for i, n in enumerate(MENU)]


def open_menu(g, player):
    """Show the build menu. A click sets the trigger score, as /trigger aoe_build set N does, and closes the menu."""
    def choose(p, slot):
        if slot < len(MENU):
            g.command(f"scoreboard players set {p} {OBJECTIVE} {slot + 1}")
            chest.close(g, p)
    return chest.show(g, player, "Build", items(), choose)


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
