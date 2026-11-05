"""A #const with no value skips only its own name, not the next directive or section (#5767)."""
import numpy as np

import rmap


def expand(text, consts):
    return rmap.expand(rmap.tokens(text), np.random.default_rng(0), set(), consts, [])


SCRIPT = """#const TREE_A
#const TREE_B
#const TREE_C 5
<LAND_GENERATION>
base_terrain GRASS
"""


def test_no_value_keeps_next_const():
    consts = {}
    out = expand(SCRIPT, consts)
    assert consts == {"TREE_C": 5}
    assert "TREE_B" not in out and out == ["<LAND_GENERATION>", "base_terrain", "GRASS"]
