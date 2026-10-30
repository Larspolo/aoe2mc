"""About 1 oak or dead tree in 10 has bracket fungus (shelf_mushroom) on the trunk, facing away from it (#558)."""
import numpy as np
from mcvalid import block_error

import aoe2mc


def trees(kind, n=200):
    """{(x, y, z): state} of n trees of one kind in a row, 10 blocks apart."""
    out = {}
    for i in range(n):
        E = aoe2mc.Edits()
        aoe2mc.make_tree(E, kind, 10 * i, 64, 5, np.random.default_rng(i))
        for x, y, z, ids, _ in E.parts:
            out.update({(int(a), int(b), int(c)): aoe2mc.B.states[k].removeprefix("minecraft:")
                        for a, b, c, k in zip(x, y, z, ids)})
    return out


def mushrooms(blocks):
    return {p: s for p, s in blocks.items() if s.startswith("shelf_mushroom")}


def test_one_tree_in_ten_has_fungus_on_the_trunk():
    for kind in ("oak", "dead"):
        blocks = trees(kind)
        m = mushrooms(blocks)
        with_fungus = {x // 10 for x, _, _ in m}
        assert 8 <= len(with_fungus) <= 35, (kind, len(with_fungus))
        for (x, y, z), s in m.items():
            dx, dz = aoe2mc.FACE[s.split("facing=")[1].rstrip("]")]
            assert blocks[(x - dx, y, z - dz)].endswith("_log"), (kind, s)  # the trunk is behind the mushroom
            assert 65 <= y <= 67 and block_error(s) is None


def test_other_trees_have_no_fungus():
    assert not mushrooms(trees("birch", 50)) and not mushrooms(trees("spruce", 50))


def test_fungus_is_deterministic():
    assert mushrooms(trees("oak", 50)) == mushrooms(trees("oak", 50))
