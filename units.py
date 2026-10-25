"""
Units for aoe2mc: AoE2 units -> Minecraft mobs, boats and minecarts.

All mobs stand still (NoAI), do not despawn (PersistenceRequired) and are silent.
Each unit gets a name tag with its AoE2 name in the player color.
"""
import json
import math

from nbtlib.tag import Byte, Compound, Double, Float, Int, IntArray, List, Short, String

# AoE2 DE player colors
HEX = {"blue": "#2D2DF5", "red": "#E0281E", "green": "#00B400", "yellow": "#F0F000", "cyan": "#00E0E0",
       "purple": "#A000F0", "gray": "#909090", "orange": "#FF8C00", "light_gray": "#FFFFFF"}

# Upgrade steps of the standard unit lines. Other units are "unique", "elite" or "hero".
TIER = {
    "MILITIA": 1, "MAN_AT_ARMS": 2, "LONG_SWORDSMAN": 3, "TWO_HANDED_SWORDSMAN": 4, "CHAMPION": 4,
    "SPEARMAN": 1, "PIKEMAN": 2, "HALBERDIER": 3,
    "ARCHER": 1, "CROSSBOWMAN": 2, "ARBALESTER": 3,
    "SKIRMISHER": 1, "ELITE_SKIRMISHER": 2, "IMPERIAL_SKIRMISHER": 3, "HAND_CANNONEER": 3,
    "SCOUT_CAVALRY": 1, "LIGHT_CAVALRY": 2, "HUSSAR": 3, "WINGED_HUSSAR": 4,
    "KNIGHT": 2, "CAVALIER": 3, "PALADIN": 4,
    "CAMEL_SCOUT": 1, "CAMEL_RIDER": 2, "HEAVY_CAMEL_RIDER": 3, "IMPERIAL_CAMEL_RIDER": 4,
    "CAVALRY_ARCHER": 2, "HEAVY_CAVALRY_ARCHER": 3,
    "EAGLE_SCOUT": 1, "EAGLE_WARRIOR": 2, "ELITE_EAGLE_WARRIOR": 3,
    "BATTLE_ELEPHANT": 2, "ELITE_BATTLE_ELEPHANT": 3, "STEPPE_LANCER": 2, "ELITE_STEPPE_LANCER": 3,
}

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

SKIP = ("INVISIBLE", "MAP_REVEALER", "HINT_OBJECT", "DUMMY_TARGET", "TRICKLE", "RESOURCE_ENABLER", "DISABLED",
        "TORCH_", "VMDL", "OUTLW", "RFARC", "BUTTERFLY", "SEAGULLS", "FALCON", "HAWK", "VULTURE", "STORK",
        "MACAW", "CONDOR", "RAVEN", "OWL", "PEACOCK", "FLAMINGO", "CRANE", "FLAMING_BIRD", "PLACEHOLDER",
        "TREASURE_CHEST", "PHOTONMAN", "SHARKATZOR", "NESSIE")

ANIMALS = [   # (keywords, minecraft mob, extra tags)
    (("POLAR_BEAR",), "polar_bear", {}),
    (("SHEEP", "MOUFLON", "ARGALI", "TIGER", "LION", "JAGUAR", "LEOPARD", "PANTHER", "LYNX", "OSTRICH", "RHEA",
      "GAZELLE", "MONKEY", "SNAKE", "PENGUIN", "HARE", "CAPYBARA"), "sheep", {"Color": Byte(0)}),
    (("RHINO", "CROCODILE", "CAIMAN", "KOMODO", "BEAR"), "hoglin",
     {"IsImmuneToZombification": Byte(1), "CannotBeHunted": Byte(1)}),
    (("COW_", "BUFFALO", "WALRUS", "TAPIR", "SEAL", "YAK"), "cow", {}),
    (("RED_FOX",), "fox", {"Type": String("red")}),
    (("ARCTIC_FOX",), "fox", {"Type": String("snow")}),
    (("WOLF", "DOG"), "wolf", {}),
    (("WILD_BOAR", "IRON_BOAR", "JAVELINA"), "hoglin", {"IsImmuneToZombification": Byte(1), "CannotBeHunted": Byte(1)}),
    (("PIG",), "pig", {}),
    (("DEER", "IBEX", "ELK", "GOAT"), "goat", {}),
    (("TURKEY", "GOOSE", "CHICKEN", "PHEASANT"), "chicken", {}),
    (("DONKEY",), "donkey", {"Tame": Byte(1)}),
    (("LLAMA", "ALPACA", "GUANACO"), "llama", {"Variant": Int(0)}),
    (("WILD_CAMEL", "BACTRIAN_CAMEL"), "camel", {}),
    (("HORSE", "ZEBRA"), "horse", {"Variant": Int(0)}),
]

