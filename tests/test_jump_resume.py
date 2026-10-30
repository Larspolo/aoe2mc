"""After a jump of the live replay the boss bar does not go back to times before the jump, and the gather steps of the
skipped time do not run fast after it (#1125), with a fake clock and a fake RCON."""
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import replay  # noqa: E402
from test_replay import data  # noqa: E402
from test_replay_control import Clock  # noqa: E402
from test_replay_gather import TREE, VIL, order  # noqa: E402


@pytest.mark.parametrize("ai", [False, True])
def test_the_bar_never_goes_back_after_a_jump(ai):
    d = data([order(0, 20), dict(time=200000, player=1, kind="chat", text="t200000")])
    d["objects"] += [VIL, TREE]
    game, at = Clock(), []

    def poll(control):
        if game.now >= 5 and not at:
            control["jump"] = 100000.0
            at.append(len(game.sent))
    r = replay.Replay(game, d, ai=ai)
    r.run(clock=lambda: game.now, sleep=game.sleep, log=None, poll=poll, bar=True)
    after = game.sent[at[0]:]
    shown = [int(m[1]) for c in after if (m := re.match(rf"bossbar set {replay.BAR} value (\d+)$", c))]
    assert shown[0] == 100 and shown == sorted(shown), shown[:10]      # the jump time first, then only forward
    assert 7 in r.working and r.working[7] > 100000                     # the villager still chops, after the jump time
