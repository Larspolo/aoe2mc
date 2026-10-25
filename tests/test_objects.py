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


SMALL = ["FLAME1", "FLAME4", "FLARE", "FLARE_A_PERMANENT", "FLARE_B_PERMANENT", "STUMP", "BAMBOO_STUMP", "PATH_1",
         "PATH_4", "HEAD", "IMPALED_CORPSE", "TREASURE_CHEST", "LOOT", "LEATHERWORKING_EQUIPMENT", "ARCHAIC_FENCE",
         "STAKE_BARRICADE", "PIECE_OF_THE_TRUE_CROSS", "ICE_NAVIGABLE", "SNOW_MOUNTAIN_1", "SNOW_MOUNTAIN_3",
         "BLACK_TILE"]


def test_small_objects_are_not_skipped():
    import units
    for n in SMALL:
        cols = aoe2mc.Columns(12, np.zeros((12, 12), np.int16), np.zeros((12, 12), np.float32),
                              {0: "GRASS_1"}, 4, 3, np.random.default_rng(1))
        o = dict(kind="O", name=n, player=0, x=6, y=6, rotation=0.0, hero=False, garrisoned=False)
        E, stats = aoe2mc.place_objects([o], {}, cols, np.random.default_rng(1))
        assert stats["skipped (other objects)"] == 0 and E.parts, n
    for n in ("DOLPHIN", "BOX_TURTLES"):
        assert mcvalid.entity_error("minecraft:" + aoe2mc.object_mob(n)) is None, n
    for n in ("TREASURE_CHEST", "TORCH_A_CONVERTABLE", "TORCH_B_CONVERTABLE", "PHOTONMAN", "SHARKATZOR", "NESSIE",
              "VMDL"):
        assert units.classify(n) is not None, n
