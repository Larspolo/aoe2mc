"""
AoE2 combat values of the units and buildings of the game program (#513, epic #395: milestone D).

One table, keyed by the AoE2 unit name of `units.classify`. The values are the published AoE2 DE values of the
base unit: no Blacksmith or University upgrades, no civilization bonuses. `range` is in tiles (0: melee),
`reload` in game seconds. `bonus` is extra attack against the units of a class (`classes`): AoE2 adds it
for each armor class of the target. The damage rule itself is in the next ticket (#514).
"""
from collections import namedtuple

Stats = namedtuple("Stats", "hp attack melee pierce range reload bonus classes", defaults=({}, ()))

INF, ARC, CAV, CAM, ELE, SIE, SPE = "infantry", "archer", "cavalry", "camel", "elephant", "siege", "spearman"
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
    # archers: the attack is pierce damage
    "ARCHER": Stats(30, 4, 0, 0, 4, 2.0, {SPE: 3}, (ARC,)),
    "CROSSBOWMAN": Stats(35, 5, 0, 0, 5, 2.0, {SPE: 3}, (ARC,)),
    "ARBALESTER": Stats(40, 6, 0, 0, 5, 2.0, {SPE: 3}, (ARC,)),
    "SKIRMISHER": Stats(30, 2, 0, 3, 4, 3.0, {ARC: 3, SPE: 3}, (ARC,)),
    "ELITE_SKIRMISHER": Stats(35, 3, 0, 4, 5, 3.0, {ARC: 4, SPE: 3}, (ARC,)),
    "LONGBOWMAN": Stats(35, 6, 0, 1, 5, 2.0, {SPE: 3}, (ARC,)),
    "CAVALRY_ARCHER": Stats(50, 6, 0, 0, 4, 2.0, {SPE: 2}, (ARC, CAV)),
    # cavalry
    "SCOUT_CAVALRY": Stats(45, 3, 0, 2, 0, 2.0, {}, (CAV,)),
    "LIGHT_CAVALRY": Stats(60, 7, 0, 2, 0, 2.0, {}, (CAV,)),
    "KNIGHT": Stats(100, 10, 2, 2, 0, 1.8, {}, (CAV,)),
    "CAVALIER": Stats(120, 12, 2, 2, 0, 1.8, {}, (CAV,)),
    "PALADIN": Stats(160, 14, 2, 3, 0, 1.8, {}, (CAV,)),
    "CAMEL_RIDER": Stats(100, 6, 0, 0, 0, 2.0, {CAV: 9}, (CAM,)),
    "WAR_ELEPHANT": Stats(450, 15, 1, 2, 0, 2.0, {"building": 7}, (ELE,)),
    # siege
    "MANGONEL": Stats(50, 40, 0, 6, 7, 6.0, {"building": 35}, (SIE,)),
    "SCORPION": Stats(40, 12, 0, 6, 7, 3.6, {ELE: 6}, (SIE,)),
    "BATTERING_RAM": Stats(175, 2, -3, 180, 0, 5.0, {"building": 125}, (SIE,)),
    "SIEGE_TOWER": Stats(220, 0, 0, 100, 0, 0.0, {}, (SIE,)),
    "TREBUCHET": Stats(200, 200, 2, 150, 16, 10.0, {"building": 250}, (SIE,)),
    "BOMBARD_CANNON": Stats(80, 40, 2, 5, 12, 6.5, {"building": 200}, (SIE,)),
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
DEFAULT, BUILDING = Stats(40, 4, 0, 0, 0, 2.0), Stats(1000, 0, 0, 7, 0, 0.0, {}, ("building",))


def stats(name):
    """The combat values of an AoE2 unit or building; an unknown name gets a militia-like unit."""
    return STATS.get(name) or BUILDINGS.get(name) or (BUILDING if name.endswith(("_WALL", "_GATE", "_TOWER")) else DEFAULT)
