"""game/build.py AGE and the key "age" of game/data/train.jsonl: the Castle and Imperial Age buildings, units and technologies are
locked until the age (#1082). The ages of the AoE2 DE wiki (0: Dark, 1: Feudal, 2: Castle, 3: Imperial)."""
import pytest
from test_train_castle import menus, setup

from game import civs, train

build = train.build                                                    # the module that train uses: AGE of the unique units

WIKI = {"ARCHERY_RANGE": 1, "BLACKSMITH": 1, "MARKET": 1, "STABLE": 1, "WATCH_TOWER": 1,
        "ARCHER": 1, "SCOUT_CAVALRY": 1, "SKIRMISHER": 1, "SPEARMAN": 1,
        "CASTLE": 2, "MONASTERY": 2, "SIEGE_WORKSHOP": 2, "UNIVERSITY": 2,
        "BATTERING_RAM": 2, "CAMEL_RIDER": 2, "CROSSBOWMAN": 2, "KNIGHT": 2, "LONG_SWORDSMAN": 2, "MANGONEL": 2,
        "MONK": 2, "PIKEMAN": 2, "SCORPION": 2,
        "LONGBOWMAN": 2, "MANGUDAI": 2, "WAR_ELEPHANT": 2,
        "BOMBARD_TOWER": 3, "KEEP": 3,
        "ARBALESTER": 3, "BOMBARD_CANNON": 3, "CAVALIER": 3, "CHAMPION": 3, "HALBERDIER": 3, "HUSSAR": 3,
        "PALADIN": 3, "TREBUCHET": 3, "ELITE_LONGBOWMAN": 3, "ELITE_MANGUDAI": 3}
TECHS = {"LOOM": 0, "WHEELBARROW": 1, "FORGING": 1, "FLETCHING": 1, "BLOODLINES": 1, "HORSE_COLLAR": 1,
         "DOUBLE_BIT_AXE": 1, "GOLD_MINING": 1, "STONE_MINING": 1, "SCALE_MAIL_ARMOR": 1, "SCALE_BARDING_ARMOR": 1,
         "PADDED_ARCHER_ARMOR": 1, "MAN_AT_ARMS_UPGRADE": 1}


@pytest.mark.parametrize("name", sorted(WIKI))
def test_the_age_of_each_building_and_unit_is_that_of_aoe2(name):
    assert build.AGE.get(name, 0) == WIKI[name]


@pytest.mark.parametrize("name", sorted(TECHS))
def test_the_age_of_each_technology_is_that_of_aoe2(name):
    assert train.BY_KEY["age"].get(name, 0) == TECHS[name]


def test_each_unique_unit_needs_the_castle_age_and_its_elite_the_imperial_age():
    ages = {(build.AGE_TECHS[build.AGE[n] - 1], build.AGE_TECHS[build.AGE["ELITE_" + n] - 1]) for n in train.UNIQUE.values()}
    assert ages == {("CASTLE_AGE", "IMPERIAL_AGE")}


def test_each_unit_and_technology_of_the_menus_has_an_age():
    names = {n for ns in train.TRAINS.values() for n in ns} | set(train.UNIQUE.values()) | set(build.COSTS)
    assert {n for n in names if n not in train.TECHS} - {"VILLAGER_MALE", "MILITIA", "CHAMPI_SCOUT", "HOUSE", "LUMBER_CAMP",
                                                         "MINING_CAMP", "MILL", "FOLWARK", "MULE_CART", "SETTLEMENT", "FARM", "BARRACKS", "TOWN_CENTER", "DONJON",
                                                         "PALISADE_GATE", "PALISADE_WALL", "DOCK", "FISHING_SHIP", "LEMBOS",
                                                         "TRANSPORT_SHIP"} \
        <= build.AGE.keys()
    policies = {n for r in civs.ROWS for n in r.get("policies", {}).get("effects", {})}   # the Dark Age (#2485)
    assert {n for n in names if n in train.TECHS} - {"LOOM", "FEUDAL_AGE", "FARM_RESEED", "AUTO_RESEED", *train.DOCTRINES} - policies <= train.BY_KEY["age"].keys() | build.AGE.keys()


@pytest.mark.parametrize("ages, need", [(0, "Needs the Castle Age"), (1, "Needs the Castle Age"), (2, None)])
def test_the_unique_unit_is_a_gray_item_before_the_castle_age(ages, need):
    server, g = setup(ages=ages)
    assert build.locked(g, "LONGBOWMAN") == need
    assert build.locked(g, "ELITE_LONGBOWMAN") == "Needs the Imperial Age"
    train.open_menu(g, "Steve", (12, 4))
    unique = menus(server)[0].split(" 1:")[0]                          # item 1: the trebuchet (#1351)
    assert (unique.endswith("Needs the Castle Age") and ":gray_dye:" in unique) == bool(need)


def test_a_click_on_a_locked_unique_unit_does_nothing():
    server, g = setup(ages=1)
    assert not train.queue(g, "Steve", (12, 4), "LONGBOWMAN")
    assert g.queues.get((10, 14, 2, 6), []) == [] and g.stock["wood"] == 35
