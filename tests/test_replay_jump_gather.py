"""A villager that a skipped ORDER sent to a tree gathers after a jump of the live replay (#887), with a fake clock
and a fake RCON."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_replay import data  # noqa: E402
from test_replay_control import Clock  # noqa: E402
from test_replay_gather import TREE, VIL, order  # noqa: E402

import gather  # noqa: E402
import replay  # noqa: E402


def jump(ai):
    d = data([order(0, 20), dict(time=200000, player=1, kind="chat", text="t200000")])
    d["objects"] += [VIL, TREE]
    game, done = Clock(), []

    def poll(control):
        if game.now >= 0.5 and not done:
            control["jump"] = 100000.0
            done.append(game.now)
    r = replay.Replay(game, d, ai=ai)
    r.run(clock=lambda: game.now, sleep=game.sleep, log=None, poll=poll)
    return r, game.sent


@pytest.mark.parametrize("ai", [False, True])
def test_a_villager_gathers_after_a_jump(ai):
    r, sent = jump(ai)
    assert r.map.trees[(5, 10)] < gather.TREE_WOOD and 7 in r.working               # it chops until the end
    after = sent.index("tp u1 " + " ".join(map(str, r.units[7].pos))) if not ai else 0
    assert any(c.startswith("rotate u1 facing") for c in sent[after:])
