"""default_terrain_replacement of <CONNECTION_GENERATION> (#3870)."""
import numpy as np

import rmap
from test_rms_connections import FORDS

W, S, G, R = (rmap.TERRAINS[k] for k in ("WATER", "SHALLOW", "GRASS", "ROAD"))


def test_the_default_replacement_gives_road_on_land_and_a_replace_terrain_line_wins_on_water():
    plain = np.array(rmap.generate(FORDS % "", 3, size=80)["terrain"])
    t = np.array(rmap.generate(FORDS % "default_terrain_replacement ROAD\n", 3, size=80, warn=print)["terrain"])
    assert (t == R).any() and (plain[t == R] == G).all()             # road only where the land was
    assert ((t == S) == (plain == S)).all()                            # the water tiles of the path stay shallows

