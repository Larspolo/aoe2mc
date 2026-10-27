"""
AoE2 combat values of the units and buildings of the game program (#513, epic #395: milestone D).

One table, keyed by the AoE2 unit name of `units.classify`. The values are the published AoE2 DE values of the
base unit: no Blacksmith or University upgrades, no civilization bonuses. `range` is in tiles (0: melee),
`reload` in game seconds. `bonus` is extra attack against the units of a class (`classes`): AoE2 adds it
for each armor class of the target. `damage` is the AoE2 damage rule (#514); the Paper plugin applies it
(`aoe stats` gives a mob its values, `stats_command`).
A ranged unit shoots from its AoE2 range, one shot per reload time (#515, `aoe range`, `range_command`).
The Mangonel line hits all units in its blast radius around the target (#1050, `BLAST`). It does not shoot at a target inside its minimum range (`MIN_RANGE`, #1350).
A melee unit hits once per reload time too (#848, the last value of `stats_command`).
An idle soldier attacks the nearest enemy unit in its AoE2 line of sight (#775, `aoe sight`, `sight_command`).
"""
import math
import os
import sys
import uuid as uuids
from collections import namedtuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gather import NORMAL  # noqa: E402
import garrison  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import units  # noqa: E402
from units import pretty  # noqa: E402

Stats = namedtuple("Stats", "hp attack melee pierce range reload bonus classes", defaults=({}, ()))

