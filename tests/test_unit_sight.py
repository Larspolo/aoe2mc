"""The line of sight of each unit of combat.STATS is the AoE2 DE wiki value (#1878, epic #1299).

Source: the infobox "LOS" of each unit page (MediaWiki API, `action=parse&prop=wikitext`, 2026-10-27). Rules:
- A tooltip `{{tt|A|B}}` gives its current value A.
- A unit of more ages (Militia, Spearman, Scout Cavalry, Eagle Scout, Light Cavalry) has the value of its first age.
- The infantry values have the +2 of the Feudal Age, as the infobox shows them ("+2 added automatically").
- An elite unit has the "(Elite)" value of its base page, or the value of its own page (Elite Battle Elephant,
  Elite Cannon Galleon, Elite Skirmisher, Elite Eagle Warrior, Elite Steppe Lancer). An elite unit with no own page
  and no "(Elite)" value has the base value (NO_OWN_PAGE).
- The civilization bonuses (the second "LOS" line of the infobox) are not in this table.
"""
from game import combat

WIKI = {"CATAPULT_GALLEON": 14, "DRAGON_SHIP": 6, "DROMON": 14, "LOU_CHUAN": 15, "THIRISADAI": 9,   # (#1935)
        "WAR_CHARIOT": 8,   # (#2142)
        "ALARIC_THE_GOTH": 5, "ATTILA": 5,   # (#2688)
        "CHAMPI_SCOUT": 5, "CHAMPI_RUNNER": 5, "CHAMPI_WARRIOR": 6, "ELITE_CHAMPI_WARRIOR": 6,   # (#2133)
        "ALFRED_THE_ALPACA": 6, "ARAMBAI": 7, "ARBALESTER": 7, "ARCHER": 6, "ARMORED_ELEPHANT": 6,
         "BALLISTA_ELEPHANT": 7, "BATTERING_RAM": 5, "BATTLE_ELEPHANT": 7, "BERSERK": 5, "BOMBARD_CANNON": 14,
         "BOYAR": 5, "CAMEL_ARCHER": 5, "CAMEL_RIDER": 5, "CAMEL_SCOUT": 5, "CANNON_GALLEON": 15, "CAPPED_RAM": 5, "CARRACK": 6, "CATAPHRACT": 4,
         "CAVALIER": 4, "CAVALRY_ARCHER": 5, "CENTURION": 4, "CHAKRAM_THROWER": 9, "CHAMPION": 7, "CHU_KO_NU": 6,
         "COBRA_CAR": 12, "COMPOSITE_BOWMAN": 7, "CONDOTTIERO": 8, "CONQUISTADOR": 8, "COUSTILLIER": 5,
         "CROSSBOWMAN": 7, "DEMOLITION_RAFT": 6, "DEMOLITION_SHIP": 6, "EAGLE_SCOUT": 5, "EAGLE_WARRIOR": 8, "ELEPHANT_ARCHER": 7,
         "ELITE_ARAMBAI": 7, "ELITE_BALLISTA_ELEPHANT": 7, "ELITE_BATTLE_ELEPHANT": 8, "ELITE_BERSERK": 7,
         "ELITE_BOYAR": 5, "ELITE_CAMEL_ARCHER": 5, "ELITE_CANNON_GALLEON": 17, "ELITE_CATAPHRACT": 5,
         "ELITE_CENTURION": 4, "ELITE_CHAKRAM_THROWER": 10, "ELITE_CHU_KO_NU": 6, "ELITE_COMPOSITE_BOWMAN": 7,
         "ELITE_CONQUISTADOR": 9, "ELITE_COUSTILLIER": 5, "ELITE_EAGLE_WARRIOR": 8, "ELITE_ELEPHANT_ARCHER": 7, "ELITE_GBETO": 9,
         "ELITE_FIRE_LANCER": 8,
         "ELITE_VARANGIAN_GUARD": 6,
         "ELITE_GENITOUR": 6, "ELITE_GENOESE_CROSSBOWMAN": 8, "ELITE_GHULAM": 8, "ELITE_HUSKARL": 7,
         "ELITE_HUSSITE_WAGON": 8, "ELITE_JAGUAR_WARRIOR": 7, "ELITE_JANISSARY": 10, "ELITE_KAMAYUK": 7,
         "ELITE_KARAMBIT_WARRIOR": 5, "ELITE_KESHIK": 5, "ELITE_KIPCHAK": 6, "ELITE_KONNIK": 5, "ELITE_LEITIS": 5,
         "ELITE_LONGBOWMAN": 8, "ELITE_MAGYAR_HUSZAR": 6, "ELITE_MAMELUKE": 5, "ELITE_MANGUDAI": 6, "ELITE_MONASPA": 5,
         "ELITE_OBUCH": 5, "ELITE_ORGAN_GUN": 9, "ELITE_PLUMED_ARCHER": 6, "ELITE_RATHA": 6,
         "ELITE_RATTAN_ARCHER": 6,
         "ELITE_SAMURAI": 7, "ELITE_SERJEANT": 7, "ELITE_SHOTEL_WARRIOR": 5, "ELITE_SHRIVAMSHA_RIDER": 6,
         "ELITE_SKIRMISHER": 7, "ELITE_STEPPE_LANCER": 5, "ELITE_TARKAN": 7, "ELITE_TEUTONIC_KNIGHT": 7,
         "ELITE_THROWING_AXEMAN": 8, "ELITE_URUMI_SWORDSMAN": 5, "ELITE_WAR_ELEPHANT": 8, "ELITE_WAR_WAGON": 8,
         "ELITE_WOAD_RAIDER": 7, "FAST_FIRE_SHIP": 6, "FIRE_GALLEY": 5, "FIRE_LANCER": 7, "FIRE_SHIP": 5,
         "FISHING_SHIP": 5, "FLAMING_CAMEL": 4, "FLEMISH_MILITIA": 7, "FURIOUS_THE_MONKEY_BOY": 12, "GALLEON": 9,
         "GALLEY": 7, "LEMBOS": 7, "GBETO": 8, "GENGHIS_KHAN": 4, "GENITOUR": 5, "GENOESE_CROSSBOWMAN": 8, "GHULAM": 8,
         "GRENADIER": 9, "HALBERDIER": 6, "HAND_CANNONEER": 9, "HEAVY_CAMEL_RIDER": 5, "HEAVY_CAVALRY_ARCHER": 6,
         "HEAVY_DEMOLITION_SHIP": 6, "HEAVY_ROCKET_CART": 10, "HEAVY_SCORPION": 9,
         "HEAVY_HEI_GUANG_CAVALRY": 4,   # (#1954)
         "HEAVY_MOUNTED_CROSSBOWMAN": 6, "MOUNTED_CROSSBOWMAN": 6,   # (#2012)
         "MOUNTED_TREBUCHET": 13,   # (#2191)
         "BOLAS_RIDER": 7, "ELITE_BOLAS_RIDER": 7,   # (#2135)
         "IBIRAPEMA_WARRIOR": 5, "ELITE_IBIRAPEMA_WARRIOR": 5,   # (#2158)
         "XIANBEI_RAIDER": 6,   # (#2160)
         "HEI_GUANG_CAVALRY": 4,
         "XOLOTL_WARRIOR": 4,   # (#2009)
         "CARAVEL": 9,   # (#1934)
         "ELITE_CARAVEL": 9,
         "ELITE_LONGSHIP": 9,
         "ELITE_TURTLE_SHIP": 9,
         "LONGSHIP": 8,
         "TURTLE_SHIP": 8,
         "HOUFNICE": 14, "HULK": 5, "HUSKARL": 5, "HUSSAR": 10, "HUSSITE_WAGON": 8, "IMPERIAL_CAMEL_RIDER": 5,
         "IMPERIAL_SKIRMISHER": 7, "IRON_PAGODA": 5, "JAGUAR_WARRIOR": 5, "JANISSARY": 10, "JIAN_SWORDSMAN": 4, "KAMAYUK": 6,
         "KARAMBIT_WARRIOR": 5, "KESHIK": 5, "KING": 6, "KIPCHAK": 6, "KNIGHT": 4, "KONNIK": 5, "LEGIONARY": 7,
         "LEITIS": 5, "LIGHT_CAVALRY": 8, "LONGBOWMAN": 7, "LONG_SWORDSMAN": 6, "MAGYAR_HUSZAR": 5, "MAMELUKE": 5,
         "MANGONEL": 9, "MANGUDAI": 6, "MAN_AT_ARMS": 6, "MILITIA": 4, "MISSIONARY": 9, "MONASPA": 4, "MONK": 11, "OBUCH": 5,
         "ONAGER": 10, "ORGAN_GUN": 8, "PALADIN": 5, "PETARD": 4, "PHOTONMAN": 12, "PIKEMAN": 6, "PLUMED_ARCHER": 6, "POLEMARCH": 8,
         "RATHA": 6, "RATTAN_ARCHER": 6, "ROCKET_CART": 9, "SABOTEUR": 6, "SAMURAI": 6, "SAVAR": 5, "SCORPION": 9,
         "SCOUT_CAVALRY": 4, "SERJEANT": 5, "SHARKATZOR": 11, "SHOTEL_WARRIOR": 5, "SHRIVAMSHA_RIDER": 5,
         "SIEGE_ELEPHANT": 6, "SIEGE_ONAGER": 10, "SIEGE_RAM": 5, "SIEGE_TOWER": 6, "SKIRMISHER": 6, "SLINGER": 7,
         "SPEARMAN": 4, "STEPPE_LANCER": 5, "TARKAN": 5, "TEUTONIC_KNIGHT": 5, "THROWING_AXEMAN": 7,
         "TRACTION_TREBUCHET": 18, "TRADE_CART": 7, "TRADE_COG": 6, "TRANSPORT_SHIP": 5, "TREBUCHET": 19,
         "TWO_HANDED_SWORDSMAN": 7, "URUMI_SWORDSMAN": 5,
         "VARANGIAN_GUARD": 5,
         "TEMPLE_GUARD": 5, "ELITE_TEMPLE_GUARD": 6,   # (#2157)
         "HOPLITE": 4, "ELITE_HOPLITE": 4,   # the infobox has no LOS: the default of combat.sight (#2431)
         "VILLAGER": 4, "VMDL": 4, "WAR_ELEPHANT": 7, "WAR_GALLEY": 8,
         "WAR_HULK": 5, "WAR_PENGUIN": 6, "WAR_WAGON": 7, "WHITE_FEATHER_GUARD": 4, "WINGED_HUSSAR": 10,
         "WOAD_RAIDER": 5}
