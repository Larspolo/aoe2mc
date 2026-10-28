"""Monaspa (#1755): the castle of the Georgians trains the monaspa (60 food, 45 gold, 14 s) and researches Elite Monaspa
in the Imperial Age (slot 5: 1000 food, 700 gold, 45 s), with the values of the AoE2 DE wiki "Monaspa". The upgrade
changes the live and the new units."""
from test_train_castle import menus, setup

from game import combat, train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert len(train.HELP["MONASPA"]) <= 50 and "GEORGIANS" not in train.civs.MISSING["MONASPA"]
    assert "BRITONS" in train.civs.MISSING["MONASPA"]
    assert "GEORGIANS" not in train.civs.MISSING["ELITE_MONASPA_UPGRADE"]


def test_the_castle_of_the_georgians_trains_the_monaspa():
    server, g = setup("GEORGIANS", food=60, wood=0, gold=45)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:horse_spawn_egg:Monaspa:60 food · 45 gold · 14 s · queue 0/15 " in menu
    assert "Elite Monaspa" not in menu                                 # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, 0) == 1 and g.queues[rect][0]["name"] == "MONASPA"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Monaspa" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("GEORGIANS", food=2000, wood=0, gold=2000, ages=3)
    g.soldiers["ct"] = "MONASPA"
    g.game.entities.setdefault("ct", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert " 5:book:Elite Monaspa:1000 food · 700 gold · 45 s · research " in menus(server)[-1] + " "
    assert train.queue(g, "Steve", CASTLE, "ELITE_MONASPA_UPGRADE")
    train.tick(g, 45)
    assert "ELITE_MONASPA_UPGRADE" in g.techs and g.soldiers["ct"] == "ELITE_MONASPA"
    assert combat.stats_command("ct", "ELITE_MONASPA") in server.log
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:horse_spawn_egg:Elite Monaspa:60 food · 45 gold · 14 s · queue 0/15 " in menu
    assert ":Monaspa:" not in menu and "5:book" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_MONASPA")
    assert train.queue(g, "Steve", CASTLE, "MONASPA") is None
