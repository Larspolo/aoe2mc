"""Every AoE2 terrain gives valid Minecraft blocks and a valid biome."""
import pytest
from AoE2ScenarioParser.datasets.terrains import TerrainId

import aoe2mc
import mcvalid


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
