"""Unique technologies with a walk list (#4254): Drill (the Mongols, Imperial Age) makes the units of the Siege Workshop
walk 50 % faster; Herbalism (the Muisca, Castle Age) makes the archer line, the Champi Scouts and the Xolotl Warriors
walk 15 % faster (AoE2 DE wiki "Unique technology"). The castle menu shows each one only for its civilization."""
import pytest
from test_techs_turks import CASTLE, label
from test_train_castle import setup

from game import train


def research(civ, ages, name):
    """The game of civ after the castle researched name (the stock pays it)."""
    server, g = setup(civ, food=3000, wood=3000, gold=3000, ages=ages)
    assert train.queue(g, "Steve", CASTLE, name)
    train.tick(g, train.seconds(g, name, "CASTLE"))
    assert name in g.techs
    return g


def test_only_the_castle_of_the_mongols_researches_drill():
    server, g = setup("MONGOLS", ages=3)
    assert label(g, "DRILL") is not None
    server, g = setup("BRITONS", ages=3)
    assert label(g, "DRILL") is None


def test_only_the_castle_of_the_muisca_researches_herbalism():
    server, g = setup("MUISCA", ages=2)
    assert label(g, "HERBALISM") is not None
    server, g = setup("BRITONS", ages=2)
    assert label(g, "HERBALISM") is None


def test_drill_makes_the_siege_workshop_units_walk_faster():
    _, before = setup("MONGOLS", ages=3)
    ram, trebuchet, archer = (train.speed(before, n) for n in ("BATTERING_RAM", "TREBUCHET", "ARCHER"))
    g = research("MONGOLS", 3, "DRILL")
    assert train.speed(g, "BATTERING_RAM") == pytest.approx(ram * 1.5)
    assert train.speed(g, "TREBUCHET") == pytest.approx(trebuchet)     # trained by the castle, not the workshop
    assert train.speed(g, "ARCHER") == pytest.approx(archer)


def test_herbalism_makes_the_archer_line_and_xolotls_walk_faster():
    _, before = setup("MUISCA", ages=2)
    names = ("ARCHER", "CROSSBOWMAN", "XOLOTL_WARRIOR", "SKIRMISHER")
    speeds = {n: train.speed(before, n) for n in names}
    g = research("MUISCA", 2, "HERBALISM")
    for n in ("ARCHER", "CROSSBOWMAN", "XOLOTL_WARRIOR"):
        assert train.speed(g, n) == pytest.approx(speeds[n] * 1.15), n
    assert train.speed(g, "SKIRMISHER") == pytest.approx(speeds["SKIRMISHER"])
