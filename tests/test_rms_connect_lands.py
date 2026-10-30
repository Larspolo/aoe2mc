"""The other connection commands of a random map script: all lands, non-player lands, zones (#3869)."""
import numpy as np
import pytest
from test_rms_connections import reach

import rmap

W, S = rmap.TERRAINS["WATER"], rmap.TERRAINS["SHALLOW"]
MIDDLE = """<LAND_GENERATION>
base_terrain WATER
create_player_lands { terrain_type GRASS land_percent 10 base_size 4 }
create_land { terrain_type DIRT number_of_tiles 50 base_size 3 land_position 50 50 }
<CONNECTION_GENERATION>
%s { replace_terrain WATER SHALLOW }
"""


def make(text, players=4):
    d = rmap.generate(text, 3, players=players, size=80, warn=lambda m: pytest.fail(m))
    return np.array(d["terrain"]), [(st["x"], st["y"]) for st in d["lands"]]


def test_all_lands_joins_the_middle_island_with_the_player_islands():
    t, o = make(MIDDLE % "create_connect_all_lands")
    seen = reach(t != W, (40, 40))
    assert all(c in seen for c in o)


def test_nonplayer_land_joins_each_player_island_only_with_the_middle():
    t, o = make(MIDDLE % "create_connect_to_nonplayer_land")
    assert all(c in reach(t != W, (40, 40)) for c in o)
    every = make(MIDDLE % "create_connect_all_lands")[0] == S
    some = t == S                  # the paths to the middle only: a subset of the paths of all pairs, less tiles
    assert some.any() and (every[some]).all() and some.sum() < every.sum()


def test_same_land_zones_joins_only_the_lands_of_one_zone():
    text = """<LAND_GENERATION>
base_terrain WATER
create_land { terrain_type GRASS number_of_tiles 40 base_size 2 land_position 20 20 zone 1 }
create_land { terrain_type GRASS number_of_tiles 40 base_size 2 land_position 80 80 zone 1 }
create_land { terrain_type DIRT number_of_tiles 40 base_size 2 land_position 80 20 zone 2 }
<CONNECTION_GENERATION>
create_connect_same_land_zones { replace_terrain WATER SHALLOW }
"""
    t, _ = make(text, players=2)
    seen = reach(t != W, (16, 16))
    assert (63, 63) in seen and (63, 16) not in seen


def test_land_zones_joins_the_named_zones():
    text = """<LAND_GENERATION>
base_terrain WATER
create_land { terrain_type GRASS number_of_tiles 40 base_size 2 land_position 20 20 zone 1 }
create_land { terrain_type GRASS number_of_tiles 40 base_size 2 land_position 80 80 zone 2 }
create_land { terrain_type DIRT number_of_tiles 40 base_size 2 land_position 80 20 zone 3 }
<CONNECTION_GENERATION>
create_connect_land_zones 1 2 { replace_terrain WATER SHALLOW }
"""
    t, _ = make(text, players=2)
    seen = reach(t != W, (16, 16))
    assert (63, 63) in seen and (63, 16) not in seen


def test_teams_lands_gives_no_path():
    t, _ = make(MIDDLE % "create_connect_teams_lands")
    assert not (t == S).any()
