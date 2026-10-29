"""Konnik (#1757): the castle of the Bulgarians trains the konnik and researches Elite Konnik in the Imperial Age, with
the values of the AoE2 DE wiki "Konnik". The upgrade changes the live and the new units."""
from menu_line import item
from test_train_castle import menus, setup

from game import combat, train

CASTLE = (12, 4)


def test_the_castle_of_the_bulgarians_trains_the_konnik():
    server, g = setup("BULGARIANS", food=2000, wood=2000, gold=2000)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1]
    assert item(menu, "Konnik").endswith(" · queue 0/15")
    assert "Elite Konnik" not in menu                                  # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, train.SLOTS["KONNIK"]) == 1
    assert g.queues[rect][0]["name"] == "KONNIK"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Konnik" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("BULGARIANS", food=2000, wood=2000, gold=2000, ages=3)
    g.soldiers["ct"] = "KONNIK"
    g.game.entities.setdefault("ct", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert item(menus(server)[-1], "Elite Konnik").endswith(" · research")
    assert train.queue(g, "Steve", CASTLE, "ELITE_KONNIK_UPGRADE")
    train.tick(g, train.seconds(g, "ELITE_KONNIK_UPGRADE", "CASTLE"))
    assert "ELITE_KONNIK_UPGRADE" in g.techs and g.soldiers["ct"] == "ELITE_KONNIK"
    assert combat.stats_command("ct", "ELITE_KONNIK") in server.log
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1]
    assert item(menu, "Elite Konnik").endswith(" · queue 0/15")
    assert item(menu, "Konnik") is None                       # only the elite unit
    assert train.queue(g, "Steve", CASTLE, "ELITE_KONNIK")
    assert train.queue(g, "Steve", CASTLE, "KONNIK") is None
