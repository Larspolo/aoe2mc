"""#2745 (epic #2737): with --resource-pack, the ravager of the war elephants has grey elephant skin and ivory tusks."""
import io
import zipfile

from PIL import Image

import aoe2mc

RAVAGER = "assets/minecraft/textures/entity/illager/ravager.png"


def test_the_pack_has_an_elephant_texture_for_the_ravager(tmp_path):
    aoe2mc.write_resourcepack(str(tmp_path))
    with zipfile.ZipFile(tmp_path / "resourcepacks" / "resources.zip") as z:
        im = Image.open(io.BytesIO(z.read(RAVAGER))).convert("RGBA")
    assert im.size == (128, 128)                                       # the size of the vanilla ravager texture
    r, g, b, a = im.getpixel((20, 20))                                 # the face of the head: grey skin
    assert a == 255 and abs(r - g) < 10 and abs(g - b) < 10 and 90 < g < 160
    assert im.getpixel((76, 62)) == (*aoe2mc.IVORY, 255)               # the horns are ivory tusks
    assert im.getpixel((19, 27)) == im.getpixel((28, 27)) == (30, 26, 24, 255)   # two dark eyes
    assert im.getpixel((64, 8))[3] == 255 and im.getpixel((100, 50))[3] == 0     # a leg; no pixel out of the boxes


def test_the_war_elephants_are_ravagers():
    for name in ("BATTLE_ELEPHANT", "ELEPHANT_ARCHER", "WAR_ELEPHANT"):
        assert str(aoe2mc.units.classify(name)["id"]) == "minecraft:ravager"
