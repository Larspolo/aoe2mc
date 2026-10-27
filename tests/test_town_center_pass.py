"""Units walk under the town center, as in AoE2 (#865): its open ground floor has no barriers and no blocked cells."""
import numpy as np
import pytest

import aoe2mc
import buildings
from game.gather import Map

T = 4


def town_center(arch, ref=None):
    cols = aoe2mc.Columns(16, np.zeros((16, 16), np.int16), np.zeros((16, 16), np.float32), {0: "GRASS_1"}, T, 3,
                          np.random.default_rng(1))
    E = aoe2mc.Edits(cols)
    o = dict(kind="B", name="TOWN_CENTER", player=1, x=8.0, y=8.0, rotation=0.0, hero=False, garrisoned=False, ref=ref)
    buildings.place_building(E, cols, aoe2mc.B, o, {1: {"color": "blue", "arch": arch}}, set(), {})
    last = {}
    for xs, ys, zs, ids, _ in E.parts:
        for p in zip(xs.tolist(), ys.tolist(), zs.tolist(), ids.tolist()):
            last[p[:3]] = p[3]
    return cols, o, last


@pytest.mark.parametrize("arch", sorted(buildings.ARCH))
def test_the_ground_floor_of_the_town_center_is_open(arch):
    cols, o, last = town_center(arch)
    x0, z0, x1, z1 = o["footprint"]
    base = int(cols.wtop[x0:x1, z0:z1].max())
    opened = {tuple(c) for c in o["open"]}
    assert len(opened) > (x1 - x0) * (z1 - z0) // 3                   # most of the ground floor
    for x in range(x0, x1):
        for z in range(z0, z1):
            head = [aoe2mc.B.states[last[(x, y, z)]] if (x, y, z) in last else "minecraft:air"
                    for y in (base + 1, base + 2)]
            if (x, z) in opened:
                assert not cols.blocked[x, z]
                assert all(aoe2mc.passable_states([s])[0] for s in head), (x, z, head)
            else:
                assert cols.blocked[x, z] and not all(aoe2mc.passable_states([s])[0] for s in head)


def test_a_path_goes_under_the_town_center():
    n = 24
    data = {"tile_size": T, "ground": [" ".join(["64"] * n)] * n,
            "objects": [{"name": "TOWN_CENTER", "kind": "building", "player": 2, "tile": [3.0, 3.0],
                         "footprint": [4, 4, 20, 20], "open": [[x, 12] for x in range(4, 20)]}]}
    m = Map(data)
    path = m.path((2, 12), {(21, 12)})
    assert path and len(path) == 19 and all(z == 12 for _, z in path)
    data["objects"][0].pop("open")
    assert len(Map(data).path((2, 12), {(21, 12)})) > 19                 # without open cells: around it


def test_the_replay_keeps_the_open_cells_of_a_new_town_center():
    from test_replay import Fake, data

    from game import replay
    r = replay.Replay(Fake(), data([]))
    assert r.commands({"time": 1000, "player": 1, "kind": "build", "type": 109, "name": "TOWN_CENTER",
                       "tile": [8.0, 8.0]})
    x0, x1, z0, z1 = rect = r.placed[-1][2]
    m, opened = r.grid(), r.open[rect]
    assert len(opened) > (x1 - x0) * (z1 - z0) // 3
    for x in range(x0, x1):
        for z in range(z0, z1):
            assert m.free(x, z) == ((x, z) in opened)
