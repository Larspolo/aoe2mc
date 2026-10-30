"""Every AoE2 'other' object (trees, mines, cliffs, decorations ...) places without errors and with valid blocks."""
from collections import Counter

import mcvalid
import numpy as np
from AoE2ScenarioParser.datasets.other import OtherInfo

import aoe2mc


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
    assert names["minecraft:dark_oak_fence[waterlogged=true]"] > 0
    assert names["minecraft:sea_pickle[pickles=3,waterlogged=true]"] == 1
    assert not [n for n in names if n.partition("[")[0] in aoe2mc.WATERLOGGABLE and "waterlogged=true" not in n]
    assert names["minecraft:dark_oak_wood[axis=x]"] > 0    # no waterlogged property: no change
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


def test_norse_objects_have_blocks():
    """Runestones, column, banner and wooden road place blocks in their footprint; units walk on the road (#297)."""
    for n in ("RUNESTONES", "NORSE_COLUMN", "NORSE_BANNER", "WOODEN_ROAD"):
        cols = aoe2mc.Columns(12, np.zeros((12, 12), np.int16), np.zeros((12, 12), np.float32),
                              {0: "GRASS_1"}, 4, 3, np.random.default_rng(1))
        o = dict(kind="O", name=n, player=0, x=6, y=6, rotation=0.0, hero=False, garrisoned=False)
        E, stats = aoe2mc.place_objects([o], {}, cols, np.random.default_rng(1))
        assert stats["decorations"] == 1 and stats["skipped (other objects)"] == 0, n
        x0, x1, z0, z1 = aoe2mc.object_footprint(o, 4)
        for xs, ys, zs, *_ in E.parts:
            assert ((x0 <= xs) & (xs < x1) & (z0 <= zs) & (zs < z1)).all(), n
        assert cols.blocked[x0:x1, z0:z1].any() == (n != "WOODEN_ROAD"), n
    assert mcvalid.invalid_states(aoe2mc.B.states) == {}


def test_tree_stump_is_level_with_the_ground_and_free_for_units():
    """A stump does not stop units or the player: the top of a log in the ground, no barrier, no block above (#307)."""
    B = aoe2mc.B
    for name in ("STUMP", "BAMBOO_STUMP", "BAOBAB_STUMP", "LUSH_BAMBOO_STUMP"):     # the stumps of the parser
        cols = aoe2mc.Columns(16, np.zeros((16, 16), np.int16), np.zeros((16, 16), np.float32),
                              {0: "GRASS_1"}, 4, 3, np.random.default_rng(1))
        o = dict(kind="O", name=name, player=0, x=2.5, y=2.5, rotation=0.0, hero=False, garrisoned=False)
        E, stats = aoe2mc.place_objects([o], {}, cols, np.random.default_rng(1))
        assert not cols.blocked.any(), name
        vol = aoe2mc.build_chunk(0, 0, cols, E.by_chunk(cols.n)[(0, 0)])[1]
        y = cols.surface(10, 10) - aoe2mc.MIN_Y                       # the first free block above the ground
        assert B.states[vol[y - 1, 10, 10]].endswith(("spruce_log[axis=y]", "stripped_bamboo_block[axis=y]")), name
        assert (vol[y:, 8:12, 8:12] == 0).all(), name                  # nothing above the ground: air only


def test_antiquity_and_construction_objects():
    """The crane, scaffolding, theatre and Stonehenge get blocks inside their footprint (#296)."""
    import buildings
    for n in ("CONSTRUCTION_CRANE", "SCAFFOLDING", "SCAFFOLDING_WALKABLE", "THEATRE", "STONEHENGE"):
        cols = aoe2mc.Columns(32, np.zeros((32, 32), np.int16), np.zeros((32, 32), np.float32),
                              {0: "GRASS_1"}, 4, 3, np.random.default_rng(1))
        o = dict(kind="O", name=n, player=1, x=16, y=16, rotation=0.0, hero=False, garrisoned=False)
        E, stats = aoe2mc.place_objects([o], {}, cols, np.random.default_rng(1))
        assert stats["monuments"] == 1 and stats["skipped (other objects)"] == 0, n
        s = buildings.footprint(n) * 4
        x0 = z0 = 64 - s // 2
        x1 = z1 = x0 + s
        x, _, z, ids, _ = (np.concatenate(p) for p in zip(*E.parts))
        inside = (x >= x0) & (x < x1) & (z >= z0) & (z < z1) & ~np.isin(ids, [aoe2mc.B("air"), aoe2mc.B("barrier")])
        assert inside.sum() > 20, n
    assert mcvalid.invalid_states(aoe2mc.B.states) == {}