INF, ARC, CAV, CAM, ELE, SIE, SPE = "infantry", "archer", "cavalry", "camel", "elephant", "siege", "spearman"
HSI = "heavysiege"                                    # the Hussite Wagon and Ballista Elephant lines (wiki "Armor class", #1402)
RAM = "ram"                                           # the rams, the siege tower, the unpacked trebuchet, the Armored Elephant line
UNI = "unique"                                        # the unique units of the castles (the Samurai bonus)
GUN = "gunpowder"                                     # the targets of the Condottiero and Winged Hussar bonus (#1007)
SHIP, WAR = "ship", "warship"                         # the ships; "warship": the AoE2 class "Long-range warship"
FIRE = "fireship"                                     # the AoE2 class "Fire Ships" (the hulk bonus, #1489)
SPEAR = {CAV: 15, CAM: 12, ELE: 15}                   # spearman bonus, more in the later ages of the line
STATS = {
    # infantry: militia line and spearman line
    "MILITIA": Stats(40, 4, 0, 1, 0, 2.0, {}, (INF,)),
    "MAN_AT_ARMS": Stats(45, 6, 0, 1, 0, 2.0, {}, (INF,)),
    "LONG_SWORDSMAN": Stats(60, 9, 0, 1, 0, 2.0, {}, (INF,)),
    "TWO_HANDED_SWORDSMAN": Stats(65, 12, 0, 1, 0, 2.0, {}, (INF,)),
    "CHAMPION": Stats(70, 13, 1, 1, 0, 2.0, {}, (INF,)),
    "SPEARMAN": Stats(45, 3, 0, 0, 0, 3.0, SPEAR, (INF, SPE)),
    "PIKEMAN": Stats(55, 4, 0, 0, 0, 3.0, {CAV: 22, CAM: 18, ELE: 25}, (INF, SPE)),
    "HALBERDIER": Stats(60, 6, 0, 0, 0, 3.0, {CAV: 32, CAM: 26, ELE: 28}, (INF, SPE)),
    "EAGLE_SCOUT": Stats(50, 4, 0, 2, 0, 2.0, {SIE: 3}, (INF,)),               # the Dark and Feudal Age values
    "EAGLE_WARRIOR": Stats(55, 7, 0, 3, 0, 2.0, {CAM: 2, CAV: 3, SIE: 3, SHIP: 1}, (INF,)),   # AoE2 DE wiki (#1555)
    "ELITE_EAGLE_WARRIOR": Stats(60, 9, 0, 4, 0, 2.0, {CAM: 3, CAV: 4, SIE: 5, SHIP: 2}, (INF,)),
    # archers: the attack is pierce damage
    "ARCHER": Stats(30, 4, 0, 0, 4, 2.0, {SPE: 3}, (ARC,)),
    "CROSSBOWMAN": Stats(35, 5, 0, 0, 5, 2.0, {SPE: 3}, (ARC,)),
    "ARBALESTER": Stats(40, 6, 0, 0, 5, 2.0, {SPE: 3}, (ARC,)),
    "SKIRMISHER": Stats(30, 2, 0, 3, 4, 3.0, {ARC: 3, SPE: 3}, (ARC,)),
    "ELITE_SKIRMISHER": Stats(35, 3, 0, 4, 5, 3.0, {ARC: 4, SPE: 3}, (ARC,)),
    "IMPERIAL_SKIRMISHER": Stats(35, 4, 0, 5, 5, 3.0, {ARC: 5, SPE: 4}, (ARC,)),
    "LONGBOWMAN": Stats(35, 6, 0, 0, 5, 2.0, {SPE: 2}, (ARC, UNI)),
    "CAVALRY_ARCHER": Stats(50, 6, 0, 0, 4, 2.0, {SPE: 2}, (ARC, CAV)),
    "HEAVY_CAVALRY_ARCHER": Stats(60, 7, 1, 0, 4, 2.0, {SPE: 4}, (ARC, CAV)),
    "HAND_CANNONEER": Stats(40, 17, 1, 0, 7, 3.45, {INF: 10, SPE: 1}, (ARC, GUN)),
    # cavalry
    "SCOUT_CAVALRY": Stats(45, 3, 0, 2, 0, 2.0, {}, (CAV,)),
    "LIGHT_CAVALRY": Stats(60, 7, 0, 2, 0, 2.0, {}, (CAV,)),
    "HUSSAR": Stats(75, 7, 0, 2, 0, 1.9, {}, (CAV,)),
    "KNIGHT": Stats(100, 10, 2, 2, 0, 1.8, {}, (CAV,)),
    "CAVALIER": Stats(120, 12, 2, 2, 0, 1.8, {}, (CAV,)),
    "PALADIN": Stats(160, 14, 2, 3, 0, 1.9, {}, (CAV,)),                     # ROF 1.9: the wiki infobox (#1501)
    "CAMEL_RIDER": Stats(100, 6, 0, 0, 0, 2.0, {CAV: 9, CAM: 5, SHIP: 5}, (CAM,)),   # the wiki infobox (#1550)
    "HEAVY_CAMEL_RIDER": Stats(120, 7, 0, 0, 0, 2.0, {CAM: 9, CAV: 18, SHIP: 9}, (CAM,)),
    "IMPERIAL_CAMEL_RIDER": Stats(140, 8, 0, 0, 0, 1.667, {"building": 2, CAM: 9, CAV: 18}, (CAM,)),
    "WAR_ELEPHANT": Stats(450, 15, 1, 2, 0, 2.0, {"building": 30}, (ELE, UNI)),
    "ELITE_WAR_ELEPHANT": Stats(600, 20, 1, 3, 0, 2.0, {"building": 30}, (ELE, UNI)),
    # unique units of the castle (#712; Throwing Axeman and Mameluke hit with melee damage in AoE2: here pierce). #1006:
    # the first projectile of Kipchak and Organ Gun, the ranged mode of the Ratha, the Castle Age Serjeant.
    # #1005: a Kamayuk hits from AoE2 range 1: a melee hit. #1041: the base values of the wiki without the civilization
    # bonus (Berserk 54 HP, Janissary 35 HP, Mangudai and Samurai reload, Genoese armor, Rattan Archer HP, Teutonic armor)
    "ARAMBAI": Stats(60, 12, 0, 1, 5, 2.0, {SIE: 2}, (ARC, CAV, UNI)),
    "BALLISTA_ELEPHANT": Stats(250, 9, 0, 3, 5, 2.5, {"building": 5}, (CAV, ELE, SIE, UNI, HSI)),
    "BERSERK": Stats(54, 12, 1, 1, 0, 2.0, {"building": 2}, (INF, UNI)),
    "BOYAR": Stats(100, 12, 4, 2, 0, 1.9, {}, (CAV, UNI)),
    "CAMEL_ARCHER": Stats(55, 7, 0, 1, 4, 2.0, {}, (ARC, CAM, UNI)),
    "CATAPHRACT": Stats(110, 9, 2, 1, 0, 1.8, {INF: 13}, (CAV, UNI)),
    "CENTURION": Stats(110, 13, 2, 3, 0, 1.9, {}, (CAV, UNI)),
    "CHAKRAM_THROWER": Stats(40, 3, 1, 0, 5, 2.0, {"building": 1}, (INF, UNI)),   # the Gurjaras castle (#1612)
    "CHU_KO_NU": Stats(45, 8, 0, 0, 4, 3.0, {SPE: 2}, (ARC, UNI)),
    "COMPOSITE_BOWMAN": Stats(40, 4, 1, 0, 4, 2.0, {SPE: 2}, (ARC, UNI)),
    "CONQUISTADOR": Stats(55, 16, 2, 1, 6, 2.9, {SIE: 4}, (ARC, CAV, UNI)),
    "COUSTILLIER": Stats(115, 8, 2, 2, 0, 1.9, {}, (CAV, UNI)),
    "ELITE_TEUTONIC_KNIGHT": Stats(110, 17, 8, 2, 0, 2.0, {"building": 4}, (INF, UNI)),
    "FLAMING_CAMEL": Stats(55, 20, 0, 0, 0, 2.0, {"building": 200, CAV: 50, CAM: 50, ELE: 130, SIE: 25}, (CAM, UNI)),
    "FLEMISH_MILITIA": Stats(40, 5, 1, 1, 0, 2.0, {CAV: 6, CAM: 4, ELE: 6}, (INF, UNI)),
    "GBETO": Stats(40, 10, 0, 0, 5, 2.0, {}, (INF, UNI)),
    "GENGHIS_KHAN": Stats(300, 25, 2, 2, 5, 2.0, {SIE: 3}, (ARC, CAV, UNI)),
    "GENOESE_CROSSBOWMAN": Stats(45, 6, 1, 0, 4, 2.0, {CAV: 5, CAM: 4, ELE: 5}, (ARC, UNI)),
    "GHULAM": Stats(60, 9, 0, 3, 0, 2.0, {ARC: 5, "building": 2}, (INF, UNI)),
    "HUSKARL": Stats(60, 10, 0, 6, 0, 2.0, {ARC: 6, "building": 2}, (INF, UNI)),
    "HUSSITE_WAGON": Stats(160, 10, 0, 7, 6, 3.45, {SIE: 3, "building": 1}, (SIE, UNI, HSI)),
    "JAGUAR_WARRIOR": Stats(65, 15, 1, 2, 0, 2.0, {INF: 5, "building": 2}, (INF, UNI)),
    "JANISSARY": Stats(35, 17, 1, 0, 7, 3.45, {SIE: 2}, (ARC, GUN, UNI)),
    "KAMAYUK": Stats(70, 7, 1, 0, 0, 2.0, {CAV: 8, CAM: 6, ELE: 20}, (INF, UNI)),
    "KARAMBIT_WARRIOR": Stats(30, 7, 0, 1, 0, 2.0, {}, (INF, UNI)),
    "KESHIK": Stats(120, 9, 1, 2, 0, 1.9, {}, (CAV, UNI)),
    "KIPCHAK": Stats(40, 4, 0, 0, 4, 2.2, {SPE: 1}, (ARC, CAV, UNI)),
    "KONNIK": Stats(100, 12, 2, 2, 0, 2.4, {}, (CAV, UNI)),
    "LEITIS": Stats(100, 13, 1, 1, 0, 1.9, {}, (CAV, UNI)),
    "MAGYAR_HUSZAR": Stats(80, 10, 0, 2, 0, 1.8, {SIE: 5}, (CAV, UNI)),
    "MAMELUKE": Stats(80, 8, 0, 0, 3, 2.0, {CAV: 9}, (CAM, UNI)),
    "MANGUDAI": Stats(60, 6, 0, 0, 4, 2.1, {SIE: 3, SPE: 1}, (ARC, CAV, UNI)),
    "MONASPA": Stats(70, 12, 3, 2, 0, 1.8, {}, (CAV, UNI)),
    "OBUCH": Stats(80, 8, 2, 2, 0, 2.0, {"building": 4}, (INF, UNI)),
    "ORGAN_GUN": Stats(50, 6, 2, 4, 7, 3.45, {INF: 2}, (GUN, SIE, UNI)),
    "PLUMED_ARCHER": Stats(50, 5, 0, 1, 4, 1.9, {INF: 1, SPE: 2}, (ARC, UNI)),
    "RATHA": Stats(100, 5, 3, 1, 4, 2.0, {SPE: 1}, (ARC, CAV, UNI)),
    "RATTAN_ARCHER": Stats(35, 6, 0, 4, 4, 2.0, {SPE: 2}, (ARC, UNI)),
    "SAMURAI": Stats(70, 10, 1, 1, 0, 1.9, {"building": 2, UNI: 10}, (INF, UNI)),
    "SERJEANT": Stats(75, 8, 4, 2, 0, 2.0, {"building": 2}, (INF, UNI)),
    "SHOTEL_WARRIOR": Stats(45, 16, 0, 0, 0, 2.0, {}, (INF, UNI)),
    "SHRIVAMSHA_RIDER": Stats(55, 8, 0, 1, 0, 2.0, {}, (CAV, UNI)),
    "TARKAN": Stats(100, 8, 1, 3, 0, 1.9, {"building": 8}, (CAV, UNI)),
    "TEUTONIC_KNIGHT": Stats(90, 14, 7, 2, 0, 2.0, {"building": 4}, (INF, UNI)),
    "THROWING_AXEMAN": Stats(60, 7, 0, 0, 5, 2.0, {"building": 1}, (INF, UNI)),
    "URUMI_SWORDSMAN": Stats(55, 9, 1, 0, 0, 2.0, {"building": 1}, (INF, UNI)),
    "WAR_WAGON": Stats(150, 9, 0, 2, 4, 2.5, {"building": 2}, (ARC, CAV, UNI)),
    "WOAD_RAIDER": Stats(70, 11, 0, 1, 0, 2.0, {"building": 2}, (INF, UNI)),
    # elite unique units (#1008, AoE2 wiki, DE, no upgrades): the wiki lists one bonus per class; "building" sums the bonus
    # vs standard buildings and vs all buildings. No class here: shock infantry, ships, cavalry archers. #1075: without the
    # civilization bonus, as the base units (#1041)
    "ELITE_ARAMBAI": Stats(65, 14, 0, 2, 5, 2.0, {SIE: 2}, (ARC, CAV, UNI)),
    "ELITE_BALLISTA_ELEPHANT": Stats(280, 10, 0, 3, 5, 2.5, {"building": 8}, (CAV, ELE, SIE, UNI, HSI)),
    "ELITE_BERSERK": Stats(62, 14, 2, 1, 0, 2.0, {"building": 3}, (INF, UNI)),
    "ELITE_BOYAR": Stats(130, 14, 8, 3, 0, 1.9, {}, (CAV, UNI)),
    "ELITE_CAMEL_ARCHER": Stats(60, 8, 1, 1, 4, 2.0, {}, (ARC, CAM, UNI)),
    "ELITE_CATAPHRACT": Stats(150, 12, 2, 1, 0, 1.7, {INF: 18}, (CAV, UNI)),
    "ELITE_CENTURION": Stats(155, 15, 3, 3, 0, 1.9, {}, (CAV, UNI)),
    "ELITE_CHAKRAM_THROWER": Stats(50, 4, 1, 0, 6, 2.0, {"building": 2, INF: 1}, (INF, UNI)),
    "ELITE_CHU_KO_NU": Stats(50, 10, 0, 0, 4, 3.0, {SPE: 2}, (ARC, UNI)),
    "ELITE_COMPOSITE_BOWMAN": Stats(50, 4, 2, 0, 4, 2.0, {SPE: 2}, (ARC, UNI)),
    "ELITE_CONQUISTADOR": Stats(70, 19, 2, 2, 6, 2.9, {SIE: 6, "building": 2}, (ARC, CAV, UNI)),
    "ELITE_COUSTILLIER": Stats(145, 11, 2, 2, 0, 1.9, {}, (CAV, UNI)),
    "ELITE_GBETO": Stats(50, 13, 0, 0, 6, 2.0, {}, (INF, UNI)),
    "ELITE_GENOESE_CROSSBOWMAN": Stats(50, 6, 1, 0, 4, 2.0, {CAV: 7, CAM: 6, ELE: 7}, (ARC, UNI)),
    "ELITE_GHULAM": Stats(70, 11, 0, 6, 0, 2.0, {ARC: 6, "building": 2}, (INF, UNI)),
    "ELITE_HUSKARL": Stats(70, 12, 0, 8, 0, 2.0, {ARC: 10, "building": 3}, (INF, UNI)),
    "ELITE_HUSSITE_WAGON": Stats(230, 13, 1, 10, 6, 3.45, {SIE: 3, "building": 2}, (SIE, UNI, HSI)),
    "ELITE_JAGUAR_WARRIOR": Stats(75, 19, 2, 2, 0, 2.0, {INF: 6, "building": 2}, (INF, UNI)),
    "ELITE_JANISSARY": Stats(40, 22, 2, 0, 8, 3.45, {SIE: 3}, (ARC, GUN, UNI)),
    "ELITE_KAMAYUK": Stats(80, 8, 1, 1, 0, 2.0, {CAV: 12, CAM: 10, ELE: 20}, (INF, UNI)),
    "ELITE_KARAMBIT_WARRIOR": Stats(40, 8, 1, 1, 0, 2.0, {"building": 1}, (INF, UNI)),
    "ELITE_KESHIK": Stats(145, 11, 1, 3, 0, 1.9, {}, (CAV, UNI)),
    "ELITE_KIPCHAK": Stats(45, 5, 0, 0, 4, 2.2, {SPE: 1}, (ARC, CAV, UNI)),
    "ELITE_KONNIK": Stats(120, 14, 2, 2, 0, 2.4, {}, (CAV, UNI)),
    "ELITE_LEITIS": Stats(130, 16, 2, 1, 0, 1.9, {}, (CAV, UNI)),
    "ELITE_LONGBOWMAN": Stats(40, 7, 0, 1, 6, 2.0, {SPE: 2}, (ARC, UNI)),
    "ELITE_MAGYAR_HUSZAR": Stats(90, 11, 0, 2, 0, 1.8, {SIE: 8}, (CAV, UNI)),
    "ELITE_MAMELUKE": Stats(90, 10, 1, 0, 3, 2.0, {CAV: 12}, (CAM, UNI)),
    "ELITE_MANGUDAI": Stats(60, 8, 1, 0, 4, 2.1, {SIE: 5, SPE: 1}, (ARC, CAV, UNI)),
    "ELITE_MONASPA": Stats(80, 14, 5, 2, 0, 1.8, {}, (CAV, UNI)),
    "ELITE_OBUCH": Stats(95, 10, 2, 2, 0, 2.0, {"building": 6}, (INF, UNI)),
    "ELITE_ORGAN_GUN": Stats(70, 8, 2, 6, 7, 3.45, {INF: 2, SIE: 1, "building": 1}, (GUN, SIE, UNI)),
    "ELITE_PLUMED_ARCHER": Stats(65, 5, 0, 2, 5, 1.9, {INF: 2, SPE: 2}, (ARC, UNI)),
    "ELITE_RATTAN_ARCHER": Stats(40, 7, 0, 6, 5, 2.0, {SPE: 2}, (ARC, UNI)),
    "ELITE_SAMURAI": Stats(80, 12, 1, 1, 0, 1.9, {"building": 3, UNI: 12}, (INF, UNI)),
    "ELITE_SERJEANT": Stats(85, 11, 6, 3, 0, 2.0, {"building": 3}, (INF, UNI)),
    "ELITE_SHOTEL_WARRIOR": Stats(50, 18, 0, 1, 0, 2.0, {"building": 1}, (INF, UNI)),
    "ELITE_SHRIVAMSHA_RIDER": Stats(70, 11, 0, 1, 0, 1.9, {}, (CAV, UNI)),
    "ELITE_TARKAN": Stats(150, 11, 1, 4, 0, 1.9, {"building": 10}, (CAV, UNI)),
    "ELITE_THROWING_AXEMAN": Stats(70, 8, 1, 0, 6, 2.0, {"building": 2}, (INF, UNI)),
    "ELITE_URUMI_SWORDSMAN": Stats(65, 11, 1, 0, 0, 2.0, {"building": 2}, (INF, UNI)),
    "ELITE_WAR_WAGON": Stats(200, 9, 0, 4, 5, 2.5, {"building": 2}, (ARC, CAV, UNI)),
    "ELITE_WOAD_RAIDER": Stats(85, 15, 0, 1, 0, 2.0, {"building": 3}, (INF, UNI)),
    # regional units (#1007). The steppe lancers hit from AoE2 range 1: a melee hit in Minecraft (the vanilla reach)
    "BATTLE_ELEPHANT": Stats(250, 12, 1, 2, 0, 2.0, {"building": 4}, (ELE,)),
    "CONDOTTIERO": Stats(80, 10, 1, 0, 0, 1.9, {GUN: 10, "building": 2}, (INF, UNI)),
    "ELITE_BATTLE_ELEPHANT": Stats(300, 14, 1, 3, 0, 2.0, {"building": 7}, (ELE,)),
    "ELITE_GENITOUR": Stats(55, 4, 0, 4, 4, 3.0, {ARC: 5, SPE: 3}, (ARC, CAV, UNI)),   # the wiki infobox (#1610)
    "ELITE_STEPPE_LANCER": Stats(80, 11, 0, 2, 0, 2.0, {}, (CAV,)),
    "GENITOUR": Stats(50, 3, 0, 4, 4, 3.0, {ARC: 4, SPE: 3}, (ARC, CAV, UNI)),
    "SLINGER": Stats(35, 4, 0, 0, 5, 2.0, {INF: 4, SIE: 3, SPE: 1}, (ARC,)),
    "STEPPE_LANCER": Stats(60, 9, 0, 1, 0, 2.0, {}, (CAV,)),
    "WINGED_HUSSAR": Stats(80, 9, 1, 2, 0, 1.9, {GUN: 4}, (CAV,)),
    # units of the DLCs Dynasties of India, Return of Rome and The Three Kingdoms (#1009, AoE2 wiki, DE, base unit, no civilization bonus;
    # Iron Pagoda: reload 2.16 without the Jurchen bonus). No class here: shock infantry, rams, ships; the charged
    # attacks (Fire Lancer) and "ignores armor" (Rocket Cart) are not modeled
    "ARMORED_ELEPHANT": Stats(180, 4, -2, 140, 0, 3.0, {"building": 90, SIE: 25}, (CAV, ELE, SIE, RAM)),
    "FIRE_LANCER": Stats(65, 9, 1, 0, 0, 2.0, {"building": 1, CAV: 5, CAM: 4, ELE: 5}, (INF, GUN)),
    "GRENADIER": Stats(40, 12, 1, 1, 6, 3.45, {"building": 4, INF: 9, SIE: 3, SPE: 1}, (ARC, GUN, UNI)),
    "HEAVY_ROCKET_CART": Stats(65, 5, 0, 8, 8, 5.35, {"building": 12, SIE: 2}, (GUN, SIE)),
    "HEI_GUANG_CAVALRY": Stats(60, 11, 4, 3, 0, 1.8, {}, (CAV,)),
    "HOUFNICE": Stats(90, 50, 2, 6, 12, 6.5, {"building": 250, SIE: 20}, (GUN, SIE)),
    "IRON_PAGODA": Stats(115, 12, 1, 3, 0, 2.16, {}, (CAV, UNI)),
    "LEGIONARY": Stats(75, 12, 2, 2, 0, 2.0, {"building": 4, INF: 4}, (INF,)),
    "ROCKET_CART": Stats(45, 5, 0, 6, 7, 5.5, {"building": 7, SIE: 2}, (GUN, SIE)),
    "SIEGE_ELEPHANT": Stats(220, 4, -2, 150, 0, 3.0, {"building": 105, SIE: 35}, (CAV, ELE, SIE, RAM)),
    "TRACTION_TREBUCHET": Stats(115, 50, 1, 8, 14, 11.0, {"building": 230}, (SIE,)),
    "WHITE_FEATHER_GUARD": Stats(95, 7, 0, 2, 0, 2.0, {"building": 2, CAV: 8, CAM: 6, ELE: 8}, (INF, UNI)),
    # siege
    "MANGONEL": Stats(50, 40, 0, 6, 7, 6.0, {"building": 35, HSI: 40, SIE: 12}, (SIE,)),   # AoE2 DE wiki (#1402)
    "ONAGER": Stats(60, 55, 0, 8, 8, 6.0, {"building": 45, HSI: 50, SIE: 12}, (SIE,)),
    "SIEGE_ONAGER": Stats(70, 75, 0, 8, 8, 6.0, {"building": 60, HSI: 50, SIE: 12}, (SIE,)),
    "SCORPION": Stats(40, 11, 0, 7, 7, 3.6, {"building": 3, ELE: 7, INF: 1, RAM: 1}, (SIE,)),
    "HEAVY_SCORPION": Stats(60, 14, 1, 8, 7, 3.6, {"building": 6, ELE: 10, INF: 2, RAM: 2}, (SIE,)),
    "BATTERING_RAM": Stats(175, 2, -3, 180, 0, 5.0, {"building": 150, SIE: 40}, (SIE, RAM)),
    "CAPPED_RAM": Stats(200, 3, -2, 190, 0, 5.0, {"building": 160, SIE: 50}, (SIE, RAM)),
    "SIEGE_RAM": Stats(270, 4, -1, 195, 0, 5.0, {"building": 200, SIE: 65}, (SIE, RAM)),
    "SIEGE_TOWER": Stats(175, 0, -2, 100, 0, 0.0, {}, (SIE, RAM)),         # AoE2 DE wiki (#1362)
    "TRADE_COG": Stats(80, 0, 0, 6, 0, 0.0, {}, ()),                   # AoE2 DE wiki (#1485)
    "TRANSPORT_SHIP": Stats(70, 0, 0, 2, 0, 0.0, {}, ()),              # AoE2 DE wiki (#1385)
    "TREBUCHET": Stats(150, 200, 2, 8, 16, 10.0, {"building": 250}, (SIE,)),   # AoE2 DE wiki: 150 HP (#1351); packed
    # armor (unpacked: trebuchet.UNPACKED, #1409)
    "BOMBARD_CANNON": Stats(80, 40, 2, 5, 12, 6.5, {"building": 200, HSI: 40, SIE: 20}, (GUN, SIE)),
    "PETARD": Stats(50, 25, 0, 2, 0, 2.0, {"building": 500, SIE: 60}),
    # cheat units (#818, AoE2 DE values of the wiki; the Cobra car shoots: a ranged unit)
    "ALFRED_THE_ALPACA": Stats(140, 120, 20, 20, 0, 2.0, {"building": 100}, (CAV,)),
    "COBRA_CAR": Stats(500, 10, 10, 10, 10, 0.25, {"building": 10}, (SIE,)),
    "FURIOUS_THE_MONKEY_BOY": Stats(9, 99, 99, 99, 0, 0.9, {"building": 999}),
    "PHOTONMAN": Stats(80, 30, 2, 2, 10, 2.0, {"building": 5}, (ARC, UNI)),
    "SABOTEUR": Stats(45, 100, 1, 3, 0, 2.0, {"building": 500}, (SIE,)),
    "SHARKATZOR": Stats(600, 33, 1, 0, 10, 2.1, {SIE: 5}, (SIE,)),
    "VMDL": Stats(25, 0, 0, 0, 0, 0.0),
    "WAR_PENGUIN": Stats(64, 16, 4, 4, 0, 2.0, {"building": 8}, (INF,)),
    # ships (#1386, AoE2 DE wiki): the hits go to the crew of the boat (AoePlugin.java)
    "CANNON_GALLEON": Stats(120, 50, 0, 5, 13, 10.0, {"building": 200, SIE: 25}, (SHIP, GUN, WAR)),   # (#1484) melee damage
    "DEMOLITION_RAFT": Stats(40, 75, 0, 0, 0, 0.0, {"building": 180}, (SHIP,)),   # (#1481) the Feudal Age form
    "DEMOLITION_SHIP": Stats(50, 95, 1, 0, 0, 0.0, {"building": 220}, (SHIP,)),   # one blast (BLAST), then it dies
    "ELITE_CANNON_GALLEON": Stats(150, 60, 0, 6, 15, 10.0, {"building": 275, SIE: 25}, (SHIP, GUN, WAR)),   # (#1491)
    "FAST_FIRE_SHIP": Stats(140, 4, 3, 7, 2.5, 0.25, {"building": 3, WAR: 1}, (SHIP, FIRE)),   # Heavy Warships (#1483)
    "FIRE_GALLEY": Stats(110, 2, 1, 4, 2.5, 0.25, {WAR: 1}, (SHIP, FIRE)),   # (#1481) the Feudal Age form of the fire ship
    "FIRE_SHIP": Stats(120, 3, 2, 4, 2.5, 0.25, {"building": 2, WAR: 1}, (SHIP, FIRE)),   # (#1440) melee damage, 4 hits/s
    "FISHING_SHIP": Stats(50, 0, 1, 1, 0, 0.0, {}, (SHIP,)),
    "GALLEY": Stats(110, 6, 0, 3, 5, 3.0, {"building": 6, WAR: 5}, (SHIP, WAR)),
    "GALLEON": Stats(155, 9, 0, 6, 7, 3.0, {"building": 6, WAR: 9, RAM: 3}, (SHIP, WAR)),   # Heavy Warships (#1483)
    "HEAVY_DEMOLITION_SHIP": Stats(70, 120, 2, 0, 0, 0.0, {"building": 280}, (SHIP,)),   # (#1483)
    "HULK": Stats(85, 4, 3, 1, 1, 1.75, {FIRE: 1, "standard": -3}, (SHIP,)),   # AoE2 DE wiki (#1489): melee hits at range 1
    "WAR_GALLEY": Stats(125, 7, 0, 4, 6, 3.0, {"building": 6, WAR: 5}, (SHIP, WAR)),   # Medium Warships (#1482)
    "WAR_HULK": Stats(110, 4, 4, 1, 1, 1.5, {FIRE: 1, "standard": -3}, (SHIP,)),   # Medium Warships (#1508)
    # others: no fight, but they can die
    "VILLAGER": Stats(25, 3, 0, 0, 0, 2.0, {"building": 3, HSI: 6, "stone": 6}),   # AoE2 DE wiki (#1590)
    "KING": Stats(75, 0, 0, 0, 0, 0.0),
    "MONK": Stats(30, 0, 0, 0, 9, 0.0),
    "TRADE_CART": Stats(70, 0, 0, 0, 0, 0.0),
}
# Buildings: hit points, melee and pierce armor (Dark Age base). The high pierce armor makes arrows weak, as in AoE2.
BUILDINGS = {
    "HOUSE": Stats(550, 0, 0, 7, 0, 0.0, {}, ("building",)),
    "BARRACKS": Stats(1200, 0, 0, 7, 0, 0.0, {}, ("building",)),
    "ARCHERY_RANGE": Stats(1500, 0, 0, 7, 0, 0.0, {}, ("building",)),
    "STABLE": Stats(1500, 0, 0, 7, 0, 0.0, {}, ("building",)),
    "DOCK": Stats(1800, 0, 0, 7, 0, 0.0, {SHIP: 3}, ("building",)),   # AoE2 DE wiki, the Dark Age (#1382)
    "MARKET": Stats(1800, 0, 1, 8, 0, 0.0, {}, ("building",)),       # the Feudal Age values of the wiki (#1251)
    "MONASTERY": Stats(2100, 0, 0, 7, 0, 0.0, {}, ("building",)),
    "SIEGE_WORKSHOP": Stats(2100, 0, 0, 7, 0, 0.0, {}, ("building",)),
    "BLACKSMITH": Stats(1800, 0, 1, 8, 0, 0.0, {}, ("building",)),   # the Feudal Age values of the wiki (#1403)
    "LUMBER_CAMP": Stats(600, 0, 0, 7, 0, 0.0, {}, ("building",)),
    "MILL": Stats(600, 0, 0, 7, 0, 0.0, {}, ("building",)),
    "MINING_CAMP": Stats(600, 0, 0, 7, 0, 0.0, {}, ("building",)),
    "UNIVERSITY": Stats(2100, 0, 2, 9, 0, 0.0, {}, ("building",)),   # the Castle Age values
    # the towers (AoE2 DE, wiki): a watch tower of the Castle Age (850 hit points in the Feudal Age), #1112. The attack
    # against ships: the "Attack bonus" of the wiki infobox (#1564; the dock: the Castle Age, it does not shoot yet)
    "BOMBARD_TOWER": Stats(2220, 120, 3, 9, 8, 6.0, {SHIP: 40}, ("building",)),
    "FORTIFIED_TOWER": Stats(1900, 8, 4, 7, 13, 3.0, {SHIP: 12}, ("building",)),
    "GUARD_TOWER": Stats(1500, 7, 2, 8, 8, 2.0, {SHIP: 7}, ("building",)),
    "KEEP": Stats(2250, 8, 3, 9, 8, 2.0, {SHIP: 8}, ("building",)),
    "WATCH_TOWER": Stats(1020, 5, 1, 7, 8, 2.0, {SHIP: 5}, ("building",)),
    "TOWN_CENTER": Stats(2400, 5, 3, 5, 6, 2.0, {SHIP: 5}, ("building",)),
    "CASTLE": Stats(4800, 11, 8, 11, 8, 2.0, {SHIP: 11}, ("building",)),
    "WONDER": Stats(4800, 0, 3, 10, 0, 0.0, {}, ("building",)),
}
# The walls that a player builds in the game program (#1322, AoE2 DE wiki infobox): the hit points in the Dark, Feudal,
# Castle and Imperial Age, the melee and the pierce armor. Their targets have WALL_TAG: a wall keeps no player alive in
# the conquest (conquest.alive). The walls of the map have no target.
WALLS = {
    "FORTIFIED_GATE": ((4000, 4000, 4000, 4000), 6, 7),             # the gate after Fortified Wall (#1326)
    "FORTIFIED_WALL": ((3000, 3000, 3000, 3000), 12, 12),          # the stone wall after Fortified Wall (#1326)
    "GATE": ((1650, 1650, 2750, 2750), 6, 6),                         # the Feudal Age: no Dark Age gate (#1324)
    "PALISADE_GATE": ((240, 400, 400, 400), 2, 4),
    "PALISADE_WALL": ((150, 250, 250, 250), 2, 5),
    "STONE_WALL": ((1080, 1080, 1800, 1800), 8, 10),
}
WALL_TAG = "aoe2mc.wall"
# The AoE2 class "Standard Buildings" (wiki "Armor class"): all buildings but the walls, the gates and the wonder. Arson
# gives infantry a bonus against it (#1419).
STANDARD = "standard"
BUILDINGS = {k: s if k == "WONDER" else s._replace(classes=s.classes + (STANDARD,)) for k, s in BUILDINGS.items()}
# The AoE2 class "Stone Defense" (wiki infobox "Class"): the stone walls and gates and the towers, not the castle and
# not the palisades. The villager gets a bonus against it (#1590).
STONE = "stone"
BUILDINGS = {k: s._replace(classes=s.classes + (STONE,)) if k.endswith("_TOWER") or k == "KEEP" else s
             for k, s in BUILDINGS.items()}
