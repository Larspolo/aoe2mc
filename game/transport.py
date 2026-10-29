"""The transport ship in the game program (#1385, epic #1381). The dock trains it in the Dark Age (train.py). A right
click with selected land units on an own transport ship loads up to SIZE of them, as in AoE2 DE (AoE2 wiki "Transport
Ship": garrison 20, all land units): they walk to the land cell nearest to the ship with the plugin (`aoe moveto`), and
there they go in when the ship is at that shore: the ship sails to the water next to it first, as in AoE2 (the owner,
#2055; before, the ship stayed and took the units from the nearest shore, #1653). A click on the land with the
selected loaded ship sails it to the water near that cell (fleet.order),
and at the end of its path the units come out on the land next to the ship and walk to the clicked cell, as in AoE2 DE
(#1652: before, they came out at a clicked cell near the ship). A right click on the selected ship unloads it at once
on the nearest land. When the ship sinks, the units inside are lost, as in AoE2.

Minecraft feature: the units inside ride the ship (`ride ... mount`, Minecraft riders), as in the siege tower: the
first one rides its crew (the passenger of the chest boat, which has one seat), each next one the one before (on its
rider, for a mounted unit: a horse takes one passenger). So they move with the /tp steps of the ship without own logic.
A unit inside has the state of a garrisoned unit (garrison.INSIDE) and the plugin hides it from the players.

    transport.order(g, player, u)     # gather.Gather.click: the selection goes into the own transport ship u
    transport.out(g, u)               # gather.Gather.click on the selected ship: all units come out on the shore
    transport.aim(g, ships, cell)     # gather.Gather.walk_to: a loaded ship sent to a land cell unloads there
    transport.tick(g)                 # gather.Gather.step: units at the ship at the shore go in, a ship at its goal unloads
"""
import collections
import json
import math

import civs
import replay
import units as unit_types
from aoe2mc import CARRIERS, GARRISONED, INTO, MADE_INSIDE
from garrison import INSIDE, OUTSIDE

NAME = "TRANSPORT_SHIP"
SIZE = 20                   # units inside, as in AoE2 DE (5 before update 141935)
DOOR = 2.5                  # blocks from the boarding cell or the ship: there a unit goes in, and the ship is at its berth
SHORE = 3                   # tiles from the ship to the land that units board from or go out to
BODY = 250000               # cells: the limit of the search of the land that the units can walk on (#1694)


def fits(g, u):
    """True for a unit that goes into a transport ship: a villager or an own land unit (no ship)."""
    return u in g.villagers or u in g.soldiers and not replay.ship(g.soldiers[u])


def land(g, cell, n, tiles=SHORE):
    """The n free land cells nearest to the block cell (x, z) within `tiles` tiles, the nearest first."""
    r = tiles * g.map.T
    cells = [(x, z) for x in range(cell[0] - r, cell[0] + r + 1) for z in range(cell[1] - r, cell[1] + r + 1)
             if g.map.free(x, z)]
    return sorted(cells, key=lambda c: (math.dist(c, cell), c))[:n]


def body(g, start, limit=BODY):
    """The free land cells that a unit on the block cell start reaches on foot (8 neighbours, steps of at most 1
    block, as Map.path), at most limit cells. Empty when start is not free land."""
    from gather import STEPS                                       # gather imports this module
    if not g.map.free(*start):
        return set()
    seen, todo = {start}, collections.deque([start])
    while todo and len(seen) < limit:
        x, z = todo.popleft()
        for dx, dz in STEPS:
            n = (x + dx, z + dz)
            if n not in seen and g.map.free(*n) and abs(g.map.y(*n) - g.map.y(x, z)) <= 1:
                seen.add(n)
                todo.append(n)
    return seen


