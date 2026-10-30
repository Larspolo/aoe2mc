"""The rekha deul temple has a sanctum with an idol behind its porch (#499)."""
from collections import Counter

import mcvalid
import pytest
from test_furnish_landmarks import blocks

import aoe2mc

NEEDS = ("gold_block", "chiseled_cinnabar", "candle", "orange_carpet", "potted_red_tulip", "lantern")


@pytest.mark.parametrize("arch", ["western", "south_asian", "african"])
def test_rekha_deul_is_furnished(arch):
    names = Counter(s.split("[")[0] for s in blocks("REKHA_DEUL_TEMPLE", arch).values())
    assert all(names[n] >= 1 for n in NEEDS), {n: names[n] for n in NEEDS}
    assert mcvalid.invalid_states(aoe2mc.B.states) == {}


def test_path_from_porch_to_idol_is_free():
    last = blocks("REKHA_DEUL_TEMPLE", "western")
    idol = [p for p, s in last.items() if s == "gold_block" and last.get((p[0], p[1] - 1, p[2])) == "chiseled_cinnabar"]
    assert len(idol) == 2
    gx, gy, gz = min(idol)
    free = ("air", "barrier")
    for z in range(gz + 1, gz + 8):                     # the carpet row in the sanctum, the porch and its opening
        for y in (gy - 1, gy):
            s = last.get((gx, y, z), "air")
            assert s in free or s.endswith("_carpet"), (z, y, s)


@pytest.mark.parametrize("tile", [1, 2, 3, 5])
def test_small_tile_sizes_work(tile):
    blocks("REKHA_DEUL_TEMPLE", "western", tile)
