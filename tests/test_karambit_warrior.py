"""Karambit Warrior (#1750): the castle of the Malay trains the Karambit Warrior (25 food, 15 gold, 6 s) and researches
Elite Karambit Warrior in the Imperial Age (slot 5: 900 food, 600 gold, 40 s), with the values of the AoE2 DE wiki.
The upgrade changes the live and the new units."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    for name in ("KARAMBIT_WARRIOR", "ELITE_KARAMBIT_WARRIOR", "ELITE_KARAMBIT_WARRIOR_UPGRADE"):
        assert len(train.HELP[name]) <= 50 and "MALAY" not in train.civs.MISSING[name]
        assert "BRITONS" in train.civs.MISSING[name]


def test_the_castle_of_the_malay_trains_the_karambit_warrior():
    server, g = setup("MALAY", food=25, wood=0, gold=15)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:zombie_spawn_egg:Karambit Warrior:25 food · 15 gold · 6 s · queue 0/15 " in menu
    assert "Elite Karambit Warrior" not in menu                        # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, 0) == 1 and g.queues[rect][0]["name"] == "KARAMBIT_WARRIOR"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Karambit" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("MALAY", food=2000, wood=0, gold=2000, ages=3)
    g.soldiers["kw"] = "KARAMBIT_WARRIOR"
    g.game.entities.setdefault("kw", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert " 5:book:Elite Karambit Warrior:900 food · 600 gold · 40 s · research " in menus(server)[-1] + " "
    assert train.queue(g, "Steve", CASTLE, "ELITE_KARAMBIT_WARRIOR_UPGRADE")
    train.tick(g, 40)
    assert "ELITE_KARAMBIT_WARRIOR_UPGRADE" in g.techs and g.soldiers["kw"] == "ELITE_KARAMBIT_WARRIOR"
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:zombie_spawn_egg:Elite Karambit Warrior:25 food · 15 gold · 6 s · queue 0/15 " in menu
    assert ":Karambit Warrior:" not in menu and "5:book" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_KARAMBIT_WARRIOR")
    assert train.queue(g, "Steve", CASTLE, "KARAMBIT_WARRIOR") is None
