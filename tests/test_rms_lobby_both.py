"""REGICIDE and LUDIKRIS_MAP labels in one random map script: each block gives its terrain only when its setting is on,
and the same seed gives the same map (#5086, #4821)."""
import numpy as np
import pytest

import rmap

# Both blocks in one script. With both settings on, the later LUDIKRIS_MAP block wins.
SCRIPT = """<LAND_GENERATION>
base_terrain GRASS
if REGICIDE
base_terrain DESERT
endif
if LUDIKRIS_MAP
base_terrain SNOW
endif
"""
# Player lands use the seeded random generator, so the seed changes the map.
LANDS = SCRIPT + "create_player_lands { terrain_type DIRT land_percent 20 base_size 6 }\n"
LUDIKRIS = 250                   # a side above 240 tiles: the LUDIKRIS_MAP label


def terrain(text, seed=3, size=None, mode="standard"):
    return np.array(rmap.generate(text, seed, warn=lambda m: None, size=size, mode=mode)["terrain"])


@pytest.mark.parametrize("size, mode, expected", [
    (None, "standard", "GRASS"),       # no setting
    (None, "regicide", "DESERT"),      # the mode only
    (LUDIKRIS, "standard", "SNOW"),    # the size only
    (LUDIKRIS, "regicide", "SNOW"),    # both: the later block wins
])
def test_each_block_gives_its_terrain_only_when_its_setting_is_on(size, mode, expected):
    assert (terrain(SCRIPT, size=size, mode=mode) == rmap.TERRAINS[expected]).all()


def test_same_seed_and_settings_give_the_same_terrain():
    a = terrain(LANDS, seed=5, size=LUDIKRIS, mode="regicide")
    b = terrain(LANDS, seed=5, size=LUDIKRIS, mode="regicide")
    assert np.array_equal(a, b)


def test_another_seed_gives_another_terrain():
    a = terrain(LANDS, seed=5, size=LUDIKRIS, mode="regicide")
    b = terrain(LANDS, seed=6, size=LUDIKRIS, mode="regicide")
    assert not np.array_equal(a, b)