WATCH = 4    # tiles of line of sight that Town Watch adds to each own building but walls, gates, farms, fish traps (#1454)
# Line of sight in tiles (AoE2 DE, base unit or building, wiki infobox "LOS"; the house: 1 from the edge of its
# 2 x 2 tiles, #1300) where it is not max(4, range + 2) (sight()).
SIGHT = {
    "ARCHERY_RANGE": 6,
    "BARRACKS": 6,
    "BLACKSMITH": 6,
    "BOMBARD_TOWER": 10,
    "CAMEL_RIDER": 5,                                                  # the wiki infobox (#1550)
    "CANNON_GALLEON": 15,
    "CASTLE": 11,
    "CHAMPION": 5,
    "DEMOLITION_RAFT": 6,
    "DEMOLITION_SHIP": 6,
    "FAST_FIRE_SHIP": 6,
    "DOCK": 8,
    "DONJON": 10,
    "ELITE_CANNON_GALLEON": 17,
    "ELITE_GENITOUR": 6,                                               # the wiki infobox (#1610)
    "ELITE_SHRIVAMSHA_RIDER": 6,
    "ELITE_STEPPE_LANCER": 5,
    "FIRE_GALLEY": 5,
    "FIRE_SHIP": 5,
    "GALLEON": 9,
    "GENITOUR": 5,
    "HEAVY_DEMOLITION_SHIP": 6,
    "HULK": 5,
    "FEITORIA": 6,
    "FORTIFIED_TOWER": 14,
    "GUARD_TOWER": 10,
    "HEAVY_CAMEL_RIDER": 5,
    "HOUSE": 2,
    "HUSSAR": 10,
    "KEEP": 10,
    "KREPOST": 10,
    "LIGHT_CAVALRY": 8,
    "LUMBER_CAMP": 6,
    "MARKET": 6,
    "MILL": 6,
    "MINING_CAMP": 6,
    "MONASTERY": 6,
    "OUTPOST": 4,
    "PALADIN": 5,
    "SIEGE_WORKSHOP": 6,
    "SHRIVAMSHA_RIDER": 5,
    "STABLE": 6,
    "STEPPE_LANCER": 5,
    "TOWN_CENTER": 8,
    "TRADE_COG": 6,
    "TWO_HANDED_SWORDSMAN": 5,
    "UNIVERSITY": 6,
    "WAR_HULK": 5,
    "WATCH_TOWER": 10,
    "WINGED_HUSSAR": 10,
    "WONDER": 8,
}
# Units that attack from a range with melee damage (AoE2): their hit takes the melee armor of the target (#800).
MELEE_RANGED = {"BOMBARD_CANNON",
                "CANNON_GALLEON",
                "CHAKRAM_THROWER",                # (#1612)
                "ELITE_CANNON_GALLEON",
                "ELITE_CHAKRAM_THROWER",
                "ELITE_GBETO",
                "ELITE_MAMELUKE",
                "ELITE_THROWING_AXEMAN",
                "FAST_FIRE_SHIP",
                "FIRE_GALLEY",
                "FIRE_SHIP",
                "GBETO",
                "HEAVY_ROCKET_CART",
                "HULK",
                "MAMELUKE",
                "MANGONEL",
                "ONAGER",
                "ROCKET_CART",
                "SIEGE_ONAGER",
                "THROWING_AXEMAN",
                "TRACTION_TREBUCHET",
                "WAR_HULK"}
