"""
Train villagers at the town center in the game program (#612, part of #396). A right click with the command stick on
an own town center queues a villager and takes its cost from the stock, as in AoE2. A town center trains one unit at
a time, in the AoE2 train time; then the villager appears on a free cell in front of it, with the NBT of the converter
(units.make_entity) and the AoE2 hit points (combat.stats_command), and a click can select it and send it to gather.
gather.Gather.click calls queue(), gather.Gather.step calls tick().
The population limit (#613): each complete own town center and house gives 5, at most 200. At the limit the unit at
the head of a queue does not start; the sidebar shows the population and the limit.
The menu (#620): a right click on an own town center opens its chest menu (menu.py) with the item "Villager"; a click
on it queues 1 villager, a shift click 5 (as many as the food and the queue allow), and the menu stays open with the
new queue count. gather.Gather.click calls open_menu().
Military units (#654): a right click on an own barracks opens its menu with "Militia" (TRAINS); a trained militia
joins the military units of the player (g.soldiers), so a click can select it and send it to attack. An own archery
range trains archers (#670): they shoot from their AoE2 range (combat.range_command). An own stable trains scout
cavalry (#671): a rider on a horse (the Passengers of units.make_entity); the horse is the unit.
The barracks trains spearmen (#729) and the archery range skirmishers (#730, a drowned that throws tridents) in the
Feudal Age: before it, the menu shows a gray item (build.locked).
Technologies (#655): a technology (TECHS) is an item of the menu of its building and uses the queue of the units, as in
AoE2, but needs no population room. A click queues it once; when it is complete it goes into g.techs, leaves the menu
and changes the values of the live and the new units (stats()). Loom: villagers get 15 hit points and 1/2 armor.
Ages (#672): the Feudal Age is a technology of the town center that needs 2 types of Dark Age buildings (REQUIRES). The
sidebar title shows the age of the player; all players see a title and hear a sound when a player advances.
The Castle Age (#1080) needs the Feudal Age (build.AGE: a gray item before it) and 2 types of Feudal Age buildings.
The Imperial Age (#1081) needs the Castle Age and a castle, or 2 types of Castle Age buildings (REQUIRES).
Forging at the blacksmith (#675): infantry and cavalry get +1 attack. Fletching (#724): archers (also cavalry archers and
skirmishers) get +1 attack and +1 range.
Padded Archer Armor at the blacksmith in the Feudal Age (#937, TECH_AGE): archers get +1 melee and +1 pierce armor.
Double-Bit Axe at the lumber camp (#723): villagers chop wood 20 % faster (gather.WORK_TECHS, gather.Gather.work_time).
Gold Mining at the mining camp (#727): villagers mine gold 15 % faster. Stone Mining (#939): stone 15 % faster.
Horse Collar at the mill (#726): the live and the new farms of the player have 75 more food (gather.FARM_TECHS).
Wheelbarrow at the town center in the Feudal Age (#728, TECH_AGE): villagers carry 3 more resources and walk 10 % faster (gather.CARRY, gather.PACE).
Scale Barding Armor at the blacksmith in the Feudal Age (#938): cavalry (also camels and elephants, not cavalry archers)
gets +1 melee and +1 pierce armor (barding()).
Bloodlines at the stable in the Feudal Age (#940): cavalry gets 20 more hit points, also a live unit (it keeps its lost
hit points: `aoe stats`).
Man-at-Arms at the barracks in the Feudal Age (#941, UPGRADES): the live militia of the player become men-at-arms
(name and values), and the barracks trains men-at-arms instead of militia.
Rally points (#707): the menu item "Rally point" (RALLY) and the next right click on the ground set the rally point of
the building; each new unit walks there (Minecraft path finding), a new villager gathers at a tree, bush, mine or farm.
The castle (#708) trains the unique unit of the civilization of its player (UNIQUE, trains()). Only the units with AoE2
combat values (combat.STATS) are in its menu.
The monastery trains monks in the Castle Age (#1243): a monk does not gather, so it joins g.soldiers and takes the
move orders of the military units. It researches Fervor (monks walk 15 % faster, SPEEDS, speed()) and Sanctity (monks
get 15 more hit points) in the Castle Age (#1261).
The market trains trade carts (#1253): a trade cart also joins g.soldiers, and trade.py walks it between two own markets.
It researches Caravan (trade carts walk 20 % faster, SPEEDS) in the Castle Age and Guilds (trading fee 15 %, market.FEES)
in the Imperial Age (#1254). Coinage and Banking change the tribute fee: the game program has no tribute yet.
The university researches Fortified Wall in the Castle Age (#1326, WALL_UPGRADES): the new and the complete own stone
walls and gates get the fortified design and its AoE2 hit points and armor (build.design, build.upgrade).
An age gives the complete own walls and gates the AoE2 hit points of the new age (#1372, combat.WALLS, build.upgrade).
It researches Guard Tower in the Castle Age and Keep (after Guard Tower) in the Imperial Age (#1374, TOWER_UPGRADES):
the new and the complete own watch towers get the AoE2 hit points, attack and armor of the guard tower or the keep
(build.line, build.retower). The look of the tower stays.
"""
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import units  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402
import civs  # noqa: E402
import garrison  # noqa: E402
import menu  # noqa: E402

COSTS = {"VILLAGER_MALE": {"food": 50}, "MILITIA": {"food": 60, "gold": 20},   # as in AoE2
         "ARCHER": {"wood": 25, "gold": 45}, "LOOM": {"gold": 50}, "FEUDAL_AGE": {"food": 500},
         "BATTERING_RAM": {"wood": 160, "gold": 75},
         "BERSERK": {"food": 65, "gold": 20},
         "BLOODLINES": {"food": 150, "gold": 100},
         "CAPPED_RAM": {"wood": 160, "gold": 75},
         "CAPPED_RAM_UPGRADE": {"food": 300},
         "CASTLE_AGE": {"food": 800, "gold": 200},
         "CARAVAN": {"food": 200, "gold": 200},
         "CATAPHRACT": {"food": 70, "gold": 75},
         "CHAIN_BARDING_ARMOR": {"food": 250, "gold": 150},             # AoE2 DE wiki (#1394)
         "CHAIN_MAIL_ARMOR": {"food": 200, "gold": 100},
         "CHU_KO_NU": {"wood": 40, "gold": 35},
         "DOUBLE_BIT_AXE": {"food": 100, "wood": 50},
         "FERVOR": {"gold": 140},
         "FISHING_SHIP": {"wood": 75},                                  # AoE2 DE wiki (#1383)
         "FLETCHING": {"food": 100, "gold": 50},
         "FORGING": {"food": 150},
         "FORTIFIED_WALL": {"food": 200, "wood": 100},
         "GOLD_MINING": {"food": 100, "wood": 75},
         "GUARD_TOWER": {"food": 100, "wood": 250},                    # the upgrade (AoE2 DE wiki "Watch Tower")
         "GUILDS": {"food": 300, "gold": 200},
         "HEAVY_SCORPION": {"wood": 75, "gold": 75},
         "HEAVY_SCORPION_UPGRADE": {"food": 800, "wood": 750},
         "HORSE_COLLAR": {"food": 75, "wood": 75},
         "HUSKARL": {"food": 75, "gold": 35},
         "IMPERIAL_AGE": {"food": 1000, "gold": 800},
         "JANISSARY": {"food": 60, "gold": 55},
         "KEEP": {"food": 500, "wood": 350},                           # the upgrade (AoE2 DE wiki "Guard Tower")
         "LEATHER_ARCHER_ARMOR": {"food": 150, "gold": 150},
         "LONGBOWMAN": {"wood": 35, "gold": 40},
         "MAMELUKE": {"food": 55, "gold": 85},
         "MAN_AT_ARMS": {"food": 60, "gold": 20},
         "MAN_AT_ARMS_UPGRADE": {"food": 100, "gold": 40},
         "MANGONEL": {"wood": 160, "gold": 135},
         "MANGUDAI": {"wood": 55, "gold": 65},
         "MONK": {"gold": 100},
         "ONAGER": {"wood": 160, "gold": 135},
         "ONAGER_UPGRADE": {"food": 800, "gold": 500},
         "PADDED_ARCHER_ARMOR": {"food": 100},
         "REDEMPTION": {"gold": 475},
         "SAMURAI": {"food": 45, "gold": 30},
         "SANCTITY": {"gold": 175},
         "SCALE_BARDING_ARMOR": {"food": 150},
         "SCALE_MAIL_ARMOR": {"food": 100},
         "SCORPION": {"wood": 75, "gold": 75},
         "SIEGE_TOWER": {"wood": 100, "gold": 120},                  # the Castle Age (AoE2 DE wiki, #1362)
         "SCOUT_CAVALRY": {"food": 80},
         "SIEGE_ENGINEERS": {"food": 500, "wood": 600},
         "SIEGE_ONAGER": {"wood": 160, "gold": 135},
         "SIEGE_ONAGER_UPGRADE": {"food": 1450, "gold": 1000},
         "SIEGE_RAM": {"wood": 160, "gold": 75},
         "SIEGE_RAM_UPGRADE": {"food": 1000},
         "SKIRMISHER": {"food": 25, "wood": 35},
         "STONE_MINING": {"food": 100, "wood": 75},
         "SPEARMAN": {"food": 35, "wood": 25},
         "TEUTONIC_KNIGHT": {"food": 85, "gold": 30},
         "THROWING_AXEMAN": {"food": 55, "gold": 25},
         "TRADE_CART": {"wood": 100, "gold": 50},
         "TREBUCHET": {"wood": 200, "gold": 200},                   # the castle, Imperial Age (#1351)
         "WAR_ELEPHANT": {"food": 170, "gold": 85},
         "WHEELBARROW": {"food": 175, "wood": 50},
         "WOAD_RAIDER": {"food": 70, "gold": 25}}
