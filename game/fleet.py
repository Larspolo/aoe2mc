"""
The own ships of the game program (#1383, epic #1381). A dock trains fishing ships (train.TRAINS): the new ship floats
on a water cell in front of the dock (spawn). A selected ship sails to the water cell that the player clicks (order),
or to the water nearest to a clicked land cell. A boat has no Minecraft path finding, so the ship moves with /tp steps
on a water path of gather.Map (Map.path with water, replay.sail), as the ships of the live replay (#866): own logic,
because Minecraft has no feature for it. It never goes onto the land: each step is on a water cell (Map.wet).
A warship (the galley, #1386) attacks with the crew of its boat: the plugin gives the crew the AoE2 values (aoe stats),
the range goal and the target (aoe attack), and the crew shoots the Minecraft arrows of an archer. The crew cannot move
the boat, so attack() sails the ship into its range of the target first. The crew has the hit points: when it dies,
the plugin removes its boat (the ship sinks).
A fishing ship sent to a fish (fish_order) gathers it at the AoE2 DE rate and brings each load to the nearest own dock,
as a villager brings its load to a drop site (#1384, work).
A fishing ship builds a fish trap on the water (build.WATER) and then gathers it at the AoE2 DE rate, as a farmer a
farm (#1438): Map.traps holds the own traps, Map.fish their food. An empty trap stops its ship.
A trade cog sent to a second own dock (trade_order) sails between that dock and its home dock (the nearest other own
dock), and each arrival at home gives the gold of the AoE2 trade formula (trade.gold), as a trade cart (#1485).
"""
import math

import civs
import gather
import replay
import table

# Tiles per game second (AoE2 DE wiki infobox): the key "sail" of a ship in data/units.jsonl; other ships: 1.0
SPEEDS = {r["name"]: r["sail"] for r in table.load("units.jsonl") if "sail" in r}
NEAR = 3                                 # tiles from a clicked land cell to the water that a ship sails to
PATH_CELLS = 20000                       # the path search limit (cells), as a long walk of the replay
CHASE = 2.0                              # seconds between two range checks of a warship with a target (#1386)
CONTACT = 1                              # blocks: a demolition ship sails next to its target (#1440)
CARRY = 15                               # food of one fishing ship trip (AoE2 DE wiki, "Fishing Ship")
COG = "TRADE_COG"


def ship(g, uuid):
    """The gather.Villager of own ship uuid (its path and position), made at the first use."""
    if uuid not in g.ships:
        pos = g.pos(uuid)
        if not pos:
            return None
        g.ships[uuid] = gather.Villager(uuid, pos)
    return g.ships[uuid]


def spawn(g, rect, name):
    """Summon the ship name of g.player on a water cell in front of the dock rect (the cells one after the other, as
    train.spawn). Returns its UUID, or None."""
    import train                                                      # train imports this module
    cells = g.map.front(rect, water=True)
    if not cells:
        return None
    k = g.trained[rect] = g.trained.get(rect, -1) + 1
    x, z = cells[k % len(cells)]
    pos = (x + 0.5, g.map.sea(x, z), z + 0.5)
    uuid = train.summon(g, name, pos)
    if uuid is not None:
        g.ships[uuid] = gather.Villager(uuid, pos)
        if rect in g.rally:                                            # its rally point: on the water
            order(g, [uuid], g.rally[rect][0])
    return uuid


def level(g):
    """The y of the water surface of the map, as Map.sea on the open water (the lowest land - 1): real maps have all
    water at elevation 0."""
    if getattr(g.map, "level", None) is None:
        g.map.level = g.map.sea(-99, -99, 0)                           # reach 0: the whole map
    return g.map.level


def pick(g, eye, d, reach=64):
    """The block cell (x, z) of the land or of the water surface that the ray from eye in direction d hits first, or
    None. Map.pick_ground goes through the water: a ship and a dock are on it."""
    top = level(g)
    for k in range(1, reach * 4):
        x, y, z = (eye[i] + d[i] * k / 4 for i in range(3))
        bx, bz = math.floor(x), math.floor(z)
        if not (0 <= bx < g.map.n and 0 <= bz < g.map.n):
            return None
        ground = g.map.y(bx, bz)
        if y < (top if ground is None else ground):
            return bx, bz
    return None


