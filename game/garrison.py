"""Garrisons in the game program (#808, part of #793). An order of the selected units on an own building with room
sends them into it, as in AoE2: they walk to its door with the plugin (`aoe moveto`), then stand on the free cells
of its ground floor, in a town center of its hall upstairs (#2054; "inside" in aoe2mc.json, the cells of the converter,
#807), in the state of a garrisoned unit of the converter: Invulnerable, NoAI, no visible name and the tag
aoe2mc.GARRISONED. They leave the selection, and orders skip them. The menu item UNGARRISON of the building
(train.show) lets them out next to the door, and so does the fall of the building (its target entity of the plugin is
gone), alive, as in AoE2.

    garrison.order(g, player, cell)     # gather.Gather.click: the selection goes into the building at cell
    garrison.tick(g)                    # gather.Gather.step: units at the door go in, a fallen building lets them out
    garrison.out(g, rect)               # the menu item

Each garrisoned villager or foot archer adds one arrow to the shot of its town center, tower or castle, as in AoE2
(#1113): `aoe arrows` of the plugin. An empty town center shoots no arrow, a castle 5 (BASE, #1201).
A dock takes only fishing ships, at most 5 (#1949): they sail to the water next to it with the /tp steps of fleet.py
(a boat has no Minecraft path finding), and each one adds an arrow; an empty dock does not shoot, as in AoE2 DE.
A Gurjara mill takes only herdable animals, at most 10 (civs.HERD_FOOD, BY, #2342), and they make food with no end:
15 × ln(F / 200 + 1) per AoE2 minute for F food of all animals in own mills (AoE2 DE wiki "Gurjaras"). An animal inside
cannot be captured (herd.tick).

    garrison.pasture(g, dt)             # gather.Gather.step: dt AoE2 seconds of the food of the animals in mills

An injured unit in a garrison gets its hit points back, as in AoE2 DE (#1262, AoE2 wiki "Garrison"): 0.2 per second in
a castle, 0.1 in a town center or tower (HEAL), 6 times as fast after Herbal Medicine (HERBAL, #1585). Siege units and
ships do not heal (monk.healable). A mule cart gets a share of its hit points per AoE2 minute back (REPAIR: 24 % in a town
center or tower, 48 % in a castle, CART_HERBAL times as fast after Herbal Medicine, AoE2 DE wiki "Mule Cart", #2505),
for free. The same Health change as the monk heal (monk.py); a full unit stays full inside
(Invulnerable), so it is read only once (g.whole).

    garrison.heal(g, dt)                # gather.Gather.step: dt AoE2 seconds of healing

The live replay (game/replay.py, #809) uses SIZES, cell(), enter() and leave().
"""
import json
import math

import civs
import ruins
import table
from aoe2mc import GARRISONED, MADE_INSIDE

ROWS = table.load("buildings.jsonl")                            # the keys "garrison" and "arrows" (#2034)

SIZES = {r["name"]: r["garrison"] for r in ROWS if "garrison" in r}   # units inside a complete building, as in AoE2
BY = {r["name"]: tuple(r["garrison_by"]) for r in ROWS if "garrison_by" in r}   # only these units go in (Khmer house)
HEAL = {"CASTLE": 0.2}                                           # hit points per AoE2 second inside, else 0.1
HERBAL = 6                  # Herbal Medicine: units inside heal 6 times as fast (AoE2 DE wiki, #1585)
REPAIR = {r["name"]: (r["repair"], r.get("repair_in", {})) for r in ROWS if "repair" in r}   # a cart: the share of its
CART_HERBAL = 3             # hit points per AoE2 minute in any building, and in some; Herbal Medicine: 3 times (#2505)
HEAL_EVERY = 5.0            # AoE2 seconds between two heal passes (fewer commands)
BASE = {r["name"]: r["arrows"] for r in ROWS if "arrows" in r}   # arrows of an empty building (AoE2 wiki), else 1
FISHER = "FISHING_SHIP"     # the only unit that goes into a dock (#1949)
DOOR = 2.5                  # blocks from the door cell: there a unit goes in
UNGARRISON = (7, "oak_door", "Ungarrison", "Click: all units come out")   # a slot of the first row, before RALLY
BELL = (24, "bell", "Ring Town Bell", "Click: all villagers seek shelter")   # town center: first free slot after the policies (#3419)
BACK = (24, "bell", "All Back to Work", "Click: the villagers of the bell go back to work")   # after the bell (#3420)
SPARE = 26                  # the last slot of the third row: UNGARRISON of a building with an item in slot 7 (the
                            # demolition raft of the dock #1949, Illumination of the fortified church #1948)
