"""
AoE2 combat values of the units and buildings of the game program (#513, epic #395: milestone D).

One table, keyed by the AoE2 unit name of `units.classify`. The values are the published AoE2 DE values of the
base unit: no Blacksmith or University upgrades, no civilization bonuses. `range` is in tiles (0: melee),
`reload` in game seconds. `bonus` is extra attack against the units of a class (`classes`): AoE2 adds it
for each armor class of the target. `damage` is the AoE2 damage rule (#514); the Paper plugin applies it
(`aoe stats` gives a mob its values, `stats_command`).
A ranged unit shoots from its AoE2 range, one shot per reload time (#515, `aoe range`, `range_command`).
The Mangonel line hits all units in its blast radius around the target (#1050, `BLAST`).
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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import units  # noqa: E402
from units import pretty  # noqa: E402

Stats = namedtuple("Stats", "hp attack melee pierce range reload bonus classes", defaults=({}, ()))

INF, ARC, CAV, CAM, ELE, SIE, SPE = "infantry", "archer", "cavalry", "camel", "elephant", "siege", "spearman"
UNI = "unique"                                        # the unique units of the castles (the Samurai bonus)
GUN = "gunpowder"                                     # the targets of the Condottiero and Winged Hussar bonus (#1007)
SPEAR = {CAV: 15, CAM: 12, ELE: 15}                   # spearman bonus, more in the later ages of the line
STATS = {
    # infantry: militia line and spearman line
    "MILITIA": Stats(40, 4, 0, 1, 0, 2.0, {}, (INF,)),
    "MAN_AT_ARMS": Stats(45, 6, 0, 1, 0, 2.0, {}, (INF,)),
    "LONG_SWORDSMAN": Stats(60, 9, 0, 1, 0, 2.0, {}, (INF,)),
    "TWO_HANDED_SWORDSMAN": Stats(60, 12, 0, 1, 0, 2.0, {}, (INF,)),
    "CHAMPION": Stats(70, 13, 1, 1, 0, 2.0, {}, (INF,)),
    "SPEARMAN": Stats(45, 3, 0, 0, 0, 3.0, SPEAR, (INF, SPE)),
    "PIKEMAN": Stats(55, 4, 0, 0, 0, 3.0, {CAV: 22, CAM: 18, ELE: 25}, (INF, SPE)),
    "HALBERDIER": Stats(60, 6, 0, 0, 0, 3.0, {CAV: 32, CAM: 26, ELE: 28}, (INF, SPE)),
    "EAGLE_SCOUT": Stats(50, 4, 0, 2, 0, 2.0, {SIE: 3}, (INF,)),               # the Dark and Feudal Age values
    "EAGLE_WARRIOR": Stats(55, 7, 0, 3, 0, 2.0, {CAM: 2, CAV: 3, SIE: 3}, (INF,)),
    "ELITE_EAGLE_WARRIOR": Stats(60, 9, 0, 4, 0, 2.0, {CAM: 3, CAV: 4, SIE: 5}, (INF,)),
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
    "PALADIN": Stats(160, 14, 2, 3, 0, 1.8, {}, (CAV,)),
    "CAMEL_RIDER": Stats(100, 6, 0, 0, 0, 2.0, {CAV: 9}, (CAM,)),
    "HEAVY_CAMEL_RIDER": Stats(120, 7, 0, 0, 0, 2.0, {CAM: 9, CAV: 18}, (CAM,)),
    "IMPERIAL_CAMEL_RIDER": Stats(140, 8, 0, 0, 0, 1.667, {"building": 2, CAM: 9, CAV: 18}, (CAM,)),
    "WAR_ELEPHANT": Stats(450, 15, 1, 2, 0, 2.0, {"building": 30}, (ELE, UNI)),
    "ELITE_WAR_ELEPHANT": Stats(600, 20, 1, 3, 0, 2.0, {"building": 30}, (ELE, UNI)),
    # unique units of the castle (#712; Throwing Axeman and Mameluke hit with melee damage in AoE2: here pierce). #1006:
    # the first projectile of Kipchak and Organ Gun, the ranged mode of the Ratha, the Castle Age Serjeant.
    # #1005: a Kamayuk hits from AoE2 range 1: a melee hit. #1041: the base values of the wiki without the civilization
    # bonus (Berserk 54 HP, Janissary 35 HP, Mangudai and Samurai reload, Genoese armor, Rattan Archer HP, Teutonic armor)
    "ARAMBAI": Stats(60, 12, 0, 1, 5, 2.0, {SIE: 2}, (ARC, CAV, UNI)),
    "BALLISTA_ELEPHANT": Stats(250, 9, 0, 3, 5, 2.5, {"building": 5}, (CAV, ELE, SIE, UNI)),
    "BERSERK": Stats(54, 12, 1, 1, 0, 2.0, {"building": 2}, (INF, UNI)),
    "BOYAR": Stats(100, 12, 4, 2, 0, 1.9, {}, (CAV, UNI)),
    "CAMEL_ARCHER": Stats(55, 7, 0, 1, 4, 2.0, {}, (ARC, CAM, UNI)),
    "CATAPHRACT": Stats(110, 9, 2, 1, 0, 1.8, {INF: 13}, (CAV, UNI)),
    "CENTURION": Stats(110, 13, 2, 3, 0, 1.9, {}, (CAV, UNI)),
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
    "HUSSITE_WAGON": Stats(160, 10, 0, 7, 6, 3.45, {SIE: 3, "building": 1}, (SIE, UNI)),
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
    "ELITE_BALLISTA_ELEPHANT": Stats(280, 10, 0, 3, 5, 2.5, {"building": 8}, (CAV, ELE, SIE, UNI)),
    "ELITE_BERSERK": Stats(62, 14, 2, 1, 0, 2.0, {"building": 3}, (INF, UNI)),
    "ELITE_BOYAR": Stats(130, 14, 8, 3, 0, 1.9, {}, (CAV, UNI)),
    "ELITE_CAMEL_ARCHER": Stats(60, 8, 1, 1, 4, 2.0, {}, (ARC, CAM, UNI)),
    "ELITE_CATAPHRACT": Stats(150, 12, 2, 1, 0, 1.7, {INF: 18}, (CAV, UNI)),
    "ELITE_CENTURION": Stats(155, 15, 3, 3, 0, 1.9, {}, (CAV, UNI)),
    "ELITE_CHU_KO_NU": Stats(50, 10, 0, 0, 4, 3.0, {SPE: 2}, (ARC, UNI)),
    "ELITE_COMPOSITE_BOWMAN": Stats(50, 4, 2, 0, 4, 2.0, {SPE: 2}, (ARC, UNI)),
    "ELITE_CONQUISTADOR": Stats(70, 19, 2, 2, 6, 2.9, {SIE: 6, "building": 2}, (ARC, CAV, UNI)),
    "ELITE_COUSTILLIER": Stats(145, 11, 2, 2, 0, 1.9, {}, (CAV, UNI)),
    "ELITE_GBETO": Stats(50, 13, 0, 0, 6, 2.0, {}, (INF, UNI)),
    "ELITE_GENOESE_CROSSBOWMAN": Stats(50, 6, 1, 0, 4, 2.0, {CAV: 7, CAM: 6, ELE: 7}, (ARC, UNI)),
    "ELITE_GHULAM": Stats(70, 11, 0, 6, 0, 2.0, {ARC: 6, "building": 2}, (INF, UNI)),
    "ELITE_HUSKARL": Stats(70, 12, 0, 8, 0, 2.0, {ARC: 10, "building": 3}, (INF, UNI)),
    "ELITE_HUSSITE_WAGON": Stats(230, 13, 1, 10, 6, 3.45, {SIE: 3, "building": 2}, (SIE, UNI)),
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
    "ELITE_GENITOUR": Stats(55, 4, 0, 4, 4, 3.0, {ARC: 5, SPE: 3}, (ARC, CAV, UNI)),
    "ELITE_STEPPE_LANCER": Stats(80, 11, 0, 2, 0, 2.0, {}, (CAV,)),
    "GENITOUR": Stats(50, 3, 0, 4, 4, 3.0, {ARC: 4, SPE: 3}, (ARC, CAV, UNI)),
    "SLINGER": Stats(35, 4, 0, 0, 5, 2.0, {INF: 4, SIE: 3, SPE: 1}, (ARC,)),
    "STEPPE_LANCER": Stats(60, 9, 0, 1, 0, 2.0, {}, (CAV,)),
    "WINGED_HUSSAR": Stats(80, 9, 1, 2, 0, 1.9, {GUN: 4}, (CAV,)),
    # units of the DLCs Dynasties of India, Return of Rome and The Three Kingdoms (#1009, AoE2 wiki, DE, base unit, no civilization bonus;
    # Iron Pagoda: reload 2.16 without the Jurchen bonus). No class here: shock infantry, rams, ships; the charged
    # attacks (Fire Lancer) and "ignores armor" (Rocket Cart) are not modeled
    "ARMORED_ELEPHANT": Stats(180, 4, -2, 140, 0, 3.0, {"building": 90, SIE: 25}, (CAV, ELE, SIE)),
    "FIRE_LANCER": Stats(65, 9, 1, 0, 0, 2.0, {"building": 1, CAV: 5, CAM: 4, ELE: 5}, (INF, GUN)),
    "GRENADIER": Stats(40, 12, 1, 1, 6, 3.45, {"building": 4, INF: 9, SIE: 3, SPE: 1}, (ARC, GUN, UNI)),
    "HEAVY_ROCKET_CART": Stats(65, 5, 0, 8, 8, 5.35, {"building": 12, SIE: 2}, (GUN, SIE)),
    "HEI_GUANG_CAVALRY": Stats(60, 11, 4, 3, 0, 1.8, {}, (CAV,)),
    "HOUFNICE": Stats(90, 50, 2, 6, 12, 6.5, {"building": 250, SIE: 20}, (GUN, SIE)),
    "IRON_PAGODA": Stats(115, 12, 1, 3, 0, 2.16, {}, (CAV, UNI)),
    "LEGIONARY": Stats(75, 12, 2, 2, 0, 2.0, {"building": 4, INF: 4}, (INF,)),
    "ROCKET_CART": Stats(45, 5, 0, 6, 7, 5.5, {"building": 7, SIE: 2}, (GUN, SIE)),
    "SIEGE_ELEPHANT": Stats(220, 4, -2, 150, 0, 3.0, {"building": 105, SIE: 35}, (CAV, ELE, SIE)),
    "TRACTION_TREBUCHET": Stats(115, 50, 1, 8, 14, 11.0, {"building": 230}, (SIE,)),
    "WHITE_FEATHER_GUARD": Stats(95, 7, 0, 2, 0, 2.0, {"building": 2, CAV: 8, CAM: 6, ELE: 8}, (INF, UNI)),
    # siege
    "MANGONEL": Stats(50, 40, 0, 6, 7, 6.0, {"building": 35}, (SIE,)),
    "ONAGER": Stats(60, 55, 0, 8, 8, 6.0, {"building": 45, SIE: 12}, (SIE,)),
    "SIEGE_ONAGER": Stats(70, 75, 0, 8, 8, 6.0, {"building": 60, SIE: 12}, (SIE,)),
    "SCORPION": Stats(40, 12, 0, 6, 7, 3.6, {ELE: 6}, (SIE,)),
    "HEAVY_SCORPION": Stats(60, 14, 1, 8, 7, 3.6, {"building": 6, ELE: 10, INF: 2}, (SIE,)),
    "BATTERING_RAM": Stats(175, 2, -3, 180, 0, 5.0, {"building": 125}, (SIE,)),
    "CAPPED_RAM": Stats(200, 3, -2, 190, 0, 5.0, {"building": 160, SIE: 50}, (SIE,)),
    "SIEGE_RAM": Stats(270, 4, -1, 195, 0, 5.0, {"building": 200, SIE: 65}, (SIE,)),
    "SIEGE_TOWER": Stats(220, 0, 0, 100, 0, 0.0, {}, (SIE,)),
    "TREBUCHET": Stats(200, 200, 2, 150, 16, 10.0, {"building": 250}, (SIE,)),
    "BOMBARD_CANNON": Stats(80, 40, 2, 5, 12, 6.5, {"building": 200}, (GUN, SIE)),
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
    # others: no fight, but they can die
    "VILLAGER": Stats(25, 3, 0, 0, 0, 2.0),
    "KING": Stats(75, 0, 0, 0, 0, 0.0),
    "MONK": Stats(30, 0, 0, 0, 9, 0.0),
}
# Buildings: hit points, melee and pierce armor (Dark Age base). The high pierce armor makes arrows weak, as in AoE2.
BUILDINGS = {
    "HOUSE": Stats(550, 0, 0, 7, 0, 0.0, {}, ("building",)),
    "BARRACKS": Stats(1200, 0, 0, 7, 0, 0.0, {}, ("building",)),
    "ARCHERY_RANGE": Stats(1500, 0, 0, 7, 0, 0.0, {}, ("building",)),
    "STABLE": Stats(1500, 0, 0, 7, 0, 0.0, {}, ("building",)),
    "MONASTERY": Stats(2100, 0, 0, 7, 0, 0.0, {}, ("building",)),
    "SIEGE_WORKSHOP": Stats(2100, 0, 0, 7, 0, 0.0, {}, ("building",)),
    "TOWN_CENTER": Stats(2400, 5, 3, 5, 6, 2.0, {}, ("building",)),
    "CASTLE": Stats(4800, 11, 8, 11, 8, 2.0, {}, ("building",)),
}
# Line of sight in tiles (AoE2 DE, base unit) where it is not max(4, range + 2) (sight()).
SIGHT = {
    "CHAMPION": 5,
    "LIGHT_CAVALRY": 8,
    "TWO_HANDED_SWORDSMAN": 5,
}
# Units that attack from a range with melee damage (AoE2): their hit takes the melee armor of the target (#800).
MELEE_RANGED = {"ELITE_GBETO",
                "ELITE_MAMELUKE",
                "ELITE_THROWING_AXEMAN",
                "GBETO",
                "HEAVY_ROCKET_CART",
                "MAMELUKE",
                "MANGONEL",
                "ONAGER",
                "ROCKET_CART",
                "SIEGE_ONAGER",
                "THROWING_AXEMAN",
                "TRACTION_TREBUCHET"}
# Blast radius in tiles of the units whose shot hits all units near the target, also own units (AoE2 DE, wiki "AOE";
# AoE2 tapers the damage at the edge, here each unit in the radius takes the full damage() hit, #1050).
BLAST = {"BOMBARD_CANNON": 0.5,
         "HEAVY_ROCKET_CART": 1.25,
         "HOUFNICE": 0.7,
         "MANGONEL": 1.0,
         "ONAGER": 1.25,
         "ROCKET_CART": 1.0,
         "SIEGE_ONAGER": 1.5}
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
    plugin then lets the minecart shoot too (#1050)."""
    s = s or stats(name)
    cart = (units.classify(name) or {}).get("id") == "minecraft:minecart"
    blast = f" {BLAST.get(name, 0) * T}" if name in BLAST or cart else ""
    return s.range and s.reload and f"aoe range {uuid} {s.range * T} {max(1, round(s.reload / rate * 20))}{blast}" or None


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
    "stand_ground" attacks only an enemy in its range and keeps its place; "aggressive" is the default."""
    if stance not in STANCES:
        raise ValueError(f"unknown stance: {stance}")
    return f"aoe stance {uuid} {stance}"


def setup(game, data):
    """Give each unit of the players in `aoe2mc.json` data its AoE2 values; Gaia animals keep the vanilla values.
    Each building of a player with AoE2 hit points gets a target of attacks (`building`).
    The entities must be loaded (forceload). Returns the number of units that got the values."""
    ground = [r.split() for r in data.get("ground", ())]
    for o in data["objects"]:
        if o["kind"] == "building" and o["player"] and "footprint" in o and o["name"] in BUILDINGS:
            uuid = target_uuid(o["footprint"])
            for c in building(uuid, o["name"], o["player"], building_box(o, ground)) + [label_command(uuid, o["name"])]:
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


def building(uuid, name, player, box):
    """The commands that make building `name` of `player` a target of attacks (#517): an invisible slime without AI
    that fills the footprint takes the attacks (a mob attacks only a living entity: AoePlugin.java), and the plugin
    keeps the AoE2 hit points. box: the blocks (x0, y0, z0, x1, y1, z1), both ends included, y0 the ground.
    At 0 hit points the plugin fills the box with air. The invisibility effect hides the slime: the tag Invisible is
    only for armor stands, the server drops it on a slime (#636)."""
    x0, y0, z0, x1, y1, z1 = box
    s, size = stats(name), math.ceil((max(x1 - x0, z1 - z0) + 1) / SLIME)
    n = uuids.UUID(uuid).int
    ints = ",".join(str((n >> k & 0xFFFFFFFF) - ((n >> k & 0x80000000) << 1)) for k in (96, 64, 32, 0))
    return [f"summon slime {(x0 + x1 + 1) / 2} {y0} {(z0 + z1 + 1) / 2} {{Size:{size - 1},NoAI:1b,Silent:1b,"
            f"NoGravity:1b,PersistenceRequired:1b,{INVISIBLE},Tags:[\"aoe2mc.building\"],UUID:[I;{ints}]}}",
            f"team join p{player} {uuid}", f"aoe building {uuid} {s.hp} {s.melee} {s.pierce} {' '.join(map(str, box))}"]


def building_box(o, ground):
    """The box (x0, y0, z0, x1, y1, z1) of a building of aoe2mc.json: its footprint from the lowest ground next to
    it ("ground" over a footprint is the top of its barriers) up HEIGHT blocks."""
    x0, z0, x1, z1 = o["footprint"]
    ring = [(x, z) for x in range(x0 - 1, x1 + 1) for z in (z0 - 1, z1)] + \
        [(x, z) for x in (x0 - 1, x1) for z in range(z0, z1)]
    ys = [int(ground[z][x]) for x, z in ring if 0 <= z < len(ground) and 0 <= x < len(ground[z])
          and ground[z][x] != "-"] or [64]
    return x0, min(ys), z0, x1 - 1, min(ys) + HEIGHT, z1 - 1
