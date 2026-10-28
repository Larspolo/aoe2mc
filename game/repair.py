"""Repairs in the game program (#1330, epic #1329). A right click with selected villagers on an own damaged building
sends them to it: they walk next to it (Minecraft path finding, gather.Gather.go, as builders) and repair it, as in
AoE2 DE (AoE2 wiki "Villager (Age of Empires II)", repairing): the first villager repairs 750 hit points per AoE2
minute, each other one 375 more (RATE, MORE), up to the full hit points. A click on an undamaged own building is not
a repair order: garrison.order gets it.

The repair takes half the build cost (build.price, with the bonuses of the civilization) for the full hit points, in
the share of the hit points that it gives back; a town center takes double its wood and no stone (550 wood for the
full repair). The stock pays whole units as the repair goes on. With too few resources the repair stops with a chat
line, and the villagers stand idle. A building with no build cost (build.COSTS) repairs free.

Allied buildings (#1361): the villagers also repair a damaged building of an allied player (gather.allied), as in AoE2
("While players cannot construct allied buildings, they can repair them"). The own stock pays, with the build cost of
the civilization of the ally. A building of an enemy or of no player is not repaired.

Siege units (#1331): a right click with selected villagers on an own damaged siege unit (units.siege: a minecart)
sends them next to it. AoE2 repairs siege weapons at 25 % of the building rate (SIEGE: 187.5 hit points per minute for
the first villager, 93.75 for each other one), for half the training cost (train.price). A siege unit that moves stops
the repair, as in AoE2: the villagers stand idle. The Georgian team bonus (civs.REPAIR_COST) does not lower the cost
of a unit (AoE2 wiki "Villager (Age of Empires II)": "The bonus does not apply to repairing units", #1929).

Civilization bonuses of the rate (civs.repair_rate): Roman repairers work 5 % faster, and the Saxon team bonus makes
the repairers of the Saxons and their allies 25 % faster (AoE2 wiki "Saxons", #1929). The two factors multiply.

Mule carts (#2504): a mule cart (build.MOVES) is a building that moves. Villagers repair it as a siege unit, but at
the building rate and for half its build cost with the Georgian team bonus (cost): 7.5 food and 30 wood for the full
hit points, as the AoE2 wiki "Mule Cart" says. Its mob is a mule with the hit points itself, not a crew (body).

Ships (#1661): AoE2 repairs ships at the siege rate, for half the training cost, from the shore: a villager repairs
from up to REACH tiles away. So a right click with selected villagers on an own damaged ship (fleet.SPEEDS) sends them
to the free land cells within REACH tiles of the ship. A ship far from the shore (no such cell) is not a repair order.
The crew of the boat has the hit points (fleet.py), as the crew of a minecart: the same commands.

Serjeants (#2128): the Sicilian Serjeant also repairs the Donjon (AoE2 wiki "Serjeant (Age of Empires II)": "Can build
and repair Donjons"). Selected Serjeants on an own damaged Donjon walk next to it (ai.move, the plugin path finding) and
repair it when they stand within NEAR blocks of its footprint (the key "repairs" of their line in units.jsonl,
combat.REPAIRS). The wiki gives no own rate: they count as villagers. A
new move or attack order (gather.Gather.walk_to, attack) ends their repair (drop).
They also build an own unfinished Donjon site (#2129): a right click with selected Serjeants on it, or the placement of
the site with them selected (build_order). The Serjeants within NEAR blocks of its footprint count as builders at the
villager rate (raisers, gather.Gather.step).

Minecraft feature: the plugin keeps the hit points of a building in the scoreboard aoe_hp of its target entity
(combat.building, #660), so `scoreboard players get/set <uuid> aoe_hp` reads and sets them, and `aoe label` shows the
new hearts of its name line. A siege unit has its hit points as the Health of its crew (the passenger of the minecart,
AoePlugin "stats", #836): `execute as <cart> on passengers run data get/modify entity @s Health`.

    repair.order(g, player, cell)   # gather.Gather.click: the selection repairs the damaged building at cell
    repair.unit_order(g, player, u) # gather.Gather.click: the selection repairs the damaged siege unit or ship u
    repair.tick(g, dt)              # gather.Gather.step: dt AoE2 seconds of repair
"""
import json
import math
import re
import types