TRAIN_TIMES = {"VILLAGER_MALE": 25, "MILITIA": 21, "ARCHER": 35, "LOOM": 25, "FEUDAL_AGE": 130,   # AoE2 seconds
               "BATTERING_RAM": 36,
               "BERSERK": 14,
               "BLOODLINES": 50,
               "CAPPED_RAM": 36,
               "CAPPED_RAM_UPGRADE": 50,
               "CARAVAN": 40,
               "CASTLE_AGE": 160,
               "CATAPHRACT": 20,
               "CHAIN_BARDING_ARMOR": 60,
               "CHAIN_MAIL_ARMOR": 55,
               "CHU_KO_NU": 16,
               "DOUBLE_BIT_AXE": 25,
               "FERVOR": 50,
               "FISHING_SHIP": 40,
               "FLETCHING": 30,
               "FORGING": 50,
               "FORTIFIED_WALL": 50,
               "GOLD_MINING": 30,
               "GUARD_TOWER": 30,
               "GUILDS": 50,
               "HEAVY_SCORPION": 30,
               "HEAVY_SCORPION_UPGRADE": 50,
               "HORSE_COLLAR": 20,
               "HUSKARL": 13,
               "IMPERIAL_AGE": 190,
               "JANISSARY": 21,
               "KEEP": 75,
               "LEATHER_ARCHER_ARMOR": 55,
               "LONGBOWMAN": 18,
               "MAMELUKE": 23,
               "MAN_AT_ARMS": 21,
               "MAN_AT_ARMS_UPGRADE": 40,
               "MANGONEL": 46,
               "MANGUDAI": 26,
               "MONK": 51,
               "ONAGER": 46,
               "ONAGER_UPGRADE": 75,
               "PADDED_ARCHER_ARMOR": 40,
               "REDEMPTION": 50,
               "SAMURAI": 9,
               "SANCTITY": 60,
               "SCALE_BARDING_ARMOR": 45,
               "SCALE_MAIL_ARMOR": 40,
               "SCORPION": 30,
               "SIEGE_TOWER": 36,
               "SCOUT_CAVALRY": 30,
               "SIEGE_ENGINEERS": 45,
               "SIEGE_ONAGER": 46,
               "SIEGE_ONAGER_UPGRADE": 150,
               "SIEGE_RAM": 36,
               "SIEGE_RAM_UPGRADE": 75,
               "SKIRMISHER": 22,
               "SPEARMAN": 22,
               "STONE_MINING": 30,
               "TEUTONIC_KNIGHT": 12,
               "THROWING_AXEMAN": 13,
               "TRADE_CART": 51,
               "TREBUCHET": 50,
               "WAR_ELEPHANT": 25,
               "WHEELBARROW": 75,
               "WOAD_RAIDER": 10}
TRAINS = {"TOWN_CENTER": ("VILLAGER_MALE", "LOOM", "FEUDAL_AGE", "WHEELBARROW", "CASTLE_AGE", "IMPERIAL_AGE"), "BARRACKS": ("MILITIA", "SPEARMAN", "MAN_AT_ARMS_UPGRADE"),   # the units and technologies of each
          "ARCHERY_RANGE": ("ARCHER", "SKIRMISHER"),                                         # building (#654, #670, #655)
          "BLACKSMITH": ("FORGING", "SCALE_MAIL_ARMOR", "FLETCHING",            # (#675, #725, #724, #937, #938)
                         "PADDED_ARCHER_ARMOR", "SCALE_BARDING_ARMOR",
                         "CHAIN_MAIL_ARMOR", "LEATHER_ARCHER_ARMOR", "CHAIN_BARDING_ARMOR"),   # the Castle Age (#1394)
          "CASTLE": ("TREBUCHET",),                                             # and the unique unit: trains() (#708, #1351)
          "STABLE": ("SCOUT_CAVALRY", "BLOODLINES"),                           # (#671, #940)
          "UNIVERSITY": ("FORTIFIED_WALL", "GUARD_TOWER", "KEEP", "SIEGE_ENGINEERS"),   # (#1326, #1374, #1352)
          "DOCK": ("FISHING_SHIP",),                                            # (#1383)
          "LUMBER_CAMP": ("DOUBLE_BIT_AXE",),                                   # (#723)
          "MARKET": ("TRADE_CART", "CARAVAN", "GUILDS"),                       # (#1253, #1254)
          "MILL": ("HORSE_COLLAR",),                                            # (#726)
          "MINING_CAMP": ("GOLD_MINING", "STONE_MINING"),                      # (#727, #939)
          "MONASTERY": ("MONK", "FERVOR", "SANCTITY", "REDEMPTION"),            # (#1243, #1261, #1264)
          "SIEGE_WORKSHOP": ("BATTERING_RAM", "MANGONEL", "SCORPION", "SIEGE_TOWER",   # (#1349, #1362)
                             "CAPPED_RAM_UPGRADE", "SIEGE_RAM_UPGRADE", "ONAGER_UPGRADE", "SIEGE_ONAGER_UPGRADE",
                             "HEAVY_SCORPION_UPGRADE")}                 # (#1352)
