"""The DE map constants PLAYER_COUNT and MAPSCALE_AREA (the map area relative to a 100x100 map) in #const math (#4928)."""
import numpy as np
import pytest

import rmap

SCRIPT = """#const N (PLAYER_COUNT * 100)
#const M (MAPSCALE_AREA * 100)
<LAND_GENERATION>
base_terrain WATER
create_land { terrain_type GRASS number_of_tiles N land_position 50 50 }
create_land { terrain_type DESERT number_of_tiles M land_position 20 20 }
"""


@pytest.mark.parametrize("players,size", [(2, 120), (4, 200)])
def test_player_count_and_mapscale_area_follow_the_map(players, size):
    notes = []
    d = rmap.generate(SCRIPT, 1, players=players, size=size, warn=notes.append)
    assert not [m for m in notes if "unknown constant" in m]
    t = np.array(d["terrain"])
    assert np.count_nonzero(t == rmap.TERRAINS["GRASS"]) == players * 100
    assert np.count_nonzero(t == rmap.TERRAINS["DESERT"]) == size * size // 100
