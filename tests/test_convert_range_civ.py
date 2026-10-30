"""game/monk.py: the conversion range of a civilization by age (the key "convert_range", Egyptian priests +2/+3, #4447).
Test data only: a monkeypatched line of civs.BY_KEY for the civilization of the test, and the age techs of each age.
The rule modules import civs by its plain name too, so the line is patched in both (as tests/test_techs_saxons.py)."""
import pytest
import civs as plain_civs
from test_monk_convert import setup

from game import build, civs, monk


@pytest.mark.parametrize("age, tiles", [(0, 0), (1, 0), (2, 2), (3, 3)])
def test_a_civilization_converts_farther_in_the_castle_and_imperial_age(monkeypatch, age, tiles):
    reach = monk.MONKS["MONK"]
    server, g = setup(("far", "MILITIA", 2, 5.5 + reach + tiles))         # at the edge of the range of its age
    for m in (civs, plain_civs):
        monkeypatch.setitem(m.BY_KEY["convert_range"], civs.civ(g), (0, 0, 2, 3))
    g.techs.update(build.AGE_TECHS[:age])
    assert monk.near(g, "monk", "far", g.positions(["monk", "far"]))
    server.entities["far"]["Pos"] = (5.5 + reach + tiles + 1, 64.0, 5.5)   # 1 tile beyond: too far
    assert not monk.near(g, "monk", "far", g.positions(["monk", "far"]))
