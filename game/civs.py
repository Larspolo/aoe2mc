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

# The cost bonuses (#1091): civilization -> [(what, resource or None (all), change in the Dark, Feudal, Castle and
# Imperial Age)]. what: a group of GROUPS (units), "buildings", "buildings but farms", "technologies", "ages" or a
# tuple of names. A float multiplies the cost (0.0: free), an int adds to it. AoE2 rounds half up (35 × 0.75 = 26).
SMITH = ("BLAST_FURNACE", "BODKIN_ARROW", "BRACER", "CHAIN_BARDING_ARMOR", "CHAIN_MAIL_ARMOR", "FLETCHING", "FORGING",
         "IRON_CASTING", "LEATHER_ARCHER_ARMOR", "PADDED_ARCHER_ARMOR",
         "PLATE_BARDING_ARMOR", "PLATE_MAIL_ARMOR", "RING_ARCHER_ARMOR",   # (#1452)
         "SCALE_BARDING_ARMOR", "SCALE_MAIL_ARMOR")   # the blacksmith
ECONOMY = ("BOW_SAW", "CARAVAN", "CROP_ROTATION", "DOUBLE_BIT_AXE", "FISHING_LINES", "GILLNETS", "GOLD_MINING",
           "GOLD_SHAFT_MINING", "GUILDS", "HAND_CART", "HEAVY_PLOW", "HORSE_COLLAR", "STONE_MINING", "STONE_SHAFT_MINING",
           "TWO_MAN_SAW", "WHEELBARROW")   # the economic technologies but Coinage and Banking (AoE2 wiki "Burgundians")
