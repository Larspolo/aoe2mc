"""--orientation turns the finished map in steps of 90°, with all block directions (#23)."""
import contextlib
import io
import os

import numpy as np
import pytest
from PIL import Image

import aoe2mc
import mcvalid


@pytest.mark.parametrize("state, k, turned", [
    ("oak_door[facing=south,half=lower,hinge=left,open=false]", 1,
     "oak_door[facing=west,half=lower,hinge=left,open=false]"),
    ("oak_log[axis=x]", 1, "oak_log[axis=z]"),
    ("oak_log[axis=y]", 1, "oak_log[axis=y]"),
    ("oak_log[axis=x]", 2, "oak_log[axis=x]"),
    ("oak_sign[rotation=14]", 1, "oak_sign[rotation=2]"),
    ("oak_fence[east=true,north=false,south=false,west=true]", 1,
     "oak_fence[south=true,east=false,west=false,north=true]"),
    ("rail[shape=north_south]", 1, "rail[shape=east_west]"),
    ("rail[shape=south_east]", 1, "rail[shape=south_west]"),
    ("rail[shape=north_west]", 3, "rail[shape=south_west]"),
    ("rail[shape=ascending_north]", 1, "rail[shape=ascending_east]"),
    ("oak_stairs[facing=north,half=bottom,shape=inner_left]", 3, "oak_stairs[facing=west,half=bottom,shape=inner_left]"),
    ("barrel[facing=up]", 1, "barrel[facing=up]"),
])
def test_turn_state(state, k, turned):
    assert aoe2mc.turn_state(state, k) == turned
    assert mcvalid.block_error("minecraft:" + turned) is None


def house(k):
    """Blocks {(x, y, z): state} of a house at tile (4, 5) on a 12 × 12 map turned k times."""
    cols = aoe2mc.Columns(12, np.zeros((12, 12), np.int16), np.zeros((12, 12), np.float32),
                          {0: "GRASS_1"}, 4, 3, np.random.default_rng(1))
    o = dict(kind="B", name="HOUSE", player=1, x=4.0, y=5.0, rotation=0.0, hero=False, garrisoned=False)
    E, _ = aoe2mc.place_objects([o], {1: dict(color="blue", arch="western", civ="BRITONS")}, cols,
                                np.random.default_rng(1))
    aoe2mc.turn_world(cols, E, k)
    out = {}
    for xs, ys, zs, ids, _ in E.parts:
        out.update(((int(x), int(y), int(z)), aoe2mc.B.states[i]) for x, y, z, i in zip(xs, ys, zs, ids))
    return out, cols


@pytest.mark.parametrize("k", [0, 1, 2, 3])
def test_house_turns_with_the_map(k):
    raw, cols0 = house(0)
    turned, cols = house(k)
    n = cols.n
    expect = {}
    for (x, y, z), s in raw.items():
        tx, tz = aoe2mc.turn_xz(x, z, k, n - 1)
        expect[(tx, y, tz)] = "minecraft:" + aoe2mc.turn_state(s.removeprefix("minecraft:"), k)
    assert turned == expect
    assert (cols.blocked[:n, :n] == np.rot90(cols0.blocked[:n, :n], k)).all()
    # The door is on the side of the AoE2 camera: south for "ne", then west, north and east.
    cx, cz = aoe2mc.turn_xz(16, 20, k, n)                # the center of the house in block positions
    door = [(x + 0.5 - cx, z + 0.5 - cz, s) for (x, y, z), s in turned.items() if "_door[" in s]
    sx, sz = [(0, 1), (-1, 0), (0, -1), (1, 0)][k]
    assert door and all(sx * dx + sz * dz > abs(sx * dz - sz * dx) for dx, dz, _ in door)
    assert all(f"facing={aoe2mc.DIRS[(2 + k) % 4]}" in s for _, _, s in door)


def test_turned_world(tiny_world, tmp_path):
    """The preview of "sw" is the preview of "ne" turned by 180°. The spawn view turns too."""
    from nbtlib import load
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.main([os.path.join(os.path.dirname(tiny_world[0]), "tiny.aoe2scenario"), str(tmp_path / "W"),
                     "--preview", "--orientation", "sw"])
    a = np.array(Image.open(os.path.join(tiny_world[0], "preview.png")))
    b = np.array(Image.open(tmp_path / "W" / "preview.png"))
    assert (np.rot90(a, 2) == b).all()
    assert float(load(tmp_path / "W" / "level.dat")["Data"]["SpawnAngle"]) == aoe2mc.SPAWN_YAW + 180
