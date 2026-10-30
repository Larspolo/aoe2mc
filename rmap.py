"""
The land of a random map from an AoE2 random map script (.rms, #963, decision A of #961): the user gives the script
of the own AoE2 install, the repository has no game script. generate() reads the land part of the script and returns
a map description of #960 (aoe2mc.read_json): the terrain and the elevation of each tile, and only the trees of the
forest tiles as objects (FOREST_TREES) yet.

Read: `#const` (also `rnd(A,B)`, fractions and `(MATH)`, #4306), `#define`, `if`/`elseif`/`else`/`endif`, `start_random`/`percent_chance`/`end_random`,
<PLAYER_SETUP> (`grouped_by_team` with --teams), <LAND_GENERATION> (`base_terrain`, `create_player_lands`, `create_land` with
`terrain_type`, `base_layer` (a land layer on the terrain_type, #3967), `land_percent`, `number_of_tiles`, `base_size`, `clumping_factor`, `land_position`, `assign_to_player` and `assign_to_team` (direct_placement, #3947) and the borders
`left_border`, `right_border`, `top_border`, `bottom_border`: percent of the map size at the low x, high x, low y and
high y side that the land does not take; `other_zone_avoidance_distance`, `min_placement_distance`, #4421) and
<TERRAIN_GENERATION> (`create_terrain` with `base_terrain`, `number_of_clumps`, `number_of_tiles`, `land_percent`,
`spacing_to_other_terrain_types`, `set_avoid_player_start_areas`, `clumping_factor`), <CONNECTION_GENERATION>
(`create_connect_all_players_land` with `replace_terrain`, `terrain_cost`, `terrain_size`: paths between the player
lands, #3868; `create_connect_all_lands`, `create_connect_to_nonplayer_land`, `create_connect_same_land_zones`,
`create_connect_land_zones` and the `zone` of a land, #3869) and <ELEVATION_GENERATION>
(`create_elevation HEIGHT` with `base_terrain`, `base_layer`, `number_of_clumps`, `number_of_tiles`, `spacing`: hills level by level,
never on water or shallows, #3822), <CLIFF_GENERATION> (cliff lines of CLIFF_DEFAULT objects, cliffs(), #3850) and
<OBJECTS_GENERATION> (`create_object`: objects(), #3855). The sections run in the AoE2 DE order: lands, elevation,
terrains, connections (#3966); then all water goes to level 0. Other sections and attributes: a warning.
`#include_drs FILE` reads FILE from the folder of the script (#4304); without the file: `random_map.def` has no effect
(the constants are in TERRAINS), another #include file gives a warning. All
randomness comes from numpy.random.default_rng(seed).
"""
import heapq
import os
import re
import sys

import numpy as np

from units import rows

# The lines of data/rmap.jsonl (#2037): "terrain": the AoE2 terrain ID (AoE2ScenarioParser TerrainId value) of a
# terrain constant of the RMS language. "forest": the forest terrains of a tree: the game puts one on each forest tile,
# a scenario keeps them as objects. "start", "scatter", "fish", "shore_fish": see START, SCATTER, FISH and fish().
RMAP = rows("rmap.jsonl")
TERRAINS = {r["name"]: r["terrain"] for r in RMAP if "terrain" in r}
OBJECTS = {r["name"]: r["object"] for r in RMAP if "object" in r}     # the object constants of random_map.def: AoE2 IDs
FOREST_TREES = dict(sorted((t, r["name"]) for r in RMAP for t in r.get("forest", ())))
ASSIGN = {r["name"]: r["assign"] for r in RMAP if "assign" in r}       # the targets of assign_to: player, color, team
CLIFF_TYPES = {r["name"]: r["cliff_type"] for r in RMAP if "cliff_type" in r}   # cliff_type word: object name prefix
SHORE_FISH = next(r["name"] for r in RMAP if r.get("shore_fish"))
SIZES = {1: 120, 2: 120, 3: 144, 4: 144, 5: 168, 6: 168, 7: 200, 8: 200}    # AoE2 map size of a player count
LABELS = ((120, "TINY_MAP"), (144, "SMALL_MAP"), (168, "MEDIUM_MAP"), (200, "LARGE_MAP"), (220, "HUGE_MAP"))
BORDERS = ("left_border", "right_border", "top_border", "bottom_border")   # of create_land (low x, high x, low y, high y)
RING = 0.35                     # the circle of the player lands: radius in map sizes
AVOID = 13                      # set_avoid_player_start_areas: default tiles from a player origin
STEPS = ((1, 0), (-1, 0), (0, 1), (0, -1))
SECTIONS = (                    # the sections that generate reads, one per line in the AoE2 DE order (#4014)
    "PLAYER_SETUP",
    "LAND_GENERATION",
    "ELEVATION_GENERATION",
    "CLIFF_GENERATION",
    "TERRAIN_GENERATION",
    "CONNECTION_GENERATION",
    "OBJECTS_GENERATION",
)
# <CLIFF_GENERATION> defaults of the AoE2 DE random map scripting guide (#3850). A length counts cliff pieces.
CLIFF_DEFAULTS = {"min_number_of_cliffs": 3, "max_number_of_cliffs": 8, "min_length_of_cliff": 5,
                  "max_length_of_cliff": 9, "cliff_curliness": 36, "min_distance_cliffs": 2, "min_terrain_distance": 2}
CLIFF_STEP = 3                  # tiles between two cliff pieces: the converter draws a CLIFF 3 tiles wide (aoe2mc, big)
DIRS = ((1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1))


class RmsError(ValueError):
    pass


def tokens(text):
    """The words of a script without its /* comments */; braces and section names are words. Comments nest, as in the
    game: the */ of an inner comment does not end the outer one (a commented-out block with a note in it, #4695)."""
    keep, depth = [], 0
    for part in re.split(r"(/\*|\*/)", text):
        if part == "/*":
            depth += 1
        elif part == "*/":
            depth = max(depth - 1, 0)
        elif not depth:
            keep.append(part)
    return re.sub(r"([{}])", r" \1 ", " ".join(keep)).split()