# The unique unit of each civilization (AoE2 DE), trained at its castle. A unit without COSTS is not in the menu yet:
# it has no AoE2 combat values in combat.STATS.
UNIQUE = {"BRITONS": "LONGBOWMAN", "PERSIANS": "WAR_ELEPHANT", "BYZANTINES": "CATAPHRACT", "CELTS": "WOAD_RAIDER",
          "CHINESE": "CHU_KO_NU", "FRANKS": "THROWING_AXEMAN", "GOTHS": "HUSKARL", "JAPANESE": "SAMURAI",
          "MONGOLS": "MANGUDAI", "SARACENS": "MAMELUKE", "TEUTONS": "TEUTONIC_KNIGHT", "TURKS": "JANISSARY",
          "VIKINGS": "BERSERK", "AZTECS": "JAGUAR_WARRIOR", "HUNS": "TARKAN", "KOREANS": "WAR_WAGON",
          "MAYANS": "PLUMED_ARCHER", "SPANISH": "CONQUISTADOR", "INCAS": "KAMAYUK", "ITALIANS": "GENOESE_CROSSBOWMAN",
          "MAGYARS": "MAGYAR_HUSZAR", "SLAVS": "BOYAR", "BERBERS": "CAMEL_ARCHER", "ETHIOPIANS": "SHOTEL_WARRIOR",
          "MALIANS": "GBETO", "PORTUGUESE": "ORGAN_GUN", "BURMESE": "ARAMBAI", "KHMER": "BALLISTA_ELEPHANT",
          "MALAY": "KARAMBIT_WARRIOR", "VIETNAMESE": "RATTAN_ARCHER", "BULGARIANS": "KONNIK", "CUMANS": "KIPCHAK",
          "LITHUANIANS": "LEITIS", "TATARS": "KESHIK", "BURGUNDIANS": "COUSTILLIER", "SICILIANS": "SERJEANT",
          "POLES": "OBUCH", "BOHEMIANS": "HUSSITE_WAGON", "HINDUSTANIS": "GHULAM", "DRAVIDIANS": "URUMI_SWORDSMAN",
          "BENGALIS": "RATHA", "GURJARAS": "SHRIVAMSHA_RIDER", "ROMANS": "CENTURION", "ARMENIANS": "COMPOSITE_BOWMAN",
          "GEORGIANS": "MONASPA"}
build.AGE |= dict.fromkeys(UNIQUE.values(), 2) | dict.fromkeys(("ELITE_" + n for n in UNIQUE.values()), 3)   # (#1082)
def engineers(name, s):
    """Siege Engineers (AoE2 DE, wiki): a siege unit +20 % bonus attack against buildings (rounded), a ranged one
    +1 range."""
    if "siege" not in s.classes:
        return s
    bonus = {**s.bonus, "building": round(s.bonus["building"] * 1.2)} if "building" in s.bonus else s.bonus
    return s._replace(range=s.range + (s.range > 0), bonus=bonus)


TECHS = {"BLOODLINES": lambda name, s: s._replace(hp=s.hp + 20) if "cavalry" in s.classes else s,
         "CAPPED_RAM_UPGRADE": lambda name, s: s,                  # a new unit name: UPGRADES
         "CARAVAN": lambda name, s: s,                             # the walk speed: SPEEDS
         "CASTLE_AGE": lambda name, s: s,                          # an age: REQUIRES
         "CHAIN_BARDING_ARMOR": lambda name, s: s._replace(melee=s.melee + 1, pierce=s.pierce + 1)
         if barding(s) else s,
         "CHAIN_MAIL_ARMOR": lambda name, s: s._replace(melee=s.melee + 1, pierce=s.pierce + 1)
         if "infantry" in s.classes else s,
         "DOUBLE_BIT_AXE": lambda name, s: s,                      # an economy technology: gather.WORK_TECHS
         "FERVOR": lambda name, s: s,                              # the walk speed: SPEEDS
         "FLETCHING": lambda name, s: s._replace(attack=s.attack + 1, range=s.range + 1) if "archer" in s.classes else s,
         "FORGING": lambda name, s: s._replace(attack=s.attack + 1) if melee(s) else s,
         "FORTIFIED_WALL": lambda name, s: s,                      # the walls of the player: WALL_UPGRADES
         "GOLD_MINING": lambda name, s: s,                         # an economy technology: gather.WORK_TECHS
         "GUARD_TOWER": lambda name, s: s,                         # the towers of the player: TOWER_UPGRADES
         "GUILDS": lambda name, s: s,                              # the trading fee: market.FEES
         "HEAVY_SCORPION_UPGRADE": lambda name, s: s,
         "HORSE_COLLAR": lambda name, s: s,                        # an economy technology: gather.FARM_TECHS
         "IMPERIAL_AGE": lambda name, s: s,                        # an age: REQUIRES
         "KEEP": lambda name, s: s,                                # the towers of the player: TOWER_UPGRADES
         "LEATHER_ARCHER_ARMOR": lambda name, s: s._replace(melee=s.melee + 1, pierce=s.pierce + 1)
         if "archer" in s.classes else s,
         "LOOM": lambda name, s: s._replace(hp=s.hp + 15, melee=s.melee + 1, pierce=s.pierce + 2)
         if "VILLAGER" in name else s,
         "MAN_AT_ARMS_UPGRADE": lambda name, s: s,                 # a new unit name: UPGRADES
         "ONAGER_UPGRADE": lambda name, s: s,
         "PADDED_ARCHER_ARMOR": lambda name, s: s._replace(melee=s.melee + 1, pierce=s.pierce + 1)
         if "archer" in s.classes else s,
         "REDEMPTION": lambda name, s: s,                          # monks convert buildings and siege: monk.py
         "SCALE_BARDING_ARMOR": lambda name, s: s._replace(melee=s.melee + 1, pierce=s.pierce + 1)
         if barding(s) else s,
         "SANCTITY": lambda name, s: s._replace(hp=s.hp + 15) if name == "MONK" else s,
         "SCALE_MAIL_ARMOR": lambda name, s: s._replace(melee=s.melee + 1, pierce=s.pierce + 1)
         if "infantry" in s.classes else s,
         "SIEGE_ENGINEERS": engineers,
         "SIEGE_ONAGER_UPGRADE": lambda name, s: s,
         "SIEGE_RAM_UPGRADE": lambda name, s: s,
         "STONE_MINING": lambda name, s: s,                        # an economy technology: gather.WORK_TECHS
         "FEUDAL_AGE": lambda name, s: s,   # the change of each technology to the AoE2 values
         "WHEELBARROW": lambda name, s: s}                         # no combat change: gather.CARRY and gather.PACE
SPEEDS = {"CARAVAN": ("TRADE_CART", 1.2),                         # technology: the unit and its walk speed factor
          "FERVOR": ("MONK", 1.15)}
UPGRADES = {                                                       # technology: the unit and its new unit (#941)
    "CAPPED_RAM_UPGRADE": ("BATTERING_RAM", "CAPPED_RAM"),           # the siege upgrades of AoE2 DE (#1352)
    "HEAVY_SCORPION_UPGRADE": ("SCORPION", "HEAVY_SCORPION"),
    "MAN_AT_ARMS_UPGRADE": ("MILITIA", "MAN_AT_ARMS"),
    "ONAGER_UPGRADE": ("MANGONEL", "ONAGER"),
    "SIEGE_ONAGER_UPGRADE": ("ONAGER", "SIEGE_ONAGER"),
    "SIEGE_RAM_UPGRADE": ("CAPPED_RAM", "SIEGE_RAM"),
}
AFTER = {"CHAIN_BARDING_ARMOR": "SCALE_BARDING_ARMOR", "CHAIN_MAIL_ARMOR": "SCALE_MAIL_ARMOR", "KEEP": "GUARD_TOWER",
         "LEATHER_ARCHER_ARMOR": "PADDED_ARCHER_ARMOR", "SIEGE_ONAGER_UPGRADE": "ONAGER_UPGRADE", "SIEGE_RAM_UPGRADE": "CAPPED_RAM_UPGRADE"}   # the upgrade before it
