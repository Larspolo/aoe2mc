"""--orientation turns the tile grid by quarter turns: terrain, objects, units, buildings and the spawn view (#23)."""
import contextlib
import io
import math

import mcvalid
import numpy as np
import pytest
import world_reader

import aoe2mc
import buildings


@pytest.mark.parametrize("o", sorted(aoe2mc.ORIENTATIONS))
def test_turn_tile_matches_the_terrain_turn(o):
    k, yaw = aoe2mc.ORIENTATIONS[o]
    t = np.arange(36).reshape(6, 6)
    obj = [dict(x=1.5, y=4.5, rotation=0.0)]
    t2, _ = aoe2mc.turn_map(k, 6, t, t.astype(np.float32), obj, {1: {"view": (2, 3)}})
    assert t2[int(obj[0]["x"]), int(obj[0]["y"])] == t[1, 4]
    # The top corner of the AoE2 screen (tile (max, 0)) goes to the corner that the name gives.
    x, y = aoe2mc.turn_tile(6, 0, 6, k)
    assert ("n" if y == 0 else "s") + ("e" if x == 6 else "w") == o
    # The spawn yaw looks at that corner (Minecraft: the view direction is (-sin yaw, cos yaw)).
    assert (round(-math.sin(math.radians(yaw))), round(math.cos(math.radians(yaw)))) == \
           ((1 if x else -1), (1 if y else -1))
    # A unit that looks along tile +x looks along the turned +x axis.
    r = obj[0]["rotation"]
    assert (round(math.cos(r)), round(math.sin(r))) == aoe2mc.turn_tile(1, 0, 0, k)


def test_turn_state():
    for s in ("oak_stairs[facing=north,half=bottom,shape=inner_left]", "rail[shape=south_east]",
              "oak_fence[east=true,north=false,south=false,waterlogged=false,west=false]", "white_banner[rotation=14]"):
        assert buildings.turn_state(s, 4) == s
        assert buildings.turn_state(buildings.turn_state(s, 1), 3) == s
    assert buildings.turn_state("oak_door[facing=south,half=lower]", 1) == "oak_door[facing=west,half=lower]"
    assert buildings.turn_state("oak_log[axis=x]", 1) == "oak_log[axis=z]"


def blocks(o, k):
    cols = aoe2mc.Columns(16, np.zeros((16, 16), np.int16), np.zeros((16, 16), np.float32), {0: "GRASS_1"}, 4, 3,
                          np.random.default_rng(1))
    buildings.TURN = k
    try:
        E, _ = aoe2mc.place_objects([dict(dict(kind="B", player=1, rotation=0.0, hero=False, garrisoned=False), **o)],
                                    {}, cols, np.random.default_rng(1))
    finally:
        buildings.TURN = 0
    x, y, z, ids, _ = (np.concatenate(p) for p in zip(*E.parts))
    return {(int(a), int(b), int(c)): aoe2mc.B.states[i] for a, b, c, i in zip(x, y, z, ids)}


@pytest.mark.parametrize("name", ["HOUSE", "BARRACKS", "CASTLE", "DOCK"])
def test_buildings_turn_with_the_map(name):
    """A building in the map center turns in place: each block goes to the turned position, with turned states."""
    raw = blocks(dict(name=name, x=8.0, y=8.0), 0)
    for k in (1, 2, 3):
        turned = blocks(dict(name=name, x=8.0, y=8.0), k)
        want = {}
        for (x, y, z), s in raw.items():
            for _ in range(k):
                x, z = 63 - z, x
            want[x, y, z] = buildings.turn_state(s, k)
        assert turned == want, (name, k)
        assert mcvalid.invalid_states(turned.values()) == {}


def test_building_position():
    """A house (2 × 2 tiles) at tile (4, 6) is at tile (10, 4) after one turn (orientation se)."""
    obj = [dict(kind="B", name="HOUSE", x=4.0, y=6.0, rotation=0.0)]
    aoe2mc.turn_map(1, 16, np.zeros((16, 16)), np.zeros((16, 16)), obj, {})
    assert (obj[0]["x"], obj[0]["y"]) == (10.0, 4.0)
    low = [(x, z) for (x, y, z) in blocks(dict(name="HOUSE", x=10.0, y=4.0), 1) if y <= aoe2mc.WATER_Y + 8]
    xs, zs = zip(*low)
    assert (min(xs), max(xs), min(zs), max(zs)) == (36, 43, 12, 19)


def test_convert_with_orientation(tmp_path):
    import scenarios
    src = scenarios.tiny(str(tmp_path / "tiny.aoe2scenario"))
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        aoe2mc.convert(src, str(tmp_path / "W"), orientation="nw")
    assert world_reader.World(str(tmp_path / "W")).spawn()[3] == 135
    assert "units in a block (moved up): 0" in out.getvalue() or "moved up" not in out.getvalue()
    assert buildings.TURN == 0


def test_lone_diagonal_gate_turns():
    """Without walls next to it, a diagonal gate takes its diagonal from the name; an odd turn swaps it."""
    o = dict(kind="B", name="GATE_NORTH_TO_SOUTH", x=8.5, y=8.5)
    assert buildings.plan_walls([o])[1][id(o)] == "diag-"
    buildings.TURN = 1
    try:
        assert buildings.plan_walls([o])[1][id(o)] == "diag+"
    finally:
        buildings.TURN = 0


def test_book_is_in_the_spawn_view():
    """The lectern with the scenario texts is in front of the turned spawn view (south-west for sw)."""
    for k, want in ((0, (42, 38)), (2, (38, 42))):
        cols = aoe2mc.Columns(20, np.zeros((20, 20), np.int16), np.zeros((20, 20), np.float32), {0: "GRASS_1"}, 4, 3,
                              np.random.default_rng(1))
        buildings.TURN = k
        try:
            assert aoe2mc.place_book(cols, aoe2mc.Edits(), (40, 70, 40), {"instructions": "Win."}, "t")[::2] == want
        finally:
            buildings.TURN = 0