RATE = 750 / 60             # hit points per AoE2 second of the first repairer
MORE = 375 / 60             # hit points per AoE2 second of each other repairer
SHARE = 0.5                 # of the build cost for the full hit points
SIEGE = 0.25                # the rate of a siege unit: a share of the building rate (AoE2 wiki "Villager")
STILL = 0.5                 # blocks: a siege unit that moved more stops the repair
REACH = 2                   # tiles from a villager on the shore to the ship that it repairs (AoE2 wiki "Villager")
NEAR = 2                    # blocks from the footprint: a Serjeant there repairs


def owners(g):
    """{block footprint (x0, x1, z0, z1): (name, player)} of the own and the allied buildings with AoE2 hit points (a
    target entity): the start ones and the complete construction sites of the player and of the bots (#1361)."""
    from gather import allied                                      # gather imports this module
    import combat
    mine = {g.player} | {int(p) for p in g.players if int(p) and allied(g.players, g.player, int(p))}   # no Gaia
    out = {(x0, x1, z0, z1): (o["name"], o["player"]) for o in g.data["objects"] if o["kind"] == "building"
           and o["name"] in combat.BUILDINGS and o["player"] in mine and "footprint" in o for x0, z0, x1, z1 in [o["footprint"]]}
    return out | {tuple(s["footprint"]): (s["name"], s["player"]) for s in g.sites + [s for b in g.bots for s in b.g.sites]
                  if s.get("done") and s["player"] in mine and (s["name"] in combat.BUILDINGS or s["name"] in combat.WALLS)}


def buildings(g):
    """{block footprint (x0, x1, z0, z1): name} of the own and the allied buildings with AoE2 hit points (owners)."""
    return {r: n for r, (n, _) in owners(g).items()}


def full(g, name, player, rect=None):
    """The full hit points of building name of player: a wall or gate has those of its design in the age of its
    player (combat.wall, as build.target, #1360), a watch tower those of its tower technology (build.line, #1374), a
    building those of Masonry (build.values, #1398) and of its upgrade of one building at the footprint rect (#2497)."""
    import build, civs, combat                                     # build imports gather
    who = next((b.g for b in g.bots if b.g.player == player), g)   # an allied bot: its techs and age
    if name not in combat.WALLS:
        return build.values(who, name, rect=rect).hp
    return combat.wall(build.design(who, name, player), build.ages(who), civs.civ(who, player),
                       civs.handicap(who.data, player)).hp


def uuid(rect):
    """The UUID of the target entity of the building with block footprint rect."""
    import combat
    return combat.target_uuid([rect[0], rect[2], rect[1], rect[3]])


def hp(g, rect):
    """The hit points of the building rect (the score aoe_hp of its target entity), or None when it has none."""
    m = re.search(r" has (-?\d+) ", g.command(f"scoreboard players get {uuid(rect)} aoe_hp"))
    return int(m[1]) if m else None


def cost(g, name, player=None):
    """{resource: amount} for the full hit points of building name of the player of g, or of an ally (#1361)."""
    import build, civs                                             # build imports gather
    if name not in build.COSTS:
        return {}
    price, k = build.price(g, name, player), civs.repair_cost(g)    # the Georgian team bonus (#1730)
    if name == "TOWN_CENTER":                                      # AoE2 wiki: 550 wood (double the wood), no stone
        return {"wood": price.get("wood", 0) * 2 * k}
    return {r: v * SHARE * k for r, v in price.items()}


def crew(u):
    """The prefix of a command that runs on the crew of siege unit u (it has the hit points)."""
    return f"execute as {u} on passengers run "


def body(g, u):
    """The prefix of a command that runs on the mob of unit u with its hit points: the crew of a siege unit or ship,
    the mob itself of a mule cart (build.MOVES, a mule with no passenger, #2504)."""
    import build                                                   # build imports gather
    return f"execute as {u} run " if g.soldiers.get(u) in build.MOVES else crew(u)


