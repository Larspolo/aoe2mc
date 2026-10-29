"""Live replay: a villager whose tree or mine is empty takes the nearest one of the same kind, as in AoE2 (#720)."""
import pytest

import gather
from test_replay_gather import MINE, TREE, hits, order, play
from test_replay_walk import tps


@pytest.mark.parametrize("ai", [False, True])
def test_the_villager_takes_the_next_tree(ai):
    second = dict(TREE, ref=23, tile=[7.5, 10.5])
    r, sent = play([order(0, 20)], [TREE, second], 330000, ai)
    assert r.map.trees[(5, 10)] == 0
    assert 0 < gather.TREE_WOOD - r.map.trees[(7, 10)] < gather.TREE_WOOD and 7 in r.working
    assert r.units[7].cell in r.map.around(r.map.cells((7, 10)))
    assert len(hits(sent, "oak_log")) == 2 * gather.TREE_WOOD - r.map.trees[(5, 10)] - r.map.trees[(7, 10)]


def test_the_villager_takes_the_next_mine():
    second = dict(MINE, ref=24, tile=[9.0, 10.0])
    r, _ = play([order(0, 22)], [MINE, second], 1100000)
    full = gather.MINES["STONE_MINE"][1]
    assert r.map.mines["stone"][(6, 10)] == 0 and 0 < full - r.map.mines["stone"][(9, 10)] < full
    assert 7 in r.working


def test_a_far_tree_or_another_kind_is_not_taken():
    far = dict(TREE, ref=23, tile=[14.5, 10.5])
    bush = {"kind": "other", "name": "FRUIT_BUSH", "player": 0, "ref": 21, "tile": [5.5, 12.5]}
    r, sent = play([order(0, 20)], [TREE, far, bush], 330000)
    assert r.map.trees[(5, 10)] == 0 and r.map.trees[(14, 10)] == gather.TREE_WOOD and r.map.bushes[(5, 12)] == gather.BUSH_FOOD
    assert not r.working and not r.moving
    assert tps(sent)[-1] == r.units[7].cell                            # it stays at the felled tree
