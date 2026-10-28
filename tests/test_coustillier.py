"""Coustillier (#1753): the castle of the Burgundians trains the Coustillier (55 food, 55 gold, 15 s) and researches
Elite Coustillier in the Imperial Age (slot 5: 1000 food, 800 gold, 45 s), with the values of the AoE2 DE wiki.
The upgrade changes the live and the new units."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    for name in ("COUSTILLIER", "ELITE_COUSTILLIER", "ELITE_COUSTILLIER_UPGRADE"):
        assert len(train.HELP[name]) <= 50 and "BURGUNDIANS" not in train.civs.MISSING[name]
        assert "BRITONS" in train.civs.MISSING[name]


def test_the_castle_of_the_malay_trains_the_coustillier_warrior():
    server, g = setup("BURGUNDIANS", food=55, wood=0, gold=55)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:horse_spawn_egg:Coustillier:55 food · 55 gold · 15 s · queue 0/15 " in menu
    assert "Elite Coustillier" not in menu                        # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, 0) == 1 and g.queues[rect][0]["name"] == "COUSTILLIER"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Karambit" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("BURGUNDIANS", food=2000, wood=0, gold=2000, ages=3)
    g.soldiers["co"] = "COUSTILLIER"
    g.game.entities.setdefault("co", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert " 5:book:Elite Coustillier:1000 food · 800 gold · 45 s · research " in menus(server)[-1] + " "
    assert train.queue(g, "Steve", CASTLE, "ELITE_COUSTILLIER_UPGRADE")
    train.tick(g, 45)
    assert "ELITE_COUSTILLIER_UPGRADE" in g.techs and g.soldiers["co"] == "ELITE_COUSTILLIER"
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:horse_spawn_egg:Elite Coustillier:55 food · 55 gold · 14 s · queue 0/15 " in menu
    assert ":Coustillier:" not in menu and "5:book" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_COUSTILLIER")
    assert train.queue(g, "Steve", CASTLE, "COUSTILLIER") is None
