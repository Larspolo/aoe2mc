"""The trigger of a live replay takes over a player of the record (#5601): /trigger aoe_replay set TAKEOVER + p."""
import json
import threading

import replay_input
import run
import savegame
import takeover

PLAYERS = {1: ("Player 1 (Britons)", "blue"), 2: ("Player 2 (Franks)", "red")}


def test_trigger_sets_the_player():
    control = {"players": PLAYERS}
    assert replay_input.apply(replay_input.TAKEOVER + 2, control) == "Take over player 2"
    assert control["takeover"] == 2


def test_trigger_of_a_missing_player_changes_nothing():
    control = {"players": PLAYERS}
    assert replay_input.apply(replay_input.TAKEOVER + 5, control) is None
    assert "takeover" not in control


def test_chat_line_clicks_each_player():
    line = json.loads(replay_input.takeover_text(PLAYERS))
    cmds = [x["click_event"]["command"] for x in line["extra"] if "click_event" in x]
    assert cmds == [f"/trigger {replay_input.OBJECTIVE} set {replay_input.TAKEOVER + p}" for p in PLAYERS]


class FakeGame:
    def __init__(self, world, version, server=None):
        self.world, self.port, self.kind, self.joined = world, 0, "paper", frozenset()

    def command(self, cmd):
        pass

    def start(self):
        pass

    def stop(self):
        pass


def test_trigger_plays_the_player(tmp_path, monkeypatch):
    (tmp_path / "level.dat").write_bytes(b"")
    (tmp_path / "aoe2mc.json").write_text(json.dumps({"players": {}}))
    r, got = object(), {}

    def fake_replay(game, world, speed, start, *args, stop=False, **kw):
        got["stop"] = stop
        return run.Taken(r, 2)

    def fake_write(game, replay, saves, t=None, taken=None, difficulty=None, bot_attack=None):
        assert replay is r
        got["taken"] = taken
        return "SAVE"

    def fake_play(game, world, log=None, cheats=False, bot=0, *args, state=None, people=None, wait=None, **kw):
        got["play"] = (bot, people, game.seats)

    for name, value in [("Game", FakeGame), ("replay", fake_replay), ("play", fake_play), ("ctrl_c", lambda: None),
                        ("console", lambda g: threading.Thread()), ("show_titles", lambda g: None)]:
        monkeypatch.setattr(run, name, value)
    monkeypatch.setattr(takeover, "write", fake_write)
    monkeypatch.setattr(savegame, "read", lambda path: {"players": {}})
    run.main([str(tmp_path), "--replay"])
    assert got == {"stop": False, "taken": 2, "play": ("all", 1, (2,))}


def test_replay_stops_at_the_trigger(tmp_path, monkeypatch):
    import replay
    (tmp_path / "aoe2mc.json").write_text(json.dumps({"timeline": []}))

    def fake_live(make, speed, start, restart, poll=None, **kw):
        make()
        poll({"time": 5})
        poll({"time": 6, "takeover": 2})
        raise AssertionError("no stop")

    class Game:
        kind, game_port, version, world = "vanilla", 0, "26.3", str(tmp_path)

        def forceload(self):
            pass
    monkeypatch.setattr(replay, "live", fake_live)
    monkeypatch.setattr(replay, "Replay", lambda *a, **k: "R")
    monkeypatch.setattr(replay_input, "Input", lambda g: type("I", (), {"setup": lambda s: None,
                                                                        "__call__": lambda s, c: None})())
    monkeypatch.setattr(run, "save", lambda g: str(tmp_path / "saved"))
    assert run.replay(Game(), str(tmp_path)) == ("R", 2)
