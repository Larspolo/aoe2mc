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
from gather import NORMAL, predator  # noqa: E402
import civs  # noqa: E402
import garrison  # noqa: E402
import table  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import units  # noqa: E402
from units import pretty  # noqa: E402

Stats = namedtuple("Stats", "hp attack melee pierce range reload bonus classes blast", defaults=({}, (), 0))

INF, ARC, CAV, CAM, ELE, SIE, SPE = "infantry", "archer", "cavalry", "camel", "elephant", "siege", "spearman"
HSI = "heavysiege"                                    # the Hussite Wagon and Ballista Elephant lines (wiki "Armor class", #1402)
RAM = "ram"                                           # the rams, the siege tower, the unpacked trebuchet, the Armored Elephant line
UNI = "unique"                                        # the unique units of the castles (the Samurai bonus)
GUN = "gunpowder"                                     # the targets of the Condottiero and Winged Hussar bonus (#1007)
SHIP, WAR = "ship", "warship"                         # the ships; "warship": the AoE2 class "Long-range warship"
FIRE = "fireship"                                     # the AoE2 class "Fire Ships" (the hulk bonus, #1489)
# The values of each unit: one line per unit in data/units.jsonl (#1912). "note" is the source of a value.
UNIT_ROWS = table.load("units.jsonl")
STATS = {r["name"]: Stats(**{f: r[f] for f in Stats._fields[:-2]}, classes=tuple(r["classes"]), blast=r.get("blast", 0))
         for r in UNIT_ROWS}                                    # blast: the radius that technologies change (#4283)
REPAIRS = {r["name"]: r["repairs"] for r in UNIT_ROWS if "repairs" in r}   # a soldier that repairs a building (#2128)
# Buildings: hit points, melee and pierce armor (Dark Age base), one line per building in data/buildings.jsonl (#1913).
# The high pierce armor makes arrows weak, as in AoE2. The towers have the AoE2 DE values of the wiki: a watch tower of
# the Castle Age (850 hit points in the Feudal Age), #1112. The attack against ships: the "Attack bonus" of the wiki
# infobox (#1564; the dock: the Castle Age). A line with only a "sight" has no target.
BUILDING_ROWS = table.load("buildings.jsonl")
STANDS_FOR = {r["name"]: r["as"] for r in BUILDING_ROWS if "as" in r}   # a regional building: the one it replaces (#1874, #1930)
BUILDINGS = {r["name"]: Stats(**{f: r[f] for f in Stats._fields[:-2]}, classes=tuple(r["classes"]))
             for r in BUILDING_ROWS if "hp" in r}
# The walls that a player builds in the game program (#1322, AoE2 DE wiki infobox): the hit points in the Dark, Feudal,
# Castle and Imperial Age, the melee and the pierce armor. Their targets have WALL_TAG: a wall keeps no player alive in
# the conquest (conquest.alive). The walls of the map have no target.
WALLS = {r["name"]: (tuple(r["hp_ages"]), r["melee"], r["pierce"]) for r in BUILDING_ROWS if "hp_ages" in r}
WALL_TAG = "aoe2mc.wall"
WALL = "wall"   # the AoE2 class "Walls and Gates" (wiki "Armor class"): the petard gets +900 against it (#2192)
# The AoE2 class "Standard Buildings" (wiki "Armor class"): all buildings but the walls, the gates and the wonder. Arson
# gives infantry a bonus against it (#1419).
STANDARD = "standard"
BUILDINGS = {k: s if k == "WONDER" else s._replace(classes=s.classes + (STANDARD,)) for k, s in BUILDINGS.items()}
# The AoE2 class "Stone Defense" (wiki infobox "Class"): the stone walls and gates, the towers and the Donjon
# (#1873), not the castle and not the palisades. The villager gets a bonus against it (#1590).
STONE = "stone"
STONE_ROWS = {r["name"] for r in BUILDING_ROWS if r.get("stone")}   # "stone": true in buildings.jsonl (#1873)
BUILDINGS = {k: s._replace(classes=s.classes + (STONE,)) if k.endswith("_TOWER") or k == "KEEP" or k in STONE_ROWS else s
             for k, s in BUILDINGS.items()}
