"""The fast tree and barrier code of #702 puts the same blocks as one add for each part."""
import numpy as np
from test_terrain import columns

import aoe2mc
import buildings


def blocks(E):
    return [tuple(map(int, b)) for p in E.parts for b in zip(*p)]


def test_cached_tree_has_the_blocks_of_the_drawing():
    for kind in ("oak", "spruce", "acacia", "palm", "jungle", "poplar", "birch"):
        for seed in range(6):
            E = aoe2mc.Edits()
            aoe2mc.make_tree(E, kind, 7, 64, -3, np.random.default_rng(seed))
            rng = np.random.default_rng(seed)
            h = int(rng.integers(4, 7))
            wood = aoe2mc.WOODS.get(kind, "oak")
            leaf = aoe2mc.leaves(f"{('yellow', 'orange', 'red')[int(rng.integers(3))]}_poplar") \
                if kind == "poplar" else aoe2mc.leaves(wood)
            D = aoe2mc.Edits()
            aoe2mc.tree_shape(D, kind, h, f"{wood}_log", leaf)
            want = [(x + 7, y + 64, z - 3, i, hard) for x, y, z, i, hard in blocks(D)]
            assert blocks(E)[:len(want)] == want, (kind, seed)


def test_barriers_of_an_obstacle_follow_the_ground():
    cols = columns(np.zeros((4, 4), int))
    cols.wtop[5, 6] += 2
    E = aoe2mc.Edits(cols)
    old, buildings.BARRIERS = buildings.BARRIERS, True
    try:
        aoe2mc.obstacle(E, cols, (4, 7, 5, 7))
    finally:
        buildings.BARRIERS = old
    want = [(x, y, z) for x in range(4, 7) for z in range(5, 7) for y in range(cols.surface(x, z), cols.surface(x, z) + 3)]
    assert [b[:3] for b in blocks(E)] == want
    assert cols.blocked[4:7, 5:7].all()
