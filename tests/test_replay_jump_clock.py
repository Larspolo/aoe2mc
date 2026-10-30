"""After a jump the game clock starts when the jump commands are sent, not before their slow send (#4272)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import replay  # noqa: E402
from test_replay import data  # noqa: E402
from test_replay_control import Clock, chats  # noqa: E402

SLOW = 50.0                                                         # real seconds of the send of the jump commands


class Paper(Clock):
    """A fake Paper server: commands go out in batches, and the batch with the jump text takes SLOW seconds."""
    def __init__(self):
        super().__init__()
        self.jumped, self.sent_at = False, None

    def batch(self, cmds):
        for c in cmds:
            self.command(c)
        if any("Jump to" in c for c in cmds):
            self.now += SLOW
            self.sent_at = self.now


def test_the_first_event_after_a_jump_plays_at_its_time_after_the_send():
    game = Paper()

    def poll(control):
        if game.now >= 10 and not game.jumped:
            control["jump"], game.jumped = 300000, True
    replay.Replay(game, data(chats(30000, 400000))).run(clock=lambda: game.now, sleep=game.sleep, log=None, poll=poll,
                                                          bar=True)
    assert game.sent_at is not None
    assert abs(game.at["t400000"] - (game.sent_at + 100)) < 1.5    # 100 s of game time after the jump to 5:00
