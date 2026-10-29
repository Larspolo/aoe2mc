"""
Units for aoe2mc: AoE2 units -> Minecraft mobs, boats and minecarts.

All mobs stand still (NoAI), do not despawn (PersistenceRequired) and are silent, except passive animals.
Each unit gets a name tag with its AoE2 name in the player color.
"""
import functools
import json
import math
import os

import nbtlib
from nbtlib.tag import Byte, Compound, Double, Float, Int, IntArray, List, Short, String

# AoE2 DE player colors
# AoE2 player color -> the nearest of the 16 chat colors of a team (`team modify ... color`)
TEAM_COLOR = {"blue": "blue", "red": "red", "green": "dark_green", "yellow": "yellow", "cyan": "aqua",
              "purple": "dark_purple", "gray": "gray", "orange": "gold", "light_gray": "white"}
HEX = {"blue": "#2D2DF5", "red": "#E0281E", "green": "#00B400", "yellow": "#F0F000", "cyan": "#00E0E0",
       "purple": "#A000F0", "gray": "#909090", "orange": "#FF8C00", "light_gray": "#FFFFFF"}
# Minecraft dye index of each dye name: the wool `Color` of a sheep (#1790).
DYES = ["white", "orange", "magenta", "light_blue", "yellow", "lime", "pink", "gray",
        "light_gray", "cyan", "purple", "blue", "brown", "green", "red", "black"]


def dye(p, players):
    """Dye index of the color of player p (0 white for Gaia and unknown colors)."""
    name = players.get(p, {}).get("color") if p else None
    return DYES.index(name) if name in DYES else 0

ARMOR = {   # tier -> (helmet, chestplate, leggings, boots material); None = empty
    1: ("leather", None, None, None),
    2: ("chainmail", "chainmail", None, None),
    3: ("iron", "iron", "iron", None),
    4: ("diamond", "diamond", "diamond", "diamond"),
    "unique": ("golden", "golden", "golden", "golden"),
    "elite": ("netherite", "netherite", "netherite", "netherite"),
    "hero": ("golden", "diamond", "diamond", "diamond"),
    "crew": ("chainmail", None, None, None),
}
SWORD = {1: "wooden", 2: "stone", 3: "iron", 4: "diamond", "unique": "golden", "elite": "netherite", "hero": "netherite"}
HORSE_ARMOR = {1: "leather", 2: "leather", 3: "iron", 4: "diamond", "unique": "golden", "elite": "diamond", "hero": "golden"}

FLY_HEIGHT = 6
MOUNT = "aoe2mc.mount"     # the tag of the vehicle and the crew of a unit: in the team, but not counted as a unit (#1045)
MOUNTS = ("minecraft:camel", "minecraft:horse", "minecraft:ravager", "minecraft:skeleton_horse")  # mounted(): they keep the hit points of the rider (#2976)
FLY_LOW = {"minecraft:bee": 2}  # insects fly near the flowers
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def rows(name):
    """The rows of data/NAME: one JSON object per line, in file order (#1917). A new entry is one new line, so
    parallel tickets do not conflict (`merge=union` in .gitattributes). "tags": entity NBT as SNBT."""
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return [json.loads(s) for s in f if s.strip()]


def tags(row):
    return dict(nbtlib.parse_nbt(row["tags"])) if row.get("tags") else {}


# AoE2 behavior -> a Minecraft mob of the same class (owner's rule in #43). docs/animals.md gives the source
# and the reason of each row. "military": cheat units that fight for a player; the look wins.
# The first row that matches wins. The hoglins cannot turn into zoglins or be hunted. "anger_end_time" 2147483647L:
# an angry look (game time of the end); the mob attacks all players only with gamerule universalAnger.
ANIMALS = [(tuple(r["keys"]), r["behavior"], r["mob"], tags(r)) for r in rows("animals.jsonl")]
ANIMAL_EXACT = {"ELEPHANT"}    # "ELEPHANT" alone; the war elephants are units


VILLAGER_JOBS = [("FARMER", "farmer"), ("FORAGER", "farmer"), ("FISHERMAN", "fisherman"), ("OYSTER", "fisherman"),
                 ("SHEPHERD", "shepherd"), ("HERDER", "shepherd"), ("HUNTER", "butcher"), ("BUILDER", "mason"),
                 ("REPAIRER", "toolsmith"), ("STONE_MINER", "mason"), ("GOLD_MINER", "toolsmith"),
                 ("LUMBERJACK", "fletcher"), ("MONASTERY", "cleric")]
# The look of a villager with no task: a nitwit never takes a job site. A villager with no profession and a job site
# in reach ran the vanilla YieldJobSite each tick, a path search to each villager near it: 65 % of the server tick of
# the live replay of de-63.0 after 20 minutes, a tick of 60 to 90 ms (#2761).
IDLE_JOB = "nitwit"

