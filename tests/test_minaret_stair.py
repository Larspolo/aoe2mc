"""The Minaret of Jam has a door and a spiral stair up to the top balcony (#452)."""
import mcvalid
import numpy as np
import pytest

import aoe2mc
import buildings


def blocks(monkeypatch, tile=4):
    monkeypatch.setattr(buildings, "BARRIERS", False)
    size = 16
    cols = aoe2mc.Columns(size, np.zeros((size, size), np.int16), np.zeros((size, size), np.float32),
                          {0: "GRASS_1"}, tile, 3, np.random.default_rng(1))
    E = aoe2mc.Edits(cols)
    o = dict(kind="B", name="MINARET_OF_JAM", player=1, x=8.0, y=8.0, rotation=0.0, hero=False, garrisoned=False)
    buildings.place_building(E, cols, aoe2mc.B, o, {1: {"color": "blue", "arch": "middle_eastern"}}, set(), {})
    last = {}
    for x, y, z, ids, _ in E.parts:
        for p in zip(x.tolist(), y.tolist(), z.tolist(), ids.tolist()):
            last[p[:3]] = aoe2mc.B.states[p[3]].split(":")[1]
    return last


def test_stair_goes_up_to_the_balcony(monkeypatch):
    last = blocks(monkeypatch)
    stairs = sorted((y, x, z) for (x, y, z), s in last.items() if s.startswith("smooth_sandstone_stairs"))
    door = [(x, y, z) for (x, y, z), s in last.items() if s.startswith("jungle_door") and "half=lower" in s]
    assert len(door) == 1 and mcvalid.invalid_states(aoe2mc.B.states) == {}
    dx, dy, dz = door[0]
    ys = [y for y, _, _ in stairs]
    assert ys == list(range(dy, dy + len(ys))) and len(ys) > 20               # one step per block of height
    free = lambda s: s == "air" or s.startswith("lantern")
    assert free(last.get((dx, dy, dz - 1), "air")) and free(last.get((dx, dy + 1, dz - 1), "air"))
    for y, x, z in stairs:                                                     # two blocks of headroom over each step
        assert free(last.get((x, y + 1, z), "air")) and free(last.get((x, y + 2, z), "air")), (x, y, z)
    for (_, x, z), (y, _, _) in zip(stairs, stairs[1:]):                       # the head passes over the edge
        assert free(last.get((x, y + 2, z), "air")), (x, y, z)
    y, x, z = stairs[-1]
    assert all(free(last.get((x, y + k, z), "air")) for k in (1, 2, 3))       # out through the drum
    assert sum(s.startswith("lantern") for s in last.values()) >= 4


@pytest.mark.parametrize("tile", [1, 2, 3])
def test_small_tile_sizes_work(monkeypatch, tile):
    blocks(monkeypatch, tile)