WALL_UPGRADES = {"FORTIFIED_WALL": {"STONE_WALL": "FORTIFIED_WALL", "GATE": "FORTIFIED_GATE"}}   # technology: {wall: new} (#1326)
TOWER_UPGRADES = {"GUARD_TOWER": {"WATCH_TOWER": "GUARD_TOWER"},   # technology: {tower: the tower of its values},
                  "KEEP": {"GUARD_TOWER": "KEEP", "WATCH_TOWER": "KEEP"}}   # in the research order (#1374)
REQUIRES = {"CASTLE_AGE": (2, ("ARCHERY_RANGE", "STABLE", "BLACKSMITH", "MARKET")),   # n types of these buildings
            "FEUDAL_AGE": (2, ("BARRACKS", "MILL", "LUMBER_CAMP", "MINING_CAMP", "DOCK")),
            "IMPERIAL_AGE": (2, ("MONASTERY", "UNIVERSITY", "SIEGE_WORKSHOP"), ("CASTLE",))}   # or one of these alone
TECH_AGE = {                                                       # the age of a technology (build.AGE): hidden before
    "BLOODLINES": 1,
    "CAPPED_RAM_UPGRADE": 3,
    "CARAVAN": 2,
    "CHAIN_BARDING_ARMOR": 2,
    "CHAIN_MAIL_ARMOR": 2,
    "DOUBLE_BIT_AXE": 1,
    "FERVOR": 2,
    "FLETCHING": 1,
    "FORGING": 1,
    "FORTIFIED_WALL": 2,
    "GOLD_MINING": 1,
    "GUARD_TOWER": 2,
    "GUILDS": 3,
    "HEAVY_SCORPION_UPGRADE": 3,
    "HORSE_COLLAR": 1,
    "KEEP": 3,
    "LEATHER_ARCHER_ARMOR": 2,
    "MAN_AT_ARMS_UPGRADE": 1,
    "ONAGER_UPGRADE": 3,
    "PADDED_ARCHER_ARMOR": 1,
    "REDEMPTION": 2,
    "SANCTITY": 2,
    "SCALE_BARDING_ARMOR": 1,
    "SCALE_MAIL_ARMOR": 1,
    "SIEGE_ENGINEERS": 3,
    "SIEGE_ONAGER_UPGRADE": 3,
    "SIEGE_RAM_UPGRADE": 3,
    "STONE_MINING": 1,
    "WHEELBARROW": 1,
}
AGES = ("Dark Age", "Feudal Age", "Castle Age", "Imperial Age")    # the age after each researched age (index: ages)
QUEUE = 15                                                         # units in the queue of one building, as in AoE2
HOUSING = {"TOWN_CENTER": 5, "HOUSE": 5, "CASTLE": 20}             # population of a complete building, as in AoE2
LIMIT = 200                                                        # the AoE2 population limit
REPEAT = 256                                                       # researches of one technology: "going above and beyond"
CENSUS = 2.0                                                       # AoE2 seconds between two counts of the live units
ITEMS = {"VILLAGER_MALE": (0, "villager_spawn_egg", "Villager"),   # menu slot, item and name of each unit (#620)
         "CAPPED_RAM": (0, "minecart", "Capped Ram"),
         "CAPPED_RAM_UPGRADE": (3, "book", "Capped Ram"),        # one slot for each line of upgrades
         "HEAVY_SCORPION": (2, "crossbow", "Heavy Scorpion"),
         "HEAVY_SCORPION_UPGRADE": (5, "book", "Heavy Scorpion"),
         "MILITIA": (0, "zombie_spawn_egg", "Militia"),             # the mob of units.classify
         "ARCHER": (0, "skeleton_spawn_egg", "Archer"),
         "ONAGER": (1, "dispenser", "Onager"),
         "ONAGER_UPGRADE": (4, "book", "Onager"),
         "SCOUT_CAVALRY": (0, "horse_spawn_egg", "Scout Cavalry"),
         "SIEGE_ENGINEERS": (1, "book", "Siege Engineers"),
         "SIEGE_ONAGER": (1, "dispenser", "Siege Onager"),
         "SIEGE_ONAGER_UPGRADE": (4, "book", "Siege Onager"),
         "SIEGE_RAM": (0, "minecart", "Siege Ram"),
         "SIEGE_RAM_UPGRADE": (3, "book", "Siege Ram"),
         "SKIRMISHER": (1, "drowned_spawn_egg", "Skirmisher"),
         "SPEARMAN": (1, "zombie_spawn_egg", "Spearman"),
         "BATTERING_RAM": (0, "minecart", "Battering Ram"),         # a siege unit is a minecart (units.siege)
         "BERSERK": (0, "zombie_spawn_egg", "Berserk"),
         "BLOODLINES": (1, "book", "Bloodlines"),
         "CARAVAN": (1, "book", "Caravan"),
         "CASTLE_AGE": (4, "bell", "Castle Age"),
         "CATAPHRACT": (0, "horse_spawn_egg", "Cataphract"),
         "CHAIN_BARDING_ARMOR": (4, "book", "Chain Barding Armor"),    # the slot of the Feudal armor (AFTER)
         "CHAIN_MAIL_ARMOR": (1, "book", "Chain Mail Armor"),
         "CHU_KO_NU": (0, "skeleton_spawn_egg", "Chu Ko Nu"),
         "DOUBLE_BIT_AXE": (0, "book", "Double-Bit Axe"),
         "FERVOR": (1, "book", "Fervor"),
         "FISHING_SHIP": (0, "oak_boat", "Fishing Ship"),         # a ship is a boat (units.boat)
         "FLETCHING": (2, "book", "Fletching"),
         "FORGING": (0, "book", "Forging"),
         "FORTIFIED_WALL": (0, "book", "Fortified Wall"),
         "GOLD_MINING": (0, "book", "Gold Mining"),
         "GUARD_TOWER": (2, "book", "Guard Tower"),
         "GUILDS": (2, "book", "Guilds"),
         "HORSE_COLLAR": (0, "book", "Horse Collar"),
         "HUSKARL": (0, "zombie_spawn_egg", "Huskarl"),
         "IMPERIAL_AGE": (5, "bell", "Imperial Age"),
         "JANISSARY": (0, "pillager_spawn_egg", "Janissary"),
         "KEEP": (3, "book", "Keep"),
         "LEATHER_ARCHER_ARMOR": (3, "book", "Leather Archer Armor"),
         "LONGBOWMAN": (0, "skeleton_spawn_egg", "Longbowman"),
         "LOOM": (1, "book", "Loom"),                               # a book for a technology (#618)
         "MAMELUKE": (0, "camel_spawn_egg", "Mameluke"),
         "MAN_AT_ARMS": (0, "zombie_spawn_egg", "Man-at-Arms"),
         "MAN_AT_ARMS_UPGRADE": (2, "book", "Man-at-Arms"),
         "MANGONEL": (1, "dispenser", "Mangonel"),
         "MANGUDAI": (0, "skeleton_horse_spawn_egg", "Mangudai"),
         "MONK": (0, "evoker_spawn_egg", "Monk"),
         "PADDED_ARCHER_ARMOR": (3, "book", "Padded Archer Armor"),
         "REDEMPTION": (3, "book", "Redemption"),
         "SAMURAI": (0, "zombie_spawn_egg", "Samurai"),
         "SANCTITY": (2, "book", "Sanctity"),
         "SCALE_BARDING_ARMOR": (4, "book", "Scale Barding Armor"),
         "SCALE_MAIL_ARMOR": (1, "book", "Scale Mail Armor"),
         "SCORPION": (2, "crossbow", "Scorpion"),
         "SIEGE_TOWER": (6, "ladder", "Siege Tower"),               # after the slots of the upgrades
         "STONE_MINING": (1, "book", "Stone Mining"),
         "TEUTONIC_KNIGHT": (0, "zombie_spawn_egg", "Teutonic Knight"),
         "THROWING_AXEMAN": (0, "drowned_spawn_egg", "Throwing Axeman"),
         "TRADE_CART": (0, "donkey_spawn_egg", "Trade Cart"),
         "TREBUCHET": (1, "minecart", "Trebuchet"),                 # after the unique unit
         "WAR_ELEPHANT": (0, "ravager_spawn_egg", "War Elephant"),
         "FEUDAL_AGE": (2, "bell", "Feudal Age"),
         "WHEELBARROW": (3, "book", "Wheelbarrow"),
         "WOAD_RAIDER": (0, "zombie_spawn_egg", "Woad Raider")}
