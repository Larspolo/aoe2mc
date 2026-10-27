"""
Units for aoe2mc: AoE2 units -> Minecraft mobs, boats and minecarts.

All mobs stand still (NoAI), do not despawn (PersistenceRequired) and are silent, except passive animals.
Each unit gets a name tag with its AoE2 name in the player color.
"""
import functools
import math

from nbtlib.tag import Byte, Compound, Double, Float, Int, IntArray, List, Long, Short, String

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

# Invisible markers and internal units: the game does not show them, so the converter skips them on purpose.
# (keyword, reason). place_objects, classify() and tools/coverage.py use this list.
INVISIBLE = (("MAP_REVEAL", "map revealer"), ("INVISIBLE_OBJECT", "invisible object"), ("BLOCKER", "path blocker"),
             ("HINT_OBJECT", "editor hint"), ("DUMMY_TARGET", "attack target"), ("TRICKLE", "resource trickle"),
             ("RESOURCE_ENABLER", "resource trickle"), ("AURA_QUEST_INDICATOR", "quest marker"),
             ("PLACEHOLDER", "placeholder"), ("DISABLED", "disabled unit"), ("OUTLW", "unused unit"),
             ("RFARC", "unused unit"))

FLYING = {   # flying birds -> mob; it floats FLY_HEIGHT blocks above the ground (NoGravity)
    "MACAW": ("parrot", 0), "FLAMING_BIRD": ("parrot", 0),                     # red parrot
    "FALCON": ("parrot", 4), "HAWK": ("parrot", 4), "VULTURE": ("parrot", 4),  # gray parrot
    "CONDOR": ("parrot", 4), "SEAGULLS": ("parrot", 4),
    "RAVEN": ("bat", None), "OWL": ("bat", None),
    "BUTTERFLY1": ("bee", None), "BUTTERFLY2": ("bee", None), "BUTTERFLY3": ("bee", None),   # no butterfly mob:
}                                                                       # the bee is the nearest small insect
FLY_HEIGHT = 6
MOUNT = "aoe2mc.mount"     # the tag of the vehicle and the crew of a unit: in the team, but not counted as a unit (#1045)
FLY_LOW = {"minecraft:bee": 2}  # insects fly near the flowers
JOKES = {   # joke and special units -> entity
    "TREASURE_CHEST": lambda: vehicle("chest_minecart", []),
    "TORCH_": lambda: mob("armor_stand", hands("torch"), Invisible=Byte(1), ShowArms=Byte(1)),
    "PHOTONMAN": lambda: soldier("zombie", 3, "crossbow"),      # white space suit, laser gun
    "SHARKATZOR": lambda: mob("guardian"),                     # a shark with laser eyes
    "NESSIE": lambda: mob("elder_guardian"),
}

HOGLIN = {"IsImmuneToZombification": Byte(1), "CannotBeHunted": Byte(1)}
ANGRY = {"anger_end_time": Long(2 ** 31 - 1)}   # angry look (game time of the end); attacks all players only with gamerule universalAnger


def wolf(variant):
    return {"variant": String("minecraft:" + variant), **ANGRY}