# Infantry lines and unique infantry (#83): name -> (mob, (helmet, chestplate, leggings, boots), main hand, off hand
# [, NBT]), one line each in data/lines.jsonl. Each upgrade step looks a bit stronger. A piece is a material, or
# (leather, RGB) for dyed leather. Zombies burn in the sun, so each zombie has a helmet. "mounted": the unit rides a
# horse. The elite version ("ELITE_" + name) gets a gold armor trim (see line_unit).
LINES = {r["name"]: (r["mob"], tuple(tuple(p[:1]) + (int(p[1][1:], 16),) if isinstance(p, list) else p for p in r["armor"]),
                     r["main"], r["off"], *([tags(r)] if "tags" in r else [])) for r in rows("lines.jsonl")}
TRIM = Compound({"material": String("minecraft:gold"), "pattern": String("minecraft:sentry")})

# --resource-pack (#2744): a hand item gets the AoE2 weapon model aoe2mc:<weapon> (the component minecraft:item_model);
# its id stays, as the mob fights with it (a bow shoots). A line of data/weapons.jsonl names a part of the unit name
# (upper case, the main hand only) or a vanilla item (lower case: the item or its last word); the first match wins.
# ASSETS (below) switches it on.
WEAPONS = [(r["name"], r["weapon"]) for r in rows("weapons.jsonl")]

# The own armor look of a unit in the resource pack (#2742): one line each in data/looks.jsonl ("pattern", "accent",
# "crest"). With ASSETS (--resource-pack, or a game on a world with the pack) each armor piece of the unit has the
# equipment asset aoe2mc:<name> (its textures: aoe2mc.write_resourcepack); ELITE_X wears the asset of X.
LOOKS = {r["name"]: r for r in rows("looks.jsonl")}
ASSETS = False
WORN = ("head", "chest", "legs", "feet")
DEFAULT_LOOK = {"chainmail": "mail", "golden": "scale", "iron": "mail", "leather": "quilted"}   # material -> pattern (#2743)

# The names of data/units.jsonl (#2035), one line each; the keys of a line:
# "tier": the upgrade step of a standard unit line (other units are "unique", "elite" or "hero").
# "invisible": the reason to skip an invisible marker or internal unit (a keyword; place_objects, classify() and
#   tools/coverage.py use it). "joke": a joke or special unit (a keyword) -> a maker of JOKE_MAKERS.
# "flying": [mob, parrot variant] of a flying bird; it floats FLY_HEIGHT blocks above the ground (NoGravity). No
#   butterfly mob: the bee is the nearest small insect. "bird": a bird that walks.
# "hero": the kind of a hero keyword (mounted, religious, ranged, siege). "base": a hero that the keywords do not
#   catch -> the base unit whose look it gets (with hero armor; SWORD and AXE: a foot hero with a netherite sword or
#   axe). "plain": a base that keeps its normal look. "ruler": a king. "infantry": a keyword of foot units that the
#   mounted keywords would catch. "drop": a word that pretty() leaves out.
# "crew": [mob, scale] in the minecart of a siege unit (owner decision on #1525, #1664); the first line with a
#   "crew" whose name is in the unit name wins. The scale keeps a large mob in its cart, off the units next to it.
#   The crew keeps NoAI and Silent (mob()), so it does not walk, jump, shoot or attack by itself.
UNITS = rows("units.jsonl")
TIER = {r["name"]: r["tier"] for r in UNITS if "tier" in r}
INVISIBLE = tuple((r["name"], r["invisible"]) for r in UNITS if "invisible" in r)
FLYING = {r["name"]: tuple(r["flying"]) for r in UNITS if "flying" in r}
BIRDS = {r["name"] for r in UNITS if r.get("bird")}
HEROES = {k: tuple(r["name"] for r in UNITS if r.get("hero") == k) for k in ("mounted", "religious", "ranged", "siege")}
HERO_BASE = {r["name"]: r["base"] for r in UNITS if "base" in r}
PLAIN = {r["name"] for r in UNITS if r.get("plain")}
RULERS = {r["name"] for r in UNITS if r.get("ruler")}
INFANTRY = tuple(r["name"] for r in UNITS if r.get("infantry"))
DROP = {r["name"] for r in UNITS if r.get("drop")}
SIEGE_CREW = tuple(((r["name"],), *r["crew"], tags(r)) for r in UNITS if "crew" in r)
JOKE_MAKERS = {
    "chest_minecart": lambda: vehicle("chest_minecart", []),
    "torch": lambda: mob("armor_stand", hands("torch"), Invisible=Byte(1), ShowArms=Byte(1)),
    "space_suit": lambda: soldier("zombie", 3, "crossbow"),      # white space suit, laser gun
    "guardian": lambda: mob("guardian"),                         # a shark with laser eyes
    "elder_guardian": lambda: mob("elder_guardian"),
}
JOKES = {r["name"]: JOKE_MAKERS[r["joke"]] for r in UNITS if "joke" in r}
TREBUCHET_PACKED = 0.6      # the size of the packed trebuchet crew, of the unpacked one (#1525)


