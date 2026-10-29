"""Farimba (#2046): the castle of the Malians researches it in the Imperial Age. Its effect: more attack for the
cavalry."""
from test_train_castle import setup

from game import train

CASTLE = (12, 4)


def test_the_effect_adds_attack_to_cavalry_only():
    server, g = setup("MALIANS", food=2000, wood=0, gold=2000, ages=3)
    knight = train.stats(g, "KNIGHT")
    militia = train.stats(g, "MILITIA")
    assert train.queue(g, "Steve", CASTLE, "FARIMBA")
    train.tick(g, train.TRAIN_TIMES["FARIMBA"])
    assert "FARIMBA" in g.techs
    assert train.stats(g, "KNIGHT").attack > knight.attack
    assert train.stats(g, "MILITIA").attack == militia.attack     # not cavalry
