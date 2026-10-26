"""A locked map item of the whole world (#838): aoe2mc.write_map writes data/minecraft/maps/0.dat."""
import os

import numpy as np
from nbtlib import File

import aoe2mc


def test_map_scale():
    assert [aoe2mc.map_scale(n) for n in (64, 128, 129, 480, 1920, 4000)] == [0, 0, 1, 2, 4, 4]


def test_map_colors_of_water_and_grass():
    img = np.zeros((200, 200, 3), np.uint8)
    img[:] = aoe2mc.block_color("minecraft:grass_block[snowy=false]")
    img[:, 100:] = aoe2mc.block_color("minecraft:water[level=0]")
    colors, s, c = aoe2mc.map_colors(img)
    assert (s, c) == (1, 100) and colors.shape == (128, 128)
    # scale 1: pixel k shows blocks 2k - 28 and 2k - 27; the world (0 to 199) is pixels 14 to 113
    assert colors[64, 20] // 4 == 1                    # GRASS
    assert colors[64, 100] == 32 * 4 + 0               # LAPIS, dark: the nearest to the blue of the top view
    assert colors[64, 13] == colors[13, 64] == colors[64, 114] == 0 and colors[64, 14] and colors[64, 113]


def test_write_map(tmp_path):
    img = np.full((64, 64, 3), aoe2mc.block_color("minecraft:sand"), np.uint8)
    aoe2mc.write_map(str(tmp_path), img)
    d = tmp_path / "data" / "minecraft" / "maps"
    m = File.load(str(d / "0.dat"), gzipped=True)
    assert int(m["DataVersion"]) == aoe2mc.MC["data_version"]
    v = m["data"]
    assert {k: int(v[k]) for k in ("scale", "xCenter", "zCenter", "locked", "trackingPosition", "unlimitedTracking")} \
        == {"scale": 0, "xCenter": 32, "zCenter": 32, "locked": 1, "trackingPosition": 0, "unlimitedTracking": 0}
    assert str(v["dimension"]) == "minecraft:overworld" and len(v["banners"]) == len(v["frames"]) == 0
    colors = np.array(v["colors"], np.int8).astype(np.uint8)
    assert len(colors) == 128 * 128 and colors[64 * 128 + 64] // 4 == 2 and colors[0] == 0     # SAND, outside
    assert int(File.load(str(d / "last_id.dat"), gzipped=True)["data"]["map"]) == 0


def test_converted_world_has_the_map(tiny_world):
    assert os.path.exists(os.path.join(tiny_world[0], "data", "minecraft", "maps", "0.dat"))