# --------------------------------------------------------------------------------------------
# Small helpers for entity data
# --------------------------------------------------------------------------------------------
def item(name, unbreakable=False):
    if not name:
        return Compound({})
    c = Compound({"id": String("minecraft:" + name), "count": Int(1)})
    if unbreakable:
        c["components"] = Compound({"minecraft:unbreakable": Compound({})})
    return c


def armor(tier):
    """Armor slots {feet, legs, chest, head} of the `equipment`. Helmets never break (they protect from the sun)."""
    return armor_items(ARMOR[tier])


def armor_items(pieces):
    """Armor slots from (helmet, chestplate, leggings, boots); a piece is a material or (leather, RGB). No empty slots."""
    out = {}
    for p, kind, slot in zip(reversed(pieces), ("boots", "leggings", "chestplate", "helmet"),
                             ("feet", "legs", "chest", "head")):
        mat, rgb = p if isinstance(p, tuple) else (p, None)
        if mat:
            it = out[slot] = item(f"{mat}_{kind}", unbreakable=kind == "helmet")
            if rgb is not None:
                it.setdefault("components", Compound({}))["minecraft:dyed_color"] = Int(rgb)
    return out


def asset(n):
    """The equipment asset name of unit n: its own name; ELITE_X of a unit X with a look wears the asset of X (#2742)."""
    return n[6:] if n not in LOOKS and n.startswith("ELITE_") and n[6:] in LOOKS else n


def wear(n, gear):
    """The armor pieces of gear get the equipment asset of unit n when ASSETS is on and n has a look (#2742)."""
    n = asset(n)
    if ASSETS and n in LOOKS:
        for slot in WORN:
            if slot in gear:
                gear[slot].setdefault("components", Compound({}))["minecraft:equippable"] = Compound({
                    "slot": String(slot), "asset_id": String("aoe2mc:" + n.lower())})
    return gear


def stack(d):
    """The mobs of description d: the mount, then its riders (Passengers)."""
    yield d
    for p in d.get("Passengers", []):
        yield from stack(p)


def worn(m):
    """The armor of mob m that the pack can dress (#2743): {slot: item} of its armor pieces, and "body" for the horse
    armor of a mount (equipment layer horse_body)."""
    return {s: p for s, p in m.get("equipment", {}).items() if s in WORN or s == "body" and str(p["id"]).endswith("_horse_armor")}


def pieces(d):
    """The armor of all mobs of description d (worn())."""
    return {s: p for m in stack(d) for s, p in worn(m).items()}


@functools.lru_cache(maxsize=None)
def dressed():
    """{name: hero} of each unit with armor that has its own asset in the pack (#2743): the AoE2 units and heroes of
    AoE2ScenarioParser and the names of data/units.jsonl."""
    from AoE2ScenarioParser.datasets.heroes import HeroInfo
    from AoE2ScenarioParser.datasets.units import UnitInfo
    names = {e.name: False for e in UnitInfo} | {r["name"]: r["name"] in HERO_BASE for r in UNITS} | {
        e.name: True for e in HeroInfo} | {n: False for n in (*LINES, *LOOKS)}
    return {n: h for n, h in sorted(names.items()) if (d := describe(n, h)) and pieces(d)}


def look(n, hero=False):
    """The look of unit n (#2743): its line of LOOKS, else the line of its hero base, else a look from the material of
    its chestplate (or helmet) with DEFAULT_LOOK."""
    a = asset(n)
    if a in LOOKS or HERO_BASE.get(n) in LOOKS:
        return LOOKS[a if a in LOOKS else HERO_BASE[n]]
    worn = pieces(describe(n, hero))
    mat = str(worn.get("chest", worn.get("head", worn.get("body")))["id"]).split(":")[1].split("_")[0]
    return {"name": n, "pattern": DEFAULT_LOOK.get(mat, "plate"), "accent": "#6B4A2B"}


def hands(main=None, off=None):
    return {slot: item(n) for slot, n in (("mainhand", main), ("offhand", off)) if n}


def weapon(item_id, unit=""):
    """The AoE2 weapon model of the hand item item_id ("iron_sword") of the unit, else None (#2744)."""
    for name, w in WEAPONS:
        if name in unit if name.isupper() else item_id == name or item_id.endswith("_" + name):
            return w
    return None


