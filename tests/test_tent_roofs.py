"""Tent roofs are cloth slopes of wool stairs (#525)."""
from collections import Counter

import mcvalid
import pytest
from test_furnish_landmarks import blocks

import aoe2mc


@pytest.mark.parametrize("name,wool", [("GREEK_ARMY_TENT", "white_wool"), ("TENT_A", "brown_wool"), ("TENT_B", "brown_wool")])
def test_tent_roof_has_wool_stairs(name, wool):
    last = blocks(name, "western")
    names = Counter(s.split("[")[0] for s in last.values())
    assert names[f"{wool}_stairs"] >= 8, names
    assert mcvalid.invalid_states(aoe2mc.B.states) == {}


def test_ridge_tent_slopes_rise_to_the_ridge():
    last = blocks("GREEK_ARMY_TENT", "western")
    xs = [p[0] for p, s in last.items() if s.startswith("white_wool_stairs")]
    mid = (min(xs) + max(xs)) / 2
    for (x, _, _), s in last.items():
        if s.startswith("white_wool_stairs"):
            assert ("facing=east" if x < mid else "facing=west") in s, (x, s)


@pytest.mark.parametrize("tile", [1, 2, 3])
@pytest.mark.parametrize("name", ["GREEK_ARMY_TENT", "TENT_A"])
def test_small_tile_sizes_work(name, tile):
    blocks(name, "western", tile)
