"""Ghulam (#1756): the castle of the Hindustanis trains the ghulam and researches Elite Ghulam in the Imperial Age. The
upgrade changes the live and the new units."""
from menu_line import item
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_castle_of_the_hindustanis_trains_the_ghulam():
    server, g = setup("HINDUSTANIS", food=2000, wood=2000, gold=2000)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1]
    assert item(menu, "Ghulam").endswith(" · queue 0/15")
    assert "Elite Ghulam" not in menu                                  # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, train.SLOTS["GHULAM"]) == 1
    assert g.queues[rect][0]["name"] == "GHULAM"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Ghulam" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("HINDUSTANIS", food=2000, wood=0, gold=2000, ages=3)
    g.soldiers["gh"] = "GHULAM"
    g.game.entities.setdefault("gh", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert item(menus(server)[-1], "Elite Ghulam").endswith(" · research")
    assert train.queue(g, "Steve", CASTLE, "ELITE_GHULAM_UPGRADE")
    train.tick(g, train.seconds(g, "ELITE_GHULAM_UPGRADE", "CASTLE"))
    assert "ELITE_GHULAM_UPGRADE" in g.techs and g.soldiers["gh"] == "ELITE_GHULAM"
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1]
    assert item(menu, "Elite Ghulam").endswith(" · queue 0/15")
    assert item(menu, "Ghulam") is None                       # only the elite unit
    assert train.queue(g, "Steve", CASTLE, "ELITE_GHULAM")
    assert train.queue(g, "Steve", CASTLE, "GHULAM") is None