# Blast radius in tiles of the units whose shot hits all units near the target, also own units (AoE2 DE, wiki "AOE";
# AoE2 tapers the damage at the edge, here each unit in the radius takes the full damage() hit, #1050). A ship has no
# vanilla shot: the fire ship (0: it hits only the target) and the demolition ship (#1440) shoot as a siege unit, and
# the creeper crew of the demolition ship dies after its blast (AoePlugin.java), as a vanilla creeper.
BLAST = {"BOMBARD_CANNON": 0.5,
         "CANNON_GALLEON": 0.25,
         "DEMOLITION_RAFT": 2.5,
         "DEMOLITION_SHIP": 3,
         "ELITE_CANNON_GALLEON": 0.3,
         "FAST_FIRE_SHIP": 0,
         "FIRE_GALLEY": 0,
         "FIRE_SHIP": 0,
         "HEAVY_DEMOLITION_SHIP": 3.25,
         "HEAVY_ROCKET_CART": 1.25,
         "HOUFNICE": 0.7,
         "MANGONEL": 1.0,
         "ONAGER": 1.25,
         "ROCKET_CART": 1.0,
         "SIEGE_ONAGER": 1.5}
RAM_REACH = 2.0       # blocks: a ram (a minecart with range 0) hits from next to its target, on its carrier (#1399)
CONTACT = 1.0         # tiles: the reach of a demolition ship (range 0, #1440): its raft is higher than a boat
MIN_RANGE = {"BOMBARD_CANNON": 5,     # tiles: no shot at a unit nearer (AoE2 DE, wiki infobox "MinRange", #1350)
             "CANNON_GALLEON": 3,
             "ELITE_CANNON_GALLEON": 3,
             "ELITE_ORGAN_GUN": 1,
             "HEAVY_ROCKET_CART": 2.5,
             "HEAVY_SCORPION": 2,
             "HOUFNICE": 5,
             "MANGONEL": 3,
             "ONAGER": 3,
             "ORGAN_GUN": 1,
             "ROCKET_CART": 2.5,
             "SCORPION": 2,
             "SIEGE_ONAGER": 3,
             "TRACTION_TREBUCHET": 4,
             "TREBUCHET": 4}
