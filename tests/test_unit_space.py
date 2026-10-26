"""A unit on the block of a shrub stands next to it, not on its leaves (#415)."""
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
    assert "leaves" in aoe2mc.B.states[vol[cols.surface(6, 6) - aoe2mc.MIN_Y, 6, 6]]
    ents = [e for c in aoe2mc.plan_units([leopard], {}, cols, np.random.default_rng(1), Counter()).values()
            for e in c]
    passable = np.array([s.split(":")[1].split("[")[0] in ("air", "cave_air") for s in aoe2mc.B.states])
    before = sum(aoe2mc.MOVED.values())
    aoe2mc.entity_chunk(0, 0, ents, cols, vol, passable)
    assert sum(aoe2mc.MOVED.values()) == before
    x, y, z = (float(v) for v in units.top_entity(ents[0][0])["Pos"])
    assert y == cols.surface(6, 6) and (int(x), int(z)) != (6, 6)
