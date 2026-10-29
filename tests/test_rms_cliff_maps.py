"""The own random map generators with cliffs in AoE2 DE have cliff lines (#3853)."""
import numpy as np
import pytest

import rmap

CLIFFED = {"arabia", "highland"}               # the AoE2 wiki names cliffs only on these maps


def cliffs(d):
    return [o for o in d["objects"] if o["name"].startswith("CLIFF")]


@pytest.mark.parametrize("seed", range(1, 4))
def test_highland_cliffs_avoid_the_starts_and_the_river(seed):
    d = rmap.random_map("highland", seed)
    t, c = np.array(d["terrain"]), cliffs(d)
    assert c
    wet = rmap.dilate(np.isin(t, [rmap.TERRAINS["WATER"], rmap.TERRAINS["SHALLOW"]]), 1)
    for o in c:
        x, y = int(o["x"]), int(o["y"])
        assert not wet[x, y]
        for st in d["lands"]:
            assert max(abs(x - st["x"]), abs(y - st["y"])) > st["base_size"]


@pytest.mark.parametrize("kind", sorted(rmap.GENERATORS))
def test_only_the_cliffed_maps_have_cliffs(kind):
    assert bool(cliffs(rmap.random_map(kind, 5))) == (kind in CLIFFED)
