"""base_elevation of create_land and create_player_lands (#4418): the land is raised to that level, its edge steps up
one level per tile, the base terrain far from it stays at 0."""
import numpy as np
import pytest

import rmap

LAND = "<LAND_GENERATION>\nbase_terrain GRASS\ncreate_land { terrain_type DIRT number_of_tiles 400 base_size 6 land_position 50 50 base_elevation 3 }\n"
PLAYERS = "<LAND_GENERATION>\nbase_terrain GRASS\ncreate_player_lands { terrain_type DIRT number_of_tiles 600 base_size 6 base_elevation 3 }\n"


def level(text, seed=1):
    d = rmap.generate(text, seed, size=80, warn=lambda m: pytest.fail(m))
    return d, np.array(d["elevation"])


def test_a_land_is_raised_at_its_origin_and_not_far_from_it():
    d, e = level(LAND)
    assert e[40, 40] == 3 and e[0, 0] == 0 and e[79, 79] == 0
    assert np.abs(np.diff(e, axis=0)).max() <= 1 and np.abs(np.diff(e, axis=1)).max() <= 1   # a slope, no wall
    assert d == level(LAND)[0]


def test_each_player_land_is_raised_at_its_origin():
    d, e = level(PLAYERS)
    assert d["lands"] and all(e[land["x"], land["y"]] == 3 for land in d["lands"])
    assert e[0, 0] == 0 and d == level(PLAYERS)[0]
