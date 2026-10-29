"""Karambit Warrior (#1750): the castle of the Malay trains the Karambit Warrior and researches Elite Karambit Warrior in
the Imperial Age, with the values of the AoE2 DE wiki. The upgrade changes the live and the new units."""
from menu_line import item
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_castle_of_the_malay_trains_the_karambit_warrior():
    server, g = setup("MALAY", food=2000, wood=2000, gold=2000)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1]
    assert item(menu, "Karambit Warrior").endswith(" · queue 0/15")
    assert "Elite Karambit Warrior" not in menu                        # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, train.SLOTS["KARAMBIT_WARRIOR"]) == 1
    assert g.queues[rect][0]["name"] == "KARAMBIT_WARRIOR"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Karambit" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("MALAY", food=2000, wood=2000, gold=2000, ages=3)
    g.soldiers["kw"] = "KARAMBIT_WARRIOR"
    g.game.entities.setdefault("kw", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert item(menus(server)[-1], "Elite Karambit Warrior").endswith(" · research")
    assert train.queue(g, "Steve", CASTLE, "ELITE_KARAMBIT_WARRIOR_UPGRADE")
    train.tick(g, train.seconds(g, "ELITE_KARAMBIT_WARRIOR_UPGRADE", "CASTLE"))
    assert "ELITE_KARAMBIT_WARRIOR_UPGRADE" in g.techs and g.soldiers["kw"] == "ELITE_KARAMBIT_WARRIOR"
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1]
    assert item(menu, "Elite Karambit Warrior").endswith(" · queue 0/15")
    assert item(menu, "Karambit Warrior") is None                       # only the elite unit
    assert train.queue(g, "Steve", CASTLE, "ELITE_KARAMBIT_WARRIOR")
    assert train.queue(g, "Steve", CASTLE, "KARAMBIT_WARRIOR") is None
