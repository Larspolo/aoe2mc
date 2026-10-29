"""#3520: one difficulty for all scenarios of a campaign, kept in progress.json."""
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
    seen = {"levels": [], "ends": []}
    monkeypatch.setattr(run, "PAUSE", 0)
    monkeypatch.setattr(run, "Game", lambda *a, **k: types.SimpleNamespace(
        start=lambda: None, stop=lambda: None, port=0, command=lambda c: None))

    def play(game, world, *a, **k):
        seen["levels"].append((os.path.basename(world), k["ai_difficulty"]))
        return types.SimpleNamespace(ended=seen["ends"].pop(0) if seen["ends"] else None)
    monkeypatch.setattr(run, "play", play)
    monkeypatch.setattr(run, "console", lambda game: None)
    return tmp_path, seen


def test_the_campaign_keeps_its_first_difficulty(folder, capsys):
    tmp_path, seen = folder
    seen["ends"] = ["Victory"]
    run.main([str(tmp_path), "--play", "--ai-difficulty", "hard"])
    assert json.loads((tmp_path / "progress.json").read_text())["difficulty"] == "hard"
    assert seen["levels"] == [("1 S1", "hard"), ("2 S2", "hard")]
    run.main([str(tmp_path), "--play", "--ai-difficulty", "easiest"])
    assert seen["levels"][-1] == ("2 S2", "hard")
    assert "The campaign difficulty is hard." in capsys.readouterr().err
    assert json.loads((tmp_path / "progress.json").read_text()) == {"difficulty": "hard", "won": [1]}
