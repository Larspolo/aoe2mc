"""The unique technologies of the Lithuanians (#4099): Hill Forts (Castle Age) and Tower Shields (Imperial Age), with the
values of the AoE2 DE wiki ("Unique technology"). Only the Lithuanians have them (the key "civ" of data/train.jsonl)."""
from test_train_castle import menus, setup

from game import build, train

CASTLE = (12, 4)


def label(g, name):
    """The label of name in the castle menu of g, or None."""
    return train.layout(g, train.home(g, CASTLE)).get(name, (None, None, None))[2]


def test_hill_forts_is_in_the_castle_menu_of_the_lithuanians_only():
    server, g = setup("LITHUANIANS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label(g, 'HILL_FORTS')}:" in menus(server)[-1]
    server, g = setup("BRITONS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert label(g, "HILL_FORTS") is None


def test_tower_shields_is_in_the_castle_menu_of_the_lithuanians_only():
    server, g = setup("LITHUANIANS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label(g, 'TOWER_SHIELDS')}:" in menus(server)[-1]
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert label(g, "TOWER_SHIELDS") is None


def test_hill_forts_adds_town_center_range():
    server, g = setup("LITHUANIANS", food=3000, wood=3000, gold=3000, ages=2)
    town_center = build.values(g, "TOWN_CENTER").range
    assert train.queue(g, "Steve", CASTLE, "HILL_FORTS")
    train.tick(g, train.seconds(g, "HILL_FORTS", "CASTLE"))
    assert "HILL_FORTS" in g.techs
    assert build.values(g, "TOWN_CENTER").range > town_center


def test_tower_shields_adds_pierce_armor_to_spearmen_and_skirmishers_only():
    server, g = setup("LITHUANIANS", food=3000, wood=3000, gold=3000, ages=3)
    pikeman = train.stats(g, "PIKEMAN").pierce
    skirmisher = train.stats(g, "ELITE_SKIRMISHER").pierce
    archer = train.stats(g, "ARCHER").pierce
    assert train.queue(g, "Steve", CASTLE, "TOWER_SHIELDS")
    train.tick(g, train.seconds(g, "TOWER_SHIELDS", "CASTLE"))
    assert "TOWER_SHIELDS" in g.techs
    assert train.stats(g, "PIKEMAN").pierce > pikeman
    assert train.stats(g, "ELITE_SKIRMISHER").pierce > skirmisher
    assert train.stats(g, "ARCHER").pierce == archer    # not a spearman or skirmisher
