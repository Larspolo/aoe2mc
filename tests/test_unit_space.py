"""A unit on the block of a shrub stands on the ground: in the bush block, not on leaves (#415, #524)."""
from collections import Counter

import numpy as np

import aoe2mc
import units


def test_unit_next_to_a_shrub_stands_on_the_ground():
    cols = aoe2mc.Columns(4, np.zeros((4, 4), np.int16), np.zeros((4, 4), np.float32),
                          {0: "GRASS_1"}, 4, 3, np.random.default_rng(1))
    shrub = dict(kind="O", name="PLANT_SHRUB_GREEN", player=0, x=1.5, y=1.5, rotation=0.0, hero=False,
                 garrisoned=False)
    leopard = dict(shrub, kind="U", name="SNOW_LEOPARD")
    E, _ = aoe2mc.place_objects([shrub], {}, cols, np.random.default_rng(1))
    vol = aoe2mc.build_chunk(0, 0, cols, E.by_chunk(cols.n)[(0, 0)])[1]
    assert aoe2mc.B.states[vol[cols.surface(6, 6) - aoe2mc.MIN_Y, 6, 6]] == "minecraft:bush"
    ents = [e for c in aoe2mc.plan_units([leopard], {}, cols, np.random.default_rng(1), Counter()).values()
            for e in c]
    passable = aoe2mc.passable_states(aoe2mc.B.states)
    before = sum(aoe2mc.MOVED.values())
    aoe2mc.entity_chunk(0, 0, ents, cols, vol, passable)
    assert sum(aoe2mc.MOVED.values()) == before
    x, y, z = (float(v) for v in units.top_entity(ents[0][0])["Pos"])
    assert y == cols.surface(int(x), int(z)) == cols.surface(6, 6)
