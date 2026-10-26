"""The Minecraft data files for mcvalid: one per supported version."""
import aoe2mc
import mcvalid


def test_default_version_is_the_output_version():
    assert mcvalid.DEFAULT_VERSION == aoe2mc.VERSION_NAME                # the code uses the 26.3 names (#428)


def test_names_of_26_3():
    # 1.21.9 renamed chain to iron_chain (docs/minecraft-versions.md)
    assert mcvalid.block_error("minecraft:chain[axis=y]") is not None
    assert mcvalid.block_error("minecraft:iron_chain[axis=y]") is None
    # 1.21.2 gave each boat wood its own entity type
    assert mcvalid.entity_error("minecraft:boat") is not None
    assert mcvalid.entity_error("minecraft:oak_boat") is None
    assert mcvalid.biome_error("minecraft:mangrove_swamp") is None
