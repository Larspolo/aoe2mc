"""The hills of the own generators Arabia and Highland (#3824)."""
import numpy as np

import rmap


def test_arabia_has_hills():
    d = rmap.random_map("arabia", 1)
    assert (np.array(d["elevation"]) > 0).sum() > 100


def test_highland_has_hills_and_flat_water():
    for seed in (1, 2, 3):
        d = rmap.random_map("highland", seed)
        e, t = np.array(d["elevation"]), np.array(d["terrain"])
        assert (e > 0).any()
        assert (e[np.isin(t, [rmap.TERRAINS["WATER"], rmap.TERRAINS["SHALLOW"]])] == 0).all()
