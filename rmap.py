"""
The land of a random map from an AoE2 random map script (.rms, #963, decision A of #961): the user gives the script
of the own AoE2 install, the repository has no game script. generate() reads the land part of the script and returns
a map description of #960 (aoe2mc.read_json): the terrain and the elevation of each tile, and only the trees of the
forest tiles as objects (FOREST_TREES) yet.

Read: `#const`, `#define`, `if`/`elseif`/`else`/`endif`, `start_random`/`percent_chance`/`end_random`,
<PLAYER_SETUP> (no effect here), <LAND_GENERATION> (`base_terrain`, `create_player_lands`, `create_land` with
`terrain_type`, `land_percent`, `number_of_tiles`, `base_size`, `clumping_factor`, `land_position` and the borders
`left_border`, `right_border`, `top_border`, `bottom_border`: percent of the map size at the low x, high x, low y and
high y side that the land does not take) and
<TERRAIN_GENERATION> (`create_terrain` with `base_terrain`, `number_of_clumps`, `number_of_tiles`, `land_percent`,
`spacing_to_other_terrain_types`, `set_avoid_player_start_areas`, `clumping_factor`), <CONNECTION_GENERATION>
(`create_connect_all_players_land` with `replace_terrain`, `terrain_cost`, `terrain_size`: paths between the player
lands, #3868; `create_connect_all_lands`, `create_connect_to_nonplayer_land`, `create_connect_same_land_zones`,
`create_connect_land_zones` and the `zone` of a land, #3869) and <ELEVATION_GENERATION>
(`create_elevation HEIGHT` with `base_terrain`, `number_of_clumps`, `number_of_tiles`, `spacing`: hills level by level,
never on water or shallows, #3822) and <CLIFF_GENERATION> (cliff lines of CLIFF_DEFAULT objects, cliffs(), #3850).
Other sections and attributes:
a warning. `#include_drs random_map.def` has no effect (the constants are in TERRAINS); another #include file: a
warning. All randomness comes from numpy.random.default_rng(seed).
"""
import heapq
import re
import sys

import numpy as np

from units import rows

# The lines of data/rmap.jsonl (#2037): "terrain": the AoE2 terrain ID (AoE2ScenarioParser TerrainId value) of a
# terrain constant of the RMS language. "forest": the forest terrains of a tree: the game puts one on each forest tile,
# a scenario keeps them as objects. "start", "scatter", "fish", "shore_fish": see START, SCATTER, FISH and fish().
RMAP = rows("rmap.jsonl")
TERRAINS = {r["name"]: r["terrain"] for r in RMAP if "terrain" in r}
FOREST_TREES = dict(sorted((t, r["name"]) for r in RMAP for t in r.get("forest", ())))
SHORE_FISH = next(r["name"] for r in RMAP if r.get("shore_fish"))
SIZES = {1: 120, 2: 120, 3: 144, 4: 144, 5: 168, 6: 168, 7: 200, 8: 200}    # AoE2 map size of a player count
LABELS = ((120, "TINY_MAP"), (144, "SMALL_MAP"), (168, "MEDIUM_MAP"), (200, "LARGE_MAP"), (220, "HUGE_MAP"))
BORDERS = ("left_border", "right_border", "top_border", "bottom_border")   # of create_land (low x, high x, low y, high y)
RING = 0.35                     # the circle of the player lands: radius in map sizes
AVOID = 13                      # set_avoid_player_start_areas: default tiles from a player origin
STEPS = ((1, 0), (-1, 0), (0, 1), (0, -1))
SECTIONS = ("PLAYER_SETUP", "LAND_GENERATION", "TERRAIN_GENERATION", "CONNECTION_GENERATION", "ELEVATION_GENERATION",
            "CLIFF_GENERATION")
# <CLIFF_GENERATION> defaults of the AoE2 DE random map scripting guide (#3850). A length counts cliff pieces.
CLIFF_DEFAULTS = {"min_number_of_cliffs": 3, "max_number_of_cliffs": 8, "min_length_of_cliff": 5,
                  "max_length_of_cliff": 9, "cliff_curliness": 36, "min_distance_cliffs": 2, "min_terrain_distance": 2}
CLIFF_STEP = 3                  # tiles between two cliff pieces: the converter draws a CLIFF 3 tiles wide (aoe2mc, big)
DIRS = ((1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1))


