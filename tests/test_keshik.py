"""Keshik (#1745): the castle of the Tatars trains the keshik and researches Elite Keshik in the Imperial Age, with the
values of the AoE2 DE wiki "Keshik". The upgrade changes the live and the new units."""
from menu_line import item
from test_train_castle import menus, setup

from game import combat, train

CASTLE = (12, 4)


def test_the_castle_of_the_tatars_trains_the_keshik():
    server, g = setup("TATARS", food=2000, wood=2000, gold=2000)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1]
    assert item(menu, "Keshik").endswith(" · queue 0/15")
    assert "Elite Keshik" not in menu                                  # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, train.SLOTS["KESHIK"]) == 1
    assert g.queues[rect][0]["name"] == "KESHIK"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Keshik" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("TATARS", food=2000, wood=2000, gold=2000, ages=3)
    g.soldiers["ct"] = "KESHIK"
    g.game.entities.setdefault("ct", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert item(menus(server)[-1], "Elite Keshik").endswith(" · research")
    assert train.queue(g, "Steve", CASTLE, "ELITE_KESHIK_UPGRADE")
    train.tick(g, train.seconds(g, "ELITE_KESHIK_UPGRADE", "CASTLE"))
    assert "ELITE_KESHIK_UPGRADE" in g.techs and g.soldiers["ct"] == "ELITE_KESHIK"
    assert combat.stats_command("ct", "ELITE_KESHIK") in server.log
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1]
    assert item(menu, "Elite Keshik").endswith(" · queue 0/15")
    assert item(menu, "Keshik") is None                       # only the elite unit
    assert train.queue(g, "Steve", CASTLE, "ELITE_KESHIK")
    assert train.queue(g, "Steve", CASTLE, "KESHIK") is None
