"""create_object with layer_to_place_on in a random map script: the objects only on the tiles of a land layer (#4132)."""
import numpy as np
import pytest

import rmap

LAYER = """<LAND_GENERATION>
base_terrain GRASS
create_land { terrain_type GRASS base_layer DIRT land_position 50 50 base_size 8 number_of_tiles 400 }
<OBJECTS_GENERATION>
create_object GOLD { number_of_objects 20 layer_to_place_on DIRT }
"""


@pytest.mark.parametrize("seed", range(1, 4))
def test_objects_only_on_the_tiles_of_the_layer(seed):
    warned = []
    d = rmap.generate(LAYER, seed, players=2, size=100, warn=warned.append)
    assert not warned
    layer = np.array(d["layer"])
    gold = [o for o in d["objects"] if o["name"] == "GOLD_MINE"]
    assert len(gold) == 20
    for o in gold:
        tx, ty = int(o["x"]), int(o["y"])
        assert layer[tx, ty] != -1 and layer[tx, ty] == layer[50, 50]


def test_no_tile_of_the_layer_gives_no_object():
    warned = []
    text = LAYER.replace("layer_to_place_on DIRT", "layer_to_place_on FOREST")
    d = rmap.generate(text, 1, players=2, size=100, warn=warned.append)
    assert not [o for o in d["objects"] if o["name"] == "GOLD_MINE"]
    assert any("no free tile" in m for m in warned)
