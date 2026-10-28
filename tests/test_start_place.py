"""#3345: the start place of each player: find_spawn(pid=...) and the "start" and "yaw" keys of aoe2mc.json."""
import json

import numpy as np

import aoe2mc


def cols():
    t = np.zeros((20, 20), np.int16)
    return aoe2mc.Columns(20, t, np.zeros((20, 20), np.float32), {0: "GRASS_1"}, 4, 2,
                          np.random.default_rng(1))


def test_start_view_of_another_player():
    x, y, z = aoe2mc.find_spawn(cols(), [], {2: {"view": (15, 3)}}, pid=2)
    assert (x, z) == (60, 12)
    assert y == cols().surface(60, 12) + 2


def test_in_front_of_the_town_center_of_another_player():
    c = cols()
    tc = dict(kind="B", name="TOWN_CENTER", player=2, x=6.0, y=6.0)
    c.blocked[16:32, 16:32] = True                  # the town center (4 x 4 tiles)
    x, _, z = aoe2mc.find_spawn(c, [tc], {2: {"view": None}}, pid=2)
    assert (x, z) == (24, 34) and not c.blocked[x, z]


def test_no_start_for_another_player_without_view_or_town_center():
    assert aoe2mc.find_spawn(cols(), [], {2: {"view": None}}, pid=2) is None
    assert aoe2mc.find_spawn(cols(), [], {}, pid=3) is None


def test_json_has_start_of_each_player_and_yaw(tmp_path):
    players = {0: {"color": "light_gray", "arch": "western", "civ": "GAIA"},
               1: {"color": "blue", "arch": "western", "civ": "BRITONS", "start": [8, 3, 9]},
               2: {"color": "red", "arch": "western", "civ": "FRANKS", "start": [60, 3, 12]}}
    path = tmp_path / "aoe2mc.json"
    c = cols()
    aoe2mc.write_objects(str(path), 20, 4, 2, players, [], c, np.zeros((c.n, c.n), int), yaw=45.0)
    data = json.loads(path.read_text())
    assert data["yaw"] == 45.0
    assert data["players"]["1"]["start"] == [8, 3, 9]
    assert data["players"]["2"]["start"] == [60, 3, 12]
    assert "start" not in data["players"]["0"]


def test_default_yaw_is_the_spawn_yaw(tmp_path):
    players = {1: {"color": "blue", "arch": "western", "civ": "BRITONS"}}
    path = tmp_path / "aoe2mc.json"
    c = cols()
    aoe2mc.write_objects(str(path), 20, 4, 2, players, [], c, np.zeros((c.n, c.n), int))
    assert json.loads(path.read_text())["yaw"] == aoe2mc.SPAWN_YAW
