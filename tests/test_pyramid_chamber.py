"""Passage and burial chamber of the Great Pyramid (#528)."""
import numpy as np
import pytest

import aoe2mc
import buildings


def draw(T):
    fn, kw = buildings.select("GREAT_PYRAMID")
    w = buildings.footprint("GREAT_PYRAMID") * T
    c = buildings.Canvas(aoe2mc.B, w, height=40)
    c.rng = np.random.default_rng(1)
    fn(c, w, buildings.ARCH["western"], "blue", T, {}, **kw)
    name = lambda x, y, z: aoe2mc.B.states[c.get(x, y, z)].removeprefix("minecraft:").split("[")[0] \
        if c.get(x, y, z) >= 0 else None
    return w, name


def test_a_passage_goes_from_the_north_face_to_the_chamber():
    w, get = draw(4)
    m, r = w // 2, w // 8
    for z in range(2, m - r):                                             # walk in: always 2 blocks of head room
        y = next(y for y in range(2, 8) if get(m, y, z) == "air")
        assert get(m, y + 1, z) == "air" and get(m - 1, y, z) == "air"
    assert get(m, r, m - 1) == "polished_blackstone" and get(m, r + 1, m) == "polished_blackstone_slab"
    assert get(m - r - 1, r + 1, m) == "polished_granite" and get(m - r, r + 3, m) == "polished_granite"
    inside = [get(x, r, z) for x in range(m - r, m + r + 1) for z in range(m - r, m + r + 1)]
    assert inside.count("gold_block") == 2 and inside.count("decorated_pot") == 2 and inside.count("lantern") == 2


@pytest.mark.parametrize("T", [1, 2, 3, 5])
def test_other_tile_sizes_draw_without_errors(T):
    draw(T)
