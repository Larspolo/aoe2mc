"""
The monks of the game program (epic #1242). An idle own monk heals the own injured units near it, as in AoE2 DE (#1244):
150 hit points per AoE2 minute (RATE), in a range of 4 tiles (AoE2 wiki, "Monk (Age of Empires II)", healing). A monk
heals one unit at a time: the nearest injured one that no other monk heals, so a monk stands idle when there are more
monks than injured units, as in AoE2. A monk does not heal itself, siege units, ships, units in a garrison or enemy
units, and a monk that walks does not heal.

A right click with selected monks on an enemy unit converts it (#1245), as in AoE2 DE (AoE2 wiki, "Conversion"): the
monk walks into a range of 9 tiles, then tries once per conversion interval of 1.25 AoE2 seconds. The first 4 tries
only warm up, each later one converts with a chance of 38 %, and the 9th always converts. After a conversion the monk
rests 62 AoE2 seconds (its faith) before it can convert again; so do all monks in range that convert the same unit,
but after Theocracy (#1586) only the monk that converts it. A monk cannot convert a building, a monk, a king, a hero
or a siege unit (Atonement is excluded until a technology ticket).

Redemption (#1264, monastery, AoE2 wiki "Redemption", "Conversion"): then a monk converts siege units and the enemy
buildings with hit points (gather.Gather.forts), but not the LASTING ones (town center, castle, monastery, walls,
gates, wonder, farm, fish trap ...). A monk converts a building, ram or trebuchet only next to it (TOUCH). A building
resists: the tries start at the 15th interval, each converts with a chance of 13 %, and the 25th always converts. A
converted building joins the team of its new player (the plugin: its towers shoot at the old owner) and works for it
(aoe2mc.json "player": train.homes, garrison.holders).

Devotion and Faith (#1584, monastery, AoE2 DE wiki): the units of a player with them resist conversion. Devotion adds
1 s to the minimum and maximum conversion time, Faith 4 s more: 1 and 3 more warm intervals, and the sure one later
(RESIST, 5 s in all).

Minecraft feature: the hit points are the `Health` of the mob (max_health = AoE2 hit points, combat.stats_command), so
`data modify entity <uuid> Health` sets them. The `regeneration` effect is not used: its rates (1 health per 50, 25,
12 ... ticks) do not match the AoE2 rate, it has no range, and the plugin cancels the natural heal of AoE2 units (#850).

    monk.heal(g, dt)        # gather.Gather.step: dt AoE2 seconds of healing
    monk.convert_order(g, monks, t)  # gather.Gather.click: the selected monks convert enemy unit t
    monk.convert(g, dt)     # gather.Gather.step: dt AoE2 seconds of conversion (also of a building with Redemption)

Relics (#1246): a right click on a relic of the map (a decorated pot of the converter) with a selected monk sends the
monk to it, and the monk picks it up: the pot block goes, and an item display of a pot rides the monk (Passengers, the
`ride` command). A right click on an own monastery sends the monk with the relic to its door, and the relic goes in.
Each relic in an own monastery gives 30 gold per AoE2 minute (GOLD, AoE2 wiki "Relic (Age of Empires II)"). A monk
with a relic does not heal (AoE2 rule). A killed monk drops the relic at its place, and a fallen monastery drops its
relics at its door. All sides of a game share one list of the relics (#3116: run.play, bot.Bot), so each relic exists
once: the key "player" of a relic names the player of its monk or monastery (own).

Civilization bonuses (#2314, AoE2 DE wiki): each relic in an own monastery gives +1 attack to the Lithuanian knights
and Leitis, at most +4 (civs.RELIC_ATTACK, civs.units; relic_tick sends the new values), and Muisca monks regain faith
100 % faster (civs.FAITH: the rest after a conversion is half as long).

    monk.order(g, player, cell)   # gather.Gather.click: a relic or a monastery at the block cell; True when it was one
    monk.relic_tick(g, dt)        # gather.Gather.step: pick up, put in, drop, and the gold
"""
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import owners  # noqa: E402
import table  # noqa: E402
import units  # noqa: E402

