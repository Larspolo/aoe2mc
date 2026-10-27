"""#2057: `run.py --play --speed N` plays N times faster: /tick rate and shorter steps of the game loop."""
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import gather  # noqa: E402
import run  # noqa: E402


def loop(monkeypatch, speed, steps=8):
    """Run Gather.run for some steps with no server. Returns (real seconds slept, game seconds of wonder.tick)."""
    for m in (gather.conquest, gather.fog, gather.herd):
        monkeypatch.setattr(m, "tick", lambda g: None)
    game = []
    monkeypatch.setattr(gather.wonder, "tick", lambda g, dt: game.append(dt))
    monkeypatch.setattr(gather.relic_victory, "tick", lambda g, dt: None)
    slept = []
    monkeypatch.setattr(gather.time, "sleep", slept.append)
    g = object.__new__(gather.Gather)
    g.tick, g.speed, g.bots, g.ended = 0.25, speed, (), None
    g.point = g.step = lambda: None
    g.clicks = lambda: ()
    g.run(until=lambda: len(game) >= steps)
    return sum(slept), sum(game)


def test_speed_2_needs_half_of_the_real_time(monkeypatch):
    real1, game1 = loop(monkeypatch, 1.0)
    real2, game2 = loop(monkeypatch, 2.0)
    assert game2 == game1 == pytest.approx(8 * 0.25 * gather.NORMAL)     # the same game time (training, building)
    assert real2 == pytest.approx(real1 / 2, rel=0.05)


class FakeGame:
    kind, game_port, version, sides = "vanilla", 0, "26.3", {}

    def __init__(self):
        self.commands = []

    def forceload(self):
        pass

    def command(self, c):
        self.commands.append(c)


@pytest.mark.parametrize("speed, rate", [(1.0, None), (2.0, "tick rate 40"), (0.5, "tick rate 10")])
def test_play_sets_the_tick_rate(speed, rate, tmp_path, monkeypatch):
    (tmp_path / "aoe2mc.json").write_text('{"players": [], "tile_size": 4}')
    runs = []

    class FakeGather:
        bots, villagers, units, ended, speed = (), [], [], None, 1.0

        def __init__(self, *a, **k):
            pass

        def setup(self):
            pass

        def run(self, seconds):
            runs.append(self.speed)
    monkeypatch.setattr(gather, "Gather", FakeGather)
    import combat
    monkeypatch.setattr(combat, "setup", lambda game, data: None)
    game = FakeGame()
    run.play(game, str(tmp_path), speed=speed)
    assert [c for c in game.commands if c.startswith("tick")] == ([rate] if rate else [])   # speed 1: as before
    assert runs == [speed]


def test_the_speed_option_goes_to_play(tmp_path, monkeypatch):
    (tmp_path / "level.dat").write_bytes(b"")
    seen = {}
    monkeypatch.setattr(run, "Game", lambda *a, **k: types.SimpleNamespace(start=lambda: None, stop=lambda: None,
                                                                         port=0))
    monkeypatch.setattr(run, "play", lambda *a, **k: seen.update(k) or types.SimpleNamespace(ended=None))
    monkeypatch.setattr(run, "console", lambda game: None)
    run.main([str(tmp_path), "--play", "--speed", "2"])
    assert seen["speed"] == 2.0
