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
Forging at the blacksmith (#675): infantry and cavalry get +1 attack. Fletching (#724): archers (also cavalry archers and
skirmishers) get +1 attack and +1 range.
Double-Bit Axe at the lumber camp (#723): villagers chop wood 20 % faster (gather.WORK_TECHS, gather.Gather.work_time).
Gold Mining at the mining camp (#727): villagers mine gold 15 % faster.
Horse Collar at the mill (#726): the live and the new farms of the player have 75 more food (gather.FARM_TECHS).
Wheelbarrow at the town center in the Feudal Age (#728, TECH_AGE): villagers carry 3 more resources and walk 10 % faster (gather.CARRY, gather.PACE).
Rally points (#707): the menu item "Rally point" (RALLY) and the next right click on the ground set the rally point of
the building; each new unit walks there (Minecraft path finding), a new villager gathers at a tree, bush, mine or farm.
The castle (#708) trains the unique unit of the civilization of its player (UNIQUE, trains()). Only the units with AoE2
combat values (combat.STATS) are in its menu.
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
import garrison  # noqa: E402
import menu  # noqa: E402

COSTS = {"VILLAGER_MALE": {"food": 50}, "MILITIA": {"food": 60, "gold": 20},   # as in AoE2
         "ARCHER": {"wood": 25, "gold": 45}, "LOOM": {"gold": 50}, "FEUDAL_AGE": {"food": 500},
         "BERSERK": {"food": 65, "gold": 20},
         "CATAPHRACT": {"food": 70, "gold": 75},
         "CHU_KO_NU": {"wood": 40, "gold": 35},
         "DOUBLE_BIT_AXE": {"food": 100, "wood": 50},
         "FLETCHING": {"food": 100, "gold": 50},
         "FORGING": {"food": 150},
         "GOLD_MINING": {"food": 100, "wood": 75},
         "HORSE_COLLAR": {"food": 75, "wood": 75},
         "HUSKARL": {"food": 75, "gold": 35},
         "JANISSARY": {"food": 60, "gold": 55},
         "LONGBOWMAN": {"wood": 35, "gold": 40},
         "MAMELUKE": {"food": 55, "gold": 85},
         "MANGUDAI": {"wood": 55, "gold": 65},
         "SAMURAI": {"food": 45, "gold": 30},
         "SCALE_MAIL_ARMOR": {"food": 100},
         "SCOUT_CAVALRY": {"food": 80},
         "SKIRMISHER": {"food": 25, "wood": 35},
         "SPEARMAN": {"food": 35, "wood": 25},
         "TEUTONIC_KNIGHT": {"food": 85, "gold": 30},
         "THROWING_AXEMAN": {"food": 55, "gold": 25},
         "WAR_ELEPHANT": {"food": 170, "gold": 85},
         "WHEELBARROW": {"food": 175, "wood": 50},
         "WOAD_RAIDER": {"food": 70, "gold": 25}}
TRAIN_TIMES = {"VILLAGER_MALE": 25, "MILITIA": 21, "ARCHER": 35, "LOOM": 25, "FEUDAL_AGE": 130,   # AoE2 seconds
               "BERSERK": 14,
               "CATAPHRACT": 20,
               "CHU_KO_NU": 16,
               "DOUBLE_BIT_AXE": 25,
               "FLETCHING": 30,
               "FORGING": 50,
               "GOLD_MINING": 30,
               "HORSE_COLLAR": 20,
               "HUSKARL": 13,
               "JANISSARY": 21,
               "LONGBOWMAN": 18,
               "MAMELUKE": 23,
               "MANGUDAI": 26,
               "SAMURAI": 9,
               "SCALE_MAIL_ARMOR": 40,
               "SCOUT_CAVALRY": 30,
               "SKIRMISHER": 22,
               "SPEARMAN": 22,
               "TEUTONIC_KNIGHT": 12,
               "THROWING_AXEMAN": 13,
               "WAR_ELEPHANT": 25,
               "WHEELBARROW": 75,
               "WOAD_RAIDER": 10}
TRAINS = {"TOWN_CENTER": ("VILLAGER_MALE", "LOOM", "FEUDAL_AGE", "WHEELBARROW"), "BARRACKS": ("MILITIA", "SPEARMAN"),   # the units and technologies of each
          "ARCHERY_RANGE": ("ARCHER", "SKIRMISHER"),                                         # building (#654, #670, #655)
          "BLACKSMITH": ("FORGING", "SCALE_MAIL_ARMOR", "FLETCHING"),           # (#675, #725, #724)
          "CASTLE": (),                                                         # the unique unit: trains() (#708)
          "STABLE": ("SCOUT_CAVALRY",),                                         # (#671)
          "LUMBER_CAMP": ("DOUBLE_BIT_AXE",),                                   # (#723)
          "MILL": ("HORSE_COLLAR",),                                            # (#726)
          "MINING_CAMP": ("GOLD_MINING",)}                                      # (#727)
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
TECHS = {"DOUBLE_BIT_AXE": lambda name, s: s,                      # an economy technology: gather.WORK_TECHS
         "FLETCHING": lambda name, s: s._replace(attack=s.attack + 1, range=s.range + 1) if "archer" in s.classes else s,
         "FORGING": lambda name, s: s._replace(attack=s.attack + 1) if melee(s) else s,
         "GOLD_MINING": lambda name, s: s,                         # an economy technology: gather.WORK_TECHS
         "HORSE_COLLAR": lambda name, s: s,                        # an economy technology: gather.FARM_TECHS
         "LOOM": lambda name, s: s._replace(hp=s.hp + 15, melee=s.melee + 1, pierce=s.pierce + 2)
         if "VILLAGER" in name else s,
         "SCALE_MAIL_ARMOR": lambda name, s: s._replace(melee=s.melee + 1, pierce=s.pierce + 1)
         if "infantry" in s.classes else s,
         "FEUDAL_AGE": lambda name, s: s,   # the change of each technology to the AoE2 values
         "WHEELBARROW": lambda name, s: s}                         # no combat change: gather.CARRY and gather.PACE
REQUIRES = {"FEUDAL_AGE": (2, ("BARRACKS", "MILL", "LUMBER_CAMP", "MINING_CAMP", "DOCK"))}   # n types of these buildings
TECH_AGE = {                                                       # the age of a technology (build.AGE): hidden before
    "DOUBLE_BIT_AXE": 1,
    "WHEELBARROW": 1,
}
AGES = ("Dark Age", "Feudal Age")                                  # the age after each researched age (index: ages)
QUEUE = 15                                                         # units in the queue of one building, as in AoE2
HOUSING = {"TOWN_CENTER": 5, "HOUSE": 5, "CASTLE": 20}             # population of a complete building, as in AoE2
LIMIT = 200                                                        # the AoE2 population limit
CENSUS = 2.0                                                       # AoE2 seconds between two counts of the live units
ITEMS = {"VILLAGER_MALE": (0, "villager_spawn_egg", "Villager"),   # menu slot, item and name of each unit (#620)
         "MILITIA": (0, "zombie_spawn_egg", "Militia"),             # the mob of units.classify
         "ARCHER": (0, "skeleton_spawn_egg", "Archer"),
         "SCOUT_CAVALRY": (0, "horse_spawn_egg", "Scout Cavalry"),
         "SKIRMISHER": (1, "drowned_spawn_egg", "Skirmisher"),
         "SPEARMAN": (1, "zombie_spawn_egg", "Spearman"),
         "BERSERK": (0, "zombie_spawn_egg", "Berserk"),
         "CATAPHRACT": (0, "horse_spawn_egg", "Cataphract"),
         "CHU_KO_NU": (0, "skeleton_spawn_egg", "Chu Ko Nu"),
         "DOUBLE_BIT_AXE": (0, "book", "Double-Bit Axe"),
         "FLETCHING": (2, "book", "Fletching"),
         "FORGING": (0, "book", "Forging"),
         "GOLD_MINING": (0, "book", "Gold Mining"),
         "HORSE_COLLAR": (0, "book", "Horse Collar"),
         "HUSKARL": (0, "zombie_spawn_egg", "Huskarl"),
         "JANISSARY": (0, "pillager_spawn_egg", "Janissary"),
         "LONGBOWMAN": (0, "skeleton_spawn_egg", "Longbowman"),
         "LOOM": (1, "book", "Loom"),                               # a book for a technology (#618)
         "MAMELUKE": (0, "camel_spawn_egg", "Mameluke"),
         "MANGUDAI": (0, "skeleton_horse_spawn_egg", "Mangudai"),
         "SAMURAI": (0, "zombie_spawn_egg", "Samurai"),
         "SCALE_MAIL_ARMOR": (1, "book", "Scale Mail Armor"),
         "TEUTONIC_KNIGHT": (0, "zombie_spawn_egg", "Teutonic Knight"),
         "THROWING_AXEMAN": (0, "drowned_spawn_egg", "Throwing Axeman"),
         "WAR_ELEPHANT": (0, "ravager_spawn_egg", "War Elephant"),
         "FEUDAL_AGE": (2, "bell", "Feudal Age"),
         "WHEELBARROW": (3, "book", "Wheelbarrow"),
         "WOAD_RAIDER": (0, "zombie_spawn_egg", "Woad Raider")}
SHIFT = 5                                                          # units of a shift click, as in AoE2
RALLY = (8, "white_banner", "Rally point", "Click, then right click the ground")   # last slot of the first row
MARK = 17.0                                                        # AoE2 seconds of the rally marker: 10 s at Normal
ROW = 9                                                            # the first slot of the queue row of the menu (#706)


def melee(s):
    """True for the combat values s of an infantry or cavalry unit (also camels and elephants): the units of the melee
    attack upgrades of the AoE2 blacksmith. Cavalry archers get the archer upgrades."""
    return bool({"infantry", "cavalry", "camel", "elephant"} & set(s.classes)) and "archer" not in s.classes


def unlocked(g, name):
    """True when the player has the age of technology name (TECH_AGE). As in AoE2, the menu shows a technology only
    from its age, but a building or unit of a later age as a gray item (build.locked)."""
    return TECH_AGE.get(name, 0) <= build.ages(g)


def homes(g):
    """{block footprint (x0, x1, z0, z1): building name} of the complete own buildings that train units (TRAINS):
    the start ones and the built ones."""
    out = {(x0, x1, z0, z1): o["name"] for o in g.data["objects"] if o["kind"] == "building" and o["name"] in TRAINS
           and o["player"] == g.player for x0, z0, x1, z1 in [o["footprint"]]}
    return out | {tuple(s["footprint"]): s["name"] for s in g.sites if s["name"] in TRAINS and s.get("done")}


def trains(g, building):
    """The units and technologies of the own building: a castle trains the unique unit of the player's civilization."""
    if building != "CASTLE":
        return TRAINS[building]
    civ = g.data.get("players", {}).get(str(g.player), {}).get("civ")
    return tuple(n for n in [UNIQUE.get(civ)] if n in COSTS)


def home(g, cell):
    """The footprint of the own training building that has the block cell (x, z) in it, or None."""
    return next((r for r in homes(g) if cell and r[0] <= cell[0] < r[1] and r[2] <= cell[1] < r[3]), None)


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
              " · ".join(f"{v} {r}" for r, v in COSTS[name].items()) + f" · {TRAIN_TIMES[name]} s · " + state(name))
             for name in trains(g, building) if name not in g.techs and unlocked(g, name) for slot, item, label in [ITEMS[name]]]
    items += [RALLY] if units_of(building) else []
    items += [garrison.UNGARRISON] if getattr(g, "garrisons", {}).get(rect) else []   # only with units inside (#808)
    q = g.queues.get(rect, [])                                         # the queue row first: the plugin sets the
    items = [(ROW + i, ITEMS[name][1], ITEMS[name][2] + (f" {int(100 * q[0]['progress'])} %" if start == 0 else ""),
              "Click: cancel 1", k) for i, (name, start, k) in enumerate(groups(q)[:ROW])] + items   # items by slot
    menu.show(g, player, build.pretty(building), items, lambda p, slot, shift: order(g, p, rect, slot, shift))


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
    q.pop(start + k - 1)
    for r, v in COSTS[name].items():
        g.stock[r] += v
        g.command(f"scoreboard players add {r.capitalize()} aoe_res {v}")
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
    name = next((n for n in trains(g, homes(g)[rect]) if ITEMS[n][0] == slot), None)
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
        ai.move(g, uuid, name, g.map.T, x + 0.5, g.map.y(x, z), z + 0.5)
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
    if name in TECHS and (name in g.techs or queued(g, name)) or not unlocked(g, name):   # a technology only once
        return None
    if need := missing(g, name):
        build.say(g, player, f"{build.pretty(name)} {need}.")
        return None
    if need := build.locked(g, name):                                  # a unit of a later age (#674)
        build.say(g, player, f"{build.pretty(name)}: {need}.")
        return None
    q = g.queues.setdefault(rect, [])
    if len(q) >= QUEUE:
        build.say(g, player, f"The queue is full ({QUEUE} units).")
        return None
    cost = COSTS[name]
    if any(g.stock[r] < v for r, v in cost.items()):
        build.say(g, player, f"Not enough resources: a {build.pretty(name).lower()} costs "
                             + ", ".join(f"{v} {r}" for r, v in cost.items()) + ".")
        return None
    for r, v in cost.items():
        g.stock[r] -= v
        g.command(f"scoreboard players remove {r.capitalize()} aoe_res {v}")
    q.append({"name": name, "progress": 0.0, "player": player})
    return rect


def queued(g, name):
    """True when a queue of the player has name in it."""
    return any(e["name"] == name for q in g.queues.values() for e in q)


def owned(g):
    """The names of the complete own buildings of the player: the start ones and the built ones."""
    return [o["name"] for o in g.data["objects"] if o["kind"] == "building" and o["player"] == g.player] + \
        [s["name"] for s in g.sites if s.get("done") and s["player"] == g.player]


def missing(g, name):
    """The text of the buildings that technology name still needs (REQUIRES), or None."""
    n, names = REQUIRES.get(name, (0, ()))
    has = sorted(set(names) & set(owned(g)))
    if len(has) < n:
        return f"needs {n} of {', '.join(build.pretty(b).lower() for b in names)} ({len(has)}/{n})"


def age(g):
    """The name of the age of the player."""
    return AGES[build.ages(g)]


def stats(g, name):
    """The combat values of AoE2 unit name with the technologies of the player (combat.stats and TECHS)."""
    import combat                                                  # combat imports gather, gather imports this module
    s = combat.stats(name)
    for t in sorted(g.techs):
        s = TECHS[t](name, s)
    return s


def research(g, entry):
    """A technology is complete: keep it in g.techs and give the live villagers and military units the new values."""
    import combat, gather                                          # gather imports this module
    g.techs.add(entry["name"])
    if (more := gather.FARM_TECHS.get(entry["name"])):             # the new and the live own farms get more food
        g.map.farm_food += more
        for t in g.map.own_farms:
            if g.map.farms.get(t, 0) > 0:
                g.map.farms[t] += more
    for uuid, name in [(u["uuid"], u["name"]) for u in g.units if "uuid" in u] + list(g.soldiers.items()):
        if stats(g, name) != combat.stats(name):
            g.command(combat.stats_command(uuid, name, stats(g, name)))
        if stats(g, name).range != combat.stats(name).range:          # Fletching (#724)
            g.command(combat.range_command(uuid, name, g.map.T, s=stats(g, name)))
    if entry["name"] in REQUIRES:                                  # an age: all players see it, as in AoE2
        g.command("title @a title " + json.dumps({"text": age(g), "color": "gold"}))
        g.command("tellraw @a " + json.dumps({"text": f"Player {g.player} advances to the {age(g)}.", "color": "gold"}))
        g.command("playsound minecraft:ui.toast.challenge_complete master @a ~ ~ ~ 1 1 1")
        return
    g.command(f"tellraw {entry['player']} " + json.dumps({"text": f"{ITEMS[entry['name']][2]} is researched.",
                                                          "color": "green"}))


def limit(g):
    """The population limit: 5 per complete own town center and house, 20 per castle, at most 200."""
    return min(LIMIT, sum(HOUSING.get(n, 0) for n in owned(g)))


def census(g):
    """Count the live villagers and military units of the player (a dead unit has no position) and show the counts."""
    g.pop, g.census = len(g.positions(list(g.villagers) + list(g.soldiers))), 0.0
    sidebar(g)


def sidebar(g):
    """Show the population and the limit as two lines of the sidebar (aoe_res) and the age in its title, only when
    they changed."""
    for name, n in (("Population", g.pop), ("Limit", limit(g))):
        if g.shown.get(name) != n:
            g.shown[name] = n
            g.command(f"scoreboard players set {name} aoe_res {n}")
    if g.shown.get("Age") != age(g):
        g.shown["Age"] = age(g)
        g.command(f'scoreboard objectives modify aoe_res displayname "Resources ({age(g)})"')


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
                              + ("build more houses." if cap < LIMIT else "no more units."))
                continue
            room -= 1
            q[0]["waits"] = False
        q[0]["progress"] += 1 if getattr(g, "aegis", False) else work / TRAIN_TIMES[q[0]["name"]]   # cheats.aegis
        if q[0]["progress"] >= 1 and q[0]["name"] in TECHS:
            research(g, q.pop(0))
        elif q[0]["progress"] >= 1 and (v := spawn(g, rect, q.pop(0)["name"])):
            out.append(v)
            g.pop += 1
    sidebar(g)
    return out


def spawn(g, rect, name):
    """Summon unit name on a free cell in front of the building rect (south side first, the middle first; the units
    take the cells one after the other) and add it to the villagers of g (a military unit: to g.soldiers, #654).
    Returns the gather.Villager, the UUID of a military unit, or None."""
    cells = g.map.front(rect, "Passengers" in (units.classify(name) or {}))
    if not cells:
        return None
    k = g.trained[rect] = g.trained.get(rect, -1) + 1
    x, z = cells[k % len(cells)]
    pos = (x + 0.5, float(g.map.y(x, z)), z + 0.5)
    o = dict(name=name, player=g.player, rotation=math.pi / 2)        # it faces south
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
    if gather.military(name):
        g.soldiers[uuid] = name
        go(g, rect, uuid, name)
        return uuid
    v = g.villagers[uuid] = gather.Villager(uuid, pos)
    g.units.append({"kind": "unit", "name": name, "player": g.player, "uuid": uuid, "tile": [x / g.map.T, z / g.map.T]})
    go(g, rect, uuid, name)
    return v
