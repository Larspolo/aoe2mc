"""Serjeant (#1748): the castle of the Sicilians trains the Serjeant (55 food, 25 gold, 12 s) and researches Elite Serjeant in the
Imperial Age (slot 5: 800 food, 675 gold, 45 s), with the values of the AoE2 DE wiki. The upgrade changes the live
and the new units."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    for name in ("SERJEANT", "ELITE_SERJEANT", "ELITE_SERJEANT_UPGRADE"):
        assert len(train.HELP[name]) <= 50 and "SICILIANS" not in train.civs.MISSING[name]
        assert "BRITONS" in train.civs.MISSING[name]


def test_the_castle_of_the_huns_trains_the_serjeant():
    server, g = setup("SICILIANS", food=55, wood=0, gold=25)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:zombie_spawn_egg:Serjeant:55 food · 25 gold · 12 s · queue 0/15 " in menu
    assert "Elite Serjeant" not in menu                                  # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, 0) == 1 and g.queues[rect][0]["name"] == "SERJEANT"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Serjeant" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("SICILIANS", food=2000, wood=0, gold=2000, ages=3)
    g.soldiers["se"] = "SERJEANT"
    g.game.entities.setdefault("se", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert " 5:book:Elite Serjeant:800 food · 675 gold · 45 s · research " in menus(server)[-1] + " "
    assert train.queue(g, "Steve", CASTLE, "ELITE_SERJEANT_UPGRADE")
    train.tick(g, 45)
    assert "ELITE_SERJEANT_UPGRADE" in g.techs and g.soldiers["se"] == "ELITE_SERJEANT"
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:zombie_spawn_egg:Elite Serjeant:55 food · 25 gold · 12 s · queue 0/15 " in menu
    assert ":Serjeant:" not in menu and "5:book" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_SERJEANT")
    assert train.queue(g, "Steve", CASTLE, "SERJEANT") is None
