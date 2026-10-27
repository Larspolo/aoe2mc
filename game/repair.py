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
the repair, as in AoE2: the villagers stand idle.

Minecraft feature: the plugin keeps the hit points of a building in the scoreboard aoe_hp of its target entity
(combat.building, #660), so `scoreboard players get/set <uuid> aoe_hp` reads and sets them, and `aoe label` shows the
new hearts of its name line. A siege unit has its hit points as the Health of its crew (the passenger of the minecart,
AoePlugin "stats", #836): `execute as <cart> on passengers run data get/modify entity @s Health`.

    repair.order(g, player, cell)   # gather.Gather.click: the selection repairs the damaged building at cell
    repair.unit_order(g, player, u) # gather.Gather.click: the selection repairs the damaged siege unit u
    repair.tick(g, dt)              # gather.Gather.step: dt AoE2 seconds of repair
"""
import json
import math
import re

RATE = 750 / 60             # hit points per AoE2 second of the first repairer
MORE = 375 / 60             # hit points per AoE2 second of each other repairer
SHARE = 0.5                 # of the build cost for the full hit points
SIEGE = 0.25                # the rate of a siege unit: a share of the building rate (AoE2 wiki "Villager")
STILL = 0.5                 # blocks: a siege unit that moved more stops the repair


def owners(g):
    """{block footprint (x0, x1, z0, z1): (name, player)} of the own and the allied buildings with AoE2 hit points (a
    target entity): the start ones and the complete construction sites of the player and of the bots (#1361)."""
    from gather import allied                                      # gather imports this module
    import combat
    mine = {g.player} | {int(p) for p in g.players if int(p) and allied(g.players, g.player, int(p))}   # no Gaia
    out = {(x0, x1, z0, z1): (o["name"], o["player"]) for o in g.data["objects"] if o["kind"] == "building"
           and o["name"] in combat.BUILDINGS and o["player"] in mine and "footprint" in o for x0, z0, x1, z1 in [o["footprint"]]}
    return out | {tuple(s["footprint"]): (s["name"], s["player"]) for s in g.sites + [s for b in g.bots for s in b.g.sites]
                  if s.get("done") and s["player"] in mine and s["name"] in combat.BUILDINGS}


def buildings(g):
    """{block footprint (x0, x1, z0, z1): name} of the own and the allied buildings with AoE2 hit points (owners)."""
    return {r: n for r, (n, _) in owners(g).items()}


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
    import build                                                   # build imports gather
    if name not in build.COSTS:
        return {}
    price = build.price(g, name, player)
    if name == "TOWN_CENTER":                                      # AoE2 wiki: 550 wood (double the wood), no stone
        return {"wood": price.get("wood", 0) * 2}
    return {r: v * SHARE for r, v in price.items()}


def crew(u):
    """The prefix of a command that runs on the crew of siege unit u (it has the hit points)."""
    return f"execute as {u} on passengers run "


def unit_hp(g, u):
    """(Health, max_health) of siege unit u, or None when the server gives no number (dead, unloaded)."""
    from gather import NUMBER                                      # gather imports this module
    hp = re.findall(NUMBER, g.command(crew(u) + "data get entity @s Health").rsplit(":", 1)[-1])
    top = re.findall(r"(-?[\d.]+)", g.command(crew(u) + "attribute @s minecraft:max_health get").rsplit(" is ", 1)[-1])
    return (float(hp[0]), float(top[0])) if hp and top else None


def send(g, who, key, goals):
    """The villagers who walk to goals and repair key (a building footprint, or the UUID of a siege unit)."""
    g.repairs = vars(g).get("repairs", {})
    for u in who:
        v = g.villagers[u]
        for t in [t for t, f in g.farmers.items() if f == u]:
            del g.farmers[t]
        v.tree, v.site, v.prey = None, None, None
        g.repairs[u] = key
        g.task(v, "BUILDER")
        g.go(v, "to_repair", goals)


def unit_order(g, player, u):
    """The selected villagers repair the own damaged siege unit u. Returns True, or False (no own siege unit, it has
    its full hit points, or no villager is selected)."""
    import units                                                   # the converter's table (gather puts it on the path)
    name, who = g.soldiers.get(u), sorted(g.selected & g.villagers.keys())
    if not name or not units.siege(name) or not who or not (pos := g.pos(u)):
        return False
    h = unit_hp(g, u)
    if not h or not 0 < h[0] < h[1]:
        return False
    cell = (math.floor(pos[0]), math.floor(pos[2]))
    vars(g).setdefault("repair_at", {})[u] = pos                   # a move from here stops the repair
    send(g, who, u, g.map.around({cell}))
    g.mark(player, {cell})
    return True


def order(g, player, cell):
    """The selected villagers repair the own damaged building with the block cell (x, z) in its footprint. Returns its
    footprint, or None (no such building, it has its full hit points, or no villager is selected)."""
    import combat
    homes = buildings(g)
    rect = next((r for r in homes if cell and r[0] <= cell[0] < r[1] and r[2] <= cell[1] < r[3]), None)
    who = sorted(g.selected & g.villagers.keys())
    if rect is None or not who or not 0 < (hp(g, rect) or 0) < combat.stats(homes[rect]).hp:
        return None
    x0, x1, z0, z1 = rect
    send(g, who, rect, g.map.around({(x, z) for x in range(x0, x1) for z in range(z0, z1)}))
    g.mark(player, {(x0, z0), (x1 - 1, z1 - 1)})
    return rect


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
    if not work:
        return
    import combat
    homes, g.repair_owed = owners(g), vars(g).get("repair_owed", {})
    for rect, vs in sorted(work.items(), key=lambda kv: (isinstance(kv[0], str), kv[0])):
        if isinstance(rect, str):                                  # a siege unit (#1331)
            unit_tick(g, rect, vs, dt)
            continue
        now = hp(g, rect) if rect in homes else None
        name, player = homes.get(rect, (None, None))
        top = combat.stats(name).hp if rect in homes else 0
        if not now or now >= top:                                  # fallen or full: the work ends
            stop(g, rect, vs)
            continue
        gain = top - now if g.aegis else min(top - now, (RATE + MORE * (len(vs) - 1)) * dt)
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
    """dt AoE2 seconds of repair of siege unit u by the villagers vs: its crew gets Health back, the stock pays half
    the training cost for the full hit points. It stops when the unit is full, dead or moves."""
    import train                                                   # train imports gather
    name, h, pos = g.soldiers.get(u), unit_hp(g, u), g.pos(u)
    start = vars(g).get("repair_at", {}).get(u)
    if not name or not h or not 0 < h[0] < h[1] or not pos or not start or math.dist(pos, start) > STILL:
        stop(g, u, vs)                                             # full, dead, or it moves (AoE2)
        return
    gain = h[1] - h[0] if g.aegis else min(h[1] - h[0], (RATE + MORE * (len(vs) - 1)) * SIEGE * dt)
    new = min(h[1], round(h[0] + gain, 2))                         # Health in steps of 0.01: pay for those
    full = {r: v * SHARE for r, v in train.price(g, name).items()} if name in train.COSTS else {}
    if not charge(g, u, vs, full, (new - h[0]) / h[1], name):
        return
    g.command(crew(u) + f"data modify entity @s Health set value {new}f")
    if new >= h[1]:
        stop(g, u, vs)


def stop(g, rect, vs, text=None):
    """The villagers vs stop the repair of the building rect, with the red chat line text."""
    for v in vs:
        g.repairs.pop(v.uuid, None)
        g.set(v, "idle")
    vars(g).get("repair_hp", {}).pop(rect, None)
    if text:
        g.command(f"tellraw @a[team=p{g.player}] " + json.dumps({"text": text, "color": "red"}))