RATE = 2.5      # hit points per AoE2 second of one monk: 150 per minute
RANGE = 4       # tiles
EVERY = 1.0     # AoE2 seconds between two heal passes (fewer commands); a pass heals for all the time since the last one
STILL = 0.2     # blocks: a monk that moved more since the last pass walks
CONVERT = 9     # tiles: the conversion range
# The units that heal, convert and carry relics: their conversion range (#1939, the key "convert" of data/units.jsonl)
MONKS = {r["name"]: r["convert"] for r in table.load("units.jsonl") if "convert" in r}
PRINTING = 3    # tiles of conversion range that Block Printing adds (#1457)
INTERVAL = 1.25  # AoE2 seconds of one conversion interval
WARM = 4        # the first intervals only warm up
CHANCE = 0.38   # the chance of each later interval
SURE = 9        # the 9th interval always converts
REST = 62       # AoE2 seconds after a conversion before the monk can convert again
ILLUMINATED = 33   # the rest after Illumination: 87.5 % faster (AoE2 wiki "Illumination", #1583)
RULES = table.load("monk.jsonl")                                  # the names of IMMUNE, NEXT and LASTING (#2034)
IMMUNE = tuple(r["name"] for r in RULES if r.get("immune"))
TOUCH = 1.5     # blocks between a monk and a building, ram or trebuchet that it converts: next to it (AoE2)
NEXT = tuple(r["name"] for r in RULES if r.get("next"))   # the siege units that a monk converts only next to them
# More warm intervals and a later sure one: +1 s and +4 s (AoE2 DE wiki), 5 s in all (#1584, "resist" of data/train.jsonl)
RESIST = {r["name"]: r["resist"] for r in table.load("train.jsonl") if "resist" in r}
# A technology that converts more: "buildings" (Monotheism, antiquity mode, #3986), "monks" (the priests, as Atonement)
CONVERTS = {r["name"]: r["converts"] for r in table.load("train.jsonl") if "converts" in r}
FORT = (14, 0.13, 25)   # a building: warm intervals, chance (38 % / resistance 3) and the sure interval (AoE2 wiki)
# Parts of the names of the buildings that no monk converts, also with Redemption
LASTING = tuple(r["name"] for r in RULES if r.get("lasting"))
GOLD = 0.5      # gold per AoE2 second of one relic in a monastery: 30 per minute
REACH = 1       # blocks between the clicked cell and the relic (the ray hits the ground next to the pot)
NEAR = 2.5      # blocks from the relic or the door: there the monk picks it up or puts it in
POT = "minecraft:decorated_pot"


def relics(g):
    """[{"at": block cell or None, "monk": UUID or None, "home": monastery footprint or None, "player": the player of
    the monk or the monastery (not on the ground)}] of the relics of the map (aoe2mc.json, kind "other"). Made at the
    first call."""
    if not hasattr(g, "relics"):
        T = g.map.T
        g.relics = [{"at": (int(o["tile"][0] * T), int(o["tile"][1] * T)), "monk": None, "home": None}
                    for o in g.data["objects"] if o["kind"] == "other" and "RELIC" in o["name"]]
        g.fetching, g.relic_time, g.relic_gold, g.carrier_at = {}, 0.0, 0.0, {}
    return g.relics


def own(g, r):
    """True when relic r is with a monk or in a monastery of the player of g. A relic with no "player" (on the ground,
    or set by a test) counts for each side."""
    return r.get("player", g.player) == g.player


