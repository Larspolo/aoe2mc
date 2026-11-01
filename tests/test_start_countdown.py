"""The countdown of 5 seconds before the game starts (#5506): titles 5 to 1, then the unfreeze and the clock."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, "game"), os.path.join(ROOT, "tools")]
import run  # noqa: E402


class FakeGame:
    joined = frozenset()

    def __init__(self):
        self.sent, self.wait = [], True

    def command(self, cmd):
        self.sent.append(cmd)


class Side:
    def __init__(self, clock):
        self.clock, self.t0 = clock, clock()


def test_the_titles_count_down_before_the_unfreeze_and_the_clock_starts_after(monkeypatch):
    game, now = FakeGame(), [0.0]
    sides = [Side(lambda: now[0])]

    def sleep(s):
        now[0] += s
        if s == 0.5:
            game.joined = {"Lars"}
    run.start_on_join(game, sides, 1, sleep=sleep)
    numbers = [c for c in game.sent if c.startswith("title @a title ")]
    assert numbers == [f'title @a title "{n}"' for n in (5, 4, 3, 2, 1)]
    unfreeze = game.sent.index("tick unfreeze")
    assert all(game.sent.index(c) < unfreeze for c in numbers)
    assert game.sent.index(numbers[-1]) < unfreeze
    assert sides[0].t0 == now[0] == 5.5                # the 0.5 s join poll, then the 5 s countdown


def test_a_restart_gets_no_freeze_again():
    game, now = FakeGame(), [0.0]

    def sleep(s):
        now[0] += s
        if s == 0.5:
            game.joined = {"Lars"}
    run.start_on_join(game, [Side(lambda: now[0])], 1, sleep=sleep)
    assert game.wait is False
    assert "tick freeze" not in game.sent
