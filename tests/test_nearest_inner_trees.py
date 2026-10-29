"""game/gather.py: a villager that works on goes to the nearest tree with a free cell next to it (#3791). Gather.nearest took the
nearest tree by its middle: an inner tree of a forest has no free cell, so the villager stopped there, as AoE2 does not."""
from test_bot_inner_trees import forest_map


def test_nearest_takes_a_tree_with_a_free_cell():
    b = forest_map()
    g, v = b.g, b.g.villagers["b0"]
    v.res, v.tree = "wood", None
    inner = [t for t in g.map.trees if not g.goals(t)]
    t = g.nearest(v)
    assert t in g.map.trees and g.goals(t) and t not in inner           # the nearest tree by its middle is an inner one


def test_nearest_stops_when_only_inner_trees_are_left():
    b = forest_map()
    g, v = b.g, b.g.villagers["b0"]
    v.res, v.tree = "wood", None
    for t in list(g.map.trees):                                        # only inner trees are left
        if g.goals(t):
            g.map.trees[t] = 0
    assert g.nearest(v) is None
