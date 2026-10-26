"""Units of the live replay walk under the low leaves of a forest (#889).

A moss carpet is 1/16 block high: on it a unit of 1.95 blocks does not fit under leaves 2 blocks above the ground,
and the Minecraft path finder finds no way through the cell (the eagle scout of `samples/de-64.3.aoe2record` stood
still with an order for 40 s next to a forest).
"""
import numpy as np

import aoe2mc


def test_no_carpet_under_low_leaves():
    B = aoe2mc.B
    t = np.zeros((4, 4), np.int16)
    cols = aoe2mc.Columns(4, t, np.zeros((4, 4), np.float32), {0: "GRASS_1"}, 4, 3, np.random.default_rng(1))
    cells = {"leaves": (2, 2), "open": (4, 4), "high": (6, 6), "rug": (8, 8)}
    for x, z in cells.values():
        cols.deco[x, z] = B("moss_carpet")
    y = {k: int(cols.top[x, z]) + 1 for k, (x, z) in cells.items()}     # the carpet
    put = [("leaves", 2, "oak_leaves[distance=1,persistent=true,waterlogged=false]"),
           ("high", 3, "oak_leaves[distance=1,persistent=true,waterlogged=false]"),
           ("rug", 1, "barrier"), ("rug", 2, "spruce_planks")]                   # a rug in a footprint stays
    edits = tuple(np.array(a) for a in zip(*[(cells[k][0], y[k] + dy, cells[k][1], B(s), True) for k, dy, s in put]))
    vol = aoe2mc.build_chunk(0, 0, cols, edits)[1]
    name = {k: B.states[vol[y[k] - aoe2mc.MIN_Y, z, x]].split(":")[1] for k, (x, z) in cells.items()}
    assert name == {"leaves": "air", "open": "moss_carpet", "high": "moss_carpet", "rug": "moss_carpet"}
