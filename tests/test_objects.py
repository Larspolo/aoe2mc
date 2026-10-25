"""Every AoE2 'other' object (trees, mines, cliffs, decorations ...) places without errors and with valid blocks."""
import numpy as np
from AoE2ScenarioParser.datasets.other import OtherInfo

import aoe2mc
import mcvalid


def test_every_other_object():
    names = [o.name for o in OtherInfo]
    per_row, step = 20, 6
    size = (len(names) // per_row + 2) * step
    cols = aoe2mc.Columns(size, np.zeros((size, size), np.int16), np.zeros((size, size), np.float32),
                          {0: "GRASS_1"}, 4, 3, np.random.default_rng(1))
    objects = [dict(kind="O", name=n, player=0, x=3.5 + (i % per_row) * step, y=3.5 + (i // per_row) * step,
                    rotation=0.0, hero=False, garrisoned=False) for i, n in enumerate(names)]
    E, stats = aoe2mc.place_objects(objects, {}, cols, np.random.default_rng(1))
    assert stats["trees"] > 0 and stats["gold mines"] > 0
    assert mcvalid.invalid_states(aoe2mc.B.states) == {}
