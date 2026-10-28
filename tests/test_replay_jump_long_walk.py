"""A villager on a walk of more legs than one plugin order gathers after a jump of the live replay (#3022), with a
fake RCON."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_replay import Fake, data  # noqa: E402
from test_replay_gather import order  # noqa: E402

import replay  # noqa: E402

FAR = {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "u1", "ref": 7, "tile": [30.5, 30.5]}
TREE = {"kind": "other", "name": "TREE_OAK", "player": 0, "ref": 20, "tile": [3.5, 3.5]}


@pytest.mark.parametrize("ai", [False, True])
def test_a_villager_on_a_long_walk_gathers_after_a_jump(ai):
    d = data([order(1000, 20)], n=128)
    d["objects"] += [FAR, TREE]
    game = Fake()
    r = replay.Replay(game, d, ai=ai)
    r.jump(d["timeline"], 60000, 0)
    assert 7 in r.working                                               # it stands at the tree after the jump
    wood = 100 - r.map.trees[(3, 3)]
    r.steps(120000)
    assert 100 - r.map.trees[(3, 3)] > wood                             # and chops after it
