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


def test_level_dat(tiny_world):
    level = world_reader.World(tiny_world[0]).level()
    assert int(level["DataVersion"]) == aoe2mc.DATA_VERSION
    assert str(level["LevelName"]) == "tiny"
    assert int(level["GameType"]) == 1


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
