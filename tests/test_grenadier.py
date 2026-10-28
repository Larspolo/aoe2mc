"""Grenadier (#2159): the Jurchen archery range trains the grenadier from the Castle Age (slot 29: 55 food, 50 gold,
21 s), with the values of the AoE2 DE wiki infobox "Grenadier" (revision 1090749). Only the Jurchens have it."""
from test_castle_upgrades import RANGE, setup
from test_forging import menus

import units
from game import build, civs, train

CASTLE = ("FEUDAL_AGE", "CASTLE_AGE")
UNIT = " 29:pillager_spawn_egg:Grenadier:55 food · 50 gold · 21 s · queue 0/15 "


def archery_range(civ="JURCHENS", ages=CASTLE):
    server, g = setup(ages=ages)
    g.data["players"] = {"1": {"civ": civ}}
    return server, g


def test_the_values_are_those_of_the_wiki():
    assert build.AGE["GRENADIER"] == 2 and len(train.HELP["GRENADIER"]) <= 50
    assert units.classify("GRENADIER")["id"] == "minecraft:pillager"


def test_only_the_jurchens_have_it():
    have = set().union(*civs.MISSING.values())
    assert have - set(civs.MISSING["GRENADIER"]) == {"JURCHENS"}


def test_the_menu_has_the_unit_from_the_castle_age_for_the_jurchens():
    server, g = archery_range(ages=("FEUDAL_AGE",))
    train.open_menu(g, "Steve", RANGE)
    assert " 29:gray_dye:Grenadier:55 food · 50 gold · 21 s · Needs the Castle Age" in menus(server)[-1]
    server, g = archery_range()
    train.open_menu(g, "Steve", RANGE)
    assert UNIT in menus(server)[-1] + " "
    g.stock.update(food=55, gold=50)
    assert train.queue(g, "Steve", RANGE, "GRENADIER") and g.stock["food"] == g.stock["gold"] == 0
    for civ in ("BRITONS", "CHINESE"):
        server, g = archery_range(civ)
        train.open_menu(g, "Steve", RANGE)
        assert "Grenadier" not in menus(server)[-1], civ
        assert train.queue(g, "Steve", RANGE, "GRENADIER") is None, civ
