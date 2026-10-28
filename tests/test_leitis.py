"""Leitis (#1746): the castle of the Lithuanians trains the leitis (70 food, 50 gold, 20 s) and researches Elite Leitis
in the Imperial Age (slot 5: 750 food, 750 gold, 45 s), with the values of the AoE2 DE wiki infobox "Leitis". The elite
unit trains in 18 s. The upgrade changes the live and the new units."""
from test_train_castle import menus, setup

from game import combat, train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert "LEITIS" in combat.STATS and "ELITE_LEITIS" in combat.STATS
    for name in ("LEITIS", "ELITE_LEITIS", "ELITE_LEITIS_UPGRADE"):
        assert len(train.HELP[name]) <= 50 and "LITHUANIANS" not in train.civs.MISSING[name]
        assert "BRITONS" in train.civs.MISSING[name]


def test_the_castle_of_the_lithuanians_trains_the_leitis():
    server, g = setup("LITHUANIANS", food=70, wood=0, gold=50)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:horse_spawn_egg:Leitis:70 food · 50 gold · 20 s · queue 0/15 " in menu
    assert "Elite Leitis" not in menu                                  # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, 0) == 1 and g.queues[rect][0]["name"] == "LEITIS"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Leitis" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("LITHUANIANS", food=2000, wood=0, gold=2000, ages=3)
    g.soldiers["lt"] = "LEITIS"
    g.game.entities.setdefault("lt", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert " 5:book:Elite Leitis:750 food · 750 gold · 45 s · research " in menus(server)[-1] + " "
    assert train.queue(g, "Steve", CASTLE, "ELITE_LEITIS_UPGRADE")
    train.tick(g, 45)
    assert "ELITE_LEITIS_UPGRADE" in g.techs and g.soldiers["lt"] == "ELITE_LEITIS"
    assert combat.stats_command("lt", "ELITE_LEITIS") in server.log
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:horse_spawn_egg:Elite Leitis:70 food · 50 gold · 18 s · queue 0/15 " in menu
    assert ":Leitis:" not in menu and "5:book" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_LEITIS")
    assert train.queue(g, "Steve", CASTLE, "LEITIS") is None
