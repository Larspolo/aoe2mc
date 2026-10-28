"""The units of the game program on the minimap of the map item (#2581, epic #2580): on Paper `run.play` turns on the
dots of the plugin (`aoe minimap on`, Minimap.java, #1237) as the live replay does, before the view square (#1762)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import combat  # noqa: E402
import gather  # noqa: E402
import replay  # noqa: E402
import run  # noqa: E402
from test_play_speed import FakeGame  # noqa: E402


def commands(tmp_path, monkeypatch, kind):
    """The commands of run.play on a fake Gather and a fake game of this kind."""
    (tmp_path / "aoe2mc.json").write_text('{"players": [], "tile_size": 4}')

    class FakeGather:
        bots, villagers, units, ended, speed, sites, data, peers = (), [], [], None, 1.0, [], {"objects": []}, ()

        def __init__(self, *a, **k):
            pass

        def setup(self):
            pass

        def run(self, seconds):
            pass
    monkeypatch.setattr(gather, "Gather", FakeGather)
    monkeypatch.setattr(combat, "setup", lambda game, data: None)
    game = FakeGame()
    game.kind = kind
    run.play(game, str(tmp_path))
    return game.commands


def test_paper_turns_on_the_unit_dots_before_the_view_square(tmp_path, monkeypatch):
    sent = commands(tmp_path, monkeypatch, "paper")
    frame = f"aoe minimap frame {replay.FRAME * 4}"
    assert sent.count("aoe minimap on") == 1 and sent.index("aoe minimap on") < sent.index(frame)


def test_vanilla_sends_no_minimap_command(tmp_path, monkeypatch):
    assert not [c for c in commands(tmp_path, monkeypatch, "vanilla") if "aoe minimap" in c]   # no plugin
