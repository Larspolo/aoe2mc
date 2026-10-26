"""
The land of a random map from an AoE2 random map script (.rms, #963, decision A of #961): the user gives the script
of the own AoE2 install, the repository has no game script. generate() reads the land part of the script and returns
a map description of #960 (aoe2mc.read_json): the terrain of each tile, elevation 0, and only the trees of the
forest tiles as objects (FOREST_TREES) yet.

Read: `#const`, `#define`, `if`/`elseif`/`else`/`endif`, `start_random`/`percent_chance`/`end_random`,
<PLAYER_SETUP> (no effect here), <LAND_GENERATION> (`base_terrain`, `create_player_lands`, `create_land` with
`terrain_type`, `land_percent`, `number_of_tiles`, `base_size`, `clumping_factor`, `land_position`) and
<TERRAIN_GENERATION> (`create_terrain` with `base_terrain`, `number_of_clumps`, `number_of_tiles`, `land_percent`,
`spacing_to_other_terrain_types`, `set_avoid_player_start_areas`, `clumping_factor`). Other sections and attributes:
a warning. All randomness comes from numpy.random.default_rng(seed).
"""
import re
import sys

import numpy as np

# The terrain constants of the RMS language -> AoE2 terrain IDs (AoE2ScenarioParser TerrainId values).
TERRAINS = {"GRASS": 0, "WATER": 1, "BEACH": 2, "DIRT3": 3, "SHALLOW": 4, "LEAVES": 5, "DIRT": 6, "FARM": 7,
            "DEAD_FARM": 8, "GRASS3": 9, "FOREST": 10, "DIRT2": 11, "GRASS2": 12, "PALM_DESERT": 13, "DESERT": 14,
            "JUNGLE": 17, "BAMBOO": 18, "PINE_FOREST": 19, "OAK_FOREST": 20, "SNOW_FOREST": 21, "DEEP_WATER": 22,
            "MED_WATER": 23, "ROAD": 24, "ROAD2": 25, "SNOW": 32, "ICE": 35, "ROCK": 40}
# The tree of each forest terrain: the game puts one on each forest tile, a scenario keeps them as objects.
FOREST_TREES = {10: "TREE_OAK_FOREST", 13: "TREE_PALM_FOREST", 17: "TREE_JUNGLE", 18: "TREE_BAMBOO_FOREST",
                19: "TREE_PINE_FOREST", 20: "TREE_OAK_FOREST", 21: "TREE_SNOW_PINE", 48: "TREE_DRAGON",
                49: "TREE_BAOBAB", 50: "TREE_ACACIA", 55: "TREE_MANGROVE", 56: "TREE_RAINFOREST"}
SIZES = {1: 120, 2: 120, 3: 144, 4: 144, 5: 168, 6: 168, 7: 200, 8: 200}    # AoE2 map size of a player count
LABELS = ((120, "TINY_MAP"), (144, "SMALL_MAP"), (168, "MEDIUM_MAP"), (200, "LARGE_MAP"), (220, "HUGE_MAP"))
RING = 0.35                     # the circle of the player lands: radius in map sizes
AVOID = 13                      # set_avoid_player_start_areas: default tiles from a player origin
STEPS = ((1, 0), (-1, 0), (0, 1), (0, -1))
SECTIONS = ("PLAYER_SETUP", "LAND_GENERATION", "TERRAIN_GENERATION")


class RmsError(ValueError):
    pass


def tokens(text):
    """The words of a script without its /* comments */; braces and section names are words."""
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    return re.sub(r"([{}])", r" \1 ", text).split()


