"""
The civilization bonuses of the players in the game program (#1089, part of #1088). WORK holds the work-rate bonuses of
the AoE2 DE civilizations (the AoE2 wiki, "Civilization bonuses" of each civilization): Gather.work_time divides the
time of one unit of resource by the factor of the player's civilization. The keys are the gather kinds of Gather:
"wood", "food" (forage bushes), "farm", "gold", "stone", "hunt" (hunted animals) and "sheep" (herdable animals).
Bonuses that the game program cannot use yet: Japanese fishing ships, Malian oyster gatherers.
CHURCH_RATE is the Georgian bonus of the Fortified Church (#1930): build.rise and repair.rate multiply the work of the
villagers in the 21-tile square around it (church_rate).
BUILD, BUILD_WONDER and BUILD_OF hold the build speed bonuses (#1893, #2115): build.rise multiplies the work of the builders (build_rate).
WORK_RATE holds the train and research rate of the buildings (#1894, Persian town centers and docks): train.seconds
divides the time of an item by work_rate(). TRAIN_RATE holds the train rate of unit groups (#1927, Aztec military
units, Khitan skirmishers ...): train.seconds divides by train_rate(), also the time of their upgrades when the third
field is True. HP holds the hit points bonus of the buildings (#1895): build.values and
combat.setup (the buildings of the map) apply it before the technologies (Masonry).
REPAIR and REPAIR_COST hold the repair bonuses (#1730, AoE2 wiki "Repairing"): repair.tick multiplies the rate and the
cost of the repairs of a player by them (repair_rate, repair_cost). REPAIR_TEAM holds the team bonuses of the repair
rate (#1929, AoE2 wiki "Saxons": "Repairers work 25% faster"): they count for the civilization and its allies, and
multiply with REPAIR. The cost bonus of the Georgians is for buildings only (AoE2 wiki "Villager (Age of Empires II)":
"The bonus does not apply to repairing units"), so siege units and ships pay the full cost.

UNITS holds the bonuses of the land units of combat.STATS (#1090): hit points, attack, armor, range, reload and walk
speed, per age. train.stats applies them before the technologies; the walk speed goes through speed(). The value
"bonus" with a float multiplies the bonus damage that the unit deals (Gurjara mounted units, Bohemian spearmen,
#2248); the value "taken" is the factor of the bonus damage that the unit takes (Bengali elephants, Sicilian units:
taken(), the plugin applies it at each hit); the value "bonus:CLASS" adds attack against a class (#2249). Bonuses of
this kind that the game program cannot use yet: the elevation (Georgians, Tatars), the Lithuanian relics, the Aztec and Slav monks, and the ships.
REGEN holds the regeneration of the units (#2247): regen.tick gives them their hit points back.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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
    "foot archers": lambda n, s: foot_archer(s),
    "foot archers but skirmishers": lambda n, s: foot_archer(s) and not tagged(n, "skirmishers"),
    "foot archers but skirmishers, condottieri": lambda n, s: GROUPS["foot archers but skirmishers"](n, s),
    "gunpowder": lambda n, s: "gunpowder" in s.classes,
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

# The tables of each civilization: one line per civilization in data/civs.jsonl (#1914, `table.load`), from the AoE2 DE
# wiki. "unique": the unique unit of its castle (train.UNIQUE). "missing": the technologies and units that it does not
# have (the availability chart of each civilization, #1373): the menu does not show them (train.unlocked). The items
# that few civilizations have are in ONLY, not here.
# "units": the bonuses of the land units (#1090): [group of GROUPS, value, change in the Dark, Feudal, Castle and
# Imperial Age]; value is a field of combat.Stats, "speed" (the walk speed) or "bonus:CLASS" (the attack against a
# class of combat.Stats.classes, #2249); an int adds, a float multiplies ("fire 25 % faster" is the reload / 1.25). "costs": the cost bonuses (#1091): [what, resource or null (all), change in each
# age]; what is a group of GROUPS (units), "buildings", "buildings but farms", "technologies", "ages", "BUILDING
# technologies" (the technologies of the menu of that building, #1925) or a list of names; a float multiplies the cost
# (0.0: free), an int adds to it; AoE2 rounds half up (35 × 0.75 = 26). "twice": the technologies whose effect it gets
# twice (train.stats, #1561). "age_gifts": the resources that it gets at each new age (#1926). "hp_age": the
# factor of the hit points of all its buildings, walls and gates in each age (#2116). "smith_units": [group of
# GROUPS, blacksmith technologies, times in the Dark, Feudal, Castle and Imperial Age]: the units of the group get the
# effect of each technology that many times, also when the test of the effect does not cover them (smith, #2174).
# "cost_per": the cost bonuses for each complete own building (#2177): [group of GROUPS, the buildings, the share less
# for each, the most share less] (Saxons: foot soldiers cost 5 % less per town center or castle, at most 20 %).
ROWS = table.load("civs.jsonl")


def tuples(x):
    """The JSON lists of a table as tuples (a tuple of names, the changes of the four ages)."""
    return tuple(tuples(v) for v in x) if isinstance(x, list) else x


UNIQUE = {r["name"]: r["unique"] for r in ROWS if "unique" in r}
UNITS = {r["name"]: [tuples(b) for b in r["units"]] for r in ROWS if "units" in r}
COSTS = {r["name"]: [tuples(b) for b in r["costs"]] for r in ROWS if "costs" in r}
COST_PER = {r["name"]: [tuples(b) for b in r["cost_per"]] for r in ROWS if "cost_per" in r}
TWICE = {r["name"]: tuples(r["twice"]) for r in ROWS if "twice" in r}
SMITH_UNITS = {r["name"]: [tuples(b) for b in r["smith_units"]] for r in ROWS if "smith_units" in r}
# An item that few civilizations have names them in the key "civs" of its line in data/train.jsonl or data/build.jsonl
# (#2235): a new unique or regional unit then changes only its own line, not each line of data/civs.jsonl.
ONLY = {r["name"]: set(r["civs"]) for f in ("train.jsonl", "build.jsonl") for r in table.load(f) if "civs" in r}
MISSING = {t: tuple(sorted(r["name"] for r in ROWS if t in r["missing"] or r["name"] not in ONLY.get(t, (r["name"],))))
           for t in sorted({t for r in ROWS for t in r["missing"]} | set(ONLY))}
GENERIC = frozenset(t for r in ROWS for t in r["missing"])   # the AoE2 setting "All Techs" gives them to all (#2298)
ELEPHANTS = tuple(r["name"] for r in ROWS if r["name"] not in MISSING["BATTLE_ELEPHANT"])   # the battle elephant (#1556)
EAGLES = tuple(r["name"] for r in ROWS if r["name"] not in MISSING["EAGLE_SCOUT"])   # the eagle line (#1555)
LANCERS = tuple(r["name"] for r in ROWS if r["name"] not in MISSING["STEPPE_LANCER"])   # the steppe lancers (#1557)
FIRE_LANCERS = tuple(r["name"] for r in ROWS if r["name"] not in MISSING["FIRE_LANCER"])   # the fire lancer (#1953)
CHURCH_RATE, CHURCH_NEAR = 1.1, 10.5                              # +10 % work in the 21-tile square around a Fortified
                                                                  # Church (tiles from its center, #1930)
TECH_ROWS = table.load("train.jsonl")
SMITH = tuple(sorted(r["name"] for r in TECH_ROWS if r.get("building") == "BLACKSMITH"))   # the blacksmith (#1452)
ECONOMY = tuple(sorted(r["name"] for r in TECH_ROWS if r.get("economy")))   # the economic technologies but Coinage and
                                                                            # Banking (AoE2 wiki "Burgundians")
# The bonuses of each civilization, keys of its line in data/civs.jsonl (AoE2 DE, the AoE2 wiki):
# "work": the work-rate factor of each gather kind (a missing kind is 1).
# "drop": the factor of a load at the drop site: "food" for each food load (also of the fishing ships), "forage" for
# a load of a fruit bush only (#2111).
# "start": the start-resource bonus (#1269), {resource: change of START}. In AoE2 the bonus comes with the first town
# center (a Nomad start gets it later); here it is in the start stock. The extra villagers of the Chinese (+3) and
# Mayans (+1) are units of the map, not of the stock. Lithuanians: +100 food for each town center, here only for the
# first one.
# "town_center": the resources that the first town center gives (Tupi +25 of each, #2293): in the start stock when the
# player has a town center at the start, else when its first town center is complete (build.rise).
# "bushes": [count, food] of the forage bushes next to the town center at the start (Gurjaras: 2 of 175, #2293).
# "shared": the shared unique units of its team bonus: an ally of the civilization has them too ("Team bonus", #1619).
# "not_shared": the shared items that it does not get from an ally (Turks: no Elite Skirmisher).
# "build", "build_wonder": the build speed of the builders (Spanish: 20 % for wonders). "build_of": the build speed of
# some buildings, {building: factor} (Sicilian fortifications and town centers, #2115). "built_food": the food that
# a complete building gives, {building: food} (Saxons, Wu, #2114). "repair": the repair rate.
# "repair_cost": the team bonus of the repair cost of buildings (Georgians). "repair_team": the team bonus of the
# repair rate (Saxons). "work_rate": the train and research rate of a building in each age (Persians). "train_rate":
# [group of GROUPS, factor, also the upgrades] (#1927). "hp": the hit points factor of a building (Persians).
# "research_time": [technologies (a rule of has), factor of the research time] (#2172: Achaemenid stable technologies
# 50 % faster, Jurchen siege and fortification technologies 100 % faster, the Gothic Loom at once).
WORK = {r["name"]: r["work"] for r in ROWS if "work" in r}
LAST = {r["name"]: r["last"] for r in ROWS if "last" in r}   # resources last longer: a gathered unit takes 1 / factor (#2112)
START = {r["name"]: r["start"] for r in ROWS if "start" in r}
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
REPAIR = {r["name"]: r["repair"] for r in ROWS if "repair" in r}
REPAIR_COST = {r["name"]: r["repair_cost"] for r in ROWS if "repair_cost" in r}
REPAIR_TEAM = {r["name"]: r["repair_team"] for r in ROWS if "repair_team" in r}
WORK_RATE = {r["name"]: {b: tuple(v) for b, v in r["work_rate"].items()} for r in ROWS if "work_rate" in r}
TRAIN_RATE = {r["name"]: [tuples(b) for b in r["train_rate"]] for r in ROWS if "train_rate" in r}
HP = {r["name"]: r["hp"] for r in ROWS if "hp" in r}
ARROWS = {r["name"]: tuples(r["arrows"]) for r in ROWS if "arrows" in r}   # factor of the base arrows in each age (#2178)
GARRISON = {r["name"]: r["garrison"] for r in ROWS if "garrison" in r}   # units inside a building (garrison.size, #2117)
HP_AGE = {r["name"]: r["hp_age"] for r in ROWS if "hp_age" in r}   # the factor of all buildings in each age (Byzantines)
# Technologies with another effect for the civilization (#2173, train.stats, train.speed): "also" gives the effect to
# one more group of GROUPS too (Bohemians: Fervor and Sanctity for the villagers), "more" multiplies the change of the
# effect (Varangians: Bloodlines and Caravan +50 %).
ALSO = {r["name"]: r["also"] for r in ROWS if "also" in r}
MORE = {r["name"]: r["more"] for r in ROWS if "more" in r}
FARM_UPGRADES = {r["name"]: r["farm_upgrades"] for r in ROWS if "farm_upgrades" in r}   # the factor of the food of the
#                                                                   farm upgrades (Sicilians: +125 %, train.research, #2230)
RESEARCH_TIME = {r["name"]: [tuples(b) for b in r["research_time"]] for r in ROWS if "research_time" in r}
# "extra": the second resource of a gather kind ("forage": a fruit bush), {kind: [resource, amount for each unit]}: Poles
# and Puru stone miners, Portuguese foragers, Shu lumberjacks (#2113). Gather.second adds it at each gathered unit.
EXTRA = {r["name"]: {k: tuple(v) for k, v in r["extra"].items()} for r in ROWS if "extra" in r}
# "drop_extra": a second resource at the drop site, {kind: [resource, factor of the load]}: "hunt" (hunters and
# shepherds), "fish" (fishermen), "ship" (fishing ships). Varangians: +10 % gold, +5 % for the ships (#2308).
DROP_EXTRA = {r["name"]: {k: tuple(v) for k, v in r["drop_extra"].items()} for r in ROWS if "drop_extra" in r}
# "per_minute": a resource for each AoE2 minute of work of a gather kind, {kind: [resource, amount]}: Thracian
# hunters and shepherds 3 gold while they gather from animals (#2308).
PER_MINUTE = {r["name"]: {k: tuple(v) for k, v in r["per_minute"].items()} for r in ROWS if "per_minute" in r}
# "carry": the extra load of a villager, [[gather kind or null (all), extra]]: Aztec villagers +3, Goth hunters +15
# (#2270). Gather.limit adds it.
CARRY = {r["name"]: [tuple(b) for b in r["carry"]] for r in ROWS if "carry" in r}
# The age-up bonuses (#1926, AoE2 DE wiki): train.research applies AGE_GIFTS and AGE_VILLAGERS at the end of each age,
# train.seconds divides the time of an age by AGE_RATE, and train.missing needs no buildings for AGE_NO_BUILDINGS (the
# game program has no other building needs). The Muisca gold discount of the ages is in COSTS (civs.jsonl).
AGE_GIFTS = {r["name"]: r["age_gifts"] for r in ROWS if "age_gifts" in r}   # resources at each new age
AGE_NO_BUILDINGS = ("KHMER",)                                      # no buildings are required to advance
AGE_RATE = {"MALAY": 1.66}                                         # advancing in age is 66 % faster
AGE_VILLAGERS = {"BENGALIS": 2}                                    # each own town center spawns 2 villagers
# "tech_gifts": the resources for each technology but an age (Spanish), "economy_villagers": the free villagers for
# each economic technology (Wei, #2175).
TECH_GIFTS = {r["name"]: r["tech_gifts"] for r in ROWS if "tech_gifts" in r}
# "regen": the regeneration of units (#2247): [group of GROUPS or a list of unit names, hit points per AoE2 minute in
# the Dark, Feudal, Castle and Imperial Age] (Polish villagers, Georgian mounted units, Wu infantry, Thracian elite
# skirmishers). regen.tick gives them back.
REGEN = {r["name"]: [tuples(b) for b in r["regen"]] for r in ROWS if "regen" in r}
ECONOMY_VILLAGERS = {r["name"]: r["economy_villagers"] for r in ROWS if "economy_villagers" in r}
# Resources for kills and deaths (game/spoils.py, #2271): "fallen" the part of the cost of a fallen own unit (Tupi),
# "kill_gold" the gold for each military unit that a mounted unit kills (Mapuche), "loot" the part of the cost of a
# destroyed enemy building (Danes).
FALLEN = {r["name"]: r["fallen"] for r in ROWS if "fallen" in r}
KILL_GOLD = {r["name"]: r["kill_gold"] for r in ROWS if "kill_gold" in r}
LOOT = {r["name"]: r["loot"] for r in ROWS if "loot" in r}
# The relic and monk bonuses (game/monk.py, #2314): "relic_attack" [units, attack per relic in an own monastery, most]
# (Lithuanian knights and Leitis), "faith" the factor of the speed of the monks that regain faith (Muisca: 100 % faster).
RELIC_ATTACK = {r["name"]: tuples(r["relic_attack"]) for r in ROWS if "relic_attack" in r}
FAITH = {r["name"]: r["faith"] for r in ROWS if "faith" in r}


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
    """The (value, change) of the civilization bonuses of UNITS for unit name (combat.Stats s) in the age of g."""
    import build                                                   # build imports gather, gather imports this module
    age = build.ages(g)
    return [(v, c[age]) for k, v, c in UNITS.get(civ(g), []) if GROUPS[k](name, s)]


def smith(g, name, s):
    """{technology: n} of SMITH_UNITS for unit name (combat.Stats s) in the age of g: the Inca villagers get the
    infantry technologies from the Castle Age, the Macedonian cavalry the infantry armor, the Roman infantry twice the
    infantry armor (AoE2 DE wiki, #2174)."""
    import build                                                   # build imports gather, gather imports this module
    age = build.ages(g)
    return {t: c[age] for k, techs, c in SMITH_UNITS.get(civ(g), []) if c[age] and GROUPS[k](name, s) for t in techs}


def regen(g, name, s):
    """The hit points per AoE2 minute that unit name (combat.Stats s) of the player of g regenerates in its age (REGEN),
    else 0. Two rules of one civilization add up."""
    import build                                                   # build imports gather, gather imports this module
    age = build.ages(g)
    return sum(c[age] for k, c in REGEN.get(civ(g), []) if (name in k if isinstance(k, tuple) else GROUPS[k](name, s)))


def units(g, name, s):
    """The combat.Stats s of unit name with the bonuses of the civilization of the player of g (UNITS, RELIC_ATTACK), the
    walk speed aside (speed)."""
    names, each, most = RELIC_ATTACK.get(civ(g), ((), 0, 0))
    if name in names:                                              # the relics in own monasteries (monk.relic_tick)
        s = s._replace(attack=s.attack + min(each * sum(r["home"] is not None for r in getattr(g, "relics", ())), most))
    for v, c in changes(g, name, s):
        if v.startswith("bonus:") and c:                           # the attack against a class (#2249)
            s = s._replace(bonus={**s.bonus, v[6:]: s.bonus.get(v[6:], 0) + c})
        elif v == "bonus" and isinstance(c, float):                # a factor of each bonus (#2248)
            s = s._replace(bonus={k: math.floor(n * c + 0.5) for k, n in s.bonus.items()})
        elif v not in ("speed", "taken") and not v.startswith("bonus:"):
            old = getattr(s, v)
            s = s._replace(**{v: round(old * c, 3 if v == "reload" else None) if isinstance(c, float) else old + c})
    return s


def taken(g, name):
    """The factor of the bonus damage that unit name of the player of g takes (UNITS, value "taken"), else 1 (#2248)."""
    import combat                                                  # combat imports gather, gather imports this module
    return math.prod(c for v, c in changes(g, name, combat.stats(name)) if v == "taken")


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
    another player (an ally: repair.cost, #1361)."""
    import build                                                   # build imports gather, gather imports this module
    out, age = dict(base), build.ages(g)
    for what, r, c in COSTS.get(civ(g, player), []):
        if has(what, name):
            for k in [r] if r else list(out):
                if k in out:
                    out[k] = max(0, int(out[k] * c[age] + 0.5) if isinstance(c[age], float) else out[k] + c[age])
    if player is None or player == g.player:                       # the own complete buildings (#2177)
        import train                                               # train imports this module
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
    run.py --all-techs, #2298) gives each civilization the GENERIC items; the unique items stay with their civilization."""
    import gather                                                  # gather imports this module
    c = civ(g)
    if c not in MISSING.get(name, ()) or g.data.get("all_techs") and name in GENERIC:
        return False
    players = g.data.get("players", {})
    return name not in SHARED or c in NOT_SHARED.get(name, ()) or not any(
        civ(g, p) == SHARED[name] and gather.allied(players, g.player, int(p)) for p in players if p.isdigit())


def civ(g, player=None):
    """The civilization of the player of g, or of another player (aoe2mc.json "players"), for example "CELTS", else None."""
    return g.data.get("players", {}).get(str(g.player if player is None else player), {}).get("civ")


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


def build_rate(g, name):
    """The factor of the build speed of the villagers of the player of g for a site of building name (BUILD,
    BUILD_WONDER, BUILD_OF), else 1."""
    c = civ(g)
    return BUILD_OF.get(c, {}).get(name) or (BUILD_WONDER.get(c, BUILD.get(c, 1)) if name == "WONDER" else BUILD.get(c, 1))


def built_food(g, name):
    """The food that a complete building name of the player of g gives (BUILT_FOOD), else 0."""
    return BUILT_FOOD.get(civ(g), {}).get(name, 0)


def church_rate(g, pos):
    """The factor of the work of a villager of the player of g at block position pos (x, z): CHURCH_RATE for a Georgian
    in the 21-tile square around a complete own Fortified Church (AoE2 wiki "Georgians"; also to build and repair,
    AoE2 wiki "Repairing"), else 1."""
    if civ(g) != "GEORGIANS":
        return 1
    import train                                                   # train imports this module
    near = CHURCH_NEAR * g.map.T
    return CHURCH_RATE if any(max(abs(pos[0] - (x0 + x1) / 2), abs(pos[1] - (z0 + z1) / 2)) <= near
                              for (x0, x1, z0, z1), n in train.homes(g).items() if n == "FORTIFIED_CHURCH") else 1


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


def hp(civ, building, s, age=0):
    """The combat.Stats s of building (a name) with the hit points bonus of civilization civ (HP, #1895) and of its
    age (HP_AGE: 0 = Dark .. 3 = Imperial, #2116). AoE2 rounds the hit points to a whole number."""
    f = HP.get(civ, {}).get(building, 1) * HP_AGE.get(civ, (1,) * 4)[min(age, 3)]
    return s if f == 1 else s._replace(hp=round(s.hp * f))


def work_rate(g, building):
    """The factor of the train and research rate of building (a name) of the player of g in its age (WORK_RATE), else 1."""
    import build                                                   # build imports gather, gather imports this module
    return WORK_RATE.get(civ(g), {}).get(building, (1,) * 4)[min(build.ages(g), 3)]


def train_rate(g, name):
    """The factor of the train rate of unit name of the player of g (TRAIN_RATE), also of an upgrade technology
    (train.UPGRADES) to a unit of the group when the bonus has its upgrades, else 1."""
    import combat, train                                           # train imports this module
    unit = name in combat.STATS
    news = [name] if unit else [new for _, new in train.lines(name)] if name in train.UPGRADES else []
    return math.prod(f for group, f, upgrades in TRAIN_RATE.get(civ(g), ()) if (unit or upgrades)
                     and any(GROUPS[group](n, combat.stats(n)) for n in news))


def start(g, base):
    """The start resources `base` with the start bonus of the civilization of the player of g (START)."""
    bonus = START.get(civ(g), {})
    return {r: max(0, v + bonus.get(r, 0)) for r, v in base.items()}


def drop(g, kind):
    """The drop-off factor of the civilization of the player of g for kind ("food", "forage": DROP), else 1."""
    return DROP.get(civ(g), {}).get(kind, 1)


def work(g, kind):
    """The work-rate factor of the civilization of the player of g for gather kind (WORK), else 1."""
    return WORK.get(civ(g), {}).get(kind, 1)


def last(g, kind):
    """The factor of how long a resource of gather kind lasts for the civilization of the player of g (LAST), else 1:
    as in AoE2, the villager gets the same amount per trip, but the source loses less (Mayans, Puru, Tatar herds)."""
    return LAST.get(civ(g), {}).get(kind, 1)


def extra(g, kind):
    """The second resource of gather kind for the civilization of the player of g: (resource, amount for each unit)
    (EXTRA), else None."""
    return EXTRA.get(civ(g), {}).get(kind)


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
