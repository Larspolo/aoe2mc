"""Bolas Rider (#2135): the Mapuche archery range trains the bolas rider from the Castle Age (slot 26: 50 wood, 55 gold,
34 s) and researches Elite Bolas Rider in the Imperial Age (slot 27: 800 food, 500 gold, 45 s), with the values of the
AoE2 DE wiki infobox "Bolas Rider" (revision 1091792). The upgrade turns the live units into elite ones, and the archery
range then trains the elite one (28 s). Only the Mapuche have it."""
from test_castle_upgrades import RANGE, research, setup
from test_forging import menus

import units
from game import civs, combat, train

CASTLE = ("FEUDAL_AGE", "CASTLE_AGE")
IMPERIAL = CASTLE + ("IMPERIAL_AGE",)
UNIT = " 26:skeleton_horse_spawn_egg:Bolas Rider:50 wood · 55 gold · 34 s · queue 0/15 "


def archery_range(civ="MAPUCHE", ages=IMPERIAL):
    server, g = setup(ages=ages)
    g.data["players"] = {"1": {"civ": civ}}
    g.soldiers["br"] = "BOLAS_RIDER"
    g.game.entities.setdefault("br", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    return server, g


def test_the_values_are_those_of_the_wiki():
    for unit in ("BOLAS_RIDER", "ELITE_BOLAS_RIDER"):
        assert len(train.HELP[unit]) <= 50
        e = units.classify(unit)
        assert e["id"] == "minecraft:skeleton_horse"
    assert len(train.HELP["ELITE_BOLAS_RIDER_UPGRADE"]) <= 50


def test_only_the_mapuche_have_it():
    have = set().union(*civs.MISSING.values())
    for name in ("BOLAS_RIDER", "ELITE_BOLAS_RIDER", "ELITE_BOLAS_RIDER_UPGRADE"):
        assert have - set(civs.MISSING[name]) == {"MAPUCHE"}, name


def test_the_menu_has_the_unit_from_the_castle_age_for_the_mapuche():
    server, g = archery_range(ages=("FEUDAL_AGE",))
    train.open_menu(g, "Steve", RANGE)
    assert " 26:gray_dye:Bolas Rider:50 wood · 55 gold · 34 s · Needs the Castle Age" in menus(server)[-1]
    server, g = archery_range(ages=CASTLE)
    train.open_menu(g, "Steve", RANGE)
    menu = menus(server)[-1] + " "
    assert UNIT in menu and "Elite Bolas Rider" not in menu                  # the upgrade: the Imperial Age
    for civ in ("BRITONS", "INCAS"):
        server, g = archery_range(civ, CASTLE)
        train.open_menu(g, "Steve", RANGE)
        assert "Bolas Rider" not in menus(server)[-1], civ
        assert train.queue(g, "Steve", RANGE, "BOLAS_RIDER") is None, civ


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = archery_range()
    train.open_menu(g, "Steve", RANGE)
    assert " 27:book:Elite Bolas Rider:800 food · 500 gold · 45 s · research " in menus(server)[-1] + " "
    research(g, RANGE, "ELITE_BOLAS_RIDER_UPGRADE")
    assert g.soldiers["br"] == "ELITE_BOLAS_RIDER"
    assert combat.stats_command("br", "ELITE_BOLAS_RIDER") in server.log
    train.open_menu(g, "Steve", RANGE)
    menu = menus(server)[-1] + " "
    assert " 26:skeleton_horse_spawn_egg:Elite Bolas Rider:50 wood · 55 gold · 28 s · queue 0/15 " in menu
    assert ":Bolas Rider:" not in menu and "27:book" not in menu
    assert train.queue(g, "Steve", RANGE, "ELITE_BOLAS_RIDER")
    assert train.queue(g, "Steve", RANGE, "BOLAS_RIDER") is None
