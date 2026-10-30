"""The key "population" of a unit group (Mahayana, Aznauri Cavalry, #4256): train.weight takes the units as "walk"
(train.faster). Test data: monkeypatched train.BY_KEY lines, not the values of the data lines (owner, #4242)."""
import pytest
import train as plain_train  # gather imports train by its plain name (not game.train)
from test_train_castle import setup

from game import train


@pytest.fixture
def techs(monkeypatch):
    for m in (train, plain_train):
        monkeypatch.setitem(m.BY_KEY["population"], "TEST_MONKS", [["villagers", "monks"], 0.9])
        monkeypatch.setitem(m.BY_KEY["population"], "TEST_CAVALRY", ["cavalry", 0.8])


def test_a_technology_lowers_the_population_of_its_group(techs):
    server, g = setup("BENGALIS")
    assert train.weight(g, "VILLAGER") == train.weight(g, None) == 1
    g.techs.add("TEST_MONKS")
    for name in ("VILLAGER", None, "MONK"):
        assert train.weight(g, name) == pytest.approx(0.9), name
    assert train.weight(g, "MILITIA") == train.weight(g, "KNIGHT") == 1
    g.techs.add("TEST_CAVALRY")
    assert train.weight(g, "KNIGHT") == pytest.approx(0.8) and train.weight(g, "MILITIA") == 1


def test_the_live_population_counts_the_lower_weight(techs, monkeypatch):
    server, g = setup("BENGALIS")
    g.villagers.clear(), g.soldiers.clear()
    g.villagers.update({f"v{i}": None for i in range(10)})
    monkeypatch.setattr(g, "positions", lambda uuids: {u: (0.0, 64.0, 0.0) for u in uuids})
    train.census(g)
    assert g.pop == pytest.approx(10)
    g.techs.add("TEST_MONKS")
    train.census(g)
    assert g.pop == pytest.approx(9)
