"""A jump of the live replay shows a loading text in the boss bar, then the clock again (#871)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import replay  # noqa: E402
from test_replay import data  # noqa: E402
from test_replay_control import Clock  # noqa: E402
from test_replay_jump import MIL, timeline  # noqa: E402
from test_replay_walk import HOUSE, VIL  # noqa: E402


def test_a_jump_shows_a_loading_text_before_its_commands_and_the_clock_after_them():
    d = data(timeline())
    d["objects"] += [VIL, MIL, HOUSE]
    game, done = Clock(), []

    def poll(control):
        if game.now >= 60 and not done:
            control["jump"] = 300000.0                                  # the input gives a float time
            done.append(game.now)
    replay.Replay(game, d).run(clock=lambda: game.now, sleep=game.sleep, log=None, poll=poll, bar=True)
    names = [i for i, c in enumerate(game.sent) if c.startswith("bossbar set aoe2mc:replay name")]
    load = next(i for i in names if "Jump to 05:00 ..." in game.sent[i])
    first, last = game.sent.index("kill u2"), max(i for i, c in enumerate(game.sent) if c.startswith("tp u1 "))
    assert load < first < last                                         # the delete of 2:30, the tp of the move
    after = next(i for i in names if i > load)
    assert after > last and '"05:00 · speed 1×"' in game.sent[after]
