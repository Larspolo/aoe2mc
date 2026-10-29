"""
The civilization bonuses of the players in the game program (#1089, part of #1088). Each civilization has one line in
data/civs.jsonl (#1914), and each key of those lines has one line in data/civ_keys.jsonl (#2281): what it does, its
issue. BY_KEY[key][civ] (or value(key, civ, default)) holds the value of each key: a new key is one line in each data
file and the code that applies it (repair.py, build.py, train.py ...), no new line here. The tables in capitals below
are the older names of some keys.
Bonuses that the game program cannot use yet: the gold of the Malian oyster gatherers, the Slav monks and the ships.
The key "church_rate" is the Georgian bonus of the Fortified Church (#1930, #2377): build.rise, repair.rate and
Gather.work_time multiply the work of the villagers in the 21-tile square around it (church_rate).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import monk  # noqa: E402
import table  # noqa: E402

# The units of each group (unit name, combat.Stats). "Mounted" in AoE2: cavalry, camels and elephants. A unit is in a
# group by the rule here, or by the key "groups" of its line in data/units.jsonl (a group of names: "archer line").
RULES = {
    "archers": lambda n, s: "archer" in s.classes,
    "barracks": lambda n, s: "infantry" in s.classes and "unique" not in s.classes,
    "camels": lambda n, s: "camel" in s.classes,
    "cavalry": lambda n, s: "cavalry" in s.classes,
    "cavalry archers": lambda n, s: "archer" in s.classes and "cavalry" in s.classes,
    "champi scout line, archery range units": lambda n, s: "CHAMPI_" in n   # the wiki: all archers but the conquistador
        or "archer" in s.classes and not tagged(n, "conquistador type"),     # type (#2116)
    "elephants": lambda n, s: "elephant" in s.classes,
    "fire galley line, fire lancers": lambda n, s: tagged(n, "fire galley line") or tagged(n, "fire lancers"),
    "foot archers": lambda n, s: foot_archer(s),
    "foot archers but skirmishers": lambda n, s: foot_archer(s) and not tagged(n, "skirmishers"),
    "foot archers but skirmishers, condottieri": lambda n, s: GROUPS["foot archers but skirmishers"](n, s),
    "gunpowder": lambda n, s: "gunpowder" in s.classes,
    "human units": lambda n, s: not tagged(n, "self-destructing") and not tagged(n, "scout line")   # the Muisca
        and "siege" not in s.classes and not GROUPS["ships"](n, s),   # Settlement heal (AoE2 DE wiki, #2432)
    "infantry": lambda n, s: "infantry" in s.classes,
    "infantry, mounted": lambda n, s: "infantry" in s.classes or mounted(s),
    "infantry, slingers, skirmishers": lambda n, s: "infantry" in s.classes or tagged(n, "slingers") or tagged(n, "skirmishers"),
    "land military units but siege": lambda n, s: not civilian(n) and "siege" not in s.classes
        and not GROUPS["ships"](n, s),
    "land siege, Lou Chuans": lambda n, s: "siege" in s.classes,   # the ships of the group: "groups" (data/units.jsonl)
    "military": lambda n, s: not n.startswith("VILLAGER"),
    "military units": lambda n, s: not civilian(n),
    "mounted": lambda n, s: mounted(s),
    "mounted, fire lancers": lambda n, s: mounted(s) or tagged(n, "fire lancers"),
    "scout line, steppe lancers": lambda n, s: tagged(n, "scout line"),
    "ships": lambda n, s: "ship" in s.classes or n.endswith(("_COG", "_SHIP")),   # also the trade cog and transport ship
    "siege": lambda n, s: "siege" in s.classes,
    "skirmishers, elephant archers": lambda n, s: tagged(n, "skirmishers"),
    "skirmishers, genitours, spearman and scout lines": lambda n, s: "spearman" in s.classes
        or tagged(n, "skirmishers") or tagged(n, "scout line"),
    "spearman line": lambda n, s: "spearman" in s.classes,
    "spearmen, skirmishers": lambda n, s: "spearman" in s.classes or tagged(n, "skirmishers"),
    "units": lambda n, s: True,
    "villagers": lambda n, s: n.startswith("VILLAGER"),
    "warships": lambda n, s: "ship" in s.classes and not tagged(n, "fishing ships"),   # not the transport and trade ships
}
TAGS = {r["name"]: tuple(r["groups"]) for r in table.load("units.jsonl") if "groups" in r}
GROUPS = {g: (lambda f, g: lambda n, s: g in TAGS.get(n, ()) or f(n, s))(RULES.get(g, lambda n, s: False), g)
          for g in sorted(set(RULES) | {g for t in TAGS.values() for g in t})}

# One line per civilization (#1914), from the AoE2 DE wiki; the keys: data/civ_keys.jsonl (#2281).
ROWS = table.load("civs.jsonl")


def tuples(x):
    """The JSON lists of a table as tuples (a tuple of names, the changes of the four ages)."""
    return tuple(tuples(v) for v in x) if isinstance(x, list) else x


def frozen(x):
    """A JSON value with tuples for its lists, also inside a dict (the form of BY_KEY)."""
    if isinstance(x, dict):
        return {k: frozen(v) for k, v in x.items()}
    return tuple(frozen(v) for v in x) if isinstance(x, (list, tuple)) else x


KEYS = {r["name"]: f"{r['text']} (#{r['issue']})" for r in table.load("civ_keys.jsonl")}   # what each key does (#2281)
BY_KEY = {k: {r["name"]: frozen(r[k]) for r in ROWS if k in r} for k in sorted(KEYS)}


def value(key, civ, default=None):
    """The value of key of data/civs.jsonl for civ (BY_KEY), else default. A key needs its line in civ_keys.jsonl."""
    assert key in KEYS, key
    return BY_KEY[key].get(civ, default)


UNIQUE = {r["name"]: r["unique"] for r in ROWS if "unique" in r}
UNITS = {r["name"]: [tuples(b) for b in r["units"]] for r in ROWS if "units" in r}
COSTS = {r["name"]: [tuples(b) for b in r["costs"]] for r in ROWS if "costs" in r}
COST_PER = {r["name"]: [tuples(b) for b in r["cost_per"]] for r in ROWS if "cost_per" in r}
TWICE = {r["name"]: tuples(r["twice"]) for r in ROWS if "twice" in r}
SMITH_UNITS = {r["name"]: [tuples(b) for b in r["smith_units"]] for r in ROWS if "smith_units" in r}
# An item that few civilizations have names them in the key "civs" of its line in data/train.jsonl or data/build.jsonl
# (#2235), an item that most have names the others in the key "not_civs" (#3200): a new item then changes only its own
# line, not the lines of data/civs.jsonl. Two tickets that changed those lines were dirty on GitHub after each merge.
ONLY = {r["name"]: set(r["civs"]) for f in ("train.jsonl", "build.jsonl") for r in table.load(f) if "civs" in r}
NOT = {r["name"]: set(r["not_civs"]) for f in ("train.jsonl", "build.jsonl") for r in table.load(f) if "not_civs" in r}
MISSING = {t: tuple(sorted(r["name"] for r in ROWS if r["name"] in NOT.get(t, ()) or r["name"] not in ONLY.get(t, (r["name"],))))
           for t in sorted(set(NOT) | set(ONLY))}
GENERIC = frozenset(NOT)   # the AoE2 setting "All Techs" gives them to all (#2298)
# The AoE2 lobby setting "Full Tech Tree" (#2354) gives each civilization the GENERIC and the ONLY items; the key
# "full_tech_tree" of a line of data/train.jsonl or data/build.jsonl makes an exception: "own" (only its civilizations
# have it: a unique unit, a scout, a regional unit after AoE2 update 141935), "none" (no civilization: a unique
# building, the Xolotl Warrior, a team bonus unit). AoE2 wiki "Full Tech Tree".
FULL = {r["name"]: r["full_tech_tree"] for f in ("train.jsonl", "build.jsonl") for r in table.load(f)
        if "full_tech_tree" in r}
ELEPHANTS = tuple(r["name"] for r in ROWS if r["name"] not in MISSING.get("BATTLE_ELEPHANT", ()))   # the battle elephant (#1556)
EAGLES = tuple(r["name"] for r in ROWS if r["name"] not in MISSING.get("EAGLE_SCOUT", ()))   # the eagle line (#1555)
LANCERS = tuple(r["name"] for r in ROWS if r["name"] not in MISSING.get("STEPPE_LANCER", ()))   # the steppe lancers (#1557)
FIRE_LANCERS = tuple(r["name"] for r in ROWS if r["name"] not in MISSING.get("FIRE_LANCER", ()))   # the fire lancer (#1953)
# "aura" (#2378): the own complete buildings that make the gatherers of some resources work faster near them and take
# these resources: {"buildings", "resources", "rate", "range": tiles from the footprint} (Thracian forts and towers).
# gather.Map.drop_site adds them to the drop sites, Gather.aura_rate gives the rate.
AURA = {r["name"]: r["aura"] for r in ROWS if "aura" in r}
TECH_ROWS = table.load("train.jsonl")
SMITH = tuple(sorted(r["name"] for r in TECH_ROWS if r.get("building") == "BLACKSMITH"))   # the blacksmith (#1452)
ECONOMY = tuple(sorted(r["name"] for r in TECH_ROWS if r.get("economy")))   # the economic technologies but Coinage and
                                                                            # Banking (AoE2 wiki "Burgundians")
WORK = {r["name"]: r["work"] for r in ROWS if "work" in r}
LAST = {r["name"]: r["last"] for r in ROWS if "last" in r}   # resources last longer: a gathered unit takes 1 / factor (#2112)
START = {r["name"]: r["start"] for r in ROWS if "start" in r}
DECAY = {r["name"]: r["decay"] for r in ROWS if "decay" in r}   # the factor of the decay of carcasses (Jurchens: 0, #2310)
PREDATOR_HIT = {r["name"]: r["predator_hit"] for r in ROWS if "predator_hit" in r}   # villager attack bonus (Magyars)
TOWN_CENTER = {r["name"]: r["town_center"] for r in ROWS if "town_center" in r}
BUSHES = {r["name"]: r["bushes"] for r in ROWS if "bushes" in r}
DROP = {r["name"]: r["drop"] for r in ROWS if "drop" in r}
SHARED = dict(sorted((n, r["name"]) for r in ROWS for n in r.get("shared", ())))
NOT_SHARED = {n: tuple(sorted(r["name"] for r in ROWS if n in r.get("not_shared", ())))
              for n in sorted({n for r in ROWS for n in r.get("not_shared", ())})}
BUILD = {r["name"]: r["build"] for r in ROWS if "build" in r}
BUILD_WONDER = {r["name"]: r["build_wonder"] for r in ROWS if "build_wonder" in r}
BUILD_OF = {r["name"]: r["build_of"] for r in ROWS if "build_of" in r}
BUILT_FOOD = {r["name"]: r["built_food"] for r in ROWS if "built_food" in r}
BUILT_UNITS = {r["name"]: {b: tuples(v) for b, v in r["built_units"].items()} for r in ROWS if "built_units" in r}
REPAIR = {r["name"]: r["repair"] for r in ROWS if "repair" in r}
REPAIR_COST = {r["name"]: r["repair_cost"] for r in ROWS if "repair_cost" in r}
REPAIR_TEAM = {r["name"]: r["repair_team"] for r in ROWS if "repair_team" in r}
WORK_RATE = {r["name"]: {b: tuple(v) for b, v in r["work_rate"].items()} for r in ROWS if "work_rate" in r}
TRAIN_RATE = {r["name"]: [tuples(b) for b in r["train_rate"]] for r in ROWS if "train_rate" in r}
HP = {r["name"]: r["hp"] for r in ROWS if "hp" in r}
ARROWS = {r["name"]: tuples(r["arrows"]) for r in ROWS if "arrows" in r}   # factor of the base arrows in each age (#2178)
GARRISON = {r["name"]: r["garrison"] for r in ROWS if "garrison" in r}   # units inside a building (garrison.size, #2117)
TRAINS = {r["name"]: r["trains"] for r in ROWS if "trains" in r}         # more units of a building (Mapuche, #2432)
HEAL_AURA = {r["name"]: r["heal_aura"] for r in ROWS if "heal_aura" in r}   # buildings that heal near them (Muisca)
HEAL_RANGE = {r["name"]: r["heal_range"] for r in ROWS if "heal_range" in r}   # factor of the monk heal range (#2269)
TECH_HP = {r["name"]: [tuples(b) for b in r["tech_hp"]] for r in ROWS if "tech_hp" in r}
EARLIER = {r["name"]: set(r["earlier"]) for r in ROWS if "earlier" in r}   # one age earlier (build.locked, #2268)
HP_AGE = {r["name"]: r["hp_age"] for r in ROWS if "hp_age" in r}   # the factor of all buildings in each age (Byzantines)
ALSO = {r["name"]: r["also"] for r in ROWS if "also" in r}
MORE = {r["name"]: r["more"] for r in ROWS if "more" in r}
FARM_UPGRADES = {r["name"]: r["farm_upgrades"] for r in ROWS if "farm_upgrades" in r}   # the factor of the food of the
#                                                                   farm upgrades (Sicilians: +125 %, train.research, #2230)
RESEARCH_TIME = {r["name"]: [tuples(b) for b in r["research_time"]] for r in ROWS if "research_time" in r}
EXTRA = {r["name"]: {k: tuple(v) for k, v in r["extra"].items()} for r in ROWS if "extra" in r}
DROP_EXTRA = {r["name"]: {k: tuple(v) for k, v in r["drop_extra"].items()} for r in ROWS if "drop_extra" in r}
PER_MINUTE = {r["name"]: {k: tuple(v) for k, v in r["per_minute"].items()} for r in ROWS if "per_minute" in r}
CARRY = {r["name"]: [tuple(b) for b in r["carry"]] for r in ROWS if "carry" in r}
HOUSING = {r["name"]: r["housing"] for r in ROWS if "housing" in r}   # population of a building in place of train.HOUSING
SIGHT = {r["name"]: r["sight"] for r in ROWS if "sight" in r}       # extra tiles of line of sight of a building (#2118)
POP_CAP = {r["name"]: tuple(r["pop_cap"]) for r in ROWS if "pop_cap" in r}   # (age, extra population limit from it)
# The age-up bonuses (#1926, AoE2 DE wiki): train.research applies AGE_GIFTS and AGE_VILLAGERS at the end of each age,
# train.seconds divides the time of an age by AGE_RATE, and train.missing needs no buildings for AGE_NO_BUILDINGS (the
# game program has no other building needs). The Muisca gold discount of the ages is in COSTS (civs.jsonl).
AGE_GIFTS = {r["name"]: r["age_gifts"] for r in ROWS if "age_gifts" in r}   # resources at each new age
AGE_NO_BUILDINGS = ("KHMER",)                                      # no buildings are required to advance
AGE_RATE = {"MALAY": 1.66}                                         # advancing in age is 66 % faster
AGE_VILLAGERS = {"BENGALIS": 2}                                    # each own town center spawns 2 villagers
TECH_GIFTS = {r["name"]: r["tech_gifts"] for r in ROWS if "tech_gifts" in r}
REGEN = {r["name"]: [tuples(b) for b in r["regen"]] for r in ROWS if "regen" in r}
FALLEN = {r["name"]: r["fallen"] for r in ROWS if "fallen" in r}
KILL_GOLD = {r["name"]: r["kill_gold"] for r in ROWS if "kill_gold" in r}
LOOT = {r["name"]: r["loot"] for r in ROWS if "loot" in r}
REVEAL = {r["name"]: [tuple(b) for b in r["reveal"]] for r in ROWS if "reveal" in r}
ELEVATION = {r["name"]: r["elevation"] for r in ROWS if "elevation" in r}
ELEVATION_BASE = {"up": 1.25, "low": 0.75, "high": 1.0}


def elevation(civ):
    """The elevation factors (up, low, high) of civilization civ (ELEVATION_BASE and its key "elevation")."""
    e = {**ELEVATION_BASE, **ELEVATION.get(civ, {})}
    return e["up"], e["low"], e["high"]


RELIC_ATTACK = {r["name"]: tuples(r["relic_attack"]) for r in ROWS if "relic_attack" in r}
FAITH = {r["name"]: r["faith"] for r in ROWS if "faith" in r}
HERD_FOOD = {r["name"]: {b: tuple(v) for b, v in r["herd_food"].items()} for r in ROWS if "herd_food" in r}


def tagged(n, group):
    """True when the line of unit n in data/units.jsonl names group in its key "groups"."""
    return group in TAGS.get(n, ())


def civilian(n):
    """True for the civilian units of gather.CIVILIANS (villagers, monks, trade units ...)."""
    import gather                                                  # gather imports this module
    return n.startswith(gather.CIVILIANS)


def mounted(s):
    return bool({"cavalry", "camel", "elephant"} & set(s.classes))


def foot_archer(s):
    """An archer on foot; the hand cannoneers and janissaries have the gunpowder bonuses."""
    return "archer" in s.classes and not mounted(s) and "gunpowder" not in s.classes


def changes(g, name, s):
    """The (value, change) of the civilization bonuses of UNITS for unit name (combat.Stats s) in the age of g. The
    group of a rule is a name of GROUPS or a list of unit names."""
    import build                                                   # build imports gather, gather imports this module
    age = build.ages(g)
    return [(v, c[age]) for k, v, c in UNITS.get(civ(g), [])
            if (name in k if isinstance(k, tuple) else GROUPS[k](name, s))]   # a list of names (Antiquity, #3827)


def smith(g, name, s):
    """{technology: n} of SMITH_UNITS for unit name (combat.Stats s) in the age of g: the Inca villagers get the
    infantry technologies from the Castle Age, the Macedonian cavalry the infantry armor, the Roman infantry twice the
    infantry armor (AoE2 DE wiki, #2174)."""
    import build                                                   # build imports gather, gather imports this module
    age = build.ages(g)
    return {t: c[age] for k, techs, c in SMITH_UNITS.get(civ(g), []) if c[age] and GROUPS[k](name, s) for t in techs}


def regen(g, name, s, foe=math.inf):
    """The hit points per AoE2 minute that unit name (combat.Stats s) of the player of g regenerates in its age (REGEN),
    else 0. Two rules of one civilization add up. foe: the tiles from the unit to the nearest enemy unit; a rule with a
    radius counts only when foe is more than it. The technologies of the player add their rate (the key "regen")."""
    import build                                                   # build imports gather, gather imports this module
    import train                                                   # train imports civs
    age = build.ages(g)
    tech = sum(hp for t, (k, hp) in train.BY_KEY["regen"].items() if t in g.techs and GROUPS[k](name, s))
    return tech + sum(c[age] for k, c, *near in REGEN.get(civ(g), []) if foe > (near or [-1])[0]
                      and (name in k if isinstance(k, tuple) else GROUPS[k](name, s)))


def units(g, name, s):
    """The combat.Stats s of unit name with the bonuses of the civilization of the player of g (UNITS, RELIC_ATTACK), the
    walk speed aside (speed)."""
    names, each, most = RELIC_ATTACK.get(civ(g), ((), 0, 0))
    if name in names:                                              # the relics in own monasteries (monk.relic_tick)
        s = s._replace(attack=s.attack + min(each * sum(r["home"] is not None and monk.own(g, r)
                                                        for r in getattr(g, "relics", ())), most))
    for v, c in changes(g, name, s):
        if v.startswith("bonus:") and isinstance(c, float):        # a factor of the attack against a class (#2272)
            s = s._replace(bonus={**s.bonus, v[6:]: math.floor(s.bonus.get(v[6:], 0) * c + 0.5)})
        elif v.startswith("bonus:") and c:                         # the attack against a class (#2249)
            s = s._replace(bonus={**s.bonus, v[6:]: s.bonus.get(v[6:], 0) + c})
        elif v == "bonus" and isinstance(c, float):                # a factor of each bonus (#2248)
            s = s._replace(bonus={k: math.floor(n * c + 0.5) for k, n in s.bonus.items()})
        elif v not in ("friendly", "speed", "taken") and not v.startswith("bonus:"):
            old = getattr(s, v)
            s = s._replace(**{v: round(old * c, 3 if v == "reload" else None) if isinstance(c, float) else old + c})
    return s


def taken(g, name):
    """The factor of the bonus damage that unit name of the player of g takes (UNITS, value "taken"), else 1 (#2248)."""
    import combat                                                  # combat imports gather, gather imports this module
    return math.prod(c for v, c in changes(g, name, combat.stats(name)) if v == "taken")


def friendly(g, name):
    """The factor of the friendly fire (the blast of an own or allied unit) that unit name of the player of g takes
    (UNITS, value "friendly"), else 1 (Jurchen military units, #2418)."""
    import combat                                                  # combat imports gather, gather imports this module
    return math.prod(c for v, c in changes(g, name, combat.stats(name)) if v == "friendly")


def has(what, name):
    """True when the rule `what` of COSTS covers unit, technology or building name."""
    import build, combat, train                                    # they import gather, gather imports this module
    if isinstance(what, tuple):
        return name in what
    if what.startswith("buildings"):
        return name in build.COSTS and not (what == "buildings but farms" and name == "FARM")
    if what in ("ages", "technologies"):
        return name in (build.AGE_TECHS if what == "ages" else train.TECHS)
    if what.endswith(" technologies"):                             # the menu of the building gives the list (#1925)
        return name in train.TECHS and name in train.TRAINS.get(what.split()[0], ())
    s = combat.STATS.get("VILLAGER" if name.startswith("VILLAGER") else name)
    return s is not None and name not in train.TECHS and GROUPS[what](name, s)


def cost(g, name, base, player=None):
    """The cost `base` ({resource: amount}) of name with the cost bonuses of the civilization of the player of g, or of
    another player (an ally: repair.cost, #1361). A cost of a scenario trigger (g.trigger_costs, #2776) wins."""
    import build                                                   # build imports gather, gather imports this module
    import train                                                   # train imports this module
    out, age = dict(base), build.ages(g)
    own = player is None or player == g.player
    techs = [(tuples(w), r, [c] * 4) for t, rules in train.BY_KEY["costs"].items() if own and train.researched(g, t)
             for w, r, c in rules]                                 # the key "costs" of a technology (#4225)
    if own and name in vars(g).get("trigger_costs", {}):            # "Change Object Cost" of a scenario (#2776)
        return dict(g.trigger_costs[name])
    for what, r, c in [*COSTS.get(civ(g, player), []), *policy(g)[1].get("costs", ()) * own, *techs]:   # (#2485)
        if has(what, name):
            for k in [r] if r else list(out):
                if k in out:
                    out[k] = max(0, int(out[k] * c[age] + 0.5) if isinstance(c[age], float) else out[k] + c[age])
    if own:                                                        # the own complete buildings (#2177)
        for what, names, each, most in COST_PER.get(civ(g, player), []):
            if has(what, name) and (n := sum(b in names for b in train.owned(g))):
                out = {k: int(v * (1 - min(each * n, most)) + 0.5) for k, v in out.items()}
    return {k: v for k, v in out.items() if v}


def speed(g, name):
    """The factor of the walk speed of unit name for the civilization of the player of g (UNITS), else 1."""
    import combat                                                  # combat imports gather, gather imports this module
    return math.prod(c for v, c in changes(g, name, combat.stats(name)) if v == "speed")


def missing(g, name):
    """True when the civilization of the player of g does not have unit or technology name (MISSING), also not as the
    shared unit of an allied player (SHARED, gather.allied). The AoE2 setting "All Techs" (aoe2mc.json "all_techs",
    run.py --all-techs, #2298) gives each civilization the GENERIC items; the unique items stay with their civilization.
    The AoE2 setting "Full Tech Tree" (aoe2mc.json "full_tech_tree", run.py --full-tech-tree) also gives the ONLY items,
    with the exceptions of FULL (#2354)."""
    import gather                                                  # gather imports this module
    if name in vars(g).get("trigger_menus", {}):                   # "Enable/Disable Object" of a scenario (#2775)
        return not g.trigger_menus[name]
    c = real(g)
    if g.data.get("full_tech_tree") and (f := FULL.get(name)) != "own" and (f or name in GENERIC or name in ONLY):
        return f == "none"
    if c not in MISSING.get(name, ()) or g.data.get("all_techs") and name in GENERIC:
        return False
    players = g.data.get("players", {})
    return name not in SHARED or c in NOT_SHARED.get(name, ()) or not any(
        civ(g, p) == SHARED[name] and gather.allied(players, g.player, int(p)) for p in players if p.isdigit())


def civ(g, player=None):
    """The civilization of the player of g, or of another player (aoe2mc.json "players"), for example "CELTS", else None.
    The AoE2 setting "Full Tech Tree" (#2354) removes all civilization and team bonuses: then None, because each bonus
    table takes its civilization from here. The tech tree and the unique units take it from real()."""
    return None if g.data.get("full_tech_tree") else real(g, player)


def handicap(data, player):
    """The factor of the AoE2 setting "Handicap" of player (aoe2mc.json "players" "handicap": 100 to 200 percent,
    run.py --handicap, #2474), else 1. It is no civilization bonus: "Full Tech Tree" keeps it."""
    return data.get("players", {}).get(str(player), {}).get("handicap", 100) / 100


def real(g, player=None):
    """The civilization of the player of g, or of another player, also with the setting "Full Tech Tree" (civ)."""
    return g.data.get("players", {}).get(str(g.player if player is None else player), {}).get("civ")


def earlier(g, name):
    """1 when the civilization of the player of g has the building, unit or technology name one age earlier (EARLIER:
    the Armenian spearman in the Dark Age, the Cuman siege workshop in the Feudal Age, #2268), else 0."""
    return int(hasattr(g, "data") and name in EARLIER.get(civ(g), ()))


def age_rate(g, name):
    """The factor of the research rate of technology name for the civilization of the player of g: AGE_RATE for an
    age, else 1."""
    import build                                                   # build imports gather, gather imports this module
    return AGE_RATE.get(civ(g), 1) if name in build.AGE_TECHS else 1


def arrows(g, building, player=None):
    """The factor of the base arrows (garrison.BASE) of building name of the player of g (or of player) in the present
    age of g: ARROWS (the Saxon towers and castles: twice from the Castle Age, #2178), else 1."""
    import build                                                   # build imports gather, gather imports this module
    return next((f[build.ages(g)] for names, f in ARROWS.get(civ(g, player), ()) if building in names), 1)


def research_time(g, name):
    """The factor of the research time of technology name for the civilization of the player of g (RESEARCH_TIME),
    else 1."""
    return math.prod(f for what, f in RESEARCH_TIME.get(civ(g), ()) if has(what, name))


TURBO = next(r for r in table.load("setup.jsonl") if "turbo" in r)    # the AoE2 setting "Turbo Mode" (#2359)


def turbo(g, name=None):
    """The factor of the AoE2 setting "Turbo Mode" (aoe2mc.json "turbo", run.py --turbo) for the work of a building on
    item name, the build of a site of building name, or (no name) the gather and carry of villagers and fishing ships:
    TURBO, but 1 for its "slow" items and without the setting."""
    return TURBO["turbo"] if getattr(g, "data", {}).get("turbo") and name not in TURBO["slow"] else 1


def build_rate(g, name):
    """The factor of the build speed of the villagers of the player of g for a site of building name (BUILD,
    BUILD_WONDER, BUILD_OF), else 1."""
    c = civ(g)
    return (BUILD_OF.get(c, {}).get(name) or (BUILD_WONDER.get(c, BUILD.get(c, 1)) if name == "WONDER" else BUILD.get(c, 1))) \
        * handicap(g.data, g.player)                                # the villager work rate (#2474)


def built_food(g, name):
    """The food that a complete building name of the player of g gives (BUILT_FOOD), else 0."""
    return BUILT_FOOD.get(civ(g), {}).get(name, 0)


def built_units(g, name):
    """(unit, number) of the herdables that a complete building name of the player of g gives in its age
    (BUILT_UNITS), else None."""
    import build                                                   # build imports gather, gather imports this module
    unit, n = BUILT_UNITS.get(civ(g), {}).get(name, (None, (0,) * 4))
    return (unit, n[build.ages(g)]) if n[build.ages(g)] else None


def church_rate(g, pos):
    """The factor of the work of a villager of the player of g at block position pos (x, z): the factor of the key
    "church_rate" in the square around a complete own building of it (a Georgian Fortified Church, AoE2 wiki
    "Georgians": to gather, build and repair, AoE2 wiki "Repairing"), else 1. Two churches give it once."""
    rate = value("church_rate", civ(g))
    if not rate:
        return 1
    import train                                                   # train imports this module
    building, square, f = rate
    near = square / 2 * g.map.T                                    # blocks from the center of the building
    return f if any(max(abs(pos[0] - (x0 + x1) / 2), abs(pos[1] - (z0 + z1) / 2)) <= near
                    for (x0, x1, z0, z1), n in train.homes(g).items() if n == building) else 1


def repair_rate(g):
    """The factor of the repair rate of the villagers of the player of g: its own bonus (REPAIR) times the largest team
    bonus (REPAIR_TEAM) of the civilization and its allies (gather.allied)."""
    import gather                                                  # gather imports this module
    players = g.data.get("players", {})
    team = max([REPAIR_TEAM.get(civ(g, p), 1) for p in players if p.isdigit() and gather.allied(players, g.player, int(p))]
               + [REPAIR_TEAM.get(civ(g), 1)])
    return REPAIR.get(civ(g), 1) * team


def repair_cost(g):
    """The factor of the repair cost of the buildings of the player of g: a team bonus of REPAIR_COST counts for the
    civilization and its allies (gather.allied); the bonuses do not add up, the smallest factor counts. Not for units."""
    import gather                                                  # gather imports this module
    players = g.data.get("players", {})
    return min([REPAIR_COST.get(civ(g, p), 1) for p in players if p.isdigit() and gather.allied(players, g.player, int(p))]
               + [REPAIR_COST.get(civ(g), 1)])


def hp(civ, building, s, age=0, factor=1):
    """The combat.Stats s of building (a name) with the hit points bonus of civilization civ (HP, #1895) and of its
    age (HP_AGE: 0 = Dark .. 3 = Imperial, #2116), and the factor of the owner's handicap (#2474). AoE2 rounds the hit
    points to a whole number."""
    f = HP.get(civ, {}).get(building, 1) * HP_AGE.get(civ, (1,) * 4)[min(age, 3)] * factor
    return s if f == 1 else s._replace(hp=round(s.hp * f))


def work_rate(g, building):
    """The factor of the train and research rate of building (a name) of the player of g in its age (WORK_RATE), else 1,
    times the handicap of the player at a military building (build.MILITARY, #2474)."""
    import build                                                   # build imports gather, gather imports this module
    return WORK_RATE.get(civ(g), {}).get(building, (1,) * 4)[min(build.ages(g), 3)] \
        * (handicap(g.data, g.player) if building in build.MILITARY else 1)


def ship_work(g):
    """The factor of the work rate of a fishing ship of the player of g in its age (the key "ship_work"), else 1."""
    import build                                                   # build imports gather, gather imports this module
    return value("ship_work", civ(g), (1,) * 4)[min(build.ages(g), 3)]


def train_time(g, building, name):
    """The factor of the train time of unit name at building (a name) of the player of g in its age: a unit of a line of
    TRAINS (Mapuche Settlements, #2432), else 1."""
    import build                                                   # build imports gather, gather imports this module
    t = TRAINS.get(civ(g), {}).get(building)
    return t.get("time", (1,) * 4)[min(build.ages(g), 3)] if t and any(name in line for line in t["lines"]) else 1


def train_rate(g, name):
    """The factor of the train rate of unit name of the player of g (TRAIN_RATE), also of an upgrade technology
    (train.UPGRADES) to a unit of the group when the bonus has its upgrades, else 1."""
    import combat, train                                           # train imports this module
    unit = name in combat.STATS
    news = [name] if unit else [new for _, new in train.lines(name)] if name in train.UPGRADES else []
    return math.prod(f for group, f, upgrades in TRAIN_RATE.get(civ(g), ()) if (unit or upgrades)
                     and any(GROUPS[group](n, combat.stats(n)) for n in news))


def start(g, base):
    """The start resources `base` with the start bonus of the civilization of the player of g (START), times the
    handicap of the player (#2474)."""
    bonus, f = START.get(civ(g), {}), handicap(g.data, g.player)
    return {r: max(0, round((v + bonus.get(r, 0)) * f)) for r, v in base.items()}


def drop(g, kind):
    """The drop-off factor of the civilization of the player of g for kind ("food", "forage": DROP), else 1."""
    return DROP.get(civ(g), {}).get(kind, 1)


def work(g, kind):
    """The work-rate factor of the civilization of the player of g for gather kind (WORK), else 1, times the handicap
    of the player (#2474)."""
    return WORK.get(civ(g), {}).get(kind, 1) * handicap(g.data, g.player)


def decay(g):
    """The factor of the decay of the carcasses that the player of g kills (DECAY), else 1 (#2310)."""
    return DECAY.get(civ(g), 1)


def predator_hit(g):
    """The attack bonus of the villagers of the player of g against predators (PREDATOR_HIT), else 0 (#2310): the
    Magyars get +30 (AoE2 wiki, "Magyars"), so a villager kills each predator in one strike."""
    return PREDATOR_HIT.get(civ(g), 0)


def last(g, kind):
    """The factor of how long a resource of gather kind lasts for the civilization of the player of g (LAST), else 1:
    as in AoE2, the villager gets the same amount per trip, but the source loses less (Mayans, Puru, Tatar herds)."""
    return LAST.get(civ(g), {}).get(kind, 1)


def extra(g, kind):
    """The second resource of gather kind for the civilization of the player of g: (resource, amount for each unit)
    (EXTRA, or the one of the active policy), else None."""
    return policy(g)[1].get("extra", {}).get(kind) or EXTRA.get(civ(g), {}).get(kind)


def policies(g):
    """The key "policies" of the civilization of the player of g (Athenians, #2485), else {}."""
    return value("policies", civ(g), {}) if hasattr(g, "data") else {}


def policy(g):
    """(name, changes) of the active policy of the player of g: the start policy until the first switch
    (train.research), else (None, {}). The changes use the keys of civs.jsonl ("costs", "extra")."""
    p = policies(g)
    name = vars(g).get("policy") or p.get("start")
    return name, p.get("effects", {}).get(name, {})


def drop_extra(g, kind):
    """The second resource of a load of gather kind at the drop site for the civilization of the player of g:
    (resource, factor of the load) (DROP_EXTRA), else None."""
    return DROP_EXTRA.get(civ(g), {}).get(kind)


def per_minute(g, kind):
    """The resource that the work of gather kind earns for the civilization of the player of g: (resource, amount for
    each AoE2 minute) (PER_MINUTE), else None."""
    return PER_MINUTE.get(civ(g), {}).get(kind)


def carry(g, kind):
    """The extra load of a villager of the player of g for gather kind (CARRY), else 0."""
    return sum(n for k, n in CARRY.get(civ(g), ()) if k in (None, kind))