def order(g, player, ship):
    """The land units of the selection walk to the shore cell nearest to the own transport ship, and the ship sails
    to the water next to that cell (its berth, fleet.order): the units go in only when the ship is there (tick), as in
    AoE2 (the owner, #2055: "they can still load while the boat is not near the coast"). Returns True, or False (no
    own transport ship, no unit of the selection fits, no land on the map, or no water path to the shore). The land
    cell is on the land of the first unit of the selection (body): a nearer shore across the sea is not a goal, the
    units cannot walk there (#1694: they walked into the sea)."""
    if g.soldiers.get(ship) != NAME or not g.paper or not (pos := g.pos(ship)):
        return False
    who = sorted(u for u in g.selected - {ship} if fits(g, u))
    cell, tiles = (math.floor(pos[0]), math.floor(pos[2])), SHORE
    first = next((p for u in who if (p := g.pos(u))), None)
    own = body(g, (math.floor(first[0]), math.floor(first[2]))) if first else set()
    at = [min(own, key=lambda c: (math.dist(c, cell), c))] if own else []
    while who and not own and not (at := land(g, cell, 1, tiles)) and tiles * g.map.T < g.map.n:
        tiles *= 2                                                 # far from the land: look farther (#1653)
    if not who or not at:
        return False
    import ai, fleet, train                                        # ai, fleet and train import gather
    x, z = at[0]
    if not (berth := fleet.order(g, {ship}, (x, z))):              # no water path to that shore
        return False
    vars(g).setdefault("berths", {})[ship] = berth[ship]
    vars(g).get("unloads", {}).pop(ship, None)                     # a boarding order ends an unload order
    g.new_order(who)
    for u in who:
        if (v := g.villagers.get(u)) is not None:                  # the villager stops its work
            v.state, v.path, v.goal, v.site = "garrison", [], None, None
        name = "VILLAGER" if u in g.villagers else g.soldiers[u]
        ai.move(g, u, name, g.map.T, x + 0.5, g.map.y(x, z), z + 0.5, ai.NORMAL * train.speed(g, name, u))
        vars(g).setdefault("loading", {})[u] = (ship, (x, z))
    g.mark(player, {(x, z)})
    return True


def mounted(name):
    """True for a unit with a rider (a horse): the next unit rides its rider."""
    return "Passengers" in (unit_types.classify(name) or {})


def ride(g, u, units):
    """The command that puts unit u on top of the units inside a ship (the UUIDs units, the crew under the first)."""
    if not units:
        return None
    last = units[-1]
    if mounted("VILLAGER" if last in g.villagers else g.soldiers.get(last, "")):
        return f"execute as {last} on passengers run ride {u} mount @s"
    return f"ride {u} mount {last}"


def size(g):
    """The units that a transport ship of the player of g takes: SIZE, more for the Saracens (the key "transport", #2344)."""
    return SIZE + civs.value("transport", civs.civ(g), 0)


def capacity(g, ship):
    """The units that the own transport ship or ram ship takes: size() for a ship, CARRIERS for a ram (#3779)."""
    name = g.soldiers.get(ship)
    return CARRIERS[name] if name in CARRIERS and name != NAME else size(g)


def carriers(g):
    """{reference ID: UUID} of the own transport ships and rams of aoe2mc.json that live (#3779)."""
    return {o["ref"]: o["uuid"] for o in g.data.get("objects", ()) if o["kind"] == "unit" and o.get("ref") is not None
            and o.get("uuid") in g.soldiers and o["name"] in CARRIERS}


def adopt(g, made):
    """The units made (UUIDs) that a trigger made inside an own transport ship or ram ("Create Garrisoned Object",
    the tag aoe2mc.in<ref>, #3779) go into it (go_in), so that out lets them out. The tags go: each unit joins once."""
    for ref, ship in sorted(carriers(g).items()):
        for u in sorted(set(g.where(None, f"@e[tag={INTO}{ref},tag={MADE_INSIDE}]")) & set(made)):
            g.command(f"tag {u} remove {MADE_INSIDE}")
            g.command(f"tag {u} remove {INTO}{ref}")
            go_in(g, u, ship)