def expand(words, rng, defined, consts):
    """The words of the active branches: if/elseif/else/endif on the defined labels, one percent_chance branch of
    each start_random (a draw only for an active block), #define and #const go into defined and consts."""
    out, stack, i = [], [], 0
    def on():
        return all(f["on"] for f in stack)
    while i < len(words):
        w = words[i]
        if w == "if":
            c = on() and words[i + 1] in defined
            stack.append({"on": c, "done": c})
            i += 2
        elif w == "elseif":
            f = stack[-1]
            f["on"] = not f["done"] and words[i + 1] in defined
            f["done"] |= f["on"]
            i += 2
        elif w == "else":
            stack[-1]["on"], stack[-1]["done"] = not stack[-1]["done"], True
            i += 1
        elif w == "start_random":
            stack.append({"on": False, "done": False, "roll": int(rng.integers(100)) if on() else 100, "acc": 0})
            i += 1
        elif w == "percent_chance":
            f, n = stack[-1], int(words[i + 1])
            f["on"] = not f["done"] and f["acc"] <= f["roll"] < f["acc"] + n
            f["done"] |= f["on"]
            f["acc"] += n
            i += 2
        elif w in ("endif", "end_random"):
            if not stack:
                raise RmsError(f"{w} without its start")
            stack.pop()
            i += 1
        elif not on():
            i += 1
        elif w == "#define":
            defined.add(words[i + 1])
            i += 2
        elif w == "#const":
            consts[words[i + 1]] = int(words[i + 2])
            i += 3
        else:
            out.append(w)
            i += 1
    if stack:
        raise RmsError("an if or start_random has no end")
    return out


def commands(words):
    """{section: [(command, [args], {attribute: [args]})]}. A command or an attribute is a lower case word; its
    arguments are the next words that are numbers or upper case constants."""
    out, section, i = {}, None, 0
    def args(i):
        a = []
        while i < len(words) and not re.fullmatch(r"[a-z_][a-z0-9_]*|[{}]|<\w+>", words[i]):
            a.append(words[i])
            i += 1
        return a, i
    while i < len(words):
        w = words[i]
        if m := re.fullmatch(r"<(\w+)>", w):
            section = out.setdefault(m[1], [])
            i += 1
            continue
        a, i = args(i + 1)
        attrs = {}
        if i < len(words) and words[i] == "{":
            i += 1
            while i < len(words) and words[i] != "}":
                name = words[i]
                attrs[name], i = args(i + 1)
            i += 1
        if section is None:
            raise RmsError(f"{w!r} before the first <SECTION>")
        section.append((w, a, attrs))
    return out


def value(word, consts):
    if re.fullmatch(r"-?\d+", word):
        return int(word)
    if word not in consts:
        raise RmsError(f"unknown constant {word!r}")
    return consts[word]