# The minimum range of the buildings that shoot, in tiles from the edge of the footprint (AoE2 DE, wiki infobox
# "MinRange", #1546). The town center has none. Murder Holes removes it.
FORT_MIN_RANGE = {"BOMBARD_TOWER": 1,
                  "CASTLE": 1,
                  "DOCK": 1,                  # it shoots only with fishing ships inside (AoE2 DE): not yet
                  "GUARD_TOWER": 1,
                  "KEEP": 1,
                  "WATCH_TOWER": 1}
# Tiles that a bolt flies past the range and hurts the enemy units on its line with half the damage (AoE2 DE, wiki
# "Pass-through damage": "Projectiles travel Range+2 tiles in total", no friendly fire, #1401). The chakram thrower
# throws as a mob (no blast), with the full damage on its line (PASS_PART, #1638).
PASS = {"CHAKRAM_THROWER": 2,
        "ELITE_CHAKRAM_THROWER": 2,
        "HEAVY_SCORPION": 2,
        "SCORPION": 2}
# The part of the damage on the units behind the target, when it is not one half (wiki: "100% pass-through damage").
PASS_PART = {"CHAKRAM_THROWER": 1.0,
             "ELITE_CHAKRAM_THROWER": 1.0}
DEFAULT, BUILDING = Stats(40, 4, 0, 0, 0, 2.0), Stats(1000, 0, 0, 7, 0, 0.0, {}, ("building",))
SLIME = 0.52                    # blocks of width and height per slime size: the target of a building (#517)
INVISIBLE = 'active_effects:[{id:"minecraft:invisibility",duration:-1,show_particles:0b}]'   # for ever, no particles
HEIGHT = 40                     # blocks above the ground that a fallen building clears


