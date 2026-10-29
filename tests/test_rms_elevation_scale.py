"""set_scale_by_size, set_scale_by_groups and enable_balanced_elevation of a random map script (#3823)."""
import numpy as np
import pytest

import rmap

LAND = """<LAND_GENERATION>
base_terrain GRASS
create_player_lands { terrain_type GRASS land_percent 60 base_size 6 }
"""


def hills(extra, size, seed=3, elevation=True):
    tail = (f"<ELEVATION_GENERATION>\ncreate_elevation 2 {{ base_terrain GRASS number_of_tiles 600 {extra} }}\n"
            if elevation else f"<TERRAIN_GENERATION>\ncreate_terrain DIRT {{ base_terrain GRASS number_of_tiles 600 "
            f"number_of_clumps 4 {extra} }}\n")
    return rmap.generate(LAND + tail, seed, size=size, warn=lambda m: pytest.fail(m))


def test_scale_by_size_gives_4_times_the_hills_on_a_map_of_twice_the_side():
    small, big = ((np.array(hills("set_scale_by_size", n)["elevation"]) > 0).sum() for n in (100, 200))
    assert 3.4 <= big / small <= 4.2
    small, big = ((np.array(hills("", n)["elevation"]) > 0).sum() for n in (100, 200))
    assert 0.8 <= big / small <= 1.2


def test_scale_by_groups_scales_the_clumps():
    assert rmap.scaled({"set_scale_by_groups": []}, {}, 200, 3, 100) == (12, 100)
    assert rmap.scaled({}, {}, 200, 3, 100) == (3, 100)


@pytest.mark.parametrize("seed", range(1, 5))
def test_balanced_elevation_gives_each_player_land_the_same_hills(seed):
    d = rmap.generate(LAND + "<ELEVATION_GENERATION>\ncreate_elevation 2 { base_terrain GRASS number_of_tiles 600 "
                      "number_of_clumps 4 enable_balanced_elevation }\n", seed, size=100, warn=lambda m: pytest.fail(m))
    e = np.array(d["elevation"]) > 0
    st = d["lands"]
    near = [np.hypot(*np.mgrid[:100, :100] - np.array([s["x"], s["y"]])[:, None, None]) for s in st]
    a, b = e[near[0] < near[1]].sum(), e[near[0] >= near[1]].sum()
    assert a and b and abs(a - b) <= 0.2 * max(a, b)


def test_create_terrain_scales_its_tiles():
    small, big = ((np.array(hills("set_scale_by_size", n, elevation=False)["terrain"]) == rmap.TERRAINS["DIRT"]).sum()
                  for n in (100, 200))
    assert 3.4 <= big / small <= 4.2
