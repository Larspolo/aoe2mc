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
Technologies (#655): a technology (TECHS: its key "effect" in
data/train.jsonl, effect(), #2029) is an item of the menu of its building and uses the queue of the units, as in
AoE2, but needs no population room. A click queues it once; when it is complete it goes into g.techs, leaves the menu
and changes the values of the live and the new units (stats()). Loom: villagers get 15 hit points and 1/2 armor.
Ages (#672): the Feudal Age is a technology of the town center that needs 2 types of Dark Age buildings (REQUIRES). The
sidebar title shows the age of the player; all players see a title and hear a sound when a player advances.
The Castle Age (#1080) needs the Feudal Age (build.AGE: a gray item before it) and 2 types of Feudal Age buildings.
The Imperial Age (#1081) needs the Castle Age and a castle, or 2 types of Castle Age buildings (REQUIRES).
Forging at the blacksmith (#675): infantry and cavalry get +1 attack. Fletching (#724): archers (also cavalry archers and
skirmishers) get +1 attack and +1 range.
Padded Archer Armor at the blacksmith in the Feudal Age (#937, the key "age"): archers get +1 melee and +1 pierce armor.
Double-Bit Axe at the lumber camp (#723): villagers chop wood 20 % faster (gather.WORK_TECHS, gather.Gather.work_time).
Gold Mining at the mining camp (#727): villagers mine gold 15 % faster. Stone Mining (#939): stone 15 % faster.
In the Castle Age (#1423, the key "after"): Bow Saw (wood 20 % faster), Gold Shaft Mining and Stone Shaft Mining (15 % faster).
Fishing Lines at the dock in the Feudal Age and Gillnets (after it) in the Castle Age (#1439): fishing ships gather 10 %
faster and carry 5 more food (gather.SHIP_TECHS, fleet.rate, fleet.carry).
Horse Collar at the mill (#726): the live and the new farms of the player have 75 more food (gather.FARM_TECHS).
Crop Rotation at the mill in the Imperial Age, after Heavy Plow (#1578): the farms have 175 more food (FARM_TECHS).
Wheelbarrow at the town center in the Feudal Age (#728, the key "age"): villagers carry 3 more resources and walk 10 % faster (gather.CARRY, gather.PACE).
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
move orders of the military units. It researches Fervor (monks walk 15 % faster, the key "walk", speed()) and Sanctity (monks
get 15 more hit points) in the Castle Age (#1261).
The market trains trade carts (#1253): a trade cart also joins g.soldiers, and trade.py walks it between two own markets.
It researches Caravan (trade carts walk 20 % faster, the key "walk") in the Castle Age and Guilds (trading fee 15 %, market.FEES)
in the Imperial Age (#1254). Coinage and Banking change the tribute fee: the game program has no tribute yet.
The barracks researches Squires in the Castle Age (#1415): all infantry of the player walks 10 % faster (the key "walk", a class).
It researches Arson in the Feudal Age (#1419): infantry gets +2 attack against the standard buildings (combat.STANDARD).
The university researches Fortified Wall in the Castle Age (#1326, the key "walls"): the new and the complete own stone
walls and gates get the fortified design and its AoE2 hit points and armor (build.design, build.upgrade).
An age gives the complete own walls and gates the AoE2 hit points of the new age (#1372, combat.WALLS, build.upgrade).
It researches Guard Tower in the Castle Age and Keep (after Guard Tower) in the Imperial Age (#1374, the key "towers"):
the new and the complete own watch towers get the AoE2 hit points, attack and armor of the guard tower or the keep
(build.line, build.retower). The look of the tower stays.
It researches Shipwright in the Imperial Age (#1490, SHIPWRIGHT): the ships of the dock cost 20 % less wood (price())
and train 54 % faster (tick()); the technologies of the dock do not change.
"""
import functools
import importlib
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
import demolish  # noqa: E402
import garrison  # noqa: E402
import menu  # noqa: E402
import monk  # noqa: E402
import near  # noqa: E402
import record  # noqa: E402
import ruins  # noqa: E402
import table  # noqa: E402

DATA = os.path.join(table.DIR, "train.jsonl")
SOUNDS = {r["name"]: r for r in table.load("sounds.jsonl")}       # building name -> the sound of a click on it (#3501)


def load(path=None):
    """The items of the menus: one JSON object per line (#1702, `table.load`); default: the file of the rule set."""
    return table.load(path or "train.jsonl")


ROWS = load()                                                      # one line per item: data/train.jsonl (#1702)
UNIT_ROWS, BUILDING_ROWS = table.load("units.jsonl"), table.load("buildings.jsonl")   # their keys below (#2030)
COSTS = {r["name"]: r["cost"] for r in ROWS}                       # as in AoE2
TRAIN_TIMES = {r["name"]: r["time"] for r in ROWS}                 # AoE2 seconds
TRAINS = {b: tuple(r["name"] for r in ROWS if r["building"] == b)    # the units and technologies of each
          for b in dict.fromkeys(r["building"] for r in ROWS if r["building"])}   # building, in file order
TRAINS["DONJON"] = ("SPEARMAN",)                                  # trains() adds the Serjeant (#1873)
TRAINS["FOLWARK"] = TRAINS.get("MILL", ())                               # the mill of the Poles (#1874)
TRAINS["KREPOST"] = ("PETARD",)                                     # trains() adds the Konnik (#1872); wiki: the petard (#2192)
TRAINS["FORTIFIED_CHURCH"] = TRAINS.get("MONASTERY", ())                  # the monastery of the Armenians, Georgians (#1930)
# A building with the menus of other buildings: the key "menus" of data/buildings.jsonl (the mule cart: the lumber and
# mining camp, #2208). The items of each later menu move right of the slots of the earlier ones (SHIFTS, slots()).
MENUS = {r["name"]: r["menus"] for r in BUILDING_ROWS if set(r.get("menus", ["?"])) <= set(TRAINS)}   # of the rules
TRAINS |= {b: sum((TRAINS[m] for m in ms), ()) for b, ms in MENUS.items()}
SLOTS = {r["name"]: r["slot"] for r in ROWS}
# An upgrade of one building (the key "one_building", #2484: the Achaemenid town centers): it changes only the building
# that researches it, and that building takes only one of them (g.upgraded: footprint -> name). Its "aura": the
# villagers within "range" tiles of that building work "rate" times as fast (Gather.aura_rate); the own military units
# heal "heal" hit points per AoE2 minute and walk "speed" times as fast (regen.military, #2496).
ONE_BUILDING = {r["name"]: r.get("aura") for r in ROWS if r.get("one_building")}
SHIFTS = {b: {n: sum(1 + max(SLOTS[x] for x in TRAINS[p]) for p in ms[:i]) for i, m in enumerate(ms) for n in TRAINS[m]}
          for b, ms in MENUS.items()}
# The unique unit of each civilization (AoE2 DE, "unique" in data/civs.jsonl, #1914), trained at its castle. A unit
# without COSTS is not in the menu yet: it has no AoE2 combat values in combat.STATS.
UNIQUE = civs.UNIQUE
# The value of each key of data/train.jsonl that value() reads, by item: one line per key in data/train_keys.jsonl (what
# it does, its issue, #2507), as civs.value (#2281). A new key then needs no new table here.
KEYS = {r["name"]: f"{r['text']} (#{r['issue']})" for r in table.load("train_keys.jsonl")}
BY_KEY = {k: {r["name"]: r[k] for r in ROWS if k in r} for k in sorted(KEYS)}
BUILDING_OF = {r["name"]: r["building"] for r in ROWS}


def more_arrows(g, building):
    """The arrows that the technologies of g.techs add to one shot of the building (Yasama, Tigui: "more_arrows", #4258)."""
    return sum(value("more_arrows", t, {}).get(building, 0) for t in g.techs)


def pass_arrows(g, building):
    """The end of `aoe arrows` for the own building: " <blocks> <part>" when a technology of g.techs lets its arrows pass
    through the units (Svan Towers: "pass_arrows", #4282), else ""."""
    v = next((v for t in sorted(g.techs) if building in (v := value("pass_arrows", t, {})).get("names", ())), None)
    return f" {v['tiles'] * g.map.T} {v['part']}" if v else ""


def dot(g, name, s):
    """The damage over time of a hit of unit name (combat.Stats s) of the player of g (#4339): (damage, AoE2 seconds, the
    target classes or ()) of the first technology of g.techs (in name order) with an entry of the key "damage_over_time"
    whose test holds (test(): Curare, Red Cliffs Tactics), else None. The plugin deals it (Dot.java)."""
    for t in sorted(getattr(g, "techs", ())):
        for e in value("damage_over_time", t, ()):
            if any(test(x, name, s) for x in e["if"]):
                return e["damage"], e["seconds"], tuple(e.get("on", ()))
    return None


def stats_line(g, uuid, name, s=None):
    """The "aoe stats" command of unit uuid of the player of g: its values s (default stats()), the bonus damage and the
    friendly fire that it takes (civs.taken, civs.friendly) and its damage over time (dot(), #4339)."""
    import combat                                                  # combat imports gather, gather imports this module
    s = s or stats(g, name, uuid)
    return combat.stats_command(uuid, name, s, civs.taken(g, name), civs.friendly(g, name), **hits(g, name),
                                 dot=dot(g, name, s))


def weight(g, name):
    """The population of one unit (None: a villager): the product of the factors of the researched technologies with the
    key "population" whose units (as faster: a building, a group, a class, a name or a list) cover it (Logistics of
    Antiquity Mode: 1/2 for the Barracks, #3918; Mahayana, Aznauri Cavalry, #4256), else 1."""
    return math.prod(f for t, (b, f) in BY_KEY["population"].items() if t in g.techs and faster(b, name or "VILLAGER"))


def work(g, building):
    """The factor of the work rate of building (a name) from the researched technologies with the key "work":
    [the building, the factor] (Perfusion: the Barracks 2, #4226), else 1."""
    return math.prod(f for t, (b, f) in BY_KEY["work"].items() if researched(g, t) and b == building)


def researched(g, tech):
    """True when the player of g researched tech, or an ally did and tech has the key "team" (Kasbah, Butalmapu,
    #4329). The allies are the Gathers of the game (fog.gathers; a bot reaches them by its share)."""
    if tech in vars(g).get("techs", ()):
        return True
    if not BY_KEY["team"].get(tech):
        return False
    import gather                                                  # gather imports this module
    root = vars(g).get("share") or g
    return any(tech in vars(h).get("techs", ()) and gather.allied(g.players, g.player, h.player)
               for h in [root, *(b.g for b in getattr(root, "bots", ())), *getattr(root, "peers", ())])


def group_rate(g, name):
    """The factor of the train rate of unit name from the researched technologies with the key "train_group": [the
    units, as "walk" (faster()), the factor] (Steppe Husbandry: the scout line 2, #4260), else 1."""
    return math.prod(f for t, (u, f) in BY_KEY["train_group"].items() if t in g.techs and faster(u, name))


def value(key, name, default=None):
    """The value of key of data/train.jsonl for item name (BY_KEY), else default. A key needs its line in
    train_keys.jsonl."""
    assert key in KEYS, key
    return BY_KEY[key].get(name, default)



def sight_more(techs, name, s):
    """The tiles of line of sight that the technologies techs add to unit name with combat values s: the key "sight"
    of data/train.jsonl, {"if": [tests of test()], "add": n} (#3981)."""
    return sum(e["add"] for t in techs if (e := BY_KEY["sight"].get(t)) and any(test(x, name, s) for x in e["if"]))

build.AGE |= dict.fromkeys(UNIQUE.values(), 2) | dict.fromkeys(("ELITE_" + n for n in UNIQUE.values()), 3)   # (#1082)


def own_civ_only():
    """{name: the other civs} of each unique unit with an elite upgrade in COSTS, its elite unit and its upgrade: only
    the own civ has them (civs.MISSING). A new unique unit needs no line in civs.py, and its elite upgrade has
    `"building": null` in data/train.jsonl: trains() adds it to the castle of the own civ (#1760). The same for a unique
    technology: its key `"civ"` (#2021)."""
    others = set().union(*civs.MISSING.values()) | set(UNIQUE)
    return {n: tuple(sorted(others - {c})) for c, u in UNIQUE.items() if f"ELITE_{u}_UPGRADE" in COSTS
            for n in (u, "ELITE_" + u, f"ELITE_{u}_UPGRADE")} | {n: tuple(sorted(others - {c})) for n, c in BY_KEY["civ"].items()}


civs.MISSING |= own_civ_only()


def chemistry(name, s):
    """Chemistry (AoE2 DE, wiki): +1 attack for archers, ranged siege units and buildings that shoot, not for gunpowder
    units (#1506). A building gets it when it is complete (build.target, build.values)."""
    shoots = "archer" in s.classes or "siege" in s.classes and s.range > 0 or "building" in s.classes and s.attack > 0
    shoots = shoots and "gunpowder" not in s.classes
    return s._replace(attack=s.attack + 1) if shoots else s


def fletching(name, s):
    """Fletching, Bodkin Arrow and Bracer (AoE2 DE, wiki): archers and the buildings that shoot +1 attack and +1 range, the town
    center +1 attack only (#1408). A complete building gets it at once (build.retower), a new one when it is complete.
    Not the Fortress of the Scenario Editor (AoE2 wiki, #2137)."""
    if "archer" in s.classes or "building" in s.classes and s.attack > 0 and name != "FORTRESS":
        return s._replace(attack=s.attack + 1, range=s.range + (name != "TOWN_CENTER"))
    return s


def thumb(name, s):
    """Thumb Ring (AoE2 DE, wiki): the archers fire faster; not the skirmishers (only their accuracy) and not the
    gunpowder units."""
    fast = "archer" in s.classes and "gunpowder" not in s.classes and "SKIRMISHER" not in name
    return s._replace(reload=round(s.reload / 1.1765, 3)) if fast else s


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


def heated(name, s):
    """Heated Shot (AoE2 DE, wiki): the arrows of the own towers get more attack against ships (HEATED, #1548)."""
    return s._replace(bonus={**s.bonus, "ship": s.bonus.get("ship", 0) + HEATED[name]}) if name in HEATED else s



def forms(first):
    """The unit first and the units that its upgrades make, in order (UPGRADES of data/train.jsonl): the archer line
    is forms("ARCHER"). No list of names in the code (tools/data_lint.py, #2061)."""
    pairs = [p for u in UPGRADES.values() for p in ([u] if isinstance(u[0], str) else u)]
    out = [first]
    while (new := next((b for a, b in pairs if a == out[-1]), None)) and new not in out:
        out.append(new)
    return tuple(out)


def test(t, name, s):
    """True when test t of an effect of data/train.jsonl holds for unit name with combat values s: {"class": C} (C in
    s.classes; a list: all of them), {"names": [...]}, {"prefix": P} (the name starts with P), {"forms": [first, ...]} (forms()) or
    {"test": F} (the function F(name, s) of this module, for a test with real logic)."""
    if "class" in t:
        return set([t["class"]] if isinstance(t["class"], str) else t["class"]) <= set(s.classes)
    if "names" in t:
        return name in t["names"]
    if "prefix" in t:
        return name.startswith(t["prefix"])
    if "forms" in t:
        return any(name in forms(f) for f in t["forms"])
    return globals()[t["test"]](name, s)


def effect(e, more=1):
    """The function (name, s) -> s of the key "effect" of a technology of data/train.jsonl (#2029): the name of a
    function of this module (an effect with real logic), or {"if": [tests], "add": {field: n}, "times": {field: f},
    "bonus": {class: n}, "bonus_times": {class: f}} (a factor of a bonus, Northmen's Fury, #4259). The unit gets the change when one of the tests holds (test(); no "if": each unit). {}: no
    change of the combat values, the effect is in another place (its "note"). A list: each change in turn (an age gives
    the eagle scout and the Flemish Militia other values, #2155). more: the factor of the change (civs.MORE, #2173)."""
    if isinstance(e, str):
        return globals()[e]
    if isinstance(e, list):
        changes = [effect(x, more) for x in e]
        return lambda name, s: functools.reduce(lambda s, f: f(name, s), changes, s)
    if not e:
        return lambda name, s: s

    def change(name, s):
        if "if" in e and not any(test(t, name, s) for t in e["if"]):
            return s
        part = (lambda n: n) if more == 1 else (lambda n: n * more if isinstance(n, float) else round(n * more))   # a blast radius stays a part of a tile (#4283)
        new = {k: getattr(s, k) + part(n) for k, n in e.get("add", {}).items()}
        new |= {k: (round if isinstance(getattr(s, k), int) else float)(getattr(s, k) * (f if more == 1 else 1 + (f - 1) * more))
                for k, f in e.get("times", {}).items()}     # a reload of 2.0 × 0.75 stays 1.5 (Stirrups, #4098)
        if "bonus" in e:
            new["bonus"] = {**s.bonus, **{k: s.bonus.get(k, 0) + part(n) for k, n in e["bonus"].items()}}
        if "bonus_times" in e:                  # a factor of a bonus, rounded as civs.units (#2272)
            new["bonus"] = {**new.get("bonus", s.bonus), **{k: math.floor(s.bonus[k] * (f if more == 1 else 1 + (f - 1) * more) + 0.5)
                                                            for k, f in e["bonus_times"].items() if k in s.bonus}}
        return s._replace(**new)
    return change


TECHS = {r["name"]: effect(r["effect"]) for r in ROWS if "effect" in r}   # a technology: its change of the AoE2 values
DOCTRINES = {r["name"]: r["building"] for r in ROWS if r.get("doctrine")}   # the switch of the Recruitment Doctrines (#2483)
EACH = {r["name"]: effect({k: v for k, v in r["effect"].items() if k != "if"})   # the same change for each unit
        for r in ROWS if isinstance(r.get("effect"), dict)}       # (civs.SMITH_UNITS, #2174)
SHIPWRIGHT = (0.8, 1.54)                                           # Shipwright: ships cost 80 % wood, train 54 % faster
CONSCRIPT = (tuple(r["name"] for r in BUILDING_ROWS if r.get("conscription")),   # Conscription: these buildings
             next((r["factor"] for r in ROWS if r["name"] == "CONSCRIPTION"), 1))   # train faster (#1455)
ARROWSLITS = {r["name"]: r["arrowslits"] for r in BUILDING_ROWS if "arrowslits" in r}   # the attack of each tower (#1504)
HEATED = {r["name"]: r["heated_shot"] for r in BUILDING_ROWS if "heated_shot" in r}   # Heated Shot: attack against
#                                           ships (AoE2 DE wiki "Attack increase against ships", #1548)
PER_ENEMY = {r["name"]: (r["per_enemy"], r["most"]) for r in ROWS if "per_enemy" in r}   # Spies: the cost for each
#                                           enemy civilian unit (the name starts with one of them) and the most (#2193)
UPGRADES = {r["name"]: tuple(map(tuple, u)) if isinstance(u[0], list) else tuple(u)   # technology: the unit and its
            for r in ROWS if (u := r.get("upgrade"))}             # new unit (#941), "upgrade" of data/train.jsonl (#1915)
REQUIRES = {r["name"]: (r["requires"][0], *map(tuple, r["requires"][1:]))   # an age: n types of these buildings, or
            for r in ROWS if "requires" in r}                      # one of the third list alone
# The AoE2 event sounds (#3502): a own site is complete, an own technology is complete, a monk converts a unit
EVENT_SOUNDS = {"built": "minecraft:block.anvil.use", "convert": "minecraft:entity.evoker.prepare_wololo",
                "research": "minecraft:block.note_block.bell"}
AGES = build.AGE_NAMES                                             # the age after each researched age (index: ages)
# AoE2 DE setting "Starting age" (game/data/setup.jsonl): the researched ages and the skipped technologies (#2265)
STARTS = {r["name"]: r for r in table.load("setup.jsonl") if "ages" in r}
SWAPS = {r["name"]: r["swap"] for r in table.load("setup.jsonl") if "swap" in r}   # a game mode: {old: new} (#2388)
AGAIN = {r["name"] for r in ROWS if r.get("again")}                # a technology that a player researches again (Treason)
SPAM = 1.0                                                         # seconds: one more click on the same building in this time opens no new menu (#3267)
QUEUE = 15                                                         # units in the queue of one building, as in AoE2
HOUSING = {r["name"]: r["housing"] for r in BUILDING_ROWS if "housing" in r}   # population of a complete building
AGE_COUNT = {r["name"]: r["age_count"] for r in BUILDING_ROWS if "age_count" in r}   # types of the age rule: the Settlement 2 (#2420)
LIMIT = 200                                                        # the AoE2 population limit
LIMITS = (*range(25, 251, 25), 300, 400, 500)                      # the AoE2 setting "Population limit" (#2266)
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


HULKS = tuple(r["name"] for r in UNIT_ROWS if r.get("melee_ship"))   # melee warships: the blacksmith attack too (#1509)
# Siphons and Incendiaries (#2165): technology: the key "charge" or "detonate" of its line of data/train.jsonl and its
# values: {"if": [tests], "attack": n, "blast": tiles, "bonus": {class: n}}, a charge also "reload" (s) and "shots";
# a list of them: one per unit line, and the blast hurts no own or allied unit (Thunderclap Bombs, #4367).
# The charge of a melee hit (Comitatenses, #4370): the key "charge_attack": {"if": [tests], "attack": n, "time": s}
FIRE = {r["name"]: (k, r[k]) for r in ROWS for k in ("charge", "charge_attack", "detonate") if k in r}


def fire_commands(g, uuid, name, techs=None):
    """The plugin commands of the charge attack (`aoe charge`) and the blast at death (`aoe detonate`) of an own ship
    after the research of their technologies (FIRE, #2165), of the charge of the next melee hit of an own unit
    (`aoe chargeattack`, #4370), and of the thrown axes of a melee unit (`aoe throw`, the key "throw": Gothikon, #4368),
    or of the technologies techs only. Vanilla has no second attack, no "on death" command, one attack value per mob
    and no shot of a melee mob. An axe has the values of the unit (its attack with the upgrades)."""
    import combat, gather                                          # both import gather, gather imports this module
    out = []
    for tech, (kind, parts) in FIRE.items():                       # a list: one value per unit line, foes only (#4367)
        for c in parts if isinstance(parts, list) else [parts]:
            if tech not in (g.techs if techs is None else techs) or not any(test(t, name, combat.stats(name)) for t in c["if"]):
                continue
            if kind == "charge_attack":
                out.append(f"aoe chargeattack {uuid} {max(1, round(c['time'] / gather.NORMAL * 20))} {c['attack']}")
                continue
            bonus, blast = ",".join(f"{k}:{v}" for k, v in sorted(c["bonus"].items())) or "-", c["blast"] * g.map.T
            out.append(f"aoe charge {uuid} {max(1, round(c['reload'] / gather.NORMAL * 20))} {c['attack']} {c['shots']} "
                       f"{blast} {bonus}" if kind == "charge" else
                       f"aoe detonate {uuid} {c['attack']} {blast} {bonus}" + " foes" * isinstance(parts, list))
    for tech, c in BY_KEY["throw"].items():                        # Gothikon: the axes of a melee unit (#4368)
        if tech in (g.techs if techs is None else techs) and any(test(t, name, combat.stats(name)) for t in c["if"]):
            ticks = [max(1, round(c[k] / gather.NORMAL * 20)) for k in ("reload", "gap")]
            out.append(f"aoe throw {uuid} {ticks[0]} {ticks[1]} {c['range'] * g.map.T:g} {c['shots']}")
    return out


def type_tag_commands(uuid, old, new):
    """The commands that move the type tag (aoe2mc.t<ID>) of a live unit from old to new, as AoE2 counts an upgraded unit
    as the new type (#2977). The tag sits on the rider of a mounted unit, else on the unit (units.make_entity)."""
    ids = units.type_ids()
    if ids.get(old) is None or ids.get(new) is None:
        return ()
    rm, add = f"aoe2mc.t{ids[old]}", f"aoe2mc.t{ids[new]}"
    return (f"tag {uuid} remove {rm}", f"execute as {uuid} on passengers run tag @s remove {rm}",
            f"execute as {uuid} on passengers run tag @s add {add}",
            f"execute as {uuid} unless entity @s[nbt={{Passengers:[{{}}]}}] run tag @s add {add}")


def volley_command(g, uuid, name):
    """The plugin command of the extra projectiles in each shot of own unit name (the key "volley" of data/civs.jsonl:
    the Armenian galley line and dromons, #2379; the key "volley" of the researched technologies: {unit: {"shots": n,
    "attack": a or "part": p}}, Double Crossbow, #4338), else None. "attack" is the AoE2 attack of each extra
    projectile, "part" a part of the attack of the unit, neither the full attack (0). The plugin keeps one attack for
    all extra projectiles of a unit: the last technology wins. Minecraft feature: one more Arrow entity; the plugin
    gives it its AoE2 damage."""
    attack = civs.value("volley", civs.civ(g), {}).get(name)
    shots, attack = (0, 0) if attack is None else (1, attack)
    for t in sorted(vars(g).get("techs", ())):
        if v := value("volley", t, {}).get(name):
            shots += v["shots"]
            attack = v["attack"] if "attack" in v else max(1, round(stats(g, name, uuid).attack * v["part"])) if "part" in v else 0
    return f"aoe volley {uuid} {shots} {attack}" if shots else None


def lead_command(g, uuid, name, techs=None):
    """The command that lets the shots of own unit name lead a moving target, as with Ballistics (the key "lead" of
    data/civs.jsonl: Spanish Cannon Galleons, #2430; the key "lead" of data/train.jsonl of the technologies techs,
    default g.techs: Arquebus, #4364), else None. Minecraft feature: a scoreboard tag that the plugin reads (AoePlugin.lead)."""
    import combat                                                  # combat imports this module's data: import it late
    if name in civs.value("lead", civs.civ(g), ()):
        return f"tag {uuid} add aoe2mc.lead"
    s = combat.stats(name)
    if any(test(t, name, s) for tech in (g.techs if techs is None else techs) if (e := BY_KEY["lead"].get(tech))
           for t in e["if"]):
        return f"tag {uuid} add aoe2mc.lead"
    return None


ORDERS = {r["name"] for r in UNIT_ROWS if r.get("orders")}         # not military, but they take move orders (summon)


def melee(name, s):
    """True for the combat values s of an infantry or cavalry unit (also camels and elephants): the units of the melee
    attack upgrades of the AoE2 blacksmith. Cavalry archers get the archer upgrades."""
    return bool({"infantry", "cavalry", "camel", "elephant"} & set(s.classes)) and "archer" not in s.classes


def barding(name, s):
    """True for the combat values s of a cavalry unit (also camels and elephants): the units of the barding armor
    upgrades of the AoE2 blacksmith. Cavalry archers get the archer armor upgrades. A mounted unit keeps its values
    on the horse (its UUID in aoe2mc.json), so the horse gets the armor (#850)."""
    return bool({"cavalry", "camel", "elephant"} & set(s.classes)) and "archer" not in s.classes


def smith(name, s):
    """True for the units of the attack upgrades of the AoE2 blacksmith: melee() and the melee warships (HULKS)."""
    return melee(name, s) or name in HULKS


def monks(name, s):
    """True for the monks (monk.MONKS): Sanctity."""
    return name in monk.MONKS


def ship(name, s):
    """True for the combat values s of ship name: the units of Careening and Dry Dock (#1441). The transport ship has
    no class "ship" in combat (the warships do not shoot at it), but it gets the armor too."""
    import combat                                                  # combat imports gather, gather imports this module
    return combat.SHIP in s.classes or name == "TRANSPORT_SHIP"


def foot_archers(name, s):
    """True for the foot archers (civs.foot_archer): Yeomen."""
    return civs.foot_archer(s)


def infantry_but_spears(name, s):
    """True for the infantry except the Spearman line (forms("SPEARMAN")): Fereters (Armenians, #4273)."""
    return "infantry" in s.classes and name not in forms("SPEARMAN")


def unlocked(g, name):
    """True when the player has the age of technology name (the key "age"). As in AoE2, the menu shows a technology only
    from its age, but a building or unit of a later age as a gray item (build.locked), and never one that the
    civilization of the player does not have (civs.missing: also not as a team bonus of an ally, #1619). An item that
    a scenario trigger turned on (g.trigger_menus, #2775) needs no age."""
    return (value("age", name, 0) - civs.earlier(g, name) <= build.ages(g) or getattr(g, "trigger_menus", {}).get(name, False)) \
        and value("after", name, "") in {""} | set(getattr(g, "techs", ())) \
        and not (hasattr(g, "data") and civs.missing(g, name) and name not in granted(g)) \
        and (name not in UPGRADES or name in REQUIRES or bool(lines(name, g))) and not swapped(g, name)   # not of this
                                                                   # civilization (#1373), no new unit (#1483); an
                                                                   # age also upgrades (#2130)


def swapped(g, name):
    """True when the game mode of g puts another technology in place of name, or name is the technology of another
    mode (SWAPS: Treason only in Regicide, in place of Spies, #2388)."""
    swap = SWAPS.get(getattr(g, "mode", "standard"), {})
    return name in swap or name not in swap.values() and any(name in s.values() for s in SWAPS.values())


def homes(g):
    """{block footprint (x0, x1, z0, z1): building name} of the complete own buildings that train units (TRAINS):
    the start ones and the built ones, not the fallen ones (ruins.py)."""
    out = {(x0, x1, z0, z1): o["name"] for o in g.data["objects"] if o["kind"] == "building" and o["name"] in TRAINS
           and o["player"] == g.player and not ruins.fallen(g, o) for x0, z0, x1, z1 in [o["footprint"]]}
    return out | {tuple(s["footprint"]): s["name"] for s in g.sites if s["name"] in TRAINS and s.get("done")}


def lines(t, g=None):
    """The (unit, new unit) pairs of upgrade technology t (UPGRADES): Medium Warships upgrades two lines (#1482). With g,
    only the new units that the civilization of the player has (civs.MISSING): Heavy Warships gives no fast fire ship
    to the Vikings (#1483)."""
    out = UPGRADES[t] if isinstance(UPGRADES[t][0], tuple) else (UPGRADES[t],)
    return tuple(p for p in out if g is None or not hasattr(g, "data") or not civs.missing(g, p[1]))


def slots(building, name):
    """(slot, item, label) of name in the menu of building: ITEMS, with the slot shift of SHIFTS. A unit line of
    civs.TRAINS (the Mapuche Settlement) comes after the items of the building, one slot per line (#2432), then the
    upgrades of each line, one slot per line (#2487)."""
    slot, item, label = ITEMS[name]
    lines = [line for c in civs.TRAINS.values() for line in c.get(building, {}).get("lines", ())]
    lines += [line_upgrades(line) for line in lines]                   # then the upgrades of each line (#2487)
    if (i := next((k for k, line in enumerate(lines) if name in line), None)) is not None:
        return 1 + max(slots(building, n)[0] for n in TRAINS[building]) + i, item, label
    return slot + SHIFTS.get(building, {}).get(name, 0), item, label


def added(g, building, name):
    """(AoE2 button, seconds) of unit name in building from "Add Train Location" (scenario.locations, #2865), or None.
    An upgraded unit keeps the entry of its line: the castle trains the man-at-arms in place of the militia."""
    got = getattr(g, "trigger_trains", {}).get(building, {})
    old = {new: old for t in UPGRADES for old, new in lines(t)}
    while name not in got and name in old:
        name = old[name]
    return got.get(name)


def placed(g, building, name):
    """slots() of name, at the slot of the AoE2 button that a scenario trigger gave it (g.trigger_places, #2864; "Add
    Train Location" in building: added(), #2865, its button 0 is the first): the buttons 1 to 8 are the first row, 9 and
    up the row under the queue (MORE). Button 0 or less keeps the slot."""
    slot, item, label = slots(building, name)
    got = added(g, building, name)
    button = vars(g).get("trigger_places", {}).get(name, [None, 0])[1] or (max(got[0], 1) if got else 0)
    return (button - 1 if button < ROW else MORE + button - ROW) if button > 0 else slot, item, label


def covered(g, building, name):
    """True when a scenario trigger moved or added another item onto the slot of name in the menu of building (#2864,
    #2865): the moved or added item takes the slot."""
    moved = vars(g).get("trigger_places", {})
    new = getattr(g, "trigger_trains", {}).get(building, {})
    return name not in moved and added(g, building, name) is None and placed(g, building, name)[0] in \
        {placed(g, b, n)[0] for n, (b, _) in moved.items() if b == building} | {placed(g, building, n)[0] for n in new}


def layout(g, rect):
    """{name: (slot, item, label)} of each shown item of the menu of building rect (#3098). An item keeps its slot
    (placed()) when no earlier item has it; else it takes the first free slot from MORE. Full Tech Tree gives a
    civilization regional items that share the slot of a generic item (Armored Elephant, Battering Ram)."""
    building = homes(g)[rect]
    names = [n for n in trains(g, building) if offered(g, rect, n) and not covered(g, building, n)]
    used = {RALLY[0]} if units_of(g, building) else set()          # the items of show() after the trained ones
    used |= {garrison.ungarrison(building)[0]} if getattr(g, "garrisons", {}).get(rect) else set()
    used |= {garrison.BELL[0]} if building == "TOWN_CENTER" else set()
    used |= {demolish.ITEM[0]}                                         # the item Delete (#3452)
    out = {}
    for name in names:
        slot, item, label = placed(g, building, name)
        if slot in used or slot in {s for s, *_ in out.values()}:
            continue
        out[name] = slot, item, label
    for name in names:
        if name not in out:
            taken = used | {s for s, *_ in out.values()}
            slot = next(s for s in range(MORE, 54) if s not in taken)
            out[name] = (slot, *placed(g, building, name)[1:])
    return {n: out[n] for n in names}


def line_upgrades(line):
    """The upgrade technologies (UPGRADES) of one unit line (a list of unit names), in the order of the line. The elite
    upgrade of a unique unit stays at the castle (the Goth barracks, #2685)."""
    return [t for n in line for t in UPGRADES if UPGRADES[t] == (n, UPGRADES[t][1]) and UPGRADES[t][1] in line
            and n not in UNIQUE.values()]


def trains(g, building):
    """own() of the building, and the free units of the technologies of the player and its allies (granted())."""
    out = own(g, building)
    return out + tuple(n for n in granted(g, building) if n not in out)


def granted(g, building=None):
    """{unit: count} of the free units of building (any building with None) that the technologies of the key "free"
    of the player or of an allied player give to each of its buildings (Cuman Mercenaries, #4330)."""
    import fog, gather                                             # both import gather, gather imports this module
    if not BY_KEY["free"] or not hasattr(g, "players"):
        return {}
    out = {}
    for h in fog.gathers(g):
        if h.player == g.player or gather.allied(g.players, g.player, h.player):
            for t, (b, unit, n) in BY_KEY["free"].items():
                if t in h.techs and building in (None, b):
                    out[unit] = max(out.get(unit, 0), n)
    return out


def free_left(g, rect, name):
    """The free units name that the building rect can still train (granted()), 0 for none."""
    return max(0, granted(g, homes(g)[rect]).get(name, 0) - vars(g).get("free_trained", {}).get(rect, {}).get(name, 0))


def own(g, building):
    """The units and technologies of the own building: a castle trains the unique unit of the player's civilization,
    a Krepost the Konnik, a Donjon the Serjeant."""
    new = {old: unit for t in UPGRADES if t in g.techs for old, unit in lines(t, g)}   # the barracks trains the new unit
    unique = [n for n in [UNIQUE.get(civs.real(g))] if n in COSTS] * (building == "CASTLE") \
        + ["KONNIK"] * (building == "KREPOST") \
        + ["SERJEANT"] * (building == "DONJON")                    # and the spearman line (AoE2 DE wiki, #1873)
    out = unique + list(TRAINS[building]) + [f"ELITE_{n}_UPGRADE" for n in unique if f"ELITE_{n}_UPGRADE" in COSTS]   # (#1760)
    out += [n for n, c in BY_KEY["civ"].items() if c == civs.civ(g)] * (building == "CASTLE")   # the unique technologies (#2021)
    more = civs.TRAINS.get(civs.civ(g), {}).get(building, {})
    more = more.get("lines", ()) if more.get("after", "") in {"", *g.techs} else ()   # after a technology: Anarchy (#2685)
    out += [line[0] for line in more] + [t for line in more for t in line_upgrades(line)]   # Mapuche (#2432, #2487)
    moved = vars(g).get("trigger_places", {})                      # "Change Train/Technology Location" (#2864)
    out = [n for n in out if moved.get(n, [building])[0] == building] + [n for n, (b, _) in moved.items() if b == building]
    out += [n for n in getattr(g, "trigger_trains", {}).get(building, {}) if n in COSTS]   # Add Train Location (#2865)
    for _ in UPGRADES:                                             # a line of upgrades: mangonel, onager, siege onager
        out = [new.get(n, n) for n in out]                         # the castle: the elite unique unit (#1624)
    return tuple(dict.fromkeys(out))                               # the camel scout becomes the camel rider (#2130)


def home(g, cell):
    """The footprint of the own training building that has the block cell (x, z) in it, or None."""
    return next((r for r in homes(g) if cell and r[0] <= cell[0] < r[1] and r[2] <= cell[1] < r[3]), None)


def lore(g):
    """Send the help line of each menu item to the plugin (#1160), also for its gray item of a later age. Sorted: the
    gray "Man-at-Arms" is the upgrade (the unit is never gray), so the help of the upgrade comes last."""
    for name in sorted(HELP):
        for material in (ITEMS[name][1], build.LOCKED):
            menu.lore(g, material, ITEMS[name][2], HELP[name])


def open_menu(g, player, cell, click=False):
    """Open the menu of the own training building at the block cell (x, z) for player. Returns its footprint, or None.
    click: a stick use of the player, which opens no new menu SPAM seconds after one on the same building (#3267)."""
    rect = home(g, cell)
    opened = vars(g).setdefault("menu_opened", {})
    if click and rect is not None and opened.get(player, (None, -SPAM))[0] == rect and g.clock() - opened[player][1] < SPAM:
        return rect                                                    # a spam click: the uses that came before the menu showed (#3267)
    if rect is not None:
        opened[player] = rect, g.clock()
        click_sound(g, player, rect)
        show(g, player, rect)
    return rect


def click_sound(g, player, rect):
    """Play the sound of the own building rect to the player who opened its menu, as AoE2 DE does (#3501). Only own
    buildings open a menu, so an enemy or allied building plays no sound. A building with no line plays none."""
    if (v := SOUNDS.get(homes(g)[rect])) and not getattr(g, "noui", False):
        x, z = (rect[0] + rect[1]) / 2, (rect[2] + rect[3]) / 2
        g.command(f"execute as {player} at @s positioned {x:.1f} ~ {z:.1f} run "
                  f"playsound minecraft:{v['select']} voice @s ~ ~ ~ 1 {v['pitch']}")


def trained_voice(g, rect, unit):
    """Play the select voice of the class of the unit that the building rect completed, to the team of the own player
    (AoE2 DE, #3563). unit: a Villager, a UUID or a ship. A class with no line plays none; a setup or a cheat spawns
    with no sound."""
    import gather                                                  # gather imports this module
    if (v := gather.VOICES.get(g.voice_class(getattr(unit, "uuid", unit)))) and not getattr(g, "noui", False):
        x, z = (rect[0] + rect[1]) / 2, (rect[2] + rect[3]) / 2
        g.command(f"playsound minecraft:{v['select']} voice @a[team=p{g.player}] {x:.1f} {g.map.y(int(x), int(z))} {z:.1f} 1 {v['pitch']}")


def show(g, player, rect):
    """Show (or refresh) the menu of the building rect: one item per unit, with its cost, time and queue. The second
    row shows the queue (#706): one item per group of the same unit (groups(), item count: the units), the first one
    with its progress; a click on it cancels a unit (cancel())."""
    n, building = len(g.queues.get(rect, [])), homes(g)[rect]
    def state(name):
        if need := build.locked(g, name):                              # a unit of a later age: a gray item (#674)
            return need
        if flag := value("toggle", name):                              # a switch (#3422)
            return "on" if vars(g).get(flag) else "off"
        if name in TECHS:
            return missing(g, name) or ("researching" if queued(g, name) and name not in ONE_BUILDING else "research")
        return f"queue {n}/{QUEUE}" + (" · Auto-queue: on" if vars(g).get("auto", {}).get(rect) == name else "")
    names = vars(g).get("trigger_names", {})                          # "Change Technology Name" (#2821)
    items = [(slot, build.LOCKED if build.locked(g, name) else item, names.get(name, label),
              (" · ".join(f"{v} {r}" for r, v in price(g, name, building, rect).items()) or "free") + f" · {round(seconds(g, name, building), 1):g} s · "
              + state(name))
             for name, (slot, item, label) in layout(g, rect).items()]
    items += [RALLY] if units_of(g, building) else []
    items += [garrison.ungarrison(building)] if getattr(g, "garrisons", {}).get(rect) else []   # only with units inside (#808)
    items += [garrison.bell_item(g)] if building == "TOWN_CENTER" else []    # the town bell (#3419)
    items += [demolish.ITEM] if demolish.shown(g, rect) else []        # the building falls (#3452)
    if building == "MARKET":                                           # the buy and sell rows under the queue (#1286)
        import market                                                  # only for a market
        items += [(market.ROW + slot, *item) for slot, *item in market.items(g)]
    q = g.queues.get(rect, [])                                         # the queue row first: the plugin sets the
    items = [(ROW + i, ITEMS[name][1], ITEMS[name][2] + (f" {int(100 * q[0]['progress'])} %" if start == 0 else ""),
              "Click: cancel 1", k) for i, (name, start, k) in enumerate(groups(q)[:ROW])] + items   # items by slot
    def click(p, slot, shift, right=False):
        if right:                                                      # a right click: the auto-queue (#3524)
            auto(g, p, rect, slot)
        elif building == "MARKET" and slot >= market.ROW:
            market.order(g, p, slot - market.ROW, shift, lambda: show(g, p, rect))
        else:
            order(g, p, rect, slot, shift)
    click.rect, click.key = rect, shown(g, rect)                       # refresh() compares the key (#1335)
    menu.show(g, player, build.pretty(building), items, click)


def auto(g, player, rect, slot):
    """A right click on the unit item in slot sets the auto-queue of the building rect to that unit, as in AoE2 DE
    (#3524): tick() queues it again each time the queue is empty. A second right click stops it. One unit per building;
    a technology or another item has none. Returns the unit name, or None."""
    name = next((n for n, (s, *_) in layout(g, rect).items() if s == slot and n not in TECHS), None)
    if name is None:
        return None
    on, by = vars(g).setdefault("auto", {}), vars(g).setdefault("auto_by", {})
    if on.get(rect) == name:
        del on[rect]
    else:
        on[rect], by[rect] = name, player
    build.say(g, player, f"Auto-queue {build.pretty(name)}: {'on' if on.get(rect) else 'off'}.")
    show(g, player, rect)
    return name if on.get(rect) else None


def requeue(g):
    """Queue the auto-queue unit of each building with an empty queue (#3524). With too few resources it waits with
    no message, as in AoE2 DE. A building that fell or changed owner (not in homes()) loses its entry."""
    on, home = vars(g).get("auto", {}), homes(g)
    for rect, name in list(on.items()):
        if rect not in home:
            del on[rect]
        elif not g.queues.get(rect) and not build.locked(g, name) and not missing(g, name) \
                and all(g.stock[r] >= v for r, v in price(g, name, home[rect], rect).items()):
            queue(g, g.auto_by.get(rect, "@a"), rect[::2], name)


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


def units_of(g, building):
    """The units (not the technologies) that building trains, with trains() (the Mapuche Settlement, the upgraded
    units, #3100): only such a building has a rally point."""
    return [n for n in trains(g, building) if n not in TECHS]


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
    if vars(g).get("auto", {}).get(rect) == name:                      # a cancel also ends its auto-queue (#3524)
        del g.auto[rect]
    e = q.pop(start + k - 1)
    if e.get("free"):                                                  # the free unit is free again (#4330)
        g.free_trained[rect][name] -= 1
    for r, v in e.get("paid", COSTS[name]).items():                    # a free technology gives back nothing
        g.stock[r] += v
        g.command(f"scoreboard players add {r.capitalize()} {g.board} {v}")
    return name


def order(g, player, rect, slot, shift=False):
    """A click on the menu item in slot: queue 1 unit (a shift click: SHIFT, as many as the resources and the queue
    allow) at the building rect, or cancel a unit of the queue row (cancel()), and refresh the menu. Returns the
    number of queued units. A click on RALLY closes the menu: the next right click on the ground sets the rally point
    (gather.Gather.click calls rally())."""
    if slot == RALLY[0] and units_of(g, homes(g)[rect]):
        g.rallying[player] = rect
        menu.close(g, player)
        g.command(f"tellraw {player} " + json.dumps({"text": "Right click the ground for the rally point.",
                                                      "color": "gray"}))
        return 0
    if slot == garrison.ungarrison(homes(g)[rect])[0] and getattr(g, "garrisons", {}).get(rect):   # all units come out (#808)
        garrison.out(g, rect)
        show(g, player, rect)
        return 0
    if slot == garrison.BELL[0] and homes(g)[rect] == "TOWN_CENTER":   # the town bell (#3419)
        garrison.all_back(g, player) if vars(g).get("bell_work") else garrison.bell(g, player)   # (#3420)
        menu.close(g, player)
        return 0
    if slot == demolish.ITEM[0] and demolish.delete(g, player, rect):   # the building falls (#3452)
        return 0
    if ROW <= slot < MORE:                                         # the queue row; MORE: more items (#1485)
        cancel(g, player, rect, slot - ROW)
        show(g, player, rect)
        return 0
    name = next((n for n, (s, *_) in layout(g, rect).items() if s == slot), None)   # the shown item of the slot (#3098)
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
        ai.move(g, uuid, name, g.map.T, x + 0.5, g.map.y(x, z), z + 0.5, ai.NORMAL * speed(g, name, uuid))
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
    if name in ONE_BUILDING and not offered(g, rect, name):           # one upgrade per building (#2484)
        return None
    if name in TECHS and name not in ONE_BUILDING and (not repeatable(g, name) or queued(g, name)) or not unlocked(g, name):
        return None                                                    # a technology once
    if flag := value("toggle", name):                                  # a switch: no queue and no cost (#3422)
        vars(g)[flag] = not vars(g).get(flag, False)
        build.say(g, player, f"{ITEMS[name][2]}: {'on' if vars(g)[flag] else 'off'}.")
        return rect
    if name in DOCTRINES:                                              # no queue: at once (#2483)
        switch(g, player, homes(g)[rect])
        return rect
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
    if not offered(g, rect, name) and name not in own(g, homes(g)[rect]):   # no free unit left (#4330)
        return None
    free = bool(free_left(g, rect, name))
    cost = price(g, name, homes(g)[rect], rect)
    if any(g.stock[r] < v for r, v in cost.items()):
        build.say(g, player, f"Not enough resources: a {build.pretty(name).lower()} costs "
                             + ", ".join(f"{v} {r}" for r, v in cost.items()) + ".")
        return None
    for r, v in cost.items():
        g.stock[r] -= v
        g.command(f"scoreboard players remove {r.capitalize()} {g.board} {v}")
    k = vars(g).get("doctrines", {}).get(homes(g)[rect], 0)            # its doctrine stays (#2483)
    if free:                                                           # one of the free units (#4330)
        n = vars(g).setdefault("free_trained", {}).setdefault(rect, {})
        n[name] = n.get(name, 0) + 1
    q.append({"name": name, "progress": 0.0, "player": player} | ({"paid": cost} if cost != COSTS[name] else {})
             | ({"free": True} if free else {})
             | ({"doctrine": k} if k and name not in TECHS else {}))
    record.queued(g, name, rect)                                       # Record Game (#2649)
    return rect


def count(g, t):
    """How often the player researched technology t: 0 or 1, more only with the cheat "going above and beyond" (#968)."""
    return (t in getattr(g, "techs", ())) + getattr(g, "repeats", {}).get(t, 0)


def offered(g, rect, name):
    """True when the building rect offers name: an upgrade of one building (ONE_BUILDING) only to a building that has
    none and researches none (#2484), the other items as repeatable() and unlocked()."""
    if name not in own(g, homes(g)[rect]) and not free_left(g, rect, name):   # no free unit left (#4330)
        return False
    if name in ONE_BUILDING and (rect in getattr(g, "upgraded", {})
                                 or any(e["name"] in ONE_BUILDING for e in g.queues.get(rect, ()))):
        return False
    return repeatable(g, name) and unlocked(g, name)


def repeatable(g, name):
    """True when the player can research technology name (again), and for each unit: a technology once, or REPEAT
    times with the cheat "going above and beyond" (#968; ages and unit upgrades stay once). The effects stack: stats()
    and the gather tables take count()."""
    if name in civs.policies(g).get("effects", ()):                # a policy: each one but the active one (#2485)
        return name != civs.policy(g)[0]
    if count(g, name) < vars(g).get("trigger_stacks", {}).get(name, 0):   # "Enable Technology Stacking" (#2866)
        return True
    return name not in g.techs or name in AGAIN or getattr(g, "beyond", False) and name not in REQUIRES and name not in UPGRADES \
        and value("walls", name) is None and count(g, name) < REPEAT


def price(g, name, building=None, rect=None):
    """The cost of unit or technology name with the bonuses of the civilization (civs.COSTS, #1091); a technology is
    free with the cheat "tech tech one two free" (#968). Shipwright: a ship costs 20 % less wood (#1490). A unit of
    building: the food and wood factor of its Recruitment Doctrine (doctrine(), Macedonians, #2483). A free unit of
    the building rect (free_left(), #4330) costs nothing."""
    if rect is not None and free_left(g, rect, name):
        return {}
    if name in TECHS and getattr(g, "free_techs", False):
        return {}
    if name in (p := civs.policies(g)).get("effects", ()):          # a switch of policy: the gold of the next one (#2485)
        n = vars(g).get("switches", 0) + sum(e["name"] in p["effects"] for q in getattr(g, "queues", {}).values() for e in q)
        return {k: v for k, v in {"gold": p["gold"][min(n, len(p["gold"]) - 1)]}.items() if v}   # the first one is free
    cost = civs.cost(g, name, per_enemy(g, name))
    if "wood" in cost and shipwright(g, name):
        cost["wood"] = int(cost["wood"] * SHIPWRIGHT[0] + 0.5)
    if building and name not in TECHS and (f := doctrine(g, building)[1]) != 1:
        cost.update((r, int(v * f + 0.5)) for r, v in cost.items() if r in ("food", "wood"))   # gold stays
    return cost


def doctrine(g, building, k=None):
    """[name, food and wood factor, time factor] of the Recruitment Doctrine k (default: the present one) of building
    (the civ key "doctrines": Macedonians at the barracks, archery range and stable, AoE2 wiki, #2483), else no change."""
    rows = civs.value("doctrines", civs.civ(g), []) if building in DOCTRINES.values() else []
    return rows[vars(g).get("doctrines", {}).get(building, 0) if k is None else k] if rows else ["Balanced", 1, 1]


def switch(g, player, building):
    """The next Recruitment Doctrine of the building type, free and at once (the menu item of DOCTRINES): it changes
    the cost and time of the units queued from now on, not of the queued ones (AoE2 wiki "Macedonians (Chronicles)")."""
    rows = civs.value("doctrines", civs.civ(g), [])
    if not rows:                                                   # no doctrine with Full Tech Tree (#3095)
        return
    d = vars(g).setdefault("doctrines", {})
    d[building] = (d.get(building, 0) + 1) % len(rows)
    build.say(g, player, f"{build.pretty(building)}: {doctrine(g, building)[0]} Recruitment.")


def per_enemy(g, name):
    """The cost of name before the civilization bonuses: COSTS, plus for the key "per_own" [kinds, cost] that cost for
    each own unit of the kinds, or for PER_ENEMY (Spies, #2193) that cost for each enemy civilian unit, at least once and at most the "most" of the line (AoE2 DE wiki: 200 to 30,000 gold)."""
    if (own := value("per_own", name)):                            # Flemish Revolution: more for each own unit (#4323)
        kinds, more = own
        names = [o["name"] for o in g.units if o.get("uuid") in g.villagers] + list(g.soldiers.values())
        n = sum(any(u.startswith(k) for k in kinds) for u in names)
        return {r: COSTS[name].get(r, 0) + more.get(r, 0) * n for r in COSTS[name] | more}
    if name not in PER_ENEMY:
        return COSTS[name]
    import fog                                                     # fog imports gather, gather imports this module
    kinds, most = PER_ENEMY[name]
    n = max(1, sum(any(u.startswith(k) for k in kinds) for u in fog.units(g)[1].values()))
    return {r: min(v * n, most.get(r, v * n)) for r, v in COSTS[name].items()}


SHIPS = {n for n in TRAINS.get("DOCK", ()) if n not in TECHS}                 # the ships of the dock (#1490) ...
for _ in UPGRADES:                                                    # ... and the ships that its upgrades make (#3100)
    SHIPS |= {new for t in UPGRADES for old, new in lines(t) if old in SHIPS}


def shipwright(g, name):
    """True when name is a ship of the dock, also after an upgrade (SHIPS), and the player researched Shipwright (#1490):
    a ship in the queue keeps the bonus when its line is upgraded."""
    return "SHIPWRIGHT" in getattr(g, "techs", ()) and name in SHIPS


def queued(g, name):
    """True when a queue of the player has name in it."""
    return any(e["name"] == name for q in g.queues.values() for e in q)


def owned(g):
    """The names of the complete own buildings of the player: the start ones and the built ones, not the fallen ones
    (ruins.py)."""
    return [o["name"] for o in g.data["objects"] if o["kind"] == "building" and o["player"] == g.player
            and not ruins.fallen(g, o)] + \
        [s["name"] for s in g.sites if s.get("done") and s["player"] == g.player]


def missing(g, name):
    """The text of the buildings that technology name still needs (REQUIRES), or None."""
    n, names, *alone = REQUIRES.get(name, (0, ()))
    if civs.civ(g) in civs.AGE_NO_BUILDINGS:                       # the Khmer (#1926)
        return None
    import combat                                                  # combat imports gather, gather imports this module
    own = {combat.STANDS_FOR.get(b, b) for b in owned(g)}          # the Folwark is a mill, the church a monastery
    has, alone = sorted(set(names) & own), alone[0] if alone else ()
    count = len(has) + sum(AGE_COUNT.get(b, 1) - 1 for b in set(owned(g)) if combat.STANDS_FOR.get(b, b) in names)
    if count < n and not set(alone) & own:
        return f"needs {''.join(f'a {build.pretty(b).lower()} or ' for b in alone)}{n} of {', '.join(build.pretty(b).lower() for b in names)} ({min(count, n)}/{n})"


def age(g):
    """The name of the age of the player."""
    return AGES[build.ages(g)]


OPERATIONS = {1: lambda v, q: q, 2: lambda v, q: v + q, 3: lambda v, q: v - q,   # the AoE2 Operation of a trigger:
              4: lambda v, q: v * q, 5: lambda v, q: v / q if q else v}   # set, add, subtract, multiply, divide
# The AoE2 unit classes (ObjectClass) of "Modify Attribute for Class" (#2859) -> a test of the combat classes of a unit:
# the camels are cavalry, a cavalry archer or a hand cannoneer is not in the class "archer"
CLASSES = {
    "archer": lambda c: "archer" in c and not {"cavalry", "gunpowder"} & c,
    "cavalry": lambda c: bool({"cavalry", "camel"} & c) and "archer" not in c,
    "cavalry_archer": lambda c: {"archer", "cavalry"} <= c,
    "hand_cannoneer": lambda c: {"archer", "gunpowder"} <= c,
    "infantry": lambda c: "infantry" in c,
    "siege_weapon": lambda c: "siege" in c,
    "spearman": lambda c: "spearman" in c,
    "war_elephant": lambda c: "elephant" in c and "archer" not in c,
    "warship": lambda c: "warship" in c,
}


def applies(unit, name):
    """True when the unit of a "Modify Attribute" line is AoE2 unit name: its type, or its class "@<class>" (CLASSES,
    #2859). A class with no test: no unit."""
    import combat                                                  # combat imports gather, gather imports this module
    test = CLASSES.get(unit[1:]) if unit.startswith("@") else None
    return unit == name or test is not None and name in combat.STATS and test(set(combat.stats(name).classes))


def trample_command(g, uuid, name):
    """combat.trample_command of unit name: its own trample (the elephants, #4397), else the splash of a researched
    technology with the key "trample" whose effect holds for the unit (Druzhina, #4496), with the blast radius of the
    unit (stats). None without both."""
    import combat                                                  # combat imports gather, gather imports this module
    if name in combat.TRAMPLE:
        return combat.trample_command(uuid, name, g.map.T)
    s = stats(g, name, uuid)
    t = next((t for tech, t in sorted(BY_KEY["trample"].items()) if tech in g.techs and s.blast and not s.range
              and any(test(x, name, combat.stats(name)) for x in value("effect", tech).get("if", ()))), None)
    return t and combat.trample_command(uuid, name, g.map.T, {**t, "radius": s.blast})


def stats(g, name, uuid=None):
    """The combat values of AoE2 unit name with the bonuses of the civilization (civs.UNITS) and the technologies of
    the player (combat.stats and TECHS), twice for civs.TWICE (#1561), n times for civs.SMITH_UNITS (#2174), and the
    hit points of civs.TECH_HP (#2269). With uuid: also the trigger changes of that unit (unit_values, #3083) and the
    steps of the own units near it (g.near, near.py, #4333)."""
    import combat                                                  # combat imports gather, gather imports this module
    s, twice = civs.units(g, name, combat.stats(name)), civs.TWICE.get(civs.civ(g), ())
    times, also, more = civs.smith(g, name, s), civs.ALSO.get(civs.civ(g), {}), civs.MORE.get(civs.civ(g), {})
    for t in sorted(g.techs):
        e = (EACH if t in times else TECHS)[t] if t not in more else effect(value("effect", t), more[t])   # Varangian
        if t in also and civs.GROUPS[also[t]](name, s):              # Bloodlines +50 %; Bohemian Sanctity: the
            e = EACH[t]                                            # villagers too (#2173)
        for _ in range(count(g, t) * (1 + (t in twice)) * times.get(t, 1)):   # "going above and beyond" stacks (#968)
            s = e(name, s)
    for group, building, hp in civs.TECH_HP.get(civs.civ(g), ()):   # the Aztec monks (#2269)
        if civs.GROUPS[group](name, s):
            s = s._replace(hp=s.hp + hp * sum(t in g.techs for t in TRAINS[building] if t in TECHS))
    for t, k in sorted(vars(g).get("near", {}).get(uuid, {}).items()):   # the own units near it (near.py, #4333)
        s = near.change(BY_KEY["near"][t], k, s)
    if name.startswith("VILLAGER") and (f := civs.handicap(g.data, g.player)) != 1:   # the AoE2 "Handicap" (#2474)
        s = s._replace(hp=round(s.hp * f))
    for unit, field, op, q in vars(g).get("trigger_attributes", ()):   # "Modify Attribute" of a scenario (#2763)
        if applies(unit, name):
            v = max(0, OPERATIONS[op](getattr(s, field), q))
            s = s._replace(**{field: v if field in ("range", "reload") else int(v)})   # AoE2: whole hit points, armor
    for field, op, q in vars(g).get("unit_values", {}).get(uuid, ()):   # "Change Object HP" and others (scenario.values)
        if field in s._fields:
            s = s._replace(**{field: int(max(0, OPERATIONS[op](getattr(s, field), q)))})
    return s


def seconds(g, name, building=None, k=None):
    """The train time of unit or technology name: TRAIN_TIMES, or the time of its key "faster" from its age (the eagle scout trains
    in 46 s in the Feudal Age and in 35 s from the Castle Age, AoE2 DE wiki) or of its key "age_times" in the age of the player (#3713),
    divided by the work rate of the civilization at building (civs.work_rate: Persian town centers and docks, #1894), its rate of the unit group
    (civs.train_rate: Aztec military units, Khitan skirmishers, #1927) and its age-up rate (civs.age_rate: the Malay, #1926),
    times its research time of the technology (civs.research_time: the Gothic Loom at once, #2172) and its time factor
    at building (civs.train_time: Mapuche Settlements, #2432), and of the Recruitment Doctrine k of a unit (doctrine(),
    default the present one, #2483). The time of "Add Train Location" at building replaces TRAIN_TIMES (#2865)."""
    age, time = value("faster", name, (9, 0))
    if each := value("age_times", name):                               # a Return of Rome dock trains faster in each age (#3713)
        age, time = 0, each[min(build.ages(g), len(each) - 1)]
    base = vars(g).get("trigger_times", {}).get(name)                  # "Change Technology Research Time" (#2820)
    own = (added(g, building, name) or (0, 0))[1] if building else 0   # Add Train Location (#2865)
    return (own or (base if base is not None else time if build.ages(g) >= age else TRAIN_TIMES[name])) \
        / (civs.work_rate(g, building) * work(g, building) if building else 1) \
        / civs.train_rate(g, name) / (group_rate(g, name) if name not in TECHS else 1) / civs.age_rate(g, name) * civs.research_time(g, name) / civs.turbo(g, name) \
        * (civs.train_time(g, building, name) if building else 1) \
        * (doctrine(g, building, k)[2] if building and name not in TECHS else 1)


def speed(g, name, uuid=None):
    """The factor of the walk speed of unit name: the bonus of the civilization (civs.speed) and the technologies of the
    player (the key "walk": Fervor, #1261; Squires for the class infantry, #1415; Husbandry for the mounted units, #1416) and the
    added tiles per second (the key "walk_add": Aristocracy, #3921), with the changes of civs.ALSO and civs.MORE (Bohemian Fervor for the villagers, Varangian Caravan +50 %, #2173); unit uuid
    near a Military Town Center walks faster (g.hurried, regen.military, #2496). The speed changes of the triggers on
    unit uuid (unit_values, scenario.values, #3083) change its tiles per second (a set: that speed)."""
    also, more = civs.ALSO.get(civs.civ(g), {}), civs.MORE.get(civs.civ(g), {})
    f = civs.speed(g, name) * math.prod((1 + (f - 1) * more[t] if t in more else f) ** count(g, t)
                                        for t, (unit, f) in BY_KEY["walk"].items() if faster(unit, name) or t in also and faster(also[t], name))
    if add := sum(v * count(g, t) for t, (unit, v) in BY_KEY["walk_add"].items() if faster(unit, name)):
        import ai                                                  # ai imports gather, gather imports this module
        f += add / ai.walk_speed(name, 1, 1)                       # tiles per second on the base speed (Aristocracy, #3921)
    if changes := [(op, q) for field, op, q in vars(g).get("unit_values", {}).get(uuid, ()) if field == "speed"]:
        import ai                                                  # ai imports gather, gather imports this module
        base = ai.walk_speed(name, 1, 1)                           # tiles per AoE2 second
        f = max(0, functools.reduce(lambda v, c: OPERATIONS[c[0]](v, c[1]), changes, base * f)) / base
    return f * vars(g).get("hurried", {}).get(uuid, 1)


def faster(unit, name):
    """True when the "walk" entry unit (a unit name, a class of combat.STATS in lower case, a group of civs.GROUPS, a
    building: the units it trains (Drill, #4254), or a list of these (Herbalism, #4254)) covers unit name."""
    if isinstance(unit, list):
        return any(faster(u, name) for u in unit)
    import combat                                                  # combat imports gather, gather imports this module
    s = combat.stats(name)
    return unit == name or unit in civs.GROUPS and civs.GROUPS[unit](name, s) or unit.islower() and unit in s.classes \
        or BUILDING_OF.get(name) == unit


def hits(g, name):
    """The keywords of combat.damage and combat.stats_command for unit name of the player of g (#4331): less, {attacker
    class: n} of the key "less" of its technologies whose units cover it (Royal Heirs), and ignore, True when a
    technology with the key "ignore_armor" covers this melee unit (Wootz Steel), or the unit has the key "ignore_armor"
    in data/units.jsonl (Leitis, #4394). faster() tests the units of both.
    rage: the attack for each 10 % of lost hit points of the key "rage" (Hamask), reflect: the part of the key "reflect"
    (Lamellar Armor, #4332), both summed over the technologies whose units cover it."""
    import combat                                                  # combat imports gather, gather imports this module
    less = {}
    for t, (unit, cut) in BY_KEY["less"].items():
        if t in getattr(g, "techs", ()) and faster(unit, name):
            less = {c: less.get(c, 0) + cut.get(c, 0) for c in less | cut}
    ignore = name in combat.IGNORE or combat.stats(name).range <= 0 and any(
        faster(u, name) for t, u in BY_KEY["ignore_armor"].items() if t in getattr(g, "techs", ()))
    more = {k: sum(n for t, (unit, n) in BY_KEY[k].items() if t in getattr(g, "techs", ()) and faster(unit, name))
            for k in ("rage", "reflect")}
    return {"less": less, "ignore": ignore} | more


def start(g, setting):
    """The AoE2 DE setting "Starting age" (STARTS, run.py --age): the player starts with the ages and with all
    technologies of the earlier ages that its civilization has (AoE2 wiki "Random map"); "post-imperial" with all
    technologies except "skip" (wiki "Post-Imperial Age"). No age bonus pays: the player does not advance (#2265)."""
    s = STARTS[setting]
    for t in build.AGE_TECHS[:s["ages"]]:
        research(g, {"name": t}, start=True)
    switches = (*DOCTRINES, *(n for r in civs.ROWS if "policies" in r for n in r["policies"].get("effects", ())))
    skip = (*build.AGE_TECHS, *s.get("skip", ()), *switches)   # a switch changes the player, it is no technology (#2967)
    while todo := [t for t in TECHS if t not in g.techs and t not in skip and value("age", t, 0) < s["ages"]
                   and t not in ONE_BUILDING and unlocked(g, t)]:  # in passes: a technology after the one before it;
        for t in todo:                                             # no upgrade of one building (#2484)
            research(g, {"name": t}, start=True)


HASTE_EVERY = 2.0                                                  # AoE2 seconds between two checks of haste()


def haste(g, dt):
    """The own military units within the "attack_aura" range (tiles from the footprint) of an upgraded own building
    attack "rate" times as fast (the Defensive Town Center: +17.65 %, 8 tiles, #2497): a unit that comes in or goes out
    gets its values again, with the reload / rate. g.hasted: {uuid: rate} of the fast units. A trebuchet keeps its
    values (the values of its state: trebuchet.stats_command)."""
    import combat, trebuchet                                       # both import this module: import them late
    auras = [(r, a) for r, n in vars(g).get("upgraded", {}).items() if (a := value("attack_aura", n))]
    hasted = vars(g).get("hasted", {})
    g.haste_time = vars(g).get("haste_time", 0.0) + dt if auras or hasted else 0.0
    if g.haste_time < HASTE_EVERY:
        return
    g.haste_time, own, T = 0.0, homes(g), g.map.T
    fast = {u: rate for u, (x, _, z) in g.positions(sorted(u for u, n in g.soldiers.items() if n != trebuchet.NAME)).items()
            if (rate := max([a["rate"] for r, a in auras if r in own
                             and max(r[0] - x, x - r[1], r[2] - z, z - r[3]) <= a["range"] * T], default=1)) != 1}
    for u in sorted(fast.keys() ^ hasted.keys() | {u for u in fast if fast[u] != hasted.get(u)}):
        name = g.soldiers.get(u)
        if name is None:
            continue
        s = stats(g, name, u)
        s = s._replace(reload=s.reload / fast.get(u, 1))
        g.command(stats_line(g, u, name, s))
        if cmd := combat.range_command(u, name, T, s=s):
            g.command(cmd)
    g.hasted = fast


def research(g, entry, start=False, rect=None):
    """A technology is complete: keep it in g.techs and give the live villagers and military units the new values.
    start: a technology of the start age (start()): no text and no bonus of an age or technology. An upgrade of one
    building (ONE_BUILDING) changes only the building rect that researched it (g.upgraded, #2484)."""
    import combat, gather                                          # gather imports this module
    if entry["name"] in civs.policies(g).get("effects", ()):       # Athenians: the new policy, not a technology (#2485)
        g.policy, g.switches = entry["name"], vars(g).get("switches", 0) + 1
        g.command(f"tellraw {entry['player']} " + json.dumps({"text": f"{ITEMS[entry['name']][2]} is active.",
                                                              "color": "green"}))
        return
    if entry["name"] in ONE_BUILDING:
        vars(g).setdefault("upgraded", {})[rect] = entry["name"]
        build.retower(g, g.techs, rect)                            # the values of this building only (#2497)
        if value("arrows", entry["name"]):
            g.command(garrison.arrows_command(g, rect))
        return
    if entry["name"] in g.techs:                                   # a repeat: "going above and beyond" (#968)
        g.repeats[entry["name"]] = g.repeats.get(entry["name"], 0) + 1
    before = set(g.techs)
    g.techs.add(entry["name"])
    if not start:
        record.aged(g, entry["name"])                                  # Record Game (#2649)
        g.command(f"playsound {EVENT_SOUNDS['research']} master @a[team=p{g.player}] ~ ~ ~ 1 1")
    if gather.has_mode(g, "scenario"):                             # a trigger condition "Research Technology" (#2656)
        g.command(f"scoreboard players set #p{g.player}.{entry['name']} aoe_tech 1")
    if start:                                                      # free: not in the score (score.py, #2355)
        vars(g).setdefault("given", set()).add(entry["name"])
    if (more := gather.FARM_TECHS.get(entry["name"])):             # the new and the live own farms get more food
        more = round(more * civs.FARM_UPGRADES.get(civs.civ(g), 1))
        g.map.farm_food += more
        for t in g.map.own_farms:
            if g.map.farms.get(t, 0) > 0:
                g.map.farms[t] += more
    if walls := value("walls", entry["name"]):                    # the complete own walls become the new wall (#1326)
        for site in [s for s in g.sites if s["name"] in walls and s.get("done")
                     and s["player"] == g.player]:
            build.upgrade(g, site, combat.wall(site["name"], build.ages(g), civs.civ(g), civs.handicap(g.data, g.player)))
    build.retower(g, before)                                       # the complete own towers get the new values (#1374),
                                                                   # the buildings those of Masonry and Fletching (#1398, #1408)
    if entry["name"] in build.AGE_TECHS and not start:             # the timeline of the recap book (#2660)
        import recap                                               # recap imports this module
        recap.aged(g, entry["name"])
    if entry["name"] in build.AGE_TECHS:                           # the base arrows of the new age (civs.ARROWS, #2178)
        names = {n for names, _ in civs.ARROWS.get(civs.civ(g), ()) for n in names}
        for rect in [r for r, o in garrison.holders(g).items() if o["name"] in names]:
            g.command(garrison.arrows_command(g, rect))
    if (more := value("more_arrows", entry["name"])) or (more := value("pass_arrows", entry["name"], {}).get("names")):
        for rect, o in garrison.holders(g).items():                # the own buildings of the names shoot more (#4258),
            if o["name"] in more:                                  # or their arrows pass through (#4282)
                g.command(garrison.arrows_command(g, rect))
    if (free := value("spawn", entry["name"])) and not start:     # free units at own buildings (First Crusade, #4365)
        unit = free["unit"]
        while (up := next((n for t in sorted(g.techs & set(UPGRADES)) for o, n in lines(t, g) if o == unit), None)):
            unit = up                                              # the upgraded unit of the line (Elite Serjeant)
        for rect in sorted(r for r, n in homes(g).items() if n == free["at"])[:free["most"]]:
            for _ in range(free["count"]):
                spawn(g, rect, unit)
    for hook in value("on_research", entry["name"], ()):          # the special effect in its own module (#3243):
        module, function = hook.rsplit(".", 1)                     # import it late, it imports gather or this module
        getattr(importlib.import_module(module), function)(g, entry)
    if entry["name"] in UPGRADES:                                  # the live units of the line get the new name
        for uuid, old, new in [(u, old, new) for old, new in lines(entry["name"], g) for u, n in g.soldiers.items()
                               if n == old]:
            g.soldiers[uuid] = new
            for cmd in type_tag_commands(uuid, old, new):          # the triggers count the new type (#2977)
                g.command(cmd)
            g.command(stats_line(g, uuid, new))
            if cmd := combat.range_command(uuid, new, g.map.T, s=stats(g, new, uuid)):   # the range and blast of an onager
                g.command(cmd)
            if cmd := volley_command(g, uuid, new):               # a war galley of the Armenians (#2379)
                g.command(cmd)
            if cmd := lead_command(g, uuid, new):                 # an elite Spanish cannon galleon (#2430)
                g.command(cmd)
            if cmd := combat.accuracy_command(uuid, new, civs.value("accuracy", civs.civ(g), {}).get(new, 0.0), g.map.T):
                g.command(cmd)                                    # an Elite Arambai hits more often (#4549)
            if cmd := combat.dodge_command(uuid, new):            # an Elite Shrivamsha Rider dodges more (#4399)
                g.command(cmd)
            if cmd := combat.frenzy_command(uuid, new):           # an Elite Temple Guard (#4468)
                g.command(cmd)
            if cmd := combat.low_hp_command(uuid, new):           # an Elite Jian Swordsman (#4472)
                g.command(cmd)
            if cmd := combat.veteran_command(uuid, new):          # an Elite Jaguar Warrior keeps its kills (#4467)
                g.command(cmd)
            if cmd := combat.sunder_command(uuid, new):           # an Elite Obuch (#4466)
                g.command(cmd)
            if cmd := combat.shield_command(uuid, new):           # an Elite Hussite Wagon (#4507)
                g.command(cmd)
            if cmd := trample_command(g, uuid, new):              # an elite elephant tramples (#4397)
                g.command(cmd)
            g.command(combat.label_command(uuid, new))               # the name of a new unit (units.pretty)
    import trebuchet                                               # trebuchet imports this module: import it late
    if vars(g).get("hasted"):                                      # the values below have no haste: haste() sends
        g.hasted = {}                                              # them again (#2497)
    for uuid, name in [(u["uuid"], u["name"]) for u in g.units if "uuid" in u] + list(g.soldiers.items()):
        if stats(g, name, uuid) != combat.stats(name) or hits(g, name) != hits(None, name) or dot(g, name, stats(g, name, uuid)):
            g.command(trebuchet.stats_command(g, uuid) if name == trebuchet.NAME   # the armor of its state (#1409)
                      else stats_line(g, uuid, name))
        if name == trebuchet.NAME and trebuchet.state(g, uuid) != "unpacked":
            continue                                               # packed: range 0, the unpack sends the range (#1414)
        new, base = stats(g, name), combat.stats(name)              # the range (Fletching, #724) or the blast (Warwolf, #4283)
        if (new.range, new.blast) != (base.range, base.blast) and (cmd := combat.range_command(uuid, name, g.map.T, s=stats(g, name, uuid))):
            g.command(cmd)                                         # a melee unit with a blast has no range (#4496)
        if entry["name"] in BY_KEY["trample"] and (cmd := trample_command(g, uuid, name)):
            g.command(cmd)                                         # the live units get the splash (Druzhina, #4496)
    for cmd in [c for uuid, name in g.soldiers.items() for c in fire_commands(g, uuid, name, {entry["name"]})]:
        g.command(cmd)                                             # the live fire ships: Siphons, Incendiaries (#2165)
    for uuid, name in g.soldiers.items():                          # the live gunpowder units aim ahead (Arquebus, #4364)
        if cmd := lead_command(g, uuid, name, {entry["name"]}):
            g.command(cmd)
    for uuid, name in g.soldiers.items():                          # the extra projectiles of the live units (#4338):
        if any(value("volley", t, {}).get(name) for t in g.techs) and (cmd := volley_command(g, uuid, name)):
            g.command(cmd)                                         # also a new attack of a "part" after an upgrade
    if entry["name"] in BY_KEY["walk"]:                            # the live units walk faster (Fervor)
        import ai, fleet                                           # ai imports gather, gather imports this module
        for uuid, name in g.soldiers.items():                      # a ship: fleet.tick reads speed() (#2136)
            if faster(value("walk", entry["name"])[0], name) and name not in fleet.SPEEDS:
                g.command(ai.speed_command(uuid, name, g.map.T, gather.NORMAL * speed(g, name, uuid)))
    if entry["name"] in REQUIRES:                                  # an age: all players see it, as in AoE2
        import ai                                                  # ai imports gather, gather imports this module
        for site in [s for s in g.sites if s["name"] in combat.WALLS and s.get("done") and s["player"] == g.player]:   # #1372
            build.upgrade(g, site, combat.wall(build.design(g, site["name"], g.player), build.ages(g) - 1, civs.civ(g),
                                                      civs.handicap(g.data, g.player)),
                          redraw=False)
        for uuid, name in g.soldiers.items():                      # the walk speed of the age (civs.UNITS, Celts)
            if civs.speed(g, name) != 1:
                g.command(ai.speed_command(uuid, name, g.map.T, gather.NORMAL * speed(g, name, uuid)))
        if start:
            return
        for r, v in civs.AGE_GIFTS.get(civs.civ(g), {}).items():    # Dravidians, Ethiopians (#1926)
            g.stock[r] += v
            g.command(f"scoreboard players add {r.capitalize()} {g.board} {v}")
        for rect in [r for r, n in homes(g).items() if n == "TOWN_CENTER"]:   # Bengalis: free villagers (#1926)
            for _ in range(civs.AGE_VILLAGERS.get(civs.civ(g), 0)):
                if spawn(g, rect, "VILLAGER_MALE"):
                    g.pop += 1
        rects = [r for r, n in homes(g).items() if n == "TOWN_CENTER"]
        unit = civs.value("age_units", civs.civ(g), {}).get(entry["name"])   # Spartans: a free Polemarch (#2480)
        if unit and rects and spawn(g, rects[0], unit):
            g.pop += 1
        g.command(f"title @a[team=p{g.player}] title " + json.dumps({"text": age(g), "color": "gold"}))  # the own team only
        g.command("tellraw @a " + json.dumps({"text": f"Player {g.player} advances to the {age(g)}.", "color": "gold"}))
        g.command("playsound minecraft:ui.toast.challenge_complete master @a ~ ~ ~ 1 1 1")
        return
    if start:
        return
    for r, v in civs.TECH_GIFTS.get(civs.civ(g), {}).items():       # Spanish: 20 gold, not for an age (#2175)
        g.stock[r] += v
        g.command(f"scoreboard players add {r.capitalize()} {g.board} {v}")
    if entry["name"] in civs.ECONOMY:                              # Wei: free villagers at an own town center (#2175)
        rects = [r for r, n in homes(g).items() if n == "TOWN_CENTER"]
        for _ in range(civs.value("economy_villagers", civs.civ(g), 0) * bool(rects)):
            if spawn(g, rects[0], "VILLAGER_MALE"):
                g.pop += 1
    g.command(f"tellraw {entry['player']} " + json.dumps({"text": f"{ITEMS[entry['name']][2]} is researched.",
                                                          "color": "green"}))


def limit(g):
    """The population limit: 5 per complete own town center and house, 20 per castle (civs.HOUSING: other values of
    a civilization, #2118), also of the buildings in g.housing_kept (ruins.fall: Nomads, #4280), at most max_pop()."""
    own = civs.HOUSING.get(civs.civ(g), {})
    factor = {}                                                        # Urbanization: the houses give double (#3919)
    for t in getattr(g, "techs", ()):
        for n, f in value("housing_factor", t, {}).items():
            factor[n] = factor.get(n, 1) * f
    kept = vars(g).get("housing_kept", [])                             # fell after a "keep_housing" research (#4280)
    return min(max_pop(g), sum(own.get(n, HOUSING.get(n, 0)) * factor.get(n, 1) for n in owned(g) + kept))


def max_pop(g):
    """The highest population limit: the setting of the game (Gather.pop_limit, run.py --pop-limit, #2266), else LIMIT,
    with the extra limit of civs.POP_CAP from its age (the Goths, #2118); 1000 with the cheat "my cpu can handle it"
    (#968)."""
    age, extra = civs.POP_CAP.get(civs.civ(g), (0, 0))
    return getattr(g, "pop_cap", None) or (getattr(g, "pop_limit", None) or LIMIT) + extra * (build.ages(g) >= age)


def census(g):
    """Count the live villagers and military units of the player (a dead unit has no position) and show the counts.
    A dead villager leaves g.villagers, the selection and its farm: the idle count and the bot see only live ones (#1039). A dead soldier leaves g.soldiers and
    the selection (#3122)."""
    live = g.positions(list(g.villagers) + list(g.soldiers))
    import spoils                                                      # spoils imports this module
    import score                                                       # score imports this module
    dead = {u: "VILLAGER" if u in g.villagers else g.soldiers[u] for u in [*g.villagers, *g.soldiers] if u not in live}
    spoils.fallen(g, dead)                                             # Tupi (#2271)
    score.fallen(g, dead)                                              # #2355
    spoils.kills(g)                                                    # Mapuche (#2271)
    spoils.attacks(g)                                                  # Varangian Guard (#2376)
    for u in [u for u in g.villagers if u not in live]:
        del g.villagers[u]
        g.drop(u)                                                      # from the selection of each person (#3486)
        for t in [t for t, f in g.farmers.items() if f == u]:
            del g.farmers[t]
    for u in [u for u in g.soldiers if u not in live]:                # the ticks of ships and towers wait for it (#3122)
        del g.soldiers[u]
        g.drop(u)                                                      # from the selection of each person (#3486)
    g.pop, g.census = sum(weight(g, g.soldiers.get(u)) for u in live if g.soldiers.get(u) not in build.MOVES), 0.0   # a mule cart is a building
    sidebar(g)


LABELS = {"Limit": "Pop. limit"}                                  # the shown name of a sidebar line (owner, #990)


def sidebar(g):
    """Show the population and the limit as two lines of the sidebar (g.board) and the age in its title, only when
    they changed."""
    for name, n in (("Population", math.ceil(g.pop)), ("Limit", limit(g))):   # a half unit counts as one (#3918)
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
    requeue(g)
    cap, out, home = limit(g), [], homes(g)
    fast = {r for r, n in home.items() if n in CONSCRIPT[0]} if "CONSCRIPTION" in g.techs else set()   # (#1455)
    room = cap - g.pop - sum(weight(g, q[0]["name"]) for q in g.queues.values()
                             if q and q[0]["progress"] > 0 and q[0]["name"] not in TECHS)
    for rect, q in g.queues.items():
        if not q:
            continue
        if q[0]["progress"] == 0 and q[0]["name"] not in TECHS:      # a technology needs no population room
            if room <= 0:
                if not q[0].get("waits"):                              # as the "need more houses" message of AoE2
                    q[0]["waits"] = True
                    build.say(g, q[0]["player"], f"The population is at the limit ({math.ceil(g.pop)}/{cap}): "
                              + ("build more houses." if cap < max_pop(g) else "no more units."))
                continue
            room -= weight(g, q[0]["name"])
            q[0]["waits"] = False
        rate = CONSCRIPT[1] if rect in fast and q[0]["name"] not in TECHS else 1   # units only, not technologies
        rate *= SHIPWRIGHT[1] if shipwright(g, q[0]["name"]) else 1          # the ships of a dock, not its technologies
        time = 0 if getattr(g, "aegis", False) else \
            seconds(g, q[0]["name"], home.get(rect), q[0].get("doctrine", 0))   # cheats.aegis; the doctrine of the queue (#2483)
        q[0]["progress"] = min(1, q[0]["progress"] + (work * rate / time if time else 1))   # 0: the Gothic Loom at once (#2172)
        if q[0]["progress"] >= 1 and q[0]["name"] in TECHS:
            research(g, q.pop(0), rect=rect)
        elif q[0]["progress"] >= 1 and (v := spawn(g, rect, q[0]["name"])):   # no room: it waits in the queue (#2470)
            g.pop += weight(g, q.pop(0)["name"])
            out.append(v)
            record.trained(g, v)                                       # its object ID (#2649)
            trained_voice(g, rect, v)
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
    g.command(f"summon {kind} {pos[0]} {pos[1]} {pos[2]} {units.summon_snbt(nbt)}")
    record.summoned(g, uuid, name, pos, o["player"])                  # a unit of a setup (Record Game, #3028)
    if o["player"] > 0:
        import owners                                              # owners imports gather, gather imports this module
        owners.add(g, uuid, name, o["player"])                     # an enemy of the other sides (#2992)
    import combat, gather                                          # both import gather, gather imports this module
    g.command(stats_line(g, uuid, name, stats(g, name)))
    import spoils                                                  # spoils imports this module
    if cmd := spoils.tag_command(uuid, name):                      # its hits make gold (#2376)
        g.command(cmd)
    if cmd := combat.range_command(uuid, name, g.map.T, s=stats(g, name)):   # an archer shoots from its range (#670)
        g.command(cmd)
    if cmd := volley_command(g, uuid, name):                       # an Armenian galley shoots twice (#2379)
        g.command(cmd)
    if cmd := lead_command(g, uuid, name):                         # a Spanish cannon galleon aims ahead (#2430)
        g.command(cmd)
    if cmd := combat.accuracy_command(uuid, name, civs.value("accuracy", civs.civ(g), {}).get(name, 0.0), g.map.T):
        g.command(cmd)                                             # a Hun trebuchet hits units more often (#2479)
    if cmd := combat.charge_command(uuid, name, g.map.T):          # the Coustillier charges its attack (#4398)
        g.command(cmd)
    if cmd := combat.charged_volley_command(uuid, name):           # a Xianbei Raider fires a charged volley (#4546)
        g.command(cmd)
    if cmd := combat.dodge_command(uuid, name):                    # a Shrivamsha Rider dodges projectiles (#4399)
        g.command(cmd)
    if cmd := combat.vs_units_command(uuid, name, g.map.T):        # the Lou Chuan shoots units in its anti-unit mode (#4505)
        g.command(cmd)
    if cmd := combat.frenzy_command(uuid, name):                   # a Temple Guard attacks faster in a long fight (#4468)
        g.command(cmd)
    if cmd := combat.low_hp_command(uuid, name):                   # a Jian Swordsman loses its shield below 45 HP (#4472)
        g.command(cmd)
    if cmd := combat.veteran_command(uuid, name):                  # a Jaguar Warrior gets attack for each kill (#4467)
        g.command(cmd)
    if cmd := combat.sunder_command(uuid, name):                   # an Obuch lowers the armor of its target (#4466)
        g.command(cmd)
    if cmd := combat.shield_command(uuid, name):                   # a Hussite Wagon shields the units behind it (#4507)
        g.command(cmd)
    if cmd := trample_command(g, uuid, name):                      # an elephant tramples the units next to its target (#4397)
        g.command(cmd)
    if cmd := combat.sight_command(uuid, name, g.map.T, s=stats(g, name), more=sight_more(g.techs, name, combat.stats(name))
                                  + civs.sight_units(g, name, combat.stats(name))):   # it attacks enemies in sight (#775)
        g.command(cmd)
    import ai                                                      # ai imports gather, gather imports this module
    g.command(ai.speed_command(uuid, name, g.map.T, gather.NORMAL * speed(g, name)))   # also without an order (#849)
    if player not in (None, g.player):
        return uuid
    for cmd in fire_commands(g, uuid, name):                       # a new fire ship after Siphons (#2165)
        g.command(cmd)
    # they take move orders as a soldier (#1243, #1253); a ship sails with fleet.py (#1383)
    if gather.soldier(name):
        g.soldiers[uuid] = name
        return uuid
    g.villagers[uuid] = gather.Villager(uuid, pos)
    g.units.append({"kind": "unit", "name": name, "player": g.player, "uuid": uuid,
                    "tile": [math.floor(pos[0]) / g.map.T, math.floor(pos[2]) / g.map.T]})
    return uuid