INSIDE = "{Invulnerable:1b,NoAI:1b,CustomNameVisible:0b}"         # the NBT of a garrisoned unit (#807)
OUTSIDE = "{Invulnerable:0b}"                                     # NoAI stays: the next order turns on the AI
CREW = "{Invulnerable:1b}"                                        # the crew of a ship in a dock keeps its AI (#1949)


def size(g, name):
    """The units inside a complete building name of the player of g: the bonus of its civilization (civs.GARRISON: a
    Khmer house 5, Teuton towers twice, #2117; civs.HERD_FOOD: a Gurjara mill 10 animals, #2342), else SIZES, else 0."""
    herd = civs.HERD_FOOD.get(civs.civ(g), {}).get(name, (0,))[0]
    return civs.GARRISON.get(civs.civ(g), {}).get(name, herd or SIZES.get(name, 0))


def holders(g):
    """{block footprint (x0, x1, z0, z1): building entry of aoe2mc.json} of the own buildings that take a garrison:
    the start ones and the complete construction sites, not the fallen ones (ruins.py)."""
    out = {(x0, x1, z0, z1): o for o in g.data["objects"] if o["kind"] == "building" and size(g, o["name"])
           and o["player"] == g.player and "footprint" in o and not ruins.fallen(g, o) for x0, z0, x1, z1 in [o["footprint"]]}
    return out | {tuple(s["footprint"]): s for s in g.sites if size(g, s["name"]) and s.get("done")}


def start(g):
    """{footprint: [UUID]}: the units that the converter put inside the own buildings (aoe2mc.json "holder")."""
    refs = {o["ref"]: rect for rect, o in holders(g).items() if o.get("ref") is not None}
    out = {}
    for o in g.data["objects"]:
        if o["kind"] == "unit" and o.get("uuid") and o.get("holder") in refs:
            out.setdefault(refs[o["holder"]], []).append(o["uuid"])
    return out


def arrows(building, names, factor=1):
    """The arrows of one shot of the building with the units `names` inside: its BASE (times factor: civs.arrows, #2178),
    and 1 more for each villager or foot archer (an archer that is not cavalry, a camel or an elephant), as in AoE2. A
    bombard tower shoots one cannon ball (#1375). A dock: 1 for each fishing ship, at most SIZES (AoE2 DE: up to 5 arrows, #1949). A fortified church:
    1 for each villager, no soldier (AoE2 DE: villagers and relics, #1948). A building with no attack: none."""
    import civs, combat                                            # combat imports gather
    if building == "BOMBARD_TOWER":
        return 1
    if building == "DOCK":
        return min(SIZES["DOCK"], sum(n.startswith(FISHER) for n in names))
    if building == "FORTIFIED_CHURCH":
        return sum(n.startswith("VILLAGER") for n in names)
    if building in combat.BUILDINGS and not combat.BUILDINGS[building].attack:   # a Khmer house does not shoot (#2117)
        return 0
    return BASE.get(building, 1) * factor + sum(n.startswith("VILLAGER") or combat.ARC in (s := combat.stats(n)).classes and not civs.mounted(s)
                   for n in names)


def arrows_command(g, rect):
    """The plugin command that gives the building rect the arrows of its garrison (#1113)."""
    import civs, combat
    names = ["VILLAGER" if u in g.villagers else g.soldiers.get(u, "") for u in g.garrisons.get(rect, [])]
    import train                                                   # train imports this module
    building = holders(g).get(rect, {}).get("name")
    more = train.value("arrows", vars(g).get("upgraded", {}).get(rect), 0)   # the Defensive Town Center (#2497)
    return f"aoe arrows {combat.target_uuid([rect[0], rect[2], rect[1], rect[3]])} {arrows(building, names, civs.arrows(g, building)) + more}"


def ungarrison(building):
    """The menu item UNGARRISON of the building, in its slot: SPARE when a menu item of the building is in its slot."""
    import train                                                   # train imports garrison
    used = {train.ITEMS[n][0] for n in train.TRAINS.get(building, ())}
    return (SPARE if UNGARRISON[0] in used else UNGARRISON[0], *UNGARRISON[1:])


