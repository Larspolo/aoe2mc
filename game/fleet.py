"""
The own ships of the game program (#1383, epic #1381). A dock trains fishing ships (train.TRAINS): the new ship floats
on a water cell in front of the dock (spawn). A selected ship sails to the water cell that the player clicks (order),
or to the water nearest to a clicked land cell. A boat has no Minecraft path finding, so the ship moves with /tp steps
on a water path of gather.Map (Map.path with water, replay.sail), as the ships of the live replay (#866): own logic,
because Minecraft has no feature for it. It never goes onto the land: each step is on a water cell (Map.wet).
A fishing ship sent to a fish (fish_order) gathers it at the AoE2 DE rate and brings each load to the nearest own dock,
as a villager brings its load to a drop site (#1384, work).
"""
import math

import gather
import replay

SPEEDS = {"FISHING_SHIP": 1.26}          # tiles per game second (AoE2 DE wiki infobox); other ships: 1.0 until a ticket
NEAR = 3                                 # tiles from a clicked land cell to the water that a ship sails to
PATH_CELLS = 20000                       # the path search limit (cells), as a long walk of the replay
CARRY = 15                               # food of one fishing ship trip (AoE2 DE wiki, "Fishing Ship")


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
    A land cell: the water within NEAR tiles of it. [] when there is none."""
    r = max(math.isqrt(n) + 2, NEAR * g.map.T if not g.map.wet(*cell) else 0)
    cells = [(x, z) for x in range(cell[0] - r, cell[0] + r + 1) for z in range(cell[1] - r, cell[1] + r + 1)
             if g.map.wet(x, z)]
    return sorted(cells, key=lambda c: (math.dist(c, cell), c))[:n]


def order(g, uuids, cell):
    """The own ships uuids sail to the clicked block cell (x, z): each one to its own water cell near it. Returns
    {uuid: goal cell} of the ships that found a water path."""
    who = [v for u in sorted(uuids) if (v := ship(g, u))]
    out = {}
    for v, goal in zip(who, goals(g, cell, len(who))):
        v.tree, v.state = None, "idle"                                 # a move order stops the fishing; the load stays
        path = g.map.path(v.cell, {goal}, PATH_CELLS, water=True)
        if path is not None:
            v.path, v.timer = path, 0.0
            out[v.uuid] = goal
    return out


def speed(name, T):
    """Blocks per game second of ship name."""
    return next((s for k, s in SPEEDS.items() if name.startswith(k)), 1.0) * T


def tick(g, dt):
    """Move each own ship with a path by the blocks of dt game seconds, one water cell per /tp step. A cell that is
    no water any more (a new dock on the way) gives a new path to the goal, or the ship stops. A ship without a path
    fishes (work)."""
    for u, v in list(g.ships.items()):
        if u not in g.soldiers:                                        # dead or converted
            del g.ships[u]
            continue
        if not v.path:
            work(g, v, dt)
            continue
        v.timer += dt * speed(g.soldiers[u], g.map.T)
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


def spots(g, tile):
    """The water cells where a ship fishes the fish on tile: on its tile and next to it."""
    cells = g.map.cells(tile)
    return {c for c in cells if g.map.wet(*c)} | g.map.around(cells, water=True)


def fish(g, uuids, tile):
    """The own fishing ships uuids sail to the fish on tile and gather it (#1384). Returns the ships with a path."""
    out = set()
    for v in [v for u in sorted(uuids) if replay.fisher(g.soldiers.get(u, "")) and (v := ship(g, u))]:
        v.res, v.tree = "food", tile
        if sail_to(g, v, "to_tree", spots(g, tile)):
            out.add(v.uuid)
    return out


def fish_order(g, name, eye, d):
    """A look of player name at a fish (the water surface over its tile) with own fishing ships in the selection: they
    fish it. True when the click was a fish order."""
    boats = {u for u in g.selected if replay.fisher(g.soldiers.get(u, ""))}
    cell = boats and pick(g, eye, d)
    tile = cell and (cell[0] // g.map.T, cell[1] // g.map.T)
    if not tile or g.map.fish.get(tile, 0) <= 0 or not fish(g, boats, tile):
        return False
    g.mark(name, g.map.spot(tile))
    return True


def remove(g, tile):
    """Remove the empty fish on tile: from the map, and its mob (no loot: an empty loot table)."""
    g.map.fish.pop(tile, None)
    g.map.shore.discard(tile)
    if kind := g.map.fish_mobs.pop(tile, None):
        T = g.map.T
        at = f"@e[type=minecraft:{kind},x={tile[0] * T},y=-64,z={tile[1] * T},dx={T - 1},dy=383,dz={T - 1}]"
        g.command(f'execute as {at} run data merge entity @s {{DeathLootTable:"minecraft:empty"}}')
        g.command(f"kill {at}")


def nearest(g, tile):
    """The fish with food nearest to tile, or None: the next fish of a ship, as the next bush of a villager."""
    return min((t for t, k in g.map.fish.items() if k > 0), key=lambda t: (math.dist(t, tile), t), default=None)


def rate(g, fish):
    """Food per game second of an own fishing ship at fish: the AoE2 DE rate (gather.SHIP_WORK) with the dock
    technologies of the player (gather.SHIP_TECHS, #1439)."""
    import train                                                      # train imports this module
    return gather.SHIP_WORK["shore" if fish in g.map.shore else "deep"] * \
        math.prod(f ** train.count(g, t) for t, (f, _) in gather.SHIP_TECHS.items())


def carry(g):
    """Food of one trip of an own fishing ship: CARRY and the more food of the dock technologies (#1439)."""
    import train                                                      # train imports this module
    return CARRY + sum(c * train.count(g, t) for t, (_, c) in gather.SHIP_TECHS.items())


def work(g, v, dt):
    """One step of fishing ship v without a path, dt game seconds: at the fish it gathers at the AoE2 DE rate
    (rate()) up to carry(), then sails to the nearest own dock; there the food goes into the stock, and it sails
    back to its fish or to the next fish. An empty fish is removed."""
    m = g.map
    if v.state == "to_tree":
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
        if v.load >= full or v.tree not in m.fish:
            docks = set().union(*(m.around(c, water=True) for c in m.docks))
            if not docks or not sail_to(g, v, "to_drop", docks):
                v.state = "idle"
    elif v.state == "to_drop":
        g.command(f"scoreboard players add Food {g.board} {v.load}")
        g.stock["food"] += v.load
        v.load = 0
        g.event(v, "drop")
        v.tree = v.tree if m.fish.get(v.tree, 0) > 0 else nearest(g, v.tree)
        if v.tree is None or not sail_to(g, v, "to_tree", spots(g, v.tree)):
            v.state = "idle"