def stats(name):
    """The combat values of an AoE2 unit or building; an unknown name gets a militia-like unit. All villager names
    (VILLAGER_MALE, VILLAGER_FEMALE_FARMER ...) get the villager values (#655)."""
    return STATS.get("VILLAGER" if name.startswith("VILLAGER") else name) or BUILDINGS.get(name) or (BUILDING if name.endswith(("_WALL", "_GATE", "_TOWER")) else DEFAULT)


def damage(attacker, target):
    """AoE2 damage of one hit: max(1, attack - armor + bonus). Melee hits the melee armor, a ranged unit the pierce armor
    (but a MELEE_RANGED unit the melee armor)."""
    a, t = stats(attacker), stats(target)
    armor = t.pierce if a.range and attacker not in MELEE_RANGED else t.melee
    return max(1, max(0, a.attack - armor) + sum(a.bonus.get(c, 0) for c in t.classes))


def stats_command(uuid, name, s=None):
    """The plugin command that gives entity `uuid` the values of AoE2 unit `name` (or the values s, for example with
    technologies, #655): max_health = hit points (at most 1024, the limit of the attribute), the lost hit points stay lost
    (a new unit has full health, #940), and the values of `damage` (the same rule in AoePlugin.java). The range kind:
    0 melee, 1 ranged, 2 ranged with melee damage (MELEE_RANGED, #800). Last the reload in ticks at Normal speed: a melee unit hits once per reload (#848)."""
    s = s or stats(name)
    bonus = ",".join(f"{c}:{n}" for c, n in sorted(s.bonus.items())) or "-"
    kind = 0 if s.range <= 0 else 2 if name in MELEE_RANGED else 1
    return (f"aoe stats {uuid} {min(s.hp, 1024)} {s.attack} {s.melee} {s.pierce} {kind} "
            f"{','.join(s.classes) or '-'} {bonus} {round(s.reload / NORMAL * 20) or 20}")


