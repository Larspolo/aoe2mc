"""Every AoE2 'other' object (trees, mines, cliffs, decorations ...) places without errors and with valid blocks."""
from collections import Counter

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


def test_invisible_objects_are_skipped_on_purpose():
    cols = aoe2mc.Columns(12, np.zeros((12, 12), np.int16), np.zeros((12, 12), np.float32),
                          {0: "GRASS_1"}, 4, 3, np.random.default_rng(1))
    objects = [dict(kind="O", name=n, player=0, x=6, y=6, rotation=0.0, hero=False, garrisoned=False)
               for n in ("BLOCKER", "MAP_REVEALER", "AURA_QUEST_INDICATOR_COINS")]
    E, stats = aoe2mc.place_objects(objects, {}, cols, np.random.default_rng(1))
    assert stats["invisible (skipped on purpose)"] == 3 and stats["skipped (other objects)"] == 0


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


def test_blocks_under_water_are_waterlogged():
    """A fish trap in deep water has waterlogged fences and an oyster gives a waterlogged sea pickle (#19)."""
    B = aoe2mc.B
    cols = aoe2mc.Columns(16, np.ones((16, 16), np.int16), np.zeros((16, 16), np.float32),
                          {1: "WATER_DEEP"}, 4, 3, np.random.default_rng(1))
    objects = [dict(kind=k, name=n, player=1, x=x, y=y, rotation=0.0, hero=False, garrisoned=False)
               for k, n, x, y in (("B", "FISH_TRAP", 4.5, 4.5), ("O", "OYSTER", 10.5, 10.5))]
    E, stats = aoe2mc.place_objects(objects, {}, cols, np.random.default_rng(1))
    chunks = E.by_chunk(cols.n)
    names = Counter()
    for (cx, cz), edits in chunks.items():
        vol = aoe2mc.build_chunk(cx, cz, cols, edits)[1]
        y = np.arange(aoe2mc.MIN_Y, aoe2mc.MAX_Y)[:, None, None]
        under = (y <= cols.wtop[cx * 16:cx * 16 + 16, cz * 16:cz * 16 + 16].T[None])
        names.update(B.states[i] for i in vol[under & (vol != aoe2mc.WATER)].ravel())
    assert names["minecraft:spruce_fence[waterlogged=true]"] > 0
    assert names["minecraft:sea_pickle[pickles=3,waterlogged=true]"] == 1
    assert not [n for n in names if n.partition("[")[0] in aoe2mc.WATERLOGGABLE and "waterlogged=true" not in n]
    assert names["minecraft:spruce_log"] > 0               # no waterlogged property: no change
    assert mcvalid.invalid_states(B.states) == {}


GARDEN = ["PAPER_LANTERN", "ASIAN_LANTERNS", "PAIFANG_GATE_SMALL", "PAIFANG_GATE_LARGE", "GARDEN_PAVILION",
          "GARDEN_BRIDGE", "HUABIAO_TOTEM", "QUE_TOWER"]


def test_chinese_garden_objects():
    """The Chinese garden objects place blocks, and below head height only in their footprint (#294)."""
    for n in GARDEN:
        for x in (6, 6.5):                              # even and odd footprint
            cols = aoe2mc.Columns(16, np.zeros((16, 16), np.int16), np.zeros((16, 16), np.float32),
                                  {0: "GRASS_1"}, 4, 3, np.random.default_rng(1))
            o = dict(kind="O", name=n, player=0, x=x, y=x, rotation=0.0, hero=False, garrisoned=False)
            E, stats = aoe2mc.place_objects([o], {}, cols, np.random.default_rng(1))
            assert stats["decorations"] == 1 and stats["skipped (other objects)"] == 0, n
            xs, ys, zs = (np.concatenate([p[k] for p in E.parts]) for k in range(3))
            x0, x1, z0, z1 = aoe2mc.object_footprint(o, 4)
            low = ys < cols.surface(x0, z0) + aoe2mc.Edits.HEAD
            assert low.any() and ((xs[low] >= x0) & (xs[low] < x1) & (zs[low] >= z0) & (zs[low] < z1)).all(), n
    assert mcvalid.invalid_states(aoe2mc.B.states) == {}
