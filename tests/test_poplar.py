"""Autumn trees get poplar wood and yellow, orange or red poplar leaves (#539)."""
import mcvalid
import numpy as np

import aoe2mc as A


def tree_states(name, seed=0):
    E = A.Edits()
    A.make_tree(E, A.tree_kind(name), 0, 64, 0, np.random.default_rng(seed))
    ids = np.unique(np.concatenate([p[3] for p in E.parts]))
    return {A.B.states[i].removeprefix("minecraft:") for i in ids}


def test_autumn_trees_are_poplar():
    colors = set()
    for name in ("TREE_OAK_AUTUMN", "TREE_OAK_AUTUMN_SNOW", "TREE_ASIAN_MAPLE_AUTUMN"):
        for seed in range(12):
            s = tree_states(name, seed)
            assert "poplar_log" in s
            leaves = {b for b in s if "leaves" in b}
            assert len(leaves) == 1 and all(b.endswith("_poplar_leaves[persistent=true]") for b in leaves)
            colors |= leaves
    assert colors == {f"{c}_poplar_leaves[persistent=true]" for c in ("yellow", "orange", "red")}
    for b in colors | {"poplar_log"}:
        assert mcvalid.block_error(b) is None, b


def test_other_trees_do_not_change():
    assert tree_states("TREE_OAK") == {"oak_log", "oak_leaves[persistent=true]"}
    assert A.tree_kind("TREE_PINE") == "spruce" and A.tree_kind("TREE_BIRCH") == "birch"
