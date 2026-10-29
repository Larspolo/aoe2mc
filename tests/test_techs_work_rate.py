"""The key "work" of a technology: the factor of the work rate of one building (Perfusion, Chivalry, #4226). Test data,
not the data lines (owner, 2026-10-29, #4242)."""
from test_train_castle import setup

import pytest
from game import train


def test_a_researched_technology_makes_its_building_work_faster(monkeypatch):
    monkeypatch.setitem(train.BY_KEY["work"], "TEST_BARRACKS", ("BARRACKS", 2))
    monkeypatch.setitem(train.BY_KEY["work"], "TEST_STABLE", ("STABLE", 1.4))
    server, g = setup("BRITONS", ages=3)
    militia, archer, knight = (train.seconds(g, n, b) for n, b in
                               (("MILITIA", "BARRACKS"), ("ARCHER", "ARCHERY_RANGE"), ("KNIGHT", "STABLE")))
    g.techs.add("TEST_BARRACKS")
    assert train.seconds(g, "MILITIA", "BARRACKS") == pytest.approx(militia / 2)
    assert train.seconds(g, "ARCHER", "ARCHERY_RANGE") == pytest.approx(archer)      # another building
    assert train.seconds(g, "KNIGHT", "STABLE") == pytest.approx(knight)
    g.techs.add("TEST_STABLE")
    assert train.seconds(g, "KNIGHT", "STABLE") == pytest.approx(knight / 1.4)
