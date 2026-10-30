"""other_zone_avoidance_distance and min_placement_distance of create_land in a random map script (#4421)."""
import itertools

import numpy as np
import pytest

import rmap

T = rmap.TERRAINS
AVOID = """<LAND_GENERATION>
base_terrain WATER
create_land { terrain_type GRASS number_of_tiles 900 base_size 2 land_position 40 50 zone 1 other_zone_avoidance_distance 4 }
create_land { terrain_type DIRT number_of_tiles 900 base_size 2 land_position 60 50 zone 2 other_zone_avoidance_distance 4 }
"""
FAR = """<LAND_GENERATION>
base_terrain WATER
create_land { terrain_type GRASS number_of_tiles 1 base_size 0 }
create_land { terrain_type DIRT number_of_tiles 1 base_size 0 min_placement_distance 30 }
create_land { terrain_type DESERT number_of_tiles 1 base_size 0 min_placement_distance 30 }
"""


def make(text, seed):
    return np.array(rmap.generate(text, seed, players=2, size=80, warn=lambda m: pytest.fail(m))["terrain"])


def test_lands_of_two_zones_keep_the_avoidance_distance():
    t = make(AVOID, 3)
    a, b = np.argwhere(t == T["GRASS"]), np.argwhere(t == T["DIRT"])
    assert len(a) > 100 and len(b) > 100
    gap = np.abs(a[:, None, :] - b[None, :, :]).max(axis=2).min()
    assert gap > 4
    assert (make(AVOID, 3) == t).all()


@pytest.mark.parametrize("seed", range(5))
def test_random_lands_keep_the_placement_distance(seed):
    t = make(FAR, seed)
    origins = [np.argwhere(t == T[k])[0] for k in ("GRASS", "DIRT", "DESERT")]
    assert all(np.hypot(*(p - q)) >= 30 for p, q in itertools.combinations(origins, 2))
    assert (make(FAR, seed) == t).all()
