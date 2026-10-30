"""The deck of the Flagship of Nearchos has rowing benches and cargo (#500)."""
from collections import Counter

import mcvalid
import pytest
from test_furnish_landmarks import blocks

import aoe2mc

NEEDS = ("spruce_slab", "barrel", "chest", "hay_block", "lantern")


def test_flagship_deck_is_furnished():
    last = blocks("FLAGSHIP_OF_NEARCHOS_MOVEABLE", "western")
    names = Counter(s.split("[")[0] for s in last.values())
    assert all(names[n] >= 1 for n in NEEDS), {n: names[n] for n in NEEDS}
    assert names["spruce_slab"] >= 4                    # benches on both sides
    assert mcvalid.invalid_states(aoe2mc.B.states) == {}


@pytest.mark.parametrize("tile", [1, 2, 3])
def test_small_tile_sizes_work(tile):
    blocks("FLAGSHIP_OF_NEARCHOS_MOVEABLE", "western", tile)
