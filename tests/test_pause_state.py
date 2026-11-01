"""#3613: a pause of 30 game seconds keeps the training queue, the gatherer and the treaty as they are (criterion 2 of
epic #3373). Unlike test_pause.py, no step is stubbed: the real steps of train, gather and treaty run."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import gather  # noqa: E402
import pause  # noqa: E402
import train  # noqa: E402
import treaty  # noqa: E402
from test_bot_gather import bot_map  # noqa: E402

from game import gather as game_gather  # noqa: E402


class FakeTime:
    """The clock of gather.time: sleep moves the time on, so 30 game seconds take no real time."""
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


def state(me):
    """What the pause must keep: the queue of the town center, the gatherer and the treaty time left."""
    v = me.villagers["p1"]
    progress = tuple(q[0]["progress"] for q in me.queues.values() if q)
    return (progress, (v.state, v.load, v.timer, v.walked), me.game.treaty - me.game.treaty_time)


def test_a_pause_of_30_game_seconds_keeps_training_gathering_and_the_treaty(monkeypatch):
    fake = FakeTime()
    for g in (gather, game_gather):                  # bot_map makes the Gather of game.gather: patch both (#5485)
        monkeypatch.setattr(g, "time", fake)
    _, me, _ = bot_map()
    me.clock = fake.monotonic
    me.clicks = lambda: ()
    me.stock["food"] = 1000
    queued = train.queue(me, "Steve", (3, 3))
    assert queued is not None
    v = me.villagers["p1"]
    v.state, v.tree = "to_tree", (1, 1)
    treaty.start(me, 60.0)
    before = state(me)

    pause.toggle(me, 1)
    me.run(seconds=30)
    assert state(me) == before
    pause.toggle(me, 1)

    me.run(seconds=30)
    after = state(me)
    assert after[0] != before[0] and after[1] != before[1] and after[2] != before[2]
