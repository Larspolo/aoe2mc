"""Live replay: an ORDER on a target that the replay does not know takes the resource near its click (#3976). AoE2
gives a tree a new object ID when a villager cuts it, so a later ORDER on the tree names an unknown ID. Fake RCON."""
from test_replay_gather import TREE, gather, order, play


def test_an_order_on_a_cut_tree_chops_the_tree_near_the_click():
    r, _ = play([dict(order(0, 999), tile=[5.6, 8.7])], TREE, 60000)   # 999: the new ID of the cut tree
    assert 7 in r.working and r.map.trees[(5, 10)] < gather.TREE_WOOD
    assert r.units[7].task != "none"


def test_an_order_on_an_unknown_target_far_from_resources_gathers_nothing():
    r, _ = play([dict(order(0, 999), tile=[12.5, 3.5])], TREE, 60000)
    assert 7 not in r.working and r.map.trees[(5, 10)] == gather.TREE_WOOD
