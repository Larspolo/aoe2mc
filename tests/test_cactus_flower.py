"""Some desert cacti have a cactus flower on top (#540)."""
import numpy as np
from mcvalid import block_error

import aoe2mc

T, H = 4, 3


def cacti(cells):
    n = 16
    cols = aoe2mc.Columns(n, np.zeros((n, n), np.int16), np.zeros((n, n), np.float32), {0: "DESERT_SAND"}, T, H,
                          np.random.default_rng(1))
    base = dict(kind="O", name="CACTUS", player=0, rotation=0.0, hero=False, garrisoned=False)
    E, _ = aoe2mc.place_objects([dict(base, x=x + 0.5, y=y + 0.5) for x, y in cells], {}, cols,
                                np.random.default_rng(1))
    x, y, z, ids, _ = (np.concatenate(p) for p in zip(*E.parts))
    return cols, {(int(a), int(b), int(c)): aoe2mc.B.states[i].removeprefix("minecraft:") for a, b, c, i in zip(x, y, z, ids)}


def test_one_in_three_cacti_bloom_on_top():
    cells = [(x, y) for x in range(1, 15, 2) for y in range(1, 15, 2)]
    cols, blocks = cacti(cells)
    flowers = 0
    for x, y in cells:
        bx, bz = int((x + 0.5) * T), int((y + 0.5) * T)
        g = cols.surface(bx, bz)
        assert blocks[(bx, g, bz)] == blocks[(bx, g + 1, bz)] == "cactus"
        top = blocks.get((bx, g + 2, bz))
        assert top in (None, "cactus_flower")
        flowers += top == "cactus_flower"
    assert len(cells) // 5 <= flowers <= len(cells) // 2
    assert block_error("cactus_flower") is None


def test_flowers_are_deterministic():
    cells = [(x, 3) for x in range(1, 15)]
    assert cacti(cells)[1] == cacti(cells)[1]
