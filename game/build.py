"""
Construction sites in the game program (#417, part of #394). A player chooses a building with `/trigger aoe_build
set N` (players without operator rights can run /trigger), then right clicks the ground with the command stick.
When the footprint is free and the stock pays the cost, a foundation appears: a ring of wool in the player color.
The footprint is blocked for paths. gather.Gather.click calls place().
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from buildings import footprint  # noqa: E402

COSTS = {"HOUSE": {"wood": 25}, "LUMBER_CAMP": {"wood": 100}, "MINING_CAMP": {"wood": 100},   # as in AoE2
         "MILL": {"wood": 100}, "FARM": {"wood": 60}, "BARRACKS": {"wood": 175},
         "TOWN_CENTER": {"wood": 275, "stone": 100}}
MENU = list(COSTS)                                                 # trigger value N -> MENU[N - 1]
OBJECTIVE = "aoe_build"


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
    for x in range(x0, x1):
        for z in range(z0, z1):
            if x in (x0, x1 - 1) or z in (z0, z1 - 1):
                g.command(f"setblock {x} {g.map.y(x, z)} {z} minecraft:{color}_wool")
    g.map.blocked |= {(x, z) for x in range(x0, x1) for z in range(z0, z1)}
    site = {"name": name, "player": g.player, "footprint": rect}
    g.sites.append(site)
    g.command(f"scoreboard players set {player} {OBJECTIVE} 0")
    return site
