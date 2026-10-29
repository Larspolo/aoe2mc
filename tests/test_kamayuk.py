"""Kamayuk (#1886): the castle of the Incas trains the Kamayuk and researches Elite Kamayuk in the Imperial Age, with the
values of the AoE2 DE wiki. The upgrade changes the live and the new units."""
from menu_line import item
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_castle_of_the_incas_trains_the_kamayuk():
    server, g = setup("INCAS", food=2000, wood=2000, gold=2000)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1]
    assert item(menu, "Kamayuk").endswith(" · queue 0/15")
    assert "Elite Kamayuk" not in menu                                 # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, train.SLOTS["KAMAYUK"]) == 1
    assert g.queues[rect][0]["name"] == "KAMAYUK"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Kamayuk" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("INCAS", food=2000, wood=2000, gold=2000, ages=3)
    g.soldiers["kk"] = "KAMAYUK"
    g.game.entities.setdefault("kk", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert item(menus(server)[-1], "Elite Kamayuk").endswith(" · research")
    assert train.queue(g, "Steve", CASTLE, "ELITE_KAMAYUK_UPGRADE")
    train.tick(g, train.seconds(g, "ELITE_KAMAYUK_UPGRADE", "CASTLE"))
    assert "ELITE_KAMAYUK_UPGRADE" in g.techs and g.soldiers["kk"] == "ELITE_KAMAYUK"
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1]
    assert item(menu, "Elite Kamayuk").endswith(" · queue 0/15")
    assert item(menu, "Kamayuk") is None                       # only the elite unit
