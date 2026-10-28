"""#2752: with --resource-pack the archers (skeleton), skirmishers (drowned) and cavalry archer horses (skeleton_horse)
get a human look: a skin and a face, no seaweed overlay, and a brown horse coat."""
import io
import zipfile

from PIL import Image

import aoe2mc

T = "assets/minecraft/textures/entity/"


def textures(tmp_path):
    aoe2mc.write_resourcepack(str(tmp_path))
    with zipfile.ZipFile(tmp_path / "resourcepacks" / "resources.zip") as z:
        return {n: Image.open(io.BytesIO(z.read(n))).convert("RGBA") for n in z.namelist() if n.endswith(".png")}


def test_the_archer_and_skirmisher_textures_have_a_human_face(tmp_path):
    ims = textures(tmp_path)
    assert ims[T + "skeleton/skeleton.png"].size == (64, 32)               # the size of the skeleton model
    assert ims[T + "zombie/drowned.png"].size == (64, 64)
    for name in ("skeleton/skeleton.png", "zombie/drowned.png"):
        im = ims[T + name]
        assert im.getpixel((9, 10)) == (240, 240, 240, 255)               # the white of the left eye
        r, g, b, _ = im.getpixel((14, 11))                                 # the cheek: skin
        assert r > g > b


def test_the_skeleton_arms_and_the_drowned_left_limbs_are_drawn(tmp_path):
    ims = textures(tmp_path)
    assert ims[T + "skeleton/skeleton.png"].getpixel((42, 20))[3] == 255   # the front of the thin arm
    assert ims[T + "skeleton/skeleton.png"].getpixel((50, 20))[3] == 0     # not the 4 wide zombie arm (40..55)
    drowned = ims[T + "zombie/drowned.png"]
    assert drowned.getpixel((36, 54))[3] == drowned.getpixel((20, 54))[3] == 255   # the left arm and leg


def test_the_drowned_overlay_is_empty_and_the_horse_is_brown(tmp_path):
    ims = textures(tmp_path)
    assert ims[T + "zombie/drowned_outer_layer.png"].getbbox() is None
    horse = ims[T + "horse/horse_skeleton.png"]
    assert horse.size == (64, 64)
    r, g, b, a = horse.getpixel((30, 40))
    assert a == 255 and r > g > b                                          # brown, not bone white
