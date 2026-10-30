"""Leitis (#1746): the castle of the Lithuanians trains the leitis and researches Elite Leitis in the Imperial Age, with
the values of the AoE2 DE wiki infobox "Leitis". The upgrade changes the live and the new units."""
from menu_line import item
from test_train_castle import menus, setup

from game import combat, train

CASTLE = (12, 4)


def test_the_castle_of_the_lithuanians_trains_the_leitis():
    server, g = setup("LITHUANIANS", food=2000, wood=2000, gold=2000)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1]
    assert item(menu, "Leitis").endswith(" · queue 0/15")
    assert "Elite Leitis" not in menu                                  # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, train.SLOTS["LEITIS"]) == 1
    assert g.queues[rect][0]["name"] == "LEITIS"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Leitis" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("LITHUANIANS", food=2000, wood=2000, gold=2000, ages=3)
    g.soldiers["lt"] = "LEITIS"
    g.game.entities.setdefault("lt", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert item(menus(server)[-1], "Elite Leitis").endswith(" · research")
    assert train.queue(g, "Steve", CASTLE, "ELITE_LEITIS_UPGRADE")
    train.tick(g, train.seconds(g, "ELITE_LEITIS_UPGRADE", "CASTLE"))
    assert "ELITE_LEITIS_UPGRADE" in g.techs and g.soldiers["lt"] == "ELITE_LEITIS"
    assert combat.stats_command("lt", "ELITE_LEITIS", **train.hits(g, "ELITE_LEITIS")) in server.log   # with its hit rules (#4394)
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1]
    assert item(menu, "Elite Leitis").endswith(" · queue 0/15")
    assert item(menu, "Leitis") is None                       # only the elite unit
    assert train.queue(g, "Steve", CASTLE, "ELITE_LEITIS")
    assert train.queue(g, "Steve", CASTLE, "LEITIS") is None