def door(g, rect):
    """The block cell in front of the door of the building rect: the middle of the free cells on its south side."""
    return next(iter(g.map.front(rect)), None)


def order(g, player, cell):
    """The selected units go into the own building with the block cell (x, z) in its footprint. Returns its footprint,
    or None (no such building, nothing selected, or no plugin): the click is then not a garrison order."""
    homes = holders(g)
    rect = next((r for r in homes if cell and r[0] <= cell[0] < r[1] and r[2] <= cell[1] < r[3]), None)
    if rect is not None and homes[rect]["name"] == "DOCK":
        return dock_order(g, player, rect)
    if rect is None or not g.selected or not g.paper or (to := door(g, rect)) is None:
        return None
    import ai, train                                               # ai and train import gather, gather imports this module
    x, z = to
    by, flock = BY.get(homes[rect]["name"]), vars(g).get("flock", set())
    units = [u for u in sorted(g.selected) if (unit_name(g, u).startswith(by) if by else u not in flock)]
    if not units:                                                  # a soldier on a Khmer house, a sheep on a tower: no
        return None                                                # garrison order
    g.new_order(units)
    for u in units:
        if (v := g.villagers.get(u)) is not None:                  # the villager stops its work
            v.state, v.path, v.goal, v.site = "garrison", [], None, None
        name = unit_name(g, u)
        ai.move(g, u, name, g.map.T, x + 0.5, g.map.y(x, z), z + 0.5, ai.NORMAL * train.speed(g, name, u))
        g.entering[u] = rect
    g.mark(player, {to})
    return rect


def bell(g, player, chosen=None):
    """Ring the town bell (#3419, AoE2 DE wiki "Town Bell"): each own villager and mule cart walks into the nearest own
    building of holders() with room left within the line of sight of a town center, the same walk as order(); one with no such building
    keeps working. Not a dock or a building of BY: they take only ships or animals. Returns the sent units.
    chosen: only these units go, with no bell sound (Seek Shelter of the selection, #3440)."""
    import ai, combat, train                                       # ai and train import gather, gather imports this module
    homes = {r: o for r, o in holders(g).items() if o["name"] != "DOCK" and o["name"] not in BY and door(g, r) is not None}
    room = {r: size(g, o["name"]) - len(g.garrisons.get(r, [])) - sum(e == r for e in g.entering.values()) for r, o in homes.items()}
    units = sorted(set(g.villagers) | {u for u, n in g.soldiers.items() if n == "MULE_CART"})
    units = units if chosen is None else [u for u in units if u in chosen]
    pos, sent, far = g.positions(units), {}, combat.sight("TOWN_CENTER") * g.map.T
    for u in [u for u in units if u in pos and u not in g.entering and not any(u in us for us in g.garrisons.values())]:
        near = sorted((math.dist((pos[u][0], pos[u][2]), (d[0] + 0.5, d[1] + 0.5)), r) for r in homes if room[r] > 0 for d in [door(g, r)])
        if near and near[0][0] <= far:
            room[rect := near[0][1]] -= 1
            sent[u] = rect
    if sent:
        g.new_order(list(sent))
    work = vars(g).setdefault("bell_work", {})                     # the work before the bell: "All Back to Work" (#3420)
    for u in sent:
        if (v := g.villagers.get(u)) is not None and v.site is not None:
            work[u] = ("site", tuple(v.site["footprint"]))
        elif v is not None and v.tree is not None and v.state != "idle":
            work[u] = ("tile", tuple(v.tree))
    for u, rect in sent.items():
        if (v := g.villagers.get(u)) is not None:                  # the villager stops its work
            v.state, v.path, v.goal, v.site = "garrison", [], None, None
        x, z = door(g, rect)
        name = unit_name(g, u)
        ai.move(g, u, name, g.map.T, x + 0.5, g.map.y(x, z), z + 0.5, ai.NORMAL * train.speed(g, name, u))
        g.entering[u] = rect
    if chosen is not None:
        text = f"{len(sent)} villagers seek shelter" if units else "No villager is selected."
    else:
        text = f"The town bell rings: {len(sent)} villagers seek shelter" if units else "You have no villagers."
        g.command(f"playsound minecraft:block.bell.use master {player}")
    g.command(f"tellraw {player} " + json.dumps({"text": text, "color": "gray"}))
    return sent


