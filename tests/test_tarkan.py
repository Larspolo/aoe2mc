"""Tarkan (#1726): the castle of the Huns trains the Tarkan (60 food, 60 gold, 14 s) and researches Elite Tarkan in the
Imperial Age (slot 5: 1000 food, 500 gold, 45 s), with the values of the AoE2 DE wiki. The upgrade changes the live
and the new units."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    for name in ("TARKAN", "ELITE_TARKAN", "ELITE_TARKAN_UPGRADE"):
        assert len(train.HELP[name]) <= 50 and "HUNS" not in train.civs.MISSING[name]
        assert "BRITONS" in train.civs.MISSING[name]


def test_the_castle_of_the_huns_trains_the_tarkan():
    server, g = setup("HUNS", food=60, wood=0, gold=60)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:horse_spawn_egg:Tarkan:60 food · 60 gold · 14 s · queue 0/15 " in menu
    assert "Elite Tarkan" not in menu                                  # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, 0) == 1 and g.queues[rect][0]["name"] == "TARKAN"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Tarkan" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("HUNS", food=2000, wood=0, gold=2000, ages=3)
    g.soldiers["ta"] = "TARKAN"
    g.game.entities.setdefault("ta", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert " 5:book:Elite Tarkan:1000 food · 500 gold · 45 s · research " in menus(server)[-1] + " "
    assert train.queue(g, "Steve", CASTLE, "ELITE_TARKAN_UPGRADE")
    train.tick(g, 45)
    assert "ELITE_TARKAN_UPGRADE" in g.techs and g.soldiers["ta"] == "ELITE_TARKAN"
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:horse_spawn_egg:Elite Tarkan:60 food · 60 gold · 14 s · queue 0/15 " in menu
    assert ":Tarkan:" not in menu and "5:book" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_TARKAN")
    assert train.queue(g, "Steve", CASTLE, "TARKAN") is None
