"""#2738: --resource-pack writes resourcepacks/resources.zip into the world folder (the 26.x place): the zombie units get a human face."""
import io
import json
import os
import zipfile

from PIL import Image

import aoe2mc

TEXTURES = ["assets/minecraft/textures/entity/zombie/husk.png", "assets/minecraft/textures/entity/zombie/zombie.png",
            "assets/minecraft/textures/entity/zombie_villager/zombie_villager.png"]


def test_the_pack_has_the_26_3_format_and_the_three_textures(tmp_path):
    aoe2mc.write_resourcepack(str(tmp_path))
    with zipfile.ZipFile(tmp_path / "resourcepacks" / "resources.zip") as z:
        assert {*TEXTURES, "pack.mcmeta"} <= set(z.namelist())     # and the weapons (#2744) and the cart (#2746)
        assert z.namelist() == sorted(z.namelist())
        pack = json.loads(z.read("pack.mcmeta"))["pack"]
        assert pack["pack_format"] == pack["min_format"] == pack["max_format"] == 97   # client.jar version.json
        for name in TEXTURES:
            im = Image.open(io.BytesIO(z.read(name))).convert("RGBA")
            assert im.size == (64, 64)
            e = 12 if "villager" in name else 10                    # the eye row of the 10 or 8 high face
            assert im.getpixel((9, e)) == (240, 240, 240, 255)      # the white of the left eye
            r, g, b, _ = im.getpixel((14, e + 1))                   # the cheek: skin, red over green (not a zombie)
            assert r > g > b


def test_two_packs_have_the_same_bytes(tmp_path):
    for d in ("a", "b"):
        os.makedirs(tmp_path / d)
        aoe2mc.write_resourcepack(str(tmp_path / d))
    assert (tmp_path / "a" / "resourcepacks" / "resources.zip").read_bytes() == \
        (tmp_path / "b" / "resourcepacks" / "resources.zip").read_bytes()


def test_without_the_option_the_world_has_no_pack(tiny_world):
    assert not os.path.exists(os.path.join(tiny_world[0], "resourcepacks"))
