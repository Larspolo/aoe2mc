"""Arambai (#1751): the castle of the Burmese trains the Arambai (75 wood, 60 gold, 18 s) and researches Elite Arambai in
the Imperial Age (slot 5: 1000 food, 750 gold, 65 s), with the values of the AoE2 DE wiki. The upgrade changes the live
and the new units."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    for name in ("ARAMBAI", "ELITE_ARAMBAI", "ELITE_ARAMBAI_UPGRADE"):
        assert len(train.HELP[name]) <= 50 and "BURMESE" not in train.civs.MISSING[name]
        assert "BRITONS" in train.civs.MISSING[name]


def test_the_castle_of_the_burmese_trains_the_arambai():
    server, g = setup("BURMESE", wood=75, gold=60)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:skeleton_horse_spawn_egg:Arambai:75 wood · 60 gold · 18 s · queue 0/15 " in menu
    assert "Elite Arambai" not in menu                                 # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, 0) == 1 and g.queues[rect][0]["name"] == "ARAMBAI"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Arambai" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("BURMESE", food=2000, wood=75, gold=2000, ages=3)
    g.soldiers["ar"] = "ARAMBAI"
    g.game.entities.setdefault("ar", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert " 5:book:Elite Arambai:1000 food · 750 gold · 65 s · research " in menus(server)[-1] + " "
    assert train.queue(g, "Steve", CASTLE, "ELITE_ARAMBAI_UPGRADE")
    train.tick(g, 65)
    assert "ELITE_ARAMBAI_UPGRADE" in g.techs and g.soldiers["ar"] == "ELITE_ARAMBAI"
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:skeleton_horse_spawn_egg:Elite Arambai:75 wood · 60 gold · 18 s · queue 0/15 " in menu
    assert ":Arambai:" not in menu and "5:book" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_ARAMBAI")
    assert train.queue(g, "Steve", CASTLE, "ARAMBAI") is None
