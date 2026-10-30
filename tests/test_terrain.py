"""Every AoE2 terrain gives valid Minecraft blocks and a valid biome."""
import mcvalid
import pytest
from AoE2ScenarioParser.datasets.terrains import TerrainId

import aoe2mc


@pytest.mark.parametrize("name", sorted(t.name for t in TerrainId))
def test_terrain_style_is_valid(name):
    s = aoe2mc.terrain_style(name)
    for key in ("top", "sub", "bottom"):
        assert mcvalid.block_error("minecraft:" + s[key]) is None, (key, s[key])
    for block, chance in s["deco"]:
        assert mcvalid.block_error("minecraft:" + block) is None, block
        assert 0 < chance <= 1
    assert mcvalid.biome_error(s["biome"]) is None


def columns(terrain):
    """Columns of a small map. All maps of one size draw the same random numbers."""
    import numpy as np
    names = {0: "GRASS_1", 1: "WATER_DEEP", 2: "GRAVEL_DEFAULT", 3: "ROAD_GRAVEL"}
    t = np.array(terrain, np.int16)
    return aoe2mc.Columns(len(t), t, np.zeros(t.shape), names, 4, 2, np.random.default_rng(1))


def test_road_pass_changes_only_roads():
    """The road pass does not change the sea floor, gravel terrain or the land next to water (#5)."""
    import numpy as np
    B = aoe2mc.B
    t = np.zeros((12, 12), int)
    t[9:] = 1                                # deep water at the east edge, next to grass and the west edge
    t[2:4, 2:4] = 2                          # gravel terrain, not a road
    plain = columns(np.where(t == 1, 0, t)).top_id[:48, :48]
    c = columns(t)
    top = c.top_id[:48, :48]
    assert (top[36:] == B("gravel")).all()           # sea floor
    assert (top[8:16, 8:16] == B("gravel")).all()    # gravel terrain
    assert (top[:36] == plain[:36]).all()            # shore and west edge (no wrap-around)


def test_gravel_road_gets_its_mix():
    import numpy as np
    B = aoe2mc.B
    t = np.zeros((12, 12), int)
    t[:, 5:7] = 3
    top = columns(t).top_id[:48, :48]
    road = top[:, 20:28]
    assert {B("coarse_dirt"), B("cobblestone"), B("dirt_path")} <= set(np.unique(road))
    assert (top[:, 19] != columns(np.zeros((12, 12), int)).top_id[:48, 19]).any()   # worn verge


def raised(terrain, elevation):
    import numpy as np
    names = {0: "GRASS_1", 1: "WATER_DEEP", 4: "WATER_SHALLOW"}
    t = np.array(terrain, np.int16)
    return aoe2mc.Columns(len(t), t, np.array(elevation, np.float32), names, 4, 2, np.random.default_rng(1))


def test_raised_river_lies_at_the_height_of_its_land():
    """A river at elevation 2 between land at elevation 2: the water surface is 1 block below the land (#165)."""
    import numpy as np
    t = np.zeros((12, 12), int)
    t[:, 5:7] = 1                                    # a river along x
    c = raised(t, np.full((12, 12), 2))
    land, water = c.top[:48, 10], c.wtop[:48, 24]    # land at z 10, river surface at z 24
    assert (water == aoe2mc.WATER_Y + 4).all() and (land == water + 1).all()
    assert (c.top[:48, 24] == water - 7).all()       # deep water: the depth counts from the surface


def test_one_level_per_body():
    """Each connected body gets the lowest elevation of its tiles. Land next to the water is not lower."""
    import numpy as np
    t = np.zeros((12, 12), int)
    t[1:5, 1:5] = 4                                  # a lake at elevation 1 and 3
    t[8:11, 8:11] = 4                                # a lake at elevation 0
    e = np.zeros((12, 12))
    e[0:6, 0:6] = 1
    e[3:5, 3:5] = 3
    c = raised(t, e)
    lake = c.wtop[4:20, 4:20][c.wtop[4:20, 4:20] > c.top[4:20, 4:20]]
    assert set(lake.tolist()) == {aoe2mc.WATER_Y + 2}
    sea = c.wtop[32:44, 32:44]
    assert (sea == aoe2mc.WATER_Y).all()
    wet = c.wtop[:48, :48] > c.top[:48, :48]
    for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):  # no water flows out: each dry neighbour is high enough
        w = np.roll(np.roll(wet, dx, 0), dz, 1)
        lvl = np.roll(np.roll(c.wtop[:48, :48], dx, 0), dz, 1)
        assert (c.top[:48, :48][w & ~wet] >= lvl[w & ~wet]).all()


