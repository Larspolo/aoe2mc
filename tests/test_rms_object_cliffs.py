"""create_object next to the cliffs of <CLIFF_GENERATION>: no object on a cliff, avoid_cliff_zone (#4131)."""
import numpy as np
import pytest

import rmap

LAND = """<LAND_GENERATION>
base_terrain GRASS
create_player_lands { terrain_type DIRT land_percent 20 base_size 8 }
create_land { terrain_type WATER number_of_tiles 600 base_size 6 land_position 50 50 }
"""
CLIFFS = """<CLIFF_GENERATION>
min_number_of_cliffs 3
max_number_of_cliffs 3
min_length_of_cliff 4
max_length_of_cliff 6
"""
STONE = """<OBJECTS_GENERATION>
create_object STONE { number_of_objects 200 }
"""


def tiles(d, names, n):
    """The tiles of the objects of the given names, as a mask."""
    mask = np.zeros((n, n), bool)
    for o in d["objects"]:
        if o["name"].startswith(names):
            mask[int(o["x"]), int(o["y"])] = True
    return mask


def stone_tiles(d, n):
    return tiles(d, ("STONE",), n)


@pytest.mark.parametrize("seed", range(1, 4))
def test_no_stone_on_a_cliff(seed):
    d = rmap.generate(LAND + CLIFFS + STONE, seed, size=120, warn=lambda m: pytest.fail(m))
    n = d["size"]
    cliff = rmap.dilate(tiles(d, ("CLIFF_DEFAULT_",), n), 1)
    stone = stone_tiles(d, n)
    assert stone.any() and not (stone & cliff).any()


@pytest.mark.parametrize("seed", range(1, 4))
def test_avoid_cliff_zone_keeps_stone_away(seed):
    script = LAND + CLIFFS + "<OBJECTS_GENERATION>\ncreate_object STONE { number_of_objects 200 avoid_cliff_zone 4 }\n"
    d = rmap.generate(script, seed, size=120, warn=lambda m: pytest.fail(m))
    n = d["size"]
    cliff = rmap.dilate(tiles(d, ("CLIFF_DEFAULT_",), n), 1)
    stone = stone_tiles(d, n)
    assert stone.any() and not (stone & rmap.dilate(cliff, 4)).any()


def test_the_same_seed_gives_the_same_objects():
    script = LAND + CLIFFS + STONE
    assert rmap.generate(script, 5, size=120)["objects"] == rmap.generate(script, 5, size=120)["objects"]
