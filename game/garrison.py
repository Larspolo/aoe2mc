"""Garrisons in the game program (#808, part of #793). An order of the selected units on an own building with room
sends them into it, as in AoE2: they walk to its door with the plugin (`aoe moveto`), then stand on the free cells
of its ground floor ("inside" in aoe2mc.json, the cells of the converter, #807), in the state of a garrisoned unit of
the converter: Invulnerable, NoAI, no visible name and the tag aoe2mc.GARRISONED. They leave the selection, and
orders skip them. The menu item UNGARRISON of the building (train.show) lets them out next to the door, and so does
the fall of the building (its target entity of the plugin is gone), alive, as in AoE2.

    garrison.order(g, player, cell)     # gather.Gather.click: the selection goes into the building at cell
    garrison.tick(g)                    # gather.Gather.step: units at the door go in, a fallen building lets them out
    garrison.out(g, rect)               # the menu item

The live replay (game/replay.py, #809) uses SIZES, cell(), enter() and leave().
"""
import json
import math

from aoe2mc import GARRISONED

SIZES = {                                                          # units inside a complete building, as in AoE2
    "BOMBARD_TOWER": 5,
    "CASTLE": 20,
    "GUARD_TOWER": 5,
    "KEEP": 5,
    "TOWN_CENTER": 15,
    "WATCH_TOWER": 5,
}
DOOR = 2.5                  # blocks from the door cell: there a unit goes in
UNGARRISON = (7, "oak_door", "Ungarrison", "Click: all units come out")   # a slot of the first row, before RALLY
INSIDE = "{Invulnerable:1b,NoAI:1b,CustomNameVisible:0b}"         # the NBT of a garrisoned unit (#807)
OUTSIDE = "{Invulnerable:0b}"                                     # NoAI stays: the next order turns on the AI


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


def door(g, rect):
    """The block cell in front of the door of the building rect: the middle of the free cells on its south side."""
    return next(iter(g.map.front(rect)), None)


def order(g, player, cell):
    """The selected units go into the own building with the block cell (x, z) in its footprint. Returns its footprint,
    or None (no such building, nothing selected, or no plugin): the click is then not a garrison order."""
    rect = next((r for r in holders(g) if cell and r[0] <= cell[0] < r[1] and r[2] <= cell[1] < r[3]), None)
    if rect is None or not g.selected or not g.paper or (to := door(g, rect)) is None:
        return None
    import ai, civs                                                # ai imports gather, gather imports this module
    x, z = to
    for u in sorted(g.selected):
        if (v := g.villagers.get(u)) is not None:                  # the villager stops its work
            v.state, v.path, v.goal, v.site = "garrison", [], None, None
        name = "VILLAGER" if u in g.villagers else g.soldiers.get(u, "")
        ai.move(g, u, name, g.map.T, x + 0.5, g.map.y(x, z), z + 0.5, ai.NORMAL * civs.speed(g, name))
        g.entering[u] = rect
    g.mark(player, {to})
    return rect


def tick(g):
    """The units at the door of their building go in (a full building: they stay at the door), and the units of a
    fallen building come out (only the plugin takes the hit points of a building)."""
    held = [r for r, us in g.garrisons.items() if us]
    if not g.entering and not (held and g.paper):
        return
    homes = holders(g)
    if g.entering:
        pos = g.positions(sorted(g.entering))
        for u, rect in list(g.entering.items()):
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
    units = g.garrisons.setdefault(rect, [])
    if len(units) >= SIZES[o["name"]]:                             # full: it stays at the door, as in AoE2
        g.command(f"aoe stop {u}")
        if (v := g.villagers.get(u)) is not None:
            v.state = "idle"
        return
    x, y, z = cell(g.map, rect, o, len(units))
    units.append(u)
    g.command(f"aoe stop {u}")
    for c in enter(u, x, y, z):
        g.command(c)
    if (v := g.villagers.get(u)) is not None:
        v.pos, v.state = (x + 0.5, float(y), z + 0.5), "garrison"
    if u in g.selected:                                            # it leaves the selection
        g.choose(g.selected - {u}, min(g.selected - {u}, default=None))


def out(g, rect):
    """All units of the building rect come out on the free cells next to it, the door side first. Returns them."""
    units = g.garrisons.pop(rect, [])
    ring = g.map.front(rect) or [((rect[0] + rect[1]) // 2, rect[3])]
    for k, u in enumerate(units):
        x, z = ring[k % len(ring)]
        y = g.map.y(x, z) or 0
        for c in leave(u, x, y, z) + [f"aoe label {u}"]:           # the plugin shows the name line again
            g.command(c)
        if (v := g.villagers.get(u)) is not None:
            v.pos, v.state = (x + 0.5, float(y), z + 0.5), "idle"
    if units:
        g.command("tellraw @a " + json.dumps({"text": f"{len(units)} units came out", "color": "gray"}))
    return units


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
    """The UUIDs of the units inside a building: orders and the selection skip them."""
    return {u for us in g.garrisons.values() for u in us}
