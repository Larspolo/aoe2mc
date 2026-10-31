"""A random map world keeps its lobby map size and game mode and the script name (#5102) in aoe2mc.json (#4825)."""
import json

import pytest

import aoe2mc
from game import run

SCRIPT = "<LAND_GENERATION>\nbase_terrain GRASS\n"


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    d = tmp_path_factory.mktemp("lobby")
    (d / "a.rms").write_text(SCRIPT, encoding="utf-8")
    aoe2mc.main([str(d / "a.rms"), str(d / "W"), "--game-mode", "regicide", "--map-size", "tiny", "--no-units"])
    return d / "W"


def test_the_world_has_the_lobby(world):
    lobby = json.loads((world / "aoe2mc.json").read_text())["lobby"]
    assert lobby == {"map_size": "tiny", "mode": "regicide", "script": "a"}


def test_the_lobby_mode_is_the_default_and_an_option_wins(world, monkeypatch):
    seen = []
    lobby_mode = run.lobby_mode
    monkeypatch.setattr(run, "lobby_mode", lambda *x: seen.append(lobby_mode(*x)) or seen[-1])
    monkeypatch.setattr(run, "civ_choices", lambda *x: (_ for _ in ()).throw(SystemExit(0)))
    with pytest.raises(SystemExit):
        run.main([str(world)])
    assert seen == ["regicide"]
    with pytest.raises(SystemExit):
        run.main([str(world), "--mode", "standard"])
    assert seen == ["regicide"]                         # the option wins: no read of the lobby


def test_a_world_without_lobby_keeps_the_default(tmp_path):
    (tmp_path / "aoe2mc.json").write_text(json.dumps({"map_size": 10}))
    assert run.lobby_mode(str(tmp_path), "standard") == "standard"
    assert run.lobby_mode(str(tmp_path / "none"), "standard") == "standard"
