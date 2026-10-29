"""Genoese Crossbowman (#1724): the castle of the Italians trains the Genoese crossbowman and researches Elite Genoese
Crossbowman in the Imperial Age. The upgrade changes the live and the new units. Pattern: the chakram thrower (#1624)."""
from menu_line import item
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_castle_of_the_italians_trains_the_genoese_crossbowman():
    server, g = setup("ITALIANS", food=2000, wood=2000, gold=2000)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1]
    assert item(menu, "Genoese Crossbowman").endswith(" · queue 0/15")
    assert "Elite Genoese" not in menu                                 # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, train.SLOTS["GENOESE_CROSSBOWMAN"]) == 1
    assert g.queues[rect][0]["name"] == "GENOESE_CROSSBOWMAN"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Genoese" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("ITALIANS", food=2000, wood=2000, gold=2000, ages=3)
    g.soldiers["gc"] = "GENOESE_CROSSBOWMAN"
    g.game.entities.setdefault("gc", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert item(menus(server)[-1], "Elite Genoese Crossbowman").endswith(" · research")
    assert train.queue(g, "Steve", CASTLE, "ELITE_GENOESE_CROSSBOWMAN_UPGRADE")
    train.tick(g, train.seconds(g, "ELITE_GENOESE_CROSSBOWMAN_UPGRADE", "CASTLE"))
    assert "ELITE_GENOESE_CROSSBOWMAN_UPGRADE" in g.techs and g.soldiers["gc"] == "ELITE_GENOESE_CROSSBOWMAN"
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1]
    assert item(menu, "Elite Genoese Crossbowman").endswith(" · queue 0/15")
    assert item(menu, "Genoese Crossbowman") is None                       # only the elite unit
    assert train.queue(g, "Steve", CASTLE, "ELITE_GENOESE_CROSSBOWMAN")
    assert train.queue(g, "Steve", CASTLE, "GENOESE_CROSSBOWMAN") is None