def free_relic(g, site):
    """Put the free relics of the civilization (key free_relic, {building: relics}) into the complete own building
    site: only into the first one of the game (AoE2 DE wiki "Armenians": the first Fortified Church, #2419)."""
    import civs                                                    # civs imports gather, gather imports this module
    n = civs.value("free_relic", civs.civ(g), {}).get(site["name"], 0)
    if n and not any(r.get("free") and own(g, r) for r in relics(g)):      # one for each player (#3116)
        g.relics += [{"at": None, "monk": None, "home": tuple(site["footprint"]), "free": True, "player": g.player}
                     for _ in range(n)]


def carriers(g):
    """{monk UUID: relic index} of the own monks that carry a relic."""
    return {r["monk"]: i for i, r in enumerate(relics(g)) if r["monk"] and own(g, r)}


def monasteries(g):
    """The footprints of the complete own monasteries."""
    import train                                                   # train imports gather, gather imports this module
    import combat
    return {r for r, n in train.homes(g).items() if combat.STANDS_FOR.get(n, n) == "MONASTERY"}   # the church too (#1930)


def order(g, player, cell):
    """A right click on the block cell with selected monks: the first free monk walks to a relic at the cell, or the
    monks with a relic walk to the door of the own monastery at the cell. False when the click is neither."""
    monks = [u for u in sorted(g.selected) if g.soldiers.get(u) in MONKS]
    if not cell or not monks or not g.paper:
        return False
    import ai, train                                               # ai imports gather, gather imports this module
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
    g.new_order(go)
    for m, target in go.items():
        name = g.soldiers[m]
        ai.move(g, m, name, T, x + 0.5, g.map.y(x, z), z + 0.5, ai.NORMAL * train.speed(g, name, m))
        g.fetching[m] = target
    g.mark(player, {to})
    return True


def drop(g, i, cell):
    """Relic i lies on the block cell, or on the nearest free land cell when the cell is water (#3119): a pot block,
    and the display on its monk goes."""
    import capture_relic, transport                                # they import gather, gather imports this module
    r = relics(g)[i]
    if not g.map.free(*cell):
        cell = next(iter(transport.land(g, cell, 1, tiles=capture_relic.SEARCH)), cell)
    x, z = cell
    g.command(f"kill @e[type=item_display,tag=aoe_relic_{i}]")
    g.command(f"setblock {x} {g.map.y(x, z)} {z} {POT} keep")
    r.update(at=cell, monk=None, home=None)
    r.pop("player", None)


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
        if r["home"] and own(g, r) and r["home"] not in homes:     # the monastery fell: the relics come out
            taken = {q["at"] for q in relics(g) if q["at"]}        # one relic on each cell, one pot each (#3010)
            ring = sorted(g.map.front(r["home"]))
            cells = ring + sorted(g.map.around(set(ring)))
            drop(g, i, next((c for c in cells if c not in taken), (r["home"][0], r["home"][2])))
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
                r.update(at=None, monk=m, player=g.player)
                g.carrier_at[m] = pos[m]
            elif kind == "home":                                   # put it in; the monk stays outside
                i = carriers(g)[m]
                g.command(f"kill @e[type=item_display,tag=aoe_relic_{i}]")
                relics(g)[i].update(monk=None, home=target)
                g.carrier_at.pop(m, None)
    if (n := sum(r["home"] is not None and own(g, r) for r in relics(g))) != getattr(g, "relic_homes", 0):
        g.relic_homes = n
        rearm(g)
    g.relic_gold += GOLD * dt * sum(r["home"] in homes for r in relics(g))
    if (n := int(g.relic_gold)) > 0:
        g.relic_gold -= n
        g.earn("gold", n)


def rearm(g):
    """The own units of civs.RELIC_ATTACK get the attack of the relics in own monasteries (Lithuanians, #2314)."""
    import civs, combat, train                                     # they import gather, gather imports this module
    names = civs.RELIC_ATTACK.get(civs.civ(g), ((),))[0]
    for uuid, name in [(u["uuid"], u["name"]) for u in g.units if "uuid" in u] + list(g.soldiers.items()):
        if name in names:
            g.command(combat.stats_command(uuid, name, train.stats(g, name, uuid)))


