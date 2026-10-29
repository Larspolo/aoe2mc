"""Magyar Huszar (#1743): the castle of the Magyars trains the Magyar Huszar and researches Elite Magyar Huszar in the
Imperial Age, with the values of the AoE2 DE wiki. The upgrade changes the live and the new units."""
from menu_line import item
from test_train_castle import menus, setup

from game import combat, train

CASTLE = (12, 4)


def test_the_castle_of_the_magyars_trains_the_magyar_huszar():
    server, g = setup("MAGYARS", food=2000, wood=2000, gold=2000)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1]
    assert item(menu, "Magyar Huszar").endswith(" · queue 0/15")
    assert "Elite Magyar" not in menu                                  # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, train.SLOTS["MAGYAR_HUSZAR"]) == 1
    assert g.queues[rect][0]["name"] == "MAGYAR_HUSZAR"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Magyar" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("MAGYARS", food=2000, wood=2000, gold=2000, ages=3)
    g.soldiers["mh"] = "MAGYAR_HUSZAR"
    g.game.entities.setdefault("mh", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert item(menus(server)[-1], "Elite Magyar Huszar").endswith(" · research")
    assert train.queue(g, "Steve", CASTLE, "ELITE_MAGYAR_HUSZAR_UPGRADE")
    train.tick(g, train.seconds(g, "ELITE_MAGYAR_HUSZAR_UPGRADE", "CASTLE"))
    assert "ELITE_MAGYAR_HUSZAR_UPGRADE" in g.techs and g.soldiers["mh"] == "ELITE_MAGYAR_HUSZAR"
    assert combat.stats_command("mh", "ELITE_MAGYAR_HUSZAR") in server.log
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1]
    assert item(menu, "Elite Magyar Huszar").endswith(" · queue 0/15")
    assert item(menu, "Magyar Huszar") is None                       # only the elite unit
    assert train.queue(g, "Steve", CASTLE, "ELITE_MAGYAR_HUSZAR")
    assert train.queue(g, "Steve", CASTLE, "MAGYAR_HUSZAR") is None
