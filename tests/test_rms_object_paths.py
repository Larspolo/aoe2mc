"""The placement flags require_path, force_placement and ignore_terrain_restrictions of create_object (#4137)."""
import numpy as np
import pytest

import rmap

N = 40
START = {"x": 3, "y": 3, "player": 1, "land": 0}


def land():
    t = np.full((N, N), rmap.TERRAINS["GRASS"])
    t[10:38, 10:38] = rmap.TERRAINS["WATER"]       # a closed ring of water around the tiles 12 to 35
    t[12:36, 12:36] = rmap.TERRAINS["GRASS"]
    return t


def run(attrs, terrain, seed=1, warn=lambda m: pytest.fail(m)):
    cmds = [("create_object", ["STONE"], attrs)]
    return rmap.objects(cmds, rmap.TERRAINS | rmap.OBJECTS, terrain, [START], np.random.default_rng(seed), warn)


@pytest.mark.parametrize("seed", range(1, 4))
def test_require_path(seed):
    attrs = {"number_of_objects": ["20"], "set_gaia_object_only": [], "set_place_for_every_player": [], "require_path": []}
    out = run(attrs, land(), seed)
    assert len(out) == 20
    assert not any(12 <= o["x"] < 36 and 12 <= o["y"] < 36 for o in out)


def test_force_placement():
    t = np.full((N, N), rmap.TERRAINS["WATER"])
    t[:2, :2] = rmap.TERRAINS["GRASS"]             # 1 free tile: a stone uses 2 × 2 tiles
    warns = []
    out = run({"number_of_objects": ["5"], "force_placement": []}, t, warn=warns.append)
    assert len(out) == 5 and not any("no free tile" in w for w in warns)


def test_ignore_terrain_restrictions():
    t = np.full((N, N), rmap.TERRAINS["WATER"])
    out = run({"number_of_objects": ["3"], "terrain_to_place_on": ["WATER"], "ignore_terrain_restrictions": []}, t)
    assert len(out) == 3 and all(t[int(o["x"]), int(o["y"])] == rmap.TERRAINS["WATER"] for o in out)
