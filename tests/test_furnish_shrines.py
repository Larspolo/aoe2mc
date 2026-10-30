"""The shrine and the pagan shrine are furnished (#450)."""
from collections import Counter

import mcvalid
import pytest
from test_furnish_landmarks import blocks

import aoe2mc

NEEDS = {"SHRINE": ("gold_block", "candle", "blue_carpet", "potted_poppy", "lantern"),
         "PAGAN_SHRINE": ("mossy_cobblestone", "skeleton_skull", "campfire", "candle", "lantern")}


@pytest.mark.parametrize("arch", ["western", "east_asian", "middle_eastern"])
@pytest.mark.parametrize("name", sorted(NEEDS))
def test_shrine_is_furnished(name, arch):
    last = blocks(name, arch)
    names = Counter(s.split("[")[0] for s in last.values())
    assert all(names[n] >= 1 for n in NEEDS[name]), (name, arch, {n: names[n] for n in NEEDS[name]})
    assert mcvalid.invalid_states(aoe2mc.B.states) == {}


def test_shrine_entrance_stays_free():
    last = blocks("SHRINE", "western")
    (gx, gy, gz), = [p for p, s in last.items() if s == "gold_block" and last.get((p[0], p[1] - 1, p[2])) == "chiseled_sandstone"]
    for x in (gx - 1, gx):                               # the opening in the south wall, and the rows at it
        for z in (gz + 3, gz + 4, gz + 5):
            s = last.get((x, gy - 1, z), "air")
            assert s in ("air", "barrier") or s.endswith("_carpet"), (x, z, s)


@pytest.mark.parametrize("tile", [1, 2, 3])
@pytest.mark.parametrize("name", sorted(NEEDS))
def test_small_tile_sizes_work(name, tile):
    blocks(name, "western", tile)