COSTS = {"BERBERS": [("cavalry", None, (1.0, 1.0, 0.85, 0.8))],
         "BOHEMIANS": [(("BLACKSMITH", "UNIVERSITY"), "wood", (-100,) * 4),
                       (("GOLD_MINING", "GOLD_SHAFT_MINING", "STONE_MINING", "STONE_SHAFT_MINING"), None, (0.0,) * 4)],   # (#1447)
         "BRITONS": [(("TOWN_CENTER",), "wood", (1.0, 1.0, 0.5, 0.5))],
         "BULGARIANS": [(("MAN_AT_ARMS_UPGRADE",), None, (0.0,) * 4), (("TOWN_CENTER",), "stone", (0.5,) * 4),
                        (SMITH, "food", (0.5,) * 4)],
         "BURGUNDIANS": [(("BLOODLINES",), None, (0.5,) * 4), (ECONOMY, "food", (0.6,) * 4)],   # (#1447)
         "BURMESE": [(("BOW_SAW", "DOUBLE_BIT_AXE", "TWO_MAN_SAW"), None, (0.0,) * 4)],   # the lumber camp (#1447)
         "BYZANTINES": [("camel riders", None, (0.75,) * 4), ("spearmen, skirmishers", None, (0.75,) * 4),
                        (("IMPERIAL_AGE",), None, (2 / 3,) * 4)],
         "CHINESE": [("technologies", None, (1.0, 0.95, 0.9, 0.85))],
         "CUMANS": [(("ARCHERY_RANGE", "STABLE"), "wood", (-75,) * 4)],
         "DRAVIDIANS": [(("MAN_AT_ARMS_UPGRADE",), None, (0.5,) * 4), ("siege", "wood", (2 / 3,) * 4)],
         "FRANKS": [(("CASTLE",), None, (1.0, 1.0, 0.85, 0.75)), (("HORSE_COLLAR",), None, (0.0,) * 4)],
         "GOTHS": [("infantry", None, (0.85, 0.8, 0.75, 0.7))],
         "HINDUSTANIS": [("villagers", None, (0.92, 0.87, 0.82, 0.77))],
         "HUNS": [("cavalry archers", None, (1.0, 1.0, 0.9, 0.8))],
         "INCAS": [("buildings", "stone", (0.85,) * 4), ("military", "food", (0.85, 0.8, 0.75, 0.7))],
         "ITALIANS": [("ages", None, (0.85,) * 4), ("gunpowder", None, (0.8,) * 4)],
         "JAPANESE": [(("LUMBER_CAMP", "MILL", "MINING_CAMP"), None, (0.5,) * 4)],
         "KOREANS": [(("LEATHER_ARCHER_ARMOR", "PADDED_ARCHER_ARMOR", "RING_ARCHER_ARMOR"), None, (0.0,) * 4), ("archers", "wood", (0.5,) * 4),
                     ("infantry", "wood", (0.5,) * 4)],
         "MAGYARS": [(("FORGING", "IRON_CASTING", "BLAST_FURNACE"), None, (0.0,) * 4), ("scout line", None, (0.85,) * 4)],
         "MALAY": [("battle elephants", None, (1.0, 1.0, 0.75, 0.65)), (("CHAIN_MAIL_ARMOR", "PLATE_MAIL_ARMOR", "SCALE_MAIL_ARMOR"), None,
                                                                              (0.0,) * 4)],
         "MALIANS": [("buildings but farms", "wood", (0.85,) * 4)],
         "MAYANS": [("foot archers but skirmishers", None, (1.0, 0.9, 0.8, 0.7))],
         "POLES": [(("BLOODLINES",), "food", (0.5,) * 4)],
         "PORTUGUESE": [("units", "gold", (0.8,) * 4)],
         "ROMANS": [("scorpions", "gold", (0.5,) * 4)],
         "SLAVS": [("siege", None, (0.85,) * 4)],
         "SPANISH": [(SMITH, "gold", (0.0,) * 4)],
         "TEUTONS": [(("FARM",), None, (0.6,) * 4)],
         "VIETNAMESE": [(ECONOMY, "wood", (0.0,) * 4)],                    # (#1447)
         "VIKINGS": [(("WHEELBARROW",), None, (0.0,) * 4)]}

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
# The technologies whose effect a civilization gets twice (AoE2 wiki, "Civilization bonuses"; train.stats, #1561).
TWICE = {"KHITANS": ("FORGING", "IRON_CASTING")}
# The technologies and units that a civilization does not have (AoE2 wiki, the availability chart of each, #1373):
# the menu does not show them (train.unlocked).
MISSING = {"ARCHITECTURE": ("ACHAEMENIDS", "ARMENIANS", "ATHENIANS", "AZTECS", "BERBERS", "BYZANTINES", "CELTS",
                            "CUMANS", "DANES", "DRAVIDIANS", "HINDUSTANIS", "HUNS", "INCAS", "JAPANESE", "KHITANS",
                            "MACEDONIANS", "MAGYARS", "MALAY", "MAPUCHE", "MONGOLS", "MUISCA", "POLES", "PURU",
                            "SARACENS", "SICILIANS", "SLAVS", "SPARTANS", "TATARS", "TEUTONS", "THRACIANS", "TUPI",
                            "VIETNAMESE", "WEI"),   # the wiki chart (#1504)
           "ARROWSLITS": ("ACHAEMENIDS", "ARMENIANS", "ATHENIANS", "BULGARIANS", "BURMESE", "CUMANS", "ETHIOPIANS",
                          "GOTHS", "GURJARAS", "HINDUSTANIS", "HUNS", "KHITANS", "KHMER", "LITHUANIANS",
                          "MACEDONIANS", "MAGYARS", "MALAY", "MALIANS", "MAYANS", "MONGOLS", "MUISCA", "PERSIANS",
                          "PORTUGUESE", "PURU", "ROMANS", "SLAVS", "SPARTANS", "TATARS", "THRACIANS", "VARANGIANS",
                          "WEI", "WU"),   # the wiki chart (#1504)
           "ARSON": ("GOTHS", "MUISCA", "ROMANS"),                                          # (#1419)
           "ATONEMENT": ("BRITONS", "BULGARIANS", "CELTS", "DANES", "FRANKS", "GEORGIANS", "GOTHS",
                         "HINDUSTANIS", "INCAS", "KHMER", "KOREANS", "MAGYARS", "PERSIANS", "POLES", "SICILIANS",
                         "TUPI", "WEI"),                                                # the wiki chart (#1581)
           "BLOCK_PRINTING": ("BERBERS", "BULGARIANS", "CELTS", "CUMANS", "ETHIOPIANS", "GOTHS", "GURJARAS", "HUNS",
                              "KHITANS", "KHMER", "MAPUCHE", "MONGOLS", "SHU", "SICILIANS", "TUPI", "TURKS",
                              "VARANGIANS", "WU"),                                          # (#1457)
           "BOMBARD_CANNON": ("ACHAEMENIDS", "ARMENIANS", "ATHENIANS", "AZTECS", "BENGALIS", "BRITONS", "BULGARIANS",
                              "CELTS", "CHINESE", "CUMANS", "DANES", "GEORGIANS", "HUNS", "INCAS", "JAPANESE",
                              "KHITANS", "KHMER", "MACEDONIANS", "MAGYARS", "MAPUCHE", "MAYANS", "MONGOLS", "MUISCA",
                              "PURU", "ROMANS", "SAXONS", "SHU", "SICILIANS", "SLAVS", "SPARTANS", "TATARS",
                              "THRACIANS", "TUPI", "VARANGIANS", "VIKINGS", "WEI", "WU"),   # (#1443)
           "BOMBARD_TOWER_TECH": ("ACHAEMENIDS", "ATHENIANS", "AZTECS", "BENGALIS", "BERBERS", "BRITONS", "BULGARIANS",
                                  "BURMESE", "CELTS", "CUMANS", "DANES", "ETHIOPIANS", "FRANKS", "GEORGIANS", "GOTHS",
                                  "GURJARAS", "HINDUSTANIS", "HUNS", "INCAS", "JAPANESE", "JURCHENS", "KHITANS", "KHMER",
                                  "MACEDONIANS", "MAGYARS", "MALIANS", "MAYANS", "MONGOLS", "MUISCA", "PERSIANS", "PURU",
                                  "ROMANS", "SARACENS", "SAXONS", "SHU", "SICILIANS", "SLAVS", "SPARTANS", "THRACIANS",
                                  "TUPI", "VARANGIANS", "VIKINGS", "WEI", "WU"),
           "BRACER": ("CELTS", "CUMANS", "FRANKS", "MALIANS", "MAPUCHE", "PERSIANS", "ROMANS", "SLAVS", "TEUTONS"),   # (#1503)
           "CAMEL_RIDER": ("ACHAEMENIDS", "ARMENIANS", "ATHENIANS", "AZTECS", "BENGALIS", "BOHEMIANS", "BRITONS",
                           "BULGARIANS", "BURGUNDIANS", "BURMESE", "CELTS", "CHINESE", "DANES", "DRAVIDIANS",
                           "FRANKS", "GEORGIANS", "GOTHS", "HUNS", "INCAS", "ITALIANS", "JAPANESE", "JURCHENS",
                           "KHMER", "KOREANS", "LITHUANIANS", "MACEDONIANS", "MAGYARS", "MALAY", "MAPUCHE", "MAYANS",
                           "MUISCA", "POLES", "PORTUGUESE", "PURU", "ROMANS", "SAXONS", "SHU", "SICILIANS", "SLAVS",
                           "SPANISH", "SPARTANS", "TEUTONS", "THRACIANS", "TUPI", "VARANGIANS", "VIETNAMESE",
                           "VIKINGS", "WEI", "WU"),   # the wiki chart (#1550)
           "CANNON_GALLEON": ("ARMENIANS", "AZTECS", "BYZANTINES", "CHINESE", "CUMANS", "DANES", "GOTHS", "HUNS", "INCAS",
                              "JURCHENS", "MAPUCHE", "MAYANS", "MUISCA", "ROMANS", "SAXONS", "SHU", "TUPI", "VARANGIANS",
                              "VIKINGS", "WEI", "WU"),                                     # (#1484)
           "CAVALIER_UPGRADE": ("AZTECS", "BENGALIS", "DANES", "DRAVIDIANS", "GURJARAS", "HINDUSTANIS", "INCAS", "JURCHENS",
                                "KHITANS", "MAPUCHE", "MAYANS", "MUISCA", "SARACENS", "SHU", "TUPI", "WEI",
                                "WU"),                                 # the wiki chart (#1501)
           "CAVALRY_ARCHER": ("AZTECS", "BENGALIS", "BOHEMIANS", "BRITONS", "BURGUNDIANS", "CELTS", "DANES", "DRAVIDIANS",
                              "FRANKS", "GURJARAS", "INCAS", "ITALIANS", "MAPUCHE", "MAYANS", "MUISCA", "POLES",
                              "PORTUGUESE", "SAXONS", "SICILIANS", "SPANISH", "TEUTONS", "TUPI", "VARANGIANS", "VIKINGS",
                              "WEI"),                                 # the wiki chart (#1430)
           "CROP_ROTATION": ("ARMENIANS", "BOHEMIANS", "BRITONS", "CELTS", "CHINESE", "DANES", "DRAVIDIANS", "ETHIOPIANS",
                             "HINDUSTANIS", "HUNS", "JAPANESE", "KHITANS", "KOREANS", "MONGOLS", "SARACENS", "SHU",
                             "SPANISH", "TUPI", "TURKS", "WU"),                     # the wiki chart (#1578)
           "DEMOLITION_RAFT": ("DANES", "KOREANS", "PORTUGUESE", "SAXONS", "VARANGIANS", "VIKINGS"),   # (#1481)
           "DEMOLITION_SHIP": ("DANES", "KOREANS", "PORTUGUESE", "SAXONS", "VARANGIANS", "VIKINGS"),   # (#1481)
           "DRY_DOCK": ("BOHEMIANS", "BULGARIANS", "BURGUNDIANS", "CUMANS", "GEORGIANS", "GOTHS", "GURJARAS",
                        "HINDUSTANIS", "KHITANS", "MAPUCHE", "MONGOLS", "POLES", "ROMANS", "TEUTONS", "WEI"),   # (#1441)
           "ELITE_CANNON_GALLEON_UPGRADE": ("ACHAEMENIDS", "ARMENIANS", "ATHENIANS", "AZTECS", "BRITONS", "BULGARIANS",
                                            "BYZANTINES", "CELTS", "CHINESE", "CUMANS", "DANES", "ETHIOPIANS", "FRANKS",
                                            "GEORGIANS", "GOTHS", "GURJARAS", "HUNS", "INCAS", "JURCHENS", "KHITANS",
                                            "MACEDONIANS", "MAGYARS", "MALIANS", "MAPUCHE", "MAYANS", "MONGOLS",
                                            "MUISCA", "POLES", "PURU", "ROMANS", "SAXONS", "SHU", "SICILIANS", "SLAVS",
                                            "SPARTANS", "TEUTONS", "THRACIANS", "TUPI", "VARANGIANS", "VIKINGS", "WEI",
                                            "WU"),   # the wiki chart (#1491)
           "FAITH": ("BULGARIANS", "DANES", "GURJARAS", "JURCHENS", "MAGYARS", "TATARS"),        # (#1584)
           "FAST_FIRE_SHIP": ("ARMENIANS", "BOHEMIANS", "BULGARIANS", "BURMESE", "CELTS", "CHINESE", "ETHIOPIANS",
                              "GURJARAS", "HINDUSTANIS", "HUNS", "JURCHENS", "MUISCA", "PORTUGUESE", "SARACENS",
                              "SAXONS", "SHU", "TUPI", "TURKS", "VIETNAMESE", "VIKINGS"),   # the wiki chart (#1483)
           "FORTIFIED_WALL": ("BULGARIANS", "CUMANS", "DANES", "GOTHS", "HUNS", "MAGYARS", "MALAY", "MAPUCHE", "MUISCA",
                              "PERSIANS", "SICILIANS", "TUPI", "WU"),
           "GALLEON": ("AZTECS", "KHITANS", "MALIANS"),                                   # (#1483)
           "GAMBESONS": ("ACHAEMENIDS", "ATHENIANS", "BERBERS", "BOHEMIANS", "BURGUNDIANS", "CHINESE", "CUMANS",
                          "ETHIOPIANS", "GOTHS", "GURJARAS", "HINDUSTANIS", "HUNS", "INCAS", "ITALIANS", "KHMER",
                          "KOREANS", "LITHUANIANS", "MACEDONIANS", "MAGYARS", "MALAY", "MALIANS", "MAPUCHE", "MAYANS",
                          "MONGOLS", "MUISCA", "POLES", "PURU", "ROMANS", "SPARTANS", "TATARS", "THRACIANS", "TUPI",
                          "TURKS", "VIETNAMESE", "VIKINGS", "WEI", "WU"),
           "HAND_CANNONEER": ("ACHAEMENIDS", "ARMENIANS", "ATHENIANS", "AZTECS", "BENGALIS", "BRITONS", "BULGARIANS",
                              "BURMESE", "CELTS", "CHINESE", "CUMANS", "DANES", "ETHIOPIANS", "HUNS", "INCAS",
                              "JURCHENS", "KHITANS", "MACEDONIANS", "MAGYARS", "MALAY", "MAPUCHE", "MAYANS",
                              "MONGOLS", "MUISCA", "POLES", "PURU", "ROMANS", "SAXONS", "SHU", "SICILIANS", "SLAVS",
                              "SPARTANS", "THRACIANS", "TUPI", "VARANGIANS", "VIETNAMESE", "VIKINGS", "WEI", "WU"),   # the wiki chart (#1535)
           "HEATED_SHOT": ("BOHEMIANS", "BURGUNDIANS", "BYZANTINES", "FRANKS", "GEORGIANS", "HINDUSTANIS", "HUNS",
                           "JAPANESE", "JURCHENS", "MAPUCHE", "MONGOLS", "MUISCA", "POLES", "ROMANS", "SARACENS",
                           "SLAVS", "SPANISH"),                                       # the wiki chart (#1548)
           "HEAVY_CAMEL_RIDER_UPGRADE": ("ACHAEMENIDS", "ARMENIANS", "ATHENIANS", "AZTECS", "BENGALIS", "BOHEMIANS",
                                         "BRITONS", "BULGARIANS", "BURGUNDIANS", "BURMESE", "CELTS", "CHINESE",
                                         "CUMANS", "DANES", "DRAVIDIANS", "FRANKS", "GEORGIANS", "GOTHS", "HUNS",
                                         "INCAS", "ITALIANS", "JAPANESE", "JURCHENS", "KHMER", "KOREANS",
                                         "LITHUANIANS", "MACEDONIANS", "MAGYARS", "MALAY", "MAPUCHE", "MAYANS",
                                         "MUISCA", "POLES", "PORTUGUESE", "PURU", "ROMANS", "SAXONS", "SHU",
                                         "SICILIANS", "SLAVS", "SPANISH", "SPARTANS", "TEUTONS", "THRACIANS", "TUPI",
                                         "VARANGIANS", "VIETNAMESE", "VIKINGS", "WEI", "WU"),   # the wiki chart (#1550)
           "HERESY": ("BENGALIS", "BRITONS", "BURGUNDIANS", "BURMESE", "CHINESE", "DANES", "DRAVIDIANS", "GOTHS",
                      "HINDUSTANIS", "ITALIANS", "JAPANESE", "JURCHENS", "KHMER", "KOREANS", "PERSIANS", "POLES",
                      "ROMANS", "SICILIANS", "SLAVS", "TATARS", "VARANGIANS", "VIETNAMESE", "WEI", "WU"),   # (#1582)
           "HEAVY_DEMOLITION_SHIP": ("ACHAEMENIDS", "ATHENIANS", "AZTECS", "BENGALIS", "BOHEMIANS", "BULGARIANS",
                                     "BURGUNDIANS", "BURMESE", "CUMANS", "DANES", "ETHIOPIANS", "GEORGIANS",
                                     "HINDUSTANIS", "INCAS", "ITALIANS", "JAPANESE", "KHITANS", "KHMER", "KOREANS",
                                     "LITHUANIANS", "MACEDONIANS", "MAGYARS", "MALAY", "MAPUCHE", "POLES",
                                     "PORTUGUESE", "PURU", "ROMANS", "SAXONS", "SLAVS", "SPARTANS", "TATARS",
                                     "THRACIANS", "TUPI", "VARANGIANS", "VIKINGS", "WEI"),   # the wiki chart (#1483)
           "HEAVY_PLOW": ("KHITANS",),                                     # (#1424)
           "HERBAL_MEDICINE": ("BYZANTINES", "DANES", "HUNS", "KHITANS", "SHU", "TURKS", "VIKINGS", "WEI"),   # (#1585)
           "HOARDINGS": ("AZTECS", "BENGALIS", "BOHEMIANS", "BULGARIANS", "BURMESE", "CHINESE", "ETHIOPIANS", "GOTHS",
                         "HUNS", "KHITANS", "KOREANS", "MALAY", "PORTUGUESE", "ROMANS", "TATARS", "VARANGIANS",
                         "WU"),                                            # (#1456)
           "HUSBANDRY": ("AZTECS", "CUMANS", "INCAS", "MAPUCHE", "MAYANS", "MUISCA", "TEUTONS", "TUPI", "VIKINGS"),
           "HUSSAR_UPGRADE": ("ACHAEMENIDS", "ARMENIANS", "ATHENIANS", "AZTECS", "BENGALIS", "BOHEMIANS", "BRITONS",
                              "CHINESE", "DANES", "DRAVIDIANS", "FRANKS", "INCAS", "JAPANESE", "LITHUANIANS",
                              "MACEDONIANS", "MALAY", "MALIANS", "MAPUCHE", "MAYANS", "MUISCA", "POLES",
                              "PORTUGUESE", "PURU", "ROMANS", "SHU", "SICILIANS", "SPARTANS", "TEUTONS", "THRACIANS",
                              "TUPI", "VIETNAMESE", "VIKINGS"),   # the wiki chart (#1502)
           "ILLUMINATION": ("CELTS", "CUMANS", "DRAVIDIANS", "GEORGIANS", "KOREANS", "MALIANS", "MAPUCHE", "MAYANS",
                            "MONGOLS", "PERSIANS", "POLES", "PORTUGUESE", "TURKS", "VIKINGS"),   # the wiki chart (#1583)
           "KNIGHT": ("AZTECS", "BENGALIS", "DRAVIDIANS", "GURJARAS", "HINDUSTANIS", "INCAS", "JURCHENS", "KHITANS",
                      "MAPUCHE", "MAYANS", "MUISCA", "SHU", "TUPI", "WEI", "WU"),   # the wiki chart (#1430)
           "PALADIN_UPGRADE": ("ACHAEMENIDS", "ARMENIANS", "ATHENIANS", "AZTECS", "BENGALIS", "BERBERS", "BOHEMIANS",
                               "BRITONS", "BULGARIANS", "BURMESE", "CHINESE", "DANES", "DRAVIDIANS", "ETHIOPIANS",
                               "GEORGIANS", "GOTHS", "GURJARAS", "HINDUSTANIS", "INCAS", "ITALIANS", "JAPANESE",
                               "JURCHENS", "KHITANS", "KHMER", "KOREANS", "MACEDONIANS", "MALAY", "MALIANS", "MAPUCHE",
                               "MAYANS", "MONGOLS", "MUISCA", "PERSIANS", "POLES", "PORTUGUESE", "PURU", "ROMANS",
                               "SARACENS", "SAXONS", "SHU", "SICILIANS", "SLAVS", "SPARTANS", "TATARS", "THRACIANS",
                               "TUPI", "TURKS", "VARANGIANS", "VIETNAMESE", "VIKINGS", "WEI", "WU"),   # the wiki chart (#1501)
           "PARTHIAN_TACTICS": ("ACHAEMENIDS", "ARMENIANS", "ATHENIANS", "AZTECS", "BENGALIS",
                                "BERBERS", "BOHEMIANS", "BRITONS", "BURGUNDIANS", "BYZANTINES",
                                "CELTS", "CHINESE", "DANES", "DRAVIDIANS", "ETHIOPIANS", "FRANKS",
                                "GOTHS", "GURJARAS", "HINDUSTANIS", "INCAS", "ITALIANS",
                                "JURCHENS", "KOREANS", "LITHUANIANS", "MACEDONIANS", "MALAY",
                                "MALIANS", "MAPUCHE", "MAYANS", "MUISCA", "POLES", "PORTUGUESE",
                                "PURU", "ROMANS", "SAXONS", "SHU", "SICILIANS", "SLAVS",
                                "SPANISH", "SPARTANS", "TEUTONS", "THRACIANS", "TUPI",
                                "VARANGIANS", "VIETNAMESE", "VIKINGS", "WU"),   # the wiki chart (#1505)
           "SAPPERS": ("BENGALIS", "BERBERS", "BULGARIANS", "BURMESE", "BYZANTINES", "DANES", "DRAVIDIANS", "FRANKS",
                       "HINDUSTANIS", "ITALIANS", "JAPANESE", "KHITANS", "KOREANS", "LITHUANIANS", "MUISCA",
                       "SARACENS", "VARANGIANS", "WEI", "WU"),                     # the wiki chart (#1580)
           "SHIPWRIGHT": ("ACHAEMENIDS", "ARMENIANS", "ATHENIANS", "BOHEMIANS", "BULGARIANS", "BURGUNDIANS", "BURMESE",
                          "CUMANS", "FRANKS", "GEORGIANS", "HINDUSTANIS", "HUNS", "JURCHENS", "KHITANS", "KHMER",
                          "LITHUANIANS", "MACEDONIANS", "MALIANS", "MAPUCHE", "MUISCA", "PERSIANS", "POLES", "PORTUGUESE",
                          "PURU", "SARACENS", "SLAVS", "SPARTANS", "TATARS", "TEUTONS", "THRACIANS", "TUPI",
                          "VIETNAMESE", "VIKINGS", "WEI", "WU"),                           # the wiki chart (#1490)
           "SQUIRES": ("CELTS", "GURJARAS", "KHMER", "MAGYARS", "MAPUCHE", "PORTUGUESE"),   # (#1415)
           "THEOCRACY": ("BURGUNDIANS", "CELTS", "CUMANS", "HUNS", "MALAY", "MONGOLS", "ROMANS", "SICILIANS",   # (#1586)
                         "TATARS", "VIKINGS"),
           "THUMB_RING": ("ARMENIANS", "AZTECS", "BENGALIS", "BOHEMIANS", "BRITONS", "BURGUNDIANS", "BURMESE", "CELTS",
                          "FRANKS", "GEORGIANS", "GOTHS", "JURCHENS", "KHMER", "MAPUCHE", "ROMANS", "SICILIANS", "SLAVS",
                          "TEUTONS", "TUPI", "VARANGIANS", "VIKINGS", "WU"),   # (#1421)
           "TREADMILL_CRANE": ("BULGARIANS", "CHINESE", "CUMANS", "DANES", "DRAVIDIANS", "ETHIOPIANS", "HINDUSTANIS",
                               "KHITANS", "MONGOLS", "PERSIANS", "ROMANS", "SPANISH"),   # (#1422)
           "TWO_MAN_SAW": ("ARMENIANS", "AZTECS", "BERBERS", "BULGARIANS", "CELTS", "DANES", "FRANKS", "GEORGIANS",
                           "GURJARAS", "INCAS", "KHMER", "MALAY", "MALIANS", "MONGOLS", "POLES", "ROMANS", "SICILIANS",
                           "TATARS", "TUPI", "WEI")}                  # the wiki chart (#1577)
