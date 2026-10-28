"""Gbeto (#1722): the castle of the Malians trains the Gbeto (50 food, 40 gold, 17 s) and researches Elite Gbeto in the
Imperial Age (slot 5: 900 food, 600 gold, 45 s), with the values of the AoE2 DE wiki. The upgrade changes the live and
the new units."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert len(train.HELP["GBETO"]) <= 50 and "MALIANS" not in train.civs.MISSING["GBETO"]
    assert "BRITONS" in train.civs.MISSING["GBETO"]


def test_the_castle_of_the_malians_trains_the_gbeto():
    server, g = setup("MALIANS", food=50, wood=0, gold=40)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:drowned_spawn_egg:Gbeto:50 food · 40 gold · 17 s · queue 0/15 " in menu
    assert "Elite Gbeto" not in menu                                   # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, 0) == 1 and g.queues[rect][0]["name"] == "GBETO"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Gbeto" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("MALIANS", food=2000, wood=0, gold=2000, ages=3)
    g.soldiers["gb"] = "GBETO"
    g.game.entities.setdefault("gb", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert " 5:book:Elite Gbeto:900 food · 600 gold · 45 s · research " in menus(server)[-1] + " "
    assert train.queue(g, "Steve", CASTLE, "ELITE_GBETO_UPGRADE")
    train.tick(g, 45)
    assert "ELITE_GBETO_UPGRADE" in g.techs and g.soldiers["gb"] == "ELITE_GBETO"
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:drowned_spawn_egg:Elite Gbeto:50 food · 40 gold · 17 s · queue 0/15 " in menu
    assert ":Gbeto:" not in menu and "5:book" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_GBETO")
    assert train.queue(g, "Steve", CASTLE, "GBETO") is None
