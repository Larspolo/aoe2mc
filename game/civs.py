"""
The civilization bonuses of the players in the game program (#1089, part of #1088). WORK holds the work-rate bonuses of
the AoE2 DE civilizations (the AoE2 wiki, "Civilization bonuses" of each civilization): Gather.work_time divides the
time of one unit of resource by the factor of the player's civilization. The keys are the gather kinds of Gather:
"wood", "food" (forage bushes), "farm", "gold", "stone", "hunt" (hunted animals) and "sheep" (herdable animals).
Bonuses that the game program cannot use yet: Japanese fishing ships, Malian oyster gatherers, Spanish builders, the
Roman builders and repairers, the Georgian fortified church (+10 % near it), the Persian town centers and docks.

UNITS holds the bonuses of the land units of combat.STATS (#1090): hit points, attack, armor, range, reload and walk
speed, per age. train.stats applies them before the technologies; the walk speed goes through speed(). Bonuses of
this kind that the game program cannot use yet: the bonus damage (Bengali elephants and Sicilian units take less,
Gurjara mounted units and Bohemian spearmen deal more, Bengali cavalry and Japanese mounted archers against some
classes, Goth infantry against buildings), the Georgian and Polish regeneration, the elevation (Georgians, Tatars),
the Lithuanian relics, the Roman infantry armor technologies, the Incan villagers with the infantry technologies,
the Aztec and Slav monks, and the ships.
"""
import math

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
    "barracks": lambda n, s: "infantry" in s.classes and ("unique" not in s.classes or n == "CONDOTTIERO"),
    "battle elephants": lambda n, s: n in ("BATTLE_ELEPHANT", "ELITE_BATTLE_ELEPHANT"),
    "camel riders": lambda n, s: n in ("CAMEL_RIDER", "HEAVY_CAMEL_RIDER", "IMPERIAL_CAMEL_RIDER"),
    "camels": lambda n, s: "camel" in s.classes,
    "cavalry archers": lambda n, s: "archer" in s.classes and "cavalry" in s.classes,
    "foot archers": lambda n, s: foot_archer(s),
    "foot archers but skirmishers": lambda n, s: foot_archer(s) and "SKIRMISHER" not in n,
    "foot archers but skirmishers, condottieri": lambda n, s: n == "CONDOTTIERO" or GROUPS["foot archers but skirmishers"](n, s),
    "gunpowder": lambda n, s: "gunpowder" in s.classes,
    "infantry": lambda n, s: "infantry" in s.classes,
    "infantry, mounted": lambda n, s: "infantry" in s.classes or mounted(s),
    "mounted": lambda n, s: mounted(s),
    "scout line": lambda n, s: n in ("SCOUT_CAVALRY", "LIGHT_CAVALRY", "HUSSAR"),
    "scout line, steppe lancers": lambda n, s: n in ("SCOUT_CAVALRY", "LIGHT_CAVALRY", "HUSSAR", "STEPPE_LANCER",
                                                     "ELITE_STEPPE_LANCER"),
    "siege": lambda n, s: "siege" in s.classes,
    "skirmishers, elephant archers": lambda n, s: "SKIRMISHER" in n or n.endswith("ELEPHANT_ARCHER"),
    "spearmen, skirmishers": lambda n, s: "spearman" in s.classes or "SKIRMISHER" in n,
    "villagers": lambda n, s: n.startswith("VILLAGER"),
}
# Civilization -> [(group, value, change in the Dark, Feudal, Castle and Imperial Age)] (AoE2 DE, the AoE2 wiki).
# value: a field of combat.Stats or "speed" (the walk speed); an int adds, a float multiplies. "Fire 25 % faster" is
# the reload / 1.25.
UNITS = {"BERBERS": [("villagers", "speed", (1.05, 1.1, 1.1, 1.1))],
         "BRITONS": [("foot archers but skirmishers", "range", (0, 0, 1, 2))],
         "BURGUNDIANS": [("gunpowder", "attack", (1.25,) * 4)],
         "BURMESE": [("battle elephants", "melee", (1,) * 4), ("battle elephants", "pierce", (1,) * 4),
                     ("infantry", "attack", (0, 1, 2, 3))],
         "CELTS": [("infantry", "speed", (1.05, 1.1, 1.15, 1.2)), ("siege", "reload", (1 / 1.25,) * 4)],
         "CUMANS": [("mounted", "speed", (1.0, 1.05, 1.1, 1.15))],
         "DRAVIDIANS": [("skirmishers, elephant archers", "reload", (1 / 1.25,) * 4)],
         "ETHIOPIANS": [("archer line", "reload", (1 / 1.18,) * 4)],
         "FRANKS": [("mounted", "hp", (1.0, 1.2, 1.2, 1.2))],
         "HINDUSTANIS": [("camel riders", "reload", (1 / 1.2,) * 4), ("gunpowder", "melee", (1,) * 4),
                         ("gunpowder", "pierce", (1,) * 4)],
         "ITALIANS": [("foot archers but skirmishers, condottieri", "melee", (1,) * 4),
                      ("foot archers but skirmishers, condottieri", "pierce", (1,) * 4)],
         "JAPANESE": [("infantry", "reload", (1.0,) + (1 / 1.33,) * 3)],
         "KHMER": [("battle elephants", "speed", (1.1,) * 4)],
         "LITHUANIANS": [("spearmen, skirmishers", "speed", (1.1,) * 4)],
         "MALIANS": [("barracks", "pierce", (0, 1, 2, 3))],
         "MONGOLS": [("cavalry archers", "reload", (1 / 1.25,) * 4),
                     ("scout line, steppe lancers", "hp", (1.0, 1.0, 1.2, 1.3))],
         "SARACENS": [("camels", "hp", (1.25,) * 4)],
         "SPANISH": [("gunpowder", "reload", (1 / 1.18,) * 4)],
         "TEUTONS": [("infantry, mounted", "melee", (0, 0, 1, 2))],
         "TURKS": [("gunpowder", "hp", (1.25,) * 4), ("scout line", "pierce", (1,) * 4)],
         "VIETNAMESE": [("foot archers", "hp", (1.2,) * 4)],
         "VIKINGS": [("infantry", "hp", (1.0, 1.2, 1.2, 1.2))]}


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


def speed(g, name):
    """The factor of the walk speed of unit name for the civilization of the player of g (UNITS), else 1."""
    import combat                                                  # combat imports gather, gather imports this module
    return math.prod(c for v, c in changes(g, name, combat.stats(name)) if v == "speed")


def civ(g):
    """The civilization of the player of g (aoe2mc.json "players"), for example "CELTS", else None."""
    return g.data.get("players", {}).get(str(g.player), {}).get("civ")


def work(g, kind):
    """The work-rate factor of the civilization of the player of g for gather kind (WORK), else 1."""
    return WORK.get(civ(g), {}).get(kind, 1)
