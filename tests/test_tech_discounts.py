"""game/civs.py: the technology cost discounts of the civilizations act on train.price() (AoE2 DE wiki, #1925)."""
from test_civ_costs import setup

from game import civs, train


def price(civ, name):
    return train.price(setup(civ)[1], name)


def test_danes_pay_a_third_of_the_gold_of_barracks_and_siege_workshop_technologies():
    assert price("DANES", "MAN_AT_ARMS_UPGRADE") == {"food": 100, "gold": 14}             # 40 gold × 0.34
    assert price("DANES", "ONAGER_UPGRADE") == {"food": 800, "gold": 170}
    assert price("DANES", "FLETCHING") == {"food": 100, "gold": 50}                      # the blacksmith: no discount
    assert price("FRANKS", "MAN_AT_ARMS_UPGRADE") == {"food": 100, "gold": 40}


def test_italian_dock_and_university_technologies_are_25_percent_cheaper():
    assert price("ITALIANS", "GILLNETS") == {"food": 113, "wood": 150}                    # 150 × 0.75 = 112.5, half up
    assert price("ITALIANS", "MASONRY") == {"food": 113, "wood": 131}
    assert price("ITALIANS", "FORGING") == {"food": 150}


def test_jurchen_siege_and_fortification_technologies_cost_a_quarter_of_the_wood():
    assert price("JURCHENS", "SIEGE_ENGINEERS") == {"food": 500, "wood": 150}
    assert price("JURCHENS", "HEAVY_SCORPION_UPGRADE") == {"food": 800, "wood": 188}
    assert price("JURCHENS", "HOARDINGS") == {"food": 400, "wood": 100}
    assert price("JURCHENS", "BALLISTICS") == {"wood": 300, "gold": 175}                  # not in the list of the wiki


def test_shu_archery_unit_technologies_are_25_percent_cheaper():
    assert price("SHU", "THUMB_RING") == {"food": 225, "wood": 188}
    assert price("SHU", "BRACER") == {"food": 225, "gold": 150}
    assert price("SHU", "ELITE_SKIRMISHER_UPGRADE") == {"wood": 230, "gold": 130}         # not an archery unit line
    assert price("SHU", "FORGING") == {"food": 150}


def test_tupi_archery_range_and_barracks_technologies_cost_half_the_food():
    assert price("TUPI", "THUMB_RING") == {"food": 150, "wood": 250}
    assert price("TUPI", "SQUIRES") == {"food": 50}
    assert price("TUPI", "FORGING") == {"food": 150}


def test_turkish_gunpowder_technologies_are_half_the_price():
    assert price("TURKS", "BOMBARD_TOWER_TECH") == {"food": 400, "wood": 200}
    assert price("TURKS", "ELITE_CANNON_GALLEON_UPGRADE") == {"wood": 263, "gold": 250}
    assert price("TURKS", "KEEP") == {"food": 500, "wood": 350}


def test_a_building_group_takes_only_the_technologies_of_its_menu():
    assert civs.has("BARRACKS technologies", "SQUIRES")
    assert not civs.has("BARRACKS technologies", "MILITIA")                              # a unit, not a technology
    assert not civs.has("BARRACKS technologies", "FLETCHING")
    assert not civs.has("NO_SUCH_BUILDING technologies", "SQUIRES")