def weapon_models(nbt, unit):
    """Give the hand items of the entity, its mount and its crew the weapon models of the resource pack (#2744)."""
    stack = [nbt]
    while stack:
        e = stack.pop()
        stack += list(e.get("Passengers", []))
        for slot, it in e.get("equipment", {}).items():
            w = slot in ("mainhand", "offhand") and "id" in it and \
                weapon(str(it["id"]).removeprefix("minecraft:"), unit if slot == "mainhand" else "")
            if w:
                it.setdefault("components", Compound({}))["minecraft:item_model"] = String("aoe2mc:" + w)


def no_trades():
    """An empty trade list: a right click on the villager opens no trade menu, and the statistic
    talked_to_villager still counts the click (the selection of the game program, #988)."""
    return Compound({"Recipes": List[Compound]([])})


CART_AT, CART_SCALE = (0.0, -0.9, -1.7), (1.1, 1.0, 1.5)   # blocks from the seat of the horse, size (#2746)


def mob(kind, gear=None, **tags):
    """A mob that stands still. gear: the `equipment` slots {feet, ..., mainhand, offhand, saddle, body}."""
    d = {"id": String("minecraft:" + kind), "NoAI": Byte(1), "PersistenceRequired": Byte(1), "Silent": Byte(1)}
    d.update(tags)
    if gear:
        d["equipment"] = Compound(gear)
    return d


def soldier(kind, tier, weapon=None):
    return mob(kind, armor(tier) | hands(weapon))


def sword(tier):
    return f"{SWORD.get(tier, 'iron')}_sword"


def mounted(mount, rider, tier=None, mount_tags=None):
    gear = {"saddle": item("saddle")} if mount in ("horse", "skeleton_horse", "zombie_horse", "camel", "donkey") else {}
    if mount == "horse" and tier is not None:
        gear["body"] = item(f"{HORSE_ARMOR.get(tier, 'iron')}_horse_armor")
    m = mob(mount, gear, Tame=Byte(1), **(mount_tags or {}))
    if rider:
        m["Passengers"] = [rider]
    return m


def cart(model):
    """The cart that a horse pulls (#2746): an item_display of a chest that rides the horse, moved behind it and down
    to the ground. The item has the custom_model_data "aoe2mc:<model>": without a resource pack it is a vanilla chest,
    with --resource-pack the model of the pack (write_resourcepack). The plugin turns it with its horse."""
    return {"id": String("minecraft:item_display"),
            "item": Compound({"id": String("minecraft:chest"), "count": Int(1), "components": Compound({
                "minecraft:custom_model_data": Compound({"strings": List[String]([String(f"aoe2mc:{model}")])})})}),
            "transformation": Compound({"translation": List[Float]([Float(v) for v in CART_AT]),
                                        "left_rotation": List[Float]([Float(0), Float(0), Float(0), Float(1)]),
                                        "right_rotation": List[Float]([Float(0), Float(0), Float(0), Float(1)]),
                                        "scale": List[Float]([Float(v) for v in CART_SCALE])})}


def vehicle(kind, crew, **tags):
    d = {"id": String("minecraft:" + kind)}
    d.update(tags)
    if crew:
        d["Passengers"] = [c for c in crew if c]
    return d


def boat(wood, crew, chest=False):
    """Since 1.21.2 each wood is an own entity type (bamboo: a raft)."""
    return vehicle(f"{wood}_{'chest_' if chest else ''}{'raft' if wood == 'bamboo' else 'boat'}", crew)


def pretty(name, hero=False):
    """ELITE_TEUTONIC_KNIGHT -> Elite Teutonic Knight."""
    parts = name.split("_")
    # A one-letter part is a variant letter (COW_A), but a hero keeps its numeral (HENRY_V) and particles (#3059)
    parts = [p for p in parts if p not in DROP and not (len(p) == 1 and p.isalpha() and not hero)] or parts  # BARRACKS (#4145)
    if parts and parts[0] == "VILLAGER" and len(parts) > 1:
        parts = parts[1:]
    small = {"OF", "THE", "DE", "D", "AP", "VON", "IBN", "WITH", "IN", "A", "DA"}
    words = [p.lower() if p in small and i else p.capitalize() for i, p in enumerate(parts)]
    if hero:  # "d" joins the next word: d'Alencon
        joined = []
        for w in words:
            if joined and joined[-1] == "d":
                joined[-1] = "d'" + w
            else:
                joined.append(w)
        words = joined
    if name.endswith("_PACKED"):
        words = words[:-1] + ["(packed)"]
    return " ".join(words) or name


# --------------------------------------------------------------------------------------------
# Classification: AoE2 unit name -> entity description (nested dict)
# --------------------------------------------------------------------------------------------
def has(n, *keys):
    return any(k in n for k in keys)


def tier_of(n, hero):
    if hero:
        return "hero"
    if n in TIER:
        return TIER[n]
    return "elite" if n.startswith("ELITE_") else "unique"


