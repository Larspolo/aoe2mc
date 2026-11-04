"""The shore of a sea with borders varies by more than 2 tiles from its box, as the Baltic sea of AoE2 DE (#5716)."""
import numpy as np

import rmap

SCRIPT = """<LAND_GENERATION>
base_terrain GRASS
create_land { terrain_type WATER land_percent 100 base_size 15 left_border 10 right_border 10 top_border 38 bottom_border 38 }
"""


def test_the_shore_varies_by_more_than_2_tiles():
    for seed in (1, 2, 3):
        t = np.array(rmap.generate(SCRIPT, seed, 2, size=100, warn=lambda w: None)["terrain"])
        wet = t == t[50][50]
        solid = wet & np.roll(wet, -1, 1) & np.roll(wet, -2, 1)    # the start of 3 water tiles: not a lone tile
        first = np.array([int(np.argmax(solid[x])) for x in range(20, 80)])
        shore = [np.median(first[i:i + 5]) for i in range(len(first) - 4)]     # the coast line, not its noise
        assert max(shore) - min(shore) > 2
