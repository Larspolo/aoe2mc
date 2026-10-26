"""Inside of the Svan tower and the wooden fort (#441): floors with a ladder, furniture, light, a free door."""
from collections import Counter

import numpy as np
import pytest

import aoe2mc
import buildings

FURNITURE = {"chest", "barrel", "hay_block", "cauldron", "campfire", "lantern", "grindstone"}


def draw(name, T=4):
    fn, kw = buildings.select(name)
    w = buildings.footprint(name) * T
    c = buildings.Canvas(aoe2mc.B, w, height=40)
    c.rng = np.random.default_rng(1)
    fn(c, w, buildings.ARCH["western"], "blue", T, {}, **kw)
    name = lambda x, y, z: aoe2mc.B.states[c.get(x, y, z)].removeprefix("minecraft:").split("[")[0] \
        if c.get(x, y, z) >= 0 else None
    return c, w, name


@pytest.mark.parametrize("name, light", [("SVAN_TOWER", 4), ("WOODEN_FORT", 2)])
def test_the_inside_has_furniture_light_and_a_ladder(name, light):
    c, w, get = draw(name)
    blocks = Counter(get(x, y, z) for x in range(w) for y in range(30) for z in range(w))
    assert sum(blocks[b] for b in FURNITURE) >= 5 and blocks["lantern"] + blocks["campfire"] >= light
    assert blocks["ladder"] >= 5
    x, z = next((x, w - 1 - k) for x in range(w) for k in range(w) if get(x, 1, w - 1 - k) == "spruce_door")
    assert get(x, 1, z - 1) == get(x, 2, z - 1) == "air"                 # the cell inside the door stays free


def test_each_floor_of_the_svan_tower_has_a_ladder_hole():
    c, w, get = draw("SVAN_TOWER")
    for y in (5, 9, 13):
        assert get(1, y, 1) == "ladder" and get(2, y, 2) == "spruce_planks"