def invisible(n):
    """The reason to skip the invisible type n, or None."""
    return next((r for k, r in INVISIBLE if k in n), None)


def animal(n):
    """(AoE2 behavior, minecraft mob, extra tags) for an animal name, else None."""
    if "ELEPHANT" in n and n not in ANIMAL_EXACT or has(n, "CAMEL_", "ARCHER", "RIDER", "CAVALRY", "_WARRIOR") or \
            n in HEROES["mounted"] or siege_scale(n) is not None:   # Richard the Lionheart, the Warwolf trebuchet (#3626)
        return None
    return next((row[1:] for row in ANIMALS if has(n, *row[0])), None)


def siege_scale(n):
    """The scale of the crew mob of siege unit n (SIEGE_CREW), or None for a crew without a row."""
    row = next((r for r in SIEGE_CREW if has(n, *r[0])), None)
    return None if row is None else row[2] * (TREBUCHET_PACKED if row[1] == "warden" and "PACKED" in n else 1)


def siege_crew(n):
    """The crew mob of siege unit n from SIEGE_CREW, with its scale attribute, or None."""
    row = next((r for r in SIEGE_CREW if has(n, *r[0])), None)
    if row is None:
        return None
    _, kind, _, extra = row
    scale = Compound({"id": String("minecraft:scale"), "base": Double(siege_scale(n))})
    return mob(kind, hands("crossbow") if kind == "piglin" else None, attributes=List[Compound]([scale]), **extra)


@functools.lru_cache(maxsize=None)
def siege(n):
    """A siege unit: a minecart with a crew. The game program walks it on a carrier mob of the plugin (#836).
    A hero siege unit of a campaign is one too (its hero flag, #3020)."""
    return any(d and d["id"] == "minecraft:minecart" for d in (classify(n), classify(n, True)))


def wagon(n):
    """A unit that a horse pulls: its cart (cart()) rides the horse. The horse shoots as a siege unit of the plugin, with
    the blast 0 of a shot that hits only the target (combat.range_command, #2746)."""
    d = classify(n)
    return bool(d) and any(p["id"] == "minecraft:item_display" for p in d.get("Passengers", []))


def classify(n, hero=False):
    """Return the entity description for unit name n, or None to skip it. With ASSETS each armor piece (pieces()) has
    the equipment asset of n (#2743)."""
    d = describe(n, hero)
    if d and ASSETS and n in dressed():
        for m in stack(d):
            for slot, p in worn(m).items():
                p.setdefault("components", Compound({}))["minecraft:equippable"] = Compound({
                    "slot": String(slot), "asset_id": String("aoe2mc:" + asset(n).lower())})
    return d


