"""Leaf litter on the forest floor and wildflowers on grass, the new blocks of 26.3 (#522)."""
from collections import Counter

import mcvalid
import numpy as np

import aoe2mc


def deco(name):
    t = np.zeros((24, 24), np.int16)
    cols = aoe2mc.Columns(24, t, np.zeros(t.shape), {0: name}, 4, 2, np.random.default_rng(1))
    return Counter(aoe2mc.B.states[i].split(":")[1].split("[")[0] for i in cols.deco.ravel().tolist())


def test_forest_floor_has_leaf_litter():
    c = deco("FOREST_OAK")
    assert c["leaf_litter"] > 0.05 * 96 * 96, c
    assert c["fern"] > 0 and "wildflowers" not in c


def test_grass_has_wildflowers():
    c = deco("GRASS_1")
    assert 0 < c["wildflowers"] < 0.05 * 96 * 96, c
    assert "leaf_litter" not in c


def test_states_are_valid_and_varied():
    deco("FOREST_OAK"), deco("GRASS_1")
    assert mcvalid.invalid_states(aoe2mc.B.states) == {}
    litter = {s for s in aoe2mc.B.states if s.startswith("minecraft:leaf_litter")}
    assert len(litter) == 16
