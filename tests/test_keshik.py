"""Keshik (#1745): the castle of the Tatars trains the keshik (60 food, 40 gold, 17 s) and researches Elite Keshik
in the Imperial Age (slot 5: 700 food, 600 gold, 40 s), with the values of the AoE2 DE wiki "Keshik". The upgrade
changes the live and the new units."""
from test_train_castle import menus, setup

from game import combat, train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert len(train.HELP["KESHIK"]) <= 50 and "TATARS" not in train.civs.MISSING["KESHIK"]
    assert "BRITONS" in train.civs.MISSING["KESHIK"]
    assert "TATARS" not in train.civs.MISSING["ELITE_KESHIK_UPGRADE"]


def test_the_castle_of_the_tatars_trains_the_keshik():
    server, g = setup("TATARS", food=60, wood=0, gold=40)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:horse_spawn_egg:Keshik:60 food · 40 gold · 17 s · queue 0/15 " in menu
    assert "Elite Keshik" not in menu                                  # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, 0) == 1 and g.queues[rect][0]["name"] == "KESHIK"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Keshik" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("TATARS", food=2000, wood=0, gold=2000, ages=3)
    g.soldiers["ct"] = "KESHIK"
    g.game.entities.setdefault("ct", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert " 5:book:Elite Keshik:700 food · 600 gold · 40 s · research " in menus(server)[-1] + " "
    assert train.queue(g, "Steve", CASTLE, "ELITE_KESHIK_UPGRADE")
    train.tick(g, 40)
    assert "ELITE_KESHIK_UPGRADE" in g.techs and g.soldiers["ct"] == "ELITE_KESHIK"
    assert combat.stats_command("ct", "ELITE_KESHIK") in server.log
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:horse_spawn_egg:Elite Keshik:60 food · 40 gold · 15 s · queue 0/15 " in menu
    assert ":Keshik:" not in menu and "5:book" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_KESHIK")
    assert train.queue(g, "Steve", CASTLE, "KESHIK") is None
