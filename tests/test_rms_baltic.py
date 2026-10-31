"""A land with borders and no border_fuzziness grows with an irregular edge, as the Baltic sea of AoE2 DE (#5382)."""
import numpy as np

import rmap

SCRIPT = """<LAND_GENERATION>
base_terrain GRASS
create_land { terrain_type WATER land_percent 100 left_border 10 right_border 10 top_border 38 bottom_border 38 }
"""


def sea(seed=1):
    d = rmap.generate(SCRIPT, seed, 2, size=100, warn=lambda w: None)
    return np.array(d["terrain"]) == rmap.generate(SCRIPT, seed, 2, size=100, warn=lambda w: None)["terrain"][50][50]


def test_the_edge_of_the_sea_is_not_straight():
    wet = sea()
    top = [int(np.argmax(wet[x])) for x in range(20, 80)]      # the first water tile of each column
    assert len(set(top)) > 2


def test_the_sea_stays_near_its_box():
    wet = sea()
    assert not wet[:, :25].any() and not wet[:, 75:].any()