WATCH = 4    # tiles of line of sight that Town Watch adds to each own building but walls, gates, farms, fish traps (#1454)
# Line of sight in tiles (AoE2 DE, wiki infobox "LOS"; the house: 1 from the edge of its 2 x 2 tiles, #1300) where it
# is not max(4, range + 2) (sight()). A unit of more ages has its first value; the infantry values have the +2 of the
# Feudal Age, as the infobox shows them (#1878). The key "sight" of a line in the data files (#1913).
SIGHT = {r["name"]: r["sight"] for r in UNIT_ROWS + BUILDING_ROWS if "sight" in r}
# Units that attack from a range with melee damage (AoE2): their hit takes the melee armor of the target (#800).
# The key "melee_ranged" of a line of data/units.jsonl.
MELEE_RANGED = {r["name"] for r in UNIT_ROWS if r.get("melee_ranged")}
# Blast radius in tiles of the units whose shot hits all units near the target, also own units (AoE2 DE, wiki "AOE";
# AoE2 tapers the damage at the edge, here each unit in the radius takes the full damage() hit, #1050). A ship has no
# vanilla shot: the fire ship (0: it hits only the target) and the demolition ship (#1440) shoot as a siege unit, and
# the creeper crew of the demolition ship dies after its blast (AoePlugin.java), as a vanilla creeper.
# The key "blast" of a line of data/units.jsonl.
BLAST = {r["name"]: r["blast"] for r in UNIT_ROWS if "blast" in r}
# The key "attack_ground": the units of the AoE2 order Attack Ground (#4079, docs/research/gameplay.md).
GROUND = {r["name"] for r in UNIT_ROWS if r.get("attack_ground")}
RAM_REACH = 2.0       # blocks: a ram (a minecart with range 0) hits from next to its target, on its carrier (#1399)
CONTACT = 1.0         # tiles: the reach of a demolition ship (range 0, #1440): its raft is higher than a boat
# Tiles: no shot at a unit nearer (AoE2 DE, wiki infobox "MinRange", #1350). The key "min_range" of data/units.jsonl.
MIN_RANGE = {r["name"]: r["min_range"] for r in UNIT_ROWS if "min_range" in r}
ACCURACY = {r["name"]: r["accuracy"] for r in UNIT_ROWS if "accuracy" in r}   # siege shots at units that hit (#2479)
# The minimum range of the buildings that shoot, in tiles from the edge of the footprint (AoE2 DE, wiki infobox
# "MinRange", #1546). The town center has none. Murder Holes removes it.
# The key "min_range" of a line of data/buildings.jsonl (the dock shoots only with fishing ships inside, #1949).
FORT_MIN_RANGE = {r["name"]: r["min_range"] for r in BUILDING_ROWS if "min_range" in r}
# Tiles that a bolt flies past the range and hurts the enemy units on its line with half the damage (AoE2 DE, wiki
# "Pass-through damage": "Projectiles travel Range+2 tiles in total", no friendly fire, #1401). The chakram thrower
# throws as a mob (no blast), with the full damage on its line (PASS_PART, #1638).
# Gold per AoE2 minute while the unit attacks enemy units, not buildings (AoE2 DE wiki: the Varangian Guard 35, #2376).
# The key "attack_gold" of data/units.jsonl; game/spoils.py gives it.
ATTACK_GOLD = {r["name"]: r["attack_gold"] for r in UNIT_ROWS if "attack_gold" in r}
REGEN = {r["name"]: r["regen"] for r in UNIT_ROWS if "regen" in r}             # the key "regen": hit points per minute (#2688)
PASS = {r["name"]: r["pass"] for r in UNIT_ROWS if "pass" in r}               # the key "pass" of data/units.jsonl
# The part of the damage on the units behind the target, when it is not one half (wiki: "100% pass-through damage").
PASS_PART = {r["name"]: r["pass_part"] for r in UNIT_ROWS if "pass_part" in r}
DEFAULT, BUILDING = Stats(40, 4, 0, 0, 0, 2.0), Stats(1000, 0, 0, 7, 0, 0.0, {}, ("building",))
SLIME = 0.52                    # blocks of width and height per slime size: the target of a building (#517)
INVISIBLE = 'active_effects:[{id:"minecraft:invisibility",duration:-1,show_particles:0b}]'   # for ever, no particles
HEIGHT = 40                     # blocks above the ground that a fallen building clears


