"""The objects of decor() get their decor design: place_objects() reaches no later case for them (#3042)."""
import numpy as np

import aoe2mc


def blocks(name):
    cols = aoe2mc.Columns(16, np.zeros((16, 16), np.int16), np.zeros((16, 16), np.float32),
                          {0: "GRASS_1"}, 4, 3, np.random.default_rng(1))
    o = dict(kind="O", name=name, player=0, x=8.5, y=8.5, rotation=0.0, hero=False, garrisoned=False)
    E, _ = aoe2mc.place_objects([o], {}, cols, np.random.default_rng(1))
    _, _, _, ids, _ = (np.concatenate(p) for p in zip(*E.parts))
    return sorted(aoe2mc.B.states[i].split(":")[1] for i in ids)


def test_lumber_is_a_log_pile():
    assert blocks("LUMBER") == ["oak_log[axis=x]"] * 4


def test_flower_bed_is_a_bed_of_flowers():
    assert blocks("FLOWER_BED") == ["allium", "oxeye_daisy", "oxeye_daisy", "poppy", "poppy", "red_tulip", "red_tulip"]


def test_sign_is_a_sign_without_fence():
    assert blocks("SIGN") == ["oak_sign[rotation=8]"]


def test_broken_cart_is_the_decor_cart():
    assert blocks("BROKEN_CART") == ["barrel[facing=east]", "spruce_slab[type=bottom]", "spruce_slab[type=bottom]",
                                     "spruce_trapdoor[facing=east,half=bottom,open=true]"]


def test_plant_flowers_is_the_decor_flower_bed():
    assert blocks("PLANT_FLOWERS") == blocks("FLOWER_BED")


def test_skeleton_and_torch_keep_their_cases():
    assert blocks("SKELETON_1") == ["bone_block[axis=x]", "bone_block[axis=z]"]
    assert blocks("TORCH_A") == ["oak_fence", "torch"]
