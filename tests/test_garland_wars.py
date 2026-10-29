"""Garland Wars (#2042): the castle of the Aztecs researches it in the Imperial Age. Infantry get more attack."""
from test_train_castle import setup

from game import train

CASTLE = (12, 4)


def test_the_effect_changes_infantry_only():
    server, g = setup("AZTECS", food=2000, wood=0, gold=2000, ages=3)
    before = train.stats(g, "MILITIA")
    archer = train.stats(g, "ARCHER")
    assert train.queue(g, "Steve", CASTLE, "GARLAND_WARS")
    train.tick(g, train.TRAIN_TIMES["GARLAND_WARS"])
    assert "GARLAND_WARS" in g.techs
    assert train.stats(g, "MILITIA").attack > before.attack
    assert train.stats(g, "ARCHER").attack == archer.attack