VILLAGER_JOBS = [("FARMER", "farmer"), ("FORAGER", "farmer"), ("FISHERMAN", "fisherman"), ("OYSTER", "fisherman"),
                 ("SHEPHERD", "shepherd"), ("HERDER", "shepherd"), ("HUNTER", "butcher"), ("BUILDER", "mason"),
                 ("REPAIRER", "toolsmith"), ("STONE_MINER", "mason"), ("GOLD_MINER", "toolsmith"),
                 ("LUMBERJACK", "fletcher"), ("MONASTERY", "cleric")]

MOUNTED_HEROES = ("RICHARD_THE_LIONHEART", "FREDERICK_BARBAROSSA", "SALADIN", "EL_CID", "CHARLEMAGNE", "GENGHIS_KHAN",
                  "ATTILA", "BLEDA", "TAMERLANE", "SUBOTAI", "BELISARIUS", "ROLAND", "LANCELOT", "GAWAIN",
                  "KING_ARTHUR", "SIEUR_", "CONSTABLE", "VYTAUTAS", "TSAR_KONSTANTIN", "JOHN_THE_FEARLESS",
                  "WILLIAM_THE_CONQUEROR", "HENRY_THE_LION", "ALEXANDER_NEVSKI", "KOTYAN", "BABUR", "ULRICH",
                  "ALEXANDER", "LU_BU", "GUAN_YU", "ZHAO_YUN", "TOKHTAMYSH", "KHAN")
RELIGIOUS_HEROES = ("POPE", "ARCHBISHOP", "IMAM", "FRIAR", "PRIEST")
RANGED_HEROES = ("ROBIN_HOOD", "ARCHER", "SHERIFF")
SIEGE_HEROES = ("BAD_NEIGHBOR", "GODS_OWN_SLING", "WARWOLF", "TREBUCHET")


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
    """ArmorItems list: feet, legs, chest, head. Helmets never break (they protect from the sun)."""
    h, c, l, b = ARMOR[tier]
    return List[Compound]([item(b and f"{b}_boots"), item(l and f"{l}_leggings"),
                           item(c and f"{c}_chestplate"), item(f"{h}_helmet" if h else None, unbreakable=True)])


def hands(main=None, off=None):
    return List[Compound]([item(main), item(off)])


def mob(kind, **tags):
    """A mob that stands still."""
    d = {"id": String("minecraft:" + kind), "NoAI": Byte(1), "PersistenceRequired": Byte(1), "Silent": Byte(1)}
    d.update(tags)
    return d


def soldier(kind, tier, weapon=None):
    return mob(kind, ArmorItems=armor(tier), HandItems=hands(weapon))


def sword(tier):
    return f"{SWORD.get(tier, 'iron')}_sword"


def mounted(mount, rider, tier=None, mount_tags=None):
    m = mob(mount, Tame=Byte(1), **(mount_tags or {}))
    if mount in ("horse", "skeleton_horse", "zombie_horse", "camel", "donkey"):
        m["SaddleItem"] = item("saddle")
    if mount == "horse" and tier is not None:
        m["body_armor_item"] = item(f"{HORSE_ARMOR.get(tier, 'iron')}_horse_armor")
    if rider:
        m["Passengers"] = [rider]
    return m


def vehicle(kind, crew, **tags):
    d = {"id": String("minecraft:" + kind)}
    d.update(tags)
    if crew:
        d["Passengers"] = [c for c in crew if c]
    return d


def boat(wood, crew, chest=False):
    return vehicle("chest_boat" if chest else "boat", crew, Type=String(wood))


def pretty(name, hero=False):
    """ELITE_TEUTONIC_KNIGHT -> Elite Teutonic Knight."""
    parts = name.split("_")
    drop = {"EMPTY", "FULL", "MALE", "FEMALE", "BARRACKS", "STABLE", "DONJON", "KREPOST", "ORIGINAL", "ANTIQUITY"}
    parts = [p for p in parts if p not in drop and not (len(p) == 1 and p.isalpha())]
    if parts and parts[0] == "VILLAGER" and len(parts) > 1:
        parts = parts[1:]
    small = {"OF", "THE", "DE", "D", "AP", "VON", "IBN", "WITH", "IN", "A", "DA"}
    words = [p.lower() if p in small and i else p.capitalize() for i, p in enumerate(parts)]
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


