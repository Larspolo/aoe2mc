"""The key "convert_resist" (#4449, Antiquity Mode Macedonians): the units of a civilization with the factor f are f
times harder to convert: the mean conversion time is about f times as long. Test data only: a monkeypatched line."""
import civs as plain_civs
import pytest
from test_monk_convert import setup, until_converted

from game import civs, monk

CIV = "TEST_RESISTANT"


def mean(civ, seeds=300):
    """The mean AoE2 seconds until the monk of player 1 converts a militia of player 2 of civ."""
    total = 0.0
    for seed in range(seeds):
        server, g = setup(("foe", "MILITIA", 2, 12.5))
        g.data.setdefault("players", {})["2"] = {"civ": civ}
        g.chance.seed(seed)
        assert monk.convert_order(g, {"monk"}, "foe")
        total += until_converted(g, "foe", limit=200)
        assert "foe" not in g.enemies
    return total / seeds


def test_a_unit_of_the_civilization_converts_4_times_slower(monkeypatch):
    for m in (civs, plain_civs):
        monkeypatch.setitem(m.BY_KEY["convert_resist"], CIV, 4)
    assert mean(CIV) / mean("BRITONS") == pytest.approx(4, rel=0.1)