def healable(name):
    """True for an AoE2 unit that a monk heals: no siege unit (a minecart), no ship (a boat) and no building that moves
    (the mule cart, AoE2 DE wiki "Mule Cart": "a building which can move and not a unit", #2522)."""
    import combat                                                  # combat imports gather, gather imports this module
    d, classes = units.classify(name), combat.stats(name).classes
    return combat.SIE not in classes and "building" not in classes and not units.is_boat(d) \
        and (d or {}).get("id") != "minecraft:minecart"


def health(g, uuid):
    """(Health, max_health) of unit uuid, or None when the server gives no number."""
    from gather import NUMBER                                      # gather imports this module
    hp = re.findall(NUMBER, g.command(f"data get entity {uuid} Health").rsplit(":", 1)[-1])
    top = re.findall(r"(-?[\d.]+)", g.command(f"attribute {uuid} minecraft:max_health get").rsplit(" is ", 1)[-1])
    return (float(hp[0]), float(top[0])) if hp and top else None


def heal(g, dt):
    """Let each idle own monk of g heal the nearest injured own unit in its range for dt AoE2 seconds."""
    monks = sorted(u for u, n in g.soldiers.items() if n in MONKS and u not in carriers(g))   # a carrier: no heal
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
    import civs                                                    # civs imports gather, gather imports this module
    reach = RANGE * civs.HEAL_RANGE.get(civs.civ(g), 1) * g.map.T   # the Teutons: twice (#2269)
    import train                                                   # train imports this module's callers (#3984)
    rate = RATE * math.prod(train.value("heal_rate", t, 1) for t in g.techs)   # Medicine of Antiquity Mode: 2
    hurt, taken = {}, set()
    for m in monks:
        if m in inside or m in g.converting or m not in pos or m not in last or math.dist(pos[m], last[m]) > STILL:
            continue                                               # dead, inside, converts, or it walks (or just came)
        near = sorted((math.dist(pos[m], pos[u]), u) for u in others if u != m and u not in taken and u in pos)
        for d, u in near:
            if d > reach:
                break
            if u not in hurt:
                hurt[u] = health(g, u)
            if hurt[u] and hurt[u][0] < hurt[u][1]:
                hp = min(hurt[u][1], hurt[u][0] + rate * dt)
                g.command(f"data modify entity {u} Health set value {round(hp, 2)}f")
                g.command(f"execute at {u} anchored eyes run particle minecraft:heart ^ ^ ^ 0.3 0.3 0.3 0 2")   # #1634
                taken.add(u)
                break


def converts(g, what):
    """True when a researched technology converts `what` (CONVERTS, key "converts" of data/train.jsonl)."""
    return any(what in CONVERTS.get(t, ()) for t in g.techs)


def convertible(g, uuid):
    """True for an enemy unit that a monk converts: no monk (the religious units are evokers; with Atonement or
    Monotheism: also them), king, hero or siege (with Redemption: siege, and an enemy building that is not LASTING;
    Monotheism: the building too)."""
    redeemed = "REDEMPTION" in g.techs
    if uuid in g.forts:
        return (redeemed or converts(g, "buildings")) and not any(n in g.fort_names.get(uuid, "") for n in LASTING)
    name = g.enemies.get(uuid)
    if name is None or name in IMMUNE or units.siege(name) and not redeemed or "EMPEROR" in name:
        return False
    hero = any(o.get("hero") for o in g.data["objects"] if o.get("uuid") == uuid)
    religious = name in MONKS or str((units.classify(name, hero) or {}).get("id")) == "minecraft:evoker"
    return not hero and (not religious or "ATONEMENT" in g.techs or converts(g, "monks"))


def convert_order(g, monks, target):
    """Let the monks convert the enemy unit or building (target UUID) target. Returns False when no monk can
    convert it."""
    if not convertible(g, target):
        return False
    g.new_order(monks)
    for m in monks:
        g.converting[m] = [target, 0.0, 0]                         # target, AoE2 seconds of the interval, intervals
    return True