def stats(name):
    """The combat values of an AoE2 unit or building; an unknown name gets a militia-like unit. All villager names
    (VILLAGER_MALE, VILLAGER_FEMALE_FARMER ...) get the villager values (#655)."""
    return STATS.get("VILLAGER" if name.startswith("VILLAGER") else name) or BUILDINGS.get(name) or (BUILDING if name.endswith(("_WALL", "_GATE", "_TOWER")) else DEFAULT)


def damage(attacker, target, a=None, t=None, taken=1.0):
    """AoE2 damage of one hit: max(1, attack - armor + bonus). Melee hits the melee armor, a ranged unit the pierce armor
    (but a MELEE_RANGED unit the melee armor). a and t: other values of the two units (train.stats); taken: the factor
    of the bonus damage that the target takes (civs.taken, Sicilian units, #2248), rounded half up as in the plugin."""
    a, t = a or stats(attacker), t or stats(target)
    armor = t.pierce if a.range and attacker not in MELEE_RANGED else t.melee
    return max(1, max(0, a.attack - armor) + math.floor(sum(a.bonus.get(c, 0) for c in t.classes) * taken + 0.5))


def elevation(dy, H, attacker_civ=None, target_civ=None):
    """The factor of the damage of a hit from dy blocks above the target (#2307, AoE2 wiki "Elevation"; the same rule
    in AoePlugin.java): one elevation level (H blocks) or more higher: the "up" factor of the attacker's civilization
    times the "high" factor of the target's; one level or more lower: the "low" factor of the target's; else 1. The
    damage is max(1, damage * factor), the AoE2 order: the factor comes after the armor."""
    if H <= 0 or abs(dy) < H:
        return 1.0
    return civs.elevation(attacker_civ)[0] * civs.elevation(target_civ)[2] if dy > 0 else civs.elevation(target_civ)[1]


def elevation_command(data):
    """The plugin command of the elevation rule (#2307): the blocks of one level, and the factors up:low:high of each
    player's team (civs.elevation). None for data without a level height."""
    if not data.get("level_height"):
        return None
    players = sorted(data.get("players", {}).items(), key=lambda p: int(p[0]))
    return " ".join([f"aoe elevation {data['level_height']}"] + [f"p{n}:" + ":".join(f"{f:g}" for f in
                                                                   civs.elevation(full.get("civ"))) for n, p in players
                                                                   for full in [{} if data.get("full_tech_tree") else p]])


def stats_command(uuid, name, s=None, taken=1.0, friendly=1.0):
    """The plugin command that gives entity `uuid` the values of AoE2 unit `name` (or the values s, for example with
    technologies, #655): max_health = hit points (at most 1024, the limit of the attribute), the lost hit points stay lost
    (a new unit has full health, #940), and the values of `damage` (the same rule in AoePlugin.java). The range kind:
    0 melee, 1 ranged, 2 ranged with melee damage (MELEE_RANGED, #800). Then the reload in ticks at Normal speed: a melee unit hits once per reload (#848). Last, only when it is
    not 1, the factor of the bonus damage that the unit takes (civs.taken, #2248), and when friendly is not 1, the factor
    of the friendly fire that it takes (civs.friendly, #2418)."""
    s = s or stats(name)
    bonus = ",".join(f"{c}:{n}" for c, n in sorted(s.bonus.items())) or "-"
    kind = 0 if s.range <= 0 else 2 if name in MELEE_RANGED else 1
    return (f"aoe stats {uuid} {min(s.hp, 1024)} {s.attack} {s.melee} {s.pierce} {kind} "
            f"{','.join(s.classes) or '-'} {bonus} {round(s.reload / NORMAL * 20) or 20}"
            + f" {taken:g}" * (taken != 1 or friendly != 1) + f" {friendly:g}" * (friendly != 1))


def label_command(uuid, name=None):
    """The plugin command that shows the name line of a unit again (after a selection change), or with a name sets the name
    of a building target (#661): the name and 5 hearts, visible only when the unit is hurt or selected (AoePlugin.java).
    The units keep the name of the converter: `aoe stats` takes it."""
    return f"aoe label {uuid}" + (f" {pretty(name)}" if name else "")


