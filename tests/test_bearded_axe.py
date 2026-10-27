"""Unique technology (#2044): the castle of the Franks researches Bearded Axe in the Castle Age (slot 6: 300 food,
300 gold, 60 s) with the values of the AoE2 DE wiki ("Bearded Axe"). Only the Franks have it (the key "civ" of
data/train.jsonl). Its effect: the throwing axemen get +2 range."""
from test_train_castle import menus, setup

from game import combat, train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert train.CIV_TECHS["BEARDED_AXE"] == "FRANKS"
    assert len(train.HELP["BEARDED_AXE"]) <= 50 and "FRANKS" not in train.civs.MISSING["BEARDED_AXE"]
    assert "BRITONS" in train.civs.MISSING["BEARDED_AXE"]


def test_only_the_castle_of_the_franks_researches_it():
    server, g = setup("FRANKS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert " 6:book:Bearded Axe:300 food · 300 gold · 60 s · research " in menus(server)[-1] + " "
    server, g = setup("BRITONS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert "Bearded Axe" not in menus(server)[-1]


def test_the_effect_gives_the_throwing_axemen_range():
    server, g = setup("FRANKS", food=2000, wood=0, gold=2000, ages=2)
    before = train.stats(g, "THROWING_AXEMAN")
    assert train.queue(g, "Steve", CASTLE, "BEARDED_AXE")
    train.tick(g, 60)
    assert "BEARDED_AXE" in g.techs
    assert train.stats(g, "THROWING_AXEMAN").range == before.range + 2
    assert train.stats(g, "ELITE_THROWING_AXEMAN").range == combat.stats("ELITE_THROWING_AXEMAN").range + 2
    assert train.stats(g, "ARBALESTER").range == combat.stats("ARBALESTER").range   # not a throwing axeman
