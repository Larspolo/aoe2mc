"""Gbeto (#1722): the castle of the Malians trains the Gbeto and researches Elite Gbeto in the Imperial Age. The upgrade
changes the live and the new units."""
from menu_line import item
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_castle_of_the_malians_trains_the_gbeto():
    server, g = setup("MALIANS", food=2000, wood=2000, gold=2000)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1]
    assert item(menu, "Gbeto").endswith(" · queue 0/15")
    assert item(menu, "Elite Gbeto") is None                           # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, int(item(menu, "Gbeto").split(":")[0])) == 1
    assert g.queues[rect][0]["name"] == "GBETO"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Gbeto" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("MALIANS", food=2000, wood=0, gold=2000, ages=3)
    g.soldiers["gb"] = "GBETO"
    g.game.entities.setdefault("gb", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert item(menus(server)[-1], "Elite Gbeto").endswith(" · research")
    assert train.queue(g, "Steve", CASTLE, "ELITE_GBETO_UPGRADE")
    train.tick(g, train.seconds(g, "ELITE_GBETO_UPGRADE", "CASTLE"))
    assert "ELITE_GBETO_UPGRADE" in g.techs and g.soldiers["gb"] == "ELITE_GBETO"
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1]
    assert item(menu, "Elite Gbeto").endswith(" · queue 0/15")
    assert item(menu, "Gbeto") is None                                 # only the elite unit
    assert train.queue(g, "Steve", CASTLE, "ELITE_GBETO")
    assert train.queue(g, "Steve", CASTLE, "GBETO") is None