# AoE2 behavior -> a Minecraft mob of the same class (owner's rule in #43). docs/animals.md gives the source
# and the reason of each row. "military": cheat units that fight for a player; the look wins.
# The first row that matches wins.
ANIMALS = [   # (keywords, AoE2 behavior, minecraft mob, extra tags)
    (("ALFRED_THE_ALPACA",), "military", "llama", {"Variant": Int(1)}),
    (("FURIOUS_THE_MONKEY_BOY",), "military", "ocelot", {}),
    (("WAR_PENGUIN",), "military", "chicken", {}),
    (("WAR_DOG", "STORMY_DOG"), "military", "wolf", wolf("black")),
    (("POLAR_BEAR",), "aggressive", "polar_bear", ANGRY),
    (("BROWN_BEAR", "BLACK_BEAR", "CROCODILE", "CAIMAN", "KOMODO", "IRON_BOAR"), "aggressive", "hoglin", HOGLIN),
    (("SNAKE",), "aggressive", "silverfish", {}),
    (("ARCTIC_WOLF", "SNOW_LEOPARD"), "aggressive", "wolf", wolf("snowy")),
    (("ARABIAN_WOLF", "TIGER"), "aggressive", "wolf", wolf("striped")),
    (("DIRE_WOLF", "PANTHER"), "aggressive", "wolf", wolf("black")),
    (("RABID_WOLF",), "aggressive", "wolf", wolf("ashen")),
    (("LION",), "aggressive", "wolf", wolf("chestnut")),
    (("JAGUAR",), "aggressive", "wolf", wolf("spotted")),
    (("LYNX",), "aggressive", "wolf", wolf("rusty")),
    (("WOLF",), "aggressive", "wolf", wolf("pale")),
    (("WILD_BOAR", "JAVELINA", "RHINO", "TAPIR"), "defensive", "panda",
     {"MainGene": String("aggressive"), "HiddenGene": String("aggressive")}),
    (("ELEPHANT", "WALRUS"), "defensive", "polar_bear", {}),
    (("ELK",), "defensive", "llama", {"Variant": Int(2)}),
    (("SHEEP",), "passive", "sheep", {"Color": Byte(0)}),
    (("MOUFLON", "ARGALI", "IBEX"), "passive", "sheep", {"Color": Byte(12)}),
    (("GOAT",), "passive", "sheep", {"Color": Byte(8)}),
    (("COW_", "BUFFALO", "YAK"), "passive", "cow", {}),
    (("SEAL",), "passive", "turtle", {}),
    (("RED_FOX",), "passive", "fox", {"Type": String("red")}),
    (("ARCTIC_FOX",), "passive", "fox", {"Type": String("snow")}),
    (("PIG", "CAPYBARA"), "passive", "pig", {}),
    (("TURKEY", "GOOSE", "CHICKEN", "PHEASANT", "OSTRICH", "RHEA", "PENGUIN", "PEACOCK", "FLAMINGO", "STORK",
      "RED_CROWN_CRANE"), "passive", "chicken", {}),
    (("ARCTIC_HARE",), "passive", "rabbit", {"RabbitType": Int(1)}),
    (("HARE",), "passive", "rabbit", {"RabbitType": Int(0)}),
    (("MONKEY",), "passive", "ocelot", {}),
    (("DONKEY",), "passive", "donkey", {"Tame": Byte(1)}),
    (("LLAMA", "ALPACA", "GUANACO", "WILD_CAMEL", "BACTRIAN_CAMEL"), "passive", "camel", {}),
    (("DEER",), "passive", "horse", {"Variant": Int(2 | 3 << 8)}),     # chestnut, white dots
    (("GAZELLE",), "passive", "horse", {"Variant": Int(1)}),           # creamy
    (("ZEBRA",), "passive", "horse", {"Variant": Int(0 | 4 << 8)}),    # white, black dots
    (("HORSE",), "passive", "horse", {"Variant": Int(0)}),
]
ANIMAL_EXACT = {"ELEPHANT"}    # "ELEPHANT" alone; the war elephants are units


VILLAGER_JOBS = [("FARMER", "farmer"), ("FORAGER", "farmer"), ("FISHERMAN", "fisherman"), ("OYSTER", "fisherman"),
                 ("SHEPHERD", "shepherd"), ("HERDER", "shepherd"), ("HUNTER", "butcher"), ("BUILDER", "mason"),
                 ("REPAIRER", "toolsmith"), ("STONE_MINER", "mason"), ("GOLD_MINER", "toolsmith"),
                 ("LUMBERJACK", "fletcher"), ("MONASTERY", "cleric")]

