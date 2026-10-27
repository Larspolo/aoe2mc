"""
The civilization bonuses of the players in the game program (#1089, part of #1088). WORK holds the work-rate bonuses of
the AoE2 DE civilizations (the AoE2 wiki, "Civilization bonuses" of each civilization): Gather.work_time divides the
time of one unit of resource by the factor of the player's civilization. The keys are the gather kinds of Gather:
"wood", "food" (forage bushes), "farm", "gold", "stone", "hunt" (hunted animals) and "sheep" (herdable animals).
Bonuses that the game program cannot use yet: Japanese fishing ships, Malian oyster gatherers, the Georgian fortified
church (+10 % near it).
BUILD and BUILD_WONDER hold the build speed bonuses (#1893): build.rise multiplies the work of the builders (build_rate).
WORK_RATE holds the train and research rate of the buildings (#1894, Persian town centers and docks): train.seconds
divides the time of an item by work_rate(). HP holds the hit points bonus of the buildings (#1895): build.values and
combat.setup (the buildings of the map) apply it before the technologies (Masonry).
REPAIR and REPAIR_COST hold the repair bonuses (#1730, AoE2 wiki "Repairing"): repair.tick multiplies the rate and the
cost of the repairs of a player by them (repair_rate, repair_cost).

UNITS holds the bonuses of the land units of combat.STATS (#1090): hit points, attack, armor, range, reload and walk
speed, per age. train.stats applies them before the technologies; the walk speed goes through speed(). Bonuses of
this kind that the game program cannot use yet: the bonus damage (Bengali elephants and Sicilian units take less,
Gurjara mounted units and Bohemian spearmen deal more, Bengali cavalry and Japanese mounted archers against some
classes, Goth infantry against buildings), the Georgian and Polish regeneration, the elevation (Georgians, Tatars),
the Lithuanian relics, the Roman infantry armor technologies, the Incan villagers with the infantry technologies,
the Aztec and Slav monks, and the ships.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import table  # noqa: E402

# Work-rate factor of each civilization and gather kind (AoE2 DE, the AoE2 wiki). A missing kind is 1.
ROMAN = 1.05                                                       # Romans: villagers gather 5 % faster
WORK = {"BRITONS": {"sheep": 1.25},                                # shepherds work 25 % faster
        "CELTS": {"wood": 1.15},                                   # lumberjacks work 15 % faster
        "FRANKS": {"food": 1.15},                                  # foragers work 15 % faster
        "KHMER": {"farm": 0.95},                                   # farmers work 5 % slower (no drop-off)
        "KOREANS": {"stone": 1.2},                                 # stone miners work 20 % faster
        "MALIANS": {"gold": 1.1},                                  # gold miners work 10 % faster
        "MONGOLS": {"hunt": 1.4},                                  # hunters work 40 % faster
        "ROMANS": dict.fromkeys(("farm", "food", "gold", "hunt", "sheep", "stone", "wood"), ROMAN),
        "SLAVS": {"farm": 1.15},                                   # farmers work 15 % faster
        "TURKS": {"gold": 1.25}}                                   # gold miners work 25 % faster

# The units of each group (unit name, combat.Stats). "Mounted" in AoE2: cavalry, camels and elephants.
GROUPS = {
    "archer line": lambda n, s: n in ("ARCHER", "CROSSBOWMAN", "ARBALESTER"),
    "archers": lambda n, s: "archer" in s.classes,
    "barracks": lambda n, s: "infantry" in s.classes and ("unique" not in s.classes or n == "CONDOTTIERO"),
    "battle elephants": lambda n, s: n in ("BATTLE_ELEPHANT", "ELITE_BATTLE_ELEPHANT"),
    "camel riders": lambda n, s: n in ("CAMEL_RIDER", "HEAVY_CAMEL_RIDER", "IMPERIAL_CAMEL_RIDER"),
    "camels": lambda n, s: "camel" in s.classes,
    "cavalry": lambda n, s: "cavalry" in s.classes,
    "cavalry archers": lambda n, s: "archer" in s.classes and "cavalry" in s.classes,
    "foot archers": lambda n, s: foot_archer(s),
    "foot archers but skirmishers": lambda n, s: foot_archer(s) and "SKIRMISHER" not in n,
    "foot archers but skirmishers, condottieri": lambda n, s: n == "CONDOTTIERO" or GROUPS["foot archers but skirmishers"](n, s),
    "gunpowder": lambda n, s: "gunpowder" in s.classes,
    "infantry": lambda n, s: "infantry" in s.classes,
    "infantry, mounted": lambda n, s: "infantry" in s.classes or mounted(s),
    "military": lambda n, s: not n.startswith("VILLAGER"),
    "mounted": lambda n, s: mounted(s),
    "scorpions": lambda n, s: n.endswith("SCORPION"),
    "scout line": lambda n, s: n in ("SCOUT_CAVALRY", "LIGHT_CAVALRY", "HUSSAR"),
    "scout line, steppe lancers": lambda n, s: n in ("SCOUT_CAVALRY", "LIGHT_CAVALRY", "HUSSAR", "STEPPE_LANCER",
                                                     "ELITE_STEPPE_LANCER"),
    "siege": lambda n, s: "siege" in s.classes,
    "skirmishers, elephant archers": lambda n, s: "SKIRMISHER" in n or n.endswith("ELEPHANT_ARCHER"),
    "spearmen, skirmishers": lambda n, s: "spearman" in s.classes or "SKIRMISHER" in n,
    "trade units": lambda n, s: n in ("TRADE_CART", "TRADE_COG"),
    "units": lambda n, s: True,
    "villagers": lambda n, s: n.startswith("VILLAGER"),
}

# The tables of each civilization: one line per civilization in data/civs.jsonl (#1914, `table.load`), from the AoE2 DE
# wiki. "unique": the unique unit of its castle (train.UNIQUE). "missing": the technologies and units that it does not
# have (the availability chart of each civilization, #1373): the menu does not show them (train.unlocked).
# "units": the bonuses of the land units (#1090): [group of GROUPS, value, change in the Dark, Feudal, Castle and
# Imperial Age]; value is a field of combat.Stats or "speed" (the walk speed); an int adds, a float multiplies ("fire
# 25 % faster" is the reload / 1.25). "costs": the cost bonuses (#1091): [what, resource or null (all), change in each
# age]; what is a group of GROUPS (units), "buildings", "buildings but farms", "technologies", "ages" or a list of
# names; a float multiplies the cost (0.0: free), an int adds to it; AoE2 rounds half up (35 × 0.75 = 26). "twice":
# the technologies whose effect it gets twice (train.stats, #1561).
ROWS = table.load("civs.jsonl")


def tuples(x):
    """The JSON lists of a table as tuples (a tuple of names, the changes of the four ages)."""
    return tuple(tuples(v) for v in x) if isinstance(x, list) else x


UNIQUE = {r["name"]: r["unique"] for r in ROWS if "unique" in r}
UNITS = {r["name"]: [tuples(b) for b in r["units"]] for r in ROWS if "units" in r}
COSTS = {r["name"]: [tuples(b) for b in r["costs"]] for r in ROWS if "costs" in r}
TWICE = {r["name"]: tuples(r["twice"]) for r in ROWS if "twice" in r}
MISSING = {t: tuple(sorted(r["name"] for r in ROWS if t in r["missing"]))
           for t in sorted({t for r in ROWS for t in r["missing"]})}
ELEPHANTS = tuple(r["name"] for r in ROWS if "BATTLE_ELEPHANT" not in r["missing"])   # the battle elephant (#1556)
EAGLES = tuple(r["name"] for r in ROWS if "EAGLE_SCOUT" not in r["missing"])   # the eagle line (#1555)
LANCERS = tuple(r["name"] for r in ROWS if "STEPPE_LANCER" not in r["missing"])   # the steppe lancers (#1557)
SMITH = ("BLAST_FURNACE", "BODKIN_ARROW", "BRACER", "CHAIN_BARDING_ARMOR", "CHAIN_MAIL_ARMOR", "FLETCHING", "FORGING",
         "IRON_CASTING", "LEATHER_ARCHER_ARMOR", "PADDED_ARCHER_ARMOR", "PLATE_BARDING_ARMOR", "PLATE_MAIL_ARMOR",
         "RING_ARCHER_ARMOR", "SCALE_BARDING_ARMOR", "SCALE_MAIL_ARMOR")   # the blacksmith (#1452)
ECONOMY = ("BOW_SAW", "CARAVAN", "CROP_ROTATION", "DOUBLE_BIT_AXE", "FISHING_LINES", "GILLNETS", "GOLD_MINING",
           "GOLD_SHAFT_MINING", "GUILDS", "HAND_CART", "HEAVY_PLOW", "HORSE_COLLAR", "STONE_MINING", "STONE_SHAFT_MINING",
           "TWO_MAN_SAW", "WHEELBARROW")   # the economic technologies but Coinage and Banking (AoE2 wiki "Burgundians")


# The start-resource bonuses (#1269): civilization -> {resource: change of START} (AoE2 DE, the AoE2 wiki). In AoE2 the
# bonus comes with the first town center (a Nomad start gets it later); here it is in the start stock. The extra
# villagers of the Chinese (+3) and Mayans (+1) are units of the map, not of the stock. Lithuanians: +100 food for each
# town center, here only for the first one.
START = {"AZTECS": {"gold": 50},
         "CHINESE": {"food": -200, "wood": -50},
         "HUNS": {"wood": -100},                                   # no houses
         "LITHUANIANS": {"food": 100},
         "MAYANS": {"food": -50},
         "PERSIANS": {"food": 50, "wood": 50},
         "SICILIANS": {"stone": 100}}
SHARED = {"CONDOTTIERO": "ITALIANS",                              # the shared unique units of the team bonuses: an ally
          "ELITE_GENITOUR": "BERBERS",                             # of the civilization has them too (AoE2 DE wiki,
          "ELITE_GENITOUR_UPGRADE": "BERBERS",                     # "Team bonus", #1619)
          "GENITOUR": "BERBERS",
          "IMPERIAL_SKIRMISHER_UPGRADE": "VIETNAMESE"}
NOT_SHARED = {"IMPERIAL_SKIRMISHER_UPGRADE": ("TURKS",)}           # no Elite Skirmisher: not with a Vietnamese ally
BUILD = {"ROMANS": ROMAN,                                          # Romans: builders work 5 % faster
         "SPANISH": 1.3}                                           # Spanish: builders work 30 % faster
BUILD_WONDER = {"SPANISH": 1.2}                                   # Spanish: 20 % for wonders (AoE2 DE wiki)
REPAIR = {"ROMANS": ROMAN}                                        # Romans: repairers work 5 % faster
REPAIR_COST = {"GEORGIANS": 0.75}                                 # Georgians (team bonus): repairs cost -25 %
PERSIAN = (1.05, 1.1, 1.15, 1.2)                                   # Persians: 5/10/15/20 % faster in the Dark ... Imperial Age
WORK_RATE = {"PERSIANS": {"DOCK": PERSIAN, "TOWN_CENTER": PERSIAN}}   # the train and research rate of a building in each age
HP = {"PERSIANS": {"DOCK": 2, "TOWN_CENTER": 2}}                   # Persians: town centers and docks have double hit points


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


def units(g, name, s):
    """The combat.Stats s of unit name with the bonuses of the civilization of the player of g (UNITS), the walk speed
    aside (speed)."""
    for v, c in changes(g, name, s):
        if v != "speed":
            old = getattr(s, v)
            s = s._replace(**{v: round(old * c, 3 if v == "reload" else None) if isinstance(c, float) else old + c})
    return s


def has(what, name):
    """True when the rule `what` of COSTS covers unit, technology or building name."""
    import build, combat, train                                    # they import gather, gather imports this module
    if isinstance(what, tuple):
        return name in what
    if what.startswith("buildings"):
        return name in build.COSTS and not (what == "buildings but farms" and name == "FARM")
    if what in ("ages", "technologies"):
        return name in (build.AGE_TECHS if what == "ages" else train.TECHS)
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
    return {k: v for k, v in out.items() if v}


def speed(g, name):
    """The factor of the walk speed of unit name for the civilization of the player of g (UNITS), else 1."""
    import combat                                                  # combat imports gather, gather imports this module
    return math.prod(c for v, c in changes(g, name, combat.stats(name)) if v == "speed")


def missing(g, name):
    """True when the civilization of the player of g does not have unit or technology name (MISSING), also not as the
    shared unit of an allied player (SHARED, gather.allied)."""
    import gather                                                  # gather imports this module
    c = civ(g)
    if c not in MISSING.get(name, ()):
        return False
    players = g.data.get("players", {})
    return name not in SHARED or c in NOT_SHARED.get(name, ()) or not any(
        civ(g, p) == SHARED[name] and gather.allied(players, g.player, int(p)) for p in players if p.isdigit())


def civ(g, player=None):
    """The civilization of the player of g, or of another player (aoe2mc.json "players"), for example "CELTS", else None."""
    return g.data.get("players", {}).get(str(g.player if player is None else player), {}).get("civ")


def build_rate(g, name):
    """The factor of the build speed of the villagers of the player of g for a site of building name (BUILD,
    BUILD_WONDER), else 1."""
    c = civ(g)
    return BUILD_WONDER.get(c, BUILD.get(c, 1)) if name == "WONDER" else BUILD.get(c, 1)


def repair_rate(g):
    """The factor of the repair rate of the villagers of the player of g (REPAIR), else 1."""
    return REPAIR.get(civ(g), 1)


def repair_cost(g):
    """The factor of the repair cost of the player of g: a team bonus of REPAIR_COST counts for the civilization and
    its allies (gather.allied); the bonuses do not add up, the smallest factor counts."""
    import gather                                                  # gather imports this module
    players = g.data.get("players", {})
    return min([REPAIR_COST.get(civ(g, p), 1) for p in players if p.isdigit() and gather.allied(players, g.player, int(p))]
               + [REPAIR_COST.get(civ(g), 1)])


def hp(civ, building, s):
    """The combat.Stats s of building (a name) with the hit points bonus of civilization civ (HP, #1895)."""
    return s._replace(hp=s.hp * HP.get(civ, {}).get(building, 1))


def work_rate(g, building):
    """The factor of the train and research rate of building (a name) of the player of g in its age (WORK_RATE), else 1."""
    import build                                                   # build imports gather, gather imports this module
    return WORK_RATE.get(civ(g), {}).get(building, (1,) * 4)[min(build.ages(g), 3)]


def start(g, base):
    """The start resources `base` with the start bonus of the civilization of the player of g (START)."""
    bonus = START.get(civ(g), {})
    return {r: max(0, v + bonus.get(r, 0)) for r, v in base.items()}


def work(g, kind):
    """The work-rate factor of the civilization of the player of g for gather kind (WORK), else 1."""
    return WORK.get(civ(g), {}).get(kind, 1)