def expand(words, rng, defined, consts, includes, folder=None, depth=0):
    """The words of the active branches: if/elseif/else/endif on the defined labels, one percent_chance branch of
    each start_random (a draw only for an active block), #define and #const go into defined and consts. An #include
    line is not a word: the words of an #include_drs file in folder take its place (#4304), else its (directive,
    file) goes into includes."""
    out, stack, i = [], [], 0
    def on():
        return all(f["on"] for f in stack)
    def arg():                                      # a command as the last word: an RmsError, not an IndexError (#4697)
        if i + 1 >= len(words):
            raise RmsError(f"{w} has no argument")
        return words[i + 1]
    def top():
        if not stack:
            raise RmsError(f"{w} without its start")
        return stack[-1]
    while i < len(words):
        w = words[i]
        if w == "if":
            c = on() and arg() in defined
            stack.append({"on": c, "done": c})
            i += 2
        elif w == "elseif":
            f = top()
            f["on"] = not f["done"] and arg() in defined
            f["done"] |= f["on"]
            i += 2
        elif w == "else":
            f = top()
            f["on"], f["done"] = not f["done"], True
            i += 1
        elif w == "start_random":
            stack.append({"on": False, "done": False, "roll": int(rng.integers(100)) if on() else 100, "acc": 0})
            i += 1
        elif w == "percent_chance":
            f, n = top(), int(arg())
            if "roll" not in f:
                raise RmsError("percent_chance outside start_random")
            f["on"] = not f["done"] and f["acc"] <= f["roll"] < f["acc"] + n
            f["done"] |= f["on"]
            f["acc"] += n
            i += 2
        elif w in ("endif", "end_random"):
            if not stack:
                raise RmsError(f"{w} without its start (after: {' '.join(words[max(0, i - 8):i])})")
            stack.pop()
            i += 1
        elif not on():
            i += 1
        elif w.startswith("#include"):
            path = folder and os.path.join(folder, *arg().replace("\\", "/").split("/"))
            if w == "#include_drs" and path and os.path.isfile(path):
                if depth >= 8:
                    raise RmsError(f"#include_drs {words[i + 1]}: more than 8 levels (a loop?)")
                with open(path, encoding="utf-8", errors="replace") as f:
                    out += expand(tokens(f.read()), rng, defined, consts, includes, folder, depth + 1)
            else:
                includes.append((w, arg()))
            i += 3 if w == "#include_drs" and i + 2 < len(words) and words[i + 2].isdigit() else 2
        elif w == "#define":
            defined.add(arg())
            i += 2
        elif w == "#const":                             # a #const with no value defines nothing (#4309)
            v = words[i + 2] if i + 2 < len(words) else ""
            if v.startswith(("(", "rnd(", "-")) or re.fullmatch(r"\d+\.?\d*|\.\d+", v) or v in consts:
                text, j = group(words, i + 2)
                consts[words[i + 1]] = calc(text, consts, rng)
                i = j
            else:
                i += 2
        elif w.startswith(("(", "rnd(")):
            text, i = group(words, i)
            out.append(str(calc(text, consts, rng)))     # one rnd() draw where it is written (#4306)
        else:
            out.append(w)
            i += 1
    if stack:
        raise RmsError("an if or start_random has no end")
    return out


class Args(list):
    """The arguments of a command or an attribute: a missing one gives an RmsError with the name (#4697)."""
    def __init__(self, name, words):
        super().__init__(words)
        self.name = name

    def __getitem__(self, k):
        try:
            return super().__getitem__(k)
        except IndexError:
            raise RmsError(f"{self.name}: too few arguments") from None


class Attrs(dict):
    """The attributes of a command: the arguments of the last one of each name; .many: of each one (replace_terrain
    can come more than once in a block)."""
    def __init__(self):
        super().__init__()
        self.many = {}


def commands(words):
    """{section: [(command, [args], {attribute: [args]})]}. A command or an attribute is a lower case word; its
    arguments are the next words that are numbers or upper case constants."""
    out, section, i = {}, None, 0          # a command before the first section goes to "HEADER" (#4308)
    def args(name, i):
        a = Args(name, [])
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
        a, i = args(w, i + 1)
        attrs = Attrs()
        if i < len(words) and words[i] == "{":
            i += 1
            while i < len(words) and words[i] != "}":
                name = words[i]
                attrs[name], i = args(name, i + 1)
                attrs.many.setdefault(name, []).append(attrs[name])
            i += 1
        if section is None:
            section = out.setdefault("HEADER", [])
        section.append((w, a, attrs))
    return out


def group(words, i):
    """The text of the math group or rnd() that starts at words[i] (tokens() splits it at the spaces) and the index
    after it."""
    text = words[i]
    while text.count("(") > text.count(")") and i + 1 < len(words):
        i += 1
        text += " " + words[i]
    return text, i + 1


def calc(text, consts, rng):
    """The number of a math word of AoE2 DE (#4306): a number (also 0.72), a constant, rnd(A,B) (a whole number from
    A to B), or (EXPRESSION) with + - * / and the usual order. A whole result stays an int."""
    parts = re.findall(r"rnd\(\s*-?\d+\s*,\s*-?\d+\s*\)|\d+\.?\d*|\.\d+|[A-Za-z_]\w*|[-+*/()]|\S", text)
    pos = 0
    def fail():
        raise RmsError(f"bad math {text!r}")
    def atom():
        nonlocal pos
        p = parts[pos] if pos < len(parts) else fail()
        pos += 1
        if p == "(":
            x = add()
            if pos >= len(parts) or parts[pos] != ")":
                fail()
            pos += 1
            return x
        if p == "-":
            return -atom()
        if m := re.fullmatch(r"rnd\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)", p):
            return int(rng.integers(int(m[1]), int(m[2]) + 1))
        if re.fullmatch(r"\d+\.?\d*|\.\d+", p):
            return float(p) if "." in p else int(p)
        if re.fullmatch(r"[A-Za-z_]\w*", p):
            if p not in consts:
                raise RmsError(f"unknown constant {p!r}")
            return consts[p]
        fail()
    def mul():
        nonlocal pos
        x = atom()
        while pos < len(parts) and parts[pos] in "*/":
            op = parts[pos]
            pos += 1
            y = atom()
            if op == "/" and y == 0:
                fail()
            x = x * y if op == "*" else x / y
        return x
    def add():
        nonlocal pos
        x = mul()
        while pos < len(parts) and parts[pos] in "+-":
            op = parts[pos]
            pos += 1
            x = x + mul() if op == "+" else x - mul()
        return x
    x = add()
    if pos != len(parts):
        fail()
    return int(x) if x == int(x) else x


def value(word, consts):
    """A whole number: a number word, or a constant; a fraction rounds half away from zero (#4306)."""
    if re.fullmatch(r"-?\d+", word):
        return int(word)
    if re.fullmatch(r"-?\d*\.\d+", word):
        x = float(word)
    elif word not in consts:
        raise RmsError(f"unknown constant {word!r}")
    else:
        x = consts[word]
    return int(x + (0.5 if x >= 0 else -0.5)) if isinstance(x, float) else x


