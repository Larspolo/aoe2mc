"""clumping_factor and spacing_to_other_terrain_types of create_elevation in a random map script (#5075)."""
import numpy as np
import pytest

import rmap

WET = """<LAND_GENERATION>
base_terrain GRASS
create_land { terrain_type WATER land_position 50 50 base_size 6 number_of_tiles 600 }
<ELEVATION_GENERATION>
create_elevation 1 { base_terrain GRASS number_of_clumps 6 number_of_tiles 2500 spacing_to_other_terrain_types 3 }
"""
CLUMP = """<LAND_GENERATION>
base_terrain GRASS
<ELEVATION_GENERATION>
create_elevation 1 {{ base_terrain GRASS number_of_clumps 4 number_of_tiles 800 clumping_factor {c} }}
"""


def edge(hill):
    """The hill tiles next to a tile with no hill (4 sides)."""
    p = np.pad(hill, 1)
    inner = p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
    return int((hill & ~inner).sum())


@pytest.mark.parametrize("seed", range(1, 4))
def test_no_hill_near_the_water(seed):
    d = rmap.generate(WET, seed, size=80, warn=lambda m: pytest.fail(m))
    e, wet = np.array(d["elevation"]), np.array(d["terrain"]) == rmap.TERRAINS["WATER"]
    assert wet.sum() >= 500 and (e > 0).sum() >= 500
    assert not (rmap.dilate(wet, 3) & (e > 0)).any()


def test_clumping_factor_changes_the_hills():
    low, high = (np.array(rmap.generate(CLUMP.format(c=c), 5, size=80, warn=lambda m: pytest.fail(m))["elevation"]) > 0
                 for c in (0, 40))
    assert not (low == high).all()
    assert edge(high) < edge(low)                 # a high clumping factor: rounder hills, a shorter edge


def test_the_same_seed_gives_the_same_map():
    assert rmap.generate(WET, 7, size=80) == rmap.generate(WET, 7, size=80)
