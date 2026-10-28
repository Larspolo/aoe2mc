"""#3089: the technologies of the start age set their scores in the scenario mode: the mode is set before the age starts."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import capture_relic  # noqa: E402
import combat  # noqa: E402
import gather  # noqa: E402
import run  # noqa: E402
import train  # noqa: E402


def test_the_age_start_sees_the_mode_of_the_game(tmp_path, monkeypatch):
    (tmp_path / "aoe2mc.json").write_text('{"players": {}, "tile_size": 4}')
    seen = []

    class FakeGather:
        bots, villagers, units, ended, speed, data = (), [], [], None, 1.0, {}

        def __init__(self, *a, **k):
            pass

        def setup(self):
            pass

        def run(self, seconds):
            pass
    monkeypatch.setattr(gather, "Gather", FakeGather)
    monkeypatch.setattr(capture_relic, "setup", lambda g, mode, **start: None)
    monkeypatch.setattr(train, "start", lambda g, age: seen.append((age, "capture-the-relic" in getattr(g, "modes", ()))))
    monkeypatch.setattr(combat, "setup", lambda game, data: None)
    import savegame
    monkeypatch.setattr(savegame, "load", lambda g, d: None)
    from test_play_speed import FakeGame
    run.play(FakeGame(), str(tmp_path), state=None, mode="capture-the-relic", age="feudal")
    assert seen == [("feudal", True)]
