"""Konnik (#1757): the castle of the Bulgarians trains the konnik (60 food, 70 gold, 16 s) and researches Elite Konnik
in the Imperial Age (slot 5: 1000 food, 750 gold, 70 s), with the values of the AoE2 DE wiki "Konnik". The upgrade
changes the live and the new units."""
from test_train_castle import menus, setup

from game import combat, train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert len(train.HELP["KONNIK"]) <= 50 and "BULGARIANS" not in train.civs.MISSING["KONNIK"]
    assert "BRITONS" in train.civs.MISSING["KONNIK"]
    assert "BULGARIANS" not in train.civs.MISSING["ELITE_KONNIK_UPGRADE"]


def test_the_castle_of_the_bulgarians_trains_the_konnik():
    server, g = setup("BULGARIANS", food=60, wood=0, gold=70)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:horse_spawn_egg:Konnik:60 food · 70 gold · 16 s · queue 0/15 " in menu
    assert "Elite Konnik" not in menu                                  # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, 0) == 1 and g.queues[rect][0]["name"] == "KONNIK"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Konnik" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("BULGARIANS", food=2000, wood=0, gold=2000, ages=3)
    g.soldiers["ct"] = "KONNIK"
    g.game.entities.setdefault("ct", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert " 5:book:Elite Konnik:1000 food · 750 gold · 70 s · research " in menus(server)[-1] + " "
    assert train.queue(g, "Steve", CASTLE, "ELITE_KONNIK_UPGRADE")
    train.tick(g, 70)
    assert "ELITE_KONNIK_UPGRADE" in g.techs and g.soldiers["ct"] == "ELITE_KONNIK"
    assert combat.stats_command("ct", "ELITE_KONNIK") in server.log
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:horse_spawn_egg:Elite Konnik:60 food · 70 gold · 16 s · queue 0/15 " in menu
    assert ":Konnik:" not in menu and "5:book" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_KONNIK")
    assert train.queue(g, "Steve", CASTLE, "KONNIK") is None
