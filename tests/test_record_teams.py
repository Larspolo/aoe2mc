"""The team of each player of a recorded game (#1188, epic #1187): read_record keeps it, aoe2mc.json writes it."""
import json
import os

import numpy as np
import pytest
from test_terrain import columns

import aoe2mc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pytest.importorskip("mgz.model")


def test_team_numbers():
    assert aoe2mc.team_numbers([[3, 1], [2, 4]]) == {1: 1, 3: 1, 2: 2, 4: 2}     # the team of player 1 is team 1
    assert aoe2mc.team_numbers([{4}, {2}]) == {2: 1, 4: 2}


@pytest.mark.parametrize("name", ["de-64.3.aoe2record", "hd-4.6.aoe2record"])
def test_record_teams(name):
    players = aoe2mc.read_record(os.path.join(ROOT, "samples", name))[6]
    assert players[0]["team"] is None and players[1]["team"] == 1 and players[2]["team"] == 2     # 1 against 1


def test_aoe2mc_json_has_the_teams(tmp_path):
    cols = columns(np.zeros((4, 4)))
    players = {0: {"civ": "GAIA", "color": "light_gray", "arch": "western", "team": None},
               1: {"civ": "FRANKS", "color": "blue", "arch": "western", "team": 2},
               2: {"civ": "HUNS", "color": "red", "arch": "western"}}         # a scenario: no team
    aoe2mc.write_objects(str(tmp_path / "a.json"), 4, 4, 2, players, [], cols, np.zeros((cols.n, cols.n), int))
    out = json.load(open(tmp_path / "a.json"))["players"]
    assert out["0"]["team"] is None and out["1"]["team"] == 2 and "team" not in out["2"]
