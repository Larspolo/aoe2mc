"""Convert the synthetic tiny scenario and read the world back."""
import os

import aoe2mc
import mcvalid
import world_reader
from conftest import entity_ids


def test_world_files(tiny_world):
    path, _ = tiny_world
    for f in ("level.dat", "preview.png", "region/r.0.0.mca", "entities/r.0.0.mca"):
        assert os.path.exists(os.path.join(path, f)), f


def test_world_icon(tiny_world):
    from PIL import Image
    with Image.open(os.path.join(tiny_world[0], "icon.png")) as im:
        assert im.size == (64, 64)                                # the size of the Minecraft world list icon


def test_level_dat(tiny_world):
    level = world_reader.World(tiny_world[0]).level()
    assert int(level["DataVersion"]) == aoe2mc.DATA_VERSION
    assert str(level["LevelName"]) == "tiny"
    assert int(level["GameType"]) == 1
    assert float(level["SpawnAngle"]) == aoe2mc.SPAWN_YAW == -135  # look north-east, like the AoE2 camera (#23)


def test_chunks_have_valid_blocks_and_biomes(tiny_world):
    w = world_reader.World(tiny_world[0])
    chunks = w.chunks()
    assert len(chunks) == 36                                      # 24 tiles * 4 blocks = 96 blocks = 6 x 6 chunks
    for (cx, cz), c in chunks.items():
        assert int(c["DataVersion"]) == aoe2mc.DATA_VERSION
        assert (int(c["xPos"]), int(c["zPos"])) == (cx, cz)
        for s in c["sections"]:
            for b in s["biomes"]["palette"]:
                assert mcvalid.biome_error(str(b)) is None
    assert mcvalid.invalid_states(w.palette()) == {}


def test_terrain_and_water(tiny_world):
    w = world_reader.World(tiny_world[0])
    assert w.block(90, aoe2mc.WATER_Y, 48) == "minecraft:water[level=0]"       # deep water at x >= 20 tiles
    assert w.block(90, aoe2mc.WATER_Y - 3, 48) == "minecraft:water[level=0]"
    assert w.block(0, aoe2mc.MIN_Y, 0) == "minecraft:bedrock"


def test_entities(tiny_world):
    path, out = tiny_world
    ents = world_reader.World(path).entities(flat=False)
    ids = [i for e in ents for i in entity_ids(e)]
    for i in ids:
        assert mcvalid.entity_error(i) is None, i
    assert "minecraft:horse" in ids and "minecraft:villager" in ids and "minecraft:skeleton" in ids
    assert "units in a block (moved up): 0" in out


def test_mc_version_26_3(tmp_path, monkeypatch):
    import contextlib
    import io

    import scenarios
    src = scenarios.tiny(str(tmp_path / "tiny.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.main([src, str(tmp_path / "W"), "--mc-version", "26.3"])
    w = world_reader.World(str(tmp_path / "W"))
    level = w.level()
    assert (int(level["DataVersion"]), str(level["Version"]["Name"])) == (5023, "26.3")
    assert {int(c["DataVersion"]) for c in w.chunks().values()} == {5023}
    assert {int(c["DataVersion"]) for c in w.chunks("entities").values()} == {5023}
    assert mcvalid.invalid_states(w.palette(), "26.3") == {}
    assert aoe2mc.MC["name"] == aoe2mc.VERSION_NAME               # convert() restores the default version
    # block renames of the version profile
    monkeypatch.setattr(aoe2mc, "MC", aoe2mc.VERSIONS["26.3"])
    assert str(aoe2mc.B.nbt(aoe2mc.B("chain[axis=y]"))["Name"]) == "minecraft:iron_chain"
