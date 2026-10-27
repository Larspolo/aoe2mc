"""
The monks of the game program (epic #1242). An idle own monk heals the own injured units near it, as in AoE2 DE (#1244):
150 hit points per AoE2 minute (RATE), in a range of 4 tiles (AoE2 wiki, "Monk (Age of Empires II)", healing). A monk
heals one unit at a time: the nearest injured one that no other monk heals, so a monk stands idle when there are more
monks than injured units, as in AoE2. A monk does not heal itself, siege units, ships, units in a garrison or enemy
units, and a monk that walks does not heal.

Minecraft feature: the hit points are the `Health` of the mob (max_health = AoE2 hit points, combat.stats_command), so
`data modify entity <uuid> Health` sets them. The `regeneration` effect is not used: its rates (1 health per 50, 25,
12 ... ticks) do not match the AoE2 rate, it has no range, and the plugin cancels the natural heal of AoE2 units (#850).

    monk.heal(g, dt)        # gather.Gather.step: dt AoE2 seconds of healing
"""
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import units  # noqa: E402

RATE = 2.5      # hit points per AoE2 second of one monk: 150 per minute
RANGE = 4       # tiles
EVERY = 1.0     # AoE2 seconds between two heal passes (fewer commands); a pass heals for all the time since the last one
STILL = 0.2     # blocks: a monk that moved more since the last pass walks


def healable(name):
    """True for an AoE2 unit that a monk heals: no siege unit (a minecart) and no ship (a boat)."""
    import combat                                                  # combat imports gather, gather imports this module
    d = units.classify(name)
    return combat.SIE not in combat.stats(name).classes and not units.is_boat(d) \
        and (d or {}).get("id") != "minecraft:minecart"


def health(g, uuid):
    """(Health, max_health) of unit uuid, or None when the server gives no number."""
    from gather import NUMBER                                      # gather imports this module
    hp = re.findall(NUMBER, g.command(f"data get entity {uuid} Health").rsplit(":", 1)[-1])
    top = re.findall(r"(-?[\d.]+)", g.command(f"attribute {uuid} minecraft:max_health get").rsplit(" is ", 1)[-1])
    return (float(hp[0]), float(top[0])) if hp and top else None


def heal(g, dt):
    """Let each idle own monk of g heal the nearest injured own unit in its range for dt AoE2 seconds."""
    monks = sorted(u for u, n in g.soldiers.items() if n == "MONK")
    if not monks:
        g.monk_at, g.heal_time = {}, 0.0
        return
    g.heal_time += dt
    if g.heal_time < EVERY:
        return
    dt, g.heal_time = g.heal_time, 0.0
    inside = set().union(*g.garrisons.values())
    names = {o["uuid"]: o["name"] for o in g.units if o.get("uuid") in g.villagers} | g.soldiers
    others = sorted(u for u, n in names.items() if u not in inside and healable(n))
    pos = g.positions(others)
    last, g.monk_at = g.monk_at, {m: pos[m] for m in monks if m in pos}
    reach = RANGE * g.map.T
    hurt, taken = {}, set()
    for m in monks:
        if m in inside or m not in pos or m not in last or math.dist(pos[m], last[m]) > STILL:
            continue                                               # dead, inside, or it walks (or just came)
        near = sorted((math.dist(pos[m], pos[u]), u) for u in others if u != m and u not in taken)
        for d, u in near:
            if d > reach:
                break
            if u not in hurt:
                hurt[u] = health(g, u)
            if hurt[u] and hurt[u][0] < hurt[u][1]:
                hp = min(hurt[u][1], hurt[u][0] + RATE * dt)
                g.command(f"data modify entity {u} Health set value {round(hp, 2)}f")
                taken.add(u)
                break