NO_OWN_PAGE = ("ELITE_ARAMBAI", "ELITE_BALLISTA_ELEPHANT", "ELITE_BOYAR", "ELITE_CAMEL_ARCHER", "ELITE_CENTURION",
               "ELITE_CHU_KO_NU", "ELITE_COMPOSITE_BOWMAN", "ELITE_COUSTILLIER", "ELITE_GENOESE_CROSSBOWMAN",
               "ELITE_GHULAM", "ELITE_HUSSITE_WAGON", "ELITE_JANISSARY", "ELITE_KARAMBIT_WARRIOR", "ELITE_KESHIK",
               "ELITE_KIPCHAK", "ELITE_KONNIK", "ELITE_LEITIS", "ELITE_MAMELUKE", "ELITE_MANGUDAI", "ELITE_OBUCH",
               "ELITE_RATHA", "ELITE_RATTAN_ARCHER", "ELITE_SHOTEL_WARRIOR", "ELITE_URUMI_SWORDSMAN")


def test_each_unit_has_a_wiki_value():
    assert set(WIKI) == set(combat.STATS)       # a new unit needs its wiki "LOS" here
    assert all(n in combat.STATS for n in NO_OWN_PAGE)


def test_unit_sight_is_the_wiki_value():
    wrong = {n: (combat.sight(n), w) for n, w in WIKI.items() if combat.sight(n) != w}
    assert not wrong, wrong                     # {unit: (sight(), wiki)}


def test_elite_without_own_page_sees_as_its_base_unit():
    assert all(WIKI[n] == WIKI[n[6:]] for n in NO_OWN_PAGE)
