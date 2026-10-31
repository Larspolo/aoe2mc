"""--scenario-dir DIR: the world of a recorded game gets the triggers of the scenario file that the record names
(#5157). The sample is a random map game, so the tests patch the name. Skip without mgz."""
import contextlib
import glob
import io
import json
import os

import pytest
import scenarios
from AoE2ScenarioParser.datasets.players import PlayerId

import aoe2mc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REC = os.path.join(ROOT, "samples", "de-63.0.aoe2record")
pytest.importorskip("mgz.model")


def convert(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        aoe2mc.main(argv)
    return out.getvalue()


def triggers(world):
    return glob.glob(os.path.join(world, "datapacks", "**", "function", "trigger", "*.mcfunction"), recursive=True)


def lobby(world):
    with open(os.path.join(world, "aoe2mc.json")) as f:
        return json.load(f)["lobby"]


def test_random_map_record_has_no_scenario_name(tmp_path):
    convert([REC, str(tmp_path / "W"), "--no-units"])
    assert lobby(str(tmp_path / "W"))["scenario"] == ""


@pytest.mark.parametrize("name", ["Hill.aoe2scenario", "Hill"])
def test_scenario_dir_finds_named_file(tmp_path, monkeypatch, name):
    scn = scenarios.new_scenario(aoe2mc.read_record(REC)[0])
    t = scn.trigger_manager.add_trigger("Welcome")
    t.new_condition.timer(timer=5)
    t.new_effect.send_chat(source_player=PlayerId.ONE, message="Welcome.")
    scenarios.save(scn, str(tmp_path / "Hill.aoe2scenario"))
    monkeypatch.setattr(aoe2mc, "record_scenario_name", lambda path: name)
    convert([REC, str(tmp_path / "W"), "--scenario-dir", str(tmp_path), "--no-units"])
    assert triggers(str(tmp_path / "W"))
    assert lobby(str(tmp_path / "W"))["scenario"] == name


def test_missing_file_warns_once(tmp_path, monkeypatch):
    monkeypatch.setattr(aoe2mc, "record_scenario_name", lambda path: "Gone.aoe2scenario")
    out = convert([REC, str(tmp_path / "W"), "--scenario-dir", str(tmp_path), "--no-units"])
    assert sum("warning: --scenario-dir" in line for line in out.splitlines()) == 1
    assert not triggers(str(tmp_path / "W"))
