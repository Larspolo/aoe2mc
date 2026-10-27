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

An injured unit in a garrison gets its hit points back, as in AoE2 DE (#1262, AoE2 wiki "Garrison"): 0.2 per second in
a castle, 0.1 in a town center or tower (HEAL), 6 times as fast after Herbal Medicine (HERBAL, #1585). Siege units and
ships do not heal (monk.healable). The same Health change as the monk heal (monk.py); a full unit stays full inside
(Invulnerable), so it is read only once (g.whole).

    garrison.heal(g, dt)                # gather.Gather.step: dt AoE2 seconds of healing

The live replay (game/replay.py, #809) uses SIZES, cell(), enter() and leave().
"""
import json
import math

import table
from aoe2mc import GARRISONED

ROWS = table.load("buildings.jsonl")                            # the keys "garrison" and "arrows" (#2034)

SIZES = {r["name"]: r["garrison"] for r in ROWS if "garrison" in r}   # units inside a complete building, as in AoE2
HEAL = {"CASTLE": 0.2}                                           # hit points per AoE2 second inside, else 0.1
HERBAL = 6                  # Herbal Medicine: units inside heal 6 times as fast (AoE2 DE wiki, #1585)
HEAL_EVERY = 5.0            # AoE2 seconds between two heal passes (fewer commands)
BASE = {r["name"]: r["arrows"] for r in ROWS if "arrows" in r}   # arrows of an empty building (AoE2 wiki), else 1
FISHER = "FISHING_SHIP"     # the only unit that goes into a dock (#1949)
DOOR = 2.5                  # blocks from the door cell: there a unit goes in
UNGARRISON = (7, "oak_door", "Ungarrison", "Click: all units come out")   # a slot of the first row, before RALLY
SPARE = 26                  # the last slot of the third row: UNGARRISON of a building with an item in slot 7 (the
                            # demolition raft of the dock #1949, Illumination of the fortified church #1948)
INSIDE = "{Invulnerable:1b,NoAI:1b,CustomNameVisible:0b}"         # the NBT of a garrisoned unit (#807)
OUTSIDE = "{Invulnerable:0b}"                                     # NoAI stays: the next order turns on the AI
CREW = "{Invulnerable:1b}"                                        # the crew of a ship in a dock keeps its AI (#1949)


def holders(g):
    """{block footprint (x0, x1, z0, z1): building entry of aoe2mc.json} of the own buildings that take a garrison:
    the start ones and the complete construction sites."""
    out = {(x0, x1, z0, z1): o for o in g.data["objects"] if o["kind"] == "building" and o["name"] in SIZES
           and o["player"] == g.player and "footprint" in o for x0, z0, x1, z1 in [o["footprint"]]}
    return out | {tuple(s["footprint"]): s for s in g.sites if s["name"] in SIZES and s.get("done")}


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
    and 1 more for each villager or foot archer (an archer that is not cavalry, a camel or an elephant), as in AoE2. A bombard tower shoots one cannon
    ball (#1375). A dock: 1 for each fishing ship, at most SIZES (AoE2 DE: up to 5 arrows, #1949). A fortified church:
    1 for each villager, no soldier (AoE2 DE: villagers and relics, #1948)."""
    import combat                                                  # combat imports gather
    if building == "BOMBARD_TOWER":
        return 1
    if building == "DOCK":
        return min(SIZES["DOCK"], sum(n.startswith(FISHER) for n in names))
    if building == "FORTIFIED_CHURCH":
        return sum(n.startswith("VILLAGER") for n in names)
    riders = {combat.CAV, combat.CAM, combat.ELE}
    return BASE.get(building, 1) * factor + sum(n.startswith("VILLAGER") or combat.ARC in (c := set(combat.stats(n).classes)) and not c & riders
                   for n in names)


def arrows_command(g, rect):
    """The plugin command that gives the building rect the arrows of its garrison (#1113)."""
    import civs, combat
    names = ["VILLAGER" if u in g.villagers else g.soldiers.get(u, "") for u in g.garrisons.get(rect, [])]
    building = holders(g).get(rect, {}).get("name")
    return f"aoe arrows {combat.target_uuid([rect[0], rect[2], rect[1], rect[3]])} {arrows(building, names, civs.arrows(g, building))}"


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
    for u in sorted(g.selected):
        if (v := g.villagers.get(u)) is not None:                  # the villager stops its work
            v.state, v.path, v.goal, v.site = "garrison", [], None, None
        name = "VILLAGER" if u in g.villagers else g.soldiers.get(u, "")
        ai.move(g, u, name, g.map.T, x + 0.5, g.map.y(x, z), z + 0.5, ai.NORMAL * train.speed(g, name))
        g.entering[u] = rect
    g.mark(player, {to})
    return rect


def dock_order(g, player, rect):
    """The selected fishing ships sail to the water next to the dock rect and go in (#1949). A boat has no Minecraft
    path finding: it sails with the /tp steps of fleet.py. Returns rect, or None when no fishing ship is selected."""
    import fleet                                                   # fleet imports gather, gather imports this module
    boats = [v for u in sorted(g.selected) if g.soldiers.get(u, "").startswith(FISHER) and (v := fleet.ship(g, u))]
    pier = fleet.pier(g, rect)
    if not boats or not pier or not g.paper:
        return None
    for v in boats:
        v.tree, v.site, v.prey = None, None, None                  # it stops its fishing; the load stays
        if fleet.sail_to(g, v, "garrison", pier):
            g.entering[v.uuid] = rect
    g.mark(player, {(rect[0], rect[2]), (rect[1] - 1, rect[3] - 1)})
    return rect


def tick(g):
    """The units at the door of their building go in (a full building: they stay at the door), and the units of a
    fallen building come out (only the plugin takes the hit points of a building)."""
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
    if len(units) >= SIZES[o["name"]]:                             # full: it stays at the door, as in AoE2
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
        rate = HEAL.get(homes[rect]["name"], 0.1) * herbal if rect in homes else 0.0
        for u in us:
            if u in g.whole or not rate or not monk.healable(names.get(u, "VILLAGER")) or not (h := monk.health(g, u)):
                continue
            if h[0] >= h[1]:
                g.whole.add(u)
                continue
            g.command(f"data modify entity {u} Health set value {round(min(h[1], h[0] + rate * dt), 2)}f")
