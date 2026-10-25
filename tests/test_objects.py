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


PROPS = ["WATER_POTS", "GRAIN_STORAGE", "FURNACE", "WATER_TROUGH", "AMPHORAE", "BENCH_WOODEN", "BENCH_STONE",
         "FOUNTAIN", "FOUNTAIN_ANTIQUITY", "MEDITERRANEAN_STALL", "MESOPOTAMIAN_STALL", "IMPALED_CORPSE_ANTIQUITY"]


def test_camp_and_town_props_have_blocks():
    """The small camp and town props keep their blocks in the footprint up to head height; fountain water has a rim on all sides (#295)."""
    B = aoe2mc.B
    for n in PROPS:
        cols = aoe2mc.Columns(12, np.zeros((12, 12), np.int16), np.zeros((12, 12), np.float32),
                              {0: "GRASS_1"}, 4, 3, np.random.default_rng(1))
        o = dict(kind="O", name=n, player=0, x=1.5, y=1.5, rotation=0.0, hero=False, garrisoned=False)
        E, stats = aoe2mc.place_objects([o], {}, cols, np.random.default_rng(1))
        x0, x1, z0, z1 = aoe2mc.object_footprint(o, 4)
        x, y, z, ids, _ = (np.concatenate(p) for p in zip(*E.parts))
        names = [B.states[i] for i in ids]
        solid = {(a, b, c) for a, b, c, s in zip(x, y, z, names) if "barrier" not in s}
        assert stats["decorations"] == 1 and stats["skipped (other objects)"] == 0 and solid, n
        assert all(x0 <= a < x1 and z0 <= c < z1 for a, b, c in solid if b < cols.wtop[a, c] + E.HEAD), n
        water = [(a, b, c) for a, b, c, s in zip(x, y, z, names) if s.partition("[")[0] == "minecraft:water"]
        assert bool(water) == n.startswith("FOUNTAIN"), n
        for a, b, c in water:
                assert all((a + dx, b, c + dz) in solid for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))), n
    assert mcvalid.invalid_states(B.states) == {}
