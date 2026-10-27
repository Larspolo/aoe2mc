"""
The monks of the game program (epic #1242). An idle own monk heals the own injured units near it, as in AoE2 DE (#1244):
150 hit points per AoE2 minute (RATE), in a range of 4 tiles (AoE2 wiki, "Monk (Age of Empires II)", healing). A monk
heals one unit at a time: the nearest injured one that no other monk heals, so a monk stands idle when there are more
monks than injured units, as in AoE2. A monk does not heal itself, siege units, ships, units in a garrison or enemy
units, and a monk that walks does not heal.

A right click with selected monks on an enemy unit converts it (#1245), as in AoE2 DE (AoE2 wiki, "Conversion"): the
monk walks into a range of 9 tiles, then tries once per conversion interval of 1.25 AoE2 seconds. The first 4 tries
only warm up, each later one converts with a chance of 38 %, and the 9th always converts. After a conversion the monk
rests 62 AoE2 seconds (its faith) before it can convert again. A monk cannot convert a building, a monk, a king, a hero
or a siege unit (Atonement and Redemption are excluded until a technology ticket).

Minecraft feature: the hit points are the `Health` of the mob (max_health = AoE2 hit points, combat.stats_command), so
`data modify entity <uuid> Health` sets them. The `regeneration` effect is not used: its rates (1 health per 50, 25,
12 ... ticks) do not match the AoE2 rate, it has no range, and the plugin cancels the natural heal of AoE2 units (#850).

    monk.heal(g, dt)        # gather.Gather.step: dt AoE2 seconds of healing
    monk.order(g, monks, t) # gather.Gather.click: the selected monks convert enemy unit t
    monk.convert(g, dt)     # gather.Gather.step: dt AoE2 seconds of conversion
"""
import json
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
REACH = 9       # tiles: the conversion range
INTERVAL = 1.25  # AoE2 seconds of one conversion interval
WARM = 4        # the first intervals only warm up
CHANCE = 0.38   # the chance of each later interval
SURE = 9        # the 9th interval always converts
REST = 62       # AoE2 seconds after a conversion before the monk can convert again
IMMUNE = ("KING", "QUEEN", "KHAN", "CRUSADER_KNIGHT", "HUNNIC_HORSE", "MOUNTED_SAMURAI")


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
        if m in inside or m in g.converting or m not in pos or m not in last or math.dist(pos[m], last[m]) > STILL:
            continue                                               # dead, inside, converts, or it walks (or just came)
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


def convertible(g, uuid):
    """True for an enemy unit that a monk converts: no monk (the religious units are evokers), king, hero or siege."""
    name = g.enemies.get(uuid)
    if name is None or name in IMMUNE or units.siege(name) or "EMPEROR" in name:
        return False
    hero = any(o.get("hero") for o in g.data["objects"] if o.get("uuid") == uuid)
    return str((units.classify(name, hero) or {}).get("id")) != "minecraft:evoker" and not hero


def order(g, monks, target):
    """Let the monks convert the enemy unit target. Returns False when no monk can convert it."""
    if not convertible(g, target):
        return False
    for m in monks:
        g.converting[m] = [target, 0.0, 0]                         # target, AoE2 seconds of the interval, intervals
    return True


def take(g, uuid):
    """Give the enemy unit uuid to the player of g: its tag, team and name color, and those of its horse, boat or crew
    (units.MOUNT). Its old order stops, and then it takes orders as a unit of its new player."""
    import gather                                                  # gather imports this module
    name, new = g.enemies.pop(uuid), g.player
    obj = next((o for o in g.data["objects"] if o.get("uuid") == uuid), {})
    old, obj["player"] = obj.get("player"), new
    for run in ("", f"execute as {uuid} on vehicle run ", f"execute as {uuid} on passengers run "):
        who = "@s" if run else uuid
        for cmd in (f"tag {who} remove aoe2mc.p{old}", f"tag {who} add aoe2mc.p{new}", f"team join p{new} {who}"):
            g.command(run + cmd)
    color = units.HEX.get(g.players.get(str(new), {}).get("color", ""), "#FFFFFF")
    g.command(f'data modify entity {uuid} CustomName.color set value "{color}"')
    g.command(f"aoe stop {uuid}")
    if gather.military(name) or name == "MONK":
        g.soldiers[uuid] = name
    elif pos := g.pos(uuid):
        g.villagers[uuid] = gather.Villager(uuid, pos)
        g.units.append({"kind": "unit", "name": name, "player": new, "uuid": uuid,
                        "tile": [math.floor(pos[0]) / g.map.T, math.floor(pos[2]) / g.map.T]})
    g.command("tellraw @a " + json.dumps({"text": f"A monk converts the {units.pretty(name)}.", "color": "gold"}))


def convert(g, dt):
    """dt AoE2 seconds of the conversion orders of g.converting and of the rest of the monks after a conversion."""
    for m in list(g.faith):
        g.faith[m] -= dt
        if g.faith[m] <= 0:
            del g.faith[m]
    if not g.converting:
        return
    import ai                                                      # ai imports gather, gather imports this module
    pos = g.positions(sorted(set(g.converting) | {t for t, _, _ in g.converting.values()}))
    for m, job in sorted(g.converting.items()):
        target = job[0]
        if m not in pos or target not in pos or target not in g.enemies or m not in g.soldiers:
            del g.converting[m]                                    # one of them died or the target is converted
            continue
        if math.dist(pos[m], pos[target]) > REACH * g.map.T:
            job[1:] = [0.0, 0]
            ai.move(g, m, "MONK", g.map.T, *pos[target])           # walk into range; the order follows the target
            continue
        if job[1] == 0 and job[2] == 0:
            g.command(f"aoe stop {m}")                             # in range: it stands and chants
        if m in g.faith:
            continue                                               # it rests: no faith for a conversion yet
        job[1] += dt
        while job[1] >= INTERVAL and m in g.converting:
            job[1] -= INTERVAL
            job[2] += 1
            if job[2] > WARM and (job[2] >= SURE or g.chance.random() < CHANCE):
                take(g, target)
                g.faith[m] = REST
                for k in [k for k, j in g.converting.items() if j[0] == target]:
                    del g.converting[k]
