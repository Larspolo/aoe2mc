"""The estimated resources of the live replay get the gather of the skipped time after a jump (#1056), with a fake
clock and a fake RCON."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import replay  # noqa: E402
from test_replay import data  # noqa: E402
from test_replay_control import Clock  # noqa: E402
from test_replay_gather import MINE, TREE, VIL, order  # noqa: E402

VIL2 = dict(VIL, uuid="u3", ref=9, tile=[9.5, 10.5])
TO = 100000.0


def play(ai, jump, target=20, obj=TREE, t=0):
    """Play to 2 s after TO (ms) with one jump from 0:00 to TO, or without a jump; the two villagers get the ORDER at game
    time t (ms). Returns the estimate of player 1."""
    vil = dict(order(t, target), objects=[7, 9], names=["VILLAGER_MALE"] * 2)
    d = data([vil, dict(time=TO + 2000, player=1, kind="chat", text="end")])
    d["objects"] += [VIL, VIL2, obj]
    game, done = Clock(), []

    def poll(control):
        if jump and game.now >= 0.5 and not done:
            control["jump"] = TO
            done.append(game.now)
    r = replay.Replay(game, d, ai=ai)
    r.run(clock=lambda: game.now, sleep=game.sleep, log=None, poll=poll)
    return dict(r.resources(1))


@pytest.mark.parametrize("ai, t", [(False, 0), (False, 10000), (True, 10000)])
@pytest.mark.parametrize("target, obj, res", [(20, TREE, "wood"), (22, MINE, "stone")])
def test_a_jump_counts_the_skipped_gather(ai, t, target, obj, res, monkeypatch):
    """t = 0: the villagers walk or gather when the jump starts; else a skipped ORDER sends them. A plugin unit that
    works when the jump ends catches up in steps() when it is at its resource (the fake RCON: at once). The reference
    plays without the plugin: the fake RCON has no entity that walks."""
    monkeypatch.setattr(replay.Replay, "entity", lambda self, v: None)
    start, walked, jumped = replay.START[res], play(False, False, target, obj, t), play(ai, True, target, obj, t)
    assert walked[res] > start + 20
    assert abs(jumped[res] - walked[res]) <= 0.25 * (walked[res] - start)


def test_no_gather_without_a_resource():
    r = replay.Replay(Clock(), data([]))
    r.grid()
    r.skipped(7, 0, TO)
    assert r.resources(1) == replay.START
