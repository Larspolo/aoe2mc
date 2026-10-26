"""The barricades look like the game (#457): low heaps of debris, one shape for each of the four types."""
import sys

import numpy as np

sys.path.insert(0, "tools")
import render  # noqa: E402


def heap(letter):
    xs, ys, zs, st = render.building_blocks("BARRICADE_" + letter, "western")
    ground = max(y for y, s in zip(ys, st) if "grass_block" in s)
    keep = np.array(["barrier" not in s for s in st]) & (ys > ground)
    return {(x, z) for x, z in zip(xs[keep], zs[keep])}, ys[keep], [s for s, k in zip(st, keep) if k]


def test_low_heaps_of_wood_and_stone():
    for letter in "ABCD":
        cells, ys, states = heap(letter)
        assert len(cells) >= 25 and ys.max() - ys.min() <= 3
        assert any("spruce" in s for s in states) and any("cobblestone" in s or "andesite" in s for s in states)
        assert any("mangrove_roots" in s for s in states)


def test_four_shapes():
    assert len({frozenset(heap(letter)[0]) for letter in "ABCD"}) == 4
