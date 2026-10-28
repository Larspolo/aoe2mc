"""Mounted Crossbowman (#2012): the archery range trains the mounted crossbowman from the Castle Age (slot 23: 40 wood,
65 gold, 40 s) and researches Heavy Mounted Crossbowman in the Imperial Age (slot 24: 1000 food, 650 gold, 50 s), with
the values of the AoE2 DE wiki infoboxes "Mounted Crossbowman" and "Heavy Mounted Crossbowman". The civilizations: the
availability charts of the two pages. The upgrade turns the live units into heavy ones, and the archery range then
trains the heavy one (30 s)."""
from test_castle_upgrades import RANGE, research, setup
from test_forging import menus

import units
from game import civs, combat, train

CASTLE = ("FEUDAL_AGE", "CASTLE_AGE")
IMPERIAL = CASTLE + ("IMPERIAL_AGE",)


def archery_range(civ="POLES", ages=IMPERIAL):
    server, g = setup(ages=ages)
    g.data["players"] = {"1": {"civ": civ}}
    g.soldiers["mc"] = "MOUNTED_CROSSBOWMAN"
    g.game.entities.setdefault("mc", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    return server, g


def test_the_values_are_those_of_aoe2():
    for unit in ("MOUNTED_CROSSBOWMAN", "HEAVY_MOUNTED_CROSSBOWMAN"):
        assert len(train.HELP[unit]) <= 50
        e = units.classify(unit)
        assert e["id"] == "minecraft:skeleton_horse"
        assert e["Passengers"][0]["equipment"]["mainhand"]["id"] == "minecraft:crossbow"
    assert len(train.HELP["HEAVY_MOUNTED_CROSSBOWMAN_UPGRADE"]) <= 50
    assert len(civs.MISSING["MOUNTED_CROSSBOWMAN"]) == len(civs.ROWS) - 15
    assert len(civs.MISSING["HEAVY_MOUNTED_CROSSBOWMAN_UPGRADE"]) == len(civs.ROWS) - 10
    assert {"MONGOLS", "CHINESE", "AZTECS"} <= set(civs.MISSING["MOUNTED_CROSSBOWMAN"])
    assert {"VIKINGS", "BOHEMIANS"} <= set(civs.MISSING["HEAVY_MOUNTED_CROSSBOWMAN_UPGRADE"])   # the unit, no upgrade


def test_the_menu_has_the_unit_from_the_castle_age_for_a_civ_with_it():
    server, g = archery_range(ages=("FEUDAL_AGE",))
    train.open_menu(g, "Steve", RANGE)
    assert ":gray_dye:Mounted Crossbowman:40 wood · 65 gold · 40 s · Needs the Castle Age" in menus(server)[-1]
    server, g = archery_range(ages=CASTLE)
    train.open_menu(g, "Steve", RANGE)
    menu = menus(server)[-1] + " "
    assert " 23:skeleton_horse_spawn_egg:Mounted Crossbowman:40 wood · 65 gold · 40 s · queue 0/15 " in menu
    assert "Heavy Mounted Crossbowman" not in menu                     # the upgrade: the Imperial Age
    server, g = archery_range("BRITONS", CASTLE)
    train.open_menu(g, "Steve", RANGE)
    assert ":Mounted Crossbowman:" in menus(server)[-1]
    server, g = archery_range("MONGOLS", CASTLE)
    train.open_menu(g, "Steve", RANGE)
    assert "Mounted Crossbowman" not in menus(server)[-1]
    assert train.queue(g, "Steve", RANGE, "MOUNTED_CROSSBOWMAN") is None
    server, g = archery_range("VIKINGS")                               # the unit but not the upgrade
    train.open_menu(g, "Steve", RANGE)
    assert ":Mounted Crossbowman:" in menus(server)[-1] and "Heavy Mounted Crossbowman" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = archery_range()
    train.open_menu(g, "Steve", RANGE)
    assert " 24:book:Heavy Mounted Crossbowman:1000 food · 650 gold · 50 s · research " in menus(server)[-1] + " "
    research(g, RANGE, "HEAVY_MOUNTED_CROSSBOWMAN_UPGRADE")
    assert g.soldiers["mc"] == "HEAVY_MOUNTED_CROSSBOWMAN"
    assert combat.stats_command("mc", "HEAVY_MOUNTED_CROSSBOWMAN") in server.log
    train.open_menu(g, "Steve", RANGE)
    menu = menus(server)[-1] + " "
    assert " 23:skeleton_horse_spawn_egg:Heavy Mounted Crossbowman:40 wood · 65 gold · 30 s · queue 0/15 " in menu
    assert ":Mounted Crossbowman:" not in menu and "24:book" not in menu
    assert train.queue(g, "Steve", RANGE, "HEAVY_MOUNTED_CROSSBOWMAN")
    assert train.queue(g, "Steve", RANGE, "MOUNTED_CROSSBOWMAN") is None
