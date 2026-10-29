"""Monaspa (#1755): the castle of the Georgians trains the monaspa and researches Elite Monaspa in the Imperial Age,
with the values of the AoE2 DE wiki "Monaspa" (the data). The upgrade changes the live and the new units."""
from menu_line import item
from test_train_castle import menus, setup

import buildings
from game import combat, train

CASTLE = (12, 4)
CIV = min(set(buildings.CIV_TO_ARCH) - set(train.civs.MISSING["MONASPA"]))   # the Georgians
UPGRADE = "ELITE_MONASPA_UPGRADE"


def test_the_castle_of_the_georgians_trains_the_monaspa():
    server, g = setup(CIV, food=1000, wood=0, gold=1000)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1]
    assert item(menu, "Monaspa").startswith(f"{train.SLOTS['MONASPA']}:") and item(menu, "Monaspa").endswith("queue 0/15")
    assert "Elite Monaspa" not in menu                                 # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, train.SLOTS["MONASPA"]) == 1 and g.queues[rect][0]["name"] == "MONASPA"
    server, g = setup(min(train.civs.MISSING["MONASPA"]), ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Monaspa" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    assert CIV not in train.civs.MISSING[UPGRADE]
    server, g = setup(CIV, food=5000, wood=0, gold=5000, ages=3)
    g.soldiers["ct"] = "MONASPA"
    g.game.entities.setdefault("ct", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    up = item(menus(server)[-1], "Elite Monaspa")
    assert up.startswith(f"{train.SLOTS[UPGRADE]}:") and up.endswith(" · research")
    assert train.queue(g, "Steve", CASTLE, UPGRADE)
    train.tick(g, train.seconds(g, UPGRADE, "CASTLE"))
    assert UPGRADE in g.techs and g.soldiers["ct"] == "ELITE_MONASPA"
    assert combat.stats_command("ct", "ELITE_MONASPA") in server.log
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1]
    unit = item(menu, "Elite Monaspa")                                 # one item: the unit, no upgrade
    assert unit.startswith(f"{train.SLOTS['MONASPA']}:") and unit.endswith("queue 0/15")
    assert ":Monaspa:" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_MONASPA")
    assert train.queue(g, "Steve", CASTLE, "MONASPA") is None