def ballistics(g, entry):
    """The research of Ballistics (the key "on_research" of data/train.jsonl, #3243): on Paper the plugin aims the
    arrows of the player at the place where a moving target will be (#1549)."""
    if getattr(g, "paper", False):
        g.command(f"aoe ballistics p{g.player} on")

def range_command(uuid, name, T, rate=NORMAL, s=None):
    """The plugin command that lets a ranged unit shoot from its AoE2 range (tiles * T blocks), with one shot per
    reload time at `rate` game seconds per real second (default: Normal game speed, as the walk speed). None for a
    melee unit. s: the values with technologies (Fletching, #724), default those of AoE2 unit name. A siege unit (a
    minecart, or the horse of a War Wagon: units.wagon, #2746) gets its blast radius in blocks last, 0 when its shot hits
    only the target (the Scorpion, #1062): the plugin then lets the minecart (or the horse) shoot too (#1050). Then its minimum range in blocks (MIN_RANGE, #1350), when it has
    one: it does not shoot at a target nearer than that. Then the blocks of PASS (#1401): its bolt hurts the enemy units on
    its line up to that far past its range, and the part of the damage (PASS_PART) when it is not one half. A unit that
    shoots as a mob and has a PASS (the chakram thrower, #1638) gets "-" for the blast. A melee siege unit (the ram line, range 0) gets the reach
    RAM_REACH: a carrier pig has no melee goal, so the range goal walks it to the target and hits (#1399). A demolition
    ship (#1440) gets the reach CONTACT: its blast goes off next to the target."""
    s = s or stats(name)
    cart = (units.classify(name) or {}).get("id") == "minecraft:minecart" or units.wagon(name)   # (#2746)
    blast = f" {round(s.blast * T, 6)}" if name in BLAST or cart or name in GROUND else " -" if name in PASS else ""   # s.blast: BLAST, technologies; GROUND: aoe attackground needs it (#4207)
    blast += f" {MIN_RANGE.get(name, 0) * T}" * bool(blast and (name in MIN_RANGE or name in PASS))
    blast += f" {PASS.get(name, 0) * T}" * bool(blast and name in PASS) + f" {PASS_PART.get(name)}" * (name in PASS_PART)
    reach = s.range * T or RAM_REACH * bool(cart and s.attack) or CONTACT * T * bool(name in BLAST and s.attack)
    return reach and (s.reload or name in BLAST) and f"aoe range {uuid} {reach} {max(1, round(s.reload / rate * 20))}{blast}" or None


def accuracy_command(uuid, name, bonus=0.0):
    """The plugin command of the AoE2 accuracy of a siege shot at a unit (the key "accuracy" of data/units.jsonl: the
    Trebuchet 15 %, #2479) plus bonus (the civilization key "accuracy": Huns +35 %), or None when each shot hits."""
    part = min(1.0, ACCURACY.get(name, 1.0) + bonus)
    return f"aoe accuracy {uuid} {part:g}" if part < 1 else None


def sight(name, s=None):
    """The AoE2 line of sight of unit name in tiles: an idle soldier attacks an enemy in it. Most units see 4 tiles,
    a ranged unit about 2 tiles more than its range."""
    s = s or stats(name)
    return SIGHT.get(name, max(4, s.range + 2))


# The units that also take enemy buildings in their sight (#1820, AoE2 wiki "Siege unit (Age of Empires II)": "Battering
# Ram line automatically attack only buildings", "Trebuchets automatically attack only buildings", "The Armored
# Elephant and Cannon Galleon lines prioritize attacking enemy buildings over units"): "only" or "first".
BUILDING_SIGHT = {r["name"]: r["building_sight"] for r in UNIT_ROWS if "building_sight" in r}   # data/units.jsonl
FIGHTERS = {r["name"] for r in UNIT_ROWS if r.get("fighter")}   # no armor class, but fights as a soldier (#1995)


