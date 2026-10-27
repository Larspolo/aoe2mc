"""Unique technology of the Aztecs (#2041): the castle of the Aztecs researches Atlatl in the Castle Age (slot 6:
400 food, 350 gold, 40 s), with the values of the AoE2 DE wiki ("Atlatl"). Skirmishers get +1 attack and +1 range.
Only the Aztecs have it (the key "civ" of data/train.jsonl)."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert train.CIV_TECHS["ATLATL"] == "AZTECS"
    assert train.COSTS["ATLATL"] == {"food": 400, "gold": 350} and train.TRAIN_TIMES["ATLATL"] == 40
    assert train.TECH_AGE["ATLATL"] == 2
    assert len(train.HELP["ATLATL"]) <= 50 and "AZTECS" not in train.civs.MISSING["ATLATL"]
    assert "BRITONS" in train.civs.MISSING["ATLATL"]


def test_only_the_castle_of_the_aztecs_researches_it():
    server, g = setup("AZTECS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert " 6:book:Atlatl:400 food · 350 gold · 40 s · research " in menus(server)[-1] + " "
    server, g = setup("BRITONS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert "Atlatl" not in menus(server)[-1]


def test_the_effect_gives_the_skirmishers_one_more_attack_and_range():
    server, g = setup("AZTECS", food=2000, wood=0, gold=2000, ages=2)
    before, arb = train.stats(g, "SKIRMISHER"), train.stats(g, "ARBALESTER")
    assert train.queue(g, "Steve", CASTLE, "ATLATL")
    train.tick(g, 40)
    assert "ATLATL" in g.techs
    after = train.stats(g, "SKIRMISHER")
    assert after.attack == before.attack + 1 and after.range == before.range + 1
    assert train.stats(g, "ARBALESTER") == arb                                 # not skirmishers: no change