class RmsError(ValueError):
    pass


def tokens(text):
    """The words of a script without its /* comments */; braces and section names are words."""
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    return re.sub(r"([{}])", r" \1 ", text).split()


def expand(words, rng, defined, consts, includes):
    """The words of the active branches: if/elseif/else/endif on the defined labels, one percent_chance branch of
    each start_random (a draw only for an active block), #define and #const go into defined and consts. An #include
    line is not a word: its (directive, file) goes into includes."""
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
        elif w.startswith("#include"):
            includes.append((w, words[i + 1]))
            i += 3 if w == "#include_drs" and i + 2 < len(words) and words[i + 2].isdigit() else 2
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


class Attrs(dict):
    """The attributes of a command: the arguments of the last one of each name; .many: of each one (replace_terrain
    can come more than once in a block)."""
    def __init__(self):
        super().__init__()
        self.many = {}


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
        attrs = Attrs()
        if i < len(words) and words[i] == "{":
            i += 1
            while i < len(words) and words[i] != "}":
                name = words[i]
                attrs[name], i = args(i + 1)
                attrs.many.setdefault(name, []).append(attrs[name])
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
    lands: [{"id", "cells" (start tiles), "target" (tiles), "clump", "box" (optional: (x0, x1, y0, y1), the tiles
    that the land can take)}]; free: a bool array of the tiles to take."""
    n = owner.shape[0]
    for land in lands:
        land["front"], land["seen"], land["count"] = [], set(), 0
        for c in land["cells"]:
            if free[c] and owner[c] < 0 and inside(land, c):
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
                if owner[c] >= 0 or not free[c] or not inside(land, c):
                    continue
                owner[c] = land["id"]
                land["count"] += 1
                add_front(land, c, n)
                busy = True
                break
        if not busy:
            return


def inside(land, c):
    """True when tile c is in the borders of the land (its "box"), or the land has no borders."""
    x0, x1, y0, y1 = land.get("box", (0, 1 << 30, 0, 1 << 30))
    return x0 <= c[0] < x1 and y0 <= c[1] < y1


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


def scaled(attrs, consts, n, clumps, total):
    """number_of_clumps and the tile count, scaled from a 100 × 100 map to n × n tiles: set_scale_by_groups scales the
    clumps, set_scale_by_size the tiles (as in AoE2 DE)."""
    k = n * n / 10000
    if "set_scale_by_groups" in attrs:
        clumps = max(1, round(clumps * k))
    if "set_scale_by_size" in attrs:
        total = round(total * k)
    return clumps, total


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


def route(weight, a, b):
    """The cheapest 4-step path from tile a to tile b (Dijkstra): a tile costs its weight, weight 0 is never on it."""
    n = len(weight)
    best, back, heap = {a: weight[a]}, {}, [(weight[a], a)]
    while heap:
        d, c = heapq.heappop(heap)
        if c == b:
            break
        if d > best[c]:
            continue
        for s in ((c[0] + 1, c[1]), (c[0] - 1, c[1]), (c[0], c[1] + 1), (c[0], c[1] - 1)):
            if 0 <= s[0] < n and 0 <= s[1] < n and weight[s] > 0 and d + weight[s] < best.get(s, np.inf):
                best[s], back[s] = d + weight[s], c
                heapq.heappush(heap, (best[s], s))
    path = np.zeros((n, n), bool)
    while b in back or b == a:
        path[b] = True
        if b == a:
            break
        b = back[b]
    return path


def connections(terrain, lands, cmds, consts, rng, warn):
    """<CONNECTION_GENERATION>: a path between two land origins of each pair that the command names; lands are
    (origin, player or 0, zone). replace_terrain changes the terrain on a path, and terrain_size widens it on the
    tiles of a terrain (radius ± variance). terrain_cost 0: never on a path. create_connect_teams_lands makes no path:
    generate() has no teams, so each player is a team of one.
    default_terrain_replacement: the terrain of the other path tiles. accumulate_connections has no source yet (#3870)."""
    n = len(terrain)
    pairs = {"create_connect_all_players_land": lambda a, b, z: a[1] and b[1],
             "create_connect_teams_lands": lambda a, b, z: False,
             "create_connect_all_lands": lambda a, b, z: True,
             "create_connect_to_nonplayer_land": lambda a, b, z: bool(a[1]) != bool(b[1]),
             "create_connect_same_land_zones": lambda a, b, z: a[2] == b[2],
             "create_connect_land_zones": lambda a, b, z: a[2] in z and b[2] in z}
    for cmd, args, attrs in cmds:
        if cmd not in pairs:
            warn(f"{cmd} is not read yet")
            continue
        zones = {value(v, consts) for v in args}
        each = lambda a: [[value(v, consts) for v in x] for x in attrs.many.get(a, ())]
        weight = np.ones((n, n), np.int64)
        for k, c in each("terrain_cost"):
            weight[terrain == k] = c
        path = np.zeros((n, n), bool)
        for i, a in enumerate(lands):
            for b in lands[i + 1:]:
                if pairs[cmd](a, b, zones):
                    path |= route(weight, tuple(a[0]), tuple(b[0]))
        wide = path.copy()
        for k, r, *v in each("terrain_size"):
            v = v[0] if v else 0
            for c in np.argwhere(path & (terrain == k)):
                for t in square(tuple(c), max(0, r + int(rng.integers(-v, v + 1))), n):
                    wide[t] = True
        old = terrain.copy()
        for a, b in each("replace_terrain"):
            terrain[wide & (old == a)] = b
        for d, in each("default_terrain_replacement"):                # the path tiles of no replace_terrain (#3870)
            terrain[wide & ~np.isin(old, [a for a, _ in each("replace_terrain")])] = d
        for a in set(attrs) - {"default_terrain_replacement", "replace_terrain", "terrain_cost", "terrain_size"}:
            warn(f"{cmd}: {a} is not read yet")


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
    includes = []
    sections = commands(expand(tokens(text), rng, defined, consts, includes))
    for s in sections:
        if s not in SECTIONS:
            warn(f"<{s}> is not read yet")
    for directive, file in includes:               # random_map.def gives the constants; XS scripts are not run
        if file != "random_map.def":
            warn(f"{directive} {file} is not read")
    terrain = np.zeros((n, n), np.int16)
    owner = np.full((n, n), -1, np.int32)
    lands, starts, kinds, links = [], [], {}, []
    for cmd, args, attrs in sections.get("LAND_GENERATION", ()):
        if cmd == "base_terrain":
            terrain[:] = value(args[0], consts)
        elif cmd in ("create_player_lands", "create_land"):
            base = value(attrs["base_size"][0], consts) if "base_size" in attrs else 3
            clump = value(attrs["clumping_factor"][0], consts) if "clumping_factor" in attrs else 8
            kind = value(attrs["terrain_type"][0], consts) if "terrain_type" in attrs else 0
            zone = value(attrs["zone"][0], consts) if "zone" in attrs else None      # None: a zone of its own
            edge = {a: value(attrs[a][0], consts) * n // 100 if a in attrs else 0 for a in BORDERS}
            box = (edge["left_border"], n - edge["right_border"], edge["top_border"], n - edge["bottom_border"])
            if cmd == "create_player_lands":
                total, turn = tiles(attrs, consts, n), rng.uniform(0, 2 * np.pi)
                for p in range(1, players + 1):
                    a = turn + 2 * np.pi * (p - 1) / players
                    c = (int(round((n - 1) / 2 + RING * n * np.cos(a))), int(round((n - 1) / 2 + RING * n * np.sin(a))))
                    starts.append({"player": p, "x": c[0], "y": c[1], "base_size": base, "land": len(lands)})
                    links.append((c, p, zone if zone is not None else -1 - len(lands)))
                    lands.append({"id": len(lands), "cells": square(c, base, n), "clump": clump, "box": box,
                                  "target": max(total // players, (2 * base + 1) ** 2)})
                    kinds[len(lands) - 1] = kind
            else:
                if "land_position" in attrs:
                    c = tuple(min(n - 1, value(v, consts) * n // 100) for v in attrs["land_position"][:2])
                else:
                    c = tuple(int(v) for v in rng.integers(0, n, 2))
                links.append((c, 0, zone if zone is not None else -1 - len(lands)))
                lands.append({"id": len(lands), "cells": square(c, base, n), "clump": clump, "box": box,
                              "target": tiles(attrs, consts, n, (2 * base + 1) ** 2)})
                kinds[len(lands) - 1] = kind
            for a in set(attrs) - {"base_size", "clumping_factor", "terrain_type", "land_percent", "number_of_tiles",
                                   "land_position", "zone", *BORDERS}:
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
        clumps, total = scaled(attrs, consts, n, value(attrs["number_of_clumps"][0], consts)
                               if "number_of_clumps" in attrs else 1, tiles(attrs, consts, n, 1))
        each = total // max(clumps, 1)
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
                               "spacing_to_other_terrain_types", "set_avoid_player_start_areas",
                               "set_scale_by_groups", "set_scale_by_size"}:
            warn(f"create_terrain: {a} is not read yet")
    connections(terrain, links, sections.get("CONNECTION_GENERATION", ()), consts, rng, warn)
    elevation = np.zeros((n, n), np.int16)
    for cmd, args, attrs in sections.get("ELEVATION_GENERATION", ()):
        if cmd != "create_elevation":
            warn(f"{cmd} is not read yet")
            continue
        top = value(args[0], consts) if args else 1
        on = value(attrs["base_terrain"][0], consts) if "base_terrain" in attrs else 0
        free = (terrain == on) & ~np.isin(terrain, [TERRAINS["WATER"], TERRAINS["SHALLOW"]]) & (elevation == 0)
        clumps, total = scaled(attrs, consts, n, value(attrs["number_of_clumps"][0], consts)
                               if "number_of_clumps" in attrs else 1, tiles(attrs, consts, n, 1))
        spacing = value(attrs["spacing"][0], consts) if "spacing" in attrs else 1
        # enable_balanced_elevation: each player land gets the same share of the hills (the fair hills of AoE2 DE)
        areas = ([free & (owner == st["land"]) for st in starts] if "enable_balanced_elevation" in attrs and starts
                 else [free])
        hill = np.zeros((n, n), bool)
        for area in areas:
            spots, k = np.argwhere(area), -(-clumps // len(areas))
            if len(spots) and top > 0:
                mark = np.full((n, n), -1, np.int32)
                grow(mark, [{"id": j, "cells": [tuple(int(v) for v in spots[rng.integers(len(spots))])],
                             "target": total // len(areas) // k, "clump": 8} for j in range(k)], area, rng)
                hill |= mark >= 0
        for k in range(top):                     # level k + 1 inside level k, spacing tiles from its edge
            elevation[hill] = k + 1
            hill &= ~dilate(~hill, max(spacing, 1))
        for a in set(attrs) - {"base_terrain", "number_of_clumps", "number_of_tiles", "spacing", "set_scale_by_groups",
                               "set_scale_by_size", "enable_balanced_elevation"}:
            warn(f"create_elevation: {a} is not read yet")
    objects = trees(terrain) + cliffs(sections.get("CLIFF_GENERATION", ()), terrain, starts, consts, rng, warn)
    return {"size": n, "terrain": terrain.tolist(), "elevation": elevation.tolist(), "objects": objects,
            "players": {str(p): {"color": p - 1} for p in range(1, players + 1)}, "lands": [{k: v for k, v in st.items() if k != "land"} for st in starts]}


def cliffs(cmds, terrain, starts, consts, rng, warn):
    """The cliff objects of <CLIFF_GENERATION> (#3850): lines of CLIFF_DEFAULT pieces CLIFF_STEP tiles apart. A line
    grows from a random free land tile and turns 45° at cliff_curliness percent of the steps. Free: no water, shallows
    or forest within min_terrain_distance, no player start area (base_size), no other line within min_distance_cliffs."""
    if not cmds:
        return []
    o = dict(CLIFF_DEFAULTS)
    for cmd, args, _ in cmds:
        if cmd in o and args:
            o[cmd] = value(args[0], consts)
        else:
            warn(f"{cmd} is not read yet")
    n = len(terrain)
    free = ~dilate(np.isin(terrain, [TERRAINS["WATER"], TERRAINS["SHALLOW"], *FOREST_TREES]), o["min_terrain_distance"])
    for st in starts:
        for c in square((st["x"], st["y"]), st["base_size"], n):
            free[c] = False
    out, count = [], int(rng.integers(o["min_number_of_cliffs"], max(o["min_number_of_cliffs"], o["max_number_of_cliffs"]) + 1))
    lo, hi = o["min_length_of_cliff"], max(o["min_length_of_cliff"], o["max_length_of_cliff"])
    for _ in range(count * 20):                  # tries: a line that cannot reach its length is dropped
        if len(out) == count or not free.any():
            break
        spots = np.argwhere(free)
        c, d, want = spots[rng.integers(len(spots))], int(rng.integers(8)), int(rng.integers(lo, hi + 1))
        line = [tuple(int(v) for v in c)]
        while len(line) < want:
            if rng.integers(100) < o["cliff_curliness"]:
                d = (d + (1 if rng.integers(2) else -1)) % 8
            x, y = line[-1][0] + DIRS[d][0] * CLIFF_STEP, line[-1][1] + DIRS[d][1] * CLIFF_STEP
            if not (0 <= x < n and 0 <= y < n and free[x, y]):
                break
            line.append((x, y))
        if len(line) < lo:
            continue
        out.append(line)
        mask = np.zeros((n, n), bool)
        mask[tuple(np.array(line).T)] = True
        free &= ~dilate(mask, CLIFF_STEP + o["min_distance_cliffs"])
    return [{"name": f"CLIFF_DEFAULT_{int(rng.integers(1, 10))}", "player": 0, "x": x + 0.5, "y": y + 0.5, "line": k}
            for k, line in enumerate(out) for x, y in line]


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
<ELEVATION_GENERATION>
create_elevation 2 { base_terrain DIRT number_of_clumps 14 number_of_tiles 600 spacing 2 }
"""
# The start objects of each player: (name, count, distance in tiles from the town center, owner: 0 = Gaia, 1 = the
# player). A group of more than one object stands on next tiles.
START = tuple((r["name"], *r["start"]) for r in RMAP if "start" in r)
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
<ELEVATION_GENERATION>
create_elevation 3 { base_terrain GRASS number_of_clumps 10 number_of_tiles 700 spacing 2 }
"""
# Mediterranean: a sea in the middle of the map, the player lands on the land ring around it, a beach at the coast
# (COASTS).
MEDITERRANEAN = """
<LAND_GENERATION>
base_terrain GRASS
create_player_lands { terrain_type GRASS2 land_percent 30 base_size 12 clumping_factor 15 }
create_land { terrain_type WATER land_position 50 50 base_size 8 land_percent 22 clumping_factor 20 }
<TERRAIN_GENERATION>
create_terrain FOREST { base_terrain GRASS number_of_clumps 8 land_percent 6 set_avoid_player_start_areas 16
  spacing_to_other_terrain_types 2 clumping_factor 15 }
create_terrain FOREST { base_terrain GRASS2 number_of_clumps 6 number_of_tiles 12 set_avoid_player_start_areas 12
  spacing_to_other_terrain_types 2 }
create_terrain DIRT3 { base_terrain GRASS number_of_clumps 10 land_percent 3 }
"""
# Nomad: one large land with a sea ring at the map edges (AoE2 wiki "Nomad (map)", #2336), and no town center at the
# start: the villagers stand apart (NOMADS) and the player builds the town center.
NOMAD = """
<LAND_GENERATION>
base_terrain WATER
create_player_lands { terrain_type GRASS2 land_percent 30 base_size 12 clumping_factor 15
  left_border 6 right_border 6 top_border 6 bottom_border 6 }
create_land { terrain_type GRASS land_position 50 50 base_size 12 land_percent 42 clumping_factor 20
  left_border 6 right_border 6 top_border 6 bottom_border 6 }
<TERRAIN_GENERATION>
create_terrain FOREST { base_terrain GRASS number_of_clumps 8 land_percent 6 set_avoid_player_start_areas 16
  spacing_to_other_terrain_types 2 clumping_factor 15 }
create_terrain FOREST { base_terrain GRASS2 number_of_clumps 6 number_of_tiles 12 set_avoid_player_start_areas 12
  spacing_to_other_terrain_types 2 }
create_terrain DIRT3 { base_terrain GRASS number_of_clumps 10 land_percent 3 }
"""
# Islands: water on the whole map, one island of grass for each player (ISLES keeps water between the islands), a beach
# at the coast (COASTS) and forests on each island away from the town center.
ISLANDS = """
<LAND_GENERATION>
base_terrain WATER
create_player_lands { terrain_type GRASS land_percent 40 base_size 10 clumping_factor 15 }
<TERRAIN_GENERATION>
create_terrain FOREST { base_terrain GRASS number_of_clumps 12 land_percent 7 set_avoid_player_start_areas 14
  spacing_to_other_terrain_types 2 clumping_factor 15 }
create_terrain DIRT3 { base_terrain GRASS number_of_clumps 10 land_percent 2 }
"""
GENERATORS = {"arabia": ARABIA,
              "arena": ARENA,
              "black_forest": BLACK_FOREST,
              "gold_rush": GOLD_RUSH,
              "highland": HIGHLAND,
              "islands": ISLANDS,
              "mediterranean": MEDITERRANEAN,
              "nomad": NOMAD}
WALLS = {"arena": 23}           # the radius in tiles of the stone wall circle around each player (outside START)
BAND = 6                        # the forest inside the wall: tiles of width, on the half away from the map middle
PATHS = {"black_forest": 1}     # the half width in tiles of the open path from each player to the middle
GOLDS = {"gold_rush": (10, 6, 5)}  # the gold of the middle: radius in tiles, clumps of gold mines, mines in a clump
RIVERS = {"highland": (3, 3, 5)}  # the river: half width in tiles, the least and the most fords
COASTS = {"islands": 1,         # the beach: tiles of width on the land next to the water
          "mediterranean": 1,
          "nomad": 1}
ISLES = {"islands": 2}          # the water between two islands: tiles that each island gives up next to another one
NOMADS = {"nomad": (6, 7)}      # no town center: each villager alone, at (tiles from the origin, tiles from each other)
# The Gaia resources of Nomad over the whole map, as AoE2 Nomad (#1944, wiki infobox): (name, objects of a group,
# groups per player). Pairs of sheep, single boars, 3-deer herds, 6 berry bushes, 6-tile gold and stone mines.
SCATTER = tuple((r["name"], *r["scatter"]) for r in RMAP if "scatter" in r)
AWAY = 12                       # tiles from each villager of Nomad to the SCATTER groups: the start is open land
RINGS = {"gold_rush": (14, 5)}  # the forest ring around the gold: inner radius and width in tiles, gaps between players
# The fish of a map kind: shore fish, the deep fish and its count (#1943).
FISH = {r["fish"][0]: (r["fish"][1], r["name"], r["fish"][2]) for r in RMAP if "fish" in r}
# The wolves of a map kind (#2019): (name, wolves per player near the gold of the middle, wolves per player on the whole
# map). The wiki names wolves on Gold Rush and Highland but gives no counts: the counts are own values.
WOLVES = {r["wolves"][0]: (r["name"], *r["wolves"][1:]) for r in RMAP if "wolves" in r}
TAME = 25                       # tiles from each town center to a wolf: no wolf at the start of a player
# The relics of each kind: 3 + 1 per player (AoE2 wiki: Arabia "five Relics" on 2-player maps, one more per player;
# Black Forest "Default: 3, Per player: 1"; the others "standard"), #2018. The distances in tiles to each town center
# (Nomad: each villager) and to each other relic are own values: the repository holds no text of the Microsoft
# scripts (decision #961).
RELICS = (3, 1, 20, 15)        # relics, more per player, tiles from a start, tiles from another relic
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
    elevation = np.array(d["elevation"])               # all water at level 0 (#164), a bank of level 1 at most
    wet = water | ford
    elevation[dilate(wet, 1) & ~wet] = np.minimum(elevation[dilate(wet, 1) & ~wet], 1)
    elevation[wet] = 0
    d["elevation"] = elevation.tolist()


def isles(d, gap):
    """Keep the islands apart: each land tile goes to the player origin that a walk over the land reaches first, and a
    tile within gap (a square) of the land of another player becomes water, so no walk goes from one island to another."""
    n, terrain = d["size"], np.array(d["terrain"])
    land, owner = terrain != TERRAINS["WATER"], np.full((n, n), -1, np.int32)
    for k, st in enumerate(d["lands"]):
        owner[st["x"], st["y"]] = k
    while True:                                          # grow all labels one step at a time (a walk of 4 steps)
        new = owner.copy()
        for dx, dy in STEPS:
            src = np.roll(owner, (dx, dy), (0, 1))
            if dx:
                src[0 if dx > 0 else -1, :] = -1
            else:
                src[:, 0 if dy > 0 else -1] = -1
            take = land & (new < 0) & (src >= 0)
            new[take] = src[take]
        if (new == owner).all():
            break
        owner = new
    for k in range(len(d["lands"])):
        terrain[(owner == k) & dilate((owner >= 0) & (owner != k), gap)] = TERRAINS["WATER"]
    d["terrain"] = terrain.tolist()


def coast(d, w):
    """A BEACH of w tiles on the land (not forest) next to the water."""
    terrain = np.array(d["terrain"])
    water = terrain == TERRAINS["WATER"]
    terrain[dilate(water, w) & ~water & ~np.isin(terrain, list(FOREST_TREES))] = TERRAINS["BEACH"]
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
    """The map description of an own generator (GENERATORS) and seed: the land of generate() (with the WALLS, PATHS,
    RIVERS, ISLES and COASTS of the kind), a town center at each player origin (not for NOMADS) and the START objects around
    it, on free tiles (no forest, no water, not next to a wall), the FISH of the kind and the RELICS."""
    d = generate(GENERATORS[kind], seed, players)
    rng = np.random.default_rng([seed, 993])
    if kind in PATHS:
        paths(d, PATHS[kind])
    if kind in RIVERS:
        river(d, RIVERS[kind], rng)
    if kind in ISLES:
        isles(d, ISLES[kind])
    if kind in COASTS:
        coast(d, COASTS[kind])
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
        if kind not in NOMADS:                                   # Nomad: the place stays free for the town center
            objects.append({"name": "TOWN_CENTER", "player": st["player"], "x": cx, "y": cy})
        if kind in WOODS:
            woodline(terrain, used, (cx, cy), WOODS[kind][:2], rng)
        start = START + (((FOREST_TREES[TERRAINS["FOREST"]], 1, 5, 0),) * WOODS[kind][2] if kind in WOODS else ())
        apart, far = [], NOMADS.get(kind, (0, 0))
        if kind in NOMADS:            # one group for each villager; no scout, as AoE2 Nomad (#1216); the rest: scatter()
            start = tuple((s[0], 1, far[0], s[3]) for s in start if s[0].startswith("VILLAGER") for _ in range(s[1]))
        for name, count, dist, own in start:
            turn = rng.uniform(0, 2 * np.pi)
            for k in range(36):                                          # 36 directions, from a random one
                a = turn + k * np.pi / 18
                c = (int(round(cx - 0.5 + dist * np.cos(a))), int(round(cy - 0.5 + dist * np.sin(a))))
                cells = sorted(square(c, 2, n), key=lambda t: (t[0] - c[0]) ** 2 + (t[1] - c[1]) ** 2)[:count]
                if len(cells) == count and not any(used[t] for t in cells) and \
                        all(np.hypot(c[0] - p[0], c[1] - p[1]) >= far[1] for p in apart * name.startswith("VILLAGER")):
                    break
            else:
                continue                                                 # no space: the group is missing
            for t in cells:
                used[max(0, t[0] - 1):t[0] + 2, max(0, t[1] - 1):t[1] + 2] = True
                objects.append({"name": name, "player": st["player"] * own, "x": t[0] + 0.5, "y": t[1] + 0.5})
            apart += cells * name.startswith("VILLAGER")
    if kind in FISH:
        objects += fish(terrain, FISH[kind], len(d["lands"]), rng)
    if kind in WOLVES:
        objects += wolves(used, WOLVES[kind], GOLDS.get(kind, (0,))[0] + 4, rng, d["lands"])
    if kind in NOMADS:
        objects += scatter(used, len(d["lands"]), rng, [(o["x"], o["y"]) for o in objects if o["name"].startswith("VILLAGER")])
    for o in objects:                                      # no relic next to a Nomad resource
        used[max(0, int(o["x"]) - 1):int(o["x"]) + 2, max(0, int(o["y"]) - 1):int(o["y"]) + 2] = True
    starts = [(o["x"], o["y"]) for o in objects if o["name"] == "TOWN_CENTER" or kind in NOMADS and
              o["name"].startswith("VILLAGER")]
    objects += relics(used, len(d["lands"]), np.random.default_rng([seed, 994]), starts)   # own rng: the rest stays
    d["terrain"] = terrain.tolist()
    d["objects"] = objects + trees(terrain)
    return d


def fish(terrain, spec, players, rng):
    """The fish of spec for each player: SHORE_FISH on water next to a beach, the deep fish on water 3 or more tiles from
    land (a ford is land). Each fish is 3 or more tiles from another one; a fish with no free place is missing."""
    shore, deep, count = spec
    water = terrain == TERRAINS["WATER"]
    taken, out = np.zeros(terrain.shape, bool), []
    for name, k, where in ((SHORE_FISH, shore, water & dilate(terrain == TERRAINS["BEACH"], 1)),
                           (deep, count, water & ~dilate(~water, 2))):
        x, y = np.nonzero(where)
        placed = 0
        for i in rng.permutation(len(x)):
            if placed == k * players:
                break
            if not taken[x[i], y[i]]:
                taken[max(0, x[i] - 2):x[i] + 3, max(0, y[i] - 2):y[i] + 3] = True
                out.append({"name": name, "player": 0, "x": x[i] + 0.5, "y": y[i] + 0.5})
                placed += 1
    return out


def scatter(used, players, rng, villagers):
    """The SCATTER groups of Nomad on random free tiles of the whole map (#1944): each group on next free tiles, not
    next to another object, at least AWAY tiles from each villager. A group with no space after 200 tries is missing."""
    n, out = used.shape[0], []
    x, y = np.mgrid[0:n, 0:n] + 0.5
    used = used.copy()
    for vx, vy in villagers:
        used |= np.hypot(x - vx, y - vy) < AWAY
    for name, count, groups in SCATTER:
        for _ in range(groups * players):
            for _ in range(200):
                c = (int(rng.integers(n)), int(rng.integers(n)))
                cells = sorted(square(c, 2, n), key=lambda t: (t[0] - c[0]) ** 2 + (t[1] - c[1]) ** 2)[:count]
                if len(cells) == count and not any(used[t] for t in cells):
                    break
            else:
                continue
            for t in cells:
                used[max(0, t[0] - 1):t[0] + 2, max(0, t[1] - 1):t[1] + 2] = True
                out.append({"name": name, "player": 0, "x": t[0] + 0.5, "y": t[1] + 0.5})
    return out


def wolves(used, spec, near, rng, lands):
    """The WOLVES of spec: spec[1] per player on free tiles within near tiles of the map middle (the gold of Gold Rush),
    spec[2] per player on free tiles of the whole map, each at least TAME tiles from each player origin. A wolf with no
    free tile is missing."""
    n, out = used.shape[0], []
    x, y = np.mgrid[0:n, 0:n] + 0.5
    free = ~used & np.all([np.hypot(x - st["x"], y - st["y"]) >= TAME for st in lands], axis=0)
    for count, where in ((spec[1], np.hypot(x - n / 2, y - n / 2) <= near), (spec[2], True)):
        for _ in range(count * len(lands)):
            cx, cy = np.nonzero(free & where)
            if not len(cx):
                break
            i = rng.integers(len(cx))
            free[max(0, cx[i] - 1):cx[i] + 2, max(0, cy[i] - 1):cy[i] + 2] = False
            used[cx[i], cy[i]] = True
            out.append({"name": spec[0], "player": 0, "x": cx[i] + 0.5, "y": cy[i] + 0.5})
    return out


def relics(used, players, rng, tcs):
    """The RELICS of a map (#2018) on random free tiles (`used` is False: no forest, water or shallows, not next to
    another object), far from each town center or Nomad villager of tcs and from each other relic. A relic with no
    place after 200 tries is missing."""
    count, more, start, apart = RELICS
    n, out = used.shape[0], []
    for _ in range(count + more * players):
        for _ in range(200):
            c = (int(rng.integers(n)) + 0.5, int(rng.integers(n)) + 0.5)
            if not used[int(c[0]), int(c[1])] and all(np.hypot(c[0] - x, c[1] - y) >= start for x, y in tcs) and \
                    all(np.hypot(c[0] - o["x"], c[1] - o["y"]) >= apart for o in out):
                out.append({"name": "RELIC", "player": 0, "x": c[0], "y": c[1]})
                break
    return out


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
