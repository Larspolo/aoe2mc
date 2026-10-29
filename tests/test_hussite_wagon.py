"""Hussite Wagon (#1758): the castle of the Bohemians trains the Hussite Wagon and researches Elite Hussite Wagon in the
Imperial Age, with the values of the AoE2 DE wiki. The upgrade changes the live and the new units."""
from menu_line import item
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_castle_of_the_bohemians_trains_the_hussite_wagon():
    server, g = setup("BOHEMIANS", food=2000, wood=2000, gold=2000)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1]
    assert item(menu, "Hussite Wagon").endswith(" · queue 0/15")
    assert "Elite Hussite Wagon" not in menu                           # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, train.SLOTS["HUSSITE_WAGON"]) == 1
    assert g.queues[rect][0]["name"] == "HUSSITE_WAGON"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Hussite Wagon" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("BOHEMIANS", food=2000, wood=2000, gold=2000, ages=3)
    g.soldiers["hw"] = "HUSSITE_WAGON"
    g.game.entities.setdefault("hw", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert item(menus(server)[-1], "Elite Hussite Wagon").endswith(" · research")
    assert train.queue(g, "Steve", CASTLE, "ELITE_HUSSITE_WAGON_UPGRADE")
    train.tick(g, train.seconds(g, "ELITE_HUSSITE_WAGON_UPGRADE", "CASTLE"))
    assert "ELITE_HUSSITE_WAGON_UPGRADE" in g.techs and g.soldiers["hw"] == "ELITE_HUSSITE_WAGON"
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1]
    assert item(menu, "Elite Hussite Wagon").endswith(" · queue 0/15")
    assert item(menu, "Hussite Wagon") is None                       # only the elite unit
    assert train.queue(g, "Steve", CASTLE, "ELITE_HUSSITE_WAGON")
    assert train.queue(g, "Steve", CASTLE, "HUSSITE_WAGON") is None
