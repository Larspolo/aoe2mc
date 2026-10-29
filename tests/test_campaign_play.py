"""#3506: `run.py OUT --play` on the folder of a converted campaign plays one scenario in the scenario mode."""
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
    seen = {"commands": []}
    monkeypatch.setattr(run, "Game", lambda *a, **k: types.SimpleNamespace(
        start=lambda: None, stop=lambda: None, port=0, command=seen["commands"].append))
    monkeypatch.setattr(run, "play", lambda game, world, *a, **k: seen.update(k, world=world, titles=game.titles)
                        or types.SimpleNamespace(ended=None))
    monkeypatch.setattr(run, "console", lambda game: None)
    return tmp_path, seen


def test_the_first_scenario_starts_in_the_scenario_mode(folder):
    tmp_path, seen = folder
    run.main([str(tmp_path), "--play"])
    assert seen["world"] == str(tmp_path / "1 S1") and seen["mode"] == "scenario"
    assert seen["titles"] == ["Camp", "Scenario 1: S1"] and seen["commands"] == []   # start_on_join sends them (#3772)


def test_the_scenario_option_picks_the_world(folder):
    tmp_path, seen = folder
    run.main([str(tmp_path), "--play", "--scenario", "2"])
    assert seen["world"] == str(tmp_path / "2 S2") and seen["mode"] == "scenario"


def test_a_wrong_scenario_names_the_open_ones(folder):
    tmp_path, _ = folder
    with pytest.raises(SystemExit) as e:
        run.main([str(tmp_path), "--play", "--scenario", "3"])
    assert "1 (S1)" in str(e.value) and "2 (S2)" in str(e.value)
