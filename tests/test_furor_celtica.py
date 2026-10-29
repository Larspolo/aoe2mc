"""Furor Celtica (#2043): the castle of the Celts researches it in the Imperial Age. Siege weapons get more hit
points."""
from test_train_castle import setup

from game import train

CASTLE = (12, 4)


def test_siege_weapons_get_more_hit_points():
    server, g = setup("CELTS", food=800, wood=0, gold=500, ages=3)
    before, other = train.stats(g, "MANGONEL").hp, train.stats(g, "ARAMBAI").hp
    assert train.queue(g, "Steve", CASTLE, "FUROR_CELTICA")
    train.tick(g, train.TRAIN_TIMES["FUROR_CELTICA"])
    assert "FUROR_CELTICA" in g.techs
    assert train.stats(g, "MANGONEL").hp > before
    assert train.stats(g, "ARAMBAI").hp == other                 # not siege: unchanged