def sight_command(uuid, name, T, s=None, more=0):
    """The plugin command that lets an idle soldier attack the nearest enemy unit in its line of sight (tiles * T
    blocks, #775), and the enemy buildings for the units of BUILDING_SIGHT (#1820). None for a unit that does not
    fight (villager, monk, king): no armor class, except the FIGHTERS (Furious the Monkey Boy, #1995) and the predators
    (#3397). more: tiles of sight of the technologies (train.sight_more, #3981)."""
    s = s or stats(name)
    mode = f" {BUILDING_SIGHT[name]}" if name in BUILDING_SIGHT else ""
    fights = s.classes or name in FIGHTERS or predator(name)            # a predator of Gaia fights too (#3397)
    return f"aoe sight {uuid} {(sight(name, s) + more) * T}{mode}" if fights and s.attack else None


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
    if cmd := elevation_command(data):               # the damage from higher ground (#2307)
        game.command(cmd)
    held = {}                                        # the units that the converter put inside (#807): their arrows
    for o in data["objects"]:
        if o["kind"] == "unit" and o.get("holder") is not None:
            held.setdefault(o["holder"], []).append(o["name"])
    for o in data["objects"]:
        if o["kind"] == "building" and o["player"] and "footprint" in o and o["name"] in BUILDINGS:
            uuid, civ = target_uuid(o["footprint"]), data.get("players", {}).get(str(o["player"]), {}).get("civ")
            civ = None if data.get("full_tech_tree") else civ          # no civilization bonus (#2354)
            for c in building(uuid, o["name"], o["player"], building_box(o, ground), data.get("tile_size", 4),
                              held.get(o.get("ref"), ()), civs.hp(civ, o["name"], stats(o["name"]), 0,
                                                                  civs.handicap(data, o["player"]))) \
                    + [label_command(uuid, o["name"])]:
                game.command(c)
    units = [o for o in data["objects"] if o["kind"] == "unit" and o["player"] and o.get("uuid")]
    for o in data["objects"]:                        # the predators of Gaia wake up and attack, as in AoE2 (#3397)
        if o["kind"] == "unit" and not o["player"] and o.get("uuid") and predator(o["name"]):
            game.command(stats_command(o["uuid"], o["name"]))
            game.command(sight_command(o["uuid"], o["name"], data.get("tile_size", 4)))
    for o in units:                                  # the plugin answers "Range: 0 units" for a mob that cannot shoot
        if cmd := range_command(o["uuid"], o["name"], data.get("tile_size", 4)):
            game.command(cmd)
    n = sum(game.command(stats_command(o["uuid"], o["name"], villager(data, o))).strip() == "Stats: 1 units" for o in units)
    import spoils                                    # spoils imports this module
    for o in units:                                  # the hits of a Varangian Guard make gold (#2376)
        if cmd := spoils.tag_command(o["uuid"], o["name"]):
            game.command(cmd)
    for o in units:                                  # a trebuchet misses units (#2479), with the bonus of its civ
        civ = None if data.get("full_tech_tree") else data.get("players", {}).get(str(o["player"]), {}).get("civ")
        if cmd := accuracy_command(o["uuid"], o["name"], civs.value("accuracy", civ, {}).get(o["name"], 0.0)):
            game.command(cmd)
    for o in units:                                  # after the stats: the plugin needs them for the sight
        if cmd := sight_command(o["uuid"], o["name"], data.get("tile_size", 4)):
            game.command(cmd)
    import ai                                        # ai -> gather -> build -> replay -> combat: import it late
    for o in units:                                  # the AoE2 walk speed also without an order (#849)
        game.command(ai.speed_command(o["uuid"], o["name"], data.get("tile_size", 4)))
    return n


def villager(data, o):
    """The Stats of unit object o of aoe2mc.json data with the hit points of the handicap of its owner when it is a
    villager (#2474), else None (stats_command takes its values)."""
    f = civs.handicap(data, o["player"])
    return stats(o["name"])._replace(hp=round(stats(o["name"]).hp * f)) if f != 1 and o["name"].startswith("VILLAGER") else None


def target_uuid(footprint):
    """The UUID of the target entity of the building with block footprint [x0, z0, x1, z1): the same in each run."""
    return str(uuids.uuid5(uuids.NAMESPACE_OID, "aoe2mc.building." + ".".join(map(str, footprint))))


def wall(name, age, civ=None, factor=1):
    """The Stats of wall name (WALLS) in AoE2 age 0 (Dark) .. 3 (Imperial), with the hit points bonus of civilization
    civ (civs.hp: Byzantines, #2116) and the factor of the owner's handicap (#2474)."""
    hp, melee, pierce = WALLS[name]
    return civs.hp(civ, name, Stats(hp[age], 0, melee, pierce, 0, 0.0, {}, ("building", WALL) + (STONE,) * (not name.startswith("PALISADE"))), age, factor)


