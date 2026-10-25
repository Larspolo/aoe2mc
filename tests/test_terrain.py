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