def describe(n, hero=False):
    """The entity description for unit name n with vanilla armor, or None to skip it."""
    if invisible(n):
        return None
    if n in FLYING:
        kind, variant = FLYING[n]
        return mob(kind, NoGravity=Byte(1), **({"Variant": Int(variant)} if kind == "parrot" else {"BatFlags": Byte(0)} if kind == "bat" else {}))
    joke = next((f for k, f in JOKES.items() if k in n), None)
    if joke:
        return joke()
    if hero and n in HERO_BASE:
        base = HERO_BASE[n]
        if base in ("SWORD", "AXE"):
            return soldier("zombie", "hero", sword("hero") if base == "SWORD" else "netherite_axe")
        return describe(base, base not in PLAIN)
    if n == "VMDL":                 # an old villager model
        n = "VILLAGER_MALE"
    t = tier_of(n, hero)

    # Animals (but not war animals)
    a = animal(n) if not hero else None
    if a:
        behavior, kind, extra = a
        d = mounted("camel", None) if kind == "camel" else mob(kind, **extra)
        if behavior == "passive":   # sheep and cows make their sounds (#221)
            del d["Silent"]
        return d

    # Villagers, monks, kings, traders
    if n.startswith("VILLAGER") or n.startswith("REPAIRER"):
        job = next((j for k, j in VILLAGER_JOBS if k in n), IDLE_JOB)
        return mob("villager", VillagerData=Compound({"profession": String("minecraft:" + job),
                                                       "type": String("minecraft:plains"), "level": Int(2)}),
                   Xp=Int(1), Offers=no_trades())
    if n.startswith("MISSIONARY"):                            # a mounted monk, also with a relic (#1939, #3061)
        return mounted("horse", mob("evoker"))
    if has(n, "MONK", "MISSIONARY", "PRIEST", "MERCHANT") and "SHIP" not in n or hero and has(n, *HEROES["religious"]):
        return mob("evoker")
    if n in RULERS or has(n, "EMPEROR"):
        return mob("zombie", {"head": item("golden_helmet", True)})
    if n == "MULE_CART":                                      # a drop site that moves (#2209)
        return mob("mule", Tame=Byte(1), ChestedHorse=Byte(1))
    if has(n, "TRADE_CART", "OX_CART", "OX_WAGON", "RELIC_CART") or n == "CART":
        return mob("donkey", Tame=Byte(1), ChestedHorse=Byte(1))

    # Ships: boats with a crew that shows the ship type
    if has(n, "SHIP", "GALLEY", "GALLEON", "CARAVEL", "LONGSHIP", "LONGBOAT", "JUNK", "CANOE", "DROMON", "THIRISADAI",
           "LOU_CHUAN", "LEMBOS", "MONOREME", "BIREME", "TRIREME", "LEVIATHAN", "HULK", "CARRACK", "RAFT", "COG") \
            or n in ("FISHING_BOAT", "HEAVY_TRANSPORT", "JUGGERNAUT", "LIGHT_TRANSPORT", "TRADE_BOAT"):   # Return of Rome (#3713)
        crew = soldier("skeleton", "crew", "bow")
        if has(n, "FISHING", "WHALING"):
            return boat("oak", [describe("VILLAGER_MALE_FISHERMAN")])
        if has(n, "TRANSPORT", "MERCHANT", "TRADE_COG", "TRADE_BOAT"):
            return boat("spruce" if "TRANSPORT" in n else "birch", [describe("VILLAGER_MALE")], chest=True)
        if has(n, "FIRE", "INCENDIARY"):
            return boat("mangrove", [mob("blaze")])
        if has(n, "DEMOLITION"):
            return boat("bamboo", [mob("creeper")])
        if has(n, "CANNON", "TURTLE", "CATAPULT", "ONAGER", "LEVIATHAN", "JUGGERNAUT"):
            return boat("dark_oak", [mob("pillager", hands("crossbow")), crew])
        if has(n, "LONGSHIP", "LONGBOAT", "DRAGON_SHIP"):   # LONGBOAT: the DE name (#1257)
            return boat("spruce", [soldier("zombie", "crew", "iron_axe"), crew])
        if has(n, "CANOE"):
            return boat("jungle", [crew])
        if has(n, "GALLEON", "WAR_", "ELITE_", "HEAVY_", "CARAVEL", "CARRACK", "DROMON"):
            return boat("dark_oak", [crew, soldier("skeleton", "crew", "bow")])
        return boat("oak", [crew])

    if "WAR_WAGON" in n:              # one horse pulls the cart (#2746): the horse is the unit, the cart rides it
        return mob("horse", Tame=Byte(1), Passengers=[cart("war_wagon")])
    # Siege weapons: minecarts with a crew
    if "MOUNTED_TREBUCHET" in n:      # a camel unit that carries its trebuchet (#2191): the trebuchet crew rides a camel
        return mounted("camel", siege_crew(n))
    if hero and has(n, *HEROES["siege"]) or n.endswith("_RAM") or has(n, "MANGONEL", "ONAGER", "SCORPION", "TREBUCHET",
                                             "BOMBARD_CANNON", "SIEGE_TOWER", "ORGAN_GUN", "HOUFNICE",
                                             "ROCKET_CART", "HUSSITE_WAGON", "COBRA_CAR",
                                             "FLAMETHROWER", "CHARIOT", "RATHA", "CATAPULT") \
            or n in ("BALLISTA", "HELEPOLIS", "STONE_THROWER"):                       # Return of Rome (#3713)
        if siege_crew(n):
            crew = siege_crew(n)
        elif n.endswith("_RAM") or "SIEGE_TOWER" in n:
            crew = soldier("zombie", "crew")
        elif n in ("CHARIOT", "SCYTHE_CHARIOT"):                     # the melee chariots of Antiquity Mode (#3669)
            crew = soldier("zombie", "crew", "iron_sword")
        elif has(n, "SCORPION", "HUSSITE", "CHARIOT", "RATHA") or n in ("BALLISTA", "HELEPOLIS"):
            crew = soldier("skeleton", "crew", "bow" if has(n, "HUSSITE", "CHARIOT", "RATHA") else "crossbow")
        elif has(n, "BOMBARD", "ORGAN", "HOUFNICE", "ROCKET", "COBRA"):
            crew = mob("pillager", hands("crossbow"))
        elif "FLAMETHROWER" in n:
            crew = mob("blaze")
        else:
            crew = mob("vindicator", hands("iron_axe"))
        return vehicle("minecart", [crew])
    if "PETARD" in n:
        return mob("creeper")

    # War elephants and camels
    if "ELEPHANT" in n:
        if has(n, "ARMORED", "SIEGE"):
            return mob("ravager")
        rider = soldier("skeleton", t, "bow") if has(n, "ARCHER", "BALLISTA") else soldier("zombie", t, sword(t))
        return mounted("ravager", rider)
    if has(n, "CAMEL", "MAMELUKE"):
        if "FLAMING" in n:
            return mounted("camel", mob("blaze"))
        rider = soldier("skeleton", t, "bow") if "ARCHER" in n else soldier("zombie", t, sword(t))
        return mounted("camel", rider)

    # Mounted archers and javelin riders
    if not has(n, *INFANTRY) and has(n, "CAVALRY_ARCHER", "HORSE_ARCHER", "MANGUDAI", "KIPCHAK",
                                                "MOUNTED_CROSSBOWMAN", "CONQUISTADOR", "GENITOUR", "BOLAS_RIDER",
                                                "ARAMBAI", "XIANBEI"):
        if "CONQUISTADOR" in n:
            rider = mob("pillager", hands("crossbow"))
        elif has(n, "GENITOUR", "ARAMBAI", "BOLAS"):
            rider = soldier("drowned", t, "trident")
        else:
            rider = soldier("skeleton", t, "crossbow" if "CROSSBOW" in n else "bow")
        return mounted("skeleton_horse", rider)
    # Cavalry
    if not has(n, *INFANTRY) and (hero and has(n, *HEROES["mounted"]) or n == "SCOUT" or has(
            n, "SCOUT_CAVALRY", "KNIGHT", "CAVALIER", "PALADIN", "HUSSAR", "HUSZAR", "CAVALRY", "BOYAR",
            "CATAPHRACT", "TARKAN", "KESHIK", "LEITIS", "KONNIK", "LANCER", "COUSTILLIER", "MONASPA", "SAVAR",
            "SHRIVAMSHA", "HIPPEUS", "MOUNTED", "RIDER", "HUNNIC_HORSE")):
        weapon = "trident" if "STEPPE_LANCER" in n else sword(t)        # the lance of the steppe lancer (#1557)
        return mounted("horse", soldier("zombie", t, weapon), t, {"Variant": Int(0 if t != 4 else 2)})

    # Foot soldiers
    if hero and has(n, *HEROES["ranged"]):
        return soldier("skeleton", t, "bow")
    if (line := line_unit(n)) is not None:      # a name of LINES before its name parts (HOPLITE, #2830)
        return line
    if has(n, "SKIRMISHER", "JAVELIN", "GBETO", "CHAKRAM", "THROWING", "PELTAST", "SLINGER", "EKDROMOS"):
        return soldier("drowned", t, "trident")
    if has(n, "SPEAR", "PIKE", "HALBERD", "KAMAYUK", "HOPLITE", "PHALANGITE", "SPARABARA"):
        return mob("zombie", wear(n, armor(t)) | hands("trident"))
    if has(n, "CANNONEER", "JANISSARY", "GRENADIER", "ARQUEBUS", "FIRE_LANCER"):
        return mob("pillager", hands("crossbow"))
    if has(n, "CROSSBOW", "ARBALEST", "CHU_KO_NU"):
        return soldier("skeleton", t, "crossbow")
    if has(n, "ARCHER", "BOWMAN", "LONGBOW", "PATTIYODHA", "IMMORTAL_RANGED"):
        return soldier("skeleton", t, "bow")
    return infantry(n, t)


