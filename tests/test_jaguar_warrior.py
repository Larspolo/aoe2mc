"""Jaguar Warrior (#1884): the castle of the Aztecs trains the Jaguar Warrior and researches Elite Jaguar Warrior in the
Imperial Age, with the values of the AoE2 DE wiki. The upgrade changes the live and the new units."""
from menu_line import item
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_castle_of_the_aztecs_trains_the_jaguar_warrior():
    server, g = setup("AZTECS", food=2000, wood=2000, gold=2000)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1]
    assert item(menu, "Jaguar Warrior").endswith(" · queue 0/15")
    assert train.seconds(g, "JAGUAR_WARRIOR", "CASTLE") < train.TRAIN_TIMES["JAGUAR_WARRIOR"]   # the Aztec bonus (#1927)
    assert "Elite Jaguar" not in menu                                  # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, train.SLOTS["JAGUAR_WARRIOR"]) == 1
    assert g.queues[rect][0]["name"] == "JAGUAR_WARRIOR"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Jaguar Warrior" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("AZTECS", food=2000, wood=2000, gold=2000, ages=3)
    g.soldiers["jw"] = "JAGUAR_WARRIOR"
    g.game.entities.setdefault("jw", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert item(menus(server)[-1], "Elite Jaguar Warrior").endswith(" · research")
    assert train.queue(g, "Steve", CASTLE, "ELITE_JAGUAR_WARRIOR_UPGRADE")
    train.tick(g, train.seconds(g, "ELITE_JAGUAR_WARRIOR_UPGRADE", "CASTLE"))
    assert "ELITE_JAGUAR_WARRIOR_UPGRADE" in g.techs and g.soldiers["jw"] == "ELITE_JAGUAR_WARRIOR"
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1]
    assert item(menu, "Elite Jaguar Warrior").endswith(" · queue 0/15")
    assert item(menu, "Jaguar Warrior") is None                       # only the elite unit
    assert train.queue(g, "Steve", CASTLE, "ELITE_JAGUAR_WARRIOR")
    assert train.queue(g, "Steve", CASTLE, "JAGUAR_WARRIOR") is None
