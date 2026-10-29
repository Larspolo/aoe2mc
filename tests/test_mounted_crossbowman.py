"""Mounted Crossbowman (#2012): the archery range trains the mounted crossbowman from the Castle Age and researches Heavy
Mounted Crossbowman in the Imperial Age, with the values of the AoE2 DE wiki infoboxes "Mounted Crossbowman" and "Heavy
Mounted Crossbowman" (the data). The civilizations: the availability charts of the two pages (civs.MISSING). The upgrade
turns the live units into heavy ones, and the archery range then trains the heavy one."""
from menu_line import item
from test_castle_upgrades import RANGE, research, setup
from test_forging import menus

import buildings
from game import combat, train

CASTLE = ("FEUDAL_AGE", "CASTLE_AGE")
IMPERIAL = CASTLE + ("IMPERIAL_AGE",)
UNIT, UPGRADE = "MOUNTED_CROSSBOWMAN", "HEAVY_MOUNTED_CROSSBOWMAN_UPGRADE"
NO_UNIT, NO_UPGRADE = set(train.civs.MISSING[UNIT]), set(train.civs.MISSING[UPGRADE])
BOTH = min(set(buildings.CIV_TO_ARCH) - NO_UNIT - NO_UPGRADE)          # the Poles
ONLY_UNIT = min(NO_UPGRADE - NO_UNIT)                                  # the unit but not the upgrade


def archery_range(civ=BOTH, ages=IMPERIAL):
    server, g = setup(ages=ages)
    g.data["players"] = {"1": {"civ": civ}}
    g.soldiers["mc"] = UNIT
    g.game.entities.setdefault("mc", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    return server, g


def test_the_menu_has_the_unit_from_the_castle_age_for_a_civ_with_it():
    server, g = archery_range(ages=("FEUDAL_AGE",))
    train.open_menu(g, "Steve", RANGE)
    assert item(menus(server)[-1], "Mounted Crossbowman").endswith(" · Needs the Castle Age")
    server, g = archery_range(ages=CASTLE)
    train.open_menu(g, "Steve", RANGE)
    menu = menus(server)[-1]
    assert item(menu, "Mounted Crossbowman").startswith(f"{train.SLOTS[UNIT]}:")
    assert item(menu, "Mounted Crossbowman").endswith("queue 0/15")
    assert "Heavy Mounted Crossbowman" not in menu                     # the upgrade: the Imperial Age
    server, g = archery_range(ONLY_UNIT, CASTLE)
    train.open_menu(g, "Steve", RANGE)
    assert ":Mounted Crossbowman:" in menus(server)[-1]
    server, g = archery_range(min(NO_UNIT), CASTLE)
    train.open_menu(g, "Steve", RANGE)
    assert "Mounted Crossbowman" not in menus(server)[-1]
    assert train.queue(g, "Steve", RANGE, UNIT) is None
    server, g = archery_range(ONLY_UNIT)                               # the unit but not the upgrade
    train.open_menu(g, "Steve", RANGE)
    assert ":Mounted Crossbowman:" in menus(server)[-1] and "Heavy Mounted Crossbowman" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = archery_range()
    train.open_menu(g, "Steve", RANGE)
    up = item(menus(server)[-1], "Heavy Mounted Crossbowman")
    assert up.startswith(f"{train.SLOTS[UPGRADE]}:") and up.endswith(" · research")
    research(g, RANGE, UPGRADE)
    assert g.soldiers["mc"] == "HEAVY_MOUNTED_CROSSBOWMAN"
    assert combat.stats_command("mc", "HEAVY_MOUNTED_CROSSBOWMAN") in server.log
    train.open_menu(g, "Steve", RANGE)
    menu = menus(server)[-1]
    unit = item(menu, "Heavy Mounted Crossbowman")                     # one item: the unit, no upgrade
    assert unit.startswith(f"{train.SLOTS[UNIT]}:") and unit.endswith("queue 0/15")
    assert ":Mounted Crossbowman:" not in menu
    assert train.queue(g, "Steve", RANGE, "HEAVY_MOUNTED_CROSSBOWMAN")
    assert train.queue(g, "Steve", RANGE, UNIT) is None