def bell_item(g):
    """The item of slot 24 of a town center: "All Back to Work" while villagers of the bell have work stored, else BELL."""
    return BACK if vars(g).get("bell_work") else BELL


def all_back(g, player):
    """The second click of the bell (#3420, AoE2 DE "All Back to Work"): the buildings with villagers of the bell let
    their units out (out() sends them back to work), and the villagers that still walk to a door go back to work too."""
    work = vars(g).get("bell_work", {})
    for rect in [r for r, us in getattr(g, "garrisons", {}).items() if work.keys() & set(us)]:
        out(g, rect)
    back(g, [u for u in work if u in vars(g).get("entering", {})])
    work.clear()
    g.command(f"tellraw {player} " + json.dumps({"text": "All back to work", "color": "gray"}))


def back(g, units):
    """Send each villager of units with stored work of the bell back to it: its tree, mine, bush or farm (Gather.send;
    a taken farm: the nearest free one), or its construction site while it is not complete (Gather.build). A villager
    whose work is gone stays idle."""
    work = vars(g).get("bell_work", {})
    for u in units:
        if (job := work.pop(u, None)) is None or u not in g.villagers:
            continue
        kind, where = job
        if kind == "site":
            site = next((s for s in g.sites if tuple(s["footprint"]) == where and s["progress"] < 1), None)
            if site is not None:
                g.build(site, {u})
        elif where in g.map.trees or g.map.resource(where) != "wood":     # a farm, bush or mine is food or gold
            g.send(where, {u})


def open_menu(g, player, cell):
    """Open the menu of an own building with no training menu (a tower, a keep, a house of the Khmer), at the block cell
    (x, z), when units are inside: its item UNGARRISON lets them out (#2970). Returns its footprint, or None."""
    import build, demolish, menu, train                            # train imports this module
    rect = next((r for r in holders(g) if cell and r[0] <= cell[0] < r[1] and r[2] <= cell[1] < r[3]), None)
    if rect is None or not getattr(g, "garrisons", {}).get(rect) or train.home(g, cell) is not None:
        return None
    name = holders(g)[rect]["name"]

    def click(p, slot, shift):
        if slot == ungarrison(name)[0]:
            out(g, rect)
            menu.close(g, p)
        elif slot == demolish.ITEM[0]:                             # the building falls (#3452)
            demolish.delete(g, p, rect)
    menu.show(g, player, build.pretty(name), [ungarrison(name)] + [demolish.ITEM] * demolish.shown(g, rect), click)
    return rect


def unit_name(g, u):
    """The AoE2 name of own unit u: "VILLAGER", a soldier, or a herdable animal (gather.Gather.flock, #2342)."""
    return "VILLAGER" if u in g.villagers else g.soldiers.get(u) or vars(g).get("prey", {}).get(u, "")


def dock_order(g, player, rect):
    """The selected fishing ships sail to the water next to the dock rect and go in (#1949). A boat has no Minecraft
    path finding: it sails with the /tp steps of fleet.py. Returns rect, or None when no fishing ship is selected."""
    import fleet                                                   # fleet imports gather, gather imports this module
    boats = [v for u in sorted(g.selected) if g.soldiers.get(u, "").startswith(FISHER) and (v := fleet.ship(g, u))]
    pier = fleet.pier(g, rect)
    if not boats or not pier or not g.paper:
        return None
    g.new_order({v.uuid for v in boats})
    for v in boats:
        v.tree, v.site, v.prey = None, None, None                  # it stops its fishing; the load stays
        if fleet.sail_to(g, v, "garrison", pier):
            g.entering[v.uuid] = rect
    g.mark(player, {(rect[0], rect[2]), (rect[1] - 1, rect[3] - 1)})
    return rect


def adopt(g):
    """The units that a trigger made inside an own building ("Create Garrisoned Object", aoe2mc.MADE_INSIDE, #2764)
    join its garrison, so UNGARRISON lets them out. The tag goes: each unit joins once."""
    for u, (x, _, z) in g.where(None, f"@e[tag={MADE_INSIDE},tag=aoe2mc.p{g.player}]").items():
        rect = next((r for r in holders(g) if r[0] <= x < r[1] and r[2] <= z < r[3]), None)
        if rect is not None:
            g.garrisons.setdefault(rect, []).append(u)
            g.command(f"tag {u} remove {MADE_INSIDE}")