def goals(g, cell, n):
    """n water cells (Map.wet) for n ships at the clicked block cell: the nearest ones to it, the cell itself first.
    A land cell: the water within NEAR tiles of it, else the water nearest to it (AoE2 sails to the nearest shore,
    #1515). [] when there is none."""
    r = max(math.isqrt(n) + 2, NEAR * g.map.T if not g.map.wet(*cell) else 0)
    while True:
        cells = [(x, z) for x in range(cell[0] - r, cell[0] + r + 1) for z in range(cell[1] - r, cell[1] + r + 1)
                 if g.map.wet(x, z)]
        if cells or r > 2 * g.map.n:
            return sorted(cells, key=lambda c: (math.dist(c, cell), c))[:n]
        r *= 2                                                         # a far click: a wider square, not for all clicks


def order(g, uuids, cell):
    """The own ships uuids sail to the clicked block cell (x, z): each one to its own water cell near it. Returns
    {uuid: goal cell} of the ships that found a water path."""
    who = [v for u in sorted(uuids) if (v := ship(g, u))]
    out = {}
    for v in who:
        v.prey = None                                                  # a move order ends an attack (#1386)
    for v, goal in zip(who, goals(g, cell, len(who))):
        v.tree, v.site, v.state = None, None, "idle"                   # a move order stops the fishing; the load stays
        path = g.map.path(v.cell, {goal}, PATH_CELLS, water=True)
        if path is not None:
            v.path, v.timer = path, 0.0
            out[v.uuid] = goal
    return out


def reach(g, name):
    """Blocks from which ship name shoots: its AoE2 range (combat.STATS) less one tile, so that it stays in range when
    the target moves a bit; CONTACT for a demolition ship (range 0, a blast, #1440). 0 for a ship without an attack
    (a fishing ship)."""
    import combat                                                     # combat imports gather, gather this module
    s = combat.stats(name)
    return 0 if not s.attack else int(max(1, s.range - 1) * g.map.T) if s.range else CONTACT * (name in combat.BLAST)


def attack(g, uuids, target):
    """The own warships uuids attack the unit target (#1386): the plugin gives the target to the crew (aoe attack),
    and each ship out of range sails to the water cell nearest to it in its range of the target. tick() sails it
    again when the target moves away. Returns {uuid: goal cell} of the ships that sail."""
    out = {}
    for u in sorted(uuids):
        if (v := ship(g, u)) and reach(g, g.soldiers.get(u, "")):
            v.prey = target
            out |= chase(g, v)
    return out


def chase(g, v):
    """Sail warship v into its range of its target v.prey: {uuid: goal cell}, or {} when it is in range, the target is
    gone (v.prey: None) or no water cell in range has a path."""
    pos = g.pos(v.prey)
    if not pos:
        v.prey, v.path = None, []
        return {}
    r, at = reach(g, g.soldiers[v.uuid]), (math.floor(pos[0]), math.floor(pos[2]))
    if math.dist(v.cell, at) <= r:
        v.path = []
        return {}
    cells = sorted(((x, z) for x in range(at[0] - r, at[0] + r + 1) for z in range(at[1] - r, at[1] + r + 1)
                    if math.dist((x, z), at) <= r and g.map.wet(x, z)), key=lambda c: (math.dist(c, v.cell), c))
    for goal in cells[:4]:                                             # the nearest ones: a lake behind the land fails
        path = g.map.path(v.cell, {goal}, PATH_CELLS, water=True)
        if path is not None:
            v.path, v.timer = path, 0.0
            return {v.uuid: goal}
    return {}


def speed(name, T, g=None, uuid=None):
    """Blocks per game second of ship name; with g, also the factor of the technologies and the civilization of its
    player (train.speed: Caravan for the trade cog, #1497; ship uuid near a Military Town Center, #2496)."""
    import train                                                      # train imports gather, gather this module
    return next((s for k, s in SPEEDS.items() if name.startswith(k)), 1.0) * T * (train.speed(g, name, uuid) if g else 1)


