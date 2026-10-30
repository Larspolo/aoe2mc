"""Live replay: a lumberjack whose tree is empty walks to a tree up to NEXT_TREES tiles away (#4063). In de-64.3, 19
villagers had the next tree 5 to 8 tiles away and stood idle with NEXT = 5. Other resources keep NEXT."""
import gather
import replay
from test_replay_gather import MINE, TREE, order, play


def test_a_tree_beyond_next_and_within_next_trees_is_taken():
    tile = TREE["tile"][0] + (replay.NEXT + replay.NEXT_TREES) / 2
    second = dict(TREE, ref=23, tile=[tile, TREE["tile"][1]])
    r, _ = play([order(0, 20)], [TREE, second], 330000)
    key = (int(tile), int(TREE["tile"][1]))
    assert r.map.trees[(5, 10)] == 0 and r.map.trees[key] < gather.TREE_WOOD
    assert 7 in r.working or 7 in r.moving


def test_a_mine_beyond_next_is_not_taken():
    tile = MINE["tile"][0] + (replay.NEXT + replay.NEXT_TREES) / 2
    second = dict(MINE, ref=24, tile=[tile, MINE["tile"][1]])
    r, _ = play([order(0, 22)], [MINE, second], 1100000)
    full = gather.MINES["STONE_MINE"][1]
    assert r.map.mines["stone"][(6, 10)] == 0 and r.map.mines["stone"][(int(tile), 10)] == full
    assert not r.working and not r.moving
