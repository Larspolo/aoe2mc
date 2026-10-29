"""create_elevation of <ELEVATION_GENERATION> in a random map script: hills level by level (#3822)."""
import numpy as np
import pytest

import rmap

LAND = """<LAND_GENERATION>
base_terrain GRASS
create_land { terrain_type WATER number_of_tiles 600 base_size 6 land_position 20 20 }
"""
HILLS = LAND + "<ELEVATION_GENERATION>\ncreate_elevation 3 { base_terrain GRASS number_of_tiles 400 }\n"


@pytest.mark.parametrize("seed", range(1, 6))
def test_hills_rise_level_by_level(seed):
    d = rmap.generate(HILLS, seed, size=80, warn=lambda m: pytest.fail(m))
    e, t = np.array(d["elevation"]), np.array(d["terrain"])
    assert {1, 2, 3} <= set(np.unique(e)) and e.max() == 3
    p = np.pad(e, 1, mode="edge")
    low = np.minimum.reduce([p[2:, 1:-1], p[:-2, 1:-1], p[1:-1, 2:], p[1:-1, :-2]])
    assert (low[e > 1] >= e[e > 1] - 1).all()                 # each level-k tile has its 4 neighbours at k - 1 or more
    assert not e[np.isin(t, [rmap.TERRAINS["WATER"], rmap.TERRAINS["SHALLOW"]])].any()
    assert 300 <= (e > 0).sum() <= 400


def test_the_same_seed_gives_the_same_levels():
    assert rmap.generate(HILLS, 7, size=80)["elevation"] == rmap.generate(HILLS, 7, size=80)["elevation"]


def test_a_script_with_no_elevation_gives_the_same_map():
    a, b = rmap.generate(LAND, 5, size=80), rmap.generate(LAND + "<ELEVATION_GENERATION>\n", 5, size=80)
    assert a == b and not np.array(a["elevation"]).any()
