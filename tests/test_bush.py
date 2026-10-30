"""AoE2 bushes and shrubs are the bush blocks of 26.3, not only leaves (#524)."""
import mcvalid
import numpy as np

import aoe2mc


def blocks(name, terrain="GRASS_1", water=False):
    t = np.zeros((16, 16), np.int16)
    if water:
        t[:, :4] = 1
    cols = aoe2mc.Columns(16, t, np.zeros((16, 16), np.float32), {0: terrain, 1: "WATER_DEEP"}, 4, 3,
                          np.random.default_rng(1))
    o = dict(kind="O", name=name, player=0, x=2.5, y=2.5, rotation=0.0, hero=False, garrisoned=False)
    E, stats = aoe2mc.place_objects([o], {}, cols, np.random.default_rng(1))
    vol = aoe2mc.build_chunk(0, 0, cols, E.by_chunk(cols.n)[(0, 0)])[1]
    y = cols.surface(10, 10) - aoe2mc.MIN_Y
    assert stats["plants"] == 1
    return [aoe2mc.B.states[i].split(":")[1] for i in vol[y:y + 2, 10, 10:12].ravel()], cols


def test_shrub_is_a_bush():
    names, _ = blocks("PLANT_SHRUB_GREEN")
    assert names[0] == "bush"


def test_large_bush_keeps_leaves_next_to_the_bush():
    names, _ = blocks("BUSH_A")
    assert names[0] == "bush" and names[1].startswith("oak_leaves") and names[3].startswith("oak_leaves")


def test_red_shrub_on_dry_ground_and_firefly_bush_at_water():
    assert blocks("PLANT_BUSH_GREEN", terrain="DESERT_SAND")[0][0] == "red_shrub"
    assert blocks("PLANT_BUSH_GREEN", water=True)[0][0] == "firefly_bush"
    assert mcvalid.invalid_states(aoe2mc.B.states) == {}
