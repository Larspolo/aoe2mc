"""Connections of panes, iron bars, fences and walls (#189): Edits.connect() sets them from the final neighbours."""
from types import SimpleNamespace

import numpy as np

import aoe2mc
from aoe2mc import B, Edits


def final(edits, width=64):
    """{(x, y, z): state} of the last block at each position, after connect()."""
    edits.connect()
    out = {}
    for (cx, cz), (x, y, z, ids, hard) in edits.by_chunk(width).items():
        for a, b, c, i in zip(x, y, z, ids):
            out[(cx * 16 + int(a), int(b), cz * 16 + int(c))] = B.states[int(i)][10:]
    return out


def props(state):
    return dict(kv.split("=") for kv in state.partition("[")[2][:-1].split(","))


def test_pane_between_two_walls_is_a_full_pane():
    e = Edits()
    e.box(1, 2, 70, 71, 5, 6, "stone_bricks"); e.box(3, 4, 70, 71, 5, 6, "stone_bricks")
    e.box(2, 3, 70, 71, 5, 6, "glass_pane")
    p = props(final(e)[(2, 70, 5)])
    assert (p["east"], p["west"], p["north"], p["south"]) == ("true", "true", "false", "false")


def test_lone_pane_and_bars():
    e = Edits()
    e.box(2, 3, 70, 71, 5, 6, "glass_pane")
    e.box(8, 11, 70, 71, 5, 6, "iron_bars")                  # three bars in a row connect to each other
    f = final(e)
    assert set(props(f[(2, 70, 5)]).values()) == {"false"}
    assert props(f[(9, 70, 5)])["east"] == props(f[(9, 70, 5)])["west"] == "true"
    assert props(f[(8, 70, 5)])["west"] == "false"


def test_pane_does_not_connect_to_leaves_barriers_or_slabs():
    e = Edits()
    e.box(1, 2, 70, 71, 5, 6, "oak_leaves[distance=1,persistent=true,waterlogged=false]")
    e.box(3, 4, 70, 71, 5, 6, "barrier")
    e.box(2, 3, 70, 71, 4, 5, "stone_slab[type=bottom,waterlogged=false]")
    e.box(2, 3, 70, 71, 5, 6, "glass_pane")
    assert set(props(final(e)[(2, 70, 5)]).values()) == {"false"}


def test_wall_row():
    e = Edits()
    e.box(0, 3, 70, 71, 5, 6, "stone_brick_wall")
    e.box(10, 13, 70, 71, 5, 6, "stone_brick_wall")
    e.box(11, 12, 71, 72, 5, 6, "stone_bricks")              # a block on the middle wall
    f = final(e)
    mid, end = props(f[(1, 70, 5)]), props(f[(0, 70, 5)])
    assert (mid["east"], mid["west"], mid["north"], mid["up"]) == ("low", "low", "none", "false")
    assert (end["east"], end["west"], end["up"]) == ("low", "none", "true")
    covered = props(f[(11, 70, 5)])
    assert (covered["east"], covered["west"], covered["up"]) == ("tall", "tall", "false")


def test_fence_row_across_a_chunk_border_and_gates():
    e = Edits()
    e.box(14, 18, 70, 71, 3, 4, "spruce_fence")              # x 14..17: the chunk border is between 15 and 16
    e.box(18, 19, 70, 71, 3, 4, "oak_fence_gate[facing=north,in_wall=false,open=false,powered=false]")
    e.box(14, 15, 70, 71, 4, 5, "nether_brick_fence")         # another fence family: no connection
    f = final(e)
    assert props(f[(15, 70, 3)])["east"] == "true" and props(f[(16, 70, 3)])["west"] == "true"
    assert props(f[(17, 70, 3)])["east"] == "true"           # the gate is in line (it faces north)
    assert props(f[(14, 70, 3)])["south"] == "false"
    assert props(f[(14, 70, 4)])["north"] == "false"


def test_ground_neighbour_and_waterlogged():
    cols = SimpleNamespace(top=np.full((32, 32), 60, np.int32))
    e = Edits(cols)
    e.box(5, 6, 60, 62, 5, 6, "oak_fence[east=false,north=false,south=false,waterlogged=true,west=false]")
    f = final(e)
    low, high = props(f[(5, 60, 5)]), props(f[(5, 61, 5)])
    assert set(low[d] for d in ("north", "east", "south", "west")) == {"true"}   # next to the ground
    assert set(high[d] for d in ("north", "east", "south", "west")) == {"false"}
    assert low["waterlogged"] == "true"


def test_states_are_valid():
    import mcvalid
    e = Edits()
    for i, b in enumerate(["glass_pane", "iron_bars", "spruce_fence", "cobblestone_wall", "red_stained_glass_pane"]):
        e.box(0, 4, 70, 72, 2 * i, 2 * i + 1, b)
    for s in final(e).values():
        assert mcvalid.block_error(s) is None, s
    assert aoe2mc.connect_kind("minecraft:light_gray_wool") == "solid"
