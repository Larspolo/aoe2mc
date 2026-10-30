"""The DE map constant MAPSIZE_SIDE of a random map script (#4693): the side of the map in tiles."""
import numpy as np
import pytest

import rmap

SCRIPT = """#const N (MAPSIZE_SIDE / 2)
<LAND_GENERATION>
base_terrain WATER
create_land { terrain_type GRASS number_of_tiles N land_position 50 50 }
"""


@pytest.mark.parametrize("size", [120, 200])
def test_a_const_of_mapsize_side_follows_the_map_size(size):
    notes = []
    d = rmap.generate(SCRIPT, 1, size=size, warn=notes.append)
    assert notes == []
    assert np.count_nonzero(np.array(d["terrain"]) == rmap.TERRAINS["GRASS"]) == size // 2