def label_command(uuid, name=None):
    """The plugin command that shows the name line of a unit again (after a selection change), or with a name sets the name
    of a building target (#661): the name and 5 hearts, visible only when the unit is hurt or selected (AoePlugin.java).
    The units keep the name of the converter: `aoe stats` takes it."""
    return f"aoe label {uuid}" + (f" {pretty(name)}" if name else "")


def range_command(uuid, name, T, rate=NORMAL, s=None):
    """The plugin command that lets a ranged unit shoot from its AoE2 range (tiles * T blocks), with one shot per
    reload time at `rate` game seconds per real second (default: Normal game speed, as the walk speed). None for a
    melee unit. s: the values with technologies (Fletching, #724), default those of AoE2 unit name. A siege unit (a
    minecart) gets its blast radius in blocks last, 0 when its shot hits only the target (the Scorpion, #1062): the
    plugin then lets the minecart shoot too (#1050). Then its minimum range in blocks (MIN_RANGE, #1350), when it has
    one: it does not shoot at a target nearer than that. Then the blocks of PASS (#1401): its bolt hurts the enemy units on
    its line up to that far past its range, and the part of the damage (PASS_PART) when it is not one half. A unit that
    shoots as a mob and has a PASS (the chakram thrower, #1638) gets "-" for the blast. A melee siege unit (the ram line, range 0) gets the reach
    RAM_REACH: a carrier pig has no melee goal, so the range goal walks it to the target and hits (#1399). A demolition
    ship (#1440) gets the reach CONTACT: its blast goes off next to the target."""
    s = s or stats(name)
    cart = (units.classify(name) or {}).get("id") == "minecraft:minecart"
    blast = f" {BLAST.get(name, 0) * T}" if name in BLAST or cart else " -" if name in PASS else ""
    blast += f" {MIN_RANGE.get(name, 0) * T}" * bool(blast and (name in MIN_RANGE or name in PASS))
    blast += f" {PASS.get(name, 0) * T}" * bool(blast and name in PASS) + f" {PASS_PART.get(name)}" * (name in PASS_PART)
    reach = s.range * T or RAM_REACH * bool(cart and s.attack) or CONTACT * T * bool(name in BLAST and s.attack)
    return reach and (s.reload or name in BLAST) and f"aoe range {uuid} {reach} {max(1, round(s.reload / rate * 20))}{blast}" or None


def sight(name, s=None):
    """The AoE2 line of sight of unit name in tiles: an idle soldier attacks an enemy in it. Most units see 4 tiles,
    a ranged unit about 2 tiles more than its range."""
    s = s or stats(name)
    return SIGHT.get(name, max(4, s.range + 2))


