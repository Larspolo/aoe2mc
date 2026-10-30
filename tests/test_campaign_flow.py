"""#3817: a converted campaign of two scenarios: a victory in scenario 1 carries its key value into scenario 2 (#3504)."""
import contextlib
import io
import json
import os
import shutil
import sys
import types

import pytest
import scenarios
from test_campaign import campaign

import aoe2mc

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import run  # noqa: E402


@pytest.fixture(scope="module")
def converted(tmp_path_factory):
    d = tmp_path_factory.mktemp("flow")
    s1 = scenarios.tiny(str(d / "a.aoe2scenario"))
    s2 = scenarios.save(scenarios.new_scenario(8), str(d / "b.aoe2scenario"))
    c = campaign(d / "c.aoe2campaign", [s1, s2], name="Flow test")
    out = d / "out"
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.main([str(c), str(out)])
    return out


def test_a_victory_carries_its_key_value_into_scenario_2(converted, tmp_path, monkeypatch):
    folder = tmp_path / "camp"
    shutil.copytree(converted, folder)               # the game changes the worlds: each test gets its own copy
    seen = {"keys": None}
    monkeypatch.setattr(run, "PAUSE", 0)
    monkeypatch.setattr(run, "Game", lambda *a, **k: types.SimpleNamespace(
        start=lambda: None, stop=lambda: None, port=0, command=lambda c: None))
    monkeypatch.setattr(run, "console", lambda game: None)

    def play(game, world, *a, **k):
        name = os.path.basename(world)
        if name == "1 S1":                           # the trigger effect "Store Key Value" ends scenario 1 with a victory
            run.put_keys(world, {"v1": 7})
            return types.SimpleNamespace(ended="Victory")
        seen["keys"] = run.world_keys(world)         # scenario 2 starts with the key value of scenario 1
        return types.SimpleNamespace(ended=None)
    monkeypatch.setattr(run, "play", play)

    run.main([str(folder), "--play"])
    assert seen["keys"] == {"v1": 7}
    progress = json.loads((folder / "progress.json").read_text())
    assert progress["won"] == [1]
    assert progress["keys"] == {"v1": 7}
