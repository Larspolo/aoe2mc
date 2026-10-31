"""#3507: after a victory in a campaign scenario the next one starts, after a loss the same one; progress.json keeps it."""
import json
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import run  # noqa: E402


@pytest.fixture
def folder(tmp_path, monkeypatch):
    for w in ("1 S1", "2 S2"):
        (tmp_path / w).mkdir()
        (tmp_path / w / "level.dat").write_bytes(b"")
    (tmp_path / "campaign.json").write_text(json.dumps({"name": "Camp", "scenarios": [
        {"number": 1, "name": "S1", "world": "1 S1"}, {"number": 2, "name": "S2", "world": "2 S2"}]}))
    seen = {"worlds": [], "commands": [], "ends": []}
    monkeypatch.setattr(run, "PAUSE", 0)
    monkeypatch.setattr(run, "Game", lambda *a, **k: types.SimpleNamespace(
        start=lambda: None, stop=lambda: None, port=0, command=seen["commands"].append))

    def play(game, world, *a, **k):                  # the next end of the list, else no end (the person stops)
        seen["worlds"].append(os.path.basename(world))
        (tmp_path / os.path.basename(world) / "changed").write_text("")   # the game changes the world
        return types.SimpleNamespace(ended=seen["ends"].pop(0) if seen["ends"] else None)
    monkeypatch.setattr(run, "play", play)
    monkeypatch.setattr(run, "console", lambda game: None)
    return tmp_path, seen


def test_a_victory_starts_the_next_scenario(folder):
    tmp_path, seen = folder
    seen["ends"] = ["Victory"]
    run.main([str(tmp_path), "--play"])
    assert seen["worlds"] == ["1 S1", "2 S2"]
    assert json.loads((tmp_path / "progress.json").read_text()) == {"won": [1], "difficulty": "standard"}
    assert any(c.startswith("tellraw @a ") and '"with": ["2"]' in c and "aoe2mc.run.scenario_starts" in c
               for c in seen["commands"])


def test_a_loss_starts_the_same_scenario_on_the_converted_world(folder):
    tmp_path, seen = folder
    seen["ends"] = ["Defeat"]
    run.main([str(tmp_path), "--play"])
    assert seen["worlds"] == ["1 S1", "1 S1"]
    assert "won" not in json.loads((tmp_path / "progress.json").read_text())
    assert (tmp_path / ".start" / "1 S1" / "level.dat").exists() and not (tmp_path / ".start" / "1 S1" / "changed").exists()


def test_the_last_victory_completes_the_campaign(folder):
    tmp_path, seen = folder
    seen["ends"] = ["Victory", "Victory"]
    run.main([str(tmp_path), "--play"])
    assert seen["worlds"] == ["1 S1", "2 S2"]
    assert json.loads((tmp_path / "progress.json").read_text()) == {"won": [1, 2], "difficulty": "standard"}
    assert any(c.startswith("title @a title ") and "aoe2mc.run.campaign_complete" in c for c in seen["commands"])


def test_a_second_start_plays_the_first_open_scenario(folder):
    tmp_path, seen = folder
    (tmp_path / "progress.json").write_text(json.dumps({"won": [1]}))
    run.main([str(tmp_path), "--play"])
    assert seen["worlds"] == ["2 S2"]
