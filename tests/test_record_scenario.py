"""--scenario FILE: the world of a recorded game gets the triggers and texts of a scenario file (#5156). Skip without mgz."""
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


def scenario(path, size):
    scn = scenarios.new_scenario(size)
    scn.message_manager.instructions = "Hold the hill."
    t = scn.trigger_manager.add_trigger("Welcome")
    t.new_condition.timer(timer=5)
    t.new_effect.send_chat(source_player=PlayerId.ONE, message="Welcome.")
    return scenarios.save(scn, str(path))


def convert(argv):
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.main(argv)


def trigger_files(world):
    return glob.glob(os.path.join(world, "datapacks", "**", "function", "trigger", "*.mcfunction"), recursive=True)


def test_scenario_gives_triggers_and_texts(tmp_path):
    size = aoe2mc.read_record(REC)[0]
    convert([REC, str(tmp_path / "W"), "--scenario", scenario(tmp_path / "s.aoe2scenario", size), "--no-units"])
    assert trigger_files(str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        assert "Hold the hill." in json.dumps(json.load(f))
    convert([REC, str(tmp_path / "V"), "--no-units"])
    assert not trigger_files(str(tmp_path / "V"))


def test_other_map_size_stops(tmp_path, capsys):
    size = aoe2mc.read_record(REC)[0]
    with pytest.raises(SystemExit):
        convert([REC, str(tmp_path / "W"), "--scenario", scenario(tmp_path / "s.aoe2scenario", size - 24)])
    err = capsys.readouterr().err
    assert f"map size {size - 24}" in err and f"recorded game: {size}" in err