ELEPHANTS = ("BENGALIS", "BURMESE", "DRAVIDIANS", "KHMER", "MALAY", "VIETNAMESE")   # the battle elephant (AoE2 DE wiki, #1556)
MISSING |= {"BATTLE_ELEPHANT": tuple(sorted(set().union(*MISSING.values()) - set(ELEPHANTS))),
            "ELITE_BATTLE_ELEPHANT": tuple(sorted(set().union(*MISSING.values()) - set(ELEPHANTS) | {"DRAVIDIANS"}))}   # no elite
EAGLES = ("AZTECS", "MAYANS")                                     # the eagle line (AoE2 DE wiki; not the Incas since
MISSING |= dict.fromkeys(("EAGLE_SCOUT", "EAGLE_WARRIOR", "ELITE_EAGLE_WARRIOR"),   # The Last Chieftains, #1555)
                         tuple(sorted(set().union(*MISSING.values()) - set(EAGLES))))
MISSING["WINGED_HUSSAR_UPGRADE"] = tuple(sorted(set().union(*MISSING.values()) - {"LITHUANIANS", "POLES"}))   # (#1558)
MISSING["IMPERIAL_SKIRMISHER_UPGRADE"] = tuple(sorted(set().union(*MISSING.values()) - {"VIETNAMESE"}))   # (#1611)
LANCERS = ("CUMANS", "JURCHENS", "KHITANS", "MONGOLS", "TATARS")   # the steppe lancers (AoE2 DE wiki, #1557)
MISSING |= dict.fromkeys(("STEPPE_LANCER", "ELITE_STEPPE_LANCER", "ELITE_STEPPE_LANCER_UPGRADE"),
                         tuple(sorted(set().union(*MISSING.values()) - set(LANCERS))))
