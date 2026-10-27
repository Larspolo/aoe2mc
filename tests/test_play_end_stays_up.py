"""#2051: after "Victory" or "Defeat" the server of `run.py --play` stays up, and the fog of war goes."""
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import run  # noqa: E402


class FakeGame:
    def __init__(self, *a, **k):
        self.stopped, self.port = False, 0

    def start(self):
        pass

    def stop(self):
        self.stopped = True


def test_play_that_ends_does_not_stop_the_server(tmp_path, monkeypatch):
    (tmp_path / "level.dat").write_bytes(b"")
    games = []
    monkeypatch.setattr(run, "Game", lambda *a, **k: games.append(FakeGame()) or games[-1])
    monkeypatch.setattr(run, "play", lambda *a, **k: types.SimpleNamespace(ended="Victory"))

    class Commands:                                  # the player types nothing, then presses Ctrl-C
        def is_alive(self):
            assert not games[0].stopped              # the server is still up after the end
            raise KeyboardInterrupt

        def join(self, t):
            pass
    monkeypatch.setattr(run, "console", lambda game: Commands())
    run.main([str(tmp_path), "--play"])
    assert games[0].stopped                          # Ctrl-C stops it


@pytest.mark.parametrize("reveal", ["normal", "all"])
def test_the_end_shows_all_units(reveal, monkeypatch):
    import fog
    calls = []
    monkeypatch.setattr(fog, "toggle", lambda g: calls.append(g))
    g = types.SimpleNamespace(reveal=reveal, bots=(types.SimpleNamespace(g=types.SimpleNamespace(reveal="normal")),))
    run.unveil(g)
    assert calls == ([g] if reveal == "normal" else []) + [g.bots[0].g]
