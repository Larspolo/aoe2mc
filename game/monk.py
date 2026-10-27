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

Relics (#1246): a right click on a relic of the map (a decorated pot of the converter) with a selected monk sends the
monk to it, and the monk picks it up: the pot block goes, and an item display of a pot rides the monk (Passengers, the
`ride` command). A right click on an own monastery sends the monk with the relic to its door, and the relic goes in.
Each relic in an own monastery gives 30 gold per AoE2 minute (GOLD, AoE2 wiki "Relic (Age of Empires II)"). A monk
with a relic does not heal (AoE2 rule). A killed monk drops the relic at its place, and a fallen monastery drops its
relics at its door.

    monk.order(g, player, cell)   # gather.Gather.click: a relic or a monastery at the block cell; True when it was one
    monk.relic_tick(g, dt)        # gather.Gather.step: pick up, put in, drop, and the gold
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
GOLD = 0.5      # gold per AoE2 second of one relic in a monastery: 30 per minute
REACH = 1       # blocks between the clicked cell and the relic (the ray hits the ground next to the pot)
NEAR = 2.5      # blocks from the relic or the door: there the monk picks it up or puts it in
POT = "minecraft:decorated_pot"


def relics(g):
    """[{"at": block cell or None, "monk": UUID or None, "home": monastery footprint or None}] of the relics of the
    map (aoe2mc.json, kind "other"). Made at the first call."""
    if not hasattr(g, "relics"):
        T = g.map.T
        g.relics = [{"at": (int(o["tile"][0] * T), int(o["tile"][1] * T)), "monk": None, "home": None}
                    for o in g.data["objects"] if o["kind"] == "other" and "RELIC" in o["name"]]
        g.fetching, g.relic_time, g.relic_gold, g.carrier_at = {}, 0.0, 0.0, {}
    return g.relics


def carriers(g):
    """{monk UUID: relic index} of the monks that carry a relic."""
    return {r["monk"]: i for i, r in enumerate(relics(g)) if r["monk"]}


def monasteries(g):
    """The footprints of the complete own monasteries."""
    import train                                                   # train imports gather, gather imports this module
    return {r for r, n in train.homes(g).items() if n == "MONASTERY"}


def order(g, player, cell):
    """A right click on the block cell with selected monks: the first free monk walks to a relic at the cell, or the
    monks with a relic walk to the door of the own monastery at the cell. False when the click is neither."""
    monks = [u for u in sorted(g.selected) if g.soldiers.get(u) == "MONK"]
    if not cell or not monks or not g.paper:
        return False
    import ai, civs                                                # ai imports gather, gather imports this module
    T, held = g.map.T, carriers(g)
    free = [i for i, r in enumerate(relics(g)) if r["at"] and max(abs(r["at"][0] - cell[0]), abs(r["at"][1] - cell[1])) <= REACH
            and i not in [t for k, t in g.fetching.values() if k == "relic"]]
    rect = next((r for r in monasteries(g) if r[0] <= cell[0] < r[1] and r[2] <= cell[1] < r[3]), None)
    if free and (idle := [m for m in monks if m not in held]):
        go, to = {idle[0]: ("relic", free[0])}, relics(g)[free[0]]["at"]
    elif rect and (busy := [m for m in monks if m in held]) and (to := g.map.front(rect)):
        to = next(iter(to))
        go = {m: ("home", rect) for m in busy}
    else:
        return False
    x, z = to
    for m, target in go.items():
        ai.move(g, m, "MONK", T, x + 0.5, g.map.y(x, z), z + 0.5, ai.NORMAL * civs.speed(g, "MONK"))
        g.fetching[m] = target
    g.mark(player, {to})
    return True


def drop(g, i, cell):
    """Relic i lies on the block cell: a pot block, and the display on its monk goes."""
    r = relics(g)[i]
    x, z = cell
    g.command(f"kill @e[type=item_display,tag=aoe_relic_{i}]")
    g.command(f"setblock {x} {g.map.y(x, z)} {z} {POT} keep")
    r.update(at=cell, monk=None, home=None)


def relic_tick(g, dt):
    """The monks at their relic pick it up, the monks at the door of their monastery put it in, a dead carrier and a
    fallen monastery drop their relics, and the relics in the monasteries give gold."""
    if not relics(g):
        return
    g.relic_time += dt
    if g.relic_time < EVERY:
        return
    dt, g.relic_time = g.relic_time, 0.0
    held, homes = carriers(g), monasteries(g)
    pos = g.positions(sorted(set(held) | set(g.fetching)))
    for m, i in held.items():
        if m in pos:
            g.carrier_at[m] = pos[m]
        else:                                                      # a killed monk drops the relic (AoE2)
            g.fetching.pop(m, None)
            x, _, z = g.carrier_at.pop(m)                          # set at the pick up
            drop(g, i, (math.floor(x), math.floor(z)))
    for i, r in enumerate(relics(g)):
        if r["home"] and r["home"] not in homes:                   # the monastery fell: the relics come out
            drop(g, i, next(iter(g.map.front(r["home"])), (r["home"][0], r["home"][2])))
    for m, (kind, target) in list(g.fetching.items()):
        r = relics(g)[target] if kind == "relic" else None
        to = r["at"] if r else next(iter(g.map.front(target)), None)
        if m not in pos or to is None or (kind == "home" and (target not in homes or m not in held)):
            del g.fetching[m]
        elif math.dist((pos[m][0], pos[m][2]), (to[0] + 0.5, to[1] + 0.5)) <= NEAR:
            del g.fetching[m]
            g.command(f"aoe stop {m}")
            if kind == "relic" and m not in carriers(g):           # pick it up: the pot rides the monk
                x, z = to
                y = g.map.y(x, z)
                g.command(f"fill {x} {y - 1} {z} {x} {y + 1} {z} air replace {POT}")
                g.command(f"execute at {m} run summon item_display ~ ~ ~ {{Tags:[\"aoe_relic_{target}\"],"
                          f"item:{{id:\"{POT}\",count:1}},transformation:{{left_rotation:[0f,0f,0f,1f],"
                          f"right_rotation:[0f,0f,0f,1f],translation:[0f,0.4f,0f],scale:[0.5f,0.5f,0.5f]}}}}")
                g.command(f"ride @e[type=item_display,tag=aoe_relic_{target},limit=1] mount {m}")
                r.update(at=None, monk=m)
                g.carrier_at[m] = pos[m]
            elif kind == "home":                                   # put it in; the monk stays outside
                i = carriers(g)[m]
                g.command(f"kill @e[type=item_display,tag=aoe_relic_{i}]")
                relics(g)[i].update(monk=None, home=target)
                g.carrier_at.pop(m, None)
    g.relic_gold += GOLD * dt * sum(r["home"] in homes for r in relics(g))
    if (n := int(g.relic_gold)) > 0:
        g.relic_gold -= n
        g.stock["gold"] += n
        g.command(f"scoreboard players add Gold {g.board} {n}")


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
    monks = sorted(u for u, n in g.soldiers.items() if n == "MONK" and u not in carriers(g))   # a carrier: no heal
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