MISSING |= dict.fromkeys(("GENITOUR", "ELITE_GENITOUR", "ELITE_GENITOUR_UPGRADE"),   # the Berbers (AoE2 DE wiki, #1610)
                         tuple(sorted(set().union(*MISSING.values()) - {"BERBERS"})))
MISSING |= dict.fromkeys(("CHAKRAM_THROWER", "ELITE_CHAKRAM_THROWER", "ELITE_CHAKRAM_THROWER_UPGRADE"),   # (#1624)
                         tuple(sorted(set().union(*MISSING.values()) - {"GURJARAS"})))
MISSING |= dict.fromkeys(("SHRIVAMSHA_RIDER", "ELITE_SHRIVAMSHA_RIDER", "ELITE_SHRIVAMSHA_RIDER_UPGRADE"),
                         tuple(sorted(set().union(*MISSING.values()) - {"GURJARAS"})))   # (AoE2 DE wiki, #1612)


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


def civ(g, player=None):
    """The civilization of the player of g, or of another player (aoe2mc.json "players"), for example "CELTS", else None."""
    return g.data.get("players", {}).get(str(g.player if player is None else player), {}).get("civ")


def start(g, base):
    """The start resources `base` with the start bonus of the civilization of the player of g (START)."""
    bonus = START.get(civ(g), {})
    return {r: max(0, v + bonus.get(r, 0)) for r, v in base.items()}


def work(g, kind):
    """The work-rate factor of the civilization of the player of g for gather kind (WORK), else 1."""
    return WORK.get(civ(g), {}).get(kind, 1)
