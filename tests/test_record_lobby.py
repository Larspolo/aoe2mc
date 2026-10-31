"""The lobby settings of a recorded game in aoe2mc.json (#4832). Skip without `mgz`."""
import json
import os

import pytest

import aoe2mc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REC = os.path.join(ROOT, "samples", "de-64.3.aoe2record")


@pytest.mark.slow
def test_record_keeps_the_lobby_settings(tmp_path):
    mgz = pytest.importorskip("mgz.model")
    with open(REC, "rb") as f:
        m = mgz.parse_match(f)
    aoe2mc.main([REC, str(tmp_path / "W"), "--at", "0:00"])
    lobby = json.load(open(tmp_path / "W" / "aoe2mc.json"))["lobby"]
    assert lobby == {"type": m.type, "dataset": m.dataset, "starting_age": m.starting_age,
                     "population": m.population, "all_techs": m.all_technologies, "reveal": m.map_reveal}


def test_scenario_has_no_record_lobby(tiny_world):
    world, _ = tiny_world
    data = json.load(open(os.path.join(world, "aoe2mc.json")))
    assert not {"type", "dataset", "starting_age", "population", "all_techs", "reveal"} & set(data.get("lobby", {}))