def tick(g):
    """The units at the door of their building go in (a full building: they stay at the door), and the units of a
    fallen building come out (only the plugin takes the hit points of a building)."""
    if g.paper:
        adopt(g)
    held = [r for r, us in g.garrisons.items() if us]
    if not g.entering and not (held and g.paper):
        return
    homes = holders(g)
    ships = vars(g).get("ships", {})
    for u, rect in [(u, r) for u, r in g.entering.items() if u in ships]:   # a fishing ship to a dock (#1949)
        v = ships[u]
        if rect not in homes or v.state != "garrison":             # the dock fell, or a new order
            del g.entering[u]
        elif not v.path:
            del g.entering[u]
            if v.cell in fleet_pier(g, rect):
                go_in(g, u, rect, homes[rect])
    if walkers := {u: r for u, r in g.entering.items() if u not in ships}:
        pos = g.positions(sorted(walkers))
        for u, rect in walkers.items():
            to = door(g, rect)
            if u not in pos or rect not in homes:                   # dead, or the building fell
                del g.entering[u]
            elif to is None or math.dist((pos[u][0], pos[u][2]), (to[0] + 0.5, to[1] + 0.5)) <= DOOR:
                del g.entering[u]
                go_in(g, u, rect, homes[rect])
    import combat                                                  # combat imports gather
    for rect in held if g.paper else []:                           # a start building has a target entity (combat.setup)
        o = homes.get(rect)
        if o is None or o.get("kind") == "building" and o["name"] in combat.BUILDINGS and "passed" not in g.command(
                f"execute if entity {combat.target_uuid([rect[0], rect[2], rect[1], rect[3]])}"):
            out(g, rect)


def go_in(g, u, rect, o):
    """Unit u stands inside the building rect (entry o of holders()), on its next free cell (the center without
    "inside" cells)."""
    units, boat = g.garrisons.setdefault(rect, []), vars(g).get("ships", {}).get(u)
    if len(units) >= size(g, o["name"]):                           # full: it stays at the door, as in AoE2
        if boat is None:
            g.command(f"aoe stop {u}")
        if (v := g.villagers.get(u) or boat) is not None:
            v.state = "idle"
        return
    x, y, z = cell(g.map, rect, o, len(units))
    if boat is not None and not (o.get("inside") or {}).get("cells"):   # a dock has no "ground": its water level
        y = g.map.sea(x, z)
    units.append(u)
    if boat is None:                                               # a boat has no AI
        g.command(f"aoe stop {u}")
    for c in enter(u, x, y, z) + crew(u, CREW) * (boat is not None) + [arrows_command(g, rect)]:
        g.command(c)
    if (v := g.villagers.get(u) or boat) is not None:
        v.pos, v.state, v.path = (x + 0.5, float(y), z + 0.5), "garrison", []
    if u in g.selected:                                            # it leaves the selection
        g.choose(g.selected - {u}, min(g.selected - {u}, default=None))