SHORE = ["DRIFTWOOD_GROUND", "DRIFTWOOD_WATER", "FLOTSAM", "KELP_SEAWEEDS", "WATER_LILY", "BEACHED_WHALE",
         "SMALL_WATERFALL", "FALLEN_LEAVES_PEACH_BLOSSOM", "FALLEN_LEAVES_MAPLE", "FALLEN_LEAVES_MAPLE_AUTUMN"]


def test_shore_and_ground_cover_objects():
    """Water objects find the water: lily pads on the surface, kelp under it; leaves lie on land (#298)."""
    B = aoe2mc.B
    terrain = np.zeros((12, 12), np.int16)
    terrain[6:] = 1                                    # tiles x >= 6: deep water, blocks x >= 24
    cols = aoe2mc.Columns(12, terrain, np.zeros((12, 12), np.float32), {0: "GRASS_1", 1: "WATER_DEEP"},
                          4, 3, np.random.default_rng(1))
    water = ("DRIFTWOOD_WATER", "FLOTSAM", "KELP_SEAWEEDS", "WATER_LILY")
    for n in SHORE:
        o = dict(kind="O", name=n, player=0, x=9.5 if n in water else 2.5, y=6.5, rotation=0.0, hero=False,
                 garrisoned=False)
        E, stats = aoe2mc.place_objects([o], {}, cols, np.random.default_rng(1))
        assert stats["skipped (other objects)"] == 0 and stats["decorations"] == 1, n
        blocks = [(x, y, z, B.states[i]) for xs, ys, zs, ids, _ in E.parts for x, y, z, i in zip(xs, ys, zs, ids)]
        assert blocks, n
        for x, y, z, st in blocks:
            floor, top = int(cols.top[x, z]), int(cols.wtop[x, z])
            if "lily_pad" in st:
                assert y == top + 1 and top > floor, n
            elif "kelp" in st or "seagrass" in st:
                assert floor < y <= top, n
            elif n.startswith("FALLEN_LEAVES"):
                assert y == top + 1 == floor + 1, n
        if n in ("KELP_SEAWEEDS", "WATER_LILY"):
            assert any(("kelp" if n == "KELP_SEAWEEDS" else "lily") in b[3] for b in blocks), n
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


def test_last_animals_get_a_mob():
    """Whales, howler monkeys and butterflies are mobs; a beached whale is not (#299)."""
    import units
    mobs = [aoe2mc.object_mob(n) for n in ("WHALE", "HOWLER_MONKEY")]
    assert all(mobs) and aoe2mc.object_mob("BEACHED_WHALE") is None
    for n in ("BUTTERFLY1", "BUTTERFLY2", "BUTTERFLY3"):
        assert units.classify(n)["id"] == "minecraft:bee" and units.classify(n)["NoGravity"] == 1, n
    for kind in (*mobs, "bee"):
        assert mcvalid.entity_error("minecraft:" + kind) is None, kind
    cols = aoe2mc.Columns(16, np.zeros((16, 16), np.int16), np.zeros((16, 16), np.float32),
                          {0: "GRASS_1"}, 4, 3, np.random.default_rng(1))
    o = dict(kind="O", name="HOWLER_MONKEY", player=0, x=6.5, y=6.5, rotation=0.0, hero=False, garrisoned=False)
    stats = Counter()
    ents = [e for c in aoe2mc.plan_units([o], {}, cols, np.random.default_rng(1), stats).values() for e in c]
    assert stats["animals (objects)"] == 1 and ents[0][3] is False      # on land, not in water