# The AoE2 help text of each menu item, short (#1160): the plugin shows it as the last lore line of the item (help()).
HELP = {"ARCHER": "Ranged. Strong vs. infantry; weak vs. skirmishers.",
        "BATTERING_RAM": "Siege. Strong vs. buildings; weak vs. melee.",
        "BERSERK": "Viking infantry. Heals itself.",
        "BLOODLINES": "Cavalry +20 HP.",
        "CAPPED_RAM": "Siege. Strong vs. buildings; weak vs. melee.",
        "CAPPED_RAM_UPGRADE": "Upgrades battering rams to capped rams.",
        "CARAVAN": "Trade carts +20 % speed.",
        "CASTLE_AGE": "Advance to the Castle Age.",
        "CATAPHRACT": "Byzantine cavalry. Strong vs. infantry.",
        "CHAIN_BARDING_ARMOR": "Cavalry +1 melee armor, +1 pierce armor.",
        "CHAIN_MAIL_ARMOR": "Infantry +1 melee armor, +1 pierce armor.",
        "CHU_KO_NU": "Chinese archer. Shoots many arrows.",
        "DOUBLE_BIT_AXE": "Villagers chop wood 20 % faster.",
        "FEUDAL_AGE": "Advance to the Feudal Age.",
        "FERVOR": "Monks +15 % speed.",
        "FISHING_SHIP": "Gathers food from fish.",
        "FLETCHING": "Archers, towers, town center +1 attack, +1 range.",
        "FORGING": "Infantry and cavalry +1 attack.",
        "FORTIFIED_WALL": "Stone walls +1,200 HP, +4/+2 armor; also gates.",
        "GOLD_MINING": "Villagers mine gold 15 % faster.",
        "GUARD_TOWER": "Watch towers +480 HP, +2 attack, +1/+1 armor.",
        "GUILDS": "Market trading fee 15 %.",
        "HEAVY_SCORPION": "Siege. Shoots bolts; weak vs. cavalry.",
        "HEAVY_SCORPION_UPGRADE": "Upgrades scorpions to heavy scorpions.",
        "HORSE_COLLAR": "Farms +75 food.",
        "HUSKARL": "Gothic infantry. Strong vs. archers.",
        "IMPERIAL_AGE": "Advance to the Imperial Age.",
        "JANISSARY": "Turkish gunner. Strong vs. infantry.",
        "KEEP": "Guard towers +750 HP, +1 attack, +1/+1 armor.",
        "LEATHER_ARCHER_ARMOR": "Archers +1 melee armor, +1 pierce armor.",
        "LONGBOWMAN": "Briton archer. Long range.",
        "LOOM": "Villagers +15 HP, +1/+2 armor.",
        "MAMELUKE": "Saracen camel. Strong vs. cavalry.",
        "MAN_AT_ARMS": "Infantry. Strong vs. eagles, buildings.",
        "MAN_AT_ARMS_UPGRADE": "Upgrades militia to man-at-arms.",
        "MANGONEL": "Siege. Hits all units near the target.",
        "MANGUDAI": "Mongol horse archer. Strong vs. siege.",
        "MILITIA": "Infantry. Strong vs. eagles; weak vs. archers.",
        "MONK": "Heals own units, converts enemy units.",
        "ONAGER": "Siege. Hits all units near the target.",
        "ONAGER_UPGRADE": "Upgrades mangonels to onagers.",
        "PADDED_ARCHER_ARMOR": "Archers +1 melee armor, +1 pierce armor.",
        "REDEMPTION": "Monks convert siege and most buildings.",
        "SAMURAI": "Japanese infantry. Strong vs. unique units.",
        "SANCTITY": "Monks +15 HP.",
        "SCALE_BARDING_ARMOR": "Cavalry +1 melee armor, +1 pierce armor.",
        "SCALE_MAIL_ARMOR": "Infantry +1 melee armor, +1 pierce armor.",
        "SCORPION": "Siege. Shoots bolts; weak vs. cavalry.",
        "SIEGE_TOWER": "Siege. Carries 10 infantry, archers or villagers.",
        "SCOUT_CAVALRY": "Fast. Strong vs. monks, siege; weak vs. spears.",
        "SIEGE_ENGINEERS": "Siege +1 range, +20 % attack vs. buildings.",
        "SIEGE_ONAGER": "Siege. Hits all units near the target.",
        "SIEGE_ONAGER_UPGRADE": "Upgrades onagers to siege onagers.",
        "SIEGE_RAM": "Siege. Strong vs. buildings; weak vs. melee.",
        "SIEGE_RAM_UPGRADE": "Upgrades capped rams to siege rams.",
        "SKIRMISHER": "Strong vs. archers, spears; weak vs. cavalry.",
        "SPEARMAN": "Strong vs. cavalry; weak vs. archers.",
        "STONE_MINING": "Villagers mine stone 15 % faster.",
        "TEUTONIC_KNIGHT": "Teutonic infantry. Slow, strong armor.",
        "THROWING_AXEMAN": "Frankish infantry. Melee attack at range.",
        "TRADE_CART": "Brings gold from a second own market.",
        "TREBUCHET": "Siege. Long range vs. buildings; unpacks to shoot.",
        "VILLAGER_MALE": "Gathers, builds and repairs.",
        "WAR_ELEPHANT": "Persian elephant. Slow, very strong.",
        "WHEELBARROW": "Villagers +10 % speed, +25 % carry.",
        "WOAD_RAIDER": "Celtic infantry. Fast."}
SHIFT = 5                                                          # units of a shift click, as in AoE2
RALLY = (8, "white_banner", "Rally point", "Click, then right click the ground")   # last slot of the first row
MARK = 17.0                                                        # AoE2 seconds of the rally marker: 10 s at Normal
ROW = 9                                                            # the first slot of the queue row of the menu (#706)


def melee(s):
    """True for the combat values s of an infantry or cavalry unit (also camels and elephants): the units of the melee
    attack upgrades of the AoE2 blacksmith. Cavalry archers get the archer upgrades."""
    return bool({"infantry", "cavalry", "camel", "elephant"} & set(s.classes)) and "archer" not in s.classes


def barding(s):
    """True for the combat values s of a cavalry unit (also camels and elephants): the units of the barding armor
    upgrades of the AoE2 blacksmith. Cavalry archers get the archer armor upgrades. A mounted unit keeps its values
    on the horse (its UUID in aoe2mc.json), so the horse gets the armor (#850)."""
    return bool({"cavalry", "camel", "elephant"} & set(s.classes)) and "archer" not in s.classes


def unlocked(g, name):
    """True when the player has the age of technology name (TECH_AGE). As in AoE2, the menu shows a technology only
    from its age, but a building or unit of a later age as a gray item (build.locked), and never one that the
    civilization of the player does not have (civs.MISSING)."""
    return TECH_AGE.get(name, 0) <= build.ages(g) and AFTER.get(name, "") in {""} | set(getattr(g, "techs", ())) \
        and not (hasattr(g, "data") and civs.civ(g) in civs.MISSING.get(name, ()))   # not of this civilization (#1373)