def grow(owner, lands, free, rng):
    """Grow the lands at the same time, one tile each in turn, as AoE2 does: a land takes a free tile next to it. A
    higher clumping factor tries more tiles and takes the one with most tiles of the land around it (round lands).
    lands: [{"id", "cells" (start tiles), "target" (tiles), "clump"}]; free: a bool array of the tiles to take."""
    n = owner.shape[0]
    for land in lands:
        land["front"], land["seen"], land["count"] = [], set(), 0
        for c in land["cells"]:
            if free[c] and owner[c] < 0:
                owner[c] = land["id"]
                land["count"] += 1
        for c in zip(*np.nonzero(owner == land["id"])):
            add_front(land, c, n)
    while True:
        busy = False
        for land in lands:
            front = land["front"]
            while front and land["count"] < land["target"]:
                tries = [int(rng.integers(len(front))) for _ in range(1 + land["clump"] // 5)]
                k = max(tries, key=lambda k: sum(owner[c] == land["id"] for c in near(front[k], n)))
                c = front[k]
                front[k] = front[-1]
                front.pop()
                if owner[c] >= 0 or not free[c]:
                    continue
                owner[c] = land["id"]
                land["count"] += 1
                add_front(land, c, n)
                busy = True
                break
        if not busy:
            return


def near(c, n):
    return [(c[0] + dx, c[1] + dy) for dx, dy in STEPS if 0 <= c[0] + dx < n and 0 <= c[1] + dy < n]


def add_front(land, c, n):
    for d in near(c, n):
        if d not in land["seen"]:
            land["seen"].add(d)
            land["front"].append(d)


def square(c, r, n):
    """The tiles within r of tile c (a square), in the map."""
    return [(x, y) for x in range(max(0, c[0] - r), min(n, c[0] + r + 1))
            for y in range(max(0, c[1] - r), min(n, c[1] + r + 1))]


def tiles(attrs, consts, n, default=0):
    """The tile count of number_of_tiles, else of land_percent (of the whole map), else default."""
    if "number_of_tiles" in attrs:
        return value(attrs["number_of_tiles"][0], consts)
    if "land_percent" in attrs:
        return value(attrs["land_percent"][0], consts) * n * n // 100
    return default


def dilate(mask, r):
    """The tiles within r (a square) of a True tile."""
    rows = mask.copy()
    for s in range(1, r + 1):
        rows[s:] |= mask[:-s]
        rows[:-s] |= mask[s:]
    out = rows.copy()
    for s in range(1, r + 1):
        out[:, s:] |= rows[:, :-s]
        out[:, :-s] |= rows[:, s:]
    return out


def trees(terrain):
    """One tree object on each forest tile."""
    return [{"name": FOREST_TREES[int(terrain[x, y])], "x": x + 0.5, "y": y + 0.5}
            for x, y in np.argwhere(np.isin(terrain, list(FOREST_TREES)))]


def generate(text, seed, players=2, size=None, warn=None):
    """The map description (aoe2mc.read_json) of the land part of script text, for players on a map of size tiles
    (default: the AoE2 size of the player count). "lands": [{"player", "x", "y", "base_size"}] of the player lands."""
    warn = warn or (lambda m: print(f"rms: {m}", file=sys.stderr))
    rng = np.random.default_rng(seed)
    n = size or SIZES.get(players, 200)
    defined = {next((label for s, label in LABELS if n <= s), "GIGANTIC_MAP")}
    consts = dict(TERRAINS)
    sections = commands(expand(tokens(text), rng, defined, consts))
    for s in sections:
        if s not in SECTIONS:
            warn(f"<{s}> is not read yet")
    terrain = np.zeros((n, n), np.int16)
    owner = np.full((n, n), -1, np.int32)
    lands, starts, kinds = [], [], {}
    for cmd, args, attrs in sections.get("LAND_GENERATION", ()):
        if cmd == "base_terrain":
            terrain[:] = value(args[0], consts)
        elif cmd in ("create_player_lands", "create_land"):
            base = value(attrs["base_size"][0], consts) if "base_size" in attrs else 3
            clump = value(attrs["clumping_factor"][0], consts) if "clumping_factor" in attrs else 8
            kind = value(attrs["terrain_type"][0], consts) if "terrain_type" in attrs else 0
            if cmd == "create_player_lands":
                total, turn = tiles(attrs, consts, n), rng.uniform(0, 2 * np.pi)
                for p in range(1, players + 1):
                    a = turn + 2 * np.pi * (p - 1) / players
                    c = (int(round((n - 1) / 2 + RING * n * np.cos(a))), int(round((n - 1) / 2 + RING * n * np.sin(a))))
                    starts.append({"player": p, "x": c[0], "y": c[1], "base_size": base})
                    lands.append({"id": len(lands), "cells": square(c, base, n), "clump": clump,
                                  "target": max(total // players, (2 * base + 1) ** 2)})
                    kinds[len(lands) - 1] = kind
            else:
                if "land_position" in attrs:
                    c = tuple(min(n - 1, value(v, consts) * n // 100) for v in attrs["land_position"][:2])
                else:
                    c = tuple(int(v) for v in rng.integers(0, n, 2))
                lands.append({"id": len(lands), "cells": square(c, base, n), "clump": clump,
                              "target": tiles(attrs, consts, n, (2 * base + 1) ** 2)})
                kinds[len(lands) - 1] = kind
            for a in set(attrs) - {"base_size", "clumping_factor", "terrain_type", "land_percent", "number_of_tiles",
                                   "land_position"}:
                warn(f"{cmd}: {a} is not read yet")
        else:
            warn(f"{cmd} is not read yet")
    grow(owner, lands, np.ones((n, n), bool), rng)
    for lid, kind in kinds.items():
        terrain[owner == lid] = kind
    for cmd, args, attrs in sections.get("TERRAIN_GENERATION", ()):
        if cmd != "create_terrain":
            warn(f"{cmd} is not read yet")
            continue
        kind = value(args[0], consts)
        on = value(attrs["base_terrain"][0], consts) if "base_terrain" in attrs else 0
        free = terrain == on
        if (s := value(attrs["spacing_to_other_terrain_types"][0], consts)
                if "spacing_to_other_terrain_types" in attrs else 0):
            free &= ~dilate(terrain != on, s)
        avoid = attrs.get("set_avoid_player_start_areas")      # None: not set; []: the default distance
        far = 0 if avoid is None else value(avoid[0], consts) if avoid else AVOID
        for st in starts:                      # never in the start area of a player (its base_size square)
            r = max(st["base_size"], far)
            for c in square((st["x"], st["y"]), r, n):
                free[c] = False
        clumps = value(attrs["number_of_clumps"][0], consts) if "number_of_clumps" in attrs else 1
        each = tiles(attrs, consts, n, 1) // max(clumps, 1)
        clump = value(attrs["clumping_factor"][0], consts) if "clumping_factor" in attrs else 8
        spots = np.argwhere(free)
        if not len(spots):
            continue
        mark = np.full((n, n), -1, np.int32)
        group = [{"id": k, "cells": [tuple(int(v) for v in spots[rng.integers(len(spots))])], "target": each,
                  "clump": clump} for k in range(clumps)]
        grow(mark, group, free, rng)
        terrain[mark >= 0] = kind
        for a in set(attrs) - {"base_terrain", "number_of_clumps", "number_of_tiles", "land_percent", "clumping_factor",
                               "spacing_to_other_terrain_types", "set_avoid_player_start_areas"}:
            warn(f"create_terrain: {a} is not read yet")
    return {"size": n, "terrain": terrain.tolist(), "elevation": [[0] * n for _ in range(n)], "objects": trees(terrain),
            "players": {str(p): {"color": p - 1} for p in range(1, players + 1)}, "lands": starts}


# Own generators (#993, decision B of #961): the land of a map type in the script language of generate(). The text is
# not a game script: it holds only facts about the map. Arabia: open grass and dirt land, small forests, a few single
# trees, small ponds away from the players.
ARABIA = """
<LAND_GENERATION>
base_terrain DIRT
create_player_lands { terrain_type GRASS land_percent 50 base_size 12 clumping_factor 15 }
<TERRAIN_GENERATION>
create_terrain FOREST { base_terrain GRASS number_of_clumps 4 land_percent 3 set_avoid_player_start_areas 16
  spacing_to_other_terrain_types 1 clumping_factor 15 }
create_terrain FOREST { base_terrain DIRT number_of_clumps 6 land_percent 4 set_avoid_player_start_areas 16
  spacing_to_other_terrain_types 1 clumping_factor 15 }
create_terrain FOREST { base_terrain GRASS number_of_clumps 12 number_of_tiles 12 set_avoid_player_start_areas 12
  spacing_to_other_terrain_types 2 }
create_terrain WATER { base_terrain DIRT number_of_clumps 2 number_of_tiles 50 set_avoid_player_start_areas 22
  spacing_to_other_terrain_types 3 clumping_factor 20 }
create_terrain DIRT3 { base_terrain DIRT number_of_clumps 12 land_percent 4 }
create_terrain GRASS3 { base_terrain GRASS number_of_clumps 10 land_percent 3 }
"""
# The start objects of each player: (name, count, distance in tiles from the town center, owner: 0 = Gaia, 1 = the
# player). A group of more than one object stands on next tiles.
START = (("VILLAGER_MALE", 2, 4, 1), ("VILLAGER_FEMALE", 1, 4, 1), ("SCOUT_CAVALRY", 1, 6, 1), ("SHEEP", 4, 7, 1),
         ("FORAGE_BUSH", 6, 9, 0), ("GOLD_MINE", 7, 11, 0), ("STONE_MINE", 5, 13, 0), ("WILD_BOAR", 1, 15, 0),
         ("WILD_BOAR", 1, 16, 0), ("DEER", 3, 18, 0), ("GOLD_MINE", 4, 19, 0), ("STONE_MINE", 4, 20, 0))
# Arena: each player in a circle of stone walls with a forest inside it (WALLS), open grass land between the circles.
ARENA = """
<LAND_GENERATION>
base_terrain GRASS
create_player_lands { terrain_type GRASS2 land_percent 25 base_size 14 clumping_factor 15 }
<TERRAIN_GENERATION>
create_terrain DIRT3 { base_terrain GRASS number_of_clumps 10 land_percent 3 }
"""
# Black Forest: forest on most of the map, open player lands, an open middle and open paths (PATHS) between them.
BLACK_FOREST = """
<LAND_GENERATION>
base_terrain FOREST
create_player_lands { terrain_type GRASS land_percent 25 base_size 13 clumping_factor 15 }
create_land { terrain_type GRASS land_position 50 50 base_size 5 number_of_tiles 250 clumping_factor 15 }
<TERRAIN_GENERATION>
create_terrain DIRT3 { base_terrain GRASS number_of_clumps 8 land_percent 2 }
create_terrain FOREST { base_terrain GRASS number_of_clumps 6 number_of_tiles 10 set_avoid_player_start_areas 15
  spacing_to_other_terrain_types 2 }
"""
# Gold Rush: open land, a dirt land with many gold mines in the middle (GOLDS) and a forest ring around it.
GOLD_RUSH = """
<LAND_GENERATION>
base_terrain GRASS
create_player_lands { terrain_type GRASS2 land_percent 30 base_size 12 clumping_factor 15 }
create_land { terrain_type DIRT land_position 50 50 base_size 8 number_of_tiles 450 clumping_factor 20 }
<TERRAIN_GENERATION>
create_terrain DIRT3 { base_terrain GRASS number_of_clumps 10 land_percent 3 }
create_terrain FOREST { base_terrain GRASS number_of_clumps 8 number_of_tiles 25 set_avoid_player_start_areas 16
  spacing_to_other_terrain_types 2 }
"""
# Highland: grass land with forests, a river across the map between the players (RIVERS) with shallow fords.
HIGHLAND = """
<LAND_GENERATION>
base_terrain GRASS
create_player_lands { terrain_type GRASS2 land_percent 40 base_size 12 clumping_factor 15 }
<TERRAIN_GENERATION>
create_terrain FOREST { base_terrain GRASS number_of_clumps 8 land_percent 8 set_avoid_player_start_areas 16
  spacing_to_other_terrain_types 1 clumping_factor 15 }
create_terrain FOREST { base_terrain GRASS number_of_clumps 10 number_of_tiles 12 set_avoid_player_start_areas 12
  spacing_to_other_terrain_types 2 }
create_terrain DIRT3 { base_terrain GRASS number_of_clumps 10 land_percent 3 }
create_terrain GRASS3 { base_terrain GRASS2 number_of_clumps 8 land_percent 3 }
"""
GENERATORS = {"arabia": ARABIA,
              "arena": ARENA,
              "black_forest": BLACK_FOREST,
              "gold_rush": GOLD_RUSH,
              "highland": HIGHLAND}
WALLS = {"arena": 23}           # the radius in tiles of the stone wall circle around each player (outside START)
BAND = 6                        # the forest inside the wall: tiles of width, on the half away from the map middle
PATHS = {"black_forest": 1}     # the half width in tiles of the open path from each player to the middle
GOLDS = {"gold_rush": (10, 6, 5)}  # the gold of the middle: radius in tiles, clumps of gold mines, mines in a clump
RIVERS = {"highland": (3, 3, 5)}  # the river: half width in tiles, the least and the most fords
RINGS = {"gold_rush": (14, 5)}  # the forest ring around the gold: inner radius and width in tiles, gaps between players
WOODS = {"arabia": (10, 30, 3), # the wood line of each player (tiles from the town center, forest tiles) and its
         "gold_rush": (10, 30, 3)}  # single trees (stragglers, at 4 to 6 tiles), as in AoE2 (#1144)


def walls(d, r, rng):
    """The stone wall circle of radius r around each player origin: the tiles of each disk with a tile outside it next
    to them (a closed line for 4 steps), the map edge closes it. Inside the wall a forest band of BAND tiles (with an
    uneven inner edge) on the half away from the map middle, the same for each player."""
    n, terrain = d["size"], np.array(d["terrain"])
    x, y = np.mgrid[0:n, 0:n] + 0.5
    out, phase = [], rng.uniform(0, 2 * np.pi)
    for st in d["lands"]:
        dx, dy = x - st["x"], y - st["y"]
        dist = np.hypot(dx, dy)
        disk = dist <= r
        edge = disk & dilate(~disk, 1)
        back = dx * (st["x"] - n / 2) + dy * (st["y"] - n / 2) > 0                  # away from the middle
        inner = r - 1.5 - BAND + 1.5 * np.sin(5 * np.arctan2(dy, dx) + phase)
        terrain[disk & back & (dist > inner) & ~edge] = TERRAINS["FOREST"]
        terrain[edge] = TERRAINS["GRASS2"]
        out += [{"name": "STONE_WALL", "player": st["player"], "x": i + 0.5, "y": j + 0.5} for i, j in np.argwhere(edge)]
    d["terrain"] = terrain.tolist()
    return out


def goldfield(d, gold, ring, rng):
    """The gold of the middle: gold[1] clumps of gold[2] gold mines within gold[0] tiles of the map middle, and a forest
    ring (inner radius ring[0] with an uneven edge, ring[1] tiles wide) around it, with a gap of 5 tiles half way
    between each two players: the player lands do not see the gold, and the gaps let the units in."""
    n, terrain = d["size"], np.array(d["terrain"])
    x, y = np.mgrid[0:n, 0:n] + 0.5
    dx, dy = x - n / 2, y - n / 2
    dist, a = np.hypot(dx, dy), np.arctan2(dy, dx)
    inner = ring[0] + 1.5 * np.sin(5 * a + rng.uniform(0, 2 * np.pi))
    band = (dist >= inner) & (dist < inner + ring[1])
    turns = sorted(np.arctan2(st["y"] - n / 2, st["x"] - n / 2) for st in d["lands"])
    for t0, t1 in zip(turns, turns[1:] + [turns[0] + 2 * np.pi]):
        gap = (t0 + t1) / 2
        band &= (abs(dx * np.sin(gap) - dy * np.cos(gap)) > 2.5) | (dx * np.cos(gap) + dy * np.sin(gap) < 0)
    terrain[band] = TERRAINS["FOREST"]
    d["terrain"] = terrain.tolist()
    out, used = [], dist > gold[0]
    for _ in range(gold[1]):
        for _ in range(36):                                              # a free spot for the clump
            r, b = gold[0] * np.sqrt(rng.uniform(0, 0.8)), rng.uniform(0, 2 * np.pi)
            c = (int(n / 2 + r * np.cos(b)), int(n / 2 + r * np.sin(b)))
            cells = sorted(square(c, 2, n), key=lambda t: (t[0] - c[0]) ** 2 + (t[1] - c[1]) ** 2)[:gold[2]]
            if not any(used[t] for t in cells):
                break
        else:
            continue
        for t in cells:
            used[max(0, t[0] - 1):t[0] + 2, max(0, t[1] - 1):t[1] + 2] = True
        out += [{"name": "GOLD_MINE", "player": 0, "x": t[0] + 0.5, "y": t[1] + 0.5} for t in cells]
    return out


def river(d, spec, rng):
    """A river of half width spec[0] across the whole map through the middle, on the line that is farthest from the
    player origins (for 2 players: between them), with a meander. spec[1] to spec[2] fords of SHALLOW, 3 tiles wide,
    at even places along it; no forest next to a ford, so units walk across."""
    w, least, most = spec
    n, terrain = d["size"], np.array(d["terrain"])
    x, y = np.mgrid[0:n, 0:n] + 0.5 - n / 2
    a = max(np.linspace(0, np.pi, 36, endpoint=False),                  # the normal of the river line
            key=lambda a: min(abs((st["x"] - n / 2) * np.cos(a) + (st["y"] - n / 2) * np.sin(a)) for st in d["lands"]))
    along = -x * np.sin(a) + y * np.cos(a)
    side = x * np.cos(a) + y * np.sin(a) - 3 * np.sin(along * 4 * np.pi / n + rng.uniform(0, 2 * np.pi))
    water = np.abs(side) <= w
    k = rng.integers(least, most + 1)
    fords = np.linspace(-0.6, 0.6, k) * n / 2 + rng.uniform(-3, 3, k)
    ford = water & (np.abs(along[..., None] - fords).min(-1) <= 1.5)
    terrain[water] = TERRAINS["WATER"]
    terrain[ford] = TERRAINS["SHALLOW"]
    terrain[dilate(ford, 3) & np.isin(terrain, list(FOREST_TREES))] = TERRAINS["GRASS"]
    d["terrain"] = terrain.tolist()


def paths(d, w):
    """Open grass paths of half width w from each player origin to the middle of the map."""
    n, terrain = d["size"], np.array(d["terrain"])
    way = np.zeros((n, n), bool)
    for st in d["lands"]:
        for t in np.linspace(0, 1, 2 * n):
            way[int(st["x"] + t * ((n - 1) / 2 - st["x"])), int(st["y"] + t * ((n - 1) / 2 - st["y"]))] = True
    way = dilate(way, w) & np.isin(terrain, list(FOREST_TREES))
    terrain[way] = TERRAINS["GRASS"]
    d["terrain"] = terrain.tolist()


def random_map(kind, seed, players=2):
    """The map description of an own generator (GENERATORS) and seed: the land of generate() (with the WALLS, PATHS
    and RIVERS of the kind), a town center at each player origin and the START objects around it, on free tiles (no
    forest, no water, not next to a wall)."""
    d = generate(GENERATORS[kind], seed, players)
    rng = np.random.default_rng([seed, 993])
    if kind in PATHS:
        paths(d, PATHS[kind])
    if kind in RIVERS:
        river(d, RIVERS[kind], rng)
    objects = walls(d, WALLS[kind], rng) if kind in WALLS else []
    if kind in GOLDS:
        objects += goldfield(d, GOLDS[kind], RINGS[kind], rng)
    n, terrain = d["size"], np.array(d["terrain"])
    used = np.isin(terrain, list(FOREST_TREES) + [TERRAINS["WATER"], TERRAINS["SHALLOW"]])
    for o in objects:                                      # no start object next to a wall or a gold mine
        used[max(0, int(o["x"]) - 1):int(o["x"]) + 2, max(0, int(o["y"]) - 1):int(o["y"]) + 2] = True
    for st in d["lands"]:
        cx, cy = st["x"], st["y"]
        used[max(0, cx - 3):cx + 3, max(0, cy - 3):cy + 3] = True       # the 4 × 4 town center and a path around it
        objects.append({"name": "TOWN_CENTER", "player": st["player"], "x": cx, "y": cy})
        if kind in WOODS:
            woodline(terrain, used, (cx, cy), WOODS[kind][:2], rng)
        start = START + (((FOREST_TREES[TERRAINS["FOREST"]], 1, 5, 0),) * WOODS[kind][2] if kind in WOODS else ())
        for name, count, dist, own in start:
            turn = rng.uniform(0, 2 * np.pi)
            for k in range(36):                                          # 36 directions, from a random one
                a = turn + k * np.pi / 18
                c = (int(round(cx - 0.5 + dist * np.cos(a))), int(round(cy - 0.5 + dist * np.sin(a))))
                cells = sorted(square(c, 2, n), key=lambda t: (t[0] - c[0]) ** 2 + (t[1] - c[1]) ** 2)[:count]
                if len(cells) == count and not any(used[t] for t in cells):
                    break
            else:
                continue                                                 # no space: the group is missing
            for t in cells:
                used[max(0, t[0] - 1):t[0] + 2, max(0, t[1] - 1):t[1] + 2] = True
                objects.append({"name": name, "player": st["player"] * own, "x": t[0] + 0.5, "y": t[1] + 0.5})
    d["terrain"] = terrain.tolist()
    d["objects"] = objects + trees(terrain)
    return d


def woodline(terrain, used, tc, wood, rng):
    """A forest clump of wood[1] tiles that grows (grow) from a free tile at wood[0] tiles from the town center tc,
    only on free land 7 to 13 tiles from it: the near wood of a player."""
    n, (dist, count) = terrain.shape[0], wood
    x, y = np.mgrid[0:n, 0:n] + 0.5
    r = np.hypot(x - tc[0], y - tc[1])
    free = (r >= 7) & (r <= 13) & ~used
    turn = rng.uniform(0, 2 * np.pi)
    for k in range(36):
        a = turn + k * np.pi / 18
        c = (int(tc[0] + dist * np.cos(a)), int(tc[1] + dist * np.sin(a)))
        if 0 <= min(c) and max(c) < n and free[max(0, c[0] - 2):c[0] + 3, max(0, c[1] - 2):c[1] + 3].all():
            break
    else:
        return                                                           # no space: no wood line
    mark = np.full((n, n), -1, np.int32)
    grow(mark, [{"id": 0, "cells": [c], "target": count, "clump": 15}], free, rng)
    terrain[mark >= 0] = TERRAINS["FOREST"]
    used[mark >= 0] = True
