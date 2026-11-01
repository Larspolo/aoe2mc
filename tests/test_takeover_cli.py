"""run.py --replay --from MM:SS --takeover 1 plays the replay to that time, saves its state and goes on as a game of
player 1 (#5450)."""
import json
import threading

import pytest
import run
import savegame
import takeover


@pytest.mark.parametrize("more", [["--play"], ["--live", "x.aoe2record"], []])
def test_takeover_needs_replay_alone(more, tmp_path, capsys):
    with pytest.raises(SystemExit) as e:
        run.main([str(tmp_path), "--takeover", "1", *(["--replay"] if more else []), *more])
    assert "--takeover" in str(e.value)


class FakeGame:
    def __init__(self, world, version, server=None):
        self.world, self.port, self.kind = world, 0, "paper"

    def start(self):
        pass

    def stop(self):
        pass


def test_takeover_plays_the_replay_state(tmp_path, monkeypatch):
    (tmp_path / "level.dat").write_bytes(b"")
    (tmp_path / "aoe2mc.json").write_text(json.dumps({"players": {}}))
    r, got = object(), {}

    def fake_replay(game, world, speed, start, *args, stop=False, **kw):
        got["replay"] = (start, stop)
        return r

    def fake_write(game, replay, saves, t=None, difficulty=None):
        assert replay is r and difficulty == "standard"
        return "SAVE"

    def fake_play(game, world, log=None, cheats=False, bot=0, *args, state=None, people=None, wait=None, **kw):
        got["play"] = (state, people, wait)
        got["bot"] = bot
        return None

    for name, value in [("Game", FakeGame), ("replay", fake_replay), ("play", fake_play), ("ctrl_c", lambda: None),
                        ("console", lambda g: threading.Thread()), ("show_titles", lambda g: None)]:
        monkeypatch.setattr(run, name, value)
    monkeypatch.setattr(takeover, "write", fake_write)
    monkeypatch.setattr(savegame, "read", lambda path: {"players": {"1": {"pop": 4}}, "from": path})
    run.main([str(tmp_path), "--replay", "--from", "0:30", "--takeover", "1"])
    assert got["replay"] == ("0:30", True)
    assert got["play"] == ({"players": {"1": {"pop": 4}}, "from": "SAVE"}, 1, False)
    assert got["bot"] == "all"                                         # a bot for each other player (#5452)


def test_replay_stops_at_its_start(tmp_path, monkeypatch):
    """stop=True: the first poll at the --from time ends the replay, and replay() returns the Replay of that run."""
    import replay
    import replay_input
    (tmp_path / "aoe2mc.json").write_text(json.dumps({"timeline": []}))
    seen = []

    def fake_live(make, speed, start, restart, poll=None, **kw):
        make()
        for t in (start - 1, start, start + 1):
            poll({"time": t})
            seen.append(t)
        return {}

    class Game:
        kind, game_port, version, world = "vanilla", 0, "26.3", str(tmp_path)

        def forceload(self):
            pass
    monkeypatch.setattr(replay, "live", fake_live)
    monkeypatch.setattr(replay, "Replay", lambda *a, **k: "R")
    monkeypatch.setattr(replay_input, "Input", lambda g: type("I", (), {"setup": lambda s: None,
                                                                        "__call__": lambda s, c: None})())
    monkeypatch.setattr(run, "save", lambda g: str(tmp_path / "saved"))
    assert run.replay(Game(), str(tmp_path), start="0:30", stop=True) == "R"
    assert seen == [29999]
