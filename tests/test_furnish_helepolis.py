"""Inside of the Helepolis (#501): a mast with a ladder through all floors, arrow barrels, light, a windlass."""
from collections import Counter

import numpy as np
import pytest

import aoe2mc
import buildings


def draw(T):
    fn, kw = buildings.select("HELEPOLIS")
    w = buildings.footprint("HELEPOLIS") * T
    c = buildings.Canvas(aoe2mc.B, w, height=40)
    c.rng = np.random.default_rng(1)
    fn(c, w, buildings.ARCH["western"], "blue", T, {}, **kw)
    name = lambda x, y, z: aoe2mc.B.states[c.get(x, y, z)].removeprefix("minecraft:").split("[")[0] \
        if c.get(x, y, z) >= 0 else None
    return w, name


def test_the_inside_has_furniture_light_and_a_ladder():
    w, get = draw(4)
    blocks = Counter(get(x, y, z) for x in range(w) for y in range(40) for z in range(w))
    assert blocks["barrel"] >= 4 and blocks["lantern"] >= 4 and blocks["grindstone"] == 1 and blocks["chest"] == 1
    m = w // 2
    ys = [y for y in range(40) if get(m, y, m - 1) == "ladder"]
    assert ys == list(range(ys[0], ys[0] + len(ys))) and len(ys) >= 12   # one ladder from the ground to the top
    assert all(get(m, y, m) == "spruce_log" for y in ys)                  # on the mast


@pytest.mark.parametrize("T", [1, 2, 3, 5])
def test_other_tile_sizes_draw_without_errors(T):
    draw(T)