def out(g, rect):
    """All units of the building rect come out on the free cells next to it, the door side first. Returns them."""
    units = g.garrisons.pop(rect, [])
    if units and g.paper:
        g.command(arrows_command(g, rect))                         # one arrow again
    ring = g.map.front(rect) or [((rect[0] + rect[1]) // 2, rect[3])]
    ships = vars(g).get("ships", {})
    pier = sorted(fleet_pier(g, rect)) if any(u in ships for u in units) else []
    for k, u in enumerate(units):
        boat = ships.get(u)
        x, z = pier[k % len(pier)] if boat is not None and pier else ring[k % len(ring)]
        y = g.map.sea(x, z) if boat is not None and pier else g.map.y(x, z) or 0   # a ship goes onto the water
        for c in leave(u, x, y, z) + crew(u, OUTSIDE) * (boat is not None) + [f"aoe label {u}"]:   # the plugin shows
            g.command(c)                                                                     # the name line again
        if (v := g.villagers.get(u) or boat) is not None:
            v.pos, v.state = (x + 0.5, float(y), z + 0.5), "idle"
    if units:
        g.command(f"tellraw @a[team=p{g.player}] " + json.dumps({"text": f"{len(units)} units came out", "color": "gray"}))
    back(g, units)                                                 # the villagers of the bell go back to work (#3420)
    return units


def fleet_pier(g, rect):
    """The water cells next to the dock rect (fleet.pier)."""
    import fleet                                                   # fleet imports gather, gather imports this module
    return fleet.pier(g, rect)


def crew(u, nbt):
    """The commands that give the crew of ship u (the rider of its boat) the NBT of a unit inside or outside (#1949)."""
    return [f"execute as {u} on passengers run data merge entity @s {nbt}"]


def cell(m, rect, o, k):
    """(x, y, z) of the k-th unit inside the building rect (entry o, gather.Map m): its "inside" cells of aoe2mc.json
    one after the other, else the center of the footprint."""
    inside = o.get("inside") or {}
    cells = inside.get("cells") or [[(rect[0] + rect[1]) // 2, (rect[2] + rect[3]) // 2]]
    x, z = cells[k % len(cells)]
    return x, inside.get("y", m.y(x, z) or 0), z


def enter(u, x, y, z):
    """The commands that put unit u inside its building, at cell (x, z) and height y."""
    return [f"tp {u} {x + 0.5} {y} {z + 0.5}", f"data merge entity {u} {INSIDE}", f"tag {u} add {GARRISONED}"]


def leave(u, x, y, z):
    """The commands that put unit u out of its building, at cell (x, z) and height y."""
    return [f"tp {u} {x + 0.5} {y} {z + 0.5}", f"data merge entity {u} {OUTSIDE}", f"tag {u} remove {GARRISONED}"]


def inside(g):
    """The UUIDs of the units inside a building, a siege tower (siege_tower.py) or a transport ship (transport.py):
    orders and the selection skip them."""
    return {u for us in [*g.garrisons.values(), *vars(g).get("towers", {}).values(), *vars(g).get("cargo", {}).values()]
            for u in us}


def pasture(g, dt):
    """The herdable animals in the own mills make food for dt AoE2 seconds (civs.HERD_FOOD: Gurjaras, #2342): a × ln(F / b
    + 1) per AoE2 minute for F food of all of them (AoE2 DE wiki "Gurjaras"), with no end. The fractions add up."""
    import gather                                                  # gather imports this module
    pens = civs.HERD_FOOD.get(civs.civ(g), {})
    if not pens or not g.garrisons:
        return
    homes = holders(g)
    _, a, b = next(iter(pens.values()))
    f = sum(gather.hunt_food(g.prey.get(u, "")) for rect, us in g.garrisons.items()
            if homes.get(rect, {}).get("name") in pens for u in us if u in g.flock)
    if not f:
        return
    g.herd_food = vars(g).get("herd_food", 0.0) + a * math.log(f / b + 1) / 60 * dt
    if (n := int(g.herd_food)) > 0:
        g.herd_food -= n
        g.earn("food", n)


def heal(g, dt):
    """Give the injured units in the garrisons of g their hit points back for dt AoE2 seconds (HEAL)."""
    import monk                                                    # monk imports gather, gather imports this module
    inside = set().union(*g.garrisons.values())
    g.whole = vars(g).get("whole", set()) & inside                 # a unit that left can come back injured
    g.garrison_heal = vars(g).get("garrison_heal", 0.0) + dt if inside else 0.0   # no heal time for an empty one
    if g.garrison_heal < HEAL_EVERY:
        return
    dt, g.garrison_heal, homes = g.garrison_heal, 0.0, holders(g)
    names = {o["uuid"]: o["name"] for o in g.units if o.get("uuid") in g.villagers} | g.soldiers
    herbal = HERBAL if "HERBAL_MEDICINE" in getattr(g, "techs", ()) else 1
    for rect, us in sorted(g.garrisons.items()):
        home = homes[rect]["name"] if rect in homes else None
        rate = HEAL.get(home, 0.1) * herbal if home else 0.0
        for u in us:
            name = names.get(u, "VILLAGER")
            if u in g.whole or not home or not (name in REPAIR or monk.healable(name)) or not (h := monk.health(g, u)):
                continue
            if h[0] >= h[1]:
                g.whole.add(u)
                continue
            if name in REPAIR:                                     # a cart: a share of its hit points (#2505)
                share, more = REPAIR[name]
                up = more.get(home, share) * h[1] / 60 * (CART_HERBAL if herbal > 1 else 1)
            else:
                up = rate
            g.command(f"data modify entity {u} Health set value {round(min(h[1], h[0] + up * dt), 2)}f")
