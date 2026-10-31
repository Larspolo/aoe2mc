"""A full forage bush or fruit bush fills its tile and is 2 blocks high (#590)."""
import mcvalid
import numpy as np

import aoe2mc


def test_full_bush_fills_its_tile_two_blocks_high():
    B = aoe2mc.B
    for name in ("FORAGE_BUSH", "FRUIT_BUSH"):
        cols = aoe2mc.Columns(16, np.zeros((16, 16), np.int16), np.zeros((16, 16), np.float32),
                              {0: "GRASS_1"}, 4, 3, np.random.default_rng(1))
        o = dict(kind="O", name=name, player=0, x=2.5, y=2.5, rotation=0.0, hero=False, garrisoned=False)
        E, stats = aoe2mc.place_objects([o], {}, cols, np.random.default_rng(1))
        assert stats["berry bushes"] == 1
        vol = aoe2mc.build_chunk(0, 0, cols, E.by_chunk(cols.n)[(0, 0)])[1]
        y = cols.surface(10, 10) - aoe2mc.MIN_Y                       # the first block above the ground
        names = np.vectorize(lambda i: B.states[i].split(":")[-1].split("[")[0])
        low, high = names(vol[y, 8:12, 8:12]), names(vol[y + 1, 8:12, 8:12])
        assert "air" not in low, (name, low)                          # the whole tile of 4 x 4 blocks
        assert (low[1:3, 1:3] == "oak_leaves").all() and (high[1:3, 1:3] == "oak_leaves").all(), name
        ring = np.ones((4, 4), bool)
        ring[1:3, 1:3] = False
        assert (low[ring] == "sweet_berry_bush").all(), name          # berries stand on the grass
        assert names(vol[y - 1, 8:12, 8:12])[ring].tolist() == ["grass_block"] * 12, name
        assert cols.blocked[8:12, 8:12].all(), name
    assert mcvalid.invalid_states(B.states) == {}


def test_a_gathered_bush_loses_its_leaves_and_still_blocks():
    from test_gather_food import food_map

    from game import gather
    server, g = food_map()
    g.select("v")
    g.send((10, 10))
    for _ in range(3000):
        g.step()
        if g.map.bushes[(10, 10)] < gather.BUSH_FOOD // 2:
            break
    leaves = [c for c in server.log if c.startswith("fill 10 ") and c.endswith("replace minecraft:oak_leaves")]
    assert leaves and all(c.split()[7] == "minecraft:barrier" for c in leaves)
