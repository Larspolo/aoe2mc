"""Eupseong (#2048): the castle of the Koreans researches it in the Castle Age (slot 6: 300 food, 300 wood, 40 s), with
the values of the AoE2 DE wiki ("Eupseong"). The guard towers and the keeps get +2 range. Only the Koreans have it (the
key "civ" of data/train.jsonl)."""
from test_train_castle import menus, setup

from game import build, train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert train.CIV_TECHS["EUPSEONG"] == "KOREANS"
    assert len(train.HELP["EUPSEONG"]) <= 50 and "KOREANS" not in train.civs.MISSING["EUPSEONG"]
    assert "BRITONS" in train.civs.MISSING["EUPSEONG"]


def test_only_the_castle_of_the_koreans_researches_it():
    server, g = setup("KOREANS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert " 6:book:Eupseong:300 food · 300 wood · 40 s · research " in menus(server)[-1] + " "
    server, g = setup("BRITONS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert "Eupseong" not in menus(server)[-1]


def test_the_effect_gives_the_towers_and_keeps_more_range():
    server, g = setup("KOREANS", food=2000, wood=2000, gold=0, ages=2)
    before = {n: build.values(g, n).range for n in ("GUARD_TOWER", "KEEP", "WATCH_TOWER")}
    assert train.queue(g, "Steve", CASTLE, "EUPSEONG")
    train.tick(g, 40)
    assert "EUPSEONG" in g.techs
    assert build.values(g, "GUARD_TOWER").range == before["GUARD_TOWER"] + 2
    assert build.values(g, "KEEP").range == before["KEEP"] + 2
    assert build.values(g, "WATCH_TOWER").range == before["WATCH_TOWER"]     # not a guard tower or keep