def tick(g, dt):
    """Move each own ship with a path by the blocks of dt game seconds, one water cell per /tp step. A cell that is
    no water any more (a new dock on the way) gives a new path to the goal, or the ship stops. A ship without a path
    fishes (work)."""
    for u, v in list(g.ships.items()):
        if u not in g.soldiers:                                        # dead or converted
            del g.ships[u]
            continue
        if v.prey and not v.path and g.clock() >= getattr(v, "chased", 0.0):   # the target moved away (#1386)
            v.chased = g.clock() + CHASE
            chase(g, v)
        if not v.path:
            work(g, v, dt)
            continue
        v.timer += dt * speed(g.soldiers[u], g.map.T, g, u)
        while v.path:
            if not g.map.wet(*v.path[0]):
                v.path = g.map.path(v.cell, {v.path[-1]}, PATH_CELLS, water=True) or [] if g.map.wet(*v.path[-1]) else []
                continue
            step = math.dist(v.cell, v.path[0])
            if v.timer < step:
                break
            v.timer -= step
            replay.sail(g, v)
        if not v.path:
            v.timer = 0.0


def sail_to(g, v, state, cells):
    """Ship v sails to the nearest of the water cells, in state. False (idle) when there is no water path."""
    path = g.map.path(v.cell, cells, PATH_CELLS, water=True)
    v.path, v.timer, v.state = path or [], 0.0, state if path is not None else "idle"
    return path is not None


def reroute(g):
    """The ships with a catch sail to the next own dock when their dock fell (ruins.fall, #3009); with none they stop."""
    for v in g.ships.values():
        if v.state == "to_drop":
            docks = set().union(*(g.map.around(c, water=True) for c in g.map.docks))
            if not docks or not sail_to(g, v, "to_drop", docks):
                v.state = "idle"


def spots(g, tile):
    """The water cells where a ship fishes the fish on tile: on its tile and next to it; next to a fish trap."""
    cells = g.map.traps.get(tile) or g.map.cells(tile)
    return {c for c in cells if g.map.wet(*c)} | g.map.around(cells, water=True)


def fish(g, uuids, tile):
    """The own fishing ships uuids sail to the fish on tile and gather it (#1384). Returns the ships with a path."""
    out = set()
    for v in [v for u in sorted(uuids) if replay.fisher(g.soldiers.get(u, "")) and (v := ship(g, u))]:
        res = g.map.resource(tile)                                     # an oyster: gold (#2465)
        if v.load and v.res != res:
            v.load = 0                                                 # AoE2 drops a load of another resource
        v.res, v.tree = res, tile
        if sail_to(g, v, "to_tree", spots(g, tile)):
            out.add(v.uuid)
    return out


