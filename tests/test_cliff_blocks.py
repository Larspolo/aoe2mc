"""Desert and snow cliffs have their own rocks (#4115)."""
import numpy as np
import pytest
from mcvalid import block_error

import aoe2mc

T, H = 4, 3
DEFAULT = {"stone", "andesite", "tuff", "cobblestone", "mossy_cobblestone"}


def cliff(name):
    n = 16
    cols = aoe2mc.Columns(n, np.zeros((n, n), np.int16), np.zeros((n, n), np.float32), {0: "GRASS"}, T, H,
                          np.random.default_rng(1))
    o = dict(kind="O", name=name, player=0, x=8.0, y=8.0, rotation=0.0, hero=False, garrisoned=False)
    E, _ = aoe2mc.place_objects([o], {}, cols, np.random.default_rng(1))
    x, y, z, ids, _ = (np.concatenate(p) for p in zip(*E.parts))
    return cols, {(int(a), int(b), int(c)): aoe2mc.B.states[i].removeprefix("minecraft:") for a, b, c, i in zip(x, y, z, ids)}


def rocks(blocks):
    return {b for b in blocks.values() if b != "barrier" and not b.startswith("snow[")}


@pytest.mark.parametrize("name", ["CLIFF_DESERT", "CLIFF_SNOW"])
def test_own_rocks(name):
    own = set(aoe2mc.OBJECT[name]["rocks"])
    assert rocks(cliff(name)[1]) and rocks(cliff(name)[1]) <= own
    assert all(block_error(b) is None for b in own | {"snow[layers=2]"})


def test_default_cliff_keeps_its_rocks():
    assert rocks(cliff("CLIFF_DEFAULT")[1]) <= DEFAULT


def test_snow_on_top_of_each_snow_rock_column():
    _, blocks = cliff("CLIFF_SNOW")
    tops = {}
    for (x, y, z), b in blocks.items():
        if b != "barrier":
            tops[x, z] = max(tops.get((x, z), -1), y)
    for (x, z), y in tops.items():
        assert blocks[(x, y, z)] == "snow[layers=2]"