def unit_hp(g, u):
    """(Health, max_health) of siege unit, ship or mule cart u, or None when the server gives no number (dead, unloaded)."""
    from gather import NUMBER                                      # gather imports this module
    hp = re.findall(NUMBER, g.command(body(g, u) + "data get entity @s Health").rsplit(":", 1)[-1])
    top = re.findall(r"(-?[\d.]+)", g.command(body(g, u) + "attribute @s minecraft:max_health get").rsplit(" is ", 1)[-1])
    return (float(hp[0]), float(top[0])) if hp and top else None


def send(g, who, key, goals):
    """The villagers who walk to goals and repair key (a building footprint, or the UUID of a siege unit)."""
    g.repairs = vars(g).get("repairs", {})
    g.new_order(who)
    for u in who:
        v = g.villagers[u]
        v.tree, v.site, v.prey = None, None, None
        g.repairs[u] = key
        g.task(v, "BUILDER")
        g.go(v, "to_repair", goals)


def resume(g, u, key, state):
    """Villager u of a loaded game repairs key again (a building footprint or the UUID of a siege unit, savegame, #2380):
    "to_repair" walks to it again, "repair" works on at its place. Returns False when key is gone."""
    import fleet                                                   # fleet imports gather
    if isinstance(key, str) and (pos := g.pos(key)):
        cell = (math.floor(pos[0]), math.floor(pos[2]))
        goals = shore(g, cell) if g.soldiers.get(key) in fleet.SPEEDS else g.map.around({cell})
        vars(g).setdefault("repair_at", {})[key] = pos             # unit_tick stops a repair of a unit that moves (#2987)
    elif isinstance(key, tuple) and key in owners(g):
        goals = g.map.around({(x, z) for x in range(key[0], key[1]) for z in range(key[2], key[3])})
    else:
        return False
    if state == "to_repair":
        send(g, [u], key, goals)
    else:
        g.repairs = vars(g).get("repairs", {})
        g.repairs[u] = key
    return True


def shore(g, cell):
    """The free land cells within REACH tiles of the ship on the water cell cell: the villagers repair it from there."""
    r, (x, z) = REACH * g.map.T, cell
    return {(x + dx, z + dz) for dx in range(-r, r + 1) for dz in range(-r, r + 1) if g.map.free(x + dx, z + dz)}


def unit_order(g, player, u):
    """The selected villagers repair the own damaged siege unit, ship or mule cart u. Returns True, or False (no own
    siege unit, ship or mule cart, it has its full hit points, a ship far from the shore, or no villager is selected)."""
    import build, fleet                                            # build and fleet import gather
    import units                                                   # the converter's table (gather puts it on the path)
    name, who = g.soldiers.get(u), sorted(g.selected & g.villagers.keys())
    if not name or not (units.siege(name) or name in fleet.SPEEDS or name in build.MOVES) or not who or not (pos := g.pos(u)):
        return False
    cell = (math.floor(pos[0]), math.floor(pos[2]))
    goals = shore(g, cell) if name in fleet.SPEEDS else g.map.around({cell})
    h = goals and unit_hp(g, u)
    if not h or not 0 < h[0] < h[1]:
        return False
    vars(g).setdefault("repair_at", {})[u] = pos                   # a move from here stops the repair
    send(g, who, u, goals)
    g.mark(player, {cell})
    return True


def order(g, player, cell):
    """The selected villagers repair the own damaged building with the block cell (x, z) in its footprint. Returns its
    footprint, or None (no such building, it has its full hit points, or no villager is selected)."""
    import combat
    homes = owners(g)
    rect = next((r for r in homes if cell and r[0] <= cell[0] < r[1] and r[2] <= cell[1] < r[3]), None)
    who = sorted(g.selected & g.villagers.keys())
    men = sorted(u for u in g.selected if rect and combat.REPAIRS.get(g.soldiers.get(u)) == homes[rect][0])   # Serjeants
    if rect is None or not (who or men) or not 0 < (hp(g, rect) or 0) < full(g, *homes[rect], rect):
        return None
    x0, x1, z0, z1 = rect
    goals = g.map.around({(x, z) for x in range(x0, x1) for z in range(z0, z1)})
    if who:
        send(g, who, rect, goals)
    march(g, men, rect, goals)
    g.mark(player, {(x0, z0), (x1 - 1, z1 - 1)})
    return rect


