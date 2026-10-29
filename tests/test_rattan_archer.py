"""Rattan Archer (#1888): the castle of the Vietnamese trains the rattan archer and researches Elite Rattan Archer in
the Imperial Age. The upgrade changes the live and the new units."""
from menu_line import item
from test_train_castle import menus, setup

from game import combat, train

CASTLE = (12, 4)


def test_the_castle_of_the_vietnamese_trains_the_rattan_archer():
    server, g = setup("VIETNAMESE", food=2000, wood=2000, gold=2000)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1]
    assert item(menu, "Rattan Archer").endswith(" · queue 0/15")
    assert item(menu, "Elite Rattan Archer") is None                   # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, int(item(menu, "Rattan Archer").split(":")[0])) == 1
    assert g.queues[rect][0]["name"] == "RATTAN_ARCHER"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Rattan Archer" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("VIETNAMESE", food=2000, wood=2000, gold=2000, ages=3)
    g.soldiers["ct"] = "RATTAN_ARCHER"
    g.game.entities.setdefault("ct", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert item(menus(server)[-1], "Elite Rattan Archer").endswith(" · research")
    assert train.queue(g, "Steve", CASTLE, "ELITE_RATTAN_ARCHER_UPGRADE")
    train.tick(g, train.seconds(g, "ELITE_RATTAN_ARCHER_UPGRADE", "CASTLE"))
    assert "ELITE_RATTAN_ARCHER_UPGRADE" in g.techs and g.soldiers["ct"] == "ELITE_RATTAN_ARCHER"
    assert combat.stats_command("ct", "ELITE_RATTAN_ARCHER", train.stats(g, "ELITE_RATTAN_ARCHER")) in server.log
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1]
    assert item(menu, "Elite Rattan Archer").endswith(" · queue 0/15")
    assert item(menu, "Rattan Archer") is None                       # only the elite unit
    assert train.queue(g, "Steve", CASTLE, "ELITE_RATTAN_ARCHER")
    assert train.queue(g, "Steve", CASTLE, "RATTAN_ARCHER") is None