def grow(owner, lands, free, rng):
    """Grow the lands at the same time, one tile each in turn, as AoE2 does: a land takes a free tile next to it. A
    higher clumping factor tries more tiles and takes the one with most tiles of the land around it (round lands).
    lands: [{"id", "cells" (start tiles), "target" (tiles), "clump", "box" (optional: (x0, x1, y0, y1), the tiles
    that the land can take), "zone" and "avoid" (optional: other_zone_avoidance_distance, #4421)}]; free: a bool
    array of the tiles to take."""
    n = owner.shape[0]
    zone = {land["id"]: land.get("zone", -1 - land["id"]) for land in lands}
    avoid = {land["id"]: land.get("avoid", 0) for land in lands}
    r = max(avoid.values(), default=0)

    def apart(land, c):                         # no tile of another zone within the larger avoidance distance
        if not r:
            return True
        x0, y0 = max(0, c[0] - r), max(0, c[1] - r)
        box = owner[x0:c[0] + r + 1, y0:c[1] + r + 1]
        for x, y in zip(*np.nonzero(box >= 0)):
            o = int(box[x, y])
            if zone[o] != zone[land["id"]] and max(abs(x0 + x - c[0]), abs(y0 + y - c[1])) <= max(avoid[o], avoid[land["id"]]):
                return False
        return True
    for land in lands:
        land["front"], land["seen"], land["count"] = [], set(), 0
        for c in land["cells"]:
            if free[c] and owner[c] < 0 and inside(land, c) and apart(land, c):
                owner[c] = land["id"]
                land["count"] += 1
        for c in zip(*np.nonzero(owner == land["id"])):
            add_front(land, c, n)
    while True:
        busy = False
        for land in lands:
            front = land["front"]
            while front and land["count"] < land["target"]:
                tries = [int(rng.integers(len(front))) for _ in range(max(1, 1 + land["clump"] // 5))]
                                                       # a negative clumping_factor: one try, not none (#4309)
                k = max(tries, key=lambda k: sum(owner[c] == land["id"] for c in near(front[k], n)))
                c = front[k]
                front[k] = front[-1]
                front.pop()
                if owner[c] >= 0 or not free[c] or not inside(land, c, rng) or not apart(land, c):
                    continue
                owner[c] = land["id"]
                land["count"] += 1
                add_front(land, c, n)
                busy = True
                break
        if not busy:
            return


def inside(land, c, rng=None):
    """True when tile c is in the borders of the land (its "box"), or the land has no borders. A land with a "fuzz"
    (border_fuzziness 0 to 100, #4422) takes a tile out of the box with the chance (100 - fuzz) %: 0 ignores the
    borders, 100 keeps them. It draws only for such a tile, so that the maps of other scripts stay the same."""
    x0, x1, y0, y1 = land.get("box", (0, 1 << 30, 0, 1 << 30))
    if x0 <= c[0] < x1 and y0 <= c[1] < y1:
        return True
    return rng is not None and land.get("fuzz", 100) < 100 and rng.uniform(0, 100) >= land["fuzz"]


def near(c, n):
    return [(c[0] + dx, c[1] + dy) for dx, dy in STEPS if 0 <= c[0] + dx < n and 0 <= c[1] + dy < n]


def add_front(land, c, n):
    for d in near(c, n):
        if d not in land["seen"]:
            land["seen"].add(d)
            land["front"].append(d)


def square(c, r, n, circular=False):
    """The tiles within r of tile c (a square), in the map. circular: only the tiles of the circle of radius r
    (set_circular_base, #4420)."""
    return [(x, y) for x in range(max(0, c[0] - r), min(n, c[0] + r + 1))
            for y in range(max(0, c[1] - r), min(n, c[1] + r + 1))
            if not circular or (x - c[0]) ** 2 + (y - c[1]) ** 2 <= r * r]


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
    default_terrain_replacement: the terrain of the other path tiles. Without accumulate_connections (DE), a connection
    reads the terrain of the start of the section, not the terrain that the earlier connections made (#4174)."""
    n = len(terrain)
    start = terrain.copy()
    acc = any(cmd == "accumulate_connections" for cmd, *_ in cmds)
    pairs = {"create_connect_all_players_land": lambda a, b, z: a[1] and b[1],
             "create_connect_teams_lands": lambda a, b, z: False,
             "create_connect_all_lands": lambda a, b, z: True,
             "create_connect_to_nonplayer_land": lambda a, b, z: bool(a[1]) != bool(b[1]),
             "create_connect_same_land_zones": lambda a, b, z: a[2] == b[2],
             "create_connect_land_zones": lambda a, b, z: a[2] in z and b[2] in z}
    for cmd, args, attrs in cmds:
        if cmd == "accumulate_connections":
            continue
        if cmd not in pairs:
            warn(f"{cmd} is not read yet")
            continue
        base = terrain if acc else start
        zones = {value(v, consts) for v in args}
        each = lambda a: [[value(v, consts) for v in x] for x in attrs.many.get(a, ())]
        weight = np.ones((n, n), np.int64)
        for k, c in each("terrain_cost"):
            weight[base == k] = c
        path = np.zeros((n, n), bool)
        for i, a in enumerate(lands):
            for b in lands[i + 1:]:
                if pairs[cmd](a, b, zones):
                    path |= route(weight, tuple(a[0]), tuple(b[0]))
        wide = path.copy()
        for k, r, *v in each("terrain_size"):
            v = v[0] if v else 0
            for c in np.argwhere(path & (base == k)):
                for t in square(tuple(c), max(0, r + int(rng.integers(-v, v + 1))), n):
                    wide[t] = True
        old = base.copy()
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


def elevate(section, terrain, layer, owner, starts, consts, rng, warn):
    """<ELEVATION_GENERATION>: the level of each tile. It runs on the land terrain, before <TERRAIN_GENERATION>, as in
    AoE2 DE: the base_terrain of create_elevation is a land terrain, and the forests and lakes come on the hills later.
    base_layer selects the tiles of a land layer (the base_layer of create_land, #3967) in place of base_terrain."""
    n = len(terrain)
    elevation = np.zeros((n, n), np.int16)
    for cmd, args, attrs in section:
        if cmd != "create_elevation":
            warn(f"{cmd} is not read yet")
            continue
        top = value(args[0], consts) if args else 1
        on = value(attrs["base_terrain"][0], consts) if "base_terrain" in attrs else 0
        under = (layer == value(attrs["base_layer"][0], consts)) if "base_layer" in attrs else terrain == on
        free = under & ~np.isin(terrain, [TERRAINS["WATER"], TERRAINS["SHALLOW"]]) & (elevation == 0)
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
        for a in set(attrs) - {"base_terrain", "base_layer", "number_of_clumps", "number_of_tiles", "spacing", "set_scale_by_groups",
                               "set_scale_by_size", "enable_balanced_elevation"}:
            warn(f"create_elevation: {a} is not read yet")
    return elevation


def lower_to_water(terrain, elevation):
    """All water at level 0 (#164) and the land at most d levels high d tiles from it: a hill steps down to a lake of
    <TERRAIN_GENERATION> or a river one level per tile, with no wall of blocks."""
    wet, out, near = np.isin(terrain, [TERRAINS["WATER"], TERRAINS["SHALLOW"]]), np.array(elevation), None
    for d in range(int(out.max(initial=0))):
        near = wet if near is None else dilate(near, 1)
        out[near & (out > d)] = d
    return out


def generate(text, seed, players=2, size=None, warn=None, teams=None, folder=None):
    """The map description (aoe2mc.read_json) of the land part of script text, for players on a map of size tiles
    (default: the AoE2 size of the player count). folder: the folder of the script, for its #include_drs files. teams: one team (or None) per player (#3946), see circle(). "lands": [{"player", "x", "y", "base_size"}] of the player lands.
    "mood": the color mood of color_correction (aoe2mc.MOODS). enable_waves and water_definition have no effect: Minecraft
    water takes its color from the biome."""
    warn = warn or (lambda m: print(f"rms: {m}", file=sys.stderr))
    rng = np.random.default_rng(seed)
    n = size or SIZES.get(players, 200)
    defined = {next((label for s, label in LABELS if n <= s), "GIGANTIC_MAP")}
    consts = TERRAINS | OBJECTS | {"MAPSIZE_SIDE": n}   # DE: the side of the map in tiles (#4693)
    includes = []
    sections = commands(expand(tokens(text), rng, defined, consts, includes, folder))
    for cmd, a, _ in sections.pop("HEADER", []):
        if cmd == "override_map_size" and a and not size:   # AoE2 DE: the script sets the map size
            n = int(value(a[0], consts))
        elif cmd != "override_map_size":
            warn(f"{cmd} is not read yet")
    for cmd, a, _ in sections.get("PLAYER_SETUP", ()):   # override_map_size works here too (#4580)
        if cmd == "override_map_size" and a and not size:
            n = int(value(a[0], consts))
        elif cmd not in PLAYER_SETUP:
            warn(f"{cmd} is not read yet")
    for s in sections:
        if s not in SECTIONS:
            warn(f"<{s}> is not read yet")
    for directive, file in includes:               # random_map.def gives the constants; XS scripts are not run
        if file != "random_map.def":
            warn(f"{directive} {file} is not read")
    terrain = np.zeros((n, n), np.int16)
    owner = np.full((n, n), -1, np.int32)
    layer = np.full((n, n), -1, np.int16)            # the land layer of each tile (aoe2mc.read_json "layer", -1 = none)
    lands, starts, kinds, links, layers = [], [], {}, [], {}
    heights = {}                                     # the base_elevation of each land index (#4418)
    ids = {}                                         # the land_id of a create_land -> its land index (#4133)
    mood = None                                      # color_correction CC_X: the color mood X (aoe2mc.MOODS, #4430)
    for cmd, args, attrs in sections.get("LAND_GENERATION", ()):
        if cmd == "base_terrain":
            terrain[:] = value(args[0], consts)
        elif cmd == "color_correction":
            from aoe2mc import MOODS
            name = args[0].upper().removeprefix("CC_") if args else ""
            if name in MOODS:
                mood = name
            else:
                warn(f"color_correction {' '.join(args)}: no such color mood")
        elif cmd in ("enable_waves", "water_definition"):   # Minecraft water has no waves and no look of its own
            pass
        elif cmd in ("create_player_lands", "create_land"):
            base = value(attrs["base_size"][0], consts) if "base_size" in attrs else 3
            clump = value(attrs["clumping_factor"][0], consts) if "clumping_factor" in attrs else 8
            kind = value(attrs["terrain_type"][0], consts) if "terrain_type" in attrs else 0
            zone = value(attrs["zone"][0], consts) if "zone" in attrs else None      # None: a zone of its own
            top = value(attrs["base_layer"][0], consts) if "base_layer" in attrs else None   # a layer on the land
            height = value(attrs["base_elevation"][0], consts) if "base_elevation" in attrs else 0
            edge = {a: value(attrs[a][0], consts) * n // 100 if a in attrs else 0 for a in BORDERS}
            box = (edge["left_border"], n - edge["right_border"], edge["top_border"], n - edge["bottom_border"])
            fuzz = value(attrs["border_fuzziness"][0], consts) if "border_fuzziness" in attrs else 100   # strict (#4422)
            avoid = value(attrs["other_zone_avoidance_distance"][0], consts) if "other_zone_avoidance_distance" in attrs else 0
            if cmd == "create_player_lands":
                total, turn = tiles(attrs, consts, n), rng.uniform(0, 2 * np.pi)
                order = circle(sections.get("PLAYER_SETUP", ()), players, teams, seed)
                radius = attrs.get("circle_radius")       # percent of the map size and its random change (#4420)
                ring = value(radius[0], consts) / 100 if radius else RING
                vary = value(radius[1], consts) / 100 if radius and len(radius) > 1 else 0
                for p in range(1, players + 1):
                    if any(st["player"] == p for st in starts):     # a land with assign_to_player has it (#3947)
                        continue
                    a = turn + 2 * np.pi * order.index(p) / players
                    r = ring + (rng.uniform(-vary, vary) if vary else 0)   # no draw with no change: same maps
                    c = (int(round((box[0] + box[1] - 1) / 2 + r * n * np.cos(a))),   # the circle in the box middle,
                         int(round((box[2] + box[3] - 1) / 2 + r * n * np.sin(a))))   # each start inside the box (#4719)
                    c = tuple(int(np.clip(v, lo + min(base, (hi - lo) // 2), hi - 1 - min(base, (hi - lo - 1) // 2)))
                              for v, lo, hi in ((c[0], box[0], box[1]), (c[1], box[2], box[3])))
                    starts.append({"player": p, "x": c[0], "y": c[1], "base_size": base, "land": len(lands)})
                    t = teams[p - 1] if teams and "set_zone_by_team" in attrs else None
                    z = zone if zone is not None else -1 - len(lands)
                    links.append((c, p, ("team", t) if t is not None else z))   # one zone per team (#4696)
                    lands.append({"id": len(lands), "cells": square(c, base, n, circular="set_circular_base" in attrs),
                                  "clump": clump, "box": box, "fuzz": fuzz, "zone": links[-1][2], "avoid": avoid,
                                  "target": max(total // players, (2 * base + 1) ** 2)})
                    kinds[len(lands) - 1] = kind
                    layers[len(lands) - 1] = top
                    heights[len(lands) - 1] = height
            else:
                if "land_position" in attrs:
                    c = tuple(min(n - 1, value(v, consts) * n // 100) for v in attrs["land_position"][:2])
                else:
                    c = tuple(int(v) for v in rng.integers(0, n, 2))
                    far = value(attrs["min_placement_distance"][0], consts) if "min_placement_distance" in attrs else 0
                    for _ in range(100):                # draw again until the origins before it are far enough (#4421)
                        if all(np.hypot(c[0] - o[0][0], c[1] - o[0][1]) >= far for o in links):
                            break
                        c = tuple(int(v) for v in rng.integers(0, n, 2))
                p = owner_of(attrs, consts, starts, players, teams)
                if p:                                       # direct_placement: the land of player p (#3947)
                    starts.append({"player": p, "x": c[0], "y": c[1], "base_size": base, "land": len(lands)})
                links.append((c, p, zone if zone is not None else -1 - len(lands)))
                lands.append({"id": len(lands), "cells": square(c, base, n, circular="set_circular_base" in attrs),
                              "clump": clump, "box": box, "fuzz": fuzz, "zone": links[-1][2], "avoid": avoid,
                              "target": tiles(attrs, consts, n, (2 * base + 1) ** 2)})
                kinds[len(lands) - 1] = kind
                layers[len(lands) - 1] = top
                heights[len(lands) - 1] = height
                if "land_id" in attrs:                  # only create_land: the guide gives player lands no ID
                    ids[value(attrs["land_id"][0], consts)] = len(lands) - 1
            for a in sorted(set(attrs) - set(CREATE_LAND)):
                warn(f"{cmd}: {a} is not read yet")
        else:
            warn(f"{cmd} is not read yet")
    if starts and len(starts) < players:            # direct_placement with too few lands: the rest on the circle
        for p in sorted(set(range(1, players + 1)) - {st["player"] for st in starts}):
            warn(f"player {p} has no land: a land on the circle")
            a = 2 * np.pi * (p - 1) / players
            c = (int(round((n - 1) / 2 + RING * n * np.cos(a))), int(round((n - 1) / 2 + RING * n * np.sin(a))))
            starts.append({"player": p, "x": c[0], "y": c[1], "base_size": 3, "land": len(lands)})
            links.append((c, p, -1 - len(lands)))
            lands.append({"id": len(lands), "cells": square(c, 3, n), "clump": 8, "box": (0, n, 0, n), "target": 49})
    grow(owner, lands, np.ones((n, n), bool), rng)
    for lid, kind in kinds.items():
        terrain[owner == lid] = kind
        if layers[lid] is not None:
            layer[owner == lid] = layers[lid]
    elevation = elevate(sections.get("ELEVATION_GENERATION", ()), terrain, layer, owner, starts, consts, rng, warn)
    for lid, height in heights.items():              # a raised land: its edge steps up one level per tile (AoE2 DE)
        land, step = owner == lid, 1
        near = ~land
        while step < height:
            near = dilate(near, 1)
            ring = land & near & (elevation < step)
            elevation[ring] = step
            land &= ~near
            step += 1
        elevation[land & (elevation < height)] = height
    for cmd, args, attrs in sections.get("TERRAIN_GENERATION", ()):
        if cmd != "create_terrain":
            warn(f"{cmd} is not read yet")
            continue
        kind = value(args[0], consts)
        on = value(attrs["base_terrain"][0], consts) if "base_terrain" in attrs else 0
        free = terrain == on
        if "height_limits" in attrs:               # only on the hill levels from MIN to MAX (AoE2 DE)
            lo, hi = (value(v, consts) for v in attrs["height_limits"][:2])
            free &= (elevation >= lo) & (elevation <= hi)
        if "set_flat_terrain_only" in attrs:       # only where the 8 neighbours have the same level
            p, flat = np.pad(elevation, 1, mode="edge"), np.ones((n, n), bool)
            for dy in (0, 1, 2):
                for dx in (0, 1, 2):
                    flat &= p[dy:dy + n, dx:dx + n] == elevation
            free &= flat
        if (s := value(attrs["spacing_to_other_terrain_types"][0], consts)
                if "spacing_to_other_terrain_types" in attrs else 0):
            free &= ~dilate(terrain != on, s)
        if "spacing_to_specific_terrain" in attrs:          # N tiles from terrain T
            t, s = (value(v, consts) for v in attrs["spacing_to_specific_terrain"][:2])
            free &= ~dilate(terrain == t, s)
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
        mask = value(attrs["terrain_mask"][0], consts) if "terrain_mask" in attrs else 0
        if mask == 1:                          # on top: the new terrain is only the look (#4419)
            layer[mark >= 0] = kind
        elif mask == 2:                        # under: the new terrain has the game role, the old one the look
            layer[mark >= 0] = terrain[mark >= 0]
            terrain[mark >= 0] = kind
        else:
            terrain[mark >= 0] = kind
        wet = np.isin(terrain, [TERRAINS["WATER"], TERRAINS["SHALLOW"]])
        if "beach_terrain" in attrs and wet[mark >= 0].all():   # the land tiles at the shore of new water get T
            terrain[dilate(mark >= 0, 1) & ~wet] = value(attrs["beach_terrain"][0], consts)
        for a in sorted(set(attrs) - set(CREATE_TERRAIN)):
            warn(f"create_terrain: {a} is not read yet")
    connections(terrain, links, sections.get("CONNECTION_GENERATION", ()), consts, rng, warn)
    elevation = lower_to_water(terrain, elevation)
    ridges = cliffs(sections.get("CLIFF_GENERATION", ()), terrain, starts, consts, rng, warn)   # draws before objects()
    found = []                                     # one line per object part, so that parallel parts do not conflict
    found += objects(sections.get("OBJECTS_GENERATION", ()), consts, terrain, starts, rng, warn, owner, ridges, layer,
                     land_ids=ids)
    found += trees(terrain)
    found += ridges
    return {"size": n, "terrain": terrain.tolist(), "elevation": elevation.tolist(), "layer": layer.tolist(),
            "objects": found, **({"mood": mood} if mood else {}),
            "players": {str(p): {"color": p - 1} | ({"team": teams[p - 1]} if teams else {}) for p in range(1, players + 1)},
            "lands": [{k: v for k, v in st.items() if k != "land"} for st in starts]}


def owner_of(attrs, consts, starts, players, teams):
    """The player of a create_land (#3947): assign_to_player N, or for assign_to_team T the next player of team T
    (teams, #3946) with no land yet; assign_to TARGET N (#4424): the player N, the player of color N (the default
    colors: player N) or the next player of team N (-1: any team). 0: no player."""
    taken = {st["player"] for st in starts}
    if "assign_to" in attrs:
        target, n = ASSIGN.get(attrs["assign_to"][0]), value(attrs["assign_to"][1], consts)
        if target != "team":
            return n if 1 <= n <= players and n not in taken else 0
        return next((p for p in range(1, players + 1) if p not in taken
                     and (n == -1 and teams and teams[p - 1] is not None or teams and teams[p - 1] == n)), 0)
    if "assign_to_player" in attrs:
        p = value(attrs["assign_to_player"][0], consts)
        return p if 1 <= p <= players and p not in taken else 0
    if "assign_to_team" in attrs and teams:
        t = value(attrs["assign_to_team"][0], consts)
        return next((p for p in range(1, players + 1) if teams[p - 1] == t and p not in taken), 0)
    return 0


def circle(setup, players, teams, seed):
    """The players in their order on the circle of create_player_lands (#3946). No teams: player order (the maps of
    earlier versions). With teams: random_placement (the AoE2 default) shuffles them, grouped_by_team puts the members
    of a team next to each other (the teams and the members of a team in a random order). A new generator, so that
    the other random numbers of the map do not change."""
    order = list(range(1, players + 1))
    if not teams:
        return order
    rng = np.random.default_rng([seed, 996])
    if any(cmd == "grouped_by_team" for cmd, _, _ in setup):
        groups = {}
        for p in order:                     # a player with no team is a team of its own
            groups.setdefault(teams[p - 1] if teams[p - 1] is not None else -p, []).append(p)
        keys = list(groups)
        return [p for k in rng.permutation(len(keys)) for p in rng.permutation(groups[keys[k]]).tolist()]
    return rng.permutation(order).tolist()


PLAYER_SETUP = (                # the commands of <PLAYER_SETUP> that generate() reads or that have no map effect: no warning (#4580)
    "ai_info_map_type",             # the AI map type: no effect on the land
    "behavior_version",             # the script version: no effect on the land
    "direct_placement",             # the start of the players: the game's own choice
    "effect_amount",                # the player settings of the game: no effect on the land
    "effect_percent",               # the player settings of the game: no effect on the land
    "force_nomad_treaty",           # the game rule: no effect on the land
    "grouped_by_team",              # the order of the players on the circle (circle())
    "guard_state",                  # the start units: no effect on the land
    "nomad_resources",              # the start resources: no effect on the land
    "override_map_size",            # the map size, the last value wins (generate())
    "random_placement",             # the order of the players on the circle (circle())
    "set_gaia_civilization",        # the Gaia civilization: no effect on the land
    "terrain_state",                # the terrain look: no effect on the land
    "weather_type",                 # the weather: no effect on the land
)
CREATE_LAND = (                 # the attributes of create_land and create_player_lands that generate() reads: one per line (#4417)
    "assign_to",
    "assign_to_player",
    "assign_to_team",
    "base_elevation",
    "base_layer",
    "base_size",
    "border_fuzziness",
    "bottom_border",
    "circle_radius",
    "clumping_factor",
    "generate_mode",                # no source gives its effect: read with no warning (#4423)
    "land_conformity",              # no source gives its effect: read with no warning (#4423)
    "land_id",
    "land_percent",
    "land_position",
    "left_border",
    "min_placement_distance",
    "number_of_tiles",
    "other_zone_avoidance_distance",
    "right_border",
    "set_circular_base",
    "set_zone_by_team",             # the lands of a team share one zone (#4696)
    "terrain_type",
    "top_border",
    "zone",
)
CREATE_TERRAIN = (              # the attributes of create_terrain that generate() reads: one per line (#4417)
    "base_terrain",
    "beach_terrain",
    "clumping_factor",
    "height_limits",
    "land_percent",
    "number_of_clumps",
    "number_of_tiles",
    "set_avoid_player_start_areas",
    "set_flat_terrain_only",
    "set_scale_by_groups",
    "set_scale_by_size",
    "spacing_to_other_terrain_types",
    "spacing_to_specific_terrain",
    "terrain_mask",
)
CREATE_OBJECT = (               # the attributes of create_object that objects() reads: one per line, in alphabetical order (#4224)
    "actor_area",                   # mark the tiles around each object for a later avoid_actor_area (#3858)
    "actor_area_radius",            # the radius of actor_area, default 1 (#3858)
    "actor_area_to_place_in",       # only in this actor area (#4134)
    "avoid_actor_area",             # out of this actor area (#3858)
    "avoid_all_actor_areas",        # out of each actor area (#4134)
    "avoid_cliff_zone",             # tiles from a cliff, default 1; never on the cliff tiles (#4131, `ridges`: the cliffs)
    "avoid_forest_zone",            # tiles from a forest, default 1 (#3858)
    "avoid_other_land_zones",       # tiles from each other land: other than the player land or the specific land (#4133)
    "find_closest",                 # the free tile nearest to the origin of the land, first in scan order (#4135)
    "find_closest_to_map_center",   # the free tile nearest to the map middle (#4135)
    "find_closest_to_map_edge",     # the free tile nearest to a map edge (#4135)
    "force_placement",              # with no free tile left, a used tile of the band (#4137)
    "generate_for_first_land_only", # only the first land of set_place_for_every_player (#4138)
    "group_placement_radius",       # tiles of a loose group from its first object, default 3 (#3856)
    "group_variance",               # ± objects in each group (#3856)
    "ignore_terrain_restrictions",  # also a land object on water, a fish on land (#4137)
    "layer_to_place_on",            # only the tiles of this land layer (#4132, `layer`: the land layer of each tile)
    "max_distance_to_other_zones",  # tiles from the lands of the other players (#3857)
    "max_distance_to_players",      # tiles from the origin of the player land (#3855)
    "min_distance_group_placement", # tiles from the other objects (#3857)
    "min_distance_to_map_edge",     # tiles from each map edge (#4427)
    "min_distance_to_players",      # tiles from the origin of the player land (#3855)
    "number_of_groups",             # groups of number_of_objects (± group_variance) objects (#3856)
    "number_of_objects",            # default 1; 3 for a VILLAGER: the start villagers of AoE2 DE (#3855, #4120)
    "place_on_forest_zone",         # only the tiles next to a forest (#3858)
    "place_on_specific_land_id",    # only the tiles of the create_land with this land_id (#4133)
    "require_path",                 # only the tiles with a land path to the origin of the player land (#4137)
    "resource_delta",               # more or less resources in the object: a key of the object for gather (#4429)
    "second_object",                # one more object on each tile (#3858)
    "set_circular_placement",       # a circle band of min and max_distance_to_players, default a square (#4136)
    "set_gaia_object_only",         # Gaia owns the objects of set_place_for_every_player (#3855)
    "set_loose_grouping",           # the default grouping (#3856)
    "set_place_for_every_player",   # number_of_objects for each player (#3855)
    "set_scaling_to_map_size",      # scale the groups, else the objects: a 100 × 100 map is the base (#3857)
    "set_scaling_to_player_number", # scale the groups, else the objects, by the player count (#3857)
    "set_tight_grouping",           # each next object on a free tile next to an object of the group (#3856)
    "temp_min_distance_group_placement",  # tiles between the groups of this command only (#4138)
    "terrain_to_place_on",          # only on this terrain (#3857)
)


def path(land, origin):
    """The tiles of land with a path (4 neighbours) to origin: a flood fill (#4137)."""
    out = np.zeros_like(land)
    if not land[origin]:
        return out
    out[origin] = True
    while True:
        grow = out.copy()
        grow[1:] |= out[:-1]
        grow[:-1] |= out[1:]
        grow[:, 1:] |= out[:, :-1]
        grow[:, :-1] |= out[:, 1:]
        grow &= land
        if (grow == out).all():
            return out
        out = grow


def objects(cmds, consts, terrain, starts, rng, warn, owner=None, ridges=(), layer=None, land_ids=None):
    """The objects of the create_object commands of <OBJECTS_GENERATION> (#3855), with the attributes of
    `CREATE_OBJECT`: number_of_objects on random free tiles, in groups with number_of_groups or a grouping attribute (#3856, #4699).
    Never on water (only a fish or a ship), a forest, a cliff or another object; an object with no free tile is missing.
    temp_min_distance_group_placement keeps the groups of one command apart; later commands do not avoid them (#4138).
    generate_for_first_land_only gives the objects of set_place_for_every_player to the first land only (#4138).
    require_path, force_placement and ignore_terrain_restrictions as in `CREATE_OBJECT` (#4137)."""
    import aoe2mc
    kinds = aoe2mc.object_kinds(old=False)
    n, out = terrain.shape[0], []
    wet = np.isin(terrain, [TERRAINS["WATER"], TERRAINS["SHALLOW"], TERRAINS["DEEP_WATER"]])
    used = np.isin(terrain, list(FOREST_TREES))
    cliff = np.zeros((n, n), bool)                     # the cliff pieces and their neighbours (#4131)
    for r in ridges:
        cliff[int(r["x"]), int(r["y"])] = True
    cliff = dilate(cliff, 1)
    used |= cliff
    placed = np.zeros((n, n), bool)                    # the tiles of the objects (min_distance_group_placement)
    x, y = np.mgrid[0:n, 0:n]
    areas = {}                                         # actor_area ID -> the tiles of its objects (#3858)
    for cmd, args, attrs in cmds:
        if cmd != "create_object":
            warn(f"{cmd} is not read yet")
            continue
        kind, base = kinds.get(value(args[0], consts), (None, None))
        if base is None:
            warn(f"create_object: unknown object {args[0]}")
            continue
        count = value(attrs["number_of_objects"][0], consts) if "number_of_objects" in attrs else 1 + 2 * (base == "VILLAGER_MALE")
                                                       # VILLAGER with no amount: the 3 start villagers of AoE2 DE (#4120)
        lo = value(attrs["min_distance_to_players"][0], consts) if "min_distance_to_players" in attrs else 0
        hi = value(attrs["max_distance_to_players"][0], consts) if "max_distance_to_players" in attrs else 2 * n
        water = any(w in base for w in ("FISH", "SHIP", "BOAT"))
        owners = ([(st, 0 if "set_gaia_object_only" in attrs else st["player"]) for st in starts]
                  if "set_place_for_every_player" in attrs else [(None, 0)])
        if "generate_for_first_land_only" in attrs:
            owners = owners[:1]
        groups = value(attrs["number_of_groups"][0], consts) if "number_of_groups" in attrs else None
        vary = value(attrs["group_variance"][0], consts) if "group_variance" in attrs else 0
        delta = {"resource_delta": value(attrs["resource_delta"][0], consts)} if "resource_delta" in attrs else {}
        radius = value(attrs["group_placement_radius"][0], consts) if "group_placement_radius" in attrs else 3
        tight = "set_tight_grouping" in attrs
        grouped = groups is not None or any(a in attrs for a in ("group_placement_radius", "set_loose_grouping", "set_tight_grouping"))
        circle = "set_circular_placement" in attrs
        k = (n * n / 10000 if "set_scaling_to_map_size" in attrs else 1) * (
            len(starts) if "set_scaling_to_player_number" in attrs else 1)
        if k != 1 and groups is None:
            count = max(1, round(count * k))
        elif k != 1:
            groups = max(1, round(groups * k))
        ground = (terrain == value(attrs["terrain_to_place_on"][0], consts)) if "terrain_to_place_on" in attrs else (wet == water) | ("ignore_terrain_restrictions" in attrs)
        if "layer_to_place_on" in attrs and layer is not None:
            ground = ground & (layer == value(attrs["layer_to_place_on"][0], consts))
        gap = value(attrs["min_distance_group_placement"][0], consts) if "min_distance_group_placement" in attrs else 0
        temp = value(attrs["temp_min_distance_group_placement"][0], consts) if "temp_min_distance_group_placement" in attrs else 0
        mine = np.zeros((n, n), bool)                  # the tiles of the groups of this command (temp_min_distance_group_placement)
        zones = value(attrs["max_distance_to_other_zones"][0], consts) if "max_distance_to_other_zones" in attrs else 0
        forest = np.isin(terrain, list(FOREST_TREES))
        # the filters of the ground: one each, in alphabetical order (#4224)
        if "actor_area_to_place_in" in attrs:
            ground = ground & areas.get(value(attrs["actor_area_to_place_in"][0], consts), np.zeros((n, n), bool))
        if "avoid_actor_area" in attrs:
            ground = ground & ~areas.get(value(attrs["avoid_actor_area"][0], consts), np.zeros((n, n), bool))
        if "avoid_all_actor_areas" in attrs:
            for area in areas.values():
                ground = ground & ~area
        if "avoid_cliff_zone" in attrs:
            ground = ground & ~dilate(cliff, value(attrs["avoid_cliff_zone"][0], consts) if attrs["avoid_cliff_zone"] else 1)
        if "avoid_forest_zone" in attrs:
            ground = ground & ~dilate(forest, value(attrs["avoid_forest_zone"][0], consts) if attrs["avoid_forest_zone"] else 1)
        if "min_distance_to_map_edge" in attrs:        # no tile within N tiles of an edge (#4427)
            edge = np.zeros((n, n), bool)
            m = value(attrs["min_distance_to_map_edge"][0], consts)
            edge[m:n - m, m:n - m] = True
            ground = ground & edge
        if "place_on_forest_zone" in attrs:
            ground = ground & dilate(forest, 1) & ~forest
        land = None                                    # the land of place_on_specific_land_id (#4133)
        if "place_on_specific_land_id" in attrs:
            land = (land_ids or {}).get(value(attrs["place_on_specific_land_id"][0], consts))
            if land is None or owner is None:
                warn(f"create_object {args[0]}: unknown land_id {attrs['place_on_specific_land_id'][0]}")
                continue
            ground = ground & (owner == land)
        other = value(attrs["avoid_other_land_zones"][0], consts) if "avoid_other_land_zones" in attrs else 0
        actor = value(attrs["actor_area"][0], consts) if "actor_area" in attrs else None
        reach = value(attrs["actor_area_radius"][0], consts) if "actor_area_radius" in attrs else 1
        second = kinds.get(value(attrs["second_object"][0], consts), (None, None))[1] if "second_object" in attrs else None
        for st, player in owners:
            if zones and st and owner is not None:
                place = ground & ~dilate((owner >= 0) & (owner != st["land"]), zones)
            else:
                place = ground
            own = land if land is not None else st["land"] if st else None
            if other and owner is not None:
                place = place & ~dilate((owner >= 0) & (owner != (-1 if own is None else own)), other)
            if "require_path" in attrs and st:          # a land path: no water, forest or cliff (#4137)
                place = place & path(~wet & ~forest & ~cliff, (int(st["x"]), int(st["y"])))
            dist = (np.hypot(x - st["x"], y - st["y"]) if circle else np.maximum(abs(x - st["x"]), abs(y - st["y"]))) if st else np.full((n, n), float(lo))
            # number_of_objects (± group_variance) is the size of each group (AoE2 DE scripting guide; loose grouping and
            # radius 3 are the defaults). Without number_of_groups: one group when a grouping attribute is set (the 7 gold
            # of Arabia), else each object is a group of 1. Single objects with min_distance_group_placement fill the ring (#4699).
            key = (dist if "find_closest" in attrs and st else
                   np.hypot(x - (n - 1) / 2, y - (n - 1) / 2) if "find_closest_to_map_center" in attrs else
                   np.minimum(np.minimum(x, y), np.minimum(n - 1 - x, n - 1 - y)) if "find_closest_to_map_edge" in attrs else None)
            sizes = [1] * count if groups is None and not grouped else [
                max(1, count + int(rng.integers(-vary, vary + 1))) for _ in range(groups or 1)]
            for size in sizes:
                free = ~used & place & ~dilate(placed, gap) & ~(dilate(mine, temp) if temp else mine)
                spots = np.argwhere((dist >= lo) & (dist <= hi) & free)
                if not len(spots) and "force_placement" in attrs:   # objects on the same tile (#4137)
                    free = place.copy()
                    spots = np.argwhere((dist >= lo) & (dist <= hi) & free)
                if not len(spots):
                    warn(f"create_object {args[0]}: no free tile")
                    break
                if key is None:
                    mid = tuple(int(v) for v in spots[rng.integers(len(spots))])
                else:                           # find_closest: the first spot of the smallest key (#4135)
                    mid = tuple(int(v) for v in spots[np.argmin(key[spots[:, 0], spots[:, 1]])])
                if tight:
                    cells = [mid]               # each next object on a free tile next to an object of the group
                    while len(cells) < size:
                        edge = sorted({t for c in cells for t in square(c, 1, n) if free[t] and t not in cells})
                        if not edge:
                            break
                        cells.append(edge[rng.integers(len(edge))])
                else:
                    near = np.argwhere(free & (np.hypot(x - mid[0], y - mid[1]) <= radius))
                    near = [tuple(int(v) for v in t) for t in near if tuple(t) != mid]
                    cells = [mid] + [near[i] for i in rng.permutation(len(near))[:size - 1]]
                for tx, ty in cells:
                    mine[tx, ty] = True
                    name = base
                    r = 3 if kind == "B" else 1                      # a building: its tile is the corner of its middle
                    used[max(0, tx - r):tx + r, max(0, ty - r):ty + r] = True
                    placed[max(0, tx - r):tx + r, max(0, ty - r):ty + r] = True
                    if name == "VILLAGER_MALE" and rng.integers(2):    # AoE2 DE: a male or a female villager
                        name = "VILLAGER_FEMALE"
                    out.append({"name": name, "player": player, "x": tx + 0.5 * (kind != "B"), "y": ty + 0.5 * (kind != "B")}
                               | delta)                                # more or less food, wood, gold or stone (#4429)
                    if second:
                        out.append({"name": second, "player": player, "x": tx + 0.5, "y": ty + 0.5})
                    if actor is not None:
                        area = areas.setdefault(actor, np.zeros((n, n), bool))
                        area[max(0, tx - reach):tx + reach + 1, max(0, ty - reach):ty + reach + 1] = True
        for a in sorted(set(attrs) - set(CREATE_OBJECT)):
            warn(f"create_object: {a} is not read yet")
    return out


def cliffs(cmds, terrain, starts, consts, rng, warn):
    """The cliff objects of <CLIFF_GENERATION> (#3850): lines of CLIFF_DEFAULT pieces CLIFF_STEP tiles apart. A line
    grows from a random free land tile and turns 45° at cliff_curliness percent of the steps. Free: no water, shallows
    or forest within min_terrain_distance, no player start area (base_size), no other line within min_distance_cliffs."""
    if not cmds:
        return []
    o, kind = dict(CLIFF_DEFAULTS), "CLIFF_DEFAULT"
    for cmd, args, _ in cmds:
        if cmd == "cliff_type" and args:
            if args[0] in CLIFF_TYPES:
                kind = CLIFF_TYPES[args[0]]
            else:
                warn(f"cliff_type {args[0]} has no cliff object: default cliffs")
        elif cmd in o and args:
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
    return [{"name": f"{kind}_{int(rng.integers(1, 10))}", "player": 0, "x": x + 0.5, "y": y + 0.5, "line": k}
            for k, line in enumerate(out) for x, y in line]


# Own generators (#993, decision B of #961): the land of a map type in the script language of generate(). The text is
# not a game script: it holds only facts about the map. Arabia: open grass and dirt land, small forests, a few single
# trees, small ponds away from the players, "a few scattered cliffs" (AoE2 wiki "Arabia", #3853).
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
<CLIFF_GENERATION>
min_number_of_cliffs 3
max_number_of_cliffs 5
min_length_of_cliff 4
max_length_of_cliff 6
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
# Black Forest: forest on most of the map, open player lands, an open middle and open paths (a connection) between them.
BLACK_FOREST = """
<LAND_GENERATION>
base_terrain FOREST
create_player_lands { terrain_type GRASS land_percent 25 base_size 13 clumping_factor 15 }
create_land { terrain_type GRASS land_position 50 50 base_size 5 number_of_tiles 250 clumping_factor 15 }
<TERRAIN_GENERATION>
create_terrain DIRT3 { base_terrain GRASS number_of_clumps 8 land_percent 2 }
create_terrain FOREST { base_terrain GRASS number_of_clumps 6 number_of_tiles 10 set_avoid_player_start_areas 15
  spacing_to_other_terrain_types 2 }
<CONNECTION_GENERATION>
create_connect_all_lands { replace_terrain FOREST GRASS terrain_size FOREST 1 0 }
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
# Highland: grass land with forests, a river across the map between the players (RIVERS) with shallow fords (FORDS), and
# "a cliffed, highly forested land" (AoE2 wiki "Highland", #3853). The wiki pages of the other maps name no cliffs.
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
<CLIFF_GENERATION>
min_number_of_cliffs 4
max_number_of_cliffs 8
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
GOLDS = {"gold_rush": (10, 6, 5)}  # the gold of the middle: radius in tiles, clumps of gold mines, mines in a clump
RIVERS = {"highland": 3}        # the river: half width in tiles
# The fords: a <CONNECTION_GENERATION> after river() (generate() runs before the river, so its connections see no water)
FORDS = {"highland": "create_connect_all_players_land { replace_terrain WATER SHALLOW terrain_size WATER 2 0 "
                     "terrain_cost WATER 7 terrain_cost FOREST 0 }"}
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
    player origins (for 2 players: between them), with a meander. fords() makes the fords."""
    w = spec
    n, terrain = d["size"], np.array(d["terrain"])
    x, y = np.mgrid[0:n, 0:n] + 0.5 - n / 2
    a = max(np.linspace(0, np.pi, 36, endpoint=False),                  # the normal of the river line
            key=lambda a: min(abs((st["x"] - n / 2) * np.cos(a) + (st["y"] - n / 2) * np.sin(a)) for st in d["lands"]))
    along = -x * np.sin(a) + y * np.cos(a)
    side = x * np.cos(a) + y * np.sin(a) - 3 * np.sin(along * 4 * np.pi / n + rng.uniform(0, 2 * np.pi))
    water = np.abs(side) <= w
    terrain[water] = TERRAINS["WATER"]
    d["terrain"] = terrain.tolist()
    d["elevation"] = lower_to_water(terrain, d["elevation"]).tolist()


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


def fords(d, text, seed):
    """The connections of text on the map d after river(), between the player lands: the fords across the river."""
    terrain, consts = np.array(d["terrain"]), TERRAINS | OBJECTS
    lands = [((st["x"], st["y"]), st["player"], -1 - k) for k, st in enumerate(d["lands"])]
    connections(terrain, lands, commands(expand(tokens("<CONNECTION_GENERATION>\n" + text), np.random.default_rng(seed),
                                                set(), consts, []))["CONNECTION_GENERATION"],
                consts, np.random.default_rng([seed, 995]), lambda m: print(f"rms: {m}", file=sys.stderr))
    terrain[dilate(terrain == TERRAINS["SHALLOW"], 3) & np.isin(terrain, list(FOREST_TREES))] = TERRAINS["GRASS"]
    d["terrain"] = terrain.tolist()
    d["elevation"] = lower_to_water(terrain, d["elevation"]).tolist()


def random_map(kind, seed, players=2, teams=None):
    """The map description of an own generator (GENERATORS) and seed: the land of generate() (with the WALLS,
    RIVERS, FORDS, ISLES and COASTS of the kind), a town center at each player origin (not for NOMADS) and the START objects around
    it, on free tiles (no forest, no water, not next to a wall), the FISH of the kind and the RELICS."""
    d = generate(GENERATORS[kind], seed, players, teams=teams)
    rng = np.random.default_rng([seed, 993])
    if kind in RIVERS:
        river(d, RIVERS[kind], rng)
    if kind in FORDS:
        fords(d, FORDS[kind], seed)
    if kind in ISLES:
        isles(d, ISLES[kind])
    if kind in COASTS:
        coast(d, COASTS[kind])
    objects = walls(d, WALLS[kind], rng) if kind in WALLS else []
    wet = dilate(np.isin(np.array(d["terrain"]), [TERRAINS["WATER"], TERRAINS["SHALLOW"]]), 1)
    objects += [o for o in d["objects"] if o["name"].startswith("CLIFF") and not wet[int(o["x"]), int(o["y"])]]  # not on the river
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
                if name == "VILLAGER_MALE" and rng.integers(2):    # AoE2 DE: a male or a female villager
                    name = "VILLAGER_FEMALE"
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
                if name == "VILLAGER_MALE" and rng.integers(2):    # AoE2 DE: a male or a female villager
                    name = "VILLAGER_FEMALE"
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
