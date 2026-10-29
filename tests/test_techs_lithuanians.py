"""The unique technologies of the Lithuanians (#4099): Hill Forts (Castle Age) and Tower Shields (Imperial Age), with the
values of the AoE2 DE wiki ("Unique technology"). Only the Lithuanians have them (the key "civ" of data/train.jsonl)."""
from test_train_castle import menus, setup

from game import build, train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    for name in ("HILL_FORTS", "TOWER_SHIELDS"):
        assert len(train.HELP[name]) <= 50 and "LITHUANIANS" not in train.civs.MISSING[name]
        assert "BRITONS" in train.civs.MISSING[name]


def test_hill_forts_is_in_the_castle_menu_of_the_lithuanians_only():
    server, g = setup("LITHUANIANS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert " 6:book:Hill Forts:250 food · 250 gold · 40 s · research " in menus(server)[-1] + " "
    server, g = setup("BRITONS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert "Hill Forts" not in menus(server)[-1]


def test_tower_shields_is_in_the_castle_menu_of_the_lithuanians_only():
    server, g = setup("LITHUANIANS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert " 7:book:Tower Shields:500 food · 200 gold · 40 s · research " in menus(server)[-1] + " "
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Tower Shields" not in menus(server)[-1]


def test_hill_forts_adds_town_center_range():
    server, g = setup("LITHUANIANS", food=3000, gold=3000, ages=2)
    town_center = build.values(g, "TOWN_CENTER").range
    assert train.queue(g, "Steve", CASTLE, "HILL_FORTS")
    train.tick(g, 40)
    assert "HILL_FORTS" in g.techs
    assert build.values(g, "TOWN_CENTER").range == town_center + 3


def test_tower_shields_adds_pierce_armor_to_spearmen_and_skirmishers_only():
    server, g = setup("LITHUANIANS", food=3000, gold=3000, ages=3)
    pikeman = train.stats(g, "PIKEMAN").pierce
    skirmisher = train.stats(g, "ELITE_SKIRMISHER").pierce
    archer = train.stats(g, "ARCHER").pierce
    assert train.queue(g, "Steve", CASTLE, "TOWER_SHIELDS")
    train.tick(g, 40)
    assert "TOWER_SHIELDS" in g.techs
    assert train.stats(g, "PIKEMAN").pierce == pikeman + 2
    assert train.stats(g, "ELITE_SKIRMISHER").pierce == skirmisher + 2
    assert train.stats(g, "ARCHER").pierce == archer    # not a spearman or skirmisher
