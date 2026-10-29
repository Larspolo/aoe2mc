"""Live replay: a villager whose target tree has no path chops the nearest tree that it can reach, as in AoE2 (#869)."""
import pytest

import gather
from test_replay_gather import TREE, hits, order, play


def forest():
    """A tree at tile (6, 10) in a ring of 8 trees: no path to it."""
    ring = [dict(TREE, ref=30 + k, tile=[6.5 + dx, 10.5 + dz])
            for k, (dx, dz) in enumerate((dx, dz) for dx in (-1, 0, 1) for dz in (-1, 0, 1) if dx or dz)]
    return [dict(TREE, tile=[6.5, 10.5])] + ring


@pytest.mark.parametrize("ai", [False, True])
def test_an_order_on_an_enclosed_tree_chops_the_nearest_reachable_tree(ai):
    r, sent = play([order(0, 20)], forest(), 60000, ai)
    assert r.map.path(r.units[7].cell, r.map.around(r.map.cells((6, 10))), 20000) is None   # the tree is enclosed
    assert r.map.trees[(6, 10)] == gather.TREE_WOOD
    assert 7 in r.working and r.units[7].tree == (5, 10)               # the nearest tree of the ring, west side
    assert r.units[7].cell in r.map.around(r.map.cells((5, 10)))
    assert r.map.trees[(5, 10)] < gather.TREE_WOOD and hits(sent, "oak_log")

