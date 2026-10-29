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
Rows (#1805): a sneak right click (Shift) places a foundation and keeps the choice, as the shift click of AoE2. The
selected villagers build the foundations of the row in the order of the clicks (next_tile).
Gates (#1324): a gate (GATES) goes on 4 own wall tiles in a straight line along x or z, as in AoE2 (4 x 1 tiles), or
on 3 tiles of a diagonal line (3 x 3 tiles, #1655). It replaces them: a wall site goes (its builders go on to the
gate), a complete wall tile loses its target.
A complete gate gets a portcullis across its passage (#1325, #1656, portcullis()): iron bars from the ground to the top
of the passage. On Paper the plugin raises them while an own or allied unit is near or walks a path through the gate
(aoe gate, Gates.java), as the AoE2 gate (the decision #1323).
Fortified Wall (#1326, the key "walls" of train.jsonl): the new and the complete own stone walls and gates get the fortified design
and its hit points (design(), upgrade()); a damaged one keeps its lost hit points, as in AoE2.
Minimap (#2582, epic #2580): on Paper each building is a square in the player color on map 0 (`aoe minimap building`,
Minimap.java) from its foundation on (found()), and its square goes when it falls (gather.Gather.fall: `aoe minimap
unbuild`). run.play draws the buildings of the start (minimap()). With the fog of war, the plugin shows an enemy
building to a team only after a tile of it was in its sight (fog.minimap, #2583).
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
import herd  # noqa: E402
import menu as chest  # noqa: E402  (menu() below is the chat text)
import monk  # noqa: E402
import record  # noqa: E402
from replay import Replay  # noqa: E402
import table  # noqa: E402
import units  # noqa: E402

# The buildings of the menu (in menu order), the age of each building, unit and age, and the technology that each
# needs: one line per name in data/build.jsonl (#2028). Cost and time as in AoE2 (seconds of one builder).
ROWS = table.load("build.jsonl")
COSTS = {r["name"]: r["cost"] for r in ROWS if "cost" in r}
BUILD_TIMES = {r["name"]: r["time"] for r in ROWS if "time" in r}
MILITARY = {r["name"] for r in ROWS if r.get("military")}         # the AoE2 "Handicap" speeds them up (civs.work_rate, #2474)
FOLWARK_SHARE, FOLWARK_REACH = 0.1, 4                               # of the food of a farm; tiles from the Folwark
MENU = list(COSTS)                                                 # trigger value N -> MENU[N - 1]
OBJECTIVE = "aoe_build"
SNEAK = '{type:"minecraft:entity_properties",entity:"this",predicate:{flags:{is_sneaking:true}}}'   # as gather.SNEAK
ICONS = {r["name"]: r["icon"] for r in ROWS if "icon" in r}           # a block of the design
AGE_TECHS = tuple(r["name"] for r in sorted((r for r in ROWS if "age_tech" in r), key=lambda r: r["age_tech"]))
AGE = {r["name"]: r["age"] for r in ROWS if "age" in r}           # (0: Dark)
WALLS = tuple(r["name"] for r in ROWS if r.get("wall"))          # a line of 1-tile sites with two clicks (#1322)
GATES = tuple(r["name"] for r in ROWS if r.get("gate"))          # on 4 own wall tiles in a line (#1324)
NEEDS = {r["name"]: r["needs"] for r in ROWS if "needs" in r}     # a unit or building after a technology (#1380)
SHORE = ("DOCK",)                                                  # on water next to the land, as in AoE2 (#1382)
WATER = ("FISH_TRAP",)                                             # on free water only, ships build it (#1438)
FLAT = tuple(r["name"] for r in ROWS if r.get("flat"))                 # on one elevation level also for the Thracians (#2545)
MOVES = {r["name"] for r in table.load("buildings.jsonl") if r.get("moves")}   # a mob when complete (cart, #2209)
GHOST = 400                                                        # block displays of one ghost: a coarser shape above
CRANE = 1.2                                                        # the build speed factor of Treadmill Crane (#1422)
NOT_UNITS = ("block_display", "interaction", "item_display", "marker", "text_display")   # ghosts, name lines
LOCKED = "gray_dye"                                                # the item of a locked building or unit


def pretty(name):
    return name.replace("_", " ").title()


def setup(g):
    g.command(f"scoreboard objectives add {OBJECTIVE} trigger")
    g.ghosts, g.shapes = {}, {}                                        # player -> [building, color]; building -> shape


def tick(g):
    """Players who joined since the last tick get the menu; all players may use the trigger (it locks after use)."""
    who = getattr(g, "who", "@a")                                      # two people: only the own team (#1310)
    for text in menu():
        g.command(f"execute as {who} unless score @s {OBJECTIVE} matches 0.. run tellraw @s {text}")
    g.command(f"scoreboard players add {who} {OBJECTIVE} 0")
    g.command(f"scoreboard players enable {who} {OBJECTIVE}")
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


def ghost_commands(g, player, name, rect, origin=None, way=None):
    """The plugin commands that give player the ghost of building name: its design at rect (x0, x1, z0, z1) without
    the cleared air and the foundation, relative to the floor of the north-west corner, or of the block column origin
    (x, z) where the plugin puts the ghost (a gate: the tile under the cursor, #1357). At most 1446 bytes per RCON
    command: the shape goes in parts. An empty list where the design does not stand (outside the map, on water).
    way: the way of a gate (gate_spot), else from the shape of rect."""
    T, (ox, oz) = g.map.T, origin or (rect[0], rect[2])
    along_z = rect[3] - rect[2] > rect[1] - rect[0] if way is None else way   # a gate along z or diagonal (#1655)
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
    import fleet, gather                                               # gather imports build
    who = {}
    if "passed" in g.command(f"execute if entity {gather.only(g.who, f'scores={{{OBJECTIVE}=1..}}')}"):
        for p in g.people():
            if p and (name := chosen(g, p)) and not locked(g, name):
                who[p] = name
    for p in [p for p in g.ghosts if p not in who]:
        g.command(f"aoe ghost-clear {p}")
        del g.ghosts[p]
    for p, name in who.items():
        pos = g.pos(p)
        rot = [float(v) for v in re.findall(gather.NUMBER, g.command(f"data get entity {p} Rotation").rsplit(":", 1)[-1])]
        eye, d = pos and (pos[0], pos[1] + 1.62, pos[2]), len(rot) == 2 and gather.direction(*rot)
        cell = pos and d and (fleet.pick(g, eye, d) if name in SHORE + WATER else g.map.pick_ground(eye, d))
        if not cell:
            continue
        rect, spot, way, T = area(g, name, cell), None, None, g.map.T
        if name in GATES:                                              # on the wall tiles of gate_spot, else along x
            corner = (cell[0] // T * T, cell[1] // T * T)
            spot, way, _ = gate_spot(g, cell) or ((corner[0] - 2 * T, corner[0] + 2 * T, corner[1], corner[1] + T), False, None)
        if g.ghosts.get(p, [None])[0] != name or g.ghosts[p][2:] != [spot, way]:
            if not (cmds := ghost_commands(g, p, name, spot or rect, spot and corner, way)):
                continue
            for c in cmds:
                g.command(c)
            g.ghosts[p] = [name, None, spot, way]
        ok = gate_rect(g, cell) if name in GATES else shore(g, rect) if name in SHORE else water(g, rect) \
            if name in WATER else free(g, rect) and level(g, name, rect)
        color = "green" if ok else "red"                               # a gate: on a wall, a dock: at the shore
        if g.ghosts[p][1] != color:
            g.command(f"aoe ghost-color {p} {color}")
            g.ghosts[p][1] = color


def ages(g):
    """The number of ages that the player researched: 0 in the Dark Age."""
    return sum(t in getattr(g, "techs", ()) for t in AGE_TECHS)


def locked(g, name):
    """The text "Needs the ... Age" when the player is not yet in the AoE2 age of building or unit name, else None.
    An age after the AoE2 setting "Ending age" (aoe2mc.json "end_age", run.py --end-age, #2346) stays locked."""
    if name in AGE_TECHS and AGE_TECHS.index(name) + 1 > getattr(g, "data", {}).get("end_age", len(AGE_TECHS)):
        return f"The game ends in the {('Dark', 'Feudal', 'Castle', 'Imperial')[g.data['end_age']]} Age"   # #2346
    if g is not None and (age := AGE.get(name, 0) - civs.earlier(g, name)) > ages(g):
        return f"Needs the {('Dark', 'Feudal', 'Castle', 'Imperial')[age]} Age"
    if g is not None and name in NEEDS and NEEDS[name] not in getattr(g, "techs", ()):
        return "Needs " + pretty(NEEDS[name].removesuffix("_TECH"))
    from gather import has_mode                                        # gather imports this module
    if name == "TOWN_CENTER" and has_mode(g, "sudden-death") and town_center(g):
        return "Sudden Death: only one town center"                    # (#2407)
    if getattr(g, "mode", None) == "capture-the-relic":
        import combat                                                  # combat -> gather -> build: import it late
        if combat.STANDS_FOR.get(name, name) == "MONASTERY":           # the fortified church too (#1930)
            return "Capture the Relic: no more monasteries"            # (#2458)
    if g is not None and name == "TOWN_CENTER" and ages(g) < (1 if civs.civ(g) == "CUMANS" else 2) and town_center(g):
        return "Needs the Castle Age"                                  # a second one (AoE2; the Cumans: Feudal, #1951)


def town_center(g, player=None):
    """True when the player (default g.player) has a town center: a construction site, or a complete one whose target
    still stands."""
    import combat                                                      # combat imports gather, which imports this module
    player = g.player if player is None else player
    sites = [s for s in getattr(g, "sites", ()) if s["name"] == "TOWN_CENTER" and s["player"] == player]
    if any(not s.get("done") for s in sites):
        return True
    rects = [o["footprint"] for o in g.data.get("objects", ()) if o["kind"] == "building" and o["name"] == "TOWN_CENTER"
             and o["player"] == player and "footprint" in o]
    rects += [[x0, z0, x1, z1] for s in sites for x0, x1, z0, z1 in [s["footprint"]]]
    return any("passed" in g.command(f"execute if entity {combat.target_uuid(r)}") for r in rects)


def hidden(g, name):
    """True when the civilization of the player of g does not have building name (civs.MISSING: a regional building
    such as the Krepost, #1872): the build menu does not show it, as in AoE2."""
    return g is not None and hasattr(g, "data") and civs.missing(g, name)


def menu():
    """The chat texts of the build menu: two halves, else one command is longer than RCON takes (rcon.MAX, #1930)."""
    lines = [f"/trigger {OBJECTIVE} set {i}: {pretty(n)} ({', '.join(f'{v} {r}' for r, v in COSTS[n].items())})"
             for i, n in enumerate(MENU, 1)]
    half = (len(lines) + 1) // 2
    return [json.dumps({"text": text, "color": "gray"})
            for text in ("Build: " + "\n".join(lines[:half]), "\n".join(lines[half:]))]


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


DELETE = 35                                                            # slot: kill the selected own units (#3451)
SHELTER = 44                                     # slot: the selected villagers seek shelter (#3440), last of the next free row


def open_menu(g, player):
    """Show the build menu. A click sets the trigger score, as /trigger aoe_build set N does, and closes the menu.
    A building that the civilization does not have is not in it (hidden); the other items keep their slots.
    Slot DELETE deletes the selected own units (stance.delete, #3451), slot SHELTER sends them into a building (#3440)."""
    def choose(p, slot, shift):                                        # shift: one building all the same
        if slot == DELETE:
            import stance                                              # stance imports gather, gather imports this module
            stance.delete(g)
            chest.close(g, p)
        elif slot == SHELTER:
            import garrison                                            # garrison imports gather, gather imports this module
            garrison.bell(g, p, set(g.selected))
            chest.close(g, p)
        elif slot < len(MENU) and not locked(g, MENU[slot]) and not hidden(g, MENU[slot]):
            g.command(f"scoreboard players set {p} {OBJECTIVE} {slot + 1}")
            chest.close(g, p)
    return chest.show(g, player, "Build", [it for it in items(g) if not hidden(g, MENU[it[0]])]
                      + [(DELETE, "tnt", "Delete", "Kills the selected units"),
                         (SHELTER, "oak_door", "Seek Shelter", "The selected villagers go into the nearest building")], choose)


def chosen(g, player):
    """The building that the player chose with /trigger, or None."""
    out = g.command(f"scoreboard players get {player} {OBJECTIVE}")
    n = int(out.split(" has ")[1].split()[0]) if " has " in out else 0
    return MENU[n - 1] if 0 < n <= len(MENU) and not hidden(g, MENU[n - 1]) else None   # /trigger: as the menu


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


def level(g, name, rect):
    """True when building name may stand on the ground of the footprint rect (AoE2 wiki "Elevation"): a building of
    3 × 3 tiles or more, not a farm, needs one elevation level under it (less height difference than one level). The
    Thracians build the others on any elevation (civ key "any_elevation", #2545), but not the buildings of FLAT (key
    "flat" of data/build.jsonl: the Town Center)."""
    if footprint(name) < 3 or "FARM" in name or name not in FLAT and civs.value("any_elevation", civs.civ(g), 0):
        return True
    x0, x1, z0, z1 = rect
    ys = [y for x in range(x0, x1) for z in range(z0, z1) if (y := g.map.y(x, z)) is not None]
    return not ys or max(ys) - min(ys) < g.data.get("level_height", 3)


def shore(g, rect):
    """True when the footprint rect is all free water and touches free land (a dock, #1382): not on land, not on the
    open sea. The builders stand on that land (Gather.build)."""
    x0, x1, z0, z1 = rect
    cells = {(x, z) for x in range(x0, x1) for z in range(z0, z1)}
    return all(g.map.wet(*c) for c in cells) and bool(g.map.around(cells))


def water(g, rect):
    """True when the footprint rect is all free water (a fish trap, #1438): AoE2 needs no land next to it."""
    x0, x1, z0, z1 = rect
    return all(g.map.wet(x, z) for x in range(x0, x1) for z in range(z0, z1))


def place(g, player, name, eye, d):
    """Place a foundation of name at the ground that the player looks at. Returns the site or None."""
    import fleet                                                       # fleet -> gather -> build: import it late
    if need := locked(g, name):                                        # a /trigger choice of a later age
        say(g, player, f"{pretty(name)}: {need}.")
        return None
    cell = fleet.pick(g, eye, d) if name in SHORE + WATER else g.map.pick_ground(eye, d)   # as the ghost (#2058)
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
    if name in WATER and not water(g, rect):
        say(g, player, f"A {pretty(name).lower()} must stand on the water.")
        return None
    if name not in SHORE + WATER and not free(g, rect):
        say(g, player, f"No space for the {pretty(name).lower()} here.")
        return None
    if not level(g, name, rect):
        say(g, player, f"The {pretty(name).lower()} must stand on flat ground.")
        return None
    cost = price(g, name)
    if any(g.stock[r] < v for r, v in cost.items()):
        say(g, player, f"Not enough resources: a {pretty(name).lower()} costs "
                       + ", ".join(f"{v} {r}" for r, v in cost.items()) + ".")
        return None
    site = found(g, name, rect)
    rows = vars(g).setdefault("rows", {})                              # player -> (building, row) of the sneak clicks (#1805)
    last = rows.pop(player, None)
    site["row"] = last[1] if last and last[0] == name else f"{player} {id(site)}"
    if "passed" in g.command(f"execute as {player} if predicate {SNEAK}"):
        rows[player] = name, site["row"]                               # the shift click of AoE2: the choice stays
    else:
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
    """The block footprint (x0, x1, z0, z1) of a gate on the own wall line at the block cell (gate_spot), or None."""
    return (gate_spot(g, cell) or (None,))[0]


def gate_spot(g, cell):
    """(footprint, way, tiles) of a gate on the own wall tiles at the block cell, or None: 4 tiles in a line along x
    (way False) or z (True), else 3 tiles on a diagonal ("diag+": x and z grow, "diag-": z falls; #1655) with a
    footprint of 3 x 3 tiles, as the diagonal gates of AoE2 and of the converter (buildings.diagonal_gate). The
    tile in the middle first."""
    T, own = g.map.T, wall_tiles_of(g)
    tx, tz = cell[0] // T, cell[1] // T
    for d in (2, 1, 3, 0):                                             # the offset of the clicked tile in the gate
        for along_z in (False, True):
            t = [(tx, tz - d + i) if along_z else (tx - d + i, tz) for i in range(4)]
            if all(c in own for c in t):
                return (t[0][0] * T, (t[-1][0] + 1) * T, t[0][1] * T, (t[-1][1] + 1) * T), along_z, t
    for d in (1, 0, 2):
        for k in (1, -1):
            t = [(tx - d + i, tz + k * (i - d)) for i in range(3)]
            if all(c in own for c in t):
                z0 = min(t[0][1], t[2][1])
                return ((tx - d) * T, (tx - d + 3) * T, z0 * T, (z0 + 3) * T), "diag+" if k > 0 else "diag-", t
    return None


def way(site):
    """The way of the gate site for Replay.building (gate_spot), or of a straight one from its footprint."""
    x0, x1, z0, z1 = site["footprint"]
    return site.get("way", z1 - z0 > x1 - x0)


def tile_cells(g, tiles):
    T = g.map.T
    return {(x, z) for tx, tz in tiles for x in range(tx * T, tx * T + T) for z in range(tz * T, tz * T + T)}


def gate(g, player, name, cell):
    """Put a gate on the own wall line at cell: it replaces the wall tiles under it (gate_spot; AoE2: no refund).
    Returns the site, or None (no wall line of 4 straight or 3 diagonal tiles there, not enough resources)."""
    spot = gate_spot(g, cell)
    if spot is None:
        say(g, player, f"A {pretty(name).lower()} must go on 4 tiles of an own wall in a straight line, or on 3 "
                       "diagonal tiles.")
        return None
    rect, way, tiles = spot
    cost = price(g, name)
    if any(g.stock[r] < v for r, v in cost.items()):
        say(g, player, f"Not enough resources: a {pretty(name).lower()} costs "
                       + ", ".join(f"{v} {r}" for r, v in cost.items()) + ".")
        return None
    import combat                                                      # combat -> gather -> build: import it late
    old = [s for t, s in wall_tiles_of(g).items() if s and t in tiles]
    builders = {v.uuid for v in getattr(g, "villagers", {}).values() if v.site in old}
    for s in old:
        g.sites.remove(s)
        if s["progress"] >= 1:                                         # a complete tile: its target goes
            g.command(f"kill {combat.target_uuid([s['footprint'][i] for i in (0, 2, 1, 3)])}")
        else:                                                          # the wool ring of a foundation goes
            for p, state in s["ring"].items():
                g.command("setblock {} {} {} ".format(*p) + s["under"].get(p, "minecraft:air"))
    site = found(g, name, rect, way, tiles)
    g.command(f"scoreboard players set {player} {OBJECTIVE} 0")
    if builders:
        g.build(site, builders)
    return site


def next_tile(g, site):
    """The nearest unfinished site of the wall line of site, or the first unfinished site of its row of sneak clicks
    in the order of the clicks (#1805), or None."""
    if "row" in site:
        return next((s for s in g.sites if s.get("row") == site["row"] and s["progress"] < 1 and s is not site), None)
    rest = [s for s in g.sites if "line" in site and s.get("line") == site["line"] and s["progress"] < 1 and s is not site]
    return min(rest, key=lambda s: math.dist(s["footprint"][::2], site["footprint"][::2]), default=None)


def queue(g, player, site):
    """A sneak right click on the site with selected builders at work on another site: the site goes into the row of
    that site, so that the builders build it next, as the shift queue of AoE2 (#3517). True when queued."""
    now = next((v.site for u, v in sorted(g.villagers.items()) if u in g.selected and v.site is not None
                and v.site is not site and v.site["progress"] < 1 and v.state in ("to_site", "build")), None)
    if now is None or "passed" not in g.command(f"execute as {player} if predicate {SNEAK}"):
        return False
    site["row"] = now.setdefault("row", f"{player} {id(now)}")
    return True


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


def found(g, name, rect, way=None, tiles=None, free=False):
    """Pay for name and put its foundation (a wool ring in the player color) on the free footprint rect. Returns
    the construction site. way: the way of a gate (gate_spot); tiles: the tiles of a diagonal gate, the other tiles
    of its footprint stay free (#1655). free: no cost (the start town of a game mode, empire_wars.py, #2408)."""
    import fleet                                                       # fleet -> gather -> build: import it late
    paid = {} if free else price(g, name)                              # a deleted foundation gives it back (demolish.py)
    for r, v in paid.items():
        g.stock[r] -= v
        g.command(f"scoreboard players remove {r.capitalize()} {g.board} {v}")
    record.built(g, name, rect, free)                                  # Record Game (#2649), free: a setup (#3028)
    x0, x1, z0, z1 = rect
    color = g.players.get(str(g.player), {}).get("color", "light_gray")
    ring = [(x, g.map.y(x, z) if g.map.y(x, z) is not None else int(fleet.level(g) if name in WATER else g.map.sea(x, z)), z)
            for x in range(x0, x1) for z in range(z0, z1) if x in (x0, x1 - 1) or z in (z0, z1 - 1)]
    under = {c: "minecraft:water" for c in ring if g.map.y(c[0], c[2]) is None   # a dock or a fish trap: the water
             and "Test passed" in g.command("execute if block {} {} {} minecraft:water".format(*c))}   # comes back (#2059)
    for c in ring:
        g.command("setblock {} {} {} ".format(*c) + f"minecraft:{color}_wool")
    cells = {(x, z) for x in range(x0, x1) for z in range(z0, z1)} if tiles is None else tile_cells(g, tiles)
    g.map.blocked |= cells
    clear(g, cells)
    T = g.map.T                                                        # the design, bottom up (one command each)
    cmds = Replay(g, g.data, getattr(g.game, "version", VERSION_NAME)).building(
        design(g, name, g.player), g.player, (x0 + x1) / 2 / T, (z0 + z1) / 2 / T,
        along_z=z1 - z0 > x1 - x0 if way is None else way,             # a gate along z (#1324) or diagonal (#1655)
        water=int(fleet.level(g)) + 1 if name in WATER else None)      # a fish trap on the open water (#1438)
    site = {"name": name, "player": g.player, "footprint": rect, "commands": cmds, "sent": 0, "progress": 0.0,
            "paid": paid, "ring": dict.fromkeys(ring, f"minecraft:{color}_wool"), "under": under}   # under: the design blocks on the ring
    if way is not None:
        site["way"] = way
    if tiles is not None and str(way).startswith("diag"):
        site["tiles"] = tiles
    g.sites.append(site)
    if g.paper:                                                        # its square on the minimap (#2582)
        g.command(minimap_square((x0, z0, x1, z1), g.player))
    return site


def minimap_square(rect, player):
    """The plugin command that draws the footprint rect (x0, z0, x1, z1; x1 and z1 not in it) of a building of player
    on the minimap (Minimap.java, #1238)."""
    return "aoe minimap building {} {} {} {} p{}".format(*rect, player)


def squares(g):
    """{(x0, z0, x1, z1): player} of the building squares on the minimap: the buildings of aoe2mc.json (not Gaia) and
    the construction sites of each side (a loaded game), not the buildings that fell (score.razed of a side, #2981):
    the sites keep them."""
    import combat                                                      # combat -> gather -> build: import it late
    rects = {tuple(o["footprint"]): o["player"] for o in g.data["objects"]
             if o["kind"] == "building" and o["player"] > 0 and "footprint" in o}
    for x in sides(g):
        rects.update({(f[0], f[2], f[1], f[3]): s["player"] for s in x.sites for f in [s["footprint"]]})
    gone = {u for x in sides(g) for u in vars(x).get("razed", {})}
    return {r: p for r, p in rects.items() if not gone or combat.target_uuid(r) not in gone}   # fog.remember: each tick


def minimap(g):
    """The minimap commands of the buildings at the start of a game (#2582, squares)."""
    return [minimap_square(r, p) for r, p in sorted(squares(g).items())]


def clear(g, cells):
    """Move each unit whose feet are on the cells of a new foundation to the nearest free cell next to them, as in AoE2
    (#1769): else the blocks of the site suffocate it. On Paper all mobs of all players and the animals, else the own
    units. A rider moves with its vehicle: a /tp of a passenger dismounts it. Returns {UUID: cell}."""
    xs, zs = [x for x, _ in cells], [z for _, z in cells]
    area = "x={},y=-64,z={},dx={},dy=400,dz={}".format(min(xs), min(zs), max(xs) - min(xs), max(zs) - min(zs))
    moved = {}
    sea = sorted(g.map.around(cells, water=True))                      # boats first, to the water (#3112): a tp of
    boats = (g.where(None, f"@e[type=#minecraft:boat,{area}]") if g.paper   # a boat keeps its riders (crews)
             else g.positions(sorted({*g.ships, *(u for u, n in g.soldiers.items() if units.is_boat(units.classify(n)))})))
    for u, (fx, fy, fz) in sorted(boats.items()) if sea else ():
        if (math.floor(fx), math.floor(fz)) in cells:
            x, z = min(sea, key=lambda c: ((c[0] + 0.5 - fx) ** 2 + (c[1] + 0.5 - fz) ** 2, c))
            y = g.map.sea(x, z)
            g.command(f"tp {u} {x + 0.5} {y} {z + 0.5}")
            if (v := g.ships.get(u)) is not None:
                v.pos, v.path = (x + 0.5, y, z + 0.5), []
            moved[u] = (x, z)
    ring = sorted(g.map.around(cells))
    if not ring:
        return moved
    sel = "@e[type=!player,{}{}]".format("".join(f"type=!{t}," for t in NOT_UNITS), area)
    pos = g.where(None, sel) if g.paper else g.positions(sorted({*g.villagers, *g.soldiers} - moved.keys()))
    for u, (fx, fy, fz) in sorted(pos.items()):
        if u not in moved and (math.floor(fx), math.floor(fz)) in cells:
            x, z = min(ring, key=lambda c: ((c[0] + 0.5 - fx) ** 2 + (c[1] + 0.5 - fz) ** 2, c))
            y = g.map.y(x, z)
            to = f"{x + 0.5} {y} {z + 0.5}"
            if not g.command(f"execute as {u} on vehicle run tp @s {to}").strip():   # no vehicle
                g.command(f"tp {u} {to}")
            if (v := g.villagers.get(u)) is not None:
                v.pos = (x + 0.5, float(y), z + 0.5)
            moved[u] = (x, z)
    return moved


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
    The wool ring stays on top of the design until the building is complete. Returns True when it is complete.
    Treadmill Crane: the builders of the player work 20 % faster (CRANE, AoE2 DE wiki, #1422); the civilization
    bonus multiplies with it (civs.build_rate, #1893)."""
    if site.get("player", g.player) == g.player:
        x0, x1, z0, z1 = site["footprint"]                                 # the builders stand at its edge
        work *= CRANE ** ("TREADMILL_CRANE" in getattr(g, "techs", ())) * civs.build_rate(g, site["name"]) \
            * civs.church_rate(g, ((x0 + x1) / 2, (z0 + z1) / 2)) \
            * civs.turbo(g, site["name"])                              # Georgian Fortified Church (#1930), Turbo (#2359)
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
        for p in [p for p in ring if p not in hit]:                    # the ring goes: the design, the water or air
            g.command("setblock {} {} {} ".format(*p) + site["under"].get(p, "minecraft:air"))
        if site["name"] in MOVES and site["player"] == g.player:
            cart(g, site)
            return True
        x0, x1, z0, z1 = site["footprint"]
        s, T = footprint(site["name"]), g.map.T
        settle(g, site)                                                # the map and the forts (as savegame.load)
        if "FARM" in site["name"] and site["player"] == g.player:
            folwark(g, site, (x0 // T + s // 2, z0 // T + s // 2))
        if site["name"] == "TOWN_CENTER" and site["player"] == g.player:
            g.town_center(tuple(site["footprint"]))
        target(g, site)
        if site["name"] in GATES:
            portcullis(g, site)
        if site["player"] == g.player and (food := civs.built_food(g, site["name"])):
            g.earn("food", food)                                       # Saxon camps, Wu military buildings (#2114)
        if site["player"] == g.player and (born := civs.built_units(g, site["name"])):
            herd.spawn(g, site["footprint"], *born)                    # Tatar sheep at a town center (#2313)
        if site["player"] == g.player:
            monk.free_relic(g, site)                                   # the first Armenian Fortified Church (#2419)
    return site["progress"] >= 1


def cart(g, site):
    """A complete building that moves (MOVES: the mule cart, AoE2 DE wiki "Mule Cart", #2209): its blocks go, and a
    mob with its AoE2 values stands in their place. It takes move orders as a trade cart, and the mob path finding moves
    it (Minecraft features first). Its footprint and its drop cells follow the mob (moved_carts)."""
    import train                                                   # train imports this module
    x0, x1, z0, z1 = site["footprint"]
    cells = {(x, z) for x in range(x0, x1) for z in range(z0, z1)}
    g.map.blocked -= cells                                         # the cart blocks no path (found blocked them)
    y = min(g.map.y(x, z) for x, z in cells)
    top = max((b[0][4] for c in site["commands"] if (b := box(c))), default=y)
    if top >= y:
        g.command(f"fill {x0} {y} {z0} {x1 - 1} {top} {z1 - 1} minecraft:air")
    x, z = (x0 + x1) // 2, (z0 + z1) // 2
    site["uuid"] = uuid = train.summon(g, site["name"], (x + 0.5, float(g.map.y(x, z)), z + 0.5))
    if uuid:
        site["cells"] = cells
        g.map.drop_site(site["name"], cells)


def moved_carts(g):
    """Move the footprint and the drop cells of each complete cart (cart) under its mob, with the same size: the next
    villager carries its load to the new place. A dead cart is no drop site."""
    for site in [s for s in g.sites if "cells" in s]:
        if not (p := g.pos(site["uuid"])):
            for r in g.map.drops:
                g.map.drops[r] = [d for d in g.map.drops[r] if d is not site["cells"]]
            del site["cells"]
            continue
        x0, x1, z0, z1 = site["footprint"]
        w, d = x1 - x0, z1 - z0
        x0, z0 = math.floor(p[0]) - w // 2, math.floor(p[2]) - d // 2
        site["footprint"] = (x0, x0 + w, z0, z0 + d)
        site["cells"].clear()
        site["cells"].update((x, z) for x in range(x0, x0 + w) for z in range(z0, z0 + d))


def folwark(g, farm, tile):
    """A new own farm with its whole footprint within FOLWARK_REACH tiles of an own complete Folwark: the player gets
    FOLWARK_SHARE of its food at once, and the farm keeps the rest (AoE2 DE wiki "Folwark", #1874)."""
    r = FOLWARK_REACH * g.map.T
    x0, x1, z0, z1 = farm["footprint"]
    if any(f["name"] == "FOLWARK" and f.get("done") and f["player"] == farm["player"] and f["footprint"][0] - r <= x0
           and x1 <= f["footprint"][1] + r and f["footprint"][2] - r <= z0 and z1 <= f["footprint"][3] + r for f in g.sites):
        food = int(g.map.farms[tile] * FOLWARK_SHARE + 0.5)            # 18 of 175, 55 of 550 (the wiki table)
        g.map.farms[tile] -= food
        g.earn("food", food)


def design(g, name, player):
    """The design of building name of player: a stone wall (gate) of the player after Fortified Wall is a fortified
    wall (gate), #1326."""
    import train                                                       # train imports this module
    new = {old: wall for t, walls in train.BY_KEY["walls"].items() if t in getattr(g, "techs", ()) for old, wall in walls.items()}
    return new.get(name, name) if player == g.player else name


def line(g, name, techs=None):
    """The building whose AoE2 values building name of the player of g has: a watch tower after Guard Tower (Keep) has
    those of the guard tower (keep), #1374. techs: the technologies (default: those of the player)."""
    import train                                                       # train imports this module
    techs = getattr(g, "techs", ()) if techs is None else techs
    for t, towers in train.BY_KEY["towers"].items():                  # in the research order
        name = towers.get(name, name) if t in techs else name
    return name


def values(g, name, techs=None, rect=None):
    """The AoE2 values of building name of the player of g: those of its tower (line, #1374) with the building
    technologies (train.TECHS: Chemistry, Masonry, #1398). techs: the technologies (default: those of the player). A
    technology sees the name of the tower of the values (Arrowslits: a keep +3, #1504). rect: the footprint of the
    building, with the effect of its upgrade of one building (g.upgraded: the Defensive Town Center, #2497)."""
    import combat, train                                               # combat -> gather -> build: import it late
    techs = getattr(g, "techs", ()) if techs is None else techs
    name = line(g, name, techs)
    wall = name in combat.WALLS or name.endswith(("_WALL", "_GATE"))   # its age: combat.wall (upgrade, #1372)
    s = civs.hp(civs.civ(g) if hasattr(g, "data") else None, name, combat.stats(name),
                0 if wall else sum(t in techs for t in AGE_TECHS),    # before Masonry (#1895), of the age (#2116)
                civs.handicap(g.data, g.player) if hasattr(g, "data") else 1)   # #2474
    for t in sorted(techs):
        s = train.TECHS[t](name, s)
    if up := vars(g).get("upgraded", {}).get(rect):
        s = train.TECHS[up](name, s)
    return s


def minimum(g, name, techs=None):
    """The minimum range in tiles of building name of the player of g (combat.FORT_MIN_RANGE): 0 after Murder Holes
    (#1547). techs: the technologies (default: those of the player)."""
    import combat                                                      # combat -> gather -> build: import it late
    techs = getattr(g, "techs", ()) if techs is None else techs
    return 0 if "MURDER_HOLES" in techs else combat.FORT_MIN_RANGE.get(name, 0)


def retower(g, before, fresh=None):
    """The complete own buildings get their new values after a tower technology (#1374) or Masonry (#1398, values): the
    target keeps its lost hit points, as a wall (upgrade). before: the technologies before the research. fresh: the
    footprint of a building that has a new upgrade of one building (#2497), else None. A destroyed building stays air."""
    import combat, repair                                              # combat -> gather -> build: import it late
    rects = [(x0, x1, z0, z1, o["name"]) for o in g.data["objects"] if o["kind"] == "building" and o["player"] == g.player
             and "footprint" in o for x0, z0, x1, z1 in [o["footprint"]]] \
        + [(*s["footprint"], s["name"]) for s in g.sites if s.get("done") and s["player"] == g.player]
    for x0, x1, z0, z1, name in rects:
        rect = (x0, x1, z0, z1)
        a, b, new = values(g, name, before, None if rect == fresh else rect), values(g, name, rect=rect), line(g, name)
        if (a, minimum(g, new, before)) == (b, minimum(g, new)) or (hp := repair.hp(g, (x0, x1, z0, z1))) is None or hp <= 0:
            continue
        uuid = combat.target_uuid([x0, z0, x1, z1])
        box = combat.building_box({"footprint": [x0, z0, x1, z1]}, g.map.ground)
        for c in [c for c in combat.building(uuid, new, g.player, box, g.map.T, s=b, low=minimum(g, new)) if c.startswith("aoe building ")] \
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
    new = combat.wall(name, ages(g), civs.civ(g, site["player"]), civs.handicap(g.data, site["player"]))
    if new == old or (hp := repair.hp(g, (x0, x1, z0, z1))) is None or hp <= 0:
        return
    for c in Replay(g, g.data, getattr(g.game, "version", VERSION_NAME)).building(
            name, site["player"], (x0 + x1) / 2 / T, (z0 + z1) / 2 / T, along_z=way(site)) * redraw:   # as found()
        g.command(c)
    if redraw and site["name"] in GATES:                               # the redraw cleared the portcullis
        portcullis(g, site)
    uuid = combat.target_uuid([x0, z0, x1, z1])
    if redraw:                                                         # the damage stages keep the new blocks (#3071)
        g.command(f"aoe unwear {uuid}")
    box = combat.building_box({"footprint": [x0, z0, x1, z1]}, g.map.ground)
    for c in [c for c in combat.building(uuid, name, site["player"], box, T, s=new) if c.startswith("aoe building ")] \
            + [f"scoreboard players set {uuid} aoe_hp {min(new.hp, hp + new.hp - old.hp)}", combat.label_command(uuid, name)]:
        g.command(c)


def portcullis(g, site):
    """A closed portcullis across the passage of the complete gate site (#1656, the owner's look): iron bars 3 blocks
    high from the walk level on each block of the middle 2 tiles, in the middle of the wall depth. The 4 blocks high
    passage of a stone gate gets the raised bars on top. On Paper the plugin raises the 3 lower rows while a unit of
    the player or an ally is within 2 blocks or walks a path through it (aoe gate, #1325)."""
    x0, x1, z0, z1 = site["footprint"]
    T, along_z = g.map.T, way(site)
    if str(along_z).startswith("diag"):
        cells = [(x, z) for x, z, _, _ in diagonal_doors(site, T)]
    else:
        cells = [(x0 + T // 2, z) for z in range(z0 + T, z1 - T)] if along_z else \
            [(x, z0 + T // 2) for x in range(x0 + T, x1 - T)]
    y = max((v for x in range(x0, x1) for z in range(z0, z1) if (v := g.map.y(x, z)) is not None), default=None)
    if y is None or not cells:
        return
    top = 3 if site["name"] == "GATE" and not str(along_z).startswith("diag") else 2   # the palisade: logs above
    for x, z in cells:
        g.command(f"fill {x} {y} {z} {x} {y + top} {z} minecraft:iron_bars")
    if getattr(g, "paper", False):
        (ax, bx), (az, bz) = [(min(v), max(v)) for v in zip(*cells)]
        g.command(f"aoe gate p{site['player']} {ax} {y} {az} {bx} {y + 2} {bz}")


def diagonal_doors(site, T):
    """[(x, z, facing, hinge)] of the doors across the passage of a diagonal gate site (#1655); portcullis() puts its
    bars on these cells (#1656): a staircase of 2 lines that also closes the diagonal steps. The passage of
    buildings.diagonal_gate is the middle tile of the band x = z (local); a door is a thin panel on one side of its
    block, so one line of doors on the diagonal leaves gaps. The doors on the diagonal close their east side
    (facing west), the doors north of them close their south side (facing north): a closed staircase. Open, the
    panels go to the sides that the passage does not cross. "diag-" mirrors z."""
    x0, x1, z0, z1 = site["footprint"]
    out = [(i, i, "west", "left") for i in range(T, 2 * T)] + [(i, i - 1, "north", "right") for i in range(T + 1, 2 * T)]
    if site.get("way") == "diag-":                                     # the mirror swaps north and south and the hinges
        flip = {"north": "south", "west": "west", "left": "right", "right": "left"}
        out = [(x, 3 * T - 1 - z, flip[f], flip[h]) for x, z, f, h in out]
    return [(x0 + x, z0 + z, f, h) for x, z, f, h in out]


def target(g, site):
    """A complete building of combat.BUILDINGS gets its target entity, as a building of the map (combat.setup): the
    AoE2 hit points, and the arrows of a town center, tower or castle (#1202). wonder.tick makes the one of a wonder."""
    import combat                                                      # combat -> gather -> build: import it late
    if not is_fort(site):
        return
    x0, x1, z0, z1 = site["footprint"]
    uuid = combat.target_uuid([x0, z0, x1, z1])
    box = combat.building_box({"footprint": [x0, z0, x1, z1]}, g.map.ground)
    wall, name = site["name"] in combat.WALLS, line(g, design(g, site["name"], site["player"]))   # the hit points of the age
                                                                       # (#1322), a guard tower or keep (#1374)
    s = combat.wall(name, ages(g), civs.civ(g, site["player"]), civs.handicap(g.data, site["player"])) if wall else values(g, name)   # Chemistry (#1375), Masonry (#1398)
    for c in combat.building(uuid, name, site["player"], box, g.map.T, s=s, low=minimum(g, name),
                             factor=civs.arrows(g, name, site["player"])) \
            + [f"tag {uuid} add {combat.WALL_TAG}"] * wall + [combat.label_command(uuid, name)]:
        g.command(c)
    forts(g, site)


def is_fort(site):
    """A complete building that the sides can attack: a building or a wall of combat.py, but not a wonder (#2458)."""
    import combat                                                      # combat -> gather -> build: import it late
    return (site["name"] in combat.BUILDINGS or site["name"] in combat.WALLS) and site["name"] != "WONDER" \
        and not site.get("lasting")                                    # the monastery of Capture the Relic (#2458)


def settle(g, site, loaded=False):
    """Put a site on the map (#2980): a foundation blocks its cells, and a complete building works (Map.building and the
    forts of the sides). rise() calls it at the completion. loaded: a saved site (savegame.load), which sends no command
    and gives no one-time gift again: the world keeps the blocks and the targets, and the saved amounts win."""
    x0, x1, z0, z1 = site["footprint"]
    cells = {(x, z) for x in range(x0, x1) for z in range(z0, z1)}
    if not site.get("done"):
        g.map.blocked |= tile_cells(g, site["tiles"]) if "tiles" in site else cells
        return
    if site["name"] in MOVES:                                          # a cart: its drop cells (cart)
        if loaded and "cells" in site:
            g.map.drop_site(site["name"], site["cells"])
        return
    s, T = footprint(site["name"]), g.map.T
    if "FARM" in site["name"]:                                         # free ground again: the farmer stands on it
        g.map.blocked -= cells
    open_cells = cells - tile_cells(g, site["tiles"]) if "tiles" in site else ()   # beside a diagonal gate (#1655)
    g.map.building(site["name"], site["footprint"], (x0 // T + s // 2, z0 // T + s // 2), site["player"] == g.player,
                   open_cells)
    if loaded and is_fort(site):                                       # rise() does it in target()
        forts(g, site)


def forts(g, site):
    """Each side knows a complete building as a fort, with its target entity: each other side can attack it, the bot and
    player 1 alike (#1819). No command: the target entity is in the world already (savegame.load, #2980)."""
    import combat                                                      # combat -> gather -> build: import it late
    x0, x1, z0, z1 = site["footprint"]
    uuid = combat.target_uuid([x0, z0, x1, z1])
    box = combat.building_box({"footprint": [x0, z0, x1, z1]}, g.map.ground)
    for o in sides(g):
        o.fort_names[uuid] = site["name"]
        if site["player"] != o.player:
            o.forts[uuid] = box
            vars(o).setdefault("fort_players", {})[uuid] = site["player"]


def sides(g):
    """The Gathers of all sides of the game of g: player 1 holds the bots and the other people (run.py, Gather.bots),
    a bot knows player 1 (share), a person the others (peers)."""
    first = g.peers[0] if g.peers else getattr(g, "share", None) or g
    return [first, *(b.g for b in getattr(first, "bots", ()))]
