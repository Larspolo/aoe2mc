"""The buildings of the game program turn with --orientation (#3035): a replay draws each building with the turn
of its map (`"turn"` in aoe2mc.json), as the converter does."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import data  # noqa: E402

import aoe2mc  # noqa: E402
import buildings  # noqa: E402


def door_facings(data_extra):
    """The facings of the door blocks of a HOUSE drawn by Replay.draw()."""
    d = data([]) | data_extra
    r = replay.Replay(None, d)
    cols, E, o = r.draw("HOUSE", 1, 8.0, 8.0)
    names = [aoe2mc.B.states[i] for p in E.parts for i in p[3].tolist() if i]
    return {s.split("[", 1)[1].split("]")[0].split(",")[0] for s in names if "_door[" in s}, buildings.TURN


def test_house_door_faces_south_with_no_turn():
    facings, turn = door_facings({})
    assert facings == {"facing=south"}
    assert turn == 0


def test_house_door_turns_with_the_map():
    facings, turn = door_facings({"turn": 1})
    assert facings == {"facing=west"}
    assert turn == 0


def test_aoe2mc_json_has_the_turn(tmp_path, monkeypatch):
    import json

    from test_terrain import columns
    cols = columns(np.zeros((4, 4)))
    players = {0: {"civ": "GAIA", "color": "light_gray", "arch": "western"}}
    out = tmp_path / "a.json"
    monkeypatch.setattr(buildings, "TURN", 1)
    aoe2mc.write_objects(str(out), 4, 4, 2, players, [], cols, np.zeros((cols.n, cols.n), int))
    assert json.load(open(out))["turn"] == 1
    monkeypatch.setattr(buildings, "TURN", 0)
    aoe2mc.write_objects(str(out), 4, 4, 2, players, [], cols, np.zeros((cols.n, cols.n), int))
    assert "turn" not in json.load(open(out))
