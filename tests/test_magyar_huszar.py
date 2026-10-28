"""Magyar Huszar (#1743): the castle of the Magyars trains the Magyar Huszar (35 food, 45 gold, 18 s) and researches
Elite Magyar Huszar in the Imperial Age (slot 5: 800 food, 600 gold, 60 s), with the values of the AoE2 DE wiki.
The upgrade changes the live and the new units."""
from test_train_castle import menus, setup

from game import combat, train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert len(train.HELP["MAGYAR_HUSZAR"]) <= 50 and "MAGYARS" not in train.civs.MISSING["MAGYAR_HUSZAR"]
    assert "BRITONS" in train.civs.MISSING["MAGYAR_HUSZAR"]


def test_the_castle_of_the_magyars_trains_the_magyar_huszar():
    server, g = setup("MAGYARS", food=35, wood=0, gold=45)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:horse_spawn_egg:Magyar Huszar:35 food · 45 gold · 18 s · queue 0/15 " in menu
    assert "Elite Magyar" not in menu                                  # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, 0) == 1 and g.queues[rect][0]["name"] == "MAGYAR_HUSZAR"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Magyar" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("MAGYARS", food=2000, wood=0, gold=2000, ages=3)
    g.soldiers["mh"] = "MAGYAR_HUSZAR"
    g.game.entities.setdefault("mh", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert " 5:book:Elite Magyar Huszar:800 food · 600 gold · 60 s · research " in menus(server)[-1] + " "
    assert train.queue(g, "Steve", CASTLE, "ELITE_MAGYAR_HUSZAR_UPGRADE")
    train.tick(g, 60)
    assert "ELITE_MAGYAR_HUSZAR_UPGRADE" in g.techs and g.soldiers["mh"] == "ELITE_MAGYAR_HUSZAR"
    assert combat.stats_command("mh", "ELITE_MAGYAR_HUSZAR") in server.log
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:horse_spawn_egg:Elite Magyar Huszar:35 food · 45 gold · 12 s · queue 0/15 " in menu
    assert ":Magyar Huszar:" not in menu and "5:book" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_MAGYAR_HUSZAR")
    assert train.queue(g, "Steve", CASTLE, "MAGYAR_HUSZAR") is None
