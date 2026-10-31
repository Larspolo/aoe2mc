"""run() calls inspect() in all loop branches, at most each INSPECT_EVERY s of wall time (#5313)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import replay  # noqa: E402
from test_replay import data  # noqa: E402
from test_replay_control import Clock, chats  # noqa: E402


def test_a_busy_record_calls_inspect_each_second():
    game, calls = Clock(), []
    r = replay.Replay(game, data(chats(*range(100, 20001, 100))))
    r.inspect = lambda t, clock: calls.append(game.now) or []
    r.run(clock=lambda: game.now, sleep=game.sleep, log=None)
    assert calls and calls[0] < 1
    gaps = [b - a for a, b in zip([0.0, *calls], [*calls, game.now])]
    assert max(gaps) <= 1, gaps
    assert min(b - a for a, b in zip(calls, calls[1:])) >= replay.INSPECT_EVERY - 1e-9
