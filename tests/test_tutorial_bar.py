"""A game without --tutorial removes the boss bar of a stopped tutorial game (#5883)."""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, "game"), os.path.join(ROOT, "tools")]
import run  # noqa: E402
import tutorial  # noqa: E402


class Stop(Exception):
    pass


class FakeGame:
    def __init__(self):
        self.sent = []

    def forceload(self):
        pass

    def command(self, cmd):
        self.sent.append(cmd)
        if not cmd.startswith("bossbar remove"):
            raise Stop                                       # the next game command: the bar is done


class FakeGather:
    def __init__(self, game, data, **kw):
        self.villagers, self.units = {}, []

    def setup(self):
        pass


@pytest.mark.parametrize("on", [False, True])
def test_play_removes_the_tutorial_bar_only_without_tutorial(on, tmp_path, monkeypatch):
    (tmp_path / "aoe2mc.json").write_text("{}")
    monkeypatch.setattr("gather.Gather", FakeGather)
    game = FakeGame()
    with pytest.raises(Exception):
        run.play(game, str(tmp_path), tutorial=on)
    assert (f"bossbar remove {tutorial.BAR}" in game.sent) is not on, game.sent
