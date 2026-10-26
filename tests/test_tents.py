"""Tents like the game models (#454): round large and square small army tents, a Greek ridge tent, nomad hide tents."""
import numpy as np
import pytest

import aoe2mc
import buildings


def draw(name, T=4):
    fn, kw = buildings.select(name)
    w = buildings.footprint(name) * T
    c = buildings.Canvas(aoe2mc.B, w, height=20)
    c.rng = np.random.default_rng(1)
    fn(c, w, buildings.ARCH["western"], "blue", T, {"name": name}, **kw)
    return w, lambda x, y, z: aoe2mc.B.states[c.get(x, y, z)].removeprefix("minecraft:").split("[")[0] \
        if c.get(x, y, z) >= 0 else None


@pytest.mark.parametrize("name, corner, cloth", [("ARMY_TENT_A", None, "blue_wool"), ("ARMY_TENT_E", None, "blue_wool"),
                                                 ("ARMY_TENT_B", "stripped_spruce_log", "white_wool"),
                                                 ("ARMY_TENT_F", "stripped_spruce_log", "white_wool"),
                                                 ("TENT_C", None, "brown_wool")])
def test_the_tent_shapes(name, corner, cloth):
    w, get = draw(name)
    assert get(0, 1, 0) is None if corner is None else get(1, 1, 1) == corner   # round: free corners; pavilion: poles
    assert get(0, 1, w // 2) == cloth or get(1, 1, w // 2) == cloth
    m = w // 2
    assert get(m, 1, w - 1) in (None, "air") and get(m, 1, w - 2) == get(m, 2, w - 2) == "air"   # the door: south


def test_the_greek_tent_has_a_ridge_from_north_to_south():
    w, get = draw("GREEK_ARMY_TENT")
    top = (w + 1) // 2
    assert all(get(w // 2 - 1, top, z) == "white_wool" for z in range(w - 1))
    assert get(w // 2, 1, w - 2) == "air"
