"""Genoese Crossbowman (#1724): the castle of the Italians trains the Genoese crossbowman (45 wood, 40 gold, 14 s) and
researches Elite Genoese Crossbowman in the Imperial Age (slot 5: 900 food, 750 gold, 60 s), with the values of the AoE2
DE wiki. The upgrade changes the live and the new units. Pattern: the chakram thrower (#1624)."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert len(train.HELP["GENOESE_CROSSBOWMAN"]) <= 50
    assert "ITALIANS" not in train.civs.MISSING["GENOESE_CROSSBOWMAN"]
    assert "BRITONS" in train.civs.MISSING["GENOESE_CROSSBOWMAN"]


def test_the_castle_of_the_italians_trains_the_genoese_crossbowman():
    server, g = setup("ITALIANS", wood=45, gold=40)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:skeleton_spawn_egg:Genoese Crossbowman:45 wood · 40 gold · 14 s · queue 0/15 " in menu
    assert "Elite Genoese" not in menu                                 # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, 0) == 1 and g.queues[rect][0]["name"] == "GENOESE_CROSSBOWMAN"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Genoese" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("ITALIANS", food=2000, wood=2000, gold=2000, ages=3)
    g.soldiers["gc"] = "GENOESE_CROSSBOWMAN"
    g.game.entities.setdefault("gc", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert " 5:book:Elite Genoese Crossbowman:900 food · 750 gold · 60 s · research " in menus(server)[-1] + " "
    assert train.queue(g, "Steve", CASTLE, "ELITE_GENOESE_CROSSBOWMAN_UPGRADE")
    train.tick(g, 60)
    assert "ELITE_GENOESE_CROSSBOWMAN_UPGRADE" in g.techs and g.soldiers["gc"] == "ELITE_GENOESE_CROSSBOWMAN"
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:skeleton_spawn_egg:Elite Genoese Crossbowman:45 wood · 40 gold · 14 s · queue 0/15 " in menu
    assert ":Genoese Crossbowman:" not in menu and "5:book" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_GENOESE_CROSSBOWMAN")
    assert train.queue(g, "Steve", CASTLE, "GENOESE_CROSSBOWMAN") is None