def homes(g):
    """{block footprint (x0, x1, z0, z1): building name} of the complete own buildings that train units (TRAINS):
    the start ones and the built ones."""
    out = {(x0, x1, z0, z1): o["name"] for o in g.data["objects"] if o["kind"] == "building" and o["name"] in TRAINS
           and o["player"] == g.player for x0, z0, x1, z1 in [o["footprint"]]}
    return out | {tuple(s["footprint"]): s["name"] for s in g.sites if s["name"] in TRAINS and s.get("done")}


def trains(g, building):
    """The units and technologies of the own building: a castle trains the unique unit of the player's civilization."""
    if building != "CASTLE":
        new = {old: unit for t, (old, unit) in UPGRADES.items() if t in g.techs}     # the barracks trains the new unit
        out = list(TRAINS[building])
        for _ in UPGRADES:                                         # a line of upgrades: mangonel, onager, siege onager
            out = [new.get(n, n) for n in out]
        return tuple(out)
    return tuple(n for n in [UNIQUE.get(civs.civ(g))] if n in COSTS) + TRAINS[building]


def home(g, cell):
    """The footprint of the own training building that has the block cell (x, z) in it, or None."""
    return next((r for r in homes(g) if cell and r[0] <= cell[0] < r[1] and r[2] <= cell[1] < r[3]), None)


def lore(g):
    """Send the help line of each menu item to the plugin (#1160), also for its gray item of a later age. Sorted: the
    gray "Man-at-Arms" is the upgrade (the unit is never gray), so the help of the upgrade comes last."""
    for name in sorted(HELP):
        for material in (ITEMS[name][1], build.LOCKED):
            menu.lore(g, material, ITEMS[name][2], HELP[name])


def open_menu(g, player, cell):
    """Open the menu of the own training building at the block cell (x, z) for player. Returns its footprint, or None."""
    rect = home(g, cell)
    if rect is not None:
        show(g, player, rect)
    return rect


def show(g, player, rect):
    """Show (or refresh) the menu of the building rect: one item per unit, with its cost, time and queue. The second
    row shows the queue (#706): one item per group of the same unit (groups(), item count: the units), the first one
    with its progress; a click on it cancels a unit (cancel())."""
    n, building = len(g.queues.get(rect, [])), homes(g)[rect]
    def state(name):
        if need := build.locked(g, name):                              # a unit of a later age: a gray item (#674)
            return need
        if name in TECHS:
            return missing(g, name) or ("researching" if queued(g, name) else "research")
        return f"queue {n}/{QUEUE}"
    items = [(slot, build.LOCKED if build.locked(g, name) else item, label,
              (" · ".join(f"{v} {r}" for r, v in price(g, name).items()) or "free") + f" · {TRAIN_TIMES[name]} s · "
              + state(name))
             for name in trains(g, building) if repeatable(g, name) and unlocked(g, name) for slot, item, label in [ITEMS[name]]]
    items += [RALLY] if units_of(building) else []
    items += [garrison.UNGARRISON] if getattr(g, "garrisons", {}).get(rect) else []   # only with units inside (#808)
    if building == "MARKET":                                           # the buy and sell rows under the queue (#1286)
        import market                                                  # only for a market
        items += [(market.ROW + slot, *item) for slot, *item in market.items(g)]
    q = g.queues.get(rect, [])                                         # the queue row first: the plugin sets the
    items = [(ROW + i, ITEMS[name][1], ITEMS[name][2] + (f" {int(100 * q[0]['progress'])} %" if start == 0 else ""),
              "Click: cancel 1", k) for i, (name, start, k) in enumerate(groups(q)[:ROW])] + items   # items by slot
    def click(p, slot, shift):
        if building == "MARKET" and slot >= market.ROW:
            market.order(g, p, slot - market.ROW, shift, lambda: show(g, p, rect))
        else:
            order(g, p, rect, slot, shift)
    click.rect, click.key = rect, shown(g, rect)                       # refresh() compares the key (#1335)
    menu.show(g, player, build.pretty(building), items, click)


def shown(g, rect):
    """What an open menu of the building rect shows of its queue: the groups and the progress of the first unit in
    10 % steps. refresh() shows the menu again only when it changes, so the RCON commands stay few (#1335)."""
    q = g.queues.get(rect, [])
    return tuple(groups(q)), int(10 * q[0]["progress"]) if q else 0


def refresh(g):
    """Show each open training menu again when its queue changed (a unit is done, 10 % more progress, #1335)."""
    for player, handler in list(getattr(g, "menus", {}).items()):
        rect = getattr(handler, "rect", None)
        if rect in homes(g) and handler.key != shown(g, rect):
            show(g, player, rect)


def units_of(building):
    """The units (not the technologies) that building trains: only such a building has a rally point."""
    return [n for n in TRAINS[building] if n not in TECHS]


def groups(q):
    """The queue q as (name, index of the first, count) of the same unit next to each other."""
    out = []
    for i, e in enumerate(q):
        if out and out[-1][0] == e["name"]:
            out[-1] = (e["name"], out[-1][1], out[-1][2] + 1)
        else:
            out.append((e["name"], i, 1))
    return out


def cancel(g, player, rect, group):
    """Remove the last unit of queue group `group` (groups()) of the building rect and give back its full cost, as in
    AoE2 (also for the unit in training). Returns its name, or None."""
    q = g.queues.get(rect, [])
    gs = groups(q)
    if not 0 <= group < len(gs):
        return None
    name, start, k = gs[group]
    for r, v in q.pop(start + k - 1).get("paid", COSTS[name]).items():   # a free technology gives back nothing
        g.stock[r] += v
        g.command(f"scoreboard players add {r.capitalize()} {g.board} {v}")
    return name


def order(g, player, rect, slot, shift=False):
    """A click on the menu item in slot: queue 1 unit (a shift click: SHIFT, as many as the resources and the queue
    allow) at the building rect, or cancel a unit of the queue row (cancel()), and refresh the menu. Returns the
    number of queued units. A click on RALLY closes the menu: the next right click on the ground sets the rally point
    (gather.Gather.click calls rally())."""
    if slot == RALLY[0] and units_of(homes(g)[rect]):
        g.rallying[player] = rect
        menu.close(g, player)
        g.command(f"tellraw {player} " + json.dumps({"text": "Right click the ground for the rally point.",
                                                      "color": "gray"}))
        return 0
    if slot == garrison.UNGARRISON[0] and getattr(g, "garrisons", {}).get(rect):   # all units come out (#808)
        garrison.out(g, rect)
        show(g, player, rect)
        return 0
    if slot >= ROW:
        cancel(g, player, rect, slot - ROW)
        show(g, player, rect)
        return 0
    name = next((n for n in trains(g, homes(g)[rect])                # the shown item of the slot (one per line of upgrades)
                 if ITEMS[n][0] == slot and repeatable(g, n) and unlocked(g, n)), None)
    n = 0
    while name and n < (SHIFT if shift else 1) and queue(g, player, rect[::2], name):
        n += 1
    show(g, player, rect)
    return n