def take(g, uuid):
    """Give the enemy unit uuid to the player of g: its tag, team and name color, and those of its horse, boat or crew
    (units.MOUNT). Its old order stops, and then it takes orders as a unit of its new player."""
    name, new, old = g.enemies[uuid], g.player, owners.player(g, uuid)
    for run in ("", f"execute as {uuid} on vehicle run ", f"execute as {uuid} on passengers run "):
        who = "@s" if run else uuid
        for cmd in (f"tag {who} remove aoe2mc.p{old}", f"tag {who} add aoe2mc.p{new}", f"team join p{new} {who}"):
            g.command(run + cmd)
    color = units.HEX.get(g.players.get(str(new), {}).get("color", ""), "#FFFFFF")
    g.command(f'data modify entity {uuid} CustomName.color set value "{color}"')
    g.command(f"aoe stop {uuid}")
    owners.give(g, uuid, new)                                      # the lists of all sides (#2993)
    g.command(f"tellraw @a[team=p{g.player}] " + json.dumps({"text": f"A monk converts the {units.pretty(name)}.", "color": "gold"}))
    import train                                                   # train imports this module (#3502)
    g.command(f"execute at {uuid} run playsound {train.EVENT_SOUNDS['convert']} master @a ~ ~ ~ 1 1")


def heresy(g, player):
    """True when player researched Heresy (#1582): its Gather is g, a bot of g (bot.Bot) or the human Gather that the bot
    of g shares."""
    import build                                                   # build imports gather, which imports this module
    return any(h.player == player and "HERESY" in h.techs for h in [g, *build.sides(g)])   # also a second person (#3106)


def die(g, uuid):
    """The enemy unit uuid dies in place of a conversion (Heresy of its player), with its horse, camel, boat or rider."""
    name = g.enemies.pop(uuid)
    owners.killed(g, {uuid})                                           # update_enemies keeps it out (#2996)
    for run in (f"execute as {uuid} on vehicle run ", f"execute as {uuid} on passengers run ", ""):
        g.command(run + ("kill @s" if run else f"kill {uuid}"))
    g.command(f"tellraw @a[team=p{g.player}] " + json.dumps({"text": f"The {units.pretty(name)} dies (Heresy).",
                                                               "color": "gold"}))


def win(g, uuid):
    """Give the enemy building with the target uuid to the player of g (Redemption): its target entity joins the team
    of the player, and its entry of aoe2mc.json gets the player, so that it trains and takes a garrison for it."""
    import build, combat                                           # they import gather, gather imports this module
    owners.give_building(g, uuid, g.player)                        # the sides of the game, and the sites (#2994)
    g.sieged.discard(uuid)
    for o in g.data["objects"]:
        if o["kind"] == "building" and "footprint" in o and combat.target_uuid(o["footprint"]) == uuid:
            o["player"] = g.player
    g.command(f"team join p{g.player} {uuid}")
    g.command(f"tellraw @a[team=p{g.player}] " + json.dumps({"text": f"A monk converts the {build.pretty(g.fort_names.get(uuid, 'BUILDING'))}.",
                                          "color": "gold"}))


def resist(g, uuid):
    """The extra conversion intervals of the unit uuid: Devotion and Faith of its player (RESIST), from the Gather of
    that player (g or one of its bots)."""
    player = owners.player(g, uuid)                                # also a unit of the game (#2992)
    import build                                                   # build imports gather, which imports this module
    techs = next((x.techs for x in (g, *build.sides(g)) if x.player == player), ())   # also a second person (#3106)
    return sum(RESIST.get(t, 0) for t in techs)


