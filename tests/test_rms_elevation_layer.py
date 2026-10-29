"""base_layer of create_elevation in a random map script: hills only on a land layer (#3967)."""
import numpy as np
import pytest

import aoe2mc
import rmap

LAYER = """<LAND_GENERATION>
base_terrain GRASS
create_land { terrain_type GRASS base_layer DIRT number_of_tiles 900 base_size 8 land_position 30 30 }
<ELEVATION_GENERATION>
create_elevation 2 { base_layer DIRT number_of_tiles 300 }
"""


@pytest.mark.parametrize("seed", range(1, 4))
def test_hills_rise_only_on_the_layer(seed):
    d = rmap.generate(LAYER, seed, size=80, warn=lambda m: pytest.fail(m))
    e, layer = np.array(d["elevation"]), np.array(d["layer"])
    assert (layer == rmap.TERRAINS["DIRT"]).sum() >= 800 and set(np.unique(layer)) == {-1, rmap.TERRAINS["DIRT"]}
    assert e.max() == 2 and 200 <= (e > 0).sum() <= 300
    assert (layer[e > 0] == rmap.TERRAINS["DIRT"]).all()
    assert (np.array(d["terrain"]) == rmap.TERRAINS["GRASS"]).all()


def test_the_same_seed_gives_the_same_map():
    assert rmap.generate(LAYER, 7, size=80) == rmap.generate(LAYER, 7, size=80)


def test_read_json_draws_the_layer():
    d = rmap.generate(LAYER, 3, size=80)
    terrain = aoe2mc.map_description(d, "layer.rms")[1]
    assert (np.asarray(terrain)[np.array(d["layer"]) >= 0] == rmap.TERRAINS["DIRT"]).all()
