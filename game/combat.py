"""
AoE2 combat values of the units and buildings of the game program (#513, epic #395: milestone D).

One table (`STATS`, one line per unit in `data/units.jsonl`, #1912), keyed by the AoE2 unit name of `units.classify`.
The values are the published AoE2 DE values of the base unit: no Blacksmith or University upgrades, no civilization
bonuses. `range` is in tiles (0: melee), `reload` in game seconds. `bonus` is extra attack against the units of a
class (`classes`): AoE2 adds it for each armor class of the target. `damage` is the AoE2 damage rule (#514); the Paper plugin applies it
(`aoe stats` gives a mob its values, `stats_command`).
A ranged unit shoots from its AoE2 range, one shot per reload time (#515, `aoe range`, `range_command`).
The Mangonel line hits all units in its blast radius around the target (#1050, `BLAST`). It does not shoot at a target inside its minimum range (`MIN_RANGE`, #1350).
A melee unit hits once per reload time too (#848, the last value of `stats_command`).
An idle soldier attacks the nearest enemy unit in its AoE2 line of sight (#775, `aoe sight`, `sight_command`); rams,
trebuchets, Armored Elephants and Cannon Galleons also take the nearest enemy building in it (#1820, `BUILDING_SIGHT`).
"""
import math
import os
import sys
import uuid as uuids
from collections import namedtuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gather import NORMAL  # noqa: E402
import civs  # noqa: E402
import garrison  # noqa: E402
import table  # noqa: E402

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
# The values of each unit: one line per unit in data/units.jsonl (#1912). "note" is the source of a value.
STATS = {r["name"]: Stats(**{f: r[f] for f in Stats._fields if f != "classes"}, classes=tuple(r["classes"]))
         for r in table.load("units.jsonl")}
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
# Line of sight in tiles (AoE2 DE, wiki infobox "LOS"; the house: 1 from the edge of its 2 x 2 tiles, #1300) where it
# is not max(4, range + 2) (sight()). A unit of more ages has its first value; the infantry values have the +2 of the
# Feudal Age, as the infobox shows them (tests/test_unit_sight.py, #1878).
SIGHT = {
    "ALFRED_THE_ALPACA": 6,
    "ARCHERY_RANGE": 6,
    "ARMORED_ELEPHANT": 6,
    "BARRACKS": 6,
    "BATTERING_RAM": 5,
    "BATTLE_ELEPHANT": 7,
    "BERSERK": 5,
    "BLACKSMITH": 6,
    "BOMBARD_TOWER": 10,
    "BOYAR": 5,
    "CAMEL_ARCHER": 5,
    "CAMEL_RIDER": 5,                                                  # the wiki infobox (#1550)
    "CANNON_GALLEON": 15,
    "CAPPED_RAM": 5,
    "CASTLE": 11,
    "CAVALRY_ARCHER": 5,
    "CHAKRAM_THROWER": 9,
    "CHAMPION": 7,
    "COMPOSITE_BOWMAN": 7,
    "CONDOTTIERO": 8,
    "COUSTILLIER": 5,
    "DEMOLITION_RAFT": 6,
    "DEMOLITION_SHIP": 6,
    "EAGLE_SCOUT": 5,
    "EAGLE_WARRIOR": 8,
    "ELITE_BATTLE_ELEPHANT": 8,
    "ELITE_BERSERK": 7,
    "ELITE_BOYAR": 5,
    "ELITE_CAMEL_ARCHER": 5,
    "ELITE_CATAPHRACT": 5,
    "ELITE_CHAKRAM_THROWER": 10,
    "ELITE_COMPOSITE_BOWMAN": 7,
    "ELITE_CONQUISTADOR": 9,
    "ELITE_COUSTILLIER": 5,
    "ELITE_EAGLE_WARRIOR": 8,
    "ELITE_GBETO": 9,
    "ELITE_GENOESE_CROSSBOWMAN": 8,
    "ELITE_GHULAM": 8,
    "ELITE_HUSKARL": 7,
    "ELITE_JAGUAR_WARRIOR": 7,
    "ELITE_KAMAYUK": 7,
    "ELITE_KARAMBIT_WARRIOR": 5,
    "ELITE_KESHIK": 5,
    "ELITE_KONNIK": 5,
    "ELITE_LEITIS": 5,
    "ELITE_MAGYAR_HUSZAR": 6,
    "ELITE_MONASPA": 5,
    "ELITE_OBUCH": 5,
    "ELITE_PLUMED_ARCHER": 6,
    "ELITE_RATTAN_ARCHER": 6,
    "ELITE_SAMURAI": 7,
    "ELITE_SERJEANT": 7,
    "ELITE_SHOTEL_WARRIOR": 5,
    "ELITE_TARKAN": 7,
    "ELITE_TEUTONIC_KNIGHT": 7,
    "ELITE_URUMI_SWORDSMAN": 5,
    "ELITE_WAR_ELEPHANT": 8,
    "ELITE_WAR_WAGON": 8,
    "ELITE_WOAD_RAIDER": 7,
    "FAST_FIRE_SHIP": 6,
    "DOCK": 8,
    "DONJON": 10,
    "ELITE_CANNON_GALLEON": 17,
    "ELITE_GENITOUR": 6,                                               # the wiki infobox (#1610)
    "ELITE_SHRIVAMSHA_RIDER": 6,
    "ELITE_STEPPE_LANCER": 5,
    "FIRE_GALLEY": 5,
    "FIRE_LANCER": 7,
    "FIRE_SHIP": 5,
    "FISHING_SHIP": 5,
    "FLEMISH_MILITIA": 7,
    "FURIOUS_THE_MONKEY_BOY": 12,
    "GALLEON": 9,
    "GBETO": 8,
    "GENGHIS_KHAN": 4,
    "GENITOUR": 5,
    "GENOESE_CROSSBOWMAN": 8,
    "GHULAM": 8,
    "GRENADIER": 9,
    "HALBERDIER": 6,
    "HEAVY_DEMOLITION_SHIP": 6,
    "HULK": 5,
    "FEITORIA": 6,
    "FORTIFIED_TOWER": 14,
    "GUARD_TOWER": 10,
    "HEAVY_CAMEL_RIDER": 5,
    "HOUSE": 2,
    "HUSKARL": 5,
    "HUSSAR": 10,
    "IMPERIAL_CAMEL_RIDER": 5,
    "IRON_PAGODA": 5,
    "JAGUAR_WARRIOR": 5,
    "JANISSARY": 10,
    "KAMAYUK": 6,
    "KARAMBIT_WARRIOR": 5,
    "KEEP": 10,
    "KESHIK": 5,
    "KING": 6,
    "KONNIK": 5,
    "KREPOST": 10,
    "LEGIONARY": 7,
    "LEITIS": 5,
    "LIGHT_CAVALRY": 8,
    "LONG_SWORDSMAN": 6,
    "LUMBER_CAMP": 6,
    "MAGYAR_HUSZAR": 5,
    "MAN_AT_ARMS": 6,
    "MARKET": 6,
    "MILL": 6,
    "MINING_CAMP": 6,
    "MONASTERY": 6,
    "OBUCH": 5,
    "ORGAN_GUN": 8,
    "OUTPOST": 4,
    "PALADIN": 5,
    "PIKEMAN": 6,
    "SABOTEUR": 6,
    "SAMURAI": 6,
    "SERJEANT": 5,
    "SHARKATZOR": 11,
    "SHOTEL_WARRIOR": 5,
    "SIEGE_ELEPHANT": 6,
    "SIEGE_RAM": 5,
    "SIEGE_TOWER": 6,
    "SIEGE_WORKSHOP": 6,
    "SHRIVAMSHA_RIDER": 5,
    "STABLE": 6,
    "STEPPE_LANCER": 5,
    "TARKAN": 5,
    "TEUTONIC_KNIGHT": 5,
    "TOWN_CENTER": 8,
    "TRACTION_TREBUCHET": 18,
    "TRADE_CART": 7,
    "TRADE_COG": 6,
    "TRANSPORT_SHIP": 5,
    "TREBUCHET": 19,
    "TWO_HANDED_SWORDSMAN": 7,
    "UNIVERSITY": 6,
    "URUMI_SWORDSMAN": 5,
    "WAR_ELEPHANT": 7,
    "WAR_HULK": 5,
    "WAR_PENGUIN": 6,
    "WAR_WAGON": 7,
    "WATCH_TOWER": 10,
    "WINGED_HUSSAR": 10,
    "WOAD_RAIDER": 5,
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


# The units that also take enemy buildings in their sight (#1820, AoE2 wiki "Siege unit (Age of Empires II)": "Battering
# Ram line automatically attack only buildings", "Trebuchets automatically attack only buildings", "The Armored
# Elephant and Cannon Galleon lines prioritize attacking enemy buildings over units"): "only" or "first".
BUILDING_SIGHT = {
    "ARMORED_ELEPHANT": "first",
    "BATTERING_RAM": "only",
    "CANNON_GALLEON": "first",
    "CAPPED_RAM": "only",
    "ELITE_CANNON_GALLEON": "first",
    "SIEGE_ELEPHANT": "first",
    "SIEGE_RAM": "only",
    "TREBUCHET": "only",
}


def sight_command(uuid, name, T, s=None):
    """The plugin command that lets an idle soldier attack the nearest enemy unit in its line of sight (tiles * T
    blocks, #775), and the enemy buildings for the units of BUILDING_SIGHT (#1820). None for a unit that does not
    fight (villager, monk, king)."""
    s = s or stats(name)
    mode = f" {BUILDING_SIGHT[name]}" if name in BUILDING_SIGHT else ""
    return f"aoe sight {uuid} {sight(name, s) * T}{mode}" if s.classes and s.attack else None


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
            uuid, civ = target_uuid(o["footprint"]), data.get("players", {}).get(str(o["player"]), {}).get("civ")
            for c in building(uuid, o["name"], o["player"], building_box(o, ground), data.get("tile_size", 4),
                              held.get(o.get("ref"), ()), civs.hp(civ, o["name"], stats(o["name"]))) \
                    + [label_command(uuid, o["name"])]:
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
