"""create_terrain changes the start square of a player unless set_avoid_player_start_areas is set (#5738)."""
import numpy as np

import rmap

SCRIPT = """<PLAYER_SETUP>
random_placement
<LAND_GENERATION>
base_terrain GRASS
create_player_lands { terrain_type 8 number_of_tiles 512 base_size 12 clumping_factor 15 other_zone_avoidance_distance 2 }
<TERRAIN_GENERATION>
create_terrain 7 { base_terrain 8 land_percent 100 number_of_clumps 1 %s}
create_terrain 24 { base_terrain 8 land_percent 100 number_of_clumps 1 %s}
"""


def count(extra):
    t = np.array(rmap.generate(SCRIPT % (extra, extra), 1, size=120)["terrain"])
    return int((t == 8).sum())


def test_no_avoidance_replaces_start_squares():
    assert count("") < 100


def test_avoidance_keeps_start_squares():
    assert count("set_avoid_player_start_areas ") > 1000