def march(g, men, rect, goals, job="mending", what=None):
    """The Serjeants men walk to the free cells goals next to the Donjon rect and repair it there (#2128), or build the
    site what there (job "raising", #2129)."""
    import ai, train                                               # ai and train import gather
    from gather import NORMAL
    jobs = vars(g).setdefault(job, {})
    cells = sorted(goals)
    for k, u in enumerate(men):
        x, z = cells[k * len(cells) // len(men)] if cells else ((rect[0] + rect[1]) // 2, rect[3])
        name = g.soldiers[u]
        ai.move(g, u, name, g.map.T, x + 0.5, g.map.y(x, z), z + 0.5, NORMAL * train.speed(g, name, u))
        jobs[u] = rect if what is None else what


def drop(g, units):
    """The units get another order: the Serjeants among them stop their repair or their build."""
    for u in units:
        vars(g).get("mending", {}).pop(u, None)
        vars(g).get("raising", {}).pop(u, None)


def build_order(g, site, units):
    """The Serjeants among units build the own unfinished site of their building (#2129). Returns them."""
    import combat
    men = sorted(u for u in units if combat.REPAIRS.get(g.soldiers.get(u)) == site["name"])
    if not men or site["progress"] >= 1 or site.get("player", g.player) != g.player:
        return []
    x0, x1, z0, z1 = rect = site["footprint"]
    march(g, men, rect, g.map.around({(x, z) for x in range(x0, x1) for z in range(z0, z1)}), "raising", site)
    return men


def raisers(g, site):
    """The Serjeants that build site and stand within NEAR blocks of its footprint (#2129)."""
    raising, out = vars(g).get("raising", {}), []
    x0, x1, z0, z1 = site["footprint"]
    for u, s in sorted(raising.items()):
        if not (u in g.soldiers and (pos := g.pos(u))):
            del raising[u]                                         # dead
        elif s is site and x0 - NEAR <= pos[0] < x1 + NEAR and z0 - NEAR <= pos[2] < z1 + NEAR:
            out.append(u)
    return out


def rate(g, vs):
    """Hit points per AoE2 second of the repairers vs of a building, with the bonus of the civilization (#1730) and the
    mean bonus of the Fortified Church at the places of the repairers (civs.church_rate, #1930)."""
    import civs                                                    # gather puts game/ on the path
    near = sum(civs.church_rate(g, (v.pos[0], v.pos[2])) for v in vs) / len(vs)
    return (RATE + MORE * (len(vs) - 1)) * civs.repair_rate(g) * near


def tick(g, dt):
    """dt AoE2 seconds of repair: the villagers in the state "repair" give their building its hit points back and the
    stock pays for them."""
    repairs = vars(g).get("repairs", {})
    work = {}
    for u, rect in list(repairs.items()):
        v = g.villagers.get(u)
        if v is None or v.state not in ("to_repair", "repair"):        # another order, or dead
            del repairs[u]
        elif v.state == "repair":
            work.setdefault(rect, []).append(v)
    mending = vars(g).get("mending", {})
    for u, rect in sorted(mending.items()):                        # the Serjeants next to their Donjon
        if not (u in g.soldiers and (pos := g.pos(u))):
            del mending[u]                                         # dead
        elif rect[0] - NEAR <= pos[0] < rect[1] + NEAR and rect[2] - NEAR <= pos[2] < rect[3] + NEAR:
            work.setdefault(rect, []).append(types.SimpleNamespace(uuid=u, pos=pos))
    if not work:
        return
    homes, g.repair_owed = owners(g), vars(g).get("repair_owed", {})
    for rect, vs in sorted(work.items(), key=lambda kv: (isinstance(kv[0], str), kv[0])):
        if isinstance(rect, str):                                  # a siege unit (#1331)
            unit_tick(g, rect, vs, dt)
            continue
        now = hp(g, rect) if rect in homes else None
        name, player = homes.get(rect, (None, None))
        top = full(g, name, player, rect) if rect in homes else 0
        if not now or now >= top:                                  # fallen or full: the work ends
            stop(g, rect, vs)
            continue
        gain = top - now if g.aegis else min(top - now, rate(g, vs) * dt)
        if not charge(g, rect, vs, cost(g, name, player), gain / top, name):
            continue
        g.repair_hp = vars(g).get("repair_hp", {})                 # the fractions of a hit point
        whole = g.repair_hp.get(rect, 0.0) + gain
        g.repair_hp[rect] = whole - math.floor(whole)
        new = min(top, now + math.floor(whole))
        g.command(f"scoreboard players set {uuid(rect)} aoe_hp {new}")
        g.command(f"aoe label {uuid(rect)}")
        if new >= top:
            stop(g, rect, vs)


def charge(g, key, vs, full, share, name):
    """Take the share of the cost full of the repair of key from the stock, in whole units (the rest is owed). Returns
    False and stops the villagers vs with a chat line when the stock is too small."""
    import combat
    owed = g.repair_owed.setdefault(key, {})
    due = {r: owed.get(r, 0.0) + v * share for r, v in full.items()}
    pay = {r: math.floor(v + 1e-9) for r, v in due.items()}           # no unit lost to a float sum
    if any(g.stock[r] < v for r, v in pay.items()):
        stop(g, key, vs, f"Not enough resources to repair the {combat.pretty(name).lower()}.")
        return False
    for r, v in pay.items():
        if v:
            g.stock[r] -= v
            g.command(f"scoreboard players remove {r.capitalize()} {g.board} {v}")
    g.repair_owed[key] = {r: v - pay[r] for r, v in due.items()}
    return True


def unit_tick(g, u, vs, dt):
    """dt AoE2 seconds of repair of siege unit or ship u by the villagers vs: its crew gets Health back, the stock pays
    half the training cost for the full hit points. It stops when the unit is full, dead or moves."""
    import build, train                                            # build and train import gather
    name, h, pos = g.soldiers.get(u), unit_hp(g, u), g.pos(u)
    start = vars(g).get("repair_at", {}).get(u)
    if not name or not h or not 0 < h[0] < h[1] or not pos or not start or math.dist(pos, start) > STILL:
        stop(g, u, vs)                                             # full, dead, or it moves (AoE2)
        return
    cart = name in build.MOVES                                     # a mule cart is a building: its rate and cost (#2504)
    gain = h[1] - h[0] if g.aegis else min(h[1] - h[0], rate(g, vs) * (1 if cart else SIEGE) * dt)
    new = min(h[1], round(h[0] + gain, 2))                         # Health in steps of 0.01: pay for those
    full = cost(g, name) if cart else {r: v * SHARE for r, v in train.price(g, name).items()} if name in train.COSTS else {}
    #                                                                a unit: no Georgian bonus (#1929)
    if not charge(g, u, vs, full, (new - h[0]) / h[1], name):
        return
    g.command(body(g, u) + f"data modify entity @s Health set value {new}f")
    g.command(f"aoe label {u}")                                   # the hearts: a data change fires no event (#1521)
    if new >= h[1]:
        stop(g, u, vs)


def stop(g, rect, vs, text=None):
    """The villagers vs stop the repair of the building rect, with the red chat line text."""
    for v in vs:
        if v.uuid in g.villagers:
            vars(g).get("repairs", {}).pop(v.uuid, None)
            g.set(v, "idle")
        else:                                                      # a Serjeant: it stands
            vars(g).get("mending", {}).pop(v.uuid, None)
    vars(g).get("repair_hp", {}).pop(rect, None)
    if text:
        g.command(f"tellraw @a[team=p{g.player}] " + json.dumps({"text": text, "color": "red"}))
