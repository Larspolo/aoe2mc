"""Flower fields on grass have a few golden dandelions, the new flower of 26.3 (#557)."""
from collections import Counter

import numpy as np
from mcvalid import block_error

import aoe2mc

FLOWERS = {"poppy", "dandelion", "cornflower", "oxeye_daisy", "azure_bluet", "allium", "red_tulip", "white_tulip",
           "orange_tulip", "pink_tulip", "lily_of_the_valley", "golden_dandelion"}


def plants(terrain="GRASS_1"):
    cols = aoe2mc.Columns(64, np.zeros((64, 64), np.int16), np.zeros((64, 64), np.float32), {0: terrain}, 4, 2,
                          np.random.default_rng(1))
    return Counter(aoe2mc.B.states[i].split(":")[1] for i in cols.deco[:cols.n, :cols.n].ravel())


def test_flower_fields_have_a_few_golden_dandelions():
    c = plants()
    flowers = sum(c[f] for f in FLOWERS)
    assert flowers > 100 and 0.02 * flowers <= c["golden_dandelion"] <= 0.1 * flowers
    assert block_error("golden_dandelion") is None


def test_golden_dandelions_are_deterministic():
    assert plants() == plants()


def test_no_tall_grass_top_above_a_flower():
    cols = aoe2mc.Columns(64, np.zeros((64, 64), np.int16), np.zeros((64, 64), np.float32), {0: "GRASS_1"}, 4, 2,
                          np.random.default_rng(1))
    n, S = cols.n, aoe2mc.B.states
    low = {S[i].split(":")[1].split("[")[0] for i in cols.deco[:n, :n][cols.deco2[:n, :n] != aoe2mc.AIR]}
    assert low <= {"tall_grass", "large_fern", "tall_dry_grass", "sunflower", "rose_bush", "peony", "lilac"}, low
