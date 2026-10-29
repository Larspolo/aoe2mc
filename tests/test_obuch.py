"""Obuch (#1747): the castle of the Poles trains the Obuch and researches Elite Obuch in the Imperial Age, with the
values of the AoE2 DE wiki (the data). The upgrade changes the live and the new units."""
from menu_line import item
from test_train_castle import menus, setup

import buildings
from game import train

CASTLE = (12, 4)
CIV = min(set(buildings.CIV_TO_ARCH) - set(train.civs.MISSING["OBUCH"]))   # the Poles
UPGRADE = "ELITE_OBUCH_UPGRADE"


def test_the_castle_of_the_poles_trains_the_obuch():
    server, g = setup(CIV, food=1000, wood=0, gold=1000)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1]
    assert item(menu, "Obuch").startswith(f"{train.SLOTS['OBUCH']}:") and item(menu, "Obuch").endswith("queue 0/15")
    assert "Elite Obuch" not in menu                                  # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, train.SLOTS["OBUCH"]) == 1 and g.queues[rect][0]["name"] == "OBUCH"
    server, g = setup(min(train.civs.MISSING["OBUCH"]), ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Obuch" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    assert CIV not in train.civs.MISSING[UPGRADE]
    server, g = setup(CIV, food=5000, wood=0, gold=5000, ages=3)
    g.soldiers["ob"] = "OBUCH"
    g.game.entities.setdefault("ob", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    up = item(menus(server)[-1], "Elite Obuch")
    assert up.startswith(f"{train.SLOTS[UPGRADE]}:") and up.endswith(" · research")
    assert train.queue(g, "Steve", CASTLE, UPGRADE)
    train.tick(g, train.seconds(g, UPGRADE, "CASTLE"))
    assert UPGRADE in g.techs and g.soldiers["ob"] == "ELITE_OBUCH"
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1]
    unit = item(menu, "Elite Obuch")                                  # one item: the unit, no upgrade
    assert unit.startswith(f"{train.SLOTS['OBUCH']}:") and unit.endswith("queue 0/15")
    assert ":Obuch:" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_OBUCH")
    assert train.queue(g, "Steve", CASTLE, "OBUCH") is None
