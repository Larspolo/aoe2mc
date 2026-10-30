"""beach_terrain and spacing_to_specific_terrain of create_terrain in a random map script (#4426)."""
import numpy as np
import pytest

import rmap

LAND = """<LAND_GENERATION>
base_terrain GRASS
create_player_lands { terrain_type GRASS land_percent 60 base_size 6 }
<TERRAIN_GENERATION>
"""
T = rmap.TERRAINS


def make(tail, seed=3):
    return np.array(rmap.generate(LAND + tail, seed, size=100, warn=lambda m: pytest.fail(m))["terrain"])


def test_beach_terrain_gives_the_shore_of_the_water():
    t = make("create_terrain WATER { base_terrain GRASS number_of_tiles 400 beach_terrain DIRT }\n")
    water = t == T["WATER"]
    shore = rmap.dilate(water, 1) & ~water
    assert water.any() and (t[shore] == T["DIRT"]).all()
    assert (t[~shore & ~water] != T["DIRT"]).all()


def test_spacing_to_specific_terrain_keeps_the_distance():
    t = make("create_terrain FOREST { base_terrain GRASS number_of_tiles 300 }\n"
             "create_terrain DIRT { base_terrain GRASS number_of_tiles 300 spacing_to_specific_terrain FOREST 3 }\n")
    dirt = t == T["DIRT"]
    assert dirt.any() and not (dirt & rmap.dilate(t == T["FOREST"], 3)).any()


def test_same_map_for_the_same_seed():
    tail = "create_terrain WATER { base_terrain GRASS number_of_tiles 400 beach_terrain DIRT }\n"
    assert (make(tail, 5) == make(tail, 5)).all()
