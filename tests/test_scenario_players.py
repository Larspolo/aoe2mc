"""The start values of each scenario player in aoe2mc.json (#2539, epic #2538): the start resources, the population
limit and the computer flag of the tab "Players" of the editor, for the scenario mode of the game program."""
import json
import os

import numpy as np
import pytest
import scenarios
from test_scx import build

import aoe2mc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def scenario(path):
    """Player 1 with own start resources and population limit, player 2 a computer player."""
    scn = scenarios.new_scenario(24)
    one, two = scn.player_manager.players[1], scn.player_manager.players[2]
    one.food, one.wood, one.gold, one.stone, one.population_cap = 500, 400, 300, 200, 75
    two.human = False
    return scenarios.save(scn, path)


def test_aoe2mc_json_has_the_start_values_of_the_scenario(tmp_path):
    src = scenario(str(tmp_path / "s.aoe2scenario"))
    aoe2mc.main([src, str(tmp_path / "W")])
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        players = json.load(f)["players"]
    assert players["1"]["resources"] == {"food": 500, "wood": 400, "gold": 300, "stone": 200}
    assert players["1"]["pop_limit"] == 75 and players["1"]["computer"] is False
    assert players["2"]["computer"] is True and players["2"]["pop_limit"] == 200
    assert "resources" not in players["0"]                              # Gaia plays no game


def test_an_old_scenario_has_no_start_values(tmp_path):
    src = build(tmp_path / "old.scx", np.zeros((16, 16), np.int16), np.zeros((16, 16), np.float32),
                {1: (1, 1, (6.0, 6.0))})
    players = aoe2mc.read_scx(str(src))[-1]
    assert not any(k in p for p in players.values() for k in ("resources", "pop_limit", "computer"))


def test_a_record_has_no_start_values():
    pytest.importorskip("mgz.model")
    players = aoe2mc.read_record(os.path.join(ROOT, "samples", "de-64.3.aoe2record"))[6]
    assert not any(k in p for p in players.values() for k in ("resources", "pop_limit", "computer"))