# Standard infantry lines: name -> (mob, (helmet, chestplate, leggings, boots), main hand, off hand).
# Each upgrade step looks a bit stronger. A piece is a material, or (leather, RGB) for dyed leather.
# Zombies burn in the sun, so each zombie has a helmet. "mounted": the unit rides a horse.
EAGLE = 0xC89B3C    # feather yellow of the eagle warriors
LINES = {
    "MILITIA": ("zombie", ("leather", "leather", None, None), "wooden_sword", None),
    "MAN_AT_ARMS": ("zombie", ("chainmail", "chainmail", None, None), "stone_sword", "shield"),
    "LONG_SWORDSMAN": ("zombie", ("iron", "iron", "chainmail", None), "iron_sword", "shield"),
    "TWO_HANDED_SWORDSMAN": ("zombie", ("iron", "iron", "iron", "iron"), "diamond_sword", None),
    "CHAMPION": ("zombie", ("diamond", "diamond", "diamond", "diamond"), "diamond_sword", "shield"),
    "HEAVY_SWORDSMAN": ("zombie", ("iron", "chainmail", "chainmail", None), "iron_sword", "shield"),
    "EASTERN_SWORDSMAN": ("husk", (("leather", 0x8E2B2B), "iron", None, None), "iron_sword", None),
    "EAGLE_SCOUT": ("husk", (("leather", EAGLE), None, None, None), "wooden_sword", None),
    "EAGLE_WARRIOR": ("husk", (("leather", EAGLE), ("leather", EAGLE), None, None), "stone_sword", "shield"),
    "ELITE_EAGLE_WARRIOR": ("husk", ("golden", ("leather", EAGLE), ("leather", EAGLE), ("leather", EAGLE)),
                            "iron_sword", "shield"),
    "CONDOTTIERO": ("zombie", ("iron", "chainmail", "chainmail", "iron"), "iron_sword", None),
    "FLEMISH_MILITIA": ("zombie_villager", (("leather", 0x3B5E2B), None, None, None), "mace", None),
    "FLEMISH_MILITIA_MALE": ("zombie_villager", (("leather", 0x3B5E2B), None, None, None), "mace", None),
    "FLEMISH_MILITIA_FEMALE": ("zombie_villager", (("leather", 0x7A3B5E), None, None, None), "mace", None),
    "SERJEANT": ("zombie", ("iron", "chainmail", None, None), "iron_sword", "shield"),
    "SERJEANT_DONJON": ("zombie", ("iron", "chainmail", None, None), "iron_sword", "shield"),
    "ELITE_SERJEANT": ("zombie", ("iron", "iron", "chainmail", "iron"), "iron_sword", "shield"),
    "ELITE_SERJEANT_DONJON": ("zombie", ("iron", "iron", "chainmail", "iron"), "iron_sword", "shield"),
    "LEGIONARY": ("zombie", ("iron", "iron", None, None), "iron_sword", "shield"),
    "IMPERIAL_LEGIONARY": ("zombie", ("golden", "iron", "iron", "iron"), "iron_sword", "shield"),
    "IMPERIAL_CENTURION": ("zombie", ("golden", "golden", "iron", "iron"), "diamond_sword", "shield"),
    "CENTURION": ("mounted", ("golden", "iron", "iron", None), "iron_sword", None),
    "ELITE_CENTURION": ("mounted", ("golden", "golden", "iron", "iron"), "diamond_sword", None),
    "BANDIT": ("zombie", (("leather", 0x1D1D21), ("leather", 0x1D1D21), None, None), "stone_sword", None),
    "INDIAN_TRIBESMAN": ("husk", (None, None, None, None), "stone_sword", None),
    "HILL_TRIBESMAN": ("husk", (None, ("leather", 0x6B4A2B), None, None), "stone_axe", None),
    "NORSE_WARRIOR": ("zombie", ("iron", ("leather", 0x6B4A2B), None, None), "iron_axe", "shield"),
}
L, BROWN, RED, WHITE, BLACK = "leather", 0x6B4A2B, 0x9B1B1B, 0xE8E0D0, 0x1D1D21
# Unique infantry (#83). The elite version ("ELITE_" + name) gets a gold armor trim (see line_unit).
LINES.update({
    "AMAZON_WARRIOR": ("husk", ((L, 0x3F6B2A), None, (L, 0x3F6B2A), None), "stone_sword", "shield"),
    "BERSERK": ("zombie", ((L, BROWN), None, (L, BROWN), None), "iron_axe", None),
    "HUSKARL": ("zombie", ("iron", "chainmail", (L, BROWN), None), "iron_axe", "shield"),
    "JAGUAR_WARRIOR": ("husk", ((L, 0xD4A017), (L, 0xD4A017), None, None), "stone_sword", None),
    "KARAMBIT_WARRIOR": ("zombie", ((L, RED), None, None, None), "iron_sword", None, {"IsBaby": Byte(1)}),
    "KONNIK_DISMOUNTED": ("zombie", ("iron", "iron", "chainmail", None), "mace", "shield"),
    "NINJA": ("zombie", ((L, BLACK), (L, BLACK), (L, BLACK), (L, BLACK)), "iron_sword", None),
    "SAMURAI": ("zombie", ("iron", (L, RED), (L, RED), None), "iron_sword", None),
    "SHOTEL_WARRIOR": ("husk", ((L, WHITE), None, None, None), "iron_sword", "iron_sword"),
    "TEUTONIC_KNIGHT": ("zombie", ("iron", "iron", "iron", "iron"), "iron_sword", "shield"),
    "WOAD_RAIDER": ("zombie", ((L, 0x2B4A9B), None, (L, 0x2B4A9B), None), "iron_sword", None),
    "IROQUOIS_WARRIOR": ("husk", ((L, BROWN), None, (L, BROWN), None), "stone_axe", None),
    "XOLOTL_WARRIOR": ("mounted", ((L, EAGLE), (L, EAGLE), None, None), "stone_sword", None),
    "OBUCH": ("zombie", ("iron", "chainmail", "chainmail", None), "mace", None),
    "URUMI_SWORDSMAN": ("husk", (None, None, (L, WHITE), None), "golden_sword", None),
    "GHULAM": ("husk", ("iron", (L, 0x2B6B6B), None, None), "trident", "shield"),
    "QIZILBASH_WARRIOR": ("zombie", ((L, RED), "chainmail", None, None), "iron_sword", "shield"),
    "IMMORTAL_MELEE": ("zombie", ("golden", (L, 0x5B2B7A), (L, 0x5B2B7A), None), "trident", "shield"),
    "STRATEGOS": ("mounted", ("golden", "golden", None, None), "iron_sword", "shield"),
    "STRATEGOS_WITH_TAXIARCHS": ("mounted", ("golden", "golden", "iron", None), "iron_sword", "shield"),
    "SAKAN_AXEMAN": ("zombie", ((L, 0x8E5A2B), (L, 0x8E5A2B), None, None), "iron_axe", None),
    "SICKLE_WARRIOR": ("husk", (None, (L, BROWN), None, None), "iron_hoe", None),
    "LYSANDERS_RAIDER": ("zombie", ("iron", (L, RED), None, None), "iron_sword", "shield"),
    "IRON_PAGODA": ("mounted", ("iron", "iron", "iron", "iron"), "mace", None),
    "LIAO_DAO": ("zombie", ("iron", "chainmail", None, None), "iron_axe", None),
    "WHITE_FEATHER_GUARD": ("zombie", ((L, 0xF0F0F0), "iron", None, None), "iron_sword", "shield"),
    "JIAN_SWORDSMAN": ("zombie", ("iron", (L, 0x2B4A7A), None, None), "iron_sword", None),
    "JIAN_SWORDSMAN_TWO_HANDED": ("zombie", ("iron", "iron", (L, 0x2B4A7A), None), "diamond_sword", None),
    "RHOMPHAIA_WARRIOR": ("zombie", ("iron", (L, BROWN), (L, BROWN), None), "golden_sword", None),
    "SANNAHYA": ("husk", ("golden", (L, WHITE), None, None), "iron_sword", "shield"),
    "SACRED_BAND": ("zombie", ("golden", "iron", "iron", None), "trident", "shield"),
    "CHAMPI_SCOUT": ("husk", ((L, 0x9B6B1B), None, None, None), "stone_axe", None),
    "CHAMPI_WARRIOR": ("husk", ((L, 0x9B6B1B), (L, 0x9B6B1B), None, None), "mace", "shield"),
    "CHAMPI_RUNNER": ("husk", (None, (L, 0x9B6B1B), None, None), "mace", None),
    "GUECHA_WARRIOR": ("husk", ((L, 0xC03030), None, (L, 0xC03030), None), "stone_sword", None),
    "KONA": ("husk", (None, None, (L, BROWN), None), "wooden_axe", None),
    "IBIRAPEMA_WARRIOR": ("husk", ((L, 0xD4A017), None, None, None), "wooden_shovel", None),
    "TEMPLE_GUARD": ("husk", ("golden", (L, 0x2B8B5B), None, None), "stone_sword", "shield"),
    "VARANGIAN_GUARD": ("zombie", ("iron", "iron", "chainmail", "chainmail"), "iron_axe", "shield"),
    "HEARTH_TROOP": ("zombie", ("chainmail", "chainmail", "chainmail", None), "iron_sword", "shield"),
    "JARL": ("mounted", ("iron", "chainmail", "chainmail", None), "iron_axe", "shield"),
    "JOMSVIKING": ("zombie", ("iron", (L, BLACK), "chainmail", None), "diamond_axe", None),
})
LINES["HUSKARL_BARRACKS"] = LINES["HUSKARL"]
TRIM = Compound({"material": String("minecraft:gold"), "pattern": String("minecraft:sentry")})

