"""The economy line of the summary of the live replay counts the skipped gather of a jump (#1097), as the estimate of
the sidebar (#1056). Fake RCON and a fake clock."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import replay  # noqa: E402
from test_replay import data  # noqa: E402
from test_replay_control import Clock  # noqa: E402
from test_replay_gather import TREE, VIL, order  # noqa: E402

TO = 100000.0


def gathered(jump):
    d = data([order(0, 20), dict(time=TO + 2000, player=1, kind="chat", text="end")])
    d["objects"] += [VIL, TREE]
    game, done = Clock(), []

    def poll(control):
        if jump and game.now >= 0.5 and not done:
            control["jump"] = TO
            done.append(game.now)
    r = replay.Replay(game, d)
    r.run(clock=lambda: game.now, sleep=game.sleep, log=None, poll=poll)
    return r.gathered.get(1, {}).get("wood", 0), r.resources(1)["wood"] - replay.START["wood"]


def test_the_summary_counts_the_skipped_gather():
    (walked, _), (jumped, estimate) = gathered(False), gathered(True)
    assert walked > 20 and abs(jumped - walked) <= 0.25 * walked
    assert jumped == estimate                                           # the summary and the sidebar agree
