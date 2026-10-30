"""terrain_mask of create_terrain: the new terrain as a layer on top (1) or under (2) the old one (#4419)."""
import numpy as np
import pytest

import rmap

GRASS, DIRT = rmap.TERRAINS["GRASS"], rmap.TERRAINS["DIRT"]


def gen(mask, seed=4):
    text = ("<LAND_GENERATION>\nbase_terrain GRASS\n<TERRAIN_GENERATION>\n"
            f"create_terrain DIRT {{ base_terrain GRASS land_percent 20 number_of_clumps 3 terrain_mask {mask} }}\n")
    d = rmap.generate(text, seed, size=60, warn=lambda m: pytest.fail(m))
    return np.array(d["terrain"]), np.array(d["layer"])


def test_mask_1_keeps_the_terrain_and_puts_the_new_one_in_the_layer():
    terrain, layer = gen(1)
    assert (terrain == GRASS).all() and (layer == DIRT).sum() > 0 and set(np.unique(layer)) <= {-1, DIRT}


def test_mask_2_puts_the_new_terrain_under_the_old_look():
    terrain, layer = gen(2)
    dirt = terrain == DIRT
    assert dirt.sum() > 0 and (layer[dirt] == GRASS).all() and (layer[~dirt] == -1).all()


def test_the_same_seed_gives_the_same_map():
    a, b = gen(1), gen(1)
    assert (a[0] == b[0]).all() and (a[1] == b[1]).all()