def fish_order(g, name, eye, d):
    """A look of player name at a fish (the water surface over its tile) with own fishing ships in the selection: they
    fish it. True when the click was a fish order."""
    boats = {u for u in g.selected if replay.fisher(g.soldiers.get(u, ""))}
    cell = boats and pick(g, eye, d)
    tile = cell and next((t for t, c in g.map.traps.items() if cell in c), (cell[0] // g.map.T, cell[1] // g.map.T))
    if not tile or g.map.fish.get(tile, 0) <= 0:
        return False
    g.new_order(boats)
    if not fish(g, boats, tile):
        return False
    g.mark(name, g.map.spot(tile))
    return True


def docks(g):
    """The block footprints of the complete own docks."""
    import train                                                      # train imports this module
    return sorted(r for r, n in train.homes(g).items() if n == "DOCK")


def pier(g, rect):
    """The water cells next to the dock rect (x0, x1, z0, z1): a trade cog stops there."""
    return g.map.around({(x, z) for x in range(rect[0], rect[1]) for z in range(rect[2], rect[3])}, water=True)


def trade_order(g, player, cell):
    """The selected trade cogs trade with the own dock with the block cell (x, z) in its footprint (#1485), as the
    trade carts with a market (trade.order). Returns its footprint, or None (no own dock there, no cog selected or no
    second own dock): the click is then not a trade order."""
    own = docks(g)
    rect = next((r for r in own if cell and r[0] <= cell[0] < r[1] and r[2] <= cell[1] < r[3]), None)
    cogs = [v for u in sorted(g.selected) if g.soldiers.get(u, "").startswith(COG) and (v := ship(g, u))]
    if rect is None or not cogs or len(own) < 2:
        return None
    g.new_order({v.uuid for v in cogs})
    mid = lambda r: ((r[0] + r[1]) / 2, (r[2] + r[3]) / 2)            # noqa: E731
    for v in cogs:
        home = min((r for r in own if r != rect), key=lambda r: (math.dist(mid(r), v.cell), r))
        v.prey, v.tree, v.site = None, None, None
        v.route = {"home": home, "dock": rect, "to": rect, "rest": getattr(v, "route", {}).get("rest", 0.0)}
        sail_to(g, v, "to_trade", pier(g, rect))
    g.mark(player, {(rect[0], rect[2]), (rect[1] - 1, rect[3] - 1)})
    return rect


def route(g, v):
    """Trade cog v is at a dock of its route: at home it gives the gold of the trip (the fraction stays for the next
    trip, as in AoE2), then it sails to the other dock. A dock that fell ends the route."""
    import trade                                                      # trade imports gather, gather this module
    r, own = v.route, docks(g)
    if r["home"] not in own or r["dock"] not in own:
        v.state = "idle"
        return
    if r["to"] == r["home"]:
        r["rest"] += trade.gold(trade.center(r["home"], g.map.T), trade.center(r["dock"], g.map.T), g.map.n / g.map.T) \
            * civs.value("trade_gold", civs.civ(g), 1)                # Palmyrans +20 % (#4446)
        n, r["rest"] = int(r["rest"]), r["rest"] - int(r["rest"])
        if n:
            g.earn("gold", n)
    r["to"] = r["dock"] if r["to"] == r["home"] else r["home"]
    sail_to(g, v, "to_trade", pier(g, r["to"]))


def trap(g, site):
    """The tile of the fish trap of the construction site (Map.traps), as build.rise gives it to Map.building."""
    x0, _, z0, _ = site["footprint"]
    s, T = gather.build.footprint(site["name"]), g.map.T
    return x0 // T + s // 2, z0 // T + s // 2


def build_site(g, uuids, site):
    """The own fishing ships uuids sail next to the fish trap site and build it (#1438): Gather.run counts them as
    builders. Returns the ships with a path."""
    x0, x1, z0, z1 = site["footprint"]
    goals = g.map.around({(x, z) for x in range(x0, x1) for z in range(z0, z1)}, water=True)
    out = set()
    for v in [v for u in sorted(uuids) if replay.fisher(g.soldiers.get(u, "")) and (v := ship(g, u))]:
        v.prey, v.tree, v.site = None, None, site
        if sail_to(g, v, "to_site", goals):
            out.add(v.uuid)
    return out


def build_order(g, name, eye, d):
    """A look of player name at an own unfinished fish trap with own fishing ships in the selection: they build it.
    True when the click was a build order."""
    import build                                                      # build imports this module
    boats = {u for u in g.selected if replay.fisher(g.soldiers.get(u, ""))}
    cell = boats and pick(g, eye, d)
    site = cell and next((s for s in g.sites if s["progress"] < 1 and s["name"] in build.WATER
                          and s["footprint"][0] <= cell[0] < s["footprint"][1]
                          and s["footprint"][2] <= cell[1] < s["footprint"][3]), None)
    if not site:
        return False
    g.new_order(boats)
    if not build_site(g, boats, site):
        return False
    x0, x1, z0, z1 = site["footprint"]
    g.mark(name, {(x0, z0), (x1 - 1, z1 - 1)})
    return True


def remove(g, tile):
    """Remove the empty fish on tile: from the map, and its mob (no loot: an empty loot table). An empty fish trap
    stays (its ship stops)."""
    if tile in g.map.traps:
        return
    g.map.fish.pop(tile, None)
    g.map.shore.discard(tile)
    if tile in g.map.oysters:                                          # the sea pickles of an oyster (#2465)
        g.map.oysters.discard(tile)
        T = g.map.T
        g.command(f"fill {tile[0] * T} -64 {tile[1] * T} {tile[0] * T + T - 1} 319 {tile[1] * T + T - 1} "
                  "minecraft:water replace minecraft:sea_pickle")
    if kind := g.map.fish_mobs.pop(tile, None):
        T = g.map.T
        at = f"@e[type=minecraft:{kind},x={tile[0] * T},y=-64,z={tile[1] * T},dx={T - 1},dy=383,dz={T - 1}]"
        g.command(f'execute as {at} run data merge entity @s {{DeathLootTable:"minecraft:empty"}}')
        g.command(f"kill {at}")


def nearest(g, tile):
    """The fish with food nearest to tile, or None: the next fish of a ship, as the next bush of a villager. Not a
    fish trap: the ship of an empty trap stops, as a farmer at an empty farm. An oyster: the next oyster (#2465)."""
    if tile in g.map.traps:
        return tile if g.map.fish.get(tile, 0) > 0 else None
    oyster = tile in g.map.oysters
    return min((t for t, k in g.map.fish.items() if k > 0 and t not in g.map.traps and (t in g.map.oysters) == oyster),
               key=lambda t: (math.dist(t, tile), t), default=None)


def rate(g, fish):
    """Food per game second of an own fishing ship at fish: the AoE2 DE rate (gather.SHIP_WORK) with the dock
    technologies of the player (gather.SHIP_TECHS, #1439) and the bonus of its civilization in its age (civs.ship_work).
    An oyster: gold, with the bonus of the gather kind "oyster" (civs.work: Puru, #2465)."""
    import train                                                      # train imports this module
    oyster = fish in g.map.oysters
    return gather.SHIP_WORK["oyster" if oyster else "trap" if fish in g.map.traps else "shore" if fish in g.map.shore
                            else "deep"] * civs.work(g, "oyster") ** oyster * \
        math.prod(f ** train.count(g, t) for t, (f, _) in gather.SHIP_TECHS.items()) * civs.ship_work(g) * \
        gather.civs.turbo(g)


def carry(g):
    """Food of one trip of an own fishing ship: CARRY, the more food of the dock technologies (#1439) and of the
    civilization (the kind "ship" of civs.CARRY, not the villager bonus of all kinds)."""
    import train                                                      # train imports this module
    n = CARRY + sum(n for k, n in civs.CARRY.get(civs.civ(g), ()) if k == "ship") + \
        sum(c * train.count(g, t) for t, (_, c) in gather.SHIP_TECHS.items())
    return n if gather.civs.turbo(g) == 1 else round(n * gather.civs.turbo(g))   # Turbo Mode (#2359)


def work(g, v, dt):
    """One step of fishing ship v without a path, dt game seconds: at the fish it gathers at the AoE2 DE rate
    (rate()) up to carry(), then sails to the nearest own dock; there the food goes into the stock, and it sails
    back to its fish or to the next fish. An empty fish is removed."""
    m = g.map
    if v.state == "to_trade":                                          # at a dock of its trade route (#1485)
        route(g, v)
    elif v.state == "to_site":                                           # next to a fish trap site: Gather.run builds
        v.state = "build" if v.site and v.site["progress"] < 1 else "idle"
    elif v.state == "to_tree":
        v.tree = v.tree if m.fish.get(v.tree, 0) > 0 else nearest(g, v.tree)
        if v.tree is not None and v.cell not in spots(g, v.tree):
            sail_to(g, v, "to_tree", spots(g, v.tree))
        else:
            v.state, v.timer = "chop" if v.tree is not None else "idle", 0.0
    elif v.state == "chop":
        full = carry(g)
        v.timer += full if getattr(g, "aegis", False) else dt * rate(g, v.tree)
        while v.timer >= 1 and v.load < full and m.fish.get(v.tree, 0) > 0:
            v.timer -= 1
            v.load += 1
            m.fish[v.tree] -= 1
            g.work(v)                                                  # the splash sound and the water particles
        if m.fish.get(v.tree, 0) <= 0:
            remove(g, v.tree)
        if v.load >= full or m.fish.get(v.tree, 0) <= 0:
            docks = set().union(*(m.around(c, water=True) for c in m.docks))
            if not docks or not sail_to(g, v, "to_drop", docks):
                v.state = "idle"
    elif v.state == "to_drop":
        g.deliver("gold" if v.res == "gold" else "food", v.load, kind="ship")   # an oyster: gold; the drop-off bonus (#2308)
        v.load = 0
        g.event(v, "drop")
        v.tree = v.tree if m.fish.get(v.tree, 0) > 0 else nearest(g, v.tree)
        if v.tree is None or not sail_to(g, v, "to_tree", spots(g, v.tree)):
            v.state = "idle"
