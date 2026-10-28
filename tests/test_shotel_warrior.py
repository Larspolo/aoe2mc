"""Shotel Warrior (#1725): the castle of the Ethiopians trains the shotel warrior (50 food, 30 gold, 8 s) and
researches Elite Shotel Warrior in the Imperial Age (slot 5: 900 food, 450 gold, 45 s), with the values of the AoE2 DE
wiki infobox "Shotel Warrior (Age of Empires II)". The elite unit trains in 4 s. The upgrade changes the live and the new units."""
from test_train_castle import menus, setup

from game import combat, train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert "SHOTEL_WARRIOR" in combat.STATS and "ELITE_SHOTEL_WARRIOR" in combat.STATS
    for name in ("SHOTEL_WARRIOR", "ELITE_SHOTEL_WARRIOR", "ELITE_SHOTEL_WARRIOR_UPGRADE"):
        assert len(train.HELP[name]) <= 50 and "ETHIOPIANS" not in train.civs.MISSING[name]
        assert "BRITONS" in train.civs.MISSING[name]


def test_the_castle_of_the_ethiopians_trains_the_shotel_warrior():
    server, g = setup("ETHIOPIANS", food=50, wood=0, gold=30)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:husk_spawn_egg:Shotel Warrior:50 food · 30 gold · 8 s · queue 0/15 " in menu
    assert "Elite Shotel" not in menu                                  # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, 0) == 1 and g.queues[rect][0]["name"] == "SHOTEL_WARRIOR"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Shotel" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("ETHIOPIANS", food=2000, wood=0, gold=2000, ages=3)
    g.soldiers["sw"] = "SHOTEL_WARRIOR"
    g.game.entities.setdefault("sw", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert " 5:book:Elite Shotel Warrior:900 food · 450 gold · 45 s · research " in menus(server)[-1] + " "
    assert train.queue(g, "Steve", CASTLE, "ELITE_SHOTEL_WARRIOR_UPGRADE")
    train.tick(g, 45)
    assert "ELITE_SHOTEL_WARRIOR_UPGRADE" in g.techs and g.soldiers["sw"] == "ELITE_SHOTEL_WARRIOR"
    assert combat.stats_command("sw", "ELITE_SHOTEL_WARRIOR") in server.log
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:husk_spawn_egg:Elite Shotel Warrior:50 food · 30 gold · 4 s · queue 0/15 " in menu
    assert ":Shotel Warrior:" not in menu and "5:book" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_SHOTEL_WARRIOR")
    assert train.queue(g, "Steve", CASTLE, "SHOTEL_WARRIOR") is None
