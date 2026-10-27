"""
Construction sites in the game program (#417, part of #394). A player chooses a building with `/trigger aoe_build
set N` (players without operator rights can run /trigger), then right clicks the ground with the command stick.
When the footprint is free and the stock pays the cost, a foundation appears: a ring of wool in the player color.
The ring stays until the building is complete, so a player sees which buildings are not finished.
The footprint is blocked for paths. gather.Gather.click calls place().
A right click on a foundation sends the selected villagers there to build it (#418): the blocks of the design
(replay.Replay.building) appear from the bottom up, in the AoE2 build time. gather.Gather.step calls rise().
A complete building works (#419): a camp, mill or town center is a drop site, a farm can be farmed.
A right click on a selected villager opens the build menu (#621): a chest menu (menu.py) with one item per building.
A click chooses the building as /trigger does and closes the menu, so the next right click places it.
Ages (#674): a Feudal Age building or unit (AGE) is locked until the player researches the Feudal Age (train.py):
its item is gray, says "Needs the Feudal Age", and a click does nothing.
Ghost (#794): while a player has a building chosen, a ghost of its design follows the ground that he looks at (block
displays of the Paper plugin, Ghost.java): green where it can stand, red where not. ghosts() sends the shape once.
Walls (#1322): a wall (WALLS) takes two clicks, the start and the end of the line, as the drag of AoE2. Each tile of
the line (aoe2mc.wall_tiles, as the replay) is one construction site with the cost of one tile; a tile on a building,
a tree or water is left out. The builders of a tile go on to the next unfinished tile of the line (gather.Gather.step).
Gates (#1324): a gate (GATES) goes on 4 own wall tiles in a straight line along x or z, as in AoE2 (4 x 1 tiles). It
replaces them: a wall site goes (its builders go on to the gate), a complete wall tile loses its target. The gate stays
closed for now.
Fortified Wall (#1326, train.WALL_UPGRADES): the new and the complete own stone walls and gates get the fortified design
and its hit points (design(), upgrade()); a damaged one keeps its lost hit points, as in AoE2.
"""
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aoe2mc import VERSION_NAME, wall_tiles  # noqa: E402
from buildings import footprint  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import civs  # noqa: E402
import menu as chest  # noqa: E402  (menu() below is the chat text)
from replay import Replay  # noqa: E402

COSTS = {"HOUSE": {"wood": 25}, "LUMBER_CAMP": {"wood": 100}, "MINING_CAMP": {"wood": 100},   # as in AoE2
         "MILL": {"wood": 100}, "FARM": {"wood": 60}, "BARRACKS": {"wood": 175},
         "BLACKSMITH": {"wood": 150},
         "BOMBARD_TOWER": {"gold": 100, "stone": 125},             # after the technology Bombard Tower (#1375)
         "ARCHERY_RANGE": {"wood": 175}, "STABLE": {"wood": 175}, "TOWN_CENTER": {"wood": 275, "stone": 100},
         "CASTLE": {"stone": 650},                                 # the Castle Age: the Imperial Age needs them (#1162)
         "DOCK": {"wood": 150},                                    # 3 x 3 tiles on water at the shore (#1382)
         "GATE": {"stone": 30},                                    # 4 x 1 tiles (AoE2 DE wiki, #1324)
         "MARKET": {"wood": 175},                                  # the Feudal Age (#1251)
         "MONASTERY": {"wood": 175},
         "PALISADE_GATE": {"wood": 30},
         "PALISADE_WALL": {"wood": 3},                             # per tile (AoE2 DE wiki, #1322)
         "SIEGE_WORKSHOP": {"wood": 200},
         "STONE_WALL": {"stone": 5},                               # per tile
         "UNIVERSITY": {"wood": 200},
         "WATCH_TOWER": {"wood": 35, "stone": 125},                # AoE2 DE (wiki: 25 wood before patch 5.8)
         "WONDER": {"wood": 1000, "gold": 1000, "stone": 1000}}
BUILD_TIMES = {"HOUSE": 25, "LUMBER_CAMP": 35, "MINING_CAMP": 35, "MILL": 35, "FARM": 15,   # AoE2 seconds,
               "BARRACKS": 50, "ARCHERY_RANGE": 50, "STABLE": 50, "TOWN_CENTER": 150,                              # one builder
               "BLACKSMITH": 40,
               "BOMBARD_TOWER": 80,
               "CASTLE": 200,
               "DOCK": 35,
               "GATE": 70,
               "MARKET": 60,
               "MONASTERY": 40,
               "PALISADE_GATE": 30,
               "PALISADE_WALL": 7,
               "SIEGE_WORKSHOP": 40,
               "STONE_WALL": 10,
               "UNIVERSITY": 60,
               "WATCH_TOWER": 80,
               "WONDER": 3500}
