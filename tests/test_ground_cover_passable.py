"""Wildflowers and leaf litter have no collision in Minecraft: a unit stands in them (#3027)."""
import aoe2mc


def test_wildflowers_and_leaf_litter_are_passable():
    states = ["minecraft:wildflowers[facing=north,flower_amount=3]",
              "minecraft:leaf_litter[facing=east,segment_amount=2]"]
    assert list(aoe2mc.passable_states(states)[:2]) == [True, True]


def test_passable_keys_name_the_ground_cover():
    assert "wildflowers" in aoe2mc.PASSABLE and "leaf_litter" in aoe2mc.PASSABLE