def rally(g, rect, cell, tile=None):
    """Set the rally point of the own building rect at the block cell (x, z); tile: the tree, bush, mine or farm tile
    there, or None. A banner in the player color and the text "Rally point" show it for MARK AoE2 seconds."""
    g.rally[rect] = cell, tile
    tag, (x, z) = f"aoe2mc.rally.{rect[0]}.{rect[2]}", cell
    y, color = g.map.y(x, z), g.players.get(str(g.player), {}).get("color", "white")
    g.command(f"kill @e[tag={tag}]")                                   # the marker of the last point
    g.command(f'summon item_display {x + 0.5} {y + 0.7} {z + 0.5} {{item:{{id:"minecraft:{color}_banner",count:1}},'
              f'billboard:"vertical",Tags:["{tag}"]}}')
    g.command(f'summon text_display {x + 0.5} {y + 1.6} {z + 0.5} {{text:"Rally point",billboard:"center",'
              f'Tags:["{tag}"]}}')
    g.marks[tag] = MARK


def go(g, rect, uuid, name):
    """Send the new unit uuid (AoE2 unit name) of the building rect to its rally point, if it has one."""
    if rect not in g.rally:
        return
    (x, z), tile = g.rally[rect]
    if uuid not in g.villagers:                                        # a military unit walks with the plugin
        import ai                                                      # ai imports gather, gather imports this module
        ai.move(g, uuid, name, g.map.T, x + 0.5, g.map.y(x, z), z + 0.5, ai.NORMAL * speed(g, name))
    elif tile:
        g.send(tile, {uuid})
    else:
        g.go(g.villagers[uuid], "to_rally", {(x, z)} if g.map.free(x, z) else g.map.around({(x, z)}))


def queue(g, player, cell, name="VILLAGER_MALE"):
    """Queue unit name at the own building that has the block cell (x, z) in its footprint, and take its cost.
    Returns the footprint of the building, or None (no building there that trains name, a full queue, not enough
    resources)."""
    rect = home(g, cell)
    if rect is None or name not in trains(g, homes(g)[rect]):
        return None
    if name in TECHS and (not repeatable(g, name) or queued(g, name)) or not unlocked(g, name):   # a technology once
        return None
    if need := build.locked(g, name):                                  # a unit or an age of a later age (#674)
        build.say(g, player, f"{build.pretty(name)}: {need}.")
        return None
    if need := missing(g, name):
        build.say(g, player, f"{build.pretty(name)} {need}.")
        return None
    q = g.queues.setdefault(rect, [])
    if len(q) >= QUEUE:
        build.say(g, player, f"The queue is full ({QUEUE} units).")
        return None
    cost = price(g, name)
    if any(g.stock[r] < v for r, v in cost.items()):
        build.say(g, player, f"Not enough resources: a {build.pretty(name).lower()} costs "
                             + ", ".join(f"{v} {r}" for r, v in cost.items()) + ".")
        return None
    for r, v in cost.items():
        g.stock[r] -= v
        g.command(f"scoreboard players remove {r.capitalize()} {g.board} {v}")
    q.append({"name": name, "progress": 0.0, "player": player} | ({"paid": cost} if cost != COSTS[name] else {}))
    return rect


def count(g, t):
    """How often the player researched technology t: 0 or 1, more only with the cheat "going above and beyond" (#968)."""
    return (t in getattr(g, "techs", ())) + getattr(g, "repeats", {}).get(t, 0)


def repeatable(g, name):
    """True when the player can research technology name (again), and for each unit: a technology once, or REPEAT
    times with the cheat "going above and beyond" (#968; ages and unit upgrades stay once). The effects stack: stats()
    and the gather tables take count()."""
    return name not in g.techs or getattr(g, "beyond", False) and name not in REQUIRES and name not in UPGRADES \
        and name not in WALL_UPGRADES and count(g, name) < REPEAT


def price(g, name):
    """The cost of unit or technology name with the bonuses of the civilization (civs.COSTS, #1091); a technology is
    free with the cheat "tech tech one two free" (#968)."""
    return {} if name in TECHS and getattr(g, "free_techs", False) else civs.cost(g, name, COSTS[name])


def queued(g, name):
    """True when a queue of the player has name in it."""
    return any(e["name"] == name for q in g.queues.values() for e in q)


def owned(g):
    """The names of the complete own buildings of the player: the start ones and the built ones."""
    return [o["name"] for o in g.data["objects"] if o["kind"] == "building" and o["player"] == g.player] + \
        [s["name"] for s in g.sites if s.get("done") and s["player"] == g.player]


def missing(g, name):
    """The text of the buildings that technology name still needs (REQUIRES), or None."""
    n, names, *alone = REQUIRES.get(name, (0, ()))
    has, alone = sorted(set(names) & set(owned(g))), alone[0] if alone else ()
    if len(has) < n and not set(alone) & set(owned(g)):
        return f"needs {''.join(f'a {build.pretty(b).lower()} or ' for b in alone)}{n} of {', '.join(build.pretty(b).lower() for b in names)} ({len(has)}/{n})"


def age(g):
    """The name of the age of the player."""
    return AGES[build.ages(g)]


def stats(g, name):
    """The combat values of AoE2 unit name with the bonuses of the civilization (civs.UNITS) and the technologies of
    the player (combat.stats and TECHS)."""
    import combat                                                  # combat imports gather, gather imports this module
    s = civs.units(g, name, combat.stats(name))
    for t in sorted(g.techs):
        for _ in range(count(g, t)):                                   # "going above and beyond" stacks (#968)
            s = TECHS[t](name, s)
    return s


def speed(g, name):
    """The factor of the walk speed of unit name: the bonus of the civilization (civs.speed) and the technologies of the
    player (SPEEDS: Fervor, #1261)."""
    return civs.speed(g, name) * math.prod(f ** count(g, t) for t, (unit, f) in SPEEDS.items() if unit == name)


def research(g, entry):
    """A technology is complete: keep it in g.techs and give the live villagers and military units the new values."""
    import combat, gather                                          # gather imports this module
    if entry["name"] in g.techs:                                   # a repeat: "going above and beyond" (#968)
        g.repeats[entry["name"]] = g.repeats.get(entry["name"], 0) + 1
    g.techs.add(entry["name"])
    if (more := gather.FARM_TECHS.get(entry["name"])):             # the new and the live own farms get more food
        g.map.farm_food += more
        for t in g.map.own_farms:
            if g.map.farms.get(t, 0) > 0:
                g.map.farms[t] += more
    if entry["name"] in WALL_UPGRADES:                             # the complete own walls become the new wall (#1326)
        for site in [s for s in g.sites if s["name"] in WALL_UPGRADES[entry["name"]] and s.get("done")
                     and s["player"] == g.player]:
            build.upgrade(g, site, combat.wall(site["name"], build.ages(g)))
    if entry["name"] in TOWER_UPGRADES:                            # the complete own towers get the new values (#1374)
        build.retower(g, g.techs - {entry["name"]})
    if entry["name"] in UPGRADES:                                  # the live units of the line get the new name
        old, new = UPGRADES[entry["name"]]
        for uuid in [u for u, n in g.soldiers.items() if n == old]:
            g.soldiers[uuid] = new
            g.command(combat.stats_command(uuid, new, stats(g, new)))
            if cmd := combat.range_command(uuid, new, g.map.T, s=stats(g, new)):   # the range and blast of an onager
                g.command(cmd)
            g.command(combat.label_command(uuid, new))               # the name of a new unit (units.pretty)
    for uuid, name in [(u["uuid"], u["name"]) for u in g.units if "uuid" in u] + list(g.soldiers.items()):
        if stats(g, name) != combat.stats(name):
            g.command(combat.stats_command(uuid, name, stats(g, name)))
        if stats(g, name).range != combat.stats(name).range:          # Fletching (#724)
            g.command(combat.range_command(uuid, name, g.map.T, s=stats(g, name)))
    if entry["name"] in SPEEDS:                                    # the live units walk faster (Fervor)
        import ai                                                  # ai imports gather, gather imports this module
        for uuid, name in g.soldiers.items():
            if name == SPEEDS[entry["name"]][0]:
                g.command(ai.speed_command(uuid, name, g.map.T, gather.NORMAL * speed(g, name)))
    if entry["name"] in REQUIRES:                                  # an age: all players see it, as in AoE2
        import ai                                                  # ai imports gather, gather imports this module
        for site in [s for s in g.sites if s["name"] in combat.WALLS and s.get("done") and s["player"] == g.player]:   # #1372
            build.upgrade(g, site, combat.wall(build.design(g, site["name"], g.player), build.ages(g) - 1), redraw=False)
        for uuid, name in g.soldiers.items():                      # the walk speed of the age (civs.UNITS, Celts)
            if civs.speed(g, name) != 1:
                g.command(ai.speed_command(uuid, name, g.map.T, gather.NORMAL * speed(g, name)))
        g.command(f"title @a[team=p{g.player}] title " + json.dumps({"text": age(g), "color": "gold"}))  # the own team only
        g.command("tellraw @a " + json.dumps({"text": f"Player {g.player} advances to the {age(g)}.", "color": "gold"}))
        g.command("playsound minecraft:ui.toast.challenge_complete master @a ~ ~ ~ 1 1 1")
        return
    g.command(f"tellraw {entry['player']} " + json.dumps({"text": f"{ITEMS[entry['name']][2]} is researched.",
                                                          "color": "green"}))