def line_unit(n):
    """The design of an infantry line or unique unit from LINES, else None. Elite: a gold trim on the armor."""
    elite = n not in LINES and n.startswith("ELITE_") and n[6:] in LINES
    if n not in LINES and not elite:
        return None
    kind, pieces, main, off, *tags = LINES[n[6:] if elite else n]
    armor = armor_items(pieces if not elite or any(pieces) else ("golden", None, None, None))
    if elite:
        worn = next(armor[k] for k in ("chest", "head", "legs", "feet") if k in armor)     # chestplate first
        worn.setdefault("components", Compound({}))["minecraft:trim"] = TRIM
    man = mob("zombie" if kind == "mounted" else kind, wear(n, armor) | hands(main, off), **(tags[0] if tags else {}))
    return mounted("horse", man, 3, {"Variant": Int(4)}) if kind == "mounted" else man


def infantry(n, t):
    """The default foot soldier. tools/coverage.py counts the units that end here."""
    return soldier("zombie", t, "iron_axe" if has(n, "AXE", "BERSERK", "HUSKARL") else sword(t))


# --------------------------------------------------------------------------------------------
# Entity NBT
# --------------------------------------------------------------------------------------------
def to_nbt(desc, pos, yaw, rng):
    d = dict(desc)
    passengers = d.pop("Passengers", [])
    tags = {k: v for k, v in d.items()}
    u = rng.integers(-2 ** 31, 2 ** 31 - 1, 4)
    tags.update({
        "Pos": List[Double]([Double(pos[0]), Double(pos[1]), Double(pos[2])]),
        "Motion": List[Double]([Double(0), Double(0), Double(0)]),
        "Rotation": List[Float]([Float(yaw), Float(0)]),
        "UUID": IntArray([int(v) for v in u]),
        "fall_distance": Double(0), "Fire": Short(-1), "Air": Short(300), "OnGround": Byte(1),
        "Invulnerable": Byte(0), "PortalCooldown": Int(0),
    })
    if passengers:
        tags["Passengers"] = List[Compound]([to_nbt(p, pos, yaw, rng) for p in passengers])
    return Compound(tags)


