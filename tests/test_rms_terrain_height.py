"""create_terrain with height_limits and set_flat_terrain_only in a random map script (#4425)."""
import numpy as np
import pytest

import rmap

LAND = """<LAND_GENERATION>
base_terrain GRASS
create_land { terrain_type WATER number_of_tiles 600 base_size 6 land_position 20 20 }
"""
HILLS = "<ELEVATION_GENERATION>\ncreate_elevation 3 { base_terrain GRASS number_of_tiles 400 }\n"


def script(terrain_attrs):
    return LAND + HILLS + f"<TERRAIN_GENERATION>\ncreate_terrain DIRT {{ base_terrain GRASS number_of_tiles 800 {terrain_attrs} }}\n"


@pytest.mark.parametrize("seed", range(1, 4))
def test_height_limits_put_the_terrain_on_the_hill_levels_from_min(seed):
    d = rmap.generate(script("height_limits 2 7"), seed, size=80, warn=lambda m: pytest.fail(m))
    e, t = np.array(d["elevation"]), np.array(d["terrain"])
    dirt = t == rmap.TERRAINS["DIRT"]
    assert dirt.any()
    assert (e[dirt] >= 2).all()


@pytest.mark.parametrize("seed", range(1, 4))
def test_set_flat_terrain_only_puts_no_terrain_on_a_slope(seed):
    d = rmap.generate(script("set_flat_terrain_only"), seed, size=80, warn=lambda m: pytest.fail(m))
    e, t = np.array(d["elevation"]), np.array(d["terrain"])
    rows, cols = np.nonzero(t == rmap.TERRAINS["DIRT"])
    inside = (rows > 0) & (cols > 0) & (rows < e.shape[0] - 1) & (cols < e.shape[1] - 1)
    assert inside.any()
    for r, c in zip(rows[inside], cols[inside]):
        assert (e[r - 1:r + 2, c - 1:c + 2] == e[r, c]).all()


def test_the_same_seed_gives_the_same_map():
    text = script("height_limits 2 7 set_flat_terrain_only")
    assert rmap.generate(text, 4, size=80) == rmap.generate(text, 4, size=80)