def limit(g):
    """The population limit: 5 per complete own town center and house, 20 per castle, at most max_pop()."""
    return min(max_pop(g), sum(HOUSING.get(n, 0) for n in owned(g)))


def max_pop(g):
    """The highest population limit: LIMIT, 1000 with the cheat "my cpu can handle it" (#968)."""
    return getattr(g, "pop_cap", None) or LIMIT


def census(g):
    """Count the live villagers and military units of the player (a dead unit has no position) and show the counts.
    A dead villager leaves g.villagers, the selection and its farm: the idle count and the bot see only live ones (#1039)."""
    live = g.positions(list(g.villagers) + list(g.soldiers))
    for u in [u for u in g.villagers if u not in live]:
        del g.villagers[u]
        g.selected.discard(u)
        for t in [t for t, f in g.farmers.items() if f == u]:
            del g.farmers[t]
    g.pop, g.census = len(live), 0.0
    sidebar(g)


LABELS = {"Limit": "Pop. limit"}                                  # the shown name of a sidebar line (owner, #990)


def sidebar(g):
    """Show the population and the limit as two lines of the sidebar (g.board) and the age in its title, only when
    they changed."""
    for name, n in (("Population", g.pop), ("Limit", limit(g))):
        if g.shown.get(name) != n:
            first, g.shown[name] = name not in g.shown, n
            g.command(f"scoreboard players set {name} {g.board} {n}")
            if first and name in LABELS:                               # a holder name has no space (#990)
                g.command(f"scoreboard players display name {name} {g.board} {json.dumps(LABELS[name])}")
    if g.shown.get("Age") != age(g):
        g.shown["Age"] = age(g)
        g.command(f'scoreboard objectives modify {g.board} displayname "Resources ({age(g)})"')


def tick(g, work):
    """Add work (AoE2 seconds) to the first unit of each queue; a unit that is complete appears. Returns the new
    units (spawn()). A unit starts only when the population and the started units are below the limit."""
    g.census += work
    if g.census >= CENSUS:
        census(g)
    for tag in list(g.marks):                                          # rally markers end
        g.marks[tag] -= work
        if g.marks[tag] <= 0:
            del g.marks[tag]
            g.command(f"kill @e[tag={tag}]")
    cap, out = limit(g), []
    room = cap - g.pop - sum(1 for q in g.queues.values() if q and q[0]["progress"] > 0 and q[0]["name"] not in TECHS)
    for rect, q in g.queues.items():
        if not q:
            continue
        if q[0]["progress"] == 0 and q[0]["name"] not in TECHS:      # a technology needs no population room
            if room <= 0:
                if not q[0].get("waits"):                              # as the "need more houses" message of AoE2
                    q[0]["waits"] = True
                    build.say(g, q[0]["player"], f"The population is at the limit ({g.pop}/{cap}): "
                              + ("build more houses." if cap < max_pop(g) else "no more units."))
                continue
            room -= 1
            q[0]["waits"] = False
        q[0]["progress"] += 1 if getattr(g, "aegis", False) else work / TRAIN_TIMES[q[0]["name"]]   # cheats.aegis
        if q[0]["progress"] >= 1 and q[0]["name"] in TECHS:
            research(g, q.pop(0))
        elif q[0]["progress"] >= 1 and (v := spawn(g, rect, q.pop(0)["name"])):
            out.append(v)
            g.pop += 1
    refresh(g)
    sidebar(g)
    return out


def spawn(g, rect, name):
    """Summon unit name on a free cell in front of the building rect (south side first, the middle first; the units
    take the cells one after the other) and add it to the villagers of g (a military unit: to g.soldiers, #654).
    Returns the gather.Villager, the UUID of a military unit, or None. A dock puts its ship on the water (fleet.spawn)."""
    if units.is_boat(units.classify(name)):
        import fleet                                                   # fleet imports this module
        return fleet.spawn(g, rect, name)
    cells = g.map.front(rect, "Passengers" in (units.classify(name) or {}))
    if not cells:
        return None
    k = g.trained[rect] = g.trained.get(rect, -1) + 1
    x, z = cells[k % len(cells)]
    uuid = summon(g, name, (x + 0.5, float(g.map.y(x, z)), z + 0.5))  # it faces south
    if uuid is None:
        return None
    go(g, rect, uuid, name)
    return g.villagers.get(uuid, uuid)


def summon(g, name, pos, rotation=math.pi / 2, player=None):
    """Summon unit name of g.player (or of another player) at pos with its AoE2 values, and add an own unit to
    g.soldiers (a military unit) or to the villagers of g. Returns its UUID, or None. Also for the transformation cheats
    (cheats.transform, #967) and the Stormy Dogs of Gaia (cheats.woof, #968)."""
    o = dict(name=name, player=g.player if player is None else player, rotation=rotation)
    players = {int(p): v for p, v in g.data.get("players", {}).items()}
    nbt = units.make_entity(o, players, pos, np.random.default_rng())  # a new random UUID
    if nbt is None:
        return None
    kind = str(nbt.pop("id"))
    del nbt["Pos"]
    uuid = units.uuid_str(nbt["UUID"])
    g.command(f"summon {kind} {pos[0]} {pos[1]} {pos[2]} {nbt.snbt()}")
    import combat, gather                                          # both import gather, gather imports this module
    g.command(combat.stats_command(uuid, name, stats(g, name)))
    if cmd := combat.range_command(uuid, name, g.map.T, s=stats(g, name)):   # an archer shoots from its range (#670)
        g.command(cmd)
    if cmd := combat.sight_command(uuid, name, g.map.T, s=stats(g, name)):   # it attacks enemies in sight (#775)
        g.command(cmd)
    import ai                                                      # ai imports gather, gather imports this module
    g.command(ai.speed_command(uuid, name, g.map.T, gather.NORMAL * speed(g, name)))   # also without an order (#849)
    if player not in (None, g.player):
        return uuid
    # they take move orders as a soldier (#1243, #1253); a ship sails with fleet.py (#1383)
    if gather.military(name) or name in ("MONK", "TRADE_CART") or units.is_boat(units.classify(name)):
        g.soldiers[uuid] = name
        return uuid
    g.villagers[uuid] = gather.Villager(uuid, pos)
    g.units.append({"kind": "unit", "name": name, "player": g.player, "uuid": uuid,
                    "tile": [math.floor(pos[0]) / g.map.T, math.floor(pos[2]) / g.map.T]})
    return uuid
