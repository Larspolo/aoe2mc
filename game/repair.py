"""Repairs in the game program (#1330, epic #1329). A right click with selected villagers on an own damaged building
sends them to it: they walk next to it (Minecraft path finding, gather.Gather.go, as builders) and repair it, as in
AoE2 DE (AoE2 wiki "Villager (Age of Empires II)", repairing): the first villager repairs 750 hit points per AoE2
minute, each other one 375 more (RATE, MORE), up to the full hit points. A click on an undamaged own building is not
a repair order: garrison.order gets it.

The repair takes half the build cost (build.price, with the bonuses of the civilization) for the full hit points, in
the share of the hit points that it gives back; a town center takes double its wood and no stone (550 wood for the
full repair). The stock pays whole units as the repair goes on. With too few resources the repair stops with a chat
line, and the villagers stand idle. A building with no build cost (build.COSTS) repairs free.

Minecraft feature: the plugin keeps the hit points of a building in the scoreboard aoe_hp of its target entity
(combat.building, #660), so `scoreboard players get/set <uuid> aoe_hp` reads and sets them, and `aoe label` shows the
new hearts of its name line.

    repair.order(g, player, cell)   # gather.Gather.click: the selection repairs the damaged building at cell
    repair.tick(g, dt)              # gather.Gather.step: dt AoE2 seconds of repair
"""
import json
import math
import re

RATE = 750 / 60             # hit points per AoE2 second of the first repairer
MORE = 375 / 60             # hit points per AoE2 second of each other repairer
SHARE = 0.5                 # of the build cost for the full hit points


def buildings(g):
    """{block footprint (x0, x1, z0, z1): name} of the own buildings with AoE2 hit points (a target entity): the start
    ones and the complete construction sites."""
    import combat                                                  # combat imports gather, gather imports this module
    out = {(x0, x1, z0, z1): o["name"] for o in g.data["objects"] if o["kind"] == "building" and o["name"] in combat.BUILDINGS
           and o["player"] == g.player and "footprint" in o for x0, z0, x1, z1 in [o["footprint"]]}
    return out | {tuple(s["footprint"]): s["name"] for s in g.sites
                  if s.get("done") and s["player"] == g.player and s["name"] in combat.BUILDINGS}


def uuid(rect):
    """The UUID of the target entity of the building with block footprint rect."""
    import combat
    return combat.target_uuid([rect[0], rect[2], rect[1], rect[3]])


def hp(g, rect):
    """The hit points of the building rect (the score aoe_hp of its target entity), or None when it has none."""
    m = re.search(r" has (-?\d+) ", g.command(f"scoreboard players get {uuid(rect)} aoe_hp"))
    return int(m[1]) if m else None


def cost(g, name):
    """{resource: amount} for the full hit points of building name."""
    import build                                                   # build imports gather
    if name not in build.COSTS:
        return {}
    price = build.price(g, name)
    if name == "TOWN_CENTER":                                      # AoE2 wiki: 550 wood (double the wood), no stone
        return {"wood": price.get("wood", 0) * 2}
    return {r: v * SHARE for r, v in price.items()}


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
    goals = g.map.around({(x, z) for x in range(x0, x1) for z in range(z0, z1)})
    g.repairs = vars(g).get("repairs", {})
    for u in who:
        v = g.villagers[u]
        for t in [t for t, f in g.farmers.items() if f == u]:
            del g.farmers[t]
        v.tree, v.site, v.prey = None, None, None
        g.repairs[u] = rect
        g.task(v, "BUILDER")
        g.go(v, "to_repair", goals)
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
    homes, g.repair_owed = buildings(g), vars(g).get("repair_owed", {})
    for rect, vs in sorted(work.items(), key=lambda kv: kv[0]):
        now = hp(g, rect) if rect in homes else None
        top = combat.stats(homes[rect]).hp if rect in homes else 0
        if not now or now >= top:                                  # fallen or full: the work ends
            stop(g, rect, vs)
            continue
        gain = top - now if g.aegis else min(top - now, (RATE + MORE * (len(vs) - 1)) * dt)
        owed = g.repair_owed.setdefault(rect, {})
        due = {r: owed.get(r, 0.0) + v * gain / top for r, v in cost(g, homes[rect]).items()}
        pay = {r: math.floor(v) for r, v in due.items()}
        if any(g.stock[r] < v for r, v in pay.items()):
            stop(g, rect, vs, f"Not enough resources to repair the {combat.pretty(homes[rect]).lower()}.")
            continue
        for r, v in pay.items():
            if v:
                g.stock[r] -= v
                g.command(f"scoreboard players remove {r.capitalize()} {g.board} {v}")
        g.repair_owed[rect] = {r: v - pay[r] for r, v in due.items()}
        g.repair_hp = vars(g).get("repair_hp", {})                 # the fractions of a hit point
        whole = g.repair_hp.get(rect, 0.0) + gain
        g.repair_hp[rect] = whole - math.floor(whole)
        new = min(top, now + math.floor(whole))
        g.command(f"scoreboard players set {uuid(rect)} aoe_hp {new}")
        g.command(f"aoe label {uuid(rect)}")
        if new >= top:
            stop(g, rect, vs)


def stop(g, rect, vs, text=None):
    """The villagers vs stop the repair of the building rect, with the red chat line text."""
    for v in vs:
        g.repairs.pop(v.uuid, None)
        g.set(v, "idle")
    vars(g).get("repair_hp", {}).pop(rect, None)
    if text:
        g.command(f"tellraw @a[team=p{g.player}] " + json.dumps({"text": text, "color": "red"}))
