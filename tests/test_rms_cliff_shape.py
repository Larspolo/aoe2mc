"""cliff_curliness, min_distance_cliffs and min_terrain_distance of <CLIFF_GENERATION> shape the cliff lines (#3851)."""
import numpy as np
import pytest
from test_rms_cliffs import LAND

import rmap


def lines(extra, seed):
    text = LAND + "<CLIFF_GENERATION>\nmin_number_of_cliffs 4\nmax_number_of_cliffs 4\n" + extra
    d = rmap.generate(text, seed, size=120, warn=lambda m: pytest.fail(m))     # no "is not read yet"
    out = {}
    for o in d["objects"]:
        if o["name"].startswith("CLIFF_DEFAULT_"):
            out.setdefault(o["line"], []).append((int(o["x"]), int(o["y"])))
    assert out
    return d, {k: np.array(v) for k, v in out.items()}


@pytest.mark.parametrize("seed", range(1, 6))
def test_no_curliness_gives_straight_lines(seed):
    _, ls = lines("cliff_curliness 0\n", seed)
    for p in ls.values():
        assert len({tuple(s) for s in np.diff(p, axis=0)}) == 1


@pytest.mark.parametrize("seed", range(1, 6))
def test_min_distance_cliffs_keeps_the_lines_apart(seed):
    _, ls = lines("min_distance_cliffs 6\n", seed)
    for a in ls:
        for b in ls:
            if a < b:
                assert np.abs(ls[a][:, None] - ls[b][None]).max(-1).min() >= 6


@pytest.mark.parametrize("seed", range(1, 6))
def test_min_terrain_distance_keeps_the_pieces_from_water(seed):
    d, ls = lines("min_terrain_distance 4\n", seed)
    water = np.argwhere(np.isin(np.array(d["terrain"]), [rmap.TERRAINS["WATER"], rmap.TERRAINS["SHALLOW"]]))
    for p in ls.values():
        assert np.abs(p[:, None] - water[None]).max(-1).min() >= 4
