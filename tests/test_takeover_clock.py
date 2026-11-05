"""#5700: after a takeover (play with a state, no wait), the game clock of player 1 goes on at the takeover time, as
the clock of the bots does."""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import combat  # noqa: E402
import gather  # noqa: E402
import recap  # noqa: E402
import run  # noqa: E402
import savegame  # noqa: E402
from test_play_speed import FakeGame  # noqa: E402


def test_play_after_a_takeover_starts_the_clock_at_the_takeover_time(tmp_path, monkeypatch):
    (tmp_path / "aoe2mc.json").write_text('{"players": {}, "tile_size": 4, "objects": []}')
    seen = []

    class FakeGather:
        bots, villagers, units, ended, speed, sites, t0 = (), {}, [], None, 1.0, [], 0.0
        clock = staticmethod(time.monotonic)

        def __init__(self, game, data, **k):
            self.game, self.data = game, data

        def setup(self):
            pass

        def run(self, seconds):
            seen.append(recap.game_time(self))

    monkeypatch.setattr(gather, "Gather", FakeGather)
    monkeypatch.setattr(combat, "setup", lambda game, data: None)
    monkeypatch.setattr(savegame, "load", lambda g, d: setattr(g.game, "loaded_seconds", d["game_time"]))
    monkeypatch.setattr(savegame, "sides", lambda g: [g])
    run.play(FakeGame(), str(tmp_path), state={"players": {}, "game_time": 300.0}, wait=False)
    assert seen and 300 <= seen[0] < 310
