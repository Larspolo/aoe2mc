"""A carpet next to leaves at head height stops a unit (#2390): the converter takes the carpet away."""
import numpy as np
from test_terrain import columns

import aoe2mc


def test_no_carpet_under_a_block_at_head_height():
    """The step onto a carpet (1/16 block) lifts the head of a unit (1.95 blocks) into a block 3 over the ground."""
    B = aoe2mc.B
    cols = columns(np.zeros((4, 4), int))
    g = int(cols.wtop[5, 5])
    for x, z in ((5, 5), (10, 10), (12, 5)):
        cols.deco[x, z] = B("moss_carpet")
    E = aoe2mc.Edits(cols)
    E.add([6], [g + 3], [5], "oak_leaves[persistent=true]")      # the case of #2304: leaves 2 over the next ground
    E.add([12], [g + 4], [6], "oak_leaves[persistent=true]")     # higher leaves leave room for the head
    E.add([3], [g + 1], [12], "red_carpet", hard=False)          # a carpet of FALLEN_LEAVES
    E.add([3], [g + 3], [13], "oak_leaves[persistent=true]", hard=False)
    aoe2mc.free_carpets(E, cols)
    assert cols.deco[5, 5] == aoe2mc.AIR
    assert cols.deco[10, 10] == cols.deco[12, 5] == B("moss_carpet")
    x, y, z, ids, _ = (np.concatenate(p) for p in zip(*E.parts))
    assert B("red_carpet") not in ids[(x == 3) & (z == 12)]
    assert (ids == B("oak_leaves[persistent=true]")).sum() == 3