MOUNTED_HEROES = ("RICHARD_THE_LIONHEART", "FREDERICK_BARBAROSSA", "SALADIN", "EL_CID", "CHARLEMAGNE", "GENGHIS_KHAN",
                  "ATTILA", "BLEDA", "TAMERLANE", "SUBOTAI", "BELISARIUS", "ROLAND", "LANCELOT", "GAWAIN",
                  "KING_ARTHUR", "SIEUR_", "CONSTABLE", "VYTAUTAS", "TSAR_KONSTANTIN", "JOHN_THE_FEARLESS",
                  "WILLIAM_THE_CONQUEROR", "HENRY_THE_LION", "ALEXANDER_NEVSKI", "KOTYAN", "BABUR", "ULRICH",
                  "ALEXANDER", "LU_BU", "GUAN_YU", "ZHAO_YUN", "TOKHTAMYSH", "KHAN")
RELIGIOUS_HEROES = ("POPE", "ARCHBISHOP", "IMAM", "FRIAR", "PRIEST")
RANGED_HEROES = ("ROBIN_HOOD", "ARCHER", "SHERIFF")
SIEGE_HEROES = ("BAD_NEIGHBOR", "GODS_OWN_SLING", "WARWOLF", "TREBUCHET")
# The mob in the minecart of a siege unit (owner decision on #1525, #1664): (name keys, mob, scale, extra tags). The
# first row with a key in the name wins. The scale keeps a large mob in its cart, off the units next to it. The crew
# keeps NoAI and Silent (mob()), so it does not walk, jump, shoot or attack by itself.
SIEGE_CREW = (
    (("SIEGE_RAM",), "iron_golem", 0.6, {}),                          # 1.2 × the battering ram
    (("CAPPED_RAM",), "iron_golem", 0.55, {}),                        # 1.1 ×
    (("BATTERING_RAM",), "iron_golem", 0.5, {}),
    (("MANGONEL", "ONAGER"), "breeze", 0.8, {}),
    (("SCORPION",), "piglin", 1.0, {"IsImmuneToZombification": Byte(1)}),   # else a zombified piglin in 15 s
    (("TREBUCHET",) + SIEGE_HEROES, "warden", 0.6, {}),               # packed: × TREBUCHET_PACKED
    (("BOMBARD_CANNON", "HOUFNICE"), "ghast", 0.3, {}),
    (("SIEGE_TOWER",), "sniffer", 0.5, {}),
    (("WAR_WAGON",), "horse", 0.7, {}),                               # owner: "War wagon a horse in the minecart"
)
TREBUCHET_PACKED = 0.6      # the size of the packed trebuchet crew, of the unpacked one (#1525)
# Heroes that the keyword lists above do not catch -> the base unit whose look they get (with hero armor).
# SWORD and AXE: a foot hero with a netherite sword or axe. From the hero names and the AoE2 campaigns.
HERO_BASE = {n: base for base, names in (
    ("PALADIN", "KHOSRAU THE_BLACK_PRINCE THEODORIC_THE_GOTH MORDRED VLAD_DRACULA MINAMOTO KING_BELA_IV "
                "CHARLES_MARTEL PRITHVIRAJ DUKE_D_ALENCON LORD_DE_GRAVILLE GUY_JOSSELYNE SIR_JOHN_FASTOLF "
                "REYNALD_DE_CHATILLON MASTER_OF_THE_TEMPLAR KUSHLUK KING_SANCHO KING_ALFONSO HENRY_V "
                "MUSA_IBN_NUSAYR TARIQ_IBN_ZIYAD RICHARD_DE_CLARE TRISTAN HENRY_II YEKUNO_AMLAK SU_DINGFANG "
                "MIKLOS_TOLDI ZAWISZA_THE_BLACK WANG_TONG IVAYLO CUMAN_CHIEF PRITHVI OSMAN EDWARD_LONGSHANKS "
                "GILBERT_DE_CLARE PHILIP_THE_GOOD ROBERT_GUISCARD ROGER_BOSSO BOHEMOND DAFYDD_AP_GRUFFYDD "
                "BERNARD_D_ARMAGNAC JACQUELINE_OF_HAINAUT JADWIGA JOGAILA KESTUTIS ALGIRDAS DMITRY_OF_MOSCOW "
                "MIKHAIL_OF_TVER MIHIRA_BHOJA SHAH_ISMAIL SELIM_THE_GRIM THOROS TAMAR YURY IVANE ZAKARE STEPHAN "
                "MLEH ARTAPHERNES DATIS DARIUS ISMAIL SHAH CAO_CAO LIU_BEI SUN_JIAN ZHANG_FEI SUN_CE SUN_QUAN "
                "DONG_ZHUO YUAN_SHAO CAO_CAO_CAMPAIGN LIU_BEI_CAMPAIGN SUN_JIAN_CAMPAIGN PHILIP PARMENION CLEITUS "
                "HEPHAISTION LAUTARO"),
    ("SCOUT_CAVALRY", "SCYTHIAN_SCOUT"),
    ("CONQUISTADOR", "FRANCISCO_DE_ORELLANA GONZALO_PIZARRO"),
    ("CAVALRY_ARCHER", "QUTLUGH"),
    ("BATTLE_ELEPHANT", "DAGNAJAN GIDAJAN JAYANEGARA SURYAVARMAN_I UDAYADITYAVARMAN_I JAYAVIRAVARMAN BAYINNAUNG "
                        "TABINSHWEHTI AMOGHAVARSHA RAJENDRA_CHOLA IBRAHIM_LODI PORUS"),
    ("SWORD", "AETHELFRITH SIEGFRIED KITABATAKE VASCO_DA_GAMA CUAUHTEMOC JOAN_THE_MAID "
              "WILLIAM_WALLACE FRANCESCO_SFORZA JOAN_OF_ARC LA_HIRE TOPA_YUPANQUI CUSI_YUPANQUI ADMIRAL_YI_SUN_SHIN "
              "NOBUNAGA SUNDJATA PRINCESS_YODIT YODIT ITZCOATL PACAL_II PACHACUTI HUAYNA_CAPAC SUMANGURU GAJAH_MADA "
              "RADEN_WIJAYA SUNDA_ROYAL_FIGHTER LE_LOI LE_LAI LE_TRIEN LUU_NHAN_CHU BUI_BI DINH_LE IVAYLO_DISMOUNTED "
              "LLYWELYN_AP_GRUFFYDD STOERTEBEKER JAN_ZIZKA GENERAL_ARAIYAN ZHOU_YU WHITE_TIGER_YAN LIU_BIAO "
              "ALEXANDER_DISMOUNTED NEARCHOS GALVARINO PACANCHIQUE CUNHAMBEBE TOSTIG_GODWINSON SCYTHIAN_WILD_WOMAN"),
    ("AXE", "LEIF_ERIKSON ERIK_THE_RED ALARIC_THE_GOTH ATAULF HARALD_HARDRADA HROLF_THE_GANGER NORSE_CHIEFTAIN "
            "LITTLE_JOHN THRACIAN_CHIEFTAIN HARALD ULF_OSPAKSSON HALLDOR_SNORRASON FINN_ARNASON KALF_ARNASON"),
    ("HOPLITE", "SOSSO_GUARD POLEMARCH POLEMARCH_2 POLEMARCH_3 POLEMARCH_4 POLEMARCH_3_WITH_EPHORATE "
                "POLEMARCH_4_WITH_EPHORATE POLEMARCH_3_WITH_MORAI POLEMARCH_4_WITH_MORAI ARISTAGORAS DIONYSIUS "
                "ARISTIDES MILTIADES THEMISTOCLES LEONIDAS BRASIDAS LYSANDER POLYCRITUS CLEON PERDICCAS"),
    ("ARCHER", "THE_MIDDLEBROOK ARTEMISIA GUACOLDA ARARIBOIA EINAR_PAUNCH_SHAKER"),
    ("CROSSBOWMAN", "GUGLIELMO_EMBRIACO"),
    ("JANISSARY", "MUSTAFA_PASHA"),
    ("BOMBARD_CANNON", "JEAN_DE_LORRAIN JEAN_BUREAU"),
    ("MONK", "YU_JI ZHANG_JUE ZHUGE_LIANG"),
    ("VILLAGER_MALE", "ENVOY CHAND_BARDAI"),
    ("VILLAGER_FEMALE", "SANYOGITA YOUNG_JADWIGA"),
    ("LONGSHIP", "DREKI"),
    ("PETARD", "SABOTEUR"),
    ("DIRE_WOLF", "HUNTING_WOLF ORNLU_THE_WOLF"),
    ("HORSE", "BUCEPHALUS"),
) for n in names.split()}


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


