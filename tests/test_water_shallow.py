"""Normal DE water ("Water, Shallow", terrain 1) is deeper than the walkable shallows (terrain 4, #1198)."""
import numpy as np

import aoe2mc


def columns(terrain):
    names = {0: "GRASS_1", 1: "WATER_SHALLOW", 4: "SHALLOWS", 114: "WATER_YELLOW_SHALLOW", 115: "SHALLOWS_YELLOW"}
    t = np.array(terrain, np.int16)
    return aoe2mc.Columns(len(t), t, np.zeros(t.shape), names, 4, 2, np.random.default_rng(1))


def test_water_shallow_is_deeper_than_the_shallows():
    t = np.zeros((12, 12), int)
    t[:, 3:5], t[:, 6:8] = 1, 4                         # a river of terrain 1 and a ford of terrain 4 along x
    c = columns(t)
    river, ford = c.wtop[8:40, 16] - c.top[8:40, 16], c.wtop[8:40, 28] - c.top[8:40, 28]
    assert (river >= 2).all() and (ford == 1).all()


def test_the_yellow_water_is_like_the_normal_water():
    for yellow, normal in (("WATER_YELLOW_SHALLOW", "WATER_SHALLOW"), ("SHALLOWS_YELLOW", "SHALLOWS")):
        assert aoe2mc.terrain_style(yellow)["depth"] == aoe2mc.terrain_style(normal)["depth"], yellow
