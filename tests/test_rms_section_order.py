"""The sections of a random map script run in the AoE2 DE order: the hills before the terrains (#3966)."""
import numpy as np
import pytest

import rmap

LAND = """<LAND_GENERATION>
base_terrain GRASS
create_land { terrain_type DIRT number_of_tiles 300 base_size 4 land_position 80 80 }
"""
HILLS = "<ELEVATION_GENERATION>\ncreate_elevation 3 { base_terrain GRASS number_of_clumps 4 number_of_tiles 400 }\n"
FOREST = "<TERRAIN_GENERATION>\ncreate_terrain FOREST { base_terrain GRASS number_of_clumps 10 number_of_tiles 800 }\n"
LAKE = "<TERRAIN_GENERATION>\ncreate_terrain WATER { base_terrain GRASS number_of_tiles 1500 }\n"


def levels(text, seed):
    d = rmap.generate(text, seed, size=60, warn=lambda m: pytest.fail(m))
    return np.array(d["elevation"]), np.array(d["terrain"])


@pytest.mark.parametrize("seed", range(1, 4))
def test_forests_stand_on_the_hills(seed):
    e, t = levels(LAND + FOREST + HILLS, seed)        # the elevation section after the terrain one in the text
    assert (e[t == rmap.TERRAINS["FOREST"]] >= 1).any()


@pytest.mark.parametrize("seed", range(1, 4))
def test_a_lake_on_a_hill_steps_down_one_level_per_tile(seed):
    e, t = levels(LAND + HILLS + LAKE, seed)
    assert not e[t == rmap.TERRAINS["WATER"]].any()
    p = np.pad(e, 1, mode="edge")
    low = np.minimum.reduce([p[2:, 1:-1], p[:-2, 1:-1], p[1:-1, 2:], p[1:-1, :-2]])
    assert (low >= e - 1).all()                        # no step of 2 levels: no wall of blocks


def test_the_same_seed_gives_the_same_map():
    assert levels(LAND + HILLS + FOREST, 7)[0].tolist() == levels(LAND + HILLS + FOREST, 7)[0].tolist()
    assert levels(LAND + HILLS + FOREST, 7)[1].tolist() == levels(LAND + HILLS + FOREST, 7)[1].tolist()
