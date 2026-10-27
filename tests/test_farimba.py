"""Farimba (#2046): the castle of the Malians researches it in the Imperial Age (slot 7: 650 food, 400 gold, 40 s),
with the values of the AoE2 DE wiki ("Farimba"). Only the Malians have it (the key "civ" of data/train.jsonl).
Its effect: cavalry +5 attack."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert len(train.HELP["FARIMBA"]) <= 50 and "MALIANS" not in train.civs.MISSING["FARIMBA"]
    assert "BRITONS" in train.civs.MISSING["FARIMBA"]


def test_only_the_castle_of_the_malians_researches_it():
    server, g = setup("MALIANS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert " 7:book:Farimba:650 food · 400 gold · 40 s · research " in menus(server)[-1] + " "
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Farimba" not in menus(server)[-1]


def test_the_effect_adds_attack_to_cavalry_only():
    server, g = setup("MALIANS", food=2000, wood=0, gold=2000, ages=3)
    knight = train.stats(g, "KNIGHT")
    militia = train.stats(g, "MILITIA")
    assert train.queue(g, "Steve", CASTLE, "FARIMBA")
    train.tick(g, 40)
    assert "FARIMBA" in g.techs
    assert train.stats(g, "KNIGHT").attack == knight.attack + 5
    assert train.stats(g, "MILITIA").attack == militia.attack     # not cavalry
