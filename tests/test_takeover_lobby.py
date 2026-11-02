"""A takeover game plays with the lobby settings of the record (#5603): mode, population, All Techs, Reveal Map."""
import json
import threading

import pytest
import run
import savegame
import table
import takeover

LOBBY = {r["lobby"]: r for r in table.load("setup.jsonl") if "lobby" in r}


class FakeGame:
    def __init__(self, world, version, server=None):
        self.world, self.port, self.kind = world, 0, "paper"

    def start(self):
        pass

    def stop(self):
        pass


def takeover_play(tmp_path, monkeypatch, lobby, *more):
    (tmp_path / "level.dat").write_bytes(b"")
    (tmp_path / "aoe2mc.json").write_text(json.dumps({"players": {}, "lobby": lobby}))
    got = {}

    def fake_play(game, world, log=None, cheats=False, bot=0, *args, **kw):
        got.update(kw, settings=game.settings)

    for name, value in [("Game", FakeGame), ("replay", lambda *a, **k: object()), ("play", fake_play),
                        ("ctrl_c", lambda: None), ("console", lambda g: threading.Thread()),
                        ("show_titles", lambda g: None)]:
        monkeypatch.setattr(run, name, value)
    monkeypatch.setattr(takeover, "write", lambda *a, **k: "SAVE")
    monkeypatch.setattr(savegame, "read", lambda path: {"players": {}})
    run.main([str(tmp_path), "--replay", "--takeover", "1", *more])
    return got


@pytest.mark.parametrize("kind", sorted(LOBBY))
def test_lobby_type_gives_its_mode(kind, tmp_path, monkeypatch):
    r, got = LOBBY[kind], takeover_play(tmp_path, monkeypatch, {"type": kind})
    if "victory" in r:
        assert got["victory"] == r["victory"]
    elif r["name"] in run.ON_TOP:
        assert got[r["name"].replace("-", "_")] is True and got["mode"] == "standard"
    else:
        assert got["mode"] == r["name"]
    assert got["settings"]["mode"] == got["mode"]                     # savegame.dump keeps it


def test_lobby_settings(tmp_path, monkeypatch):
    got = takeover_play(tmp_path, monkeypatch, {"type": "Random Map", "population": 150, "all_techs": True,
                                                "reveal": "All Visible"})
    assert (got["mode"], got["pop_limit"], got["all_techs"], got["reveal"]) == ("standard", 150, True, "all")


def test_given_options_win(tmp_path, monkeypatch):
    kind = next(k for k, r in sorted(LOBBY.items()) if r["name"] in run.ON_TOP)
    got = takeover_play(tmp_path, monkeypatch, {"type": kind, "population": 150, "reveal": "Explored"},
                        "--pop-limit", "75", "--reveal", "normal", "--mode", "standard")
    assert (got["pop_limit"], got["reveal"], got["mode"]) == (75, "normal", "standard")
    assert not got[LOBBY[kind]["name"].replace("-", "_")]
