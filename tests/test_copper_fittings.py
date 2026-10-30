"""The castle and the wonder have copper lanterns, chains and bars; other designs keep iron ones (#543)."""
import mcvalid
import render

import aoe2mc
import buildings


def names(name, arch):
    return {s.split(":")[-1].partition("[")[0] for s in render.building_blocks(name, arch)[3]}


def test_castle_has_copper_lanterns_and_window_bars():
    n = names("CASTLE", "western")
    assert {"waxed_copper_lantern", "waxed_copper_bars"} <= n and "lantern" not in n
    assert "iron_bars" in n                                     # the portcullis stays iron


def test_wonder_has_copper_lanterns():
    n = set().union(*(names("WONDER", a) for a in ("western", "middle_eastern", "east_asian")))
    assert "waxed_copper_lantern" in n and not n & {"lantern", "iron_chain", "iron_bars"}


def test_hanging_lantern_under_a_high_ceiling_hangs_on_a_copper_chain():
    c = buildings.Canvas(aoe2mc.B, 5, height=12)
    c.room(0, 5, 0, 5, 0, 7, "stone_bricks")
    c.box(0, 5, 8, 9, 0, 5, "stone_bricks")                    # the ceiling
    c.set(2, 4, 2, "lantern[hanging=true]")
    buildings.copper_fittings(c)
    assert [aoe2mc.B.states[c.get(2, y, 2)] for y in (4, 5, 6, 7)] == [
        "minecraft:waxed_copper_lantern[hanging=true]", *["minecraft:waxed_copper_chain[axis=y]"] * 3]


def test_other_designs_keep_their_lanterns():
    assert "waxed_copper_lantern" not in names("KREPOST", "western")
    assert mcvalid.invalid_states(aoe2mc.B.states) == {}
