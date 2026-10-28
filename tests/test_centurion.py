"""Centurion (#1749): the castle of the Romans trains the Centurion (75 food, 85 gold, 24 s) and researches Elite Centurion
in the Imperial Age (slot 5: 1100 food, 900 gold, 60 s), with the values of the AoE2 DE wiki. The upgrade changes the
live and the new units."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    for name in ("CENTURION", "ELITE_CENTURION", "ELITE_CENTURION_UPGRADE"):
        assert len(train.HELP[name]) <= 50 and "ROMANS" not in train.civs.MISSING[name]
        assert "BRITONS" in train.civs.MISSING[name]


def test_the_castle_of_the_romans_trains_the_centurion():
    server, g = setup("ROMANS", food=75, wood=0, gold=85)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:horse_spawn_egg:Centurion:75 food · 85 gold · 24 s · queue 0/15 " in menu
    assert "Elite Centurion" not in menu                               # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, 0) == 1 and g.queues[rect][0]["name"] == "CENTURION"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Centurion" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("ROMANS", food=2000, wood=0, gold=2000, ages=3)
    g.soldiers["ce"] = "CENTURION"
    g.game.entities.setdefault("ce", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert " 5:book:Elite Centurion:1100 food · 900 gold · 60 s · research " in menus(server)[-1] + " "
    assert train.queue(g, "Steve", CASTLE, "ELITE_CENTURION_UPGRADE")
    train.tick(g, 60)
    assert "ELITE_CENTURION_UPGRADE" in g.techs and g.soldiers["ce"] == "ELITE_CENTURION"
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:horse_spawn_egg:Elite Centurion:75 food · 85 gold · 24 s · queue 0/15 " in menu
    assert ":Centurion:" not in menu and "5:book" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_CENTURION")
    assert train.queue(g, "Steve", CASTLE, "CENTURION") is None