def sight_command(uuid, name, T, s=None):
    """The plugin command that lets an idle soldier attack the nearest enemy unit in its line of sight (tiles * T
    blocks, #775). None for a unit that does not fight (villager, monk, king)."""
    s = s or stats(name)
    return f"aoe sight {uuid} {sight(name, s) * T}" if s.classes and s.attack else None


STANCES = ("aggressive", "defensive", "stand_ground", "no_attack")


def stance_command(uuid, stance):
    """The plugin command that sets the AoE2 stance of a unit (#1104): "no_attack" never attacks without an order,
    "stand_ground" attacks only an enemy in its range and keeps its place, "defensive" chases an enemy only a short
    way and walks back to its place (#1105); "aggressive" is the default."""
    if stance not in STANCES:
        raise ValueError(f"unknown stance: {stance}")
    return f"aoe stance {uuid} {stance}"


def setup(game, data):
    """Give each unit of the players in `aoe2mc.json` data its AoE2 values; Gaia animals keep the vanilla values.
    Each building of a player with AoE2 hit points gets a target of attacks (`building`).
    The entities must be loaded (forceload). Returns the number of units that got the values."""
    ground = [r.split() for r in data.get("ground", ())]
    held = {}                                        # the units that the converter put inside (#807): their arrows
    for o in data["objects"]:
        if o["kind"] == "unit" and o.get("holder") is not None:
            held.setdefault(o["holder"], []).append(o["name"])
    for o in data["objects"]:
        if o["kind"] == "building" and o["player"] and "footprint" in o and o["name"] in BUILDINGS:
            uuid = target_uuid(o["footprint"])
            for c in building(uuid, o["name"], o["player"], building_box(o, ground), data.get("tile_size", 4),
                              held.get(o.get("ref"), ())) + [label_command(uuid, o["name"])]:
                game.command(c)
    units = [o for o in data["objects"] if o["kind"] == "unit" and o["player"] and o.get("uuid")]
    for o in units:                                  # the plugin answers "Range: 0 units" for a mob that cannot shoot
        if cmd := range_command(o["uuid"], o["name"], data.get("tile_size", 4)):
            game.command(cmd)
    n = sum(game.command(stats_command(o["uuid"], o["name"])).strip() == "Stats: 1 units" for o in units)
    for o in units:                                  # after the stats: the plugin needs them for the sight
        if cmd := sight_command(o["uuid"], o["name"], data.get("tile_size", 4)):
            game.command(cmd)
    import ai                                        # ai -> gather -> build -> replay -> combat: import it late
    for o in units:                                  # the AoE2 walk speed also without an order (#849)
        game.command(ai.speed_command(o["uuid"], o["name"], data.get("tile_size", 4)))
    return n


def target_uuid(footprint):
    """The UUID of the target entity of the building with block footprint [x0, z0, x1, z1): the same in each run."""
    return str(uuids.uuid5(uuids.NAMESPACE_OID, "aoe2mc.building." + ".".join(map(str, footprint))))


def wall(name, age):
    """The Stats of wall name (WALLS) in AoE2 age 0 (Dark) .. 3 (Imperial)."""
    hp, melee, pierce = WALLS[name]
    return Stats(hp[age], 0, melee, pierce, 0, 0.0, {}, ("building",) + (STONE,) * (not name.startswith("PALISADE")))


def building(uuid, name, player, box, T=4, inside=(), s=None, low=None):
    """The commands that make building `name` of `player` a target of attacks (#517): an invisible slime without AI
    that fills the footprint takes the attacks (a mob attacks only a living entity: AoePlugin.java), and the plugin
    keeps the AoE2 hit points. box: the blocks (x0, y0, z0, x1, y1, z1), both ends included, y0 the ground.
    A building with an attack (town center, castle) also gets its attack, its range (tiles * T blocks) and its reload
    in ticks at Normal speed: the plugin lets it shoot arrows at the enemies in its range (#1111), with the AoE2
    number of arrows of the units `inside` (garrison.arrows: an empty town center shoots none, #1201), and its
    minimum range in blocks (FORT_MIN_RANGE, 0 for the town center): no shot at a unit nearer (#1546). low: the
    minimum range in tiles (default FORT_MIN_RANGE; 0 after Murder Holes: build.minimum, #1547).
    s: the Stats (default: stats(name); a wall of the game program: wall(), #1322).
    At 0 hit points the plugin fills the box with air. The invisibility effect hides the slime: the tag Invisible is
    only for armor stands, the server drops it on a slime (#636)."""
    x0, y0, z0, x1, y1, z1 = box
    s, size = s or stats(name), math.ceil((max(x1 - x0, z1 - z0) + 1) / SLIME)
    low = FORT_MIN_RANGE.get(name, 0) if low is None else low
    bonus = ",".join(f"{c}:{n}" for c, n in sorted(s.bonus.items())) * bool(s.attack and s.range)
    n = uuids.UUID(uuid).int
    ints = ",".join(str((n >> k & 0xFFFFFFFF) - ((n >> k & 0x80000000) << 1)) for k in (96, 64, 32, 0))
    return [f"summon slime {(x0 + x1 + 1) / 2} {y0} {(z0 + z1 + 1) / 2} {{Size:{size - 1},NoAI:1b,Silent:1b,"
            f"NoGravity:1b,PersistenceRequired:1b,{INVISIBLE},Tags:[\"aoe2mc.building\"],UUID:[I;{ints}]}}",
            f"team join p{player} {uuid}"] + \
        [f"aoe arrows {uuid} {garrison.arrows(name, inside)}"] * bool(s.attack and s.range) + \
        [f"aoe building {uuid} {s.hp} {s.melee} {s.pierce} {' '.join(map(str, box))}"   # after the arrows: no shot of 1
         + (f" {s.attack} {s.range * T} {round(s.reload / NORMAL * 20)} {low * T}"   # (#1546)
            if s.attack and s.range else "")
         + (f" {','.join(s.classes)}" if s.classes != ("building", STANDARD) or bonus else "")   # a wall, a gate, the
                                                                            # wonder (#1419), a tower (STONE, #1590)
         + (f" {bonus}" if bonus else "")]                                  # the arrow bonus (Heated Shot, #1548)


def building_box(o, ground):
    """The box (x0, y0, z0, x1, y1, z1) of a building of aoe2mc.json: its footprint from the lowest ground next to
    it ("ground" over a footprint is the top of its barriers) up HEIGHT blocks."""
    x0, z0, x1, z1 = o["footprint"]
    ring = [(x, z) for x in range(x0 - 1, x1 + 1) for z in (z0 - 1, z1)] + \
        [(x, z) for x in (x0 - 1, x1) for z in range(z0, z1)]
    ys = [int(ground[z][x]) for x, z in ring if 0 <= z < len(ground) and 0 <= x < len(ground[z])
          and ground[z][x] not in ("-", None)] or [64]
    return x0, min(ys), z0, x1 - 1, min(ys) + HEIGHT, z1 - 1