def go_in(g, u, ship):
    """Unit u rides the transport ship: on its crew, or on the top unit inside. A full ship: it stays on the shore."""
    units = vars(g).setdefault("cargo", {}).setdefault(ship, [])
    g.command(f"aoe stop {u}")
    if len(units) >= capacity(g, ship):
        if (v := g.villagers.get(u)) is not None:
            v.state = "idle"
        return
    first = f"execute as {ship} on passengers run ride {u} mount @s"
    for c in (ride(g, u, units) or first, f"data merge entity {u} {INSIDE}", f"tag {u} add {GARRISONED}",
              f"aoe hide @a {u}"):
        g.command(c)
    units.append(u)
    if (v := g.villagers.get(u)) is not None:
        v.state = "garrison"
    if u in g.selected:                                            # it leaves the selection
        g.choose(g.selected - {u}, min(g.selected - {u}, default=None))


def out(g, ship):
    """All units of the transport ship come out on the land cells nearest to the ship. Returns them; [] (they stay
    inside) when the ship is empty or no land is within SHORE tiles."""
    units = vars(g).get("cargo", {}).get(ship, [])
    pos = g.pos(ship) if units else None
    if not pos:
        return []
    ring = land(g, (math.floor(pos[0]), math.floor(pos[2])), len(units))
    if not ring:
        return []
    del g.cargo[ship]
    for k, u in enumerate(reversed(units)):                        # the top of the stack first
        x, z = ring[k % len(ring)]
        y = g.map.y(x, z)
        for c in (f"ride {u} dismount", f"tp {u} {x + 0.5} {y} {z + 0.5}", f"data merge entity {u} {OUTSIDE}",
                  f"tag {u} remove {GARRISONED}", f"aoe show @a {u}", f"aoe label {u}"):
            g.command(c)
        if (v := g.villagers.get(u)) is not None:
            v.pos, v.state = (x + 0.5, float(y), z + 0.5), "idle"
    g.command(f"tellraw @a[team=p{g.player}] " + json.dumps({"text": f"{len(units)} units came out", "color": "gray"}))
    return units


def aim(g, ships, cell):
    """The loaded transport ships of ships (that sail now) unload at the block cell (x, z) at the end of their path
    when it is land; a ship sent onto the water keeps its units."""
    unloads = vars(g).setdefault("unloads", {})
    for u in ships:
        if u in vars(g).get("cargo", {}) and not g.map.wet(*cell):
            unloads[u] = cell
        else:
            unloads.pop(u, None)


def tick(g):
    """The units at the shore next to their ship go in; a loaded ship at the end of its path unloads; the units of a
    sunk ship are lost."""
    loading, cargo, unloads = vars(g).get("loading", {}), vars(g).get("cargo", {}), vars(g).get("unloads", {})
    berths = vars(g).get("berths", {})
    if loading:
        pos = g.positions(sorted(set(loading) | {s for s, _ in loading.values()}))
        for u, (ship, at) in sorted(loading.items()):
            if u not in pos or ship not in pos or g.soldiers.get(ship) != NAME:
                del loading[u]                                     # dead, or the ship sank
            elif (berth := berths.get(ship)) and math.dist((pos[ship][0], pos[ship][2]),
                                                          (berth[0] + 0.5, berth[1] + 0.5)) > DOOR:
                continue                                           # the ship is not at the shore yet (#2055)
            elif min(math.dist((pos[u][0], pos[u][2]), (at[0] + 0.5, at[1] + 0.5)),
                     math.dist((pos[u][0], pos[u][2]), (pos[ship][0], pos[ship][2]))) <= DOOR:
                del loading[u]
                go_in(g, u, ship)
    for ship in [s for s in berths if all(v[0] != s for v in loading.values())]:
        del berths[ship]                                           # all its units are in, or gone
    for ship, cell in sorted(unloads.items()):
        v = g.ships.get(ship)
        if ship not in cargo or v is None:
            del unloads[ship]
        elif not v.path:
            del unloads[ship]
            g.walk_to(None, cell, out(g, ship))                        # out at the shore, then a walk (#1515, #1652)
    for ship in [s for s in sorted(cargo) if s not in g.soldiers]:   # sunk: the units inside are lost, as in AoE2
        for u in cargo.pop(ship):
            g.command(f"kill {u}")