def hands(main=None, off=None):
    return {slot: item(n) for slot, n in (("mainhand", main), ("offhand", off)) if n}


def no_trades():
    """An empty trade list: a right click on the villager opens no trade menu, and the statistic
    talked_to_villager still counts the click (the selection of the game program, #988)."""
    return Compound({"Recipes": List[Compound]([])})


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


def invisible(n):
    """The reason to skip the invisible type n, or None."""
    return next((r for k, r in INVISIBLE if k in n), None)


def animal(n):
    """(AoE2 behavior, minecraft mob, extra tags) for an animal name, else None."""
    if "ELEPHANT" in n and n not in ANIMAL_EXACT or has(n, "CAMEL_", "ARCHER", "RIDER", "CAVALRY", "_WARRIOR"):
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
    """A siege unit: a minecart with a crew. The game program walks it on a carrier mob of the plugin (#836)."""
    d = classify(n)
    return bool(d) and d["id"] == "minecraft:minecart"


def classify(n, hero=False):
    """Return the entity description for unit name n, or None to skip it."""
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
        return classify(base, base not in ("DIRE_WOLF", "HORSE", "VILLAGER_MALE", "VILLAGER_FEMALE"))
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
        job = next((j for k, j in VILLAGER_JOBS if k in n), "none")
        return mob("villager", VillagerData=Compound({"profession": String("minecraft:" + job),
                                                       "type": String("minecraft:plains"), "level": Int(2)}),
                   Xp=Int(1), Offers=no_trades())
    if n == "MISSIONARY":                                     # a mounted monk (#1939)
        return mounted("horse", mob("evoker"))
    if has(n, "MONK", "MISSIONARY", "PRIEST", "MERCHANT") and "SHIP" not in n or hero and has(n, *RELIGIOUS_HEROES):
        return mob("evoker")
    if n in ("KING", "QUEEN", "KHAN") or has(n, "EMPEROR"):
        return mob("zombie", {"head": item("golden_helmet", True)})
    if has(n, "TRADE_CART", "OX_CART", "OX_WAGON", "RELIC_CART") or n == "CART":
        return mob("donkey", Tame=Byte(1), ChestedHorse=Byte(1))

    # Ships: boats with a crew that shows the ship type
    if has(n, "SHIP", "GALLEY", "GALLEON", "CARAVEL", "LONGSHIP", "LONGBOAT", "JUNK", "CANOE", "DROMON", "THIRISADAI",
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
            return boat("dark_oak", [mob("pillager", hands("crossbow")), crew])
        if has(n, "LONGSHIP", "LONGBOAT", "DRAGON_SHIP"):   # LONGBOAT: the DE name (#1257)
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
        if siege_crew(n):
            crew = siege_crew(n)
        elif n.endswith("_RAM") or "SIEGE_TOWER" in n:
            crew = soldier("zombie", "crew")
        elif has(n, "SCORPION", "WAR_WAGON", "HUSSITE", "CHARIOT", "RATHA"):
            crew = soldier("skeleton", "crew", "crossbow" if "SCORPION" in n else "bow")
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

    infantry_exceptions = ("TEUTONIC_KNIGHT", "DISMOUNTED", "EAGLE_SCOUT", "CHAMPI_SCOUT", "FIRE_LANCER")   # FIRE_LANCER: infantry (#1953)
    # Mounted archers and javelin riders
    if not has(n, *infantry_exceptions) and has(n, "CAVALRY_ARCHER", "HORSE_ARCHER", "MANGUDAI", "KIPCHAK",
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
    if not has(n, *infantry_exceptions) and (hero and has(n, *MOUNTED_HEROES) or has(
            n, "SCOUT_CAVALRY", "KNIGHT", "CAVALIER", "PALADIN", "HUSSAR", "HUSZAR", "CAVALRY", "BOYAR",
            "CATAPHRACT", "TARKAN", "KESHIK", "LEITIS", "KONNIK", "LANCER", "COUSTILLIER", "MONASPA", "SAVAR",
            "SHRIVAMSHA", "HIPPEUS", "MOUNTED", "RIDER", "HUNNIC_HORSE")):
        weapon = "trident" if "STEPPE_LANCER" in n else sword(t)        # the lance of the steppe lancer (#1557)
        return mounted("horse", soldier("zombie", t, weapon), t, {"Variant": Int(0 if t != 4 else 2)})

    # Foot soldiers
    if hero and has(n, *RANGED_HEROES):
        return soldier("skeleton", t, "bow")
    if has(n, "SKIRMISHER", "JAVELIN", "GBETO", "CHAKRAM", "THROWING", "PELTAST", "SLINGER", "EKDROMOS"):
        return soldier("drowned", t, "trident")
    if has(n, "SPEAR", "PIKE", "HALBERD", "KAMAYUK", "HOPLITE", "PHALANGITE", "SPARABARA"):
        return soldier("zombie", t, "trident")
    if has(n, "CANNONEER", "JANISSARY", "GRENADIER", "ARQUEBUS", "FIRE_LANCER"):
        return mob("pillager", hands("crossbow"))
    if has(n, "CROSSBOW", "ARBALEST", "CHU_KO_NU"):
        return soldier("skeleton", t, "crossbow")
    if has(n, "ARCHER", "BOWMAN", "LONGBOW", "PATTIYODHA", "IMMORTAL_RANGED"):
        return soldier("skeleton", t, "bow")
    return line_unit(n) or infantry(n, t)


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
    man = mob("zombie" if kind == "mounted" else kind, armor | hands(main, off), **(tags[0] if tags else {}))
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


def uuid_str(ints):
    """UUID int array (4 × int32, most significant first) -> the text form that commands use."""
    h = "".join(f"{int(v) & 0xFFFFFFFF:08x}" for v in ints)
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


def top_entity(nbt):
    while "Passengers" in nbt and len(nbt["Passengers"]):
        nbt = nbt["Passengers"][0]
    return nbt


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
    if o["player"]:                # the datapack puts the tagged units in the player team (#358); area triggers (#681)
        label["Tags"] = List[String]([String(f"aoe2mc.p{o['player']}")] +
                                     [String(f"aoe2mc.t{o.get('id')}")] * ("id" in o))
        stack = [nbt]              # the horse, boat or crew of the unit: the same team, but no unit of its own (#1045)
        while stack:
            e = stack.pop()
            stack += list(e.get("Passengers", []))
            if e is not label:
                e["Tags"] = List[String]([String(f"aoe2mc.p{o['player']}"), String(MOUNT)])
    return nbt


def is_bird(n):
    return n in FLYING or n in ("PEACOCK", "FLAMINGO", "STORK", "RED_CROWN_CRANE")


def is_boat(desc):
    return desc is not None and str(desc["id"]).endswith(("_boat", "_raft"))
