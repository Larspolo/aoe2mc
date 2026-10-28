"""Ballista Elephant (#1752): the castle of the Khmer trains the Ballista Elephant (100 food · 80 gold, 25 s) and
researches Elite Ballista Elephant in the Imperial Age (slot 5: 1000 food · 500 gold, 70 s), with the values of the
AoE2 DE wiki. The upgrade changes the live and the new units."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    for name in ("BALLISTA_ELEPHANT", "ELITE_BALLISTA_ELEPHANT", "ELITE_BALLISTA_ELEPHANT_UPGRADE"):
        assert len(train.HELP[name]) <= 50 and "KHMER" not in train.civs.MISSING[name]
        assert "BRITONS" in train.civs.MISSING[name]


def test_the_castle_of_the_khmer_trains_the_ballista_elephant():
    server, g = setup("KHMER", food=100, wood=0, gold=80)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:ravager_spawn_egg:Ballista Elephant:100 food · 80 gold · 25 s · queue 0/15 " in menu
    assert "Elite Ballista Elephant" not in menu                                 # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, 0) == 1 and g.queues[rect][0]["name"] == "BALLISTA_ELEPHANT"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Ballista Elephant" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("KHMER", food=2000, wood=2000, gold=2000, ages=3)
    g.soldiers["ub"] = "BALLISTA_ELEPHANT"
    g.game.entities.setdefault("ub", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert " 5:book:Elite Ballista Elephant:1000 food · 500 gold · 70 s · research " in menus(server)[-1] + " "
    assert train.queue(g, "Steve", CASTLE, "ELITE_BALLISTA_ELEPHANT_UPGRADE")
    train.tick(g, 70)
    assert "ELITE_BALLISTA_ELEPHANT_UPGRADE" in g.techs and g.soldiers["ub"] == "ELITE_BALLISTA_ELEPHANT"
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:ravager_spawn_egg:Elite Ballista Elephant:100 food · 80 gold · 25 s · queue 0/15 " in menu
    assert ":Ballista Elephant:" not in menu.replace("Elite Ballista Elephant", "") and "5:book" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_BALLISTA_ELEPHANT")
    assert train.queue(g, "Steve", CASTLE, "BALLISTA_ELEPHANT") is None
