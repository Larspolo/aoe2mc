"""game/civs.py: the technology cost discounts of the civilizations act on train.price() (AoE2 DE wiki, #1925)."""
from test_civ_costs import setup

from game import civs, train


def price(civ, name):
    return train.price(setup(civ)[1], name)


def cheaper(civ, name, *resources):
    """civ pays less than the Franks (no technology discount) for resources of name (none: all), the same for the
    others."""
    own, base = price(civ, name), price("FRANKS", name)
    assert own.keys() == base.keys(), (civ, name)
    for r in base:
        assert own[r] < base[r] if r in resources or not resources else own[r] == base[r], (civ, name, r)


def same(civ, name):
    assert price(civ, name) == price("FRANKS", name), (civ, name)


def test_danes_pay_less_gold_for_barracks_and_siege_workshop_technologies():
    cheaper("DANES", "MAN_AT_ARMS_UPGRADE", "gold")
    cheaper("DANES", "ONAGER_UPGRADE", "gold")
    same("DANES", "FLETCHING")                                           # the blacksmith: no discount


def test_italian_dock_and_university_technologies_are_cheaper():
    cheaper("ITALIANS", "GILLNETS")
    cheaper("ITALIANS", "MASONRY")
    same("ITALIANS", "FORGING")


def test_jurchen_siege_and_fortification_technologies_cost_less_wood():
    cheaper("JURCHENS", "SIEGE_ENGINEERS", "wood")
    cheaper("JURCHENS", "HEAVY_SCORPION_UPGRADE", "wood")
    cheaper("JURCHENS", "HOARDINGS", "wood")
    same("JURCHENS", "BALLISTICS")                                       # not in the list of the wiki


def test_shu_archery_unit_technologies_are_cheaper():
    cheaper("SHU", "THUMB_RING")
    cheaper("SHU", "BRACER")
    same("SHU", "ELITE_SKIRMISHER_UPGRADE")                              # not an archery unit line
    same("SHU", "FORGING")


def test_tupi_archery_range_and_barracks_technologies_cost_less_food():
    cheaper("TUPI", "THUMB_RING", "food")
    cheaper("TUPI", "SQUIRES", "food")
    same("TUPI", "FORGING")


def test_turkish_gunpowder_technologies_are_cheaper():
    cheaper("TURKS", "BOMBARD_TOWER_TECH")
    cheaper("TURKS", "ELITE_CANNON_GALLEON_UPGRADE")
    same("TURKS", "KEEP")                                                # not a gunpowder technology


def test_a_building_group_takes_only_the_technologies_of_its_menu():
    assert civs.has("BARRACKS technologies", "SQUIRES")
    assert not civs.has("BARRACKS technologies", "MILITIA")                              # a unit, not a technology
    assert not civs.has("BARRACKS technologies", "FLETCHING")
    assert not civs.has("NO_SUCH_BUILDING technologies", "SQUIRES")
