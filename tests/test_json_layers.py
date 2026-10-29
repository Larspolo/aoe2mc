"""aoe2mc.read_json: the optional "layer" key gives the land layer of each tile, as a DE scenario does (#3689)."""
import json

import pytest

import aoe2mc

GRASS, WATER, ROAD = 0, 22, 24          # GRASS_1, WATER_DEEP, ROAD (AoE2ScenarioParser TerrainId)


def write(tmp_path, **kw):
    """A 4 × 4 grass map with deep water at (3, 3); kw changes the keys of the description."""
    terrain = [[GRASS] * 4 for _ in range(4)]
    terrain[3][3] = WATER
    d = {"size": 4, "terrain": terrain, "layer": [[-1] * 4 for _ in range(4)], "players": {"1": {"civ": "BRITONS"}}} | kw
    path = tmp_path / "m.json"
    path.write_text(json.dumps(d))
    return str(path)


def test_a_road_layer_paints_the_land_and_keeps_the_water(tmp_path):
    layer = [[-1] * 4 for _ in range(4)]
    layer[0][0] = layer[1][2] = ROAD                 # two land tiles
    layer[3][3] = ROAD                               # the water tile
    _, terrain, *_ = aoe2mc.read_json(write(tmp_path, layer=layer))
    assert terrain[0, 0] == ROAD and terrain[1, 2] == ROAD
    assert terrain[3, 3] == WATER and terrain[2, 2] == GRASS


def test_a_layer_of_the_wrong_shape_is_an_error(tmp_path):
    with pytest.raises(aoe2mc.OptionError, match="\"layer\" must be 4 lists of 4 numbers"):
        aoe2mc.read_json(write(tmp_path, layer=[[-1] * 3] * 4))


def test_a_layer_with_an_unknown_id_is_an_error(tmp_path):
    layer = [[-1] * 4 for _ in range(4)]
    layer[0][1] = 999
    with pytest.raises(aoe2mc.OptionError, match="unknown layer IDs \\[999\\]"):
        aoe2mc.read_json(write(tmp_path, layer=layer))
