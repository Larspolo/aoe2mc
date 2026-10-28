"""#2316: `run.py --play --victory conquest` is the AoE2 setting "Victory" = Conquest (wiki "Victory conditions"):
only the conquest wins, a wonder or all relics start no timer. "standard" (the default): all three wins."""
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import gather  # noqa: E402
import run  # noqa: E402
from test_play_speed import FakeGame  # noqa: E402


def loop(monkeypatch, victory=None, steps=4):
    """Run Gather.run for some steps with no server. Returns the calls of the four win and fog ticks."""
    calls = []
    for m in (gather.conquest, gather.fog, gather.herd):
        monkeypatch.setattr(m, "tick", lambda g, m=m: calls.append(m.__name__))
    monkeypatch.setattr(gather.wonder, "tick", lambda g, dt: calls.append("wonder"))
    monkeypatch.setattr(gather.relic_victory, "tick", lambda g, dt: calls.append("relic_victory"))
    monkeypatch.setattr(gather.time, "sleep", lambda s: None)
    g = object.__new__(gather.Gather)
    g.tick, g.bots, g.ended = 0.25, (), None
    if victory:
        g.victory = victory
    g.point = g.step = lambda: None
    g.clicks = lambda: ()
    g.run(until=lambda: calls.count("conquest") >= steps)
    return calls


def test_conquest_runs_no_wonder_or_relic_timer(monkeypatch):
    calls = loop(monkeypatch, "conquest")
    assert calls.count("conquest") == 4 and "wonder" not in calls and "relic_victory" not in calls


@pytest.mark.parametrize("victory", [None, "standard"])
def test_standard_has_the_three_wins(monkeypatch, victory):
    calls = loop(monkeypatch, victory)
    assert calls.count("conquest") == calls.count("wonder") == calls.count("relic_victory") == 4


@pytest.mark.parametrize("victory", ["standard", "conquest"])
def test_play_sets_the_victory_on_the_gather(victory, tmp_path, monkeypatch):
    (tmp_path / "aoe2mc.json").write_text('{"players": [], "tile_size": 4}')
    seen = []

    class FakeGather:
        bots, villagers, units, ended, speed = (), [], [], None, 1.0

        def __init__(self, *a, **k):
            pass

        def setup(self):
            pass

        def run(self, seconds):
            seen.append(self.victory)
    monkeypatch.setattr(gather, "Gather", FakeGather)
    import combat
    monkeypatch.setattr(combat, "setup", lambda game, data: None)
    run.play(FakeGame(), str(tmp_path), victory=victory)
    assert seen == [victory]


def test_the_victory_option_goes_to_play(tmp_path, monkeypatch, capsys):
    (tmp_path / "level.dat").write_bytes(b"")
    seen = {}
    monkeypatch.setattr(run, "Game", lambda *a, **k: types.SimpleNamespace(start=lambda: None, stop=lambda: None,
                                                                         port=0))
    monkeypatch.setattr(run, "play", lambda *a, **k: seen.update(k) or types.SimpleNamespace(ended=None))
    monkeypatch.setattr(run, "console", lambda game: None)
    run.main([str(tmp_path), "--play", "--victory", "conquest"])
    assert seen["victory"] == "conquest"
    run.main([str(tmp_path), "--play"])
    assert seen["victory"] == "standard"
    with pytest.raises(SystemExit):
        run.main(["--help"])
    assert "{standard,conquest" in capsys.readouterr().out             # more values can follow (#2358)