MENU = list(COSTS)                                                 # trigger value N -> MENU[N - 1]
OBJECTIVE = "aoe_build"
ICONS = {"HOUSE": "spruce_stairs", "LUMBER_CAMP": "oak_log", "MINING_CAMP": "raw_gold_block",   # a block of the
         "MILL": "white_wool", "FARM": "wheat", "BARRACKS": "stone_brick_wall", "ARCHERY_RANGE": "target",
         "BLACKSMITH": "anvil", "STABLE": "hay_block",
         "BOMBARD_TOWER": "polished_basalt",                            # the cannon barrels
         "CASTLE": "stone_bricks",
         "DOCK": "dark_oak_planks",                                     # the wood of the pier
         "GATE": "iron_bars",                                           # the portcullis
         "MARKET": "barrel",                                            # the goods of the stalls
         "MONASTERY": "bell",
         "PALISADE_GATE": "stripped_spruce_log",                        # the beam over the passage
         "PALISADE_WALL": "spruce_fence",
         "SIEGE_WORKSHOP": "grindstone",
         "STONE_WALL": "mossy_stone_bricks",
         "UNIVERSITY": "bookshelf",
         "WATCH_TOWER": "cracked_stone_bricks",
         "WONDER": "weathered_cut_copper_stairs",                       # the copper roof
         "TOWN_CENTER": "cobblestone"}                                  # design
AGE_TECHS = ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")           # the technologies of the ages, in order
AGE = dict.fromkeys(("ARCHERY_RANGE", "STABLE", "BLACKSMITH", "MARKET", "WATCH_TOWER",   # the AoE2 age of each
                     "ARCHER", "SKIRMISHER", "SPEARMAN", "SCOUT_CAVALRY", "TRADE_CART",  # building, unit and age
                     "GATE",
                     "STONE_WALL",
                     "CASTLE_AGE"), 1) | {"IMPERIAL_AGE": 2} \
    | dict.fromkeys((                                                  # the Castle Age (#1082): buildings and units
        "BATTERING_RAM",
        "CAMEL_RIDER",
        "CASTLE",
        "CAVALRY_ARCHER",
        "CROSSBOWMAN",
        "ELITE_SKIRMISHER",
        "HEAVY_CAVALRY_ARCHER",
        "KNIGHT",
        "LIGHT_CAVALRY",
        "LONG_SWORDSMAN",
        "MANGONEL",
        "MONASTERY",
        "MONK",
        "PIKEMAN",
        "SCORPION",
        "SIEGE_TOWER",
        "SIEGE_WORKSHOP",
        "UNIVERSITY",
    ), 2) | dict.fromkeys((                                           # the Imperial Age (unique units: train.UNIQUE)
        "ARBALESTER",
        "BOMBARD_CANNON",
        "BOMBARD_TOWER",
        "CAPPED_RAM",
        "CAVALIER",
        "CHAMPION",
        "HALBERDIER",
        "HEAVY_CAMEL_RIDER",
        "HUSSAR",
        "KEEP",
        "ONAGER",
        "PALADIN",
        "SIEGE_RAM",
        "TREBUCHET",
        "TWO_HANDED_SWORDSMAN",
        "WONDER",
    ), 3)                                                              # (0: Dark)
WALLS = ("PALISADE_WALL", "STONE_WALL")                            # a line of 1-tile sites with two clicks (#1322)
GATES = ("GATE", "PALISADE_GATE")                                  # on 4 own wall tiles in a line (#1324)
NEEDS = {"BOMBARD_TOWER": "BOMBARD_TOWER_TECH"}                    # a building after a technology (#1375)
SHORE = ("DOCK",)                                                  # on water next to the land, as in AoE2 (#1382)
GHOST = 400                                                        # block displays of one ghost: a coarser shape above
LOCKED = "gray_dye"                                                # the item of a locked building or unit


def pretty(name):
    return name.replace("_", " ").title()


def setup(g):
    g.command(f"scoreboard objectives add {OBJECTIVE} trigger")
    g.ghosts, g.shapes = {}, {}                                        # player -> [building, color]; building -> shape


