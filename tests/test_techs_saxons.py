"""Clerical Recruitment of the Saxons (#4276, epic #4096): the key "convert_range" adds conversion tiles to the monks,
and the key "train_group" makes them train faster. Test data only: a monkeypatched line of the new key (the rule
modules import train by its plain name too, as tests/test_tech_effect_code.py)."""
import pytest
import train as plain_train
from test_monk_convert import setup
from test_train_castle import setup as castle

from game import monk, train

TECH = "TEST_CLERICAL"


def test_after_the_research_a_monk_converts_1_tile_farther(monkeypatch):
    for m in (train, plain_train):
        monkeypatch.setitem(m.BY_KEY["convert_range"], TECH, 1)
    reach = monk.MONKS["MONK"]
    server, g = setup(("far", "MILITIA", 2, 5.5 + reach + 1))           # 1 tile beyond the range of a monk
    assert not monk.near(g, "monk", "far", g.positions(["monk", "far"]))
    g.techs.add(TECH)
    assert monk.near(g, "monk", "far", g.positions(["monk", "far"]))
    server.entities["far"]["Pos"] = (5.5 + reach + 2, 64.0, 5.5)         # 2 tiles beyond: still too far
    assert not monk.near(g, "monk", "far", g.positions(["monk", "far"]))


def test_the_monk_trains_in_the_time_of_its_factor(monkeypatch):
    for m in (train, plain_train):
        monkeypatch.setitem(m.BY_KEY["train_group"], TECH, (["MONK"], 2))
    server, g = castle("SAXONS")
    base = train.seconds(g, "MONK")
    assert base == pytest.approx(train.TRAIN_TIMES["MONK"])            # no research: the time of the table
    g.techs.add(TECH)
    assert train.seconds(g, "MONK") == pytest.approx(base / 2)
