"""place_on_specific_land_id of create_object with the land_id of create_player_lands (#4722)."""
import numpy as np
import pytest

import rmap

LAND = """<LAND_GENERATION>
base_terrain GRASS
create_player_lands { terrain_type SNOW number_of_tiles 200 base_size 4 land_id 500 }
<OBJECTS_GENERATION>
"""


def stones(d):
    return [(int(o["x"]), int(o["y"])) for o in d["objects"] if o["name"] == "STONE_MINE"]


@pytest.mark.parametrize("seed", range(1, 4))
def test_objects_on_the_land_id_of_every_player_land(seed):
    notes = []
    d = rmap.generate(LAND + "create_object STONE { number_of_objects 30 place_on_specific_land_id 500 }", seed,
                      size=100, warn=notes.append)
    t = np.array(d["terrain"])
    assert not notes and len(stones(d)) == 30
    assert all(t[c] == rmap.TERRAINS["SNOW"] for c in stones(d))


@pytest.mark.parametrize("seed", range(1, 4))
def test_objects_reach_both_player_lands_of_the_same_id(seed):
    d = rmap.generate(LAND + "create_object STONE { number_of_objects 60 place_on_specific_land_id 500 }", seed,
                      size=100, warn=lambda m: pytest.fail(m))
    xs = [x for x, _ in stones(d)]
    assert min(xs) < 50 < max(xs)