def tick(g):
    """Players who joined since the last tick get the menu; all players may use the trigger (it locks after use)."""
    g.command(f"execute as @a unless score @s {OBJECTIVE} matches 0.. run tellraw @s {menu()}")
    g.command(f"scoreboard players add @a {OBJECTIVE} 0")
    g.command(f"scoreboard players enable @a {OBJECTIVE}")
    if getattr(g, "paper", False):
        ghosts(g)


def shape(blocks, limit=GHOST):
    """The ghost of a design: its outer blocks {(x, y, z): state} (a block with a free side), and the scale. Above
    limit blocks, each cell of k × k × k blocks becomes one block of size k (k = 2, 4 ...)."""
    k, cells = 1, dict(blocks)
    while True:
        out = {p: v for p, v in cells.items()
               if any((p[0] + a, p[1] + b, p[2] + c) not in cells for a, b, c in
                      ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)))}
        if len(out) <= limit:
            return out, k
        k *= 2
        cells = {}
        for (x, y, z), v in sorted(blocks.items()):
            cells.setdefault((x // k, y // k, z // k), v)


def ghost_commands(g, player, name, rect, origin=None):
    """The plugin commands that give player the ghost of building name: its design at rect (x0, x1, z0, z1) without
    the cleared air and the foundation, relative to the floor of the north-west corner, or of the block column origin
    (x, z) where the plugin puts the ghost (a gate: the tile under the cursor, #1357). At most 1446 bytes per RCON
    command: the shape goes in parts. An empty list where the design does not stand (outside the map, on water)."""
    T, (ox, oz) = g.map.T, origin or (rect[0], rect[2])
    along_z = rect[3] - rect[2] > rect[1] - rect[0]                    # a gate along z
    key = name if (along_z, rect[0] - ox, rect[2] - oz) == (False, 0, 0) else (name, along_z, rect[0] - ox, rect[2] - oz)
    if key not in g.shapes:
        cmds = Replay(g, g.data, getattr(g.game, "version", VERSION_NAME)).building(
            name, g.player, (rect[0] + rect[1]) / 2 / T, (rect[2] + rect[3]) / 2 / T, along_z=along_z)
        blocks, base = {}, None
        for c in cmds:
            b, state = box(c) or (None, None)
            if b is None or c.endswith(" keep"):                       # the foundation under the floor
                continue
            if base is None:                                           # the first fill clears the footprint
                base = b[1]
            if state.split("[")[0] in ("air", "minecraft:air", "barrier", "minecraft:barrier"):
                continue
            for x in range(b[0], b[3] + 1):
                blocks[x - ox, b[1] - base, b[2] - oz] = state.removeprefix("minecraft:")
        if not blocks:
            return []
        g.shapes[key] = shape(blocks)
    parts, k = g.shapes[key]
    out, line = [f"aoe ghost-clear {player}"], ""
    for (x, y, z), state in sorted(parts.items()):
        t = f" {x}/{y}/{z}/{state}"
        if len(line) + len(t) > 1300:
            out.append(f"aoe ghost-shape {player} {k}{line}")
            line = ""
        line += t
    return out + [f"aoe ghost-shape {player} {k}{line}"] * bool(line) + [f"aoe ghost {player} {g.map.T} {footprint(name)}"]


def ghosts(g):
    """Each tick: the players who chose a building see its ghost (#794), green over a free footprint and red over a
    blocked one, as place() tests it; the ghost goes away when the choice ends (placed, cancelled)."""
    import gather                                                      # gather imports build
    who = {}
    if "passed" in g.command(f"execute if entity @a[scores={{{OBJECTIVE}=1..}}]"):
        for p in (n.strip() for n in g.command("list").split(":", 1)[-1].split(",")):
            if p and (name := chosen(g, p)) and not locked(g, name):
                who[p] = name
    for p in [p for p in g.ghosts if p not in who]:
        g.command(f"aoe ghost-clear {p}")
        del g.ghosts[p]
    for p, name in who.items():
        pos = g.pos(p)
        rot = [float(v) for v in re.findall(gather.NUMBER, g.command(f"data get entity {p} Rotation").rsplit(":", 1)[-1])]
        eye, d = pos and (pos[0], pos[1] + 1.62, pos[2]), len(rot) == 2 and gather.direction(*rot)
        cell = pos and d and (pick_shore(g, eye, d) if name in SHORE else g.map.pick_ground(eye, d))
        if not cell:
            continue
        rect, spot, T = area(g, name, cell), None, g.map.T
        if name in GATES:                                              # on the wall tiles of gate_rect, else along x
            corner = (cell[0] // T * T, cell[1] // T * T)
            spot = gate_rect(g, cell) or (corner[0] - 2 * T, corner[0] + 2 * T, corner[1], corner[1] + T)
        if g.ghosts.get(p, [None])[0] != name or g.ghosts[p][2:] != [spot]:
            if not (cmds := ghost_commands(g, p, name, spot or rect, spot and corner)):
                continue
            for c in cmds:
                g.command(c)
            g.ghosts[p] = [name, None, spot]
        ok = gate_rect(g, cell) if name in GATES else shore(g, rect) if name in SHORE else free(g, rect)
        color = "green" if ok else "red"                               # a gate: on a wall, a dock: at the shore
        if g.ghosts[p][1] != color:
            g.command(f"aoe ghost-color {p} {color}")
            g.ghosts[p][1] = color


def ages(g):
    """The number of ages that the player researched: 0 in the Dark Age."""
    return sum(t in getattr(g, "techs", ()) for t in AGE_TECHS)


def locked(g, name):
    """The text "Needs the ... Age" when the player is not yet in the AoE2 age of building or unit name, else None."""
    if g is not None and AGE.get(name, 0) > ages(g):
        return f"Needs the {('Dark', 'Feudal', 'Castle', 'Imperial')[AGE[name]]} Age"
    if g is not None and name in NEEDS and NEEDS[name] not in getattr(g, "techs", ()):
        return "Needs " + pretty(NEEDS[name].removesuffix("_TECH"))


def menu():
    lines = [f"/trigger {OBJECTIVE} set {i}: {pretty(n)} ({', '.join(f'{v} {r}' for r, v in COSTS[n].items())})"
             for i, n in enumerate(MENU, 1)]
    return json.dumps({"text": "Build: " + "\n".join(lines), "color": "gray"})


def price(g, name, player=None):
    """The cost of building name for the player of g (or another player), with the bonuses of the civilization
    (civs.COSTS, #1091)."""
    return civs.cost(g, name, COSTS[name], player) if g is not None else COSTS[name]


def items(g=None):
    """The items of the build menu: (slot, icon, name, lore) with the cost and the build time. With g: the cost of the
    civilization, and a building of a later age is gray and says which age it needs."""
    return [(i, LOCKED if locked(g, n) else ICONS[n], pretty(n),
             "\n".join([", ".join(f"{v} {r}" for r, v in price(g, n).items()) or "free", f"{BUILD_TIMES[n]} s"]
                       + [locked(g, n)] * bool(locked(g, n)))) for i, n in enumerate(MENU)]


def open_menu(g, player):
    """Show the build menu. A click sets the trigger score, as /trigger aoe_build set N does, and closes the menu."""
    def choose(p, slot, shift):                                        # shift: one building all the same
        if slot < len(MENU) and not locked(g, MENU[slot]):
            g.command(f"scoreboard players set {p} {OBJECTIVE} {slot + 1}")
            chest.close(g, p)
    return chest.show(g, player, "Build", items(g), choose)


def chosen(g, player):
    """The building that the player chose with /trigger, or None."""
    out = g.command(f"scoreboard players get {player} {OBJECTIVE}")
    n = int(out.split(" has ")[1].split()[0]) if " has " in out else 0
    return MENU[n - 1] if 0 < n <= len(MENU) else None


def say(g, player, text):
    g.command(f"tellraw {player} " + json.dumps({"text": text, "color": "red"}))


def area(g, name, cell):
    """The block footprint (x0, x1, z0, z1) of building name with the block cell under the cursor in its middle tile."""
    T, s = g.map.T, footprint(name)
    tx, tz = cell[0] // T - s // 2, cell[1] // T - s // 2
    return tx * T, (tx + s) * T, tz * T, (tz + s) * T


def free(g, rect):
    x0, x1, z0, z1 = rect
    return all(g.map.free(x, z) and (x, z) not in g.map.farm_at for x in range(x0, x1) for z in range(z0, z1))


def shore(g, rect):
    """True when the footprint rect is all free water and touches free land (a dock, #1382): not on land, not on the
    open sea. The builders stand on that land (Gather.build)."""
    x0, x1, z0, z1 = rect
    cells = {(x, z) for x in range(x0, x1) for z in range(z0, z1)}
    return all(g.map.wet(*c) for c in cells) and bool(g.map.around(cells))


def surface(g, x, z):
    """The y of the water surface at the water cell (x, z), as Map.sea, or None more than 2 tiles from the land: a
    dock touches the land, and Map.sea reads the whole map there."""
    return g.map.sea(x, z, 2 * g.map.T + 1) if any(
        g.map.y(x + dx, z + dz) is not None for dx in range(-2 * g.map.T - 1, 2 * g.map.T + 2)
        for dz in range(-2 * g.map.T - 1, 2 * g.map.T + 2)) else None


def pick_shore(g, eye, d, reach=64):
    """The block cell (x, z) of the ground or of the water surface near the land that the ray from eye in direction d
    hits first, or None: Map.pick_ground goes through the water, and a dock stands on it (#1382)."""
    for k in range(1, reach * 4):
        x, y, z = (eye[i] + d[i] * k / 4 for i in range(3))
        bx, bz = math.floor(x), math.floor(z)
        if not (0 <= bx < g.map.n and 0 <= bz < g.map.n):
            return None
        top = g.map.y(bx, bz)
        if (top if top is not None else surface(g, bx, bz) or -1e9) > y:
            return bx, bz
    return None


def place(g, player, name, eye, d):
    """Place a foundation of name at the ground that the player looks at. Returns the site or None."""
    if need := locked(g, name):                                        # a /trigger choice of a later age
        say(g, player, f"{pretty(name)}: {need}.")
        return None
    cell = pick_shore(g, eye, d) if name in SHORE else g.map.pick_ground(eye, d)
    if cell is None:
        return None
    if name in WALLS:
        return wall(g, player, name, cell)
    if name in GATES:
        return gate(g, player, name, cell)
    rect = area(g, name, cell)
    if name in SHORE and not shore(g, rect):
        say(g, player, f"A {pretty(name).lower()} must stand on water next to the shore.")
        return None
    if name not in SHORE and not free(g, rect):
        say(g, player, f"No space for the {pretty(name).lower()} here.")
        return None
    cost = price(g, name)
    if any(g.stock[r] < v for r, v in cost.items()):
        say(g, player, f"Not enough resources: a {pretty(name).lower()} costs "
                       + ", ".join(f"{v} {r}" for r, v in cost.items()) + ".")
        return None
    site = found(g, name, rect)
    g.command(f"scoreboard players set {player} {OBJECTIVE} 0")
    return site


def wall(g, player, name, cell):
    """The first click keeps the start cell of the wall line; the second one places a site on each free tile from the
    start to cell (a click on the start tile: one tile). Returns the first site of the line, or None."""
    start = vars(g).setdefault("wall_start", {}).pop(player, None)
    if start is None or start[0] != name:
        g.wall_start[player] = (name, cell)
        g.command(f"tellraw {player} " + json.dumps({"text": f"{pretty(name)}: right click the end of the wall.",
                                                       "color": "gray"}))
        return None
    T = g.map.T
    rects = [r for x, z in wall_tiles(start[1][0] // T, start[1][1] // T, cell[0] // T, cell[1] // T)
             if free(g, r := (x * T, (x + 1) * T, z * T, (z + 1) * T))]
    if not rects:
        say(g, player, f"No space for the {pretty(name).lower()} here.")
        return None
    cost = {r: v * len(rects) for r, v in price(g, name).items()}
    if any(g.stock[r] < v for r, v in cost.items()):
        say(g, player, f"Not enough resources: {len(rects)} tiles of {pretty(name).lower()} cost "
                       + ", ".join(f"{v} {r}" for r, v in cost.items()) + ".")
        return None
    sites = [found(g, name, r) for r in rects]
    for site in sites:
        site["line"] = rects[0]                                        # the line: the footprint of its first tile
    g.command(f"scoreboard players set {player} {OBJECTIVE} 0")
    return sites[0]


def wall_tiles_of(g):
    """The own wall tiles of the player of g: {(tile x, tile z): the site, or None for a wall of the map}."""
    T, out = g.map.T, {}
    for o in g.data["objects"]:
        if o["kind"] == "building" and o["player"] == g.player and "WALL" in o["name"] and "footprint" in o:
            x0, z0, x1, z1 = o["footprint"]
            if x1 - x0 == z1 - z0 == T:
                out[x0 // T, z0 // T] = None
    out.update({(s["footprint"][0] // T, s["footprint"][2] // T): s for s in g.sites
                if s["name"] in WALLS and s["player"] == g.player})
    return out


def gate_rect(g, cell):
    """The block footprint (x0, x1, z0, z1) of a gate on 4 own wall tiles in a line along x or z, with the tile of
    the block cell in it (the tile in the middle first), or None."""
    T, own = g.map.T, wall_tiles_of(g)
    tx, tz = cell[0] // T, cell[1] // T
    for d in (2, 1, 3, 0):                                             # the offset of the clicked tile in the gate
        if all((tx - d + i, tz) in own for i in range(4)):
            return (tx - d) * T, (tx - d + 4) * T, tz * T, (tz + 1) * T
        if all((tx, tz - d + i) in own for i in range(4)):
            return tx * T, (tx + 1) * T, (tz - d) * T, (tz - d + 4) * T
    return None


def gate(g, player, name, cell):
    """Put a gate on the own wall line at cell: it replaces the 4 wall tiles under it (AoE2: no refund). Returns the
    site, or None (no straight wall line of 4 tiles there, not enough resources)."""
    rect = gate_rect(g, cell)
    if rect is None:
        say(g, player, f"A {pretty(name).lower()} must go on 4 tiles of an own wall in a straight line.")
        return None
    cost = price(g, name)
    if any(g.stock[r] < v for r, v in cost.items()):
        say(g, player, f"Not enough resources: a {pretty(name).lower()} costs "
                       + ", ".join(f"{v} {r}" for r, v in cost.items()) + ".")
        return None
    import combat                                                      # combat -> gather -> build: import it late
    x0, x1, z0, z1 = rect
    T, own = g.map.T, wall_tiles_of(g)
    old = [s for t, s in own.items() if s and x0 <= t[0] * T < x1 and z0 <= t[1] * T < z1]
    builders = {v.uuid for v in getattr(g, "villagers", {}).values() if v.site in old}
    for s in old:
        g.sites.remove(s)
        if s["progress"] >= 1:                                         # a complete tile: its target goes
            g.command(f"kill {combat.target_uuid([s['footprint'][i] for i in (0, 2, 1, 3)])}")
        else:                                                          # the wool ring of a foundation goes
            for p, state in s["ring"].items():
                g.command("setblock {} {} {} ".format(*p) + s["under"].get(p, "minecraft:air"))
    site = found(g, name, rect)
    g.command(f"scoreboard players set {player} {OBJECTIVE} 0")
    if builders:
        g.build(site, builders)
    return site


def next_tile(g, site):
    """The nearest unfinished site of the wall line of site, or None."""
    rest = [s for s in g.sites if "line" in site and s.get("line") == site["line"] and s["progress"] < 1 and s is not site]
    return min(rest, key=lambda s: math.dist(s["footprint"][::2], site["footprint"][::2]), default=None)


def near(g, name, cell, reach=12):
    """A free footprint of name whose middle tile is next to the block cell (a source or the town center), with one
    free block around it for the paths, or None. The nearest tile first, the same order each time."""
    T, (cx, cz) = g.map.T, (cell[0] // g.map.T, cell[1] // g.map.T)
    for r in range(1, reach + 1):
        for tx, tz in sorted(((x, z) for x in range(cx - r, cx + r + 1) for z in range(cz - r, cz + r + 1)
                              if max(abs(x - cx), abs(z - cz)) == r), key=lambda t: (math.dist(t, (cx, cz)), t)):
            x0, x1, z0, z1 = rect = area(g, name, (tx * T, tz * T))
            if x0 > 0 and z0 > 0 and free(g, (x0 - 1, x1 + 1, z0 - 1, z1 + 1)):
                return rect
    return None


def found(g, name, rect):
    """Pay for name and put its foundation (a wool ring in the player color) on the free footprint rect. Returns
    the construction site."""
    for r, v in price(g, name).items():
        g.stock[r] -= v
        g.command(f"scoreboard players remove {r.capitalize()} {g.board} {v}")
    x0, x1, z0, z1 = rect
    color = g.players.get(str(g.player), {}).get("color", "light_gray")
    ring = [(x, g.map.y(x, z) if g.map.y(x, z) is not None else int(g.map.sea(x, z)), z)   # a dock: on the water
            for x in range(x0, x1) for z in range(z0, z1) if x in (x0, x1 - 1) or z in (z0, z1 - 1)]
    for c in ring:
        g.command("setblock {} {} {} ".format(*c) + f"minecraft:{color}_wool")
    g.map.blocked |= {(x, z) for x in range(x0, x1) for z in range(z0, z1)}
    T = g.map.T                                                        # the design, bottom up (one command each)
    cmds = Replay(g, g.data, getattr(g.game, "version", VERSION_NAME)).building(
        design(g, name, g.player), g.player, (x0 + x1) / 2 / T, (z0 + z1) / 2 / T, along_z=z1 - z0 > x1 - x0)   # a gate along z (#1324)
    site = {"name": name, "player": g.player, "footprint": rect, "commands": cmds, "sent": 0, "progress": 0.0,
            "ring": dict.fromkeys(ring, f"minecraft:{color}_wool"), "under": {}}   # under: the design blocks on the ring
    g.sites.append(site)
    return site


def pick(g, eye, d):
    """The unfinished construction site on the ground that the player looks at, or None."""
    cell = g.map.pick_ground(eye, d)
    return next((s for s in g.sites if s["progress"] < 1 and cell and s["footprint"][0] <= cell[0] < s["footprint"][1]
                 and s["footprint"][2] <= cell[1] < s["footprint"][3]), None)


def box(cmd):
    """The box (x0, y0, z0, x1, y1, z1) and the block state of a /setblock or /fill command, or None."""
    t = cmd.split()
    if t[0] == "setblock":
        return (*map(int, t[1:4]), *map(int, t[1:4])), t[4]
    if t[0] == "fill":
        return tuple(map(int, t[1:7])), t[7]
    return None


def rise(g, site, work):
    """Add work (game seconds of one builder) to the site and send the commands of the blocks that are due.
    The wool ring stays on top of the design until the building is complete. Returns True when it is complete."""
    site["progress"] = min(1.0, site["progress"] + work / BUILD_TIMES[site["name"]])
    cmds, ring = site["commands"], site.get("ring", {})
    k = len(cmds) if site["progress"] >= 1 else math.floor(site["progress"] * len(cmds))
    hit = set()
    for c in cmds[site["sent"]:k]:
        g.command(c)
        if ring and (b := box(c)):                                     # remember the design block, keep the wool
            (x0, y0, z0, x1, y1, z1), state = b
            for p in ring:
                if x0 <= p[0] <= x1 and y0 <= p[1] <= y1 and z0 <= p[2] <= z1:
                    site["under"][p] = state
                    hit.add(p)
    site["sent"] = max(site["sent"], k)
    if site["progress"] < 1:
        for p in sorted(hit):
            g.command("setblock {} {} {} ".format(*p) + ring[p])
    if site["progress"] >= 1 and not site.get("done"):                 # complete: the building works (#419)
        site["done"] = True
        for p in [p for p in ring if p not in hit]:                    # the ring goes: the design or air
            g.command("setblock {} {} {} ".format(*p) + site["under"].get(p, "minecraft:air"))
        x0, x1, z0, z1 = site["footprint"]
        s, T = footprint(site["name"]), g.map.T
        if "FARM" in site["name"]:                                     # free ground again: the farmer stands on it
            g.map.blocked -= {(x, z) for x in range(x0, x1) for z in range(z0, z1)}
        g.map.building(site["name"], site["footprint"], (x0 // T + s // 2, z0 // T + s // 2), site["player"] == g.player)
        target(g, site)
    return site["progress"] >= 1


def design(g, name, player):
    """The design of building name of player: a stone wall (gate) of the player after Fortified Wall is a fortified
    wall (gate), #1326."""
    import train                                                       # train imports this module
    new = {old: wall for t, walls in train.WALL_UPGRADES.items() if t in getattr(g, "techs", ()) for old, wall in walls.items()}
    return new.get(name, name) if player == g.player else name


def line(g, name, techs=None):
    """The building whose AoE2 values building name of the player of g has: a watch tower after Guard Tower (Keep) has
    those of the guard tower (keep), #1374. techs: the technologies (default: those of the player)."""
    import train                                                       # train imports this module
    techs = getattr(g, "techs", ()) if techs is None else techs
    for t, towers in train.TOWER_UPGRADES.items():                     # in the research order
        name = towers.get(name, name) if t in techs else name
    return name


def values(g, name, techs=None):
    """The AoE2 values of building name of the player of g: those of its tower (line, #1374) with the building
    technologies (train.TECHS: Chemistry, Masonry, #1398). techs: the technologies (default: those of the player)."""
    import combat, train                                               # combat -> gather -> build: import it late
    techs = getattr(g, "techs", ()) if techs is None else techs
    s = combat.stats(line(g, name, techs))
    for t in sorted(techs):
        s = train.TECHS[t](name, s)
    return s


def retower(g, before):
    """The complete own buildings get their new values after a tower technology (#1374) or Masonry (#1398, values): the
    target keeps its lost hit points, as a wall (upgrade). before: the technologies before the research. A destroyed
    building stays air."""
    import combat, repair                                              # combat -> gather -> build: import it late
    rects = [(x0, x1, z0, z1, o["name"]) for o in g.data["objects"] if o["kind"] == "building" and o["player"] == g.player
             and "footprint" in o for x0, z0, x1, z1 in [o["footprint"]]] \
        + [(*s["footprint"], s["name"]) for s in g.sites if s.get("done") and s["player"] == g.player]
    for x0, x1, z0, z1, name in rects:
        a, b, new = values(g, name, before), values(g, name), line(g, name)
        if a == b or (hp := repair.hp(g, (x0, x1, z0, z1))) is None or hp <= 0:
            continue
        uuid = combat.target_uuid([x0, z0, x1, z1])
        box = combat.building_box({"footprint": [x0, z0, x1, z1]}, g.map.ground)
        for c in [c for c in combat.building(uuid, new, g.player, box, g.map.T, s=b) if c.startswith("aoe building ")] \
                + [f"scoreboard players set {uuid} aoe_hp {min(b.hp, hp + b.hp - a.hp)}", combat.label_command(uuid, new)]:
            g.command(c)


def upgrade(g, site, old, redraw=True):
    """The complete wall site gets the hit points of its wall in the present age (combat.wall), and with redraw the
    design of its new wall after a wall technology (#1326). old: its Stats before the change (the old wall, or the
    last age: #1372). The target keeps its lost hit points, as in AoE2 (the score aoe_hp, repair.hp). A destroyed
    wall stays air."""
    import combat, repair                                              # combat -> gather -> build: import it late
    x0, x1, z0, z1 = site["footprint"]
    name, T = design(g, site["name"], site["player"]), g.map.T
    new = combat.wall(name, ages(g))
    if new == old or (hp := repair.hp(g, (x0, x1, z0, z1))) is None or hp <= 0:
        return
    for c in Replay(g, g.data, getattr(g.game, "version", VERSION_NAME)).building(
            name, site["player"], (x0 + x1) / 2 / T, (z0 + z1) / 2 / T, along_z=z1 - z0 > x1 - x0) * redraw:   # as found()
        g.command(c)
    uuid = combat.target_uuid([x0, z0, x1, z1])
    box = combat.building_box({"footprint": [x0, z0, x1, z1]}, g.map.ground)
    for c in [c for c in combat.building(uuid, name, site["player"], box, T, s=new) if c.startswith("aoe building ")] \
            + [f"scoreboard players set {uuid} aoe_hp {min(new.hp, hp + new.hp - old.hp)}", combat.label_command(uuid, name)]:
        g.command(c)


def target(g, site):
    """A complete building of combat.BUILDINGS gets its target entity, as a building of the map (combat.setup): the
    AoE2 hit points, and the arrows of a town center, tower or castle (#1202). wonder.tick makes the one of a wonder."""
    import combat                                                      # combat -> gather -> build: import it late
    if site["name"] not in combat.BUILDINGS and site["name"] not in combat.WALLS or site["name"] == "WONDER":
        return
    x0, x1, z0, z1 = site["footprint"]
    uuid = combat.target_uuid([x0, z0, x1, z1])
    box = combat.building_box({"footprint": [x0, z0, x1, z1]}, g.map.ground)
    wall, name = site["name"] in combat.WALLS, line(g, design(g, site["name"], site["player"]))   # the hit points of the age
                                                                       # (#1322), a guard tower or keep (#1374)
    s = combat.wall(name, ages(g)) if wall else values(g, name)                  # Chemistry (#1375), Masonry (#1398)
    for c in combat.building(uuid, name, site["player"], box, g.map.T, s=s) \
            + [f"tag {uuid} add {combat.WALL_TAG}"] * wall + [combat.label_command(uuid, name)]:
        g.command(c)
    if site["player"] != g.player:                                     # an enemy building: the player can attack it
        g.forts[uuid], g.fort_names[uuid] = box, site["name"]
