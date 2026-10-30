"""The key "keep_housing" of a technology (Nomads of the Mongols, #4280): an own building of its names that falls after
the research keeps its population room (train.limit). Test data, not the data line (owner, 2026-10-29, #4242)."""
import train as plain_train  # ruins.fall imports train by its plain name (not game.train)
from test_own_building_fall import HOUSE, ROOM
from test_train_population import setup as town

from game import ruins, train


def test_a_house_that_falls_after_the_research_keeps_its_population_room(monkeypatch):
    monkeypatch.setitem(plain_train.BY_KEY["keep_housing"], "TEST_TECH", ["HOUSE"])
    server, g = town(houses=1)
    g.techs.add("TEST_TECH")
    before = train.limit(g)
    assert "HOUSE" in train.owned(g)
    ruins.fall(g, HOUSE)
    assert "HOUSE" not in train.owned(g)
    assert train.limit(g) == before


def test_with_no_research_a_house_that_falls_takes_its_population_room(monkeypatch):
    monkeypatch.setitem(plain_train.BY_KEY["keep_housing"], "TEST_TECH", ["HOUSE"])
    server, g = town(houses=1)
    before = train.limit(g)
    assert "HOUSE" in train.owned(g)
    ruins.fall(g, HOUSE)
    assert train.limit(g) == before - ROOM[1]
