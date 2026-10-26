"""
Train villagers at the town center in the game program (#612, part of #396). A right click with the command stick on
an own town center queues a villager and takes its cost from the stock, as in AoE2. A town center trains one unit at
a time, in the AoE2 train time; then the villager appears on a free cell in front of it, with the NBT of the converter
(units.make_entity) and the AoE2 hit points (combat.stats_command), and a click can select it and send it to gather.
gather.Gather.click calls queue(), gather.Gather.step calls tick().
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import units  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402

COSTS = {"VILLAGER_MALE": {"food": 50}}                            # as in AoE2
TRAIN_TIMES = {"VILLAGER_MALE": 25}                                # AoE2 seconds
QUEUE = 15                                                         # units in the queue of one building, as in AoE2


def homes(g):
    """The block footprints (x0, x1, z0, z1) of the complete own town centers: the start ones and the built ones."""
    out = [(x0, x1, z0, z1) for o in g.data["objects"] if o["kind"] == "building" and o["name"] == "TOWN_CENTER"
           and o["player"] == g.player for x0, z0, x1, z1 in [o["footprint"]]]
    return out + [tuple(s["footprint"]) for s in g.sites if s["name"] == "TOWN_CENTER" and s.get("done")]


def queue(g, player, cell, name="VILLAGER_MALE"):
    """Queue unit name at the own town center that has the block cell (x, z) in its footprint, and take its cost.
    Returns the footprint of the town center, or None (no town center there, a full queue, not enough resources)."""
    rect = next((r for r in homes(g) if cell and r[0] <= cell[0] < r[1] and r[2] <= cell[1] < r[3]), None)
    if rect is None:
        return None
    q = g.queues.setdefault(rect, [])
    if len(q) >= QUEUE:
        build.say(g, player, f"The queue is full ({QUEUE} units).")
        return None
    cost = COSTS[name]
    if any(g.stock[r] < v for r, v in cost.items()):
        build.say(g, player, f"Not enough resources: a {build.pretty(name).lower()} costs "
                             + ", ".join(f"{v} {r}" for r, v in cost.items()) + ".")
        return None
    for r, v in cost.items():
        g.stock[r] -= v
        g.command(f"scoreboard players remove {r.capitalize()} aoe_res {v}")
    q.append({"name": name, "progress": 0.0})
    return rect


def tick(g, work):
    """Add work (AoE2 seconds) to the first unit of each queue; a unit that is complete appears. Returns the new
    gather.Villager objects."""
    out = []
    for rect, q in g.queues.items():
        if q:
            q[0]["progress"] += work / TRAIN_TIMES[q[0]["name"]]
            if q[0]["progress"] >= 1:
                out += [v for v in [spawn(g, rect, q.pop(0)["name"])] if v]
    return out


def spawn(g, rect, name):
    """Summon unit name on a free cell in front of the building rect (south side first, the middle first; the units
    take the cells one after the other) and add it to the villagers of g. Returns the gather.Villager or None."""
    x0, x1, z0, z1 = rect
    cells = sorted(g.map.around({(x, z) for x in range(x0, x1) for z in range(z0, z1)}),
                   key=lambda c: (abs(c[1] - z1), abs(2 * c[0] + 1 - x0 - x1), c))
    if not cells:
        return None
    k = g.trained[rect] = g.trained.get(rect, -1) + 1
    x, z = cells[k % len(cells)]
    pos = (x + 0.5, float(g.map.y(x, z)), z + 0.5)
    o = dict(name=name, player=g.player, rotation=math.pi / 2)        # it faces south
    players = {int(p): v for p, v in g.data.get("players", {}).items()}
    nbt = units.make_entity(o, players, pos, np.random.default_rng())  # a new random UUID
    if nbt is None:
        return None
    kind = str(nbt.pop("id"))
    del nbt["Pos"]
    uuid = units.uuid_str(nbt["UUID"])
    g.command(f"summon {kind} {pos[0]} {pos[1]} {pos[2]} {nbt.snbt()}")
    import combat, gather                                          # both import gather, gather imports this module
    g.command(combat.stats_command(uuid, name))
    v = g.villagers[uuid] = gather.Villager(uuid, pos)
    g.units.append({"kind": "unit", "name": name, "player": g.player, "uuid": uuid, "tile": [x / g.map.T, z / g.map.T]})
    return v
