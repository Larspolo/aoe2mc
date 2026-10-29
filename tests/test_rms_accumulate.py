"""accumulate_connections of <CONNECTION_GENERATION>: a connection reads the terrain of the earlier ones (#4174)."""
import numpy as np

import rmap

LEAVES, ROAD = rmap.TERRAINS["LEAVES"], rmap.TERRAINS["ROAD"]
# the example of the docs of accumulate_connections: a road through a wide gap in the forest
FOREST_ROAD = """<LAND_GENERATION>
base_terrain FOREST
create_player_lands { terrain_type GRASS land_percent 20 base_size 6 }
<CONNECTION_GENERATION>
%screate_connect_all_lands { replace_terrain FOREST LEAVES terrain_size FOREST 10 0 }
create_connect_all_lands { replace_terrain LEAVES ROAD terrain_size LEAVES 1 0 }
"""


def test_accumulate_connections_lets_the_second_connection_see_the_first():
    t = np.array(rmap.generate(FOREST_ROAD % "accumulate_connections\n", 3, players=2, size=80)["terrain"])
    assert (t == ROAD).any() and (t == LEAVES).any()


def test_without_accumulate_connections_the_second_connection_finds_no_leaves():
    t = np.array(rmap.generate(FOREST_ROAD % "", 3, players=2, size=80)["terrain"])
    assert (t == LEAVES).any() and not (t == ROAD).any()


def test_accumulate_connections_gives_no_warning():
    seen = []
    rmap.generate(FOREST_ROAD % "accumulate_connections\n", 3, players=2, size=80, warn=seen.append)
    assert not any("accumulate_connections" in m for m in seen)
