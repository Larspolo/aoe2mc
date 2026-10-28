"""Kamayuk (#1886): the castle of the Incas trains the Kamayuk (70 food, 30 gold, 10 s) and researches Elite Kamayuk in
the Imperial Age (slot 5: 900 food, 500 gold, 45 s), with the values of the AoE2 DE wiki. The upgrade changes the live
and the new units."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert len(train.HELP["KAMAYUK"]) <= 50 and "INCAS" not in train.civs.MISSING["KAMAYUK"]
    assert "BRITONS" in train.civs.MISSING["KAMAYUK"]


def test_the_castle_of_the_incas_trains_the_kamayuk():
    server, g = setup("INCAS", food=70, wood=0, gold=30)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:zombie_spawn_egg:Kamayuk:53 food · 30 gold · 10 s · queue 0/15 " in menu
    assert "Elite Kamayuk" not in menu                                 # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, 0) == 1 and g.queues[rect][0]["name"] == "KAMAYUK"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Kamayuk" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("INCAS", food=2000, wood=0, gold=2000, ages=3)
    g.soldiers["kk"] = "KAMAYUK"
    g.game.entities.setdefault("kk", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert " 5:book:Elite Kamayuk:900 food · 500 gold · 45 s · research " in menus(server)[-1] + " "
    assert train.queue(g, "Steve", CASTLE, "ELITE_KAMAYUK_UPGRADE")
    train.tick(g, 45)
    assert "ELITE_KAMAYUK_UPGRADE" in g.techs and g.soldiers["kk"] == "ELITE_KAMAYUK"
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:zombie_spawn_egg:Elite Kamayuk:49 food · 30 gold · 10 s · queue 0/15 " in menu
    assert ":Kamayuk:" not in menu and "5:book" not in menu
