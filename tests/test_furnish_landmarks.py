"""The Hall of Heroes, the Temple of Heaven, the Oracle's temple and the Gol Gumbaz are furnished inside (#440)."""
from collections import Counter

import mcvalid
import numpy as np
import pytest

import aoe2mc
import buildings

T = 4
NEEDS = {"HALL_OF_HEROES": ("waxed_copper_block", "blue_carpet", "blue_wall_banner", "chest"),
         "TEMPLE_OF_HEAVEN": ("candle", "yellow_carpet", "red_carpet"),
         "ORACLES_TEMPLE": ("cauldron", "decorated_pot", "candle"),
         "GOL_GUMBAZ": ("smooth_quartz", "green_carpet", "candle", "lantern")}


def blocks(name, arch, tile=T):
    size = 16
    cols = aoe2mc.Columns(size, np.zeros((size, size), np.int16), np.zeros((size, size), np.float32),
                          {0: "GRASS_1"}, tile, 3, np.random.default_rng(1))
    E = aoe2mc.Edits(cols)
    o = dict(kind="B", name=name, player=1, x=8.0, y=8.0, rotation=0.0, hero=False, garrisoned=False)
    buildings.place_building(E, cols, aoe2mc.B, o, {1: {"color": "blue", "arch": arch}}, set(), {})
    last = {}
    for x, y, z, ids, _ in E.parts:
        for p in zip(x.tolist(), y.tolist(), z.tolist(), ids.tolist()):
            last[p[:3]] = aoe2mc.B.states[p[3]].split(":")[1]
    return last


@pytest.mark.parametrize("arch", ["western", "east_asian", "middle_eastern"])
@pytest.mark.parametrize("name", sorted(NEEDS))
def test_landmark_is_furnished(name, arch):
    last = blocks(name, arch)
    names = Counter(s.split("[")[0] for s in last.values())
    assert all(names[n] >= 1 for n in NEEDS[name]), (name, arch, {n: names[n] for n in NEEDS[name]})
    assert mcvalid.invalid_states(aoe2mc.B.states) == {}
    for (x, y, z), s in last.items():                    # the cells inside the main door stay free
        if s.endswith("_door[facing=south,half=lower,hinge=left,open=false]"):
            inside = last.get((x, y, z - 1), "air")
            assert inside in ("air", "barrier") or inside.endswith("_carpet"), (name, inside)


@pytest.mark.parametrize("tile", [1, 2, 3])
@pytest.mark.parametrize("name", sorted(NEEDS))
def test_small_tile_sizes_work(name, tile):
    blocks(name, "western", tile)
