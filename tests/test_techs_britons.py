"""Yeomen (#4103): the castle of the Britons researches it in the Castle Age (slot 6: 750 wood, 450 gold, 60 s), with the
values of the AoE2 DE wiki ("Unique technology"). Only the Britons have it (the key "civ" of data/train.jsonl).
Its effects: foot archers +1 range, towers +2 attack."""
from test_train_castle import menus, setup

from game import build, train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert len(train.HELP["YEOMEN"]) <= 50 and "BRITONS" not in train.civs.MISSING["YEOMEN"]
    assert "FRANKS" in train.civs.MISSING["YEOMEN"]


def test_only_the_castle_of_the_britons_researches_it():
    server, g = setup("BRITONS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert " 6:book:Yeomen:750 wood · 450 gold · 60 s · research " in menus(server)[-1] + " "
    server, g = setup("FRANKS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert "Yeomen" not in menus(server)[-1]


def test_the_effects_change_foot_archers_and_towers_only():
    server, g = setup("BRITONS", wood=3000, gold=3000, ages=2)
    longbowman = train.stats(g, "LONGBOWMAN")
    cavalry_archer = train.stats(g, "CAVALRY_ARCHER")
    guard = build.values(g, "GUARD_TOWER")
    assert train.queue(g, "Steve", CASTLE, "YEOMEN")
    train.tick(g, 60)
    assert "YEOMEN" in g.techs
    assert train.stats(g, "LONGBOWMAN").range == longbowman.range + 1
    assert build.values(g, "GUARD_TOWER").attack == guard.attack + 2
    assert train.stats(g, "CAVALRY_ARCHER") == cavalry_archer     # mounted: no change