def classify(n, hero=False):
    """Return the entity description for unit name n, or None to skip it."""
    if has(n, *SKIP):
        return None
    t = tier_of(n, hero)

    # Animals (but not war animals)
    if not hero and n == "ELEPHANT":
        return mob("ravager")
    if not hero and not has(n, "CAMEL_", "ARCHER", "RIDER", "CAVALRY"):
        for keys, kind, extra in ANIMALS:
            if has(n, *keys) and not has(n, "_WARRIOR", "CAVALRY"):
                if kind == "camel":
                    return mounted("camel", None)
                return mob(kind, **extra)

    # Villagers, monks, kings, traders
    if n.startswith("VILLAGER") or n.startswith("REPAIRER"):
        job = next((j for k, j in VILLAGER_JOBS if k in n), "none")
        return mob("villager", VillagerData=Compound({"profession": String("minecraft:" + job),
                                                       "type": String("minecraft:plains"), "level": Int(2)}),
                   Xp=Int(1))
    if has(n, "MONK", "MISSIONARY", "PRIEST", "MERCHANT") and "SHIP" not in n or hero and has(n, *RELIGIOUS_HEROES):
        return mob("evoker")
    if n in ("KING", "QUEEN", "KHAN") or has(n, "EMPEROR"):
        return mob("zombie", ArmorItems=List[Compound]([item(None), item(None), item(None),
                                                        item("golden_helmet", True)]), HandItems=hands())
    if has(n, "TRADE_CART", "OX_CART", "OX_WAGON", "RELIC_CART") or n == "CART":
        return mob("donkey", Tame=Byte(1), ChestedHorse=Byte(1))

    # Ships: boats with a crew that shows the ship type
    if has(n, "SHIP", "GALLEY", "GALLEON", "CARAVEL", "LONGSHIP", "JUNK", "CANOE", "DROMON", "THIRISADAI",
           "LOU_CHUAN", "LEMBOS", "MONOREME", "BIREME", "TRIREME", "LEVIATHAN", "HULK", "CARRACK", "RAFT", "COG"):
        crew = soldier("skeleton", "crew", "bow")
        if has(n, "FISHING", "WHALING"):
            return boat("oak", [classify("VILLAGER_MALE_FISHERMAN")])
        if has(n, "TRANSPORT", "MERCHANT", "TRADE_COG"):
            return boat("spruce" if "TRANSPORT" in n else "birch", [classify("VILLAGER_MALE")], chest=True)
        if has(n, "FIRE", "INCENDIARY"):
            return boat("mangrove", [mob("blaze")])
        if has(n, "DEMOLITION"):
            return boat("bamboo", [mob("creeper")])
        if has(n, "CANNON", "TURTLE", "CATAPULT", "ONAGER", "LEVIATHAN"):
            return boat("dark_oak", [mob("pillager", HandItems=hands("crossbow")), crew])
        if has(n, "LONGSHIP", "DRAGON_SHIP"):
            return boat("spruce", [soldier("zombie", "crew", "iron_axe"), crew])
        if has(n, "CANOE"):
            return boat("jungle", [crew])
        if has(n, "GALLEON", "WAR_", "ELITE_", "HEAVY_", "CARAVEL", "CARRACK", "DROMON"):
            return boat("dark_oak", [crew, soldier("skeleton", "crew", "bow")])
        return boat("oak", [crew])

    # Siege weapons: minecarts with a crew
    if hero and has(n, *SIEGE_HEROES) or n.endswith("_RAM") or has(n, "MANGONEL", "ONAGER", "SCORPION", "TREBUCHET",
                                             "BOMBARD_CANNON", "SIEGE_TOWER", "ORGAN_GUN", "HOUFNICE",
                                             "ROCKET_CART", "WAR_WAGON", "HUSSITE_WAGON", "COBRA_CAR",
                                             "FLAMETHROWER", "CHARIOT", "RATHA", "CATAPULT"):
        if n.endswith("_RAM") or "SIEGE_TOWER" in n:
            crew = soldier("zombie", "crew")
        elif has(n, "SCORPION", "WAR_WAGON", "HUSSITE", "CHARIOT", "RATHA"):
            crew = soldier("skeleton", "crew", "crossbow" if "SCORPION" in n else "bow")
        elif has(n, "BOMBARD", "ORGAN", "HOUFNICE", "ROCKET", "COBRA"):
            crew = mob("pillager", HandItems=hands("crossbow"))
        elif "FLAMETHROWER" in n:
            crew = mob("blaze")
        else:
            crew = mob("vindicator", HandItems=hands("iron_axe"))
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

    infantry_exceptions = ("TEUTONIC_KNIGHT", "DISMOUNTED", "EAGLE_SCOUT", "CHAMPI_SCOUT")
    # Mounted archers and javelin riders
    if not has(n, *infantry_exceptions) and has(n, "CAVALRY_ARCHER", "HORSE_ARCHER", "MANGUDAI", "KIPCHAK",
                                                "MOUNTED_CROSSBOWMAN", "CONQUISTADOR", "GENITOUR", "BOLAS_RIDER",
                                                "ARAMBAI", "XIANBEI"):
        if "CONQUISTADOR" in n:
            rider = mob("pillager", HandItems=hands("crossbow"))
        elif has(n, "GENITOUR", "ARAMBAI", "BOLAS"):
            rider = soldier("drowned", t, "trident")
        else:
            rider = soldier("skeleton", t, "crossbow" if "CROSSBOW" in n else "bow")
        return mounted("skeleton_horse", rider)
    # Cavalry
    if not has(n, *infantry_exceptions) and (hero and has(n, *MOUNTED_HEROES) or has(
            n, "SCOUT_CAVALRY", "KNIGHT", "CAVALIER", "PALADIN", "HUSSAR", "HUSZAR", "CAVALRY", "BOYAR",
            "CATAPHRACT", "TARKAN", "KESHIK", "LEITIS", "KONNIK", "LANCER", "COUSTILLIER", "MONASPA", "SAVAR",
            "SHRIVAMSHA", "HIPPEUS", "MOUNTED", "RIDER", "HUNNIC_HORSE")):
        return mounted("horse", soldier("zombie", t, sword(t)), t, {"Variant": Int(0 if t != 4 else 2)})

    # Foot soldiers
    if hero and has(n, *RANGED_HEROES):
        return soldier("skeleton", t, "bow")
    if has(n, "SKIRMISHER", "JAVELIN", "GBETO", "CHAKRAM", "THROWING", "PELTAST", "SLINGER", "EKDROMOS"):
        return soldier("drowned", t, "trident")
    if has(n, "SPEAR", "PIKE", "HALBERD", "KAMAYUK", "HOPLITE", "PHALANGITE", "SPARABARA"):
        return soldier("zombie", t, "trident")
    if has(n, "CANNONEER", "JANISSARY", "GRENADIER", "ARQUEBUS", "FIRE_LANCER"):
        return mob("pillager", HandItems=hands("crossbow"))
    if has(n, "CROSSBOW", "ARBALEST", "CHU_KO_NU"):
        return soldier("skeleton", t, "crossbow")
    if has(n, "ARCHER", "BOWMAN", "LONGBOW", "PATTIYODHA", "IMMORTAL_RANGED"):
        return soldier("skeleton", t, "bow")
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
        "FallDistance": Float(0), "Fire": Short(-1), "Air": Short(300), "OnGround": Byte(1),
        "Invulnerable": Byte(0), "PortalCooldown": Int(0),
    })
    if passengers:
        tags["Passengers"] = List[Compound]([to_nbt(p, pos, yaw, rng) for p in passengers])
    return Compound(tags)


def top_entity(nbt):
    while "Passengers" in nbt and len(nbt["Passengers"]):
        nbt = nbt["Passengers"][0]
    return nbt


def make_entity(o, players, pos, rng):
    """Entity NBT for AoE2 unit o at block position pos, or None."""
    desc = classify(o["name"], o.get("hero", False))
    if desc is None:
        return None
    r = o.get("rotation", 0.0)
    yaw = math.degrees(math.atan2(-math.cos(r), math.sin(r)))
    nbt = to_nbt(desc, pos, yaw, rng)
    color = HEX.get(players.get(o["player"], {}).get("color", "light_gray"), "#FFFFFF")
    label = top_entity(nbt)
    label["CustomName"] = String(json.dumps({"text": pretty(o["name"], o.get("hero")), "color": color}))
    label["CustomNameVisible"] = Byte(1)
    return nbt


def is_boat(desc):
    return desc is not None and desc["id"] in ("minecraft:boat", "minecraft:chest_boat")
