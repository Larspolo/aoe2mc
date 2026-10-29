"""place_on_specific_land_id and avoid_other_land_zones of create_object in a random map script (#4133)."""
import numpy as np
import pytest

import rmap
from rmap import dilate

LAND = """<LAND_GENERATION>
base_terrain GRASS
create_land { terrain_type DIRT land_percent 30 land_id 1 land_position 25 25 }
create_land { terrain_type SNOW land_percent 30 land_id 2 land_position 75 75 }
<OBJECTS_GENERATION>
"""


def stones(d):
    return [(int(o["x"]), int(o["y"])) for o in d["objects"] if o["name"] == "STONE_MINE"]


@pytest.mark.parametrize("seed", range(1, 4))
def test_objects_only_on_the_named_land(seed):
    d = rmap.generate(LAND + "create_object STONE { number_of_objects 30 place_on_specific_land_id 2 }", seed,
                      size=100, warn=lambda m: pytest.fail(m))
    t = np.array(d["terrain"])
    assert len(stones(d)) == 30 and all(t[c] == rmap.TERRAINS["SNOW"] for c in stones(d))


@pytest.mark.parametrize("seed", range(1, 4))
def test_objects_keep_away_from_other_lands(seed):
    d = rmap.generate(LAND + "create_object STONE { number_of_objects 30 place_on_specific_land_id 2 avoid_other_land_zones 3 }",
                      seed, size=100, warn=lambda m: pytest.fail(m))
    near = dilate(np.array(d["terrain"]) == rmap.TERRAINS["DIRT"], 3)
    assert stones(d) and not any(near[c] for c in stones(d))


def test_an_unknown_land_id_gives_a_warning_and_no_object():
    notes = []
    d = rmap.generate(LAND + "create_object STONE { place_on_specific_land_id 9 }", 1, size=100, warn=notes.append)
    assert not stones(d) and any("unknown land_id 9" in m for m in notes)
