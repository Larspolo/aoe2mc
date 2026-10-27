"""Garland Wars (#2042): the castle of the Aztecs researches it in the Imperial Age (slot 7: 450 food, 750 gold,
60 s), with the values of the AoE2 DE wiki ("Garland Wars"). Infantry get +4 attack. Only the Aztecs have it (the
key "civ" of data/train.jsonl)."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert train.CIV_TECHS["GARLAND_WARS"] == "AZTECS"
    assert train.COSTS["GARLAND_WARS"] == {"food": 450, "gold": 750} and train.TRAIN_TIMES["GARLAND_WARS"] == 60
    assert train.TECH_AGE["GARLAND_WARS"] == 3
    assert len(train.HELP["GARLAND_WARS"]) <= 50 and "AZTECS" not in train.civs.MISSING["GARLAND_WARS"]
    assert "BRITONS" in train.civs.MISSING["GARLAND_WARS"]


def test_only_the_castle_of_the_aztecs_researches_it():
    server, g = setup("AZTECS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert " 7:book:Garland Wars:450 food · 750 gold · 60 s · research " in menus(server)[-1] + " "
    server, g = setup("AZTECS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert "Garland Wars" not in menus(server)[-1]
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Garland Wars" not in menus(server)[-1]


def test_the_effect_changes_infantry_only():
    server, g = setup("AZTECS", food=2000, wood=0, gold=2000, ages=3)
    before = train.stats(g, "MILITIA")
    archer = train.stats(g, "ARCHER")
    assert train.queue(g, "Steve", CASTLE, "GARLAND_WARS")
    train.tick(g, 60)
    assert "GARLAND_WARS" in g.techs
    assert train.stats(g, "MILITIA").attack == before.attack + 4
    assert train.stats(g, "ARCHER").attack == archer.attack