def test_shores_slope_down_to_the_water():
    """High land next to water slopes down to it: no column next to the water is more than 2 blocks above the
    surface, and the faces of the steps show dirt, not stone (#166)."""
    import numpy as np
    t = np.zeros((12, 12), int)
    t[:, 6:] = 1                                     # the sea in the south
    e = np.where(t == 1, 0, 6)                       # land at elevation 6 (12 blocks above the sea with H = 2)
    c = raised(t, e)
    top, wtop = c.top[:48, :48], c.wtop[:48, :48]
    wet = wtop > top
    for d in (1, -1):
        nxt = np.roll(wet, d, 1)
        nxt[:, 0 if d == 1 else -1] = False
        assert (top[nxt & ~wet] <= np.roll(wtop, d, 1)[nxt & ~wet] + 2).all()
    assert top[:, 23].max() == aoe2mc.WATER_Y + 1 and top[:, 10].max() == aoe2mc.WATER_Y + 1 + 12
    vol = aoe2mc.build_chunk(0, 1, c, None)[1]       # blocks of the chunk at z 16..31 (the shore)
    z, x = 20 - 16, 5
    col = vol[:, z, x]
    face = range(top[x, 21] + 1 - aoe2mc.MIN_Y, top[x, z + 16] - aoe2mc.MIN_Y)   # the step down to the next column
    assert all(col[y] != aoe2mc.STONE for y in face)


def border_blocks(design, colors=("blue", "red")):
    """{(x, y, z): state} of one --border design around a 12 x 12 tile map (water in the east)."""
    import numpy as np
    t = np.zeros((12, 12), int)
    t[9:] = 1
    cols = columns(t)
    E = aoe2mc.Edits(cols)
    r = aoe2mc.border(cols, design, list(colors), E)
    x, y, z, ids, _ = (np.concatenate(p) for p in zip(*E.parts))
    return cols, r, {(a, b, c): aoe2mc.B.states[i] for a, b, c, i in zip(x, y, z, ids)}


def test_border_island():
    """The floating island (#262): a rim of earth at the edge, a cone under the map that is deepest at the center."""
    cols, r, blocks = border_blocks("island")
    n, f = cols.n, cols.floor
    assert r == 1 and f == int(cols.top[:n, :n].min()) - 6
    assert blocks[(-1, int(cols.wtop[0, 20]), 20)] == "minecraft:grass_block"
    assert blocks[(n, int(cols.wtop[n - 1, 20]), 20)] == "minecraft:sand"          # the rim holds the water
    bottom = lambda x, z: min(y for (a, y, c) in blocks if (a, c) == (x, z))
    assert bottom(n // 2, n // 2) < bottom(n // 2, 3) < bottom(n // 2, 0) <= f - 3
    assert "minecraft:hanging_roots[waterlogged=false]" in blocks.values()


def test_border_table():
    """The map table (#262): a lip above the ground, four legs and a banner in a player color on each corner."""
    cols, r, blocks = border_blocks("table")
    f = cols.floor
    assert r == 3
    assert blocks[(-1, int(cols.wtop[0, 20]) + 1, 20)] == "minecraft:dark_oak_planks"
    assert blocks[(-2, f - 10, -2)] == "minecraft:dark_oak_log[axis=y]"
    banners = sorted(s for s in blocks.values() if "banner" in s)
    assert banners == ["minecraft:blue_banner[rotation=10]", "minecraft:blue_banner[rotation=2]",
                       "minecraft:red_banner[rotation=14]", "minecraft:red_banner[rotation=6]"]
