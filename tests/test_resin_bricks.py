"""The Trowulan split gate is of orange fired brick: the resin bricks of 26.3 (#555)."""
import mcvalid
import render

import aoe2mc


def names(name, arch="southeast_asian"):
    return [s.split(":")[-1] for s in render.building_blocks(name, arch)[3]]


def test_split_gate_uses_resin_bricks():
    found = names("TROWULAN_GATE")
    assert found.count("resin_bricks") > 100 and "chiseled_resin_bricks" in found
    assert not {"bricks", "mud_bricks"} & set(found)
    assert all(mcvalid.block_error(s) is None for s in set(found))


def test_other_designs_keep_their_brick_and_the_render_has_a_color():
    assert not any(s.startswith(("resin_brick", "chiseled_resin")) for s in names("HOUSE", "western"))
    assert aoe2mc.COLORS[[k for k, _ in aoe2mc.COLORS].index("resin_brick")][1] != dict(aoe2mc.COLORS)["bricks"]
