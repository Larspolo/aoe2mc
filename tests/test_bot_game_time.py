"""#3513: at `run.py --play --speed N` each bot Gather has the speed of player 1, so recap.game_time agrees."""
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import gather  # noqa: E402
import recap  # noqa: E402
import run  # noqa: E402


class FakeGame:
    kind, game_port, version, sides = "vanilla", 0, "26.3", {}

    def forceload(self):
        pass

    def command(self, c):
        pass


def test_bot_gather_has_the_speed_of_player_1(tmp_path, monkeypatch):
    (tmp_path / "aoe2mc.json").write_text('{"players": [], "tile_size": 4}')
    made = []

    class FakeGather:
        bots, villagers, units, ended, speed = (), [], [], None, 1.0

        def __init__(self, *a, **k):
            self.clock, self.t0 = lambda: 10.0, 0.0
            made.append(self)

        def setup(self):
            pass

        def run(self, seconds):
            pass
    bot = types.SimpleNamespace(g=types.SimpleNamespace(speed=1.0, t0=0.0, clock=lambda: 10.0))
    FakeGather.bots = (bot,)
    monkeypatch.setattr(gather, "Gather", FakeGather)
    import combat
    monkeypatch.setattr(combat, "setup", lambda game, data: None)
    run.play(FakeGame(), str(tmp_path), speed=2.0)
    player1 = made[0]
    assert bot.g.speed == player1.speed == 2.0
    assert recap.game_time(bot.g) == recap.game_time(player1) == 10 * gather.NORMAL * 2.0
