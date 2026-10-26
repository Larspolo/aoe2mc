"""The Minecraft data files for mcvalid: one per supported version."""
import aoe2mc
import mcvalid


def test_default_version_is_the_version_of_the_code_names():
    for v in aoe2mc.VERSIONS.values():                                  # the output versions rename from these names
        for old, new in v["renames"].items():
            assert mcvalid.block_error(old) is None and mcvalid.block_error(new, v["name"]) is None
            assert mcvalid.block_error(old, v["name"]) is not None


def test_version_data_differs():
    # 1.21.9 renamed chain to iron_chain (docs/minecraft-versions.md)
    assert mcvalid.block_error("minecraft:chain[axis=y]") is None
    assert mcvalid.block_error("minecraft:chain[axis=y]", "26.3") is not None
    assert mcvalid.block_error("minecraft:iron_chain[axis=y]", "26.3") is None
    assert mcvalid.block_error("minecraft:iron_chain[axis=y]") is not None
    # 1.21.2 gave each boat wood its own entity type
    assert mcvalid.entity_error("minecraft:boat") is None
    assert mcvalid.entity_error("minecraft:boat", "26.3") is not None
    assert mcvalid.entity_error("minecraft:oak_boat", "26.3") is None
    assert mcvalid.biome_error("minecraft:mangrove_swamp", "26.3") is None