def building(uuid, name, player, box, T=4, inside=(), s=None, low=None, factor=1, more=0, taken=1):
    """The commands that make building `name` of `player` a target of attacks (#517): an invisible slime without AI
    that fills the footprint takes the attacks (a mob attacks only a living entity: AoePlugin.java), and the plugin
    keeps the AoE2 hit points. box: the blocks (x0, y0, z0, x1, y1, z1), both ends included, y0 the ground.
    A building with an attack (town center, castle) also gets its attack, its range (tiles * T blocks) and its reload
    in ticks at Normal speed: the plugin lets it shoot arrows at the enemies in its range (#1111), with the AoE2
    number of arrows of the units `inside` (garrison.arrows: an empty town center shoots none, #1201), and its
    minimum range in blocks (FORT_MIN_RANGE, 0 for the town center): no shot at a unit nearer (#1546). low: the
    minimum range in tiles (default FORT_MIN_RANGE; 0 after Murder Holes: build.minimum, #1547).
    s: the Stats (default: stats(name); a wall of the game program: wall(), #1322). factor: of the base arrows
    (civs.arrows, #2178). more: the arrows of the technologies (train.more_arrows, #4258). taken: the factor of the
    bonus damage that the building takes (build.taken: Citadels, #4281), only for a building that shoots; a factor
    other than 1 writes the classes and the bonus ("-": none) before it.
    At 0 hit points the plugin fills the box with air. The invisibility effect hides the slime: the tag Invisible is
    only for armor stands, the server drops it on a slime (#636)."""
    x0, y0, z0, x1, y1, z1 = box
    s, size = s or stats(name), math.ceil((max(x1 - x0, z1 - z0) + 1) / SLIME)
    low = FORT_MIN_RANGE.get(name, 0) if low is None else low
    bonus = ",".join(f"{c}:{n}" for c, n in sorted(s.bonus.items())) * bool(s.attack and s.range)
    taken = taken if s.attack and s.range else 1                       # only after the attack values of the plugin
    n = uuids.UUID(uuid).int
    ints = ",".join(str((n >> k & 0xFFFFFFFF) - ((n >> k & 0x80000000) << 1)) for k in (96, 64, 32, 0))
    return [f"summon slime {(x0 + x1 + 1) / 2} {y0} {(z0 + z1 + 1) / 2} {{Size:{size - 1},NoAI:1b,Silent:1b,"
            f"NoGravity:1b,PersistenceRequired:1b,{INVISIBLE},Tags:[\"aoe2mc.building\"],UUID:[I;{ints}]}}",
            f"team join p{player} {uuid}"] + \
        [f"aoe arrows {uuid} {garrison.arrows(name, inside, factor, more)}"] * bool(s.attack and s.range) + \
        [f"aoe building {uuid} {s.hp} {s.melee} {s.pierce} {' '.join(map(str, box))}"   # after the arrows: no shot of 1
         + (f" {s.attack} {s.range * T} {round(s.reload / NORMAL * 20)} {low * T}"   # (#1546)
            if s.attack and s.range else "")
         + (f" {','.join(s.classes)}" if s.classes != ("building", STANDARD) or bonus or taken != 1 else "")   # a wall, a
                                                                            # gate, the wonder (#1419), a tower (STONE, #1590)
         + (f" {bonus or '-'}" if bonus or taken != 1 else "")              # the arrow bonus (Heated Shot, #1548)
         + (f" {taken:g}" if taken != 1 else "")]                           # Citadels (#4281)


def building_box(o, ground):
    """The box (x0, y0, z0, x1, y1, z1) of a building of aoe2mc.json: its footprint from the lowest ground next to
    it ("ground" over a footprint is the top of its barriers) up HEIGHT blocks."""
    x0, z0, x1, z1 = o["footprint"]
    ring = [(x, z) for x in range(x0 - 1, x1 + 1) for z in (z0 - 1, z1)] + \
        [(x, z) for x in (x0 - 1, x1) for z in range(z0, z1)]
    ys = [int(ground[z][x]) for x, z in ring if 0 <= z < len(ground) and 0 <= x < len(ground[z])
          and ground[z][x] not in ("-", None)] or [64]
    return x0, min(ys), z0, x1 - 1, min(ys) + HEIGHT, z1 - 1
