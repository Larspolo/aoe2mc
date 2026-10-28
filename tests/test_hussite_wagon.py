"""Hussite Wagon (#1758): the castle of the Bohemians trains the Hussite Wagon (110 wood, 80 gold, 30 s) and researches
Elite Hussite Wagon in the Imperial Age (slot 5: 800 wood, 600 gold, 45 s), with the values of the AoE2 DE wiki. The
upgrade changes the live and the new units."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert len(train.HELP["HUSSITE_WAGON"]) <= 50 and "BOHEMIANS" not in train.civs.MISSING["HUSSITE_WAGON"]
    assert "BRITONS" in train.civs.MISSING["HUSSITE_WAGON"]


def test_the_castle_of_the_bohemians_trains_the_hussite_wagon():
    server, g = setup("BOHEMIANS", food=0, wood=110, gold=80)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:minecart:Hussite Wagon:110 wood · 80 gold · 30 s · queue 0/15 " in menu
    assert "Elite Hussite Wagon" not in menu                           # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, 0) == 1 and g.queues[rect][0]["name"] == "HUSSITE_WAGON"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Hussite Wagon" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("BOHEMIANS", food=0, wood=2000, gold=2000, ages=3)
    g.soldiers["hw"] = "HUSSITE_WAGON"
    g.game.entities.setdefault("hw", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert " 5:book:Elite Hussite Wagon:800 wood · 600 gold · 45 s · research " in menus(server)[-1] + " "
    assert train.queue(g, "Steve", CASTLE, "ELITE_HUSSITE_WAGON_UPGRADE")
    train.tick(g, 45)
    assert "ELITE_HUSSITE_WAGON_UPGRADE" in g.techs and g.soldiers["hw"] == "ELITE_HUSSITE_WAGON"
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:minecart:Elite Hussite Wagon:110 wood · 80 gold · 26 s · queue 0/15 " in menu
    assert ":Hussite Wagon:" not in menu and "5:book" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_HUSSITE_WAGON")
    assert train.queue(g, "Steve", CASTLE, "HUSSITE_WAGON") is None