def near(g, m, target, pos):
    """True when monk m is in its conversion range of the target: next to a building, ram or trebuchet (TOUCH),
    else the range of MONKS (and PRINTING more after Block Printing, and the key "reach" of the techs)."""
    if target in g.forts:
        x0, _, z0, x1, _, z1 = g.forts[target]
        x, _, z = pos[m]
        return math.hypot(max(x0 - x, 0, x - x1 - 1), max(z0 - z, 0, z - z1 - 1)) <= TOUCH
    if any(n in g.enemies[target] for n in NEXT):
        return math.dist(pos[m], pos[target]) <= TOUCH + 1         # to its middle: about 1 block from its side
    import train                                                   # train imports gather, gather imports this module
    reach = MONKS.get(g.soldiers.get(m), CONVERT) + PRINTING * ("BLOCK_PRINTING" in g.techs)
    reach += sum(train.value("reach", t, 0) for t in g.techs)     # Afterlife of Antiquity Mode (#3988)
    return math.dist(pos[m], pos[target]) <= reach * g.map.T


def spot(g, m, target, pos):
    """Where monk m walks to convert the target: the cell next to a building on the side of the monk, else the
    target."""
    if target not in g.forts:
        return pos[target]
    x0, y0, z0, x1, _, z1 = g.forts[target]
    x, z = (min(max(math.floor(p), lo - 1), hi + 1) for p, lo, hi in ((pos[m][0], x0, x1), (pos[m][2], z0, z1)))
    return x + 0.5, g.map.y(x, z) or y0, z + 0.5


def faith(g):
    """The factor of the speed of the own monks that regain faith after a conversion (civs.FAITH: Muisca 2, #2314)."""
    import civs                                                    # civs imports gather, gather imports this module
    return civs.FAITH.get(civs.civ(g), 1)


def convert(g, dt):
    """dt AoE2 seconds of the conversion orders of g.converting and of the rest of the monks after a conversion."""
    for m in list(g.faith):
        g.faith[m] -= dt
        if g.faith[m] <= 0:
            del g.faith[m]
    if not g.converting:
        return
    import ai, train                                               # ai imports gather, gather imports this module
    pos = g.positions(sorted(set(g.converting) | {t for t, _, _ in g.converting.values()}))
    for m, job in sorted(g.converting.items()):
        if m not in g.converting:
            continue                                               # its group converted the target in this pass
        target = job[0]
        fort = target in g.forts
        if m not in pos or target not in pos or not (fort or target in g.enemies) or m not in g.soldiers:
            del g.converting[m]                                    # one of them died or the target is converted
            continue
        if not near(g, m, target, pos):
            job[1:] = [0.0, 0]
            name = g.soldiers.get(m, "MONK")
            ai.move(g, m, name, g.map.T, *spot(g, m, target, pos), ai.NORMAL * train.speed(g, name, m))   # walk into range; the order follows the target
            continue
        if job[1] == 0 and job[2] == 0:
            g.command(f"aoe stop {m}")                             # in range: it stands and chants
        if m in g.faith:
            continue                                               # it rests: no faith for a conversion yet
        job[1] += dt
        while job[1] >= INTERVAL and m in g.converting:
            job[1] -= INTERVAL
            job[2] += 1
            more = 0 if fort else resist(g, target)
            warm, chance, sure = FORT if fort else (WARM + more, CHANCE, SURE + more)
            if job[2] > warm and (job[2] >= sure or g.chance.random() < chance):
                group = [k for k, j in g.converting.items() if j[0] == target]
                rest = [m] if "THEOCRACY" in g.techs else [k for k in group if k in pos and near(g, k, target, pos)]
                owner = owners.player(g, target)
                (win if fort else die if heresy(g, owner) else take)(g, target)
                for k in group:
                    del g.converting[k]
                import train                                       # train imports this module (#3502)
                rest_factor = math.prod(train.value("rest", t, 1) for t in g.techs)   # Fanaticism: 0.5 (#3987)
                for k in rest:                                     # the group in range (Theocracy: one)
                    g.faith[k] = (ILLUMINATED if "ILLUMINATION" in g.techs else REST) * rest_factor / faith(g)
