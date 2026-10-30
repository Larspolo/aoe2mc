"""Dry terrain gets the dry grass blocks of 26.3; green terrain keeps green grass (#523)."""
from collections import Counter

import mcvalid
import numpy as np

import aoe2mc


def plants(terrain):
    cols = aoe2mc.Columns(32, np.zeros((32, 32), np.int16), np.zeros((32, 32), np.float32), {0: terrain}, 4, 2,
                          np.random.default_rng(1))
    return Counter(aoe2mc.B.states[i].split(":")[1] for i in cols.deco[:cols.n, :cols.n].ravel())


def test_dirt_and_steppe_get_dry_grass():
    c = plants("DIRT_1")
    assert c["short_dry_grass"] > 100 and c["tall_dry_grass"] > 10 and c["dead_bush"] > 0


def test_desert_sand_gets_a_little_dry_grass_next_to_dead_bushes():
    c = plants("DESERT_SAND")
    assert 0 < c["short_dry_grass"] < 0.05 * 128 * 128 and c["dead_bush"] > 0


def test_green_grass_keeps_green_grass():
    c = plants("GRASS_1")
    assert c["short_grass"] > 100 and not c["short_dry_grass"] and not c["tall_dry_grass"]
    assert mcvalid.invalid_states(aoe2mc.B.states) == {}