SUMMON_DROP = {"Motion": [0.0, 0.0, 0.0], "fall_distance": 0.0, "Fire": -1, "Air": 300, "OnGround": 1, "Invulnerable": 0,
               "PortalCooldown": 0}   # the to_nbt tags that a summoned entity gets anyway (or soon: OnGround)


def summon_snbt(nbt):
    """The compact SNBT of entity nbt for a summon command, without the SUMMON_DROP tags of the world file: a mounted
    unit with its equipment assets (#2743) stays below the RCON limit (rcon.MAX)."""
    def strip(c):
        out = Compound({k: v for k, v in c.items() if k not in SUMMON_DROP or v != SUMMON_DROP[k]})
        if "Passengers" in out:
            out["Passengers"] = List[Compound]([strip(p) for p in out["Passengers"]])
        return out
    return strip(nbt).snbt(compact=True)


def uuid_str(ints):
    """UUID int array (4 × int32, most significant first) -> the text form that commands use."""
    h = "".join(f"{int(v) & 0xFFFFFFFF:08x}" for v in ints)
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


def top_entity(nbt):
    """The entity of the unit: the top rider; a cart display (cart()) is no unit, its horse is (#2746)."""
    while "Passengers" in nbt and len(nbt["Passengers"]) and nbt["Passengers"][0]["id"] != "minecraft:item_display":
        nbt = nbt["Passengers"][0]
    return nbt


@functools.lru_cache(maxsize=None)
def type_ids():
    """{name: AoE2 unit ID} of the units and heroes of AoE2ScenarioParser: the type tag of a unit that a trigger or
    the game program makes (#2974). A name is in one enum only; UnitInfo wins, as in aoe2mc.object_kinds."""
    from AoE2ScenarioParser.datasets.heroes import HeroInfo
    from AoE2ScenarioParser.datasets.units import UnitInfo
    return {e.name: e.ID for e in HeroInfo} | {e.name: e.ID for e in UnitInfo}


def make_entity(o, players, pos, rng, desc=None):
    """Entity NBT for AoE2 unit o at block position pos, or None. desc: the result of classify(), if known."""
    desc = desc or classify(o["name"], o.get("hero", False))
    if desc is None:
        return None
    r = o.get("rotation", 0.0)
    yaw = math.degrees(math.atan2(-math.cos(r), math.sin(r)))
    nbt = to_nbt(desc, pos, yaw, rng)
    color = HEX.get(players.get(o["player"], {}).get("color", "light_gray"), "#FFFFFF")
    label = top_entity(nbt)
    label["CustomName"] = Compound({"text": String(pretty(o["name"], o.get("hero"))), "color": String(color)})
    label["CustomNameVisible"] = Byte(1)
    if o["player"] and "Color" in label:   # an own herdable has the wool of its player, as in AoE2 (#1790)
        label["Color"] = Byte(dye(o["player"], players))
    # the reference ID of a scenario unit, also of Gaia: the triggers find one object by it (#2617)
    ref = [String(f"aoe2mc.r{o.get('ref')}")] * (o.get("ref_tag", False) and o.get("ref") is not None)
    # the player tag, also aoe2mc.p0 of Gaia (the Gaia triggers, #2916): the datapack puts the tagged units in the
    # player team (#358, not p0); area triggers (#681)
    kind = o["id"] if "id" in o else type_ids().get(o["name"])           # the ID of the scenario wins (#2974)
    label["Tags"] = List[String]([String(f"aoe2mc.p{o['player']}")] +
                                 [String(f"aoe2mc.t{kind}")] * (kind is not None) + ref)
    stack = [nbt]              # the horse, boat or crew of the unit: the same team, but no unit of its own (#1045)
    while stack:
        e = stack.pop()
        stack += list(e.get("Passengers", []))
        if e is not label:
            e["Tags"] = List[String]([String(f"aoe2mc.p{o['player']}"), String(MOUNT)])
    if ASSETS:
        weapon_models(nbt, o["name"])
    return nbt


def is_bird(n):
    return n in FLYING or n in BIRDS


def is_boat(desc):
    return desc is not None and str(desc["id"]).endswith(("_boat", "_raft"))
