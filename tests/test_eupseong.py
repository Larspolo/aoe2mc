"""Eupseong (#2048): the castle of the Koreans researches it in the Castle Age. The guard towers and the keeps get more
range."""
from test_train_castle import setup

from game import build, train

CASTLE = (12, 4)


def test_the_effect_gives_the_towers_and_keeps_more_range():
    server, g = setup("KOREANS", food=2000, wood=2000, gold=0, ages=2)
    before = {n: build.values(g, n).range for n in ("GUARD_TOWER", "KEEP", "WATCH_TOWER")}
    assert train.queue(g, "Steve", CASTLE, "EUPSEONG")
    train.tick(g, train.TRAIN_TIMES["EUPSEONG"])
    assert "EUPSEONG" in g.techs
    assert build.values(g, "GUARD_TOWER").range > before["GUARD_TOWER"]
    assert build.values(g, "KEEP").range > before["KEEP"]
    assert build.values(g, "WATCH_TOWER").range == before["WATCH_TOWER"]     # not a guard tower or keep
