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
In the Castle Age (#1423, AFTER): Bow Saw (wood 20 % faster), Gold Shaft Mining and Stone Shaft Mining (15 % faster).
Fishing Lines at the dock in the Feudal Age and Gillnets (after it) in the Castle Age (#1439): fishing ships gather 10 %
faster and carry 5 more food (gather.SHIP_TECHS, fleet.rate, fleet.carry).
Horse Collar at the mill (#726): the live and the new farms of the player have 75 more food (gather.FARM_TECHS).
Crop Rotation at the mill in the Imperial Age, after Heavy Plow (#1578): the farms have 175 more food (FARM_TECHS).
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
The barracks researches Squires in the Castle Age (#1415): all infantry of the player walks 10 % faster (SPEEDS, a class).
It researches Arson in the Feudal Age (#1419): infantry gets +2 attack against the standard buildings (combat.STANDARD).
The university researches Fortified Wall in the Castle Age (#1326, WALL_UPGRADES): the new and the complete own stone
walls and gates get the fortified design and its AoE2 hit points and armor (build.design, build.upgrade).
An age gives the complete own walls and gates the AoE2 hit points of the new age (#1372, combat.WALLS, build.upgrade).
It researches Guard Tower in the Castle Age and Keep (after Guard Tower) in the Imperial Age (#1374, TOWER_UPGRADES):
the new and the complete own watch towers get the AoE2 hit points, attack and armor of the guard tower or the keep
(build.line, build.retower). The look of the tower stays.
It researches Shipwright in the Imperial Age (#1490, SHIPWRIGHT): the ships of the dock cost 20 % less wood (price())
and train 54 % faster (tick()); the technologies of the dock do not change.
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

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "train.jsonl")


def load(path=DATA):
    """The items of the menus: one JSON object per line (#1702). A new item is one new line, so parallel tickets
    do not conflict (`merge=union` in .gitattributes). Two lines of one name (both sides of a merge changed it)
    stop the import."""
    rows = [json.loads(s) for s in open(path, encoding="utf-8") if s.strip()]
    names = [r["name"] for r in rows]
    twice = sorted({n for n in names if names.count(n) > 1})
    if twice:
        raise ValueError(f"{path}: more than one line for {', '.join(twice)}")
    return rows


ROWS = load()                                                      # one line per item: data/train.jsonl (#1702)
COSTS = {r["name"]: r["cost"] for r in ROWS}                       # as in AoE2
TRAIN_TIMES = {r["name"]: r["time"] for r in ROWS}                 # AoE2 seconds
TRAINS = {b: tuple(r["name"] for r in ROWS if r["building"] == b)    # the units and technologies of each
          for b in dict.fromkeys(r["building"] for r in ROWS if r["building"])}   # building, in file order
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
          "BENGALIS": "RATHA", "GURJARAS": "CHAKRAM_THROWER", "ROMANS": "CENTURION", "ARMENIANS": "COMPOSITE_BOWMAN",
          "GEORGIANS": "MONASPA"}
build.AGE |= dict.fromkeys(UNIQUE.values(), 2) | dict.fromkeys(("ELITE_" + n for n in UNIQUE.values()), 3)   # (#1082)


def own_civ_only():
    """{name: the other civs} of each unique unit with an elite upgrade in COSTS, its elite unit and its upgrade: only
    the own civ has them (civs.MISSING). A new unique unit needs no line in civs.py, and its elite upgrade has
    `"building": null` in data/train.jsonl: trains() adds it to the castle of the own civ (#1760)."""
    others = set().union(*civs.MISSING.values()) | set(UNIQUE)
    return {n: tuple(sorted(others - {c})) for c, u in UNIQUE.items() if f"ELITE_{u}_UPGRADE" in COSTS
            for n in (u, "ELITE_" + u, f"ELITE_{u}_UPGRADE")}


civs.MISSING |= own_civ_only()
MILITIA_LINE = ("MILITIA", "MAN_AT_ARMS", "LONG_SWORDSMAN", "TWO_HANDED_SWORDSMAN", "CHAMPION",   # Gambesons (#1420)
                "FIRE_LANCER", "ELITE_FIRE_LANCER")


def chemistry(name, s):
    """Chemistry (AoE2 DE, wiki): +1 attack for archers, ranged siege units and buildings that shoot, not for gunpowder
    units (#1506). A building gets it when it is complete (build.target, build.values)."""
    shoots = "archer" in s.classes or "siege" in s.classes and s.range > 0 or "building" in s.classes and s.attack > 0
    shoots = shoots and "gunpowder" not in s.classes
    return s._replace(attack=s.attack + 1) if shoots else s


def fletching(name, s):
    """Fletching, Bodkin Arrow and Bracer (AoE2 DE, wiki): archers and the buildings that shoot +1 attack and +1 range, the town
    center +1 attack only (#1408). A complete building gets it at once (build.retower), a new one when it is complete."""
    if "archer" in s.classes or "building" in s.classes and s.attack > 0:
        return s._replace(attack=s.attack + 1, range=s.range + (name != "TOWN_CENTER"))
    return s


def thumb(name, s):
    """Thumb Ring (AoE2 DE, wiki): the archers fire faster; not the skirmishers (only their accuracy) and not the
    gunpowder units."""
    return "archer" in s.classes and "gunpowder" not in s.classes and "SKIRMISHER" not in name


def parthian(name, s):
    """Parthian Tactics (AoE2 DE, wiki): the mounted archers (also the Arambai), not the Genitour."""
    return "archer" in s.classes and bool({"cavalry", "camel", "elephant"} & set(s.classes)) and "GENITOUR" not in name


def engineers(name, s):
    """Siege Engineers (AoE2 DE, wiki): a siege unit +20 % bonus attack against buildings (rounded), a ranged one
    +1 range."""
    if "siege" not in s.classes:
        return s
    bonus = {**s.bonus, "building": round(s.bonus["building"] * 1.2)} if "building" in s.bonus else s.bonus
    return s._replace(range=s.range + (s.range > 0), bonus=bonus)


def masonry(name, s):
    """Masonry (AoE2 DE, wiki): a building +10 % hit points, +1 melee and +1 pierce armor; not the walls and gates
    (combat.WALLS) and not the farms and fish traps (no building Stats). The +3 building armor against the bonus damage
    of siege units and ships is not in the damage rule (combat.damage)."""
    import combat                                                  # combat imports gather, gather imports this module
    wall = name in combat.WALLS or name.endswith(("_WALL", "_GATE"))
    return s._replace(hp=round(s.hp * 1.1), melee=s.melee + 1, pierce=s.pierce + 1) if "building" in s.classes and not wall else s


def arrowslits(name, s):
    """Arrowslits (AoE2 DE, wiki): a watch tower +1, a guard tower +2 and a keep +3 attack. name: the tower of its
    values (build.line)."""
    return s._replace(attack=s.attack + ARROWSLITS[name]) if name in ARROWSLITS else s

TECHS = {"ARBALESTER_UPGRADE": lambda name, s: s,                  # a new unit name: UPGRADES
         "ARCHITECTURE": masonry,                                  # the same effect as Masonry (#1504)
         "ARROWSLITS": arrowslits,                                 # the towers of the player: build.values
         "ARSON": lambda name, s: s._replace(bonus={**s.bonus, "standard": s.bonus.get("standard", 0) + 2})
         if "infantry" in s.classes else s,                        # combat.STANDARD: not the walls (#1419)
         "ATONEMENT": lambda name, s: s,                           # monks convert enemy monks: monk.convertible
         "BLOODLINES": lambda name, s: s._replace(hp=s.hp + 20) if "cavalry" in s.classes else s,
         "BALLISTICS": lambda name, s: s,                          # the aim of the arrows: aoe ballistics (#1549)
         "BANKING": lambda name, s: s,                             # the tribute fee: diplomacy.FEES
         "BLAST_FURNACE": lambda name, s: s._replace(attack=s.attack + 2) if melee(s) or name in HULKS else s,
         "BLOCK_PRINTING": lambda name, s: s,                      # the conversion range: monk.near
         "BOMBARD_TOWER_TECH": lambda name, s: s,                  # the bombard tower in the build menu: build.NEEDS
         "BOW_SAW": lambda name, s: s,                             # an economy technology: gather.WORK_TECHS
         "BRACER": fletching,
         "BODKIN_ARROW": fletching,
         "CAPPED_RAM_UPGRADE": lambda name, s: s,                  # a new unit name: UPGRADES
         "CARAVAN": lambda name, s: s,                             # the walk speed: SPEEDS
         "CAVALIER_UPGRADE": lambda name, s: s,                    # a new unit name: UPGRADES
         "CASTLE_AGE": lambda name, s: s._replace(attack=s.attack + 3, bonus={**s.bonus, "cavalry": 2, "camel": 1,
                                                                            "ship": 1})
         if name == "EAGLE_SCOUT" else s,                          # an age: REQUIRES; the eagle scout (#1555)
         "CAREENING": lambda name, s: s._replace(pierce=s.pierce + 1) if ship(name, s) else s,
         "CHAMPION_UPGRADE": lambda name, s: s,                    # a new unit name: UPGRADES
         "CHEMISTRY": chemistry,
         "COINAGE": lambda name, s: s,                             # the tribute fee: diplomacy.FEES
         "CONSCRIPTION": lambda name, s: s,                        # the train speed: CONSCRIPT, tick()
         "CHAIN_BARDING_ARMOR": lambda name, s: s._replace(melee=s.melee + 1, pierce=s.pierce + 1)
         if barding(s) else s,
         "CHAIN_MAIL_ARMOR": lambda name, s: s._replace(melee=s.melee + 1, pierce=s.pierce + 1)
         if "infantry" in s.classes else s,
         "CROP_ROTATION": lambda name, s: s,                       # an economy technology: gather.FARM_TECHS
         "CROSSBOWMAN_UPGRADE": lambda name, s: s,
         "DEVOTION": lambda name, s: s,                            # the conversion resistance: monk.resist
         "DOUBLE_BIT_AXE": lambda name, s: s,                      # an economy technology: gather.WORK_TECHS
         "DRY_DOCK": lambda name, s: s._replace(pierce=s.pierce + 1) if ship(name, s) else s,
         "EAGLE_WARRIOR_UPGRADE": lambda name, s: s,               # a new unit name: UPGRADES
         "ELITE_ARAMBAI_UPGRADE": lambda name, s: s,               # a new unit name: UPGRADES
         "ELITE_BALLISTA_ELEPHANT_UPGRADE": lambda name, s: s,    # a new unit name: UPGRADES
         "ELITE_BATTLE_ELEPHANT_UPGRADE": lambda name, s: s,       # a new unit name: UPGRADES
         "ELITE_BOYAR_UPGRADE": lambda name, s: s,                 # a new unit name: UPGRADES
         "ELITE_CAMEL_ARCHER_UPGRADE": lambda name, s: s,          # a new unit name: UPGRADES
         "ELITE_CANNON_GALLEON_UPGRADE": lambda name, s: s,        # a new unit name: UPGRADES
         "ELITE_CENTURION_UPGRADE": lambda name, s: s,             # a new unit name: UPGRADES
         "ELITE_CHAKRAM_THROWER_UPGRADE": lambda name, s: s,       # a new unit name: UPGRADES
         "ELITE_COUSTILLIER_UPGRADE": lambda name, s: s,           # a new unit name: UPGRADES
         "ELITE_CONQUISTADOR_UPGRADE": lambda name, s: s,          # a new unit name: UPGRADES
         "ELITE_EAGLE_WARRIOR_UPGRADE": lambda name, s: s,
         "ELITE_GBETO_UPGRADE": lambda name, s: s,                 # a new unit name: UPGRADES
         "ELITE_GENITOUR_UPGRADE": lambda name, s: s,              # a new unit name: UPGRADES
         "ELITE_MAGYAR_HUSZAR_UPGRADE": lambda name, s: s,        # a new unit name: UPGRADES
         "ELITE_GENOESE_CROSSBOWMAN_UPGRADE": lambda name, s: s,   # a new unit name: UPGRADES
         "ELITE_GHULAM_UPGRADE": lambda name, s: s,               # a new unit name: UPGRADES
         "ELITE_KARAMBIT_WARRIOR_UPGRADE": lambda name, s: s,      # a new unit name: UPGRADES
         "ELITE_KESHIK_UPGRADE": lambda name, s: s,                # a new unit name: UPGRADES
         "ELITE_OBUCH_UPGRADE": lambda name, s: s,                 # a new unit name: UPGRADES
         "ELITE_SERJEANT_UPGRADE": lambda name, s: s,              # a new unit name: UPGRADES
         "ELITE_SHRIVAMSHA_RIDER_UPGRADE": lambda name, s: s,      # a new unit name: UPGRADES
         "ELITE_STEPPE_LANCER_UPGRADE": lambda name, s: s,         # a new unit name: UPGRADES
         "ELITE_SKIRMISHER_UPGRADE": lambda name, s: s,
         "ELITE_TARKAN_UPGRADE": lambda name, s: s,               # a new unit name: UPGRADES
         "ELITE_URUMI_SWORDSMAN_UPGRADE": lambda name, s: s,                # a new unit name: UPGRADES
         "FAITH": lambda name, s: s,                               # the conversion resistance: monk.resist
         "FERVOR": lambda name, s: s,                              # the walk speed: SPEEDS
         "FISHING_LINES": lambda name, s: s,                       # the fishing ships: gather.SHIP_TECHS
         "FLETCHING": fletching,
         "FORGING": lambda name, s: s._replace(attack=s.attack + 1) if melee(s) or name in HULKS else s,
         "FORTIFIED_WALL": lambda name, s: s,                      # the walls of the player: WALL_UPGRADES
         "GAMBESONS": lambda name, s: s._replace(pierce=s.pierce + 1) if name in MILITIA_LINE else s,
         "GILLNETS": lambda name, s: s,                            # the fishing ships: gather.SHIP_TECHS
         "GOLD_MINING": lambda name, s: s,                         # an economy technology: gather.WORK_TECHS
         "GOLD_SHAFT_MINING": lambda name, s: s,
         "GUARD_TOWER": lambda name, s: s,                         # the towers of the player: TOWER_UPGRADES
         "GUILDS": lambda name, s: s,                              # the trading fee: market.FEES
         "HALBERDIER_UPGRADE": lambda name, s: s,                  # a new unit name: UPGRADES
         "HAND_CART": lambda name, s: s,                           # no combat change: gather.CARRY and gather.PACE
         "HEATED_SHOT": lambda name, s: s._replace(bonus={**s.bonus, "ship": s.bonus.get("ship", 0) + HEATED[name]})
         if name in HEATED else s,                                 # the arrows of the own towers on ships (#1548)
         "HEAVY_CAMEL_RIDER_UPGRADE": lambda name, s: s,           # a new unit name: UPGRADES
         "HEAVY_CAVALRY_ARCHER_UPGRADE": lambda name, s: s,        # a new unit name: UPGRADES
         "HOARDINGS": lambda name, s: s._replace(hp=round(s.hp * 1.21)) if name == "CASTLE" else s,   # build.values
         "HEAVY_PLOW": lambda name, s: s,                          # an economy technology: gather.FARM_TECHS, FOOD_CARRY
         "HEAVY_SCORPION_UPGRADE": lambda name, s: s,
         "HERESY": lambda name, s: s,                              # a converted unit dies: monk.heresy
         "HEAVY_WARSHIPS": lambda name, s: s,                      # new unit names: UPGRADES
         "HERBAL_MEDICINE": lambda name, s: s,                     # the heal in a garrison: garrison.heal
         "HEAVY_DEMOLITION_SHIP_UPGRADE": lambda name, s: s,
         "DEMOLITION_SHIP_UPGRADE": lambda name, s: s,
         "HORSE_COLLAR": lambda name, s: s,                        # an economy technology: gather.FARM_TECHS
         "HUSBANDRY": lambda name, s: s,                           # the walk speed: SPEEDS
         "HUSSAR_UPGRADE": lambda name, s: s,                      # a new unit name: UPGRADES
         "ILLUMINATION": lambda name, s: s,                        # the rest after a conversion: monk.ILLUMINATED
         "IMPERIAL_AGE": lambda name, s: s,                        # an age: REQUIRES
         "IMPERIAL_SKIRMISHER_UPGRADE": lambda name, s: s,         # a new unit name: UPGRADES
         "IRON_CASTING": lambda name, s: s._replace(attack=s.attack + 1) if melee(s) or name in HULKS else s,
         "KEEP": lambda name, s: s,                                # the towers of the player: TOWER_UPGRADES
         "LEATHER_ARCHER_ARMOR": lambda name, s: s._replace(melee=s.melee + 1, pierce=s.pierce + 1)
         if "archer" in s.classes else s,
         "LIGHT_CAVALRY_UPGRADE": lambda name, s: s,
         "LONG_SWORDSMAN_UPGRADE": lambda name, s: s,
         "LOOM": lambda name, s: s._replace(hp=s.hp + 15, melee=s.melee + 1, pierce=s.pierce + 2)
         if "VILLAGER" in name else s,
         "MAN_AT_ARMS_UPGRADE": lambda name, s: s,                 # a new unit name: UPGRADES
         "MASONRY": masonry,                                       # the buildings of the player: build.values
         "MEDIUM_WARSHIPS": lambda name, s: s,                     # new unit names: UPGRADES
         "MURDER_HOLES": lambda name, s: s,                        # no minimum range: build.minimum
         "ONAGER_UPGRADE": lambda name, s: s,
         "PALADIN_UPGRADE": lambda name, s: s,                     # a new unit name: UPGRADES
         "PADDED_ARCHER_ARMOR": lambda name, s: s._replace(melee=s.melee + 1, pierce=s.pierce + 1)
         if "archer" in s.classes else s,
         "PARTHIAN_TACTICS": lambda name, s: s._replace(melee=s.melee + 1, pierce=s.pierce + 2,
                                                        bonus={**s.bonus, "spearman": s.bonus.get("spearman", 0) + 2})
         if parthian(name, s) else s,
         "PIKEMAN_UPGRADE": lambda name, s: s,
         "PLATE_BARDING_ARMOR": lambda name, s: s._replace(melee=s.melee + 1, pierce=s.pierce + 2)
         if barding(s) else s,
         "PLATE_MAIL_ARMOR": lambda name, s: s._replace(melee=s.melee + 1, pierce=s.pierce + 2)
         if "infantry" in s.classes else s,
         "REDEMPTION": lambda name, s: s,                          # monks convert buildings and siege: monk.py
         "RING_ARCHER_ARMOR": lambda name, s: s._replace(melee=s.melee + 1, pierce=s.pierce + 2)
         if "archer" in s.classes else s,
         "SCALE_BARDING_ARMOR": lambda name, s: s._replace(melee=s.melee + 1, pierce=s.pierce + 1)
         if barding(s) else s,
         "SANCTITY": lambda name, s: s._replace(hp=s.hp + 15) if name == "MONK" else s,
         "SAPPERS": lambda name, s: s._replace(bonus={**s.bonus, "building": s.bonus.get("building", 0) + 15,
                                                      "ram": s.bonus.get("ram", 0) + 3})
         if name.startswith("VILLAGER") else s,                    # the walls too: "building" is also stone defense
         "SCALE_MAIL_ARMOR": lambda name, s: s._replace(melee=s.melee + 1, pierce=s.pierce + 1)
         if "infantry" in s.classes else s,
         "SHIPWRIGHT": lambda name, s: s,                          # the ships: SHIPWRIGHT, price() and tick()
         "SIEGE_ENGINEERS": engineers,
         "SIEGE_ONAGER_UPGRADE": lambda name, s: s,
         "SIEGE_RAM_UPGRADE": lambda name, s: s,
         "SQUIRES": lambda name, s: s,                             # the walk speed: SPEEDS
         "STONE_MINING": lambda name, s: s,                        # an economy technology: gather.WORK_TECHS
         "STONE_SHAFT_MINING": lambda name, s: s,
         "THEOCRACY": lambda name, s: s,                           # one monk of a group rests: monk.convert
         "THUMB_RING": lambda name, s: s._replace(reload=round(s.reload / 1.1765, 3)) if thumb(name, s) else s,
         "TOWN_PATROL": lambda name, s: s,                         # the building sight: gather.seen_tiles
         "TOWN_WATCH": lambda name, s: s,                          # the building sight: gather.seen_tiles
         "TREADMILL_CRANE": lambda name, s: s,                     # the build speed: build.rise
         "TWO_HANDED_SWORDSMAN_UPGRADE": lambda name, s: s,        # a new unit name: UPGRADES
         "TWO_MAN_SAW": lambda name, s: s,                         # an economy technology: gather.WORK_TECHS
         "WINGED_HUSSAR_UPGRADE": lambda name, s: s,               # a new unit name: UPGRADES
         "FEUDAL_AGE": lambda name, s: s,   # the change of each technology to the AoE2 values
         "WHEELBARROW": lambda name, s: s}                         # no combat change: gather.CARRY and gather.PACE
SPEEDS = {"CARAVAN": ("trade units", 1.2),                        # technology: the unit (or a class of combat.STATS:
          "FERVOR": ("MONK", 1.15),                                # lower case, or a group of civs.GROUPS) and its
          "HUSBANDRY": ("mounted", 1.1),                           # walk speed factor; cavalry, camels, elephants (#1416)
          "SQUIRES": ("infantry", 1.1)}                            # (#1415)
SHIPWRIGHT = (0.8, 1.54)                                           # Shipwright: ships cost 80 % wood, train 54 % faster
FASTER = {"EAGLE_SCOUT": (2, 35)}                                  # unit: the age and its train time from it (#1555)
CONSCRIPT = (("ARCHERY_RANGE", "BARRACKS", "CASTLE", "STABLE"), 1.33)   # Conscription: these buildings train faster
ARROWSLITS = {"GUARD_TOWER": 2, "KEEP": 3, "WATCH_TOWER": 1}         # Arrowslits: the attack of each tower (#1504)
HEATED = {"BOMBARD_TOWER": 50, "CASTLE": 4, "DOCK": 4, "GUARD_TOWER": 9, "KEEP": 10,   # Heated Shot: attack against
          "WATCH_TOWER": 6}                 # ships (AoE2 DE wiki "Attack increase against ships", #1548)
UPGRADES = {                                                       # technology: the unit and its new unit (#941)
    "ARBALESTER_UPGRADE": ("CROSSBOWMAN", "ARBALESTER"),
    "DEMOLITION_SHIP_UPGRADE": ("DEMOLITION_RAFT", "DEMOLITION_SHIP"),   # (#1483)
    "CAPPED_RAM_UPGRADE": ("BATTERING_RAM", "CAPPED_RAM"),           # the siege upgrades of AoE2 DE (#1352)
    "CAVALIER_UPGRADE": ("KNIGHT", "CAVALIER"),
    "CHAMPION_UPGRADE": ("TWO_HANDED_SWORDSMAN", "CHAMPION"),
    "CROSSBOWMAN_UPGRADE": ("ARCHER", "CROSSBOWMAN"),
    "EAGLE_WARRIOR_UPGRADE": ("EAGLE_SCOUT", "EAGLE_WARRIOR"),        # (#1555)
    "ELITE_ARAMBAI_UPGRADE": ("ARAMBAI", "ELITE_ARAMBAI"),   # the castle of the Burmese (#1751)
    "ELITE_BALLISTA_ELEPHANT_UPGRADE": ("BALLISTA_ELEPHANT", "ELITE_BALLISTA_ELEPHANT"),   # the castle of the Khmer (#1752)
    "ELITE_BATTLE_ELEPHANT_UPGRADE": ("BATTLE_ELEPHANT", "ELITE_BATTLE_ELEPHANT"),   # (#1556)
    "ELITE_BOYAR_UPGRADE": ("BOYAR", "ELITE_BOYAR"),   # the castle of the Slavs (#1721)
    "ELITE_CAMEL_ARCHER_UPGRADE": ("CAMEL_ARCHER", "ELITE_CAMEL_ARCHER"),   # the castle of the Berbers (#1723)
    "ELITE_CANNON_GALLEON_UPGRADE": ("CANNON_GALLEON", "ELITE_CANNON_GALLEON"),
    "ELITE_CENTURION_UPGRADE": ("CENTURION", "ELITE_CENTURION"),   # the castle of the Romans (#1749)
    "ELITE_CHAKRAM_THROWER_UPGRADE": ("CHAKRAM_THROWER", "ELITE_CHAKRAM_THROWER"),   # the castle (#1624)
    "ELITE_COUSTILLIER_UPGRADE": ("COUSTILLIER", "ELITE_COUSTILLIER"),   # the castle of the Burgundians (#1753)
    "ELITE_CONQUISTADOR_UPGRADE": ("CONQUISTADOR", "ELITE_CONQUISTADOR"),   # the castle of the Spanish (#1744)
    "ELITE_EAGLE_WARRIOR_UPGRADE": ("EAGLE_WARRIOR", "ELITE_EAGLE_WARRIOR"),
    "ELITE_GBETO_UPGRADE": ("GBETO", "ELITE_GBETO"),   # the castle of the Malians (#1722)
    "ELITE_GENITOUR_UPGRADE": ("GENITOUR", "ELITE_GENITOUR"),   # (#1610)
    "ELITE_MAGYAR_HUSZAR_UPGRADE": ("MAGYAR_HUSZAR", "ELITE_MAGYAR_HUSZAR"),   # the castle of the Magyars (#1743)
    "ELITE_GENOESE_CROSSBOWMAN_UPGRADE": ("GENOESE_CROSSBOWMAN", "ELITE_GENOESE_CROSSBOWMAN"),   # the castle (#1724)
    "ELITE_GHULAM_UPGRADE": ("GHULAM", "ELITE_GHULAM"),   # the castle of the Hindustanis (#1756)
    "ELITE_KARAMBIT_WARRIOR_UPGRADE": ("KARAMBIT_WARRIOR", "ELITE_KARAMBIT_WARRIOR"),   # the castle of the Malay (#1750)
    "ELITE_KESHIK_UPGRADE": ("KESHIK", "ELITE_KESHIK"),   # the castle of the Tatars (#1745)
    "ELITE_OBUCH_UPGRADE": ("OBUCH", "ELITE_OBUCH"),   # the castle of the Poles (#1747)
    "ELITE_SERJEANT_UPGRADE": ("SERJEANT", "ELITE_SERJEANT"),   # the castle of the Sicilians (#1748)
    "ELITE_SHRIVAMSHA_RIDER_UPGRADE": ("SHRIVAMSHA_RIDER", "ELITE_SHRIVAMSHA_RIDER"),   # (#1612)
    "ELITE_SKIRMISHER_UPGRADE": ("SKIRMISHER", "ELITE_SKIRMISHER"),
    "ELITE_TARKAN_UPGRADE": ("TARKAN", "ELITE_TARKAN"),   # the castle of the Huns (#1726)
    "ELITE_STEPPE_LANCER_UPGRADE": ("STEPPE_LANCER", "ELITE_STEPPE_LANCER"),   # (#1557)
    "ELITE_URUMI_SWORDSMAN_UPGRADE": ("URUMI_SWORDSMAN", "ELITE_URUMI_SWORDSMAN"),   # the castle of the Dravidians (#1754)
    "HALBERDIER_UPGRADE": ("PIKEMAN", "HALBERDIER"),
    "HEAVY_CAMEL_RIDER_UPGRADE": ("CAMEL_RIDER", "HEAVY_CAMEL_RIDER"),   # (#1550)
    "HEAVY_CAVALRY_ARCHER_UPGRADE": ("CAVALRY_ARCHER", "HEAVY_CAVALRY_ARCHER"),
    "HEAVY_SCORPION_UPGRADE": ("SCORPION", "HEAVY_SCORPION"),
    "HEAVY_DEMOLITION_SHIP_UPGRADE": ("DEMOLITION_SHIP", "HEAVY_DEMOLITION_SHIP"),   # (#1483)
    "HEAVY_WARSHIPS": (("WAR_GALLEY", "GALLEON"), ("FIRE_SHIP", "FAST_FIRE_SHIP")),   # (#1483)
    "HUSSAR_UPGRADE": ("LIGHT_CAVALRY", "HUSSAR"),
    "IMPERIAL_SKIRMISHER_UPGRADE": ("ELITE_SKIRMISHER", "IMPERIAL_SKIRMISHER"),   # (#1611)
    "LIGHT_CAVALRY_UPGRADE": ("SCOUT_CAVALRY", "LIGHT_CAVALRY"),
    "LONG_SWORDSMAN_UPGRADE": ("MAN_AT_ARMS", "LONG_SWORDSMAN"),
    "MAN_AT_ARMS_UPGRADE": ("MILITIA", "MAN_AT_ARMS"),
    "MEDIUM_WARSHIPS": (("GALLEY", "WAR_GALLEY"), ("FIRE_GALLEY", "FIRE_SHIP"),   # two lines (#1482): lines()
                        ("HULK", "WAR_HULK")),                                 # (#1508)
    "ONAGER_UPGRADE": ("MANGONEL", "ONAGER"),
    "PALADIN_UPGRADE": ("CAVALIER", "PALADIN"),
    "PIKEMAN_UPGRADE": ("SPEARMAN", "PIKEMAN"),
    "SIEGE_ONAGER_UPGRADE": ("ONAGER", "SIEGE_ONAGER"),
    "SIEGE_RAM_UPGRADE": ("CAPPED_RAM", "SIEGE_RAM"),
    "TWO_HANDED_SWORDSMAN_UPGRADE": ("LONG_SWORDSMAN", "TWO_HANDED_SWORDSMAN"),
    "WINGED_HUSSAR_UPGRADE": ("LIGHT_CAVALRY", "WINGED_HUSSAR"),
}
AFTER = {r["name"]: r["after"] for r in ROWS if "after" in r}     # the technology before it in its slot
WALL_UPGRADES = {"FORTIFIED_WALL": {"STONE_WALL": "FORTIFIED_WALL", "GATE": "FORTIFIED_GATE"}}   # technology: {wall: new} (#1326)
TOWER_UPGRADES = {"GUARD_TOWER": {"WATCH_TOWER": "GUARD_TOWER"},   # technology: {tower: the tower of its values},
                  "KEEP": {"GUARD_TOWER": "KEEP", "WATCH_TOWER": "KEEP"}}   # in the research order (#1374)
REQUIRES = {"CASTLE_AGE": (2, ("ARCHERY_RANGE", "STABLE", "BLACKSMITH", "MARKET")),   # n types of these buildings
            "FEUDAL_AGE": (2, ("BARRACKS", "MILL", "LUMBER_CAMP", "MINING_CAMP", "DOCK")),
            "IMPERIAL_AGE": (2, ("MONASTERY", "UNIVERSITY", "SIEGE_WORKSHOP"), ("CASTLE",))}   # or one of these alone
TECH_AGE = {r["name"]: r["age"] for r in ROWS if "age" in r}       # the age of a technology (build.AGE)
AGES = ("Dark Age", "Feudal Age", "Castle Age", "Imperial Age")    # the age after each researched age (index: ages)
QUEUE = 15                                                         # units in the queue of one building, as in AoE2
HOUSING = {"TOWN_CENTER": 5, "HOUSE": 5, "CASTLE": 20}             # population of a complete building, as in AoE2
LIMIT = 200                                                        # the AoE2 population limit
REPEAT = 256                                                       # researches of one technology: "going above and beyond"
CENSUS = 2.0                                                       # AoE2 seconds between two counts of the live units
MORE = 18                                                          # the first slot of the item row under the queue row
ITEMS = {r["name"]: (r["slot"], r["item"], r["label"]) for r in ROWS}   # menu slot, item and name (#620)
# The AoE2 help text of each menu item, short (#1160): the plugin shows it as the last lore line of the item (help()).
HELP = {r["name"]: r["help"] for r in ROWS}                        # the help line of each item
SHIFT = 5                                                          # units of a shift click, as in AoE2
RALLY = (8, "white_banner", "Rally point", "Click, then right click the ground")   # last slot of the first row
MARK = 17.0                                                        # AoE2 seconds of the rally marker: 10 s at Normal
ROW = 9                                                            # the first slot of the queue row of the menu (#706)


HULKS = ("HULK", "WAR_HULK")                                       # melee warships: the blacksmith attack too (#1509)


def melee(s):
    """True for the combat values s of an infantry or cavalry unit (also camels and elephants): the units of the melee
    attack upgrades of the AoE2 blacksmith. Cavalry archers get the archer upgrades."""
    return bool({"infantry", "cavalry", "camel", "elephant"} & set(s.classes)) and "archer" not in s.classes


def barding(s):
    """True for the combat values s of a cavalry unit (also camels and elephants): the units of the barding armor
    upgrades of the AoE2 blacksmith. Cavalry archers get the archer armor upgrades. A mounted unit keeps its values
    on the horse (its UUID in aoe2mc.json), so the horse gets the armor (#850)."""
    return bool({"cavalry", "camel", "elephant"} & set(s.classes)) and "archer" not in s.classes


def ship(name, s):
    """True for the combat values s of ship name: the units of Careening and Dry Dock (#1441). The transport ship has
    no class "ship" in combat (the warships do not shoot at it), but it gets the armor too."""
    import combat                                                  # combat imports gather, gather imports this module
    return combat.SHIP in s.classes or name == "TRANSPORT_SHIP"


def unlocked(g, name):
    """True when the player has the age of technology name (TECH_AGE). As in AoE2, the menu shows a technology only
    from its age, but a building or unit of a later age as a gray item (build.locked), and never one that the
    civilization of the player does not have (civs.missing: also not as a team bonus of an ally, #1619)."""
    return TECH_AGE.get(name, 0) <= build.ages(g) and AFTER.get(name, "") in {""} | set(getattr(g, "techs", ())) \
        and not (hasattr(g, "data") and civs.missing(g, name)) \
        and (name not in UPGRADES or bool(lines(name, g)))         # not of this civilization (#1373), no new unit (#1483)


def homes(g):
    """{block footprint (x0, x1, z0, z1): building name} of the complete own buildings that train units (TRAINS):
    the start ones and the built ones."""
    out = {(x0, x1, z0, z1): o["name"] for o in g.data["objects"] if o["kind"] == "building" and o["name"] in TRAINS
           and o["player"] == g.player for x0, z0, x1, z1 in [o["footprint"]]}
    return out | {tuple(s["footprint"]): s["name"] for s in g.sites if s["name"] in TRAINS and s.get("done")}


def lines(t, g=None):
    """The (unit, new unit) pairs of upgrade technology t (UPGRADES): Medium Warships upgrades two lines (#1482). With g,
    only the new units that the civilization of the player has (civs.MISSING): Heavy Warships gives no fast fire ship
    to the Vikings (#1483)."""
    out = UPGRADES[t] if isinstance(UPGRADES[t][0], tuple) else (UPGRADES[t],)
    return tuple(p for p in out if g is None or not hasattr(g, "data") or not civs.missing(g, p[1]))


def trains(g, building):
    """The units and technologies of the own building: a castle trains the unique unit of the player's civilization."""
    new = {old: unit for t in UPGRADES if t in g.techs for old, unit in lines(t, g)}   # the barracks trains the new unit
    unique = [n for n in [UNIQUE.get(civs.civ(g))] if n in COSTS] * (building == "CASTLE")
    out = unique + list(TRAINS[building]) + [f"ELITE_{n}_UPGRADE" for n in unique if f"ELITE_{n}_UPGRADE" in COSTS]   # (#1760)
    for _ in UPGRADES:                                             # a line of upgrades: mangonel, onager, siege onager
        out = [new.get(n, n) for n in out]                         # the castle: the elite unique unit (#1624)
    return tuple(out)


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
              (" · ".join(f"{v} {r}" for r, v in price(g, name).items()) or "free") + f" · {seconds(g, name)} s · "
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
    if ROW <= slot < MORE:                                         # the queue row; MORE: more items (#1485)
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
    free with the cheat "tech tech one two free" (#968). Shipwright: a ship costs 20 % less wood (#1490)."""
    if name in TECHS and getattr(g, "free_techs", False):
        return {}
    cost = civs.cost(g, name, COSTS[name])
    if "wood" in cost and shipwright(g, name):
        cost["wood"] = int(cost["wood"] * SHIPWRIGHT[0] + 0.5)
    return cost


def shipwright(g, name):
    """True when name is a ship of the dock and the player researched Shipwright (#1490)."""
    return "SHIPWRIGHT" in getattr(g, "techs", ()) and name in units_of("DOCK")


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
    the player (combat.stats and TECHS), twice for civs.TWICE (#1561)."""
    import combat                                                  # combat imports gather, gather imports this module
    s, twice = civs.units(g, name, combat.stats(name)), civs.TWICE.get(civs.civ(g), ())
    for t in sorted(g.techs):
        for _ in range(count(g, t) * (1 + (t in twice))):              # "going above and beyond" stacks (#968)
            s = TECHS[t](name, s)
    return s


def seconds(g, name):
    """The train time of unit or technology name: TRAIN_TIMES, or the time of FASTER from its age (the eagle scout trains
    in 46 s in the Feudal Age and in 35 s from the Castle Age, AoE2 DE wiki)."""
    age, time = FASTER.get(name, (9, 0))
    return time if build.ages(g) >= age else TRAIN_TIMES[name]


def speed(g, name):
    """The factor of the walk speed of unit name: the bonus of the civilization (civs.speed) and the technologies of the
    player (SPEEDS: Fervor, #1261; Squires for the class infantry, #1415; Husbandry for the mounted units, #1416)."""
    return civs.speed(g, name) * math.prod(f ** count(g, t) for t, (unit, f) in SPEEDS.items() if faster(unit, name))


def faster(unit, name):
    """True when the SPEEDS entry unit (a unit name, a class of combat.STATS in lower case or a group of civs.GROUPS)
    covers unit name."""
    import combat                                                  # combat imports gather, gather imports this module
    s = combat.stats(name)
    return unit == name or unit in civs.GROUPS and civs.GROUPS[unit](name, s) or unit.islower() and unit in s.classes


def research(g, entry):
    """A technology is complete: keep it in g.techs and give the live villagers and military units the new values."""
    import combat, gather                                          # gather imports this module
    if entry["name"] in g.techs:                                   # a repeat: "going above and beyond" (#968)
        g.repeats[entry["name"]] = g.repeats.get(entry["name"], 0) + 1
    before = set(g.techs)
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
    build.retower(g, before)                                       # the complete own towers get the new values (#1374),
                                                                   # the buildings those of Masonry and Fletching (#1398, #1408)
    if entry["name"] == "BALLISTICS" and getattr(g, "paper", False):   # the plugin aims the arrows of the player (#1549)
        g.command(f"aoe ballistics p{g.player} on")
    if entry["name"] in UPGRADES:                                  # the live units of the line get the new name
        for uuid, new in [(u, new) for old, new in lines(entry["name"], g) for u, n in g.soldiers.items() if n == old]:
            g.soldiers[uuid] = new
            g.command(combat.stats_command(uuid, new, stats(g, new)))
            if cmd := combat.range_command(uuid, new, g.map.T, s=stats(g, new)):   # the range and blast of an onager
                g.command(cmd)
            g.command(combat.label_command(uuid, new))               # the name of a new unit (units.pretty)
    import trebuchet                                               # trebuchet imports this module: import it late
    for uuid, name in [(u["uuid"], u["name"]) for u in g.units if "uuid" in u] + list(g.soldiers.items()):
        if stats(g, name) != combat.stats(name):
            g.command(trebuchet.stats_command(g, uuid) if name == trebuchet.NAME   # the armor of its state (#1409)
                      else combat.stats_command(uuid, name, stats(g, name)))
        if name == trebuchet.NAME and trebuchet.state(g, uuid) != "unpacked":
            continue                                               # packed: range 0, the unpack sends the range (#1414)
        if stats(g, name).range != combat.stats(name).range:          # Fletching (#724)
            g.command(combat.range_command(uuid, name, g.map.T, s=stats(g, name)))
    if entry["name"] in SPEEDS:                                    # the live units walk faster (Fervor)
        import ai                                                  # ai imports gather, gather imports this module
        for uuid, name in g.soldiers.items():
            if faster(SPEEDS[entry["name"]][0], name):
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
    fast = {r for r, n in homes(g).items() if n in CONSCRIPT[0]} if "CONSCRIPTION" in g.techs else set()   # (#1455)
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
        rate = CONSCRIPT[1] if rect in fast and q[0]["name"] not in TECHS else 1   # units only, not technologies
        rate *= SHIPWRIGHT[1] if shipwright(g, q[0]["name"]) else 1          # the ships of a dock, not its technologies
        q[0]["progress"] += 1 if getattr(g, "aegis", False) else work * rate / seconds(g, q[0]["name"])   # cheats.aegis
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
