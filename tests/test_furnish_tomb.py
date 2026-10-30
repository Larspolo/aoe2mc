"""The Mesopotamian tomb has a burial room (#497)."""
from collections import Counter

import mcvalid
import pytest
from test_furnish_landmarks import blocks

import aoe2mc

NEEDS = ("smooth_stone", "candle", "decorated_pot", "red_carpet")


@pytest.mark.parametrize("arch", ["western", "middle_eastern"])
def test_tomb_is_furnished(arch):
    last = blocks("MESOPOTAMIAN_TOMB", arch)
    names = Counter(s.split("[")[0] for s in last.values())
    assert all(names[n] >= 1 for n in NEEDS), {n: names[n] for n in NEEDS}
    assert mcvalid.invalid_states(aoe2mc.B.states) == {}


def test_tomb_door_stays_free():
    last = blocks("MESOPOTAMIAN_TOMB", "western")
    (dx, dy, dz), = [p for p, s in last.items() if s.startswith("spruce_door") and "half=lower" in s]
    for x in (dx - 1, dx, dx + 1):                       # the cells inside the door: only the rug
        for y in (dy, dy + 1):
            s = last.get((x, y, dz - 1), "air")
            assert s in ("air", "barrier", "red_carpet") or "mud_brick" in s, (x, y, s)


@pytest.mark.parametrize("tile", [1, 2, 3])
def test_small_tile_sizes_work(tile):
    blocks("MESOPOTAMIAN_TOMB", "western", tile)
