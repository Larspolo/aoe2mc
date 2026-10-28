"""Jaguar Warrior (#1884): the castle of the Aztecs trains the Jaguar Warrior (60 food, 30 gold, 12 s) and researches Elite
Jaguar Warrior in the Imperial Age (slot 5: 1000 food, 500 gold, 45 s), with the values of the AoE2 DE wiki. The upgrade
changes the live and the new units."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert len(train.HELP["JAGUAR_WARRIOR"]) <= 50 and "AZTECS" not in train.civs.MISSING["JAGUAR_WARRIOR"]
    assert "BRITONS" in train.civs.MISSING["JAGUAR_WARRIOR"]


def test_the_castle_of_the_aztecs_trains_the_jaguar_warrior():
    server, g = setup("AZTECS", food=60, wood=0, gold=30)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:husk_spawn_egg:Jaguar Warrior:60 food · 30 gold · 10.4 s · queue 0/15 " in menu   # 12 s / 1.15 (#1927)
    assert "Elite Jaguar" not in menu                                  # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, 0) == 1 and g.queues[rect][0]["name"] == "JAGUAR_WARRIOR"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Jaguar Warrior" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("AZTECS", food=2000, wood=0, gold=2000, ages=3)
    g.soldiers["jw"] = "JAGUAR_WARRIOR"
    g.game.entities.setdefault("jw", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert " 5:book:Elite Jaguar Warrior:1000 food · 500 gold · 45 s · research " in menus(server)[-1] + " "
    assert train.queue(g, "Steve", CASTLE, "ELITE_JAGUAR_WARRIOR_UPGRADE")
    train.tick(g, 45)
    assert "ELITE_JAGUAR_WARRIOR_UPGRADE" in g.techs and g.soldiers["jw"] == "ELITE_JAGUAR_WARRIOR"
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:husk_spawn_egg:Elite Jaguar Warrior:60 food · 30 gold · 10.4 s · queue 0/15 " in menu   # 12 s / 1.15 (#1927)
    assert ":Jaguar Warrior:" not in menu and "5:book" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_JAGUAR_WARRIOR")
    assert train.queue(g, "Steve", CASTLE, "JAGUAR_WARRIOR") is None
